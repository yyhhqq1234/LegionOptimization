# AGENTS.md — AI Agent Working Agreement（全仓最高优先级指令，本文件为 canonical）

> 任何 AI agent（Claude / Codex / 本地模型 / 子智能体）在本仓动手前必须先读本文件。
> 与其他文档冲突时以本文件为准，但**数值阈值**以 `specs/` + `docs/safety-fence-spec.md` 为准。

## 0. 一句话定位

通用笔记本功耗自适应调优系统：Intel HX 全系 CPU + RTX 40/50 Laptop GPU，
本地自训练小模型实时调优（AI 专业毕设）。旧 Lenovo 静态胶水实现已删除，
冻结于 tag `legion-legacy-b2`（= B2 对比基线，可恢复，不可复活）。

## 1. 必读文档（按顺序）

| 顺序 | 文件 | 内容 |
|------|------|------|
| 1 | 本文件 | 工作协议 |
| 2 | `plans/README.md` + 当前阶段 `plans/PHASE-0x-*.md` | 执行顺序、前置依赖、验收 checklist |
| 3 | `specs/SYSTEM_SPEC_DRAFT_v1.0.md` | HAL 分层 / State48 / Action7 / Reward / 包络 |
| 4 | `docs/safety-fence-spec.md` | 门禁（影子/金丝雀/回滚/SLO），硬约束 |
| 5 | `docs/thesis-proposal-outline.md` | V01–V24 验证矩阵（每项工作必须能映射到某格） |
| 6 | `docs/kickoff-readiness-summary.md` §6 | 已确认决策（删了什么、留了什么、为什么） |

## 2. 铁律（违反任何一条 = 立刻停手并询问）

1. **命名**：`W0–W7` = 负载类型 ≠ `M1–M8` = 系统模块；`G0–G4` = 唯一档位维度，
   DC（电池）是正交维度（**永远不许出现 G5 档**）。
2. **温度禁止硬编码**：一切阈值以运行时 MSR `IA32_TEMPERATURE_TARGET (0x1A2[22:16])` 探测的 TJMax 为基准
   按相对偏移生成。已知：A 机 255HX = 105°C；B 机 14900HX = E2 探测值。
3. **dry-run 默认**：一切落盘路径必须支持 `--dry-run` 且默认为开；`--live` 需要已通过的门禁（E4/E5）
   + 用户显式确认，缺一不可。
4. **无真实写入**：门禁通过前禁止真实写 MSR / powercfg / 任何 INI 落盘（读探针除外）；G4 真实下发永远最后放行。
5. **外部参照只读**：`D:\Intel降压定频 .exe` + `D:\undervolt_config.json` 是手动对比基线，
   禁止修改/删除/调用（用户显式下令除外）；E2 起把它当外部 MSR 写入者纳入互斥设计。
6. **禁区**：`.agent-teams/`（harness 状态，已 gitignore）；`D:\` 其他个人目录一律不碰。
7. **仓库卫生**：不提交 secrets、大二进制、`artifacts/` 实测大文件（只留样例）；换行符走 `.gitattributes`，
   看到 CRLF warning 不许“修复”式全仓改行尾。
8. **诚实日志**：失败必须显式失败（R3 教训：禁止“记 done 实失败”）；验证产物缺失 = 该格“未执行”，不许补签。
9. **Git**：Conventional Commits（feat/fix/refactor/docs/chore/test）；门禁通过打 `tag phase-XX-done`；
   允许 push 到 `origin master`（既定流程）；**禁止 force-push 与改写已公开历史**。
10. **本地私有即 ignore**：在仓内新增任何本地私有内容（实测 CSV/log/照片、个人路径、secrets、临时副本、
    `*.local.*`/`private/` 类文件）后，必须立即确认 `.gitignore` 已覆盖、`git status --porcelain` 无私有文件
    后才能 commit；`artifacts/` 实测大文件与照片类大二进制永不进仓（只留 README/小样例，结论以文字合订）。
11. **双机分工**：A 机 = 主力开发机（基准+训练源+影子/金丝雀主场+唯一落盘口）；B 机 = **副开发机**
    （验证+迁移目标，可分担独立任务）。B 机允许完整 clone + 按 `requirements.txt` 配 Python/torch，
    允许 commit/push（先 `git pull --rebase`，同铁律 9 禁 force-push）；领活见 `docs/machine-registry.md` §7，
    动同一文件先通气。

## 3. 架构速览（HAL L0–L4 + 双侧车，细则见规格）

L0 传感（只读）→ L4 策略（State48→Action7 期望值）→ L3 围栏（硬截断，可审计否决）
→ L2 执行（全局互斥唯一落盘，15s 超时回滚）→ L1 换算（HAL_MAP 版本化）；
侧车 S1 影子/金丝雀，S2 BlackBox（决策/否决/回退全记录，三版本号可重放）。

## 4. 接活流程

1. 在 `plans/` 找到当前阶段，确认前置依赖与验收项。
2. 实现 + 单测；同步更新对应 V 格记录与所需产物。
3. 用阶段验收 checklist 自检，逐项贴证据（log 路径/commit），不许空勾。
4. commit + push；阶段完成打 tag。

## 5. 环境与命令

- Python 3.12，torch 2.11.0+cu128（sm_120），`pytest tests/`，依赖以 `requirements.txt` 为准（P1 落盘）。
- GPU 传感先走 `nvidia-smi` CSV 轮询（pynvml 可选）；MSR 通道需签名驱动（见 P1/P3 结论）。
- Windows 11 + PowerShell；路径用 ASCII，文件名禁空格（旧任务空格截断 bug 的教训）。

## 6. 门禁速查（细则见围栏规格）

影子 ≥8h 有效覆盖 → 金丝雀本机 48h 时间片 A/B → B 机 24h 交叉；
自动回滚：L3 1 次 / L2 24h≥2 / 流畅 burn 超阈 / 连续 3 次下发失败 / 一键否决；
LKG（B2 tag）60s 可回，永久有效。

## 7. Done 定义

代码 + 单测绿 + 文档同步 + 产物归档 + V 格记录 + commit 已推，六者缺一即未完成。
