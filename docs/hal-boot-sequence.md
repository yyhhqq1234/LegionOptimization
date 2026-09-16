# HAL 开机时序设计（P2 Step 2-1，E3 附录）

> 状态：设计稿，待 Step 2-2 两次重启实测标定 | 上游：`plans/PHASE-02-e3-boot-lkg.md`
> 旧链已删（4 计划任务无、Run 键无）；本文件为新链唯一定义，P3 实现以此为准。

## 1. 新链条

- 用户态采样 / 推理服务（拟名 `LegionSense`，新名，禁复用旧 4 任务名）：
  开机自启，Run 键与计划任务二选一（E1 权限分离：SYSTEM 禁写 HKCU；
  选型待 Step 2-2 实测二选一）。
- 提权落盘入口（拟名 `LegionActuate`，新名新参）：受限触发器，
  沿 ThrottleStop_NoUAC 思想但新实现；仅 L2 事务可调用。
- 互斥锁：`hal-actuation.lock` + PID 存活校验（禁旧锁名；
  禁抢锁失败静默 exit 0）。

## 2. 时序图

```text
t0 登录
 |  ... 服务初始化（只读传感，不落盘）
t1 LegionSense 就绪 ──→ 首个 State48 有效采样
 |  ... 错峰 ≥30s（T1）
t2 首个落盘事务（dry-run/live 按门禁）
 |
 +── boot_phase=1 窗口（t0 起 5min，State s41=1）：禁 burst / UV 加深（T2）
 |
t0+5min ──→ s41=0，正常调度
```

## 3. 可测试条款（given / when / then）

- T1 错峰：given 重启登录，when 服务就绪，then 首次落盘事务时刻 −
  服务就绪时刻 ≥30s（审计 BlackBox 时间戳）。
- T2 开机禁区：given s41 = 1，when 策略请求 burst 或 UV 加深，
  then L3 否决并记 boot 抑制事件（Reward 侧按 burst 违规 / 温度越线口径扣分，
  不新增惩罚项）。
- T3 回退优先：given 开机窗口内发生 AC→DC，when 拔电事件到达，
  then DC 安全包络 <1s 落地，**不受 T1 错峰约束**（供电仲裁高于时序，
  围栏 §0.2）。
- T4 超时有效：given 开机期 L2 事务，when 15s 未返回，
  then 回滚上一快照（与稳态同规则，不放宽）。

## 4. 超时 / 重试 / 回滚分支

- 服务 t0 + 5min 未就绪：本轮采集记缺失（valid = 0），不阻塞登录；
  记 S3 首测数据点。
- 首次事务失败：重试 1 次（D2 口径）；连续失败则停落盘转纯传感 + 告警，
  不硬闯（canary 连续 3 次失败回滚规则的开机期映射）。
- L2 / L3 跳闸：60s 内切 LKG（静态 Quiet 等效），冻结版本（围栏 §5.3）。

## 5. 待 Step 2-2 实测标定

登录→服务就绪耗时、首次有效采样时刻、首个事务落地时刻、错峰 ≥30s 复核、
开机期传感器 stale 率。标定值回填本文件 §2 / §3，不另起文档。
