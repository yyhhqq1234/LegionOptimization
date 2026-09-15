# 阶段性开工计划总览（Refactor Kickoff Plan）

> 全学期约 16 周。P0–P2 为动工门禁（只读/spec/ops，不写业务代码）；
> P3–P6 为构建与模型训练；P7 为放量与论文收官。
> 任一阶段未验收通过，不得进入下一阶段的真实下发步骤（文档/影子步骤不受限）。

| 阶段 | 文件 | 目标一句话 | 时间盒 | 门禁产出 |
|------|------|-----------|--------|---------|
| P0 | `PHASE-00-e0e1-review.md` | E0 口径确认 + E1 交叉评审，规格锁 v1.0 | W1（3–5天） | 解锁 V09+ 排期 |
| P1 | `PHASE-01-e2-probes.md` | E2：B 机冻结 + 只读探针 + 工具链锁文件 | W1–W2 | 解锁 B 列执行 |
| P2 | `PHASE-02-e3-boot-lkg.md` | E3：新开机时序 + LKG 一键回滚演练 | W2–W3 | 解锁 V22–V24 |
| P3 | `PHASE-03-hal-collector.md` | HAL L0–L3 + 采集器 + State48/Action7，实现与 dry-run | W3–W6 | 真实下发能力就绪（仍需门禁） |
| P4 | `PHASE-04-surrogate-bo.md` | A 方案：数据集 + 代理模型 + 约束 BO | W6–W9 | D_safe + 预测器 ONNX v1 |
| P5 | `PHASE-05-transfer.md` | 跨微架构迁移实验证明通用性 | W9–W11 | 迁移效率曲线（论文图） |
| P6 | `PHASE-06-offline-rl.md` | B 方案：离线 RL 对比 + OPE + 影子评估 | W11–W14 | 策略 ONNX + 影子门禁通过 |
| P7 | `PHASE-07-canary-thesis.md` | 金丝雀放量 + SLO + 论文答辩收官 | W14–W16 | 24 格全绿 + 论文初稿 |

上游契约（各阶段通用，不重复写）：
- 规格 `specs/SYSTEM_SPEC_DRAFT_v0.1.md` v0.1.1（W0–W7 / DC 正交 / G4 95℃ / TJMax 运行时探测）
- 围栏 `docs/safety-fence-spec.md` v0.1（影子≥8h / 金丝雀48h / 自动回滚）
- 验证矩阵 `docs/thesis-proposal-outline.md` §3（V01–V24）+ §3.1 正交视图
- 基线：B0 原厂 / B1 LLT 官方 / B2 `legion-legacy-b2` tag；外部参照：`D:\Intel降压定频 .exe`（只读参照，不联动）
