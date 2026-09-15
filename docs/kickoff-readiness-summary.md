# 开工准备汇总（t5 / p-synth）— Kickoff Readiness

> 输入：t1 `specs/SYSTEM_SPEC_DRAFT_v0.1.md`、t2 `docs/thesis-proposal-outline.md`、
> t3 环境盘点（dependency 结果）、t4 `docs/safety-fence-spec.md`。只汇总、不写代码。
> 结论先行：**4 项交付齐备，规格侧可进交叉评审；动工（真实下发/烤机）被 3 个 P0 确认项门禁，
> 其中 2 个是命名/口径冲突，必须先消歧，否则验证矩阵无法排期。**

---

## 1. 已锁定（Locked）

### L-SPEC（t1 系统规格 v0.1）
- [x] HAL 5层+2侧车：L0传感 / L1换算（HAL_MAP v0.1）/ L2唯一执行（全局互斥+15s回滚）/ L3围栏 / L4策略；侧车 S1影子·金丝雀 / S2 BlackBox。
- [x] 设计锁定 L1–L5：档位=包络上限；Action连续化；State48统一入口；安全硬截断；Extreme双触发收敛为单一仲裁。
- [x] State48（8组×6维=48，1Hz）：含 s46 `ts_inject_ok`（根治 R3 静默 FIVR 失败）+ valid mask（s44/45/47）。
- [x] Action7：a0频墙 / a1 turbo-EPP / a2 PL1 / a3 PL2-burst / a4 UV（0–-80mV，5mV步进）/ a5电源计划 / a6档位建议；拔电钳位（a2≤25W，a0≤3800MHz，a3=a2）。
- [x] Reward 主公式 + 8负载子模权重表 + 回合计分 `Return = mean−0.5std−2shield−1clamp`（相对静态基线 +10% 且 shield 不上升）。
- [x] 5档包络 G0–G4（继承现网 3.8/4.8/5.0/5.2GHz 与 −50/−65/−55/−45mV，新增 G0 2.8G/15W/75℃）+ F1–F5 地板 + Burst token 桶初值。
- [x] 现网基线冻结：Y7000 2025 IAX10 / U7 255HX / RTX5060；FIVR 五步；Boot 双轨；权限分离（SYSTEM 禁写 HKCU，修 P1）。

### L-THESIS（t2 开题大纲与验证矩阵）
- [x] 开题 7 章大纲 + 方法 5 件套 K1–K5（第4章节结构 + 表 4-1–4-11 脚手架）。
- [x] 24 格主矩阵 V01–V24（8模块×3基线，每格双机复测）+ 正交视图（2机×4模式×3基线）+ 指标字典（只定名不定值）。
- [x] 三基线冻结：B0 Stock / B1 LLT官方 / B2 本仓HEAD；Machine A 确认（Y7000 本机）。

### L-ENV（t3 环境盘点，只读）
- [x] CPU U7 255HX 20C/20T，Win11 22631 x64，32GB；GPU RTX 5060 Laptop（驱 616.92，nvidia-smi 可用，待机 54℃/19W）。
- [x] PyTorch 2.11.0+cu128 可用（sm_120，cudnn 91900）；psutil 7.2.2；powercfg 可用（当前 HighPerf）。
- [x] 日志与缺失清单：switch/watcher/update 日志存在（含 TS FAILED 实证）；缺失 baseline.json / metrics.json / power_log.csv / gpu_log.csv / requirements.txt / benchmark.py / export_onnx.py。

### L-SAFE（t4 安全围栏 v0.1）
- [x] 防御纵深 L0–L4 + 仲裁优先级（温度 > 供电 > 电气上限 > 流畅 > Burst）+ 通用执行语义（≥2Hz / N=3去抖 / 迟滞 / 单步限幅 / 故障保守 / 三版本 pinning）。
- [x] 温度 shield 四级（WARN90 / L1 95 / L2 98 / L3 100，DC−2℃，重武装 80/70℃+30/60s）。
- [x] 流畅 shield（p95×1.15 / 1%Low×0.8 / jank≥12 / DWM>5%，hold 10s，温度优先压制）。
- [x] Burst 分档令牌桶表（Quiet 0.15kJ … Balance 0.70kJ …）+ DC 默认禁用 + 越界语义。
- [x] 拔电回退（<1s 落地 DC-1/2/3 三档 35/25/15W + 逐档回插 + 抖动锁定）+ 影子≥8h→金丝雀48h时间片A/B→自动回滚 + SLO（S/D/F/A + burn 双轨）。

---

## 2. 待确认（Open items — 阻塞关系明确）

| # | 事项 | 来源 | 阻塞 | 建议解法（t5 意见） |
|---|------|------|------|---------------------|
| **P0-1** | **“8子模”命名冲突**：t1 m0–m7 = 负载类型（待机/办公/…/压测）；t2 M1–M8 = 系统模块（HAL/State/…/流水线）。“双机×8子模×基线”无法执行 | t1 §6.2 vs t2 §0.3 | V01–V24 行定义；§3/§3.1 排期 | **改名消歧**：负载侧改称 **W0–W7**（workload），系统模块保留 M1–M8；验证矩阵主表行 = M（模块），W 作为每个 V 格内的负载覆盖维度（t2 §3.1 正交视图扩展一列 W）。t1/t2 各改一处表头即可，不动实质内容 |
| **P0-2** | **“5档”口径冲突**：t1 G0–G4（DeepQuiet…Extreme）；t2 G1–G4 + G5 DC态（DC 作第 5 档） | t1 §6.1 vs t2 §0.2 | 包络表行数；DC 复测排期（C5） | **DC 为正交维度**：采用 t1 G0–G4（t2 §0.2 已声明以 t1 为准）；t2 G5 改为“DC 正交复测行”（AC 四档 × DC），判据用 t4 §4.3 DC-1/2/3 表。C5 关闭：DC 复测与 AC 同优先级（安全攸关，不得降级） |
| **P0-3** | **温度口径碰撞**：t1 G4 天花板 98℃ = t4 L2 跳闸 98℃，包络上限触跳闸线，无运行余量 | t1 §6.1 vs t4 §1.2 | G4 放量；S1/S2 SLO | 三选一（t5 推荐 a）：a) G4 天花板→95℃（=L1 线，留 3K 余量）；b) 声明 98℃仅允许 burst 瞬态且 L2 去抖 N=3 覆盖；c) t4 为 G4 单开例外。影子期实测后终定 |
| P1-1 | Burst 桶数值：t1 通用 C=120W·s vs t4 分档表（0.15–0.70kJ） | t1 §6.4 vs t4 §3.2 | V16–V18 参数 | **以 t4 分档表为准，t1 通用值作废**（t1 发 v0.2 时删除通用值，引用 t4 表） |
| P1-2 | Reward burst 违规惩罚项：t4 §7 强制三项（温度/burst/流畅），t1 主公式有温度+流畅+shield 附加罚，burst 违规无显式项 | t4 §7 vs t1 §5.1 | K3 章；V10–V12 重放 | t1 发 v0.2 时增补 `−w_burst·B_viol` 项（B_viol = 超 Tmax/空桶请求计数），权重初值 0.5（与 shield 附加罚同量级），影子期调参 |
| P1-3 | Machine B 型号未定 + B 机抽样比（t2 C3/C4） | t2 §5.1 | 全部 V 格 B 列排期 | B 机先冻结候选（同 Legion 异构机），抽样比按 t2 建议（M1/M3/M5/M7 必复、其余≥50%）执行，t5 在此拍板，不再阻塞 |
| P1-4 | GPU 独立 burst 桶是否立项；DC-1 35W 是否按适配器功率分表（t4 §7.3 待确认） | t4 §7 | M6 范围 | 本期均**不做**（CPU 域单桶 + DC 单表），记入 backlog，V16–V18 不覆盖 |
| P1-5 | 工具链缺口：无 pynvml、无 onnx 包/CLI、无 CUDA EP（ort 仅 CPU）、无 nvcc | t3 | M1 GPU 传感实现；M8 ONNX 导出 | M1 GPU 传感先走 **nvidia-smi CSV 轮询**（1Hz 足够），pynvml 列为可选优化；ONNX CUDA EP 缺失只影响 M8 导出验证（V22–V24 先记缺失声明，不阻塞影子）；requirements.txt 缺失 → 动工第一步补锁文件 |
| P1-6 | VRM/主板温度与风扇转速源未定（t1 s23 代理 + t4 §1.1 仅观测） | t1 §3 vs t4 §1.1 | S3 SLO 口径 | 按 t4 降级语义执行（缺失不降级判据）；s23 用功耗代理 + valid=0，t3 复核时若 EC 可读再升级 |

**t2 C1–C5 关闭状态**：C1（字段/权重/包络数值）— t1/t4 已交付，转入 P0-1–P0-3/P1-1/P1-2 交叉评审后关闭；C2（SLO/Shield/门禁）— t4 已交付，关闭；C3 → P1-3；C4 → 已拍板（P1-3）；C5 → 已拍板（P0-2）。

---

## 3. 风险（Top 5，承接只读分析 + 新识别）

| # | 风险 | 影响 | 回退/缓解 | 等级 |
|---|------|------|-----------|------|
| R1 | Extreme 双触发并发（LLT Extreme pipeline + Watcher mode=224 同跑 custom.bat，无锁） | 切 Extreme 时 copy/kill TS 竞态，FIVR 失败 | t1 L5 单一仲裁 + L2 互斥为动工前置条件；在仲裁落地前**禁测 G4 真实下发**（V09/V15/V21 的 G4 格只许 dry-run/影子） | 🔴 高（现网实证，非理论） |
| R2 | 静默 FIVR 失败（任务 Disabled 下 TS 拉不起，日志仍记 done；8/22、9/04 实证） | 动作“生效”实未生效，验证数据作废 | s46 + F5 诚实地板为门禁：任何 V09/V15/V21 真实下发格必须先过 `ts_inject_ok` 自检 | 🔴 高 |
| R3 | 开机竞态（startup.ps1 vs LLT RunOnStartup 并发抢 TS/INI） | 开机后首个包络不可信 | 动工入口 E3 先做开机时序标定（30s 错峰验证），未达标前 V22–V24 不判通过 | 🟡 中 |
| R4 | B 机 WMI 事件行为差异（mode≠224）/ TS FIVR 不兼容 | B 列复测翻车 | B 机先跑事件抓包 + FIVR 兼容性探针（动工入口 E2），不兼容则 B 机降级 powercfg-only 对照并备注（t2 §5.2 已预置） | 🟡 中 |
| R5 | 口径冲突未消歧就开跑（P0-1/P0-2）导致 24 格数据无法归位 | 返工整轮矩阵 | **门禁**：P0-1/P0-2 关闭前，V 格只许跑 V01–V08（传感/状态/动作为主，不依赖档/模口径），V09 起冻结 | 🟡 中（流程性，可控） |

---

## 4. 下一步动工入口（按顺序，每步有 done 定义）

| 入口 | 动作（不写代码，仅规格/只读 ops） | Done 定义 | 对应 V 格解锁 |
|------|----------------------------------|-----------|---------------|
| **E0 口径消歧会**（0.5 天，文档） | 关闭 P0-1（W/M 改名）、P0-2（DC 正交化）、P1-1（t4 表为准）；开 t1 v0.2 / t2 v0.2 修订单 | 三处表头修订合入，t2 C1 关闭 | 解锁 V09+ 排期资格 |
| **E1 交叉评审**（1 天，文档） | t1↔t4 对敲：P0-3 温度余量三选一、P1-2 burst 惩罚项、State 必备字段存在性（t4 §7 清单逐项打勾：温度×4/AC/电量/前台类别/帧统计/桶余量/档位/风扇） | 评审表全勾或显式降级声明；SLO 阈值冻结为 v1.0 | 冻结全部判据，可开影子 |
| **E2 B 机与探针**（只读 ops） | B 机型号冻结；B 机 WMI 抓包；B 机 FIVR 兼容探针；本机 nvidia-smi 轮询基线 + requirements.txt 锁文件 | P1-3/P1-5 关闭；B 列排期表填满 | 解锁 B 列执行 |
| **E3 开机时序标定**（只读 ops） | LegionProfile +30s vs LLT RunOnStartup 错峰验证；回滚演练（LKG .bat 一键回退计时） | R3 关闭；A2 回滚 SLO 首测达标（<60s） | 解锁 V22–V24 |
| **E4 Shadow 开跑**（影子，不下发） | V01–V08 + V10–V12/V16–V17/V19–V20 影子格；BlackBox 日志完整率统计 | 影子门禁（t4 §5.2）通过 + 人工确认 | 解锁 Canary（金丝雀 48h） |
| E5 Canary → Rollout | 按 t4 §5.3/§5.4；G4 真实下发最后放行（R1 仲裁落地后） | Canary 门禁通过；SLO 周报 | 全量 |

**立即可以做的（无门禁）**：E2 中的只读探针与锁文件、V01–V08 影子准备、E0/E1 文档修订。**禁止做的**：任何真实下发（ especially G4 / burst / UV 加深）必须等 E0+E1 关闭。

---

## 5. 交付物索引

| 交付物 | 路径/位置 | 版本 |
|--------|-----------|------|
| 系统规格草案 | `specs/SYSTEM_SPEC_DRAFT_v0.1.md` | v0.1（待 v0.2 修 P0-3/P1-1/P1-2） |
| 开题大纲与验证矩阵 | `docs/thesis-proposal-outline.md` | v0.1（待 v0.2 修 P0-1/P0-2） |
| 环境盘点 | t3 dependency 结果（建议落盘 `docs/env-inventory.md`，动工时补） | — |
| 安全围栏规格 | `docs/safety-fence-spec.md` | v0.1（阈值初始值，影子校准） |
| 本汇总 | `docs/kickoff-readiness-summary.md` | v1.0 |

*— spec-architect，t5 交付；只汇总未写代码 —*

---

## 6. 清理与决策追记（2026-09-15，用户逐项确认）

- Legacy 实现清零并提交 `6111aef`，B2 基线冻结于 tag `legion-legacy-b2`（已推远端）；P0-1/P0-2/P0-3 关闭，规格升 v0.1.1。
- 4 个 Disabled 尸体任务已删（LegionProfile / LegionUpdate / LegionGpuSwitch / ThrottleStop_NoUAC）。
- `watcher.lock` 因 Session-0 未知进程持有暂留（gitignored），重启后删；新实现禁用旧锁名（见规格§8）。
- **外部参照工具保留**：`D:\Intel降压定频 .exe`（第三方「通用 Intel CPU 控制中心」v2.7.0.0）+ `D:\undervolt_config.json`
  （-50mV / PL1 120W / PL2 168W / P4.8G / E4.3G）**留作手动对比基线**；其开机任务损坏（路径空格截断，0x80070002）实际未运行。
  E2 须将其登记为外部 MSR 写入者并纳入互斥设计；其 -50mV 可与 G1 Quiet 互为参照。
