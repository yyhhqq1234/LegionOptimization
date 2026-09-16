# 机器注册表（Machine Registry）

> 性质：名册 + 规则，不含实测数据。实测档案各自落盘：
> A 机见 `docs/a-machine-profile.md`，B 机待 P1 落盘 `docs/env-inventory.md`。
> 本表只定槽位与加入规则，C / D 机出现时填表即用，不返工改架构。

## 0. 为什么现在做

V 矩阵、产物命名、抽样比里已有“A / B 列”概念（`wmi_trace_{A,B}.csv`、
P1-3 B 列排期）。若将来加机器时再定规则，命名与矩阵必然分叉。
本次只预留位置：代码与配置经核查**零机器硬编码**（`src/`、`configs/`、
`pytest.ini`、`requirements.txt` 无 A/B 引用），所以预留只落在文档与命名层，
不加代码抽象（YAGNI）。

## 1. 在册机器

| 槽位 | 身份 | 状态 | 档案 |
|------|------|------|------|
| A | 基准机 + 主力开发机（255HX + 5060） | active | `docs/a-machine-profile.md` |
| B | 副开发机 + 验证机 + 迁移目标（14900HX + 5060） | active | 上线清单见 `docs/b-machine-env-requirements.md`；档案进 `env-inventory.md`（P1 合订，待补不阻塞副开发任务） |
| C | 未定 | **reserved** | 见 §4（出现时填） |
| D | 未定 | **reserved** | 见 §4（出现时填） |

状态枚举：`reserved`（预留空槽）→ `bringup`（按 §4 上线中）→
`active`（在册承担角色）→ `retired`（退役，只留历史产物，不删记录）。

## 2. 槽位 schema（新机填表项，缺一即未建档）

CPU 型号 / 步进、BIOS 版本、GPU 型号 / 驱动版本、EC 与散热规格、
适配器功率、TJMax 实测值（MSR `0x1A2`）、UV 锁状态、WMI mode 值、
`power.limit` 可用性、承担角色（§3）、上线日期。

## 3. 命名与消歧（铁律级）

1. 产物后缀中的机器字母一律大写单字母：`{A,B,C,D}`，
   如 `wmi_trace_C.csv`、`gpu_baseline_D.csv`；路径 ASCII、无空格。
2. **`B0 / B1 / B2` 是基线（原厂 / LLT / legacy tag），永远不是机器**；
   与机器字母正交，禁止把“B2 机器”之类的写法引入任何文档与代码。
3. 档位 `G0–G4` + DC 正交口径不变（禁 G5）；负载 `W0–W7` ≠ 模块 `M1–M8`。

## 4. 新机 onboarding（C / D 出现时执行）

1. 本表状态改为 `bringup`，填 §2  schema（未知项如实写“未知 + 顺延”，不编）。
2. 复用 B 机上线流程（建档 → WMI 抓包 → MSR 只读 → GPU 基线），
   产物按 §3.1 命名回传，合订进 `docs/env-inventory.md`（届时扩为多机档案）。
3. V 矩阵加一列：P1-3 抽样比规则复用（M1 / M3 / M5 / M7 必复、其余 ≥50%）；
   P5 迁移矩阵加一行（源 → 新机，200 条达 90% 口径不变，UV 锁则子空间）。
4. 围栏机型覆盖（fence §1.2）若需加表，走影子 / 金丝雀变更流程。
5. 状态转 `active`，关闭 bringup。

## 5. 引入触发条件（现在都不满足，只列条件）

- 需要第二个迁移目标证明通用性（论文加分项）；
- 拿到新架构硬件（如不同代 / 不同厂商 CPU、不同代 GPU）；
- 导师或评审明确要求多机证据。
  条件未触发前不主动找机器；槽位空着就是正常的。

## 6. 现在不做的事

- 不建 `configs/machines/` 机型覆盖文件（无第二实测机型，建了也是编数字）。
- 不给 `src/` 加 machine_id 抽象（无硬编码需要治理）。
- 不给 C / D 编任何“预设画像”（架构、型号一律未知，不前置假设）。

## 7. 双机开发分工（A 主力 / B 副开发，2026-09-16 生效）

- A 机：主力开发机。唯一落盘口（合订 `env-inventory.md` + 打 tag + 最终 push 确认）；
  主场：P2 E3 时序 + LKG、P3 HAL 核心（L2 互斥 / L3 围栏）、P4 训练源域 + BO、
  P6 RL 主场、P7 48h 金丝雀主场。
- B 机：副开发机（兼验证 + 迁移目标）。允许完整 `git clone` + 按 `requirements.txt`
  配 Python/torch（见 `docs/b-machine-env-requirements.md` §0）；
  适合：P1 E2 B 侧探针执行、P3 非核心模块（M1 GPU 传感复核 / M7 文档 / 单测分担）、
  P4 `D_safe_B` 采集、P5 迁移实验执行侧、P7 24h 交叉、复现验证与文档。
  不适合：LKG / tag 独占操作、G4 真实下发首发（永远 A 机先行，B 机只做交叉复测）。
- 协同：各自领独立任务；动同一文件先通气；每次 push 前 `git pull --rebase`，
  禁 force-push（AGENTS.md 铁律 9）；私有产物（实测 CSV/log/照片/secrets）走
  `artifacts/` + `.gitignore`，永不进仓（AGENTS.md 铁律 10，CLAUDE.md §7）。
