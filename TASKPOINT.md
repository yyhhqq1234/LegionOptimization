# TASKPOINT — 项目级任务断点

> 保存时间：2026-10-14 14:45（UTC+8）
> 项目根目录：D:\LegionOptimization
> 分支/版本：master @ 0a1e24d（+ 本次断点提交；tags：legion-legacy-b2、phase-00-done、phase-03-done）

## 1. 任务目标

- 一句话目标：推翻旧 Lenovo 静态调优胶水项目，重构为**通用笔记本功耗自适应调优系统**（Intel HX 全系 + RTX 40/50 Laptop，本地自训练小模型实时调优），作为人工智能专业毕设，约 16 周交付。
- 当前子目标（P4 A方案落地）：D_safe≥2000/机九宫格≥80% + 三模型对比 + 回放Return+10% shield不升 + ONNXv1<10MB<5ms + tag phase-04-done。
- 验收标准：
  - [x] P0 锁 v1.0 / [x] P1 E2 探针 / [x] P2 E3 时序+LKG / [x] P3 HAL+dry-run 45单测+tag phase-03-done
  - [x] P4 perf 标链路（PresentMon + 回填，r27/r37 加固）
  - [x] P4 E4 影子链路（shadow_run + e4_shadow_report 四判据，r28）
  - [x] P4 档位真读 + 四档映射齐全（r29/r30）；标签审计（r30）；一键同窗（r31）
  - [x] **E4 覆盖面四项全绿**：idle 9.89h✅ / 办公 2.11h✅ / 游戏 3.54h✅ / 插拔 1 次✅
  - [ ] 采集达标：`interactive_ratio` **0.136 < 0.15**（需补 ~16 分钟交互类）
  - [ ] P4 回放验收：相对 B2 基线 Return +10% 且 shield 不上升（真值待多格+perf标+E4/E5 live）
  - [ ] P4 九宫格≥80%（当前 **4/16**：W0/AC、W0/DC、W1/AC、W2/AC）
  - [ ] E4 判据：c2 ✅PASS / c4 ✅PASS / c1 BLOCKED（缺第二策略，P6）/ c3 BLOCKED（dry-run 无作动，E5）
  - [ ] 跨机迁移（P5）；影子五门禁 + 48h 金丝雀（P6/P7）；论文初稿 + 答辩演示

## 2. 背景与现状

- 旧项目已整体删除，冻结于 tag `legion-legacy-b2`（可 `git show` 恢复，不可复活进工作树）。
- 双机：A 机 Y7000 2025（U7 255HX，TJMax=105°C / RTX 5060 Laptop，驱动 617.14 / torch 2.11+cu128 sm_120）；B 机待上线（i9 14900HX + 5060）。
- 路线：A 方案（监督代理 + 约束 BO）→ B 方案（离线 RL，主 IQL）；M5 负载预测叠加。
- 当前状态（r37，2026-10-14 实测）：
  - **数据量**：`rows 55939`，覆盖 **4/16**（coverage 0.25），interactive **0.136**。
    分格：W0/AC 35172、W0/DC 438、W1/AC 7589、W2/AC 12740。
  - **真档位标签**：`gear` 列自 part5 起为真读值（`Quiet` 104 / `Balance` 1125 / `mode:2` 124 / `Beast` 5833）；
    part1–4 的 48753 行是常量 `Balance-readonly`（**不构成档位观测**，r30 审计，不回填）。
  - **Windows 电源方案 = 独立混淆变量**（r36）：12:30:40 由「节能」切到「高性能」被影子逐 tick 捕获
    （节能 454 / 高性能 5265 ticks）；CSV 自 r36 起含 `scheme` 列 + schema 错位守卫；part1–8 无该列（如实声明）。
  - **E4 影子实测**（W2 游戏窗口 5719 ticks，Beast + 高性能，FF7 Rebirth）：
    BlackBox **5719/5719**、errors 0；围栏 **OK 877 / WARN 2210 / L1 2632 / L2 0**；
    温度 57–86°C、功耗 4.74–127.62W、util 中位 99%；**帧标 p95 中位 6.28ms ≈ 159fps**；
    c1b 0.0（影子恒建议 Balance vs 人工 Beast）；c2 PASS；c4 PASS；c1/c3 BLOCKED（口径已归位）。
  - **立案（P6 处理）**：Beast 档高压游戏下 L1 触发率 **46%**（`TEMP_L1_GPU=85°C`，实测长期 84–86°C）
    → 待判「阈值过紧 vs 真实过热」；改阈值属 L 级提案，P4 内不动。
  - **本轮修掉的口径/证据问题（防假达标）**：r27 rollup 双计、r33 c3 口径、r34 插拔 vs 电量漂移、
    r36 Windows 方案缺列、r37 帧标零匹配 + 覆盖时长双计（详见 `docs/p4-gate-report.md` §8–§14）。
  - 已知局限（逐行标注）：`GetCPUTemp/GetGPUTemp` 返回 0 → 围栏输入 `cpu_temp_src="proxy-gpu"`；
    `policy_ver=stub-1`；State48 fill_rate 0.125；live 因 E4/E5 门禁缺失继续锁定。
- 约束：全程 dry-run 默认；门禁不过不真实下发；公开仓库，禁 force-push。

## 3. 总体计划

1. P0–P3 已封版 → P4（进行中）→ P5 迁移 → P6 离线 RL + 影子五门禁 → P7 金丝雀 + 论文答辩
2. 每阶段 Done 六件套：代码 + 单测绿 + 文档同步 + 产物归档 + V 格记录 + commit 已推

## 4. 团队模式

- 当前：**单 Agent 执行**。历史团队（`legion-readonly-analysis` / `legion-rebuild-prep`）均已完成并归档删除。
- 后续如需并行（如 P6 多算法训练），新建团队，任务 id 重新编号。

## 5. 步骤规划

| # | 步骤 | 负责人 | 状态 | 备注 |
|---|------|--------|------|------|
| 1–10 | 只读分析 → 开工准备 → P0–P3 → P4 合成链/B2锚/干等价 | 单 Agent(+团队/用户) | 已完成 | 详见历史条目与 commits |
| 11 | P4 影子实采 part1–8 | 单 Agent + 用户用机 | 进行中（4/16 格，55939 行） | part5 起带真档位；part8=R36/R37 游戏窗口 |
| 12 | P4 口径修正 + perf 标链路（r27） | 单 Agent | 已完成 | commit 7bdf99f/a02249d/7bdfeb2 |
| 13 | P4 E4 影子链路（r28） | 单 Agent | 已完成 | commit 055392a/7a41996 |
| 14 | P4 档位真读（r29） | 单 Agent | 已完成 | commit 681be77/36ac69f |
| 15 | P4 四档映射 + 标签审计（r30） | 单 Agent + 用户按 Fn+Q | 已完成 | commits 4bebee2/154a5d1/508a17e/4f794a3 |
| 16 | P4 一键同窗 + c3 口径 + 插拔判据（r31/r33/r34） | 单 Agent | 已完成 | 0237359/42022e7/d375da2/90c0e71 |
| 17 | P4 DC 段 + 插拔事件达标（r35） | 单 Agent + 用户拔插 | 已完成 | dfae908/b3538f8 |
| 18 | P4 Windows 方案变量 + 游戏窗口 + 帧标救回 + 覆盖去双计（r36/r37） | 单 Agent + 用户 2h 游戏 | 已完成 | 341e6eb/0a1e24d |
| 19 | P4 **补交互类 ~16 分钟**（interactive ≥0.15） | 用户 + 单 Agent | **待办（下一步）** | 需新 part9（新 schema 带 scheme） |
| 20 | P4 真数三模型 + Return+10% → tag phase-04-done | 单 Agent | 待办 | 依赖 19 |
| 21 | P5–P7 | 待定 | 待办 | 见 plans/ 各文件 |

## 6. 已完成步骤（已验证事实）

- [x] 只读分析 / 开工准备 / 根目录清理（6111aef）/ AGENTS+CLAUDE（53be743）/ P0（535081a + tag phase-00-done）
- [x] P1 E2：GPU 基线 775 samples/780s（artifacts/gpu_baseline_A.csv）
- [x] P2 E3：双重启 299s+202s + LKG 2/2 <60s（e356fa8/ecbd6cb，docs/p2-e3-drill-report.md）
- [x] P3：State48/BlackBox/HAL/护栏/dry-run V01–V09（1562a62 + tag phase-03-done，45 单测绿）
- [x] P4 合成链 + B2 锚（mean 71.4 / p50 74.9）+ 干等价 4/4 零违例（至 6e5e96a/ce69a6a/fa54b88）
- [x] P4 工具链：采集器/覆盖监测/交互探针（冷 608ms 热 88ms）/插拔 watcher（9dab39f…c4d5b24）
- [x] P4 实试点 + 合成压测（26c64d1/eb744c4/794c1d0/a7e19eb）+ 证据索引（29c32ab/143b67a）
- [x] requirements 锁定：lightgbm 4.7.0 + onnx 1.23.0 + onnxscript
- [x] r27：coverage 只读分片（48753 真行）、nvidia-smi DriverStore 回落、PresentMon + fps_join（16/16）、真数 n12081 诚实入库
- [x] r28：E4 影子链路（BlackBox 10/10、errors 0、围栏 0.0103ms、l2 dry-run）
- [x] r29：档位真读（GetThermalMode=3=Beast，COM 263ms，Set* 不调用）+ `--sense-gear` + c1 口径修正
- [x] r30：四档映射齐全（1/2/3/224）+ 档位标签审计（part1–4 为常量）
- [x] r31：一键同窗脚本（回填 15/15，c3 通道 PASS 3.26%）
- [x] r32：coverage 报告新增 gear_distribution
- [x] r33：c3 口径修正（dry-run 无作动 → BLOCKED；窗口漂移降级 c3b）+ 办公窗口 900s（W1 达标）
- [x] r34：插拔判据收紧（只认 status 切换，电量漂移不计）
- [x] r35：DC 段 438 行（第 4 格）+ 真插拔事件 `plug-in 12:11:13`
- [x] r36：Windows 电源方案入 CSV（scheme 列 + schema 守卫）+ 切换实测捕获
- [x] r37：游戏窗口帧标救回（5703/5719，99.7%）+ `_app_match` 加固 + 覆盖时长去双计（W2 3.54h 属实）

## 7. 进行中 / 下一步（新对话先干这个）

- 当前卡点：① `interactive_ratio 0.136 < 0.15`（游戏行稀释，需补 ~16 分钟交互类）② 九宫格 4/16（缺 W3–W7 与其余 DC，非 E4 硬要求）③ c1/c3 属 P6/E5 判据 ④ L1 阈值校准待 P6 立案。
- 下一步动作：
  1. **补交互类 ~16–20 分钟**（首选，直接解卡）：
     `python tools\collect_shadow.py --seconds 1200 --work W1 --acdc AC --sense-gear --out artifacts\datasets\D_safe_shadow_A_part9.csv`
     （或浏览器场景 `--work W6`）；随后 `python tools\coverage_report.py` 确认 interactive ≥0.15。
  2. **真数三模型**：`python tools\pilot_real_train.py`（现已有真档位 + 游戏类帧标 p95 数据）→ 三模型对比；
     若分布仍窄（W0 占多数）按诚实记录，不拿合成冒充。
  3. **Return+10% 回放**：与 B2 proxy 锚（mean 71.4）对比 → shield 不上升 → 冻结 D_safe → `tag phase-04-done`。
  4. 可选加分：W3 compile / W4 video-call / W5 render / W6 browser / W7 plug-flap + 其余 DC 列。
- 待验证假设：B 机 BIOS 未锁欠压（若锁则 P5 改子空间迁移）；B 机 WMI Extreme mode 值（本机 3=Beast/224=Extreme 可参照）。

## 8. 待办步骤

- [ ] 补交互类 ≥16 分钟 → interactive ≥0.15（采集达标）
- [ ] 真数三模型重训 + Return+10% 回放 + 冻结 D_safe + tag phase-04-done
- [ ] P6：L1 阈值专项（Beast 档 46% 触发）+ 影子五门禁 + 第二策略（解锁 c1）
- [ ] E5 金丝雀（解锁 c3）→ 小步 live（ΔPL≤5W / Δfreq≤100MHz / UV≤5mV）
- [ ] P5 跨机迁移（需 B 机上线）
- [ ] 附带小事：`watcher.lock` 随手删；LICENSE 权利人占位 `yyhhqq1234`；
      `tools/presentmon/*.exe`、`artifacts/samples/pm_*.csv`、`e4_shadow_*.jsonl` 均未入库（已 ignore）

## 9. 雷区（进行时必须避开）

- 基础类：`watcher.lock` 不硬删；`schtasks` 需 UAC；路径禁空格/中文；外部参照（`D:\Intel降压定频 .exe` + `undervolt_config.json`）只读；
  温度阈值禁硬编码（读 MSR 0x1A2）；术语 G0–G4（**G5 禁词**）；B2 只用 worktree；edit 前先 read；CRLF 不"修复"；
  pwsh5.1 无 `&&`；源码/测试全 ASCII；python 内 open() 读文件；pip 依赖只记新增；`chcp 65001` 处理 onnx 编码；
  502 等 60s 重推；影子 CSV 混列由 repair 归档；锁文件换新 part；合成行写 D_stress_* 不进覆盖 glob；单格窄分布不冒充。
- **coverage 口径**：glob 曾吃到 rollup 总表（83234 虚高）→ 统计只读 `*_part*.csv`，采集一律 `--out ..._part<N>.csv`。
- **`interactive_ratio` 门槛**：<0.15 不许报采集达标；游戏/长采后必须复核（本轮被稀释到 0.136）。
- **PresentMon**：录制期独占 CSV（并发读 `Errno 13`）→ 停后回填；2.6.0 用 `--timed`（无 `--capture_seconds`）；
  `--date_time` 恒偏 −28796.9s（自动重定基）；**`Application` 列含扩展名（`ff7rebirth_.exe`）**，传主干名会整窗零帧标（r37）；
  2h 全进程 CSV ≈ 400MB（已 ignore）；桌面 `dwm.exe` 帧不得混入游戏格。
- **Windows 电源方案是独立变量**：Fn+Q 不切方案（实测 Beast 下 scheme 仍"节能"）；方案中途切换会改变功耗/温度画像
  → CSV 自 r36 起记 `scheme`；part1–8 无该列，论文须声明。
- **schema 变更**：加列后**不得**向旧文件追加（守卫会拒绝）；旧数据不回填、不冒充"有该维度"。
- **插拔事件**：只认 `Win32_Battery.BatteryStatus` 切换（`plug-in`/`unplug`）；电量漂移（`charge-change`）不算插拔。
- **覆盖时长**：采集器与影子同窗并行时**不得相加**（r37 双计：2h 报成 5.13h）；JSONL 仅作判据统计。
- **档位通道**：只读 `GetThermalMode`（**空参**调用，传 Data 报"无效的参数"）；`Set*` 一律不调用；
  part1–4 的 gear 是常量，不许当档位观测用。
- **E4 判据**：c1 无第二策略一律 BLOCKED；c3 在 dry-run 阶段原理上不可测（E5 才有意义）；`e4_ready` 只在四项全 PASS 且覆盖/插拔达标为 true；
  CPU 温度 proxy 逐行标注 `cpu_temp_src="proxy-gpu"`；`l2_mutex.actuate(dry_run=False)` 直接 raise，永不放宽。
- **L1 阈值**：Beast 档游戏 46% 触发 L1（85°C）已立案；改阈值属 L 级提案，不得先改后报。

## 10. 关键文件与修改

- 协议/规格：`AGENTS.md`、`CLAUDE.md`、`specs/SYSTEM_SPEC_DRAFT_v1.0.md`、`docs/safety-fence-spec.md`、`docs/thesis-proposal-outline.md`
- 核心模块：`src/state/state48.py`、`src/blackbox/log.py`、`src/actuate/hal_map.py`、`src/actuate/l2_mutex.py`、`src/guard/*`、`src/policy/{surrogate,stub}.py`
- 传感：`src/sense/lenovo_wmi.py`（档位真读，只 Get*/Is*）、`src/sense/nvidia_poll.py`、`src/sense/wmi_events.py`
- 工具链：`tools/shadow_run.py`（E4 影子）、`tools/e4_shadow_report.py`（四判据 + c1b/c3b + 覆盖矩阵）、
  `tools/run_shadow_window.py`（一键同窗）、`tools/collect_shadow.py`（1Hz 采集，`--sense-gear`/scheme 列/schema 守卫）、
  `tools/gear_probe.py`、`tools/fps_join.py`、`tools/presentmon/README.md`、`tools/coverage_report.py`、`tools/plug_watch.py`、
  `tools/repair_shadow.py`、`tools/run_p3_dryrun.py`、`tools/pilot_real_train.py`、`tools/reward_baseline_B2.py`、
  `tools/make_dsafe_synth*.py`、`tools/train_p4_*.py`、`tools/bo_p4_synth.py`、`tools/cross_AB_synth.py`、
  `tools/gpu_stress.py`、`tools/interactive_probe.py`
- 文档链：`docs/p4-collection-protocol.md`、`docs/p4-progress-synth.md`、`docs/p4-evidence-index.md`、
  `docs/p4-gate-report.md`（§8 r29 / §9 r30 / §10 r33 / §11 r34 / §12 覆盖面 / §13 r36 / §14 r37）、
  `docs/p2-e3-drill-report.md`、`docs/hal-boot-sequence.md`、`docs/p3-gate-report.md`
- 数据：`artifacts/samples/`（小样例 + 结论型 JSON 可进仓；`pm_*.csv`、`e4_shadow_*.jsonl` 已 ignore）；
  `artifacts/datasets/`（实采大 CSV：part1–8、plug_events、gear_probe、D_stress，全部 ignore）

## 11. 验证方式

- 仓库干净 `git status --porcelain` 空；`pytest tests/` 45 绿；`git push origin master` 通。
- 覆盖：`python tools/coverage_report.py`（rows / 16 格 / interactive / gear_distribution）。
- 门禁：`python tools/e4_shadow_report.py --glob "artifacts/samples/e4_shadow_*.joined.jsonl"`（exit 2 = 未就绪，属正常）。
- 档位：`python -c "import sys;sys.path.insert(0,'src');import sense.lenovo_wmi as lw;print(lw.read_gear())"`。
- 阶段验收：`plans/PHASE-0x` §4 checklist 逐项贴证据，不许空勾。

## 12. 恢复指令

- 新对话打开本项目后执行 `/resume`，Agent 读取本文件并从「§7 下一步」继续。

---

- 更新历史：
  - 2026-09-16 初建 → 2026-09-22 P1–P3 封版 + P4 合成/实采
  - 2026-10-14 11:05 r27 口径 + 帧标；11:15 r28 E4 影子链路；11:25 r29 档位真读
  - 2026-10-14 11:45 r30/r31 四档映射 + 标签审计 + 一键同窗
  - 2026-10-14 12:00–14:45 r32–r37：coverage 档位维度、c3 口径、办公窗口（W1 达标）、插拔判据收紧、
    DC 段 + 插拔事件达标、Windows 方案变量入 CSV、2h 游戏窗口（W2 3.54h 达标 + 游戏 p95 6.28ms）
    + 帧标救回 + 覆盖去双计；**E4 覆盖面四项全绿**，interactive 待补至 0.15。
