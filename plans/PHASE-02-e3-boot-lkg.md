# PHASE-02：E3 开机时序标定 + LKG 一键回滚演练（W2–W3）

## 1. 阶段目标

定义**新**开机链时序要求并实测标定（旧链已删：4 任务无、Run 键无），
完成 LKG（`legion-legacy-b2` tag）一键回滚演练首测（A2 SLO <60s），关闭 R3。解锁 V22–V24。

## 2. 前置依赖

- PHASE-00 完成；PHASE-01 进行中（B 机结论不阻塞本阶段 A 机部分）
- 管理员终端可用（演练需读任务计划与电源配置）

## 3. 详细步骤

### Step 2-1：新开机链时序设计（文档，0.5 天）
1. 明确新链条：用户态采样/推理服务（Run 键或计划任务二选一，E1 权限分离原则：SYSTEM 禁写 HKCU）+
   提权落盘入口（受限触发器，沿用 ThrottleStop_NoUAC 思想但新名新参）。
2. 规定错峰：采样服务就绪与首次落盘事务间隔 ≥30s（旧 R3 教训制度化），开机 5min 内（`boot_phase=1`）
   禁止 burst 与 UV 加深（对应 State s41）。
3. 输出：时序图 + 超时/重试/回滚分支，写入 HAL 设计附录。

### Step 2-2：开机实测标定（ops，1 天）
1. 重启 2 次，记录：登录→服务就绪耗时、首次 State48 有效采样时刻、首个 dry-run 事务落地时刻。
2. 验证错峰 ≥30s；记录开机期传感器 stale 率（S3 SLO 首测数据点）。

### Step 2-3：LKG 一键回滚演练（ops，1 天）
1. 从 tag 恢复 B2 到**临时 staging 目录**（不污染仓库工作树，如 `$env:TEMP\lkg-drill\`）：
   `git worktree add` 或 `git archive legion-legacy-b2 | tar -x -C <staging>`。
2. 执行 LKG 落地：staging 内 `quiet.bat` 等效动作（ThrottleStop 缺失时允许 powercfg-only 降级并备注，
   演练的是流程与计时，不是调优效果）。
3. 计时：从“发起回滚”到“powercfg 落地 + 确认读回”必须 <60s（A2 SLO），连续 2 次达标。
4. 演练后删除 staging 目录并复核仓库 `git status` 干净。

### Step 2-4：A2 首测记录
回滚耗时、成功率（要求 100%）、现场 log 保留路径记入演练报告。

## 4. 阶段验收方法

- [ ] 新开机时序文档存在且错峰条款可测试（given/when/then 写清）
- [ ] 2 次重启实测：错峰≥30s，boot_phase 内无 burst/UV（审计 log）
- [ ] LKG 演练 2/2 成功且单次 <60s，staging 已清理，仓库干净
- [ ] R3 关闭；V22–V24 解锁
- [ ] 验收：演练报告（含计时表）+ 时序图 commit

## 5. 产物清单

开机时序设计（HAL 附录）/ 重启实测记录表 / LKG 演练报告 / A2 首测数据点

## 6. 风险与回退

- ThrottleStop 已删导致 LKG 等效不完整：允许 powercfg-only 降级演练，差项记入报告，不判失败。
- 本阶段无策略下发，无调优风险。
