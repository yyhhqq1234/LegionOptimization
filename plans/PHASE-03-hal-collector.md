# PHASE-03：HAL + 采集器 + State48/Action7 实现与 dry-run（W3–W6）

## 1. 阶段目标

实现 HAL L0–L3（含 L2 全局互斥 + dry-run 模式）、1Hz 遥测采集器、State48 构建器（含 valid mask）、
Action7 + HAL_MAP 换算、BlackBox 结构化日志。通过 V01–V09 的 stub/dry-run（**零真实 MSR/powercfg 写入**，
读探针除外）与围栏单元测试门禁。

## 2. 前置依赖

- PHASE-00（v1.0 冻结字段表）、PHASE-01（传感可用性结论）、PHASE-02（时序约束）
- Python 3.12 + `requirements.txt`；MSR 写通道缺失不阻塞（本阶段只要求读探针 + dry-run）

## 3. 详细步骤

### Step 3-1：仓库脚手架（2 天）
```
src/
  sense/      # L0：WMI 事件、nvidia-smi 轮询、OS 计数器、前台/帧率探针
  state/      # State48 构建 + 归一化 + valid mask（s44/45/47）
  actuate/    # L1 换算（HAL_MAP v1.0）+ L2 互斥事务 + dry-run 开关 + 回滚快照
  guard/      # L3：温度/流畅/Burst/拔电四 shield（围栏 v1.0 阈值表版本化）
  policy/     # L4 占位（本阶段只接静态包络 + 随机/网格 stub，供采集用）
  blackbox/   # 环形缓冲 + 评估 log 持久化 + 三版本号 pinning
tests/        # 围栏单元测试 + 回放测试
artifacts/    # 探针 CSV / dry-run log（gitignored 大文件仅留样例）
```
`artifacts/` 大文件 ignore，`configs/` 放包络/阈值版本化 YAML（与代码分离）。

### Step 3-2：L0 传感与 State48（1 周）
1. nvidia-smi CSV 1Hz（EGM：util/freq/power/temp/功耗墙）；OS 计数器（CPU util/分核、C0、IO、内存）；
   WMI 事件只写 `gear_desired`（L5 单一仲裁原则）。
2. State48 1Hz 构建：缺失打 `valid=0` 禁止填旧值；`s46 ts_inject_ok` 初版恒 0（F5 诚实地板即行）；
   `s33 burst_tokens` 接 token 桶记账（只记账不触发，对应 V16–V17 影子语义）。
3. 帧率探针：PresentMon/DXGI（拿不到则游戏类 W4/W5 标记降级，流畅 shield 按“静默”语义）。

### Step 3-3：L1/L2 actuation + dry-run（1 周）
1. HAL_MAP v1.0：频墙→powercfg+SST/NonTurbo 对齐表、UV mV→FIVR 编码（`×1.024→hex`）、PL→EAX/EDX 单调映射。
2. L2 全局互斥：单事务串行、15s 超时回滚上一快照、所有返回值必校验（根治 P3 虚假成功）。
3. **dry-run 总开关**：`--dry-run` 下 L2 只走校验与 log，零落盘；默认开启，真实下发需显式 `--live` + 二次确认。
4. 单例：新锁名 `hal-actuation.lock` + PID 存活校验（规格§8 教训），禁止静默 exit 0。

### Step 3-4：L3 围栏移植 + 门禁测试（1 周）
1. 四 shield 按围栏 v1.0 实现，阈值表独立版本化；裁决 p99 <50ms（S4/D1 预算）。
2. 门禁：围栏单元测试全绿 + 回放测试（B0–B2 历史 log + P1 探针 log）零 L2+ 误放行。
3. V01–V09 stub/dry-run 全跑通：V01–V03 传感自检、V04–V06 离线编码统计、V07–V09 dry-run 下发与互斥（含 Extreme 双触发收敛验证：WMI 只写期望档位，执行权唯一）。

## 4. 阶段验收方法

- [ ] `pytest tests/` 全绿；回放测试 L2+ 误放行 = 0（报告存档）
- [ ] V01–V09 dry-run 产物齐（selfcheck/state48_report/action_dryrun log），成功率 100%，**零真实写 MSR/powercfg**（审计：BlackBox 无 live 事务）
- [ ] BlackBox 日志完整率 100%，三版本号可重放一条抽样裁决
- [ ] 围栏裁决 p99 <50ms（24h 或等效压测采样）
- [ ] 验收：打 `tag phase-03-done`；真实下发能力“就绪但锁定”（等 E4/E5 门禁）

## 5. 产物清单

`src/` 实现 + `configs/*.yaml`（包络/阈值 v1.0）+ `tests/` + V01–V09 产物 + 门禁报告

## 6. 风险与回退

- MSR 驱动/签名拿不下：L1 标记 UV 通道降级，P4 先用 PL/频墙/EPP 动作子集训练，UV 后补（Reward/Action mask 已预留）。
- 帧率探针拿不到：W4/W5 流畅 shield 降级为静默，F2 地板改功耗代理并显式声明。
- 全程 dry-run，无调优风险；回滚 = 删代码重来，数据无损。
