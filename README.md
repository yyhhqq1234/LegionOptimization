# LegionOptimization（重构中）

通用笔记本功耗自适应调优系统：**Intel HX 全系 CPU + RTX 40/50 Laptop GPU**，
本地自训练小模型实时调优。AI 专业毕设项目。

> 旧 Lenovo 静态胶水实现已整体移除，冻结于 tag
> [`legion-legacy-b2`](https://github.com/yyhhqq1234/LegionOptimization/tree/legion-legacy-b2)
>（= B2 对比基线）。当前仓库处于重构准备期：规格与计划先行，`src/` 实现随阶段落地。

## 当前状态

- [x] 前期准备：系统规格 / 安全围栏 / 开题大纲 / 验证矩阵 / 阶段计划
- [ ] P0 E0+E1 评审 → 见 `plans/PHASE-00-e0e1-review.md`
- [ ] 按 `plans/README.md` 阶段表推进（P0–P7，约 16 周）

## 仓库结构

```
AGENTS.md / CLAUDE.md   AI agent 工作协议（动手前必读）
specs/                  系统规格（HAL / State48 / Action7 / Reward / 包络）
docs/                   开题大纲 / 安全围栏 / 准备汇总（含已确认决策 §6）
plans/                  P0–P7 阶段计划（每阶段独立 .md：目标/步骤/验收）
src/                    实现（P3 起落地：sense/state/actuate/guard/policy/blackbox）
configs/                包络与阈值版本化 YAML（P3 起）
tests/                  单测 + 回放测试（P3 起）
```

## 关键设计（速览，细则见 `specs/`）

- HAL 五层 + 双侧车：传感只读 → 策略建议 → 围栏硬截断 → 互斥执行 → 参数换算
- State48 状态向量 / Action7 连续动作 / 多目标 Reward（含流畅惩罚项）
- G0–G4 五档包络 + DC 正交维度；TJMax 运行时探测，禁止硬编码
- 安全门禁：影子 ≥8h → 金丝雀 48h → 放量；LKG 60s 可回

## AI 协作

本仓主要由 AI agent 协作开发。人类或 agent 接活前先读 `AGENTS.md`，
按 `plans/` 当前阶段的验收 checklist 交付（代码+单测+文档+产物+V 格记录+commit 六件套）。

## License

MIT（见 `LICENSE`）
