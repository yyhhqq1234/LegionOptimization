# TASKPOINT — 项目级任务断点

> 保存时间：2026-10-14 15:35（UTC+8）
> 项目根目录：D:\LegionOptimization
> 分支/版本：master @ c8ec7fc（+ 本次断点提交；tags：legion-legacy-b2、phase-00-done、phase-03-done）

## 1. 任务目标

- 一句话目标：推翻旧 Lenovo 静态调优胶水项目，重构为**通用笔记本功耗自适应调优系统**（Intel HX 全系 + RTX 40/50 Laptop，本地自训练小模型实时调优），作为人工智能专业毕设，约 16 周交付。
- 当前子目标（P4 A方案落地）：D_safe≥2000/机九宫格≥80% + 三模型对比 + 回放Return+10% shield不升 + ONNXv1<10MB<5ms + tag phase-04-done。
- 验收标准：
  - [x] P0–P3 全部封版（tags phase-00-done / phase-03-done）
  - [x] P4 perf 标链路、E4 影子链路、档位真读四档映射、标签审计、一键同窗（r27–r31）
  - [x] **E4 覆盖面四项全绿**：idle 9.89h / 办公 2.11h / 游戏 3.54h / 插拔 1 次（r35–r37）
  - [x] 采集达标 `interactive_ratio` **0.151 ≥ 0.15**（r39）
  - [x] **三模型真数对比**（MLP / LGB / ENS，两组，r40）
  - [x] **ONNX 真数版** <10MB <5ms：A 0.02MB/0.019ms、B 0.02MB/0.013ms（r40）
  - [~] **回放 Return**：已算（真数 mean 94.98 vs B2 锚 71.44，nominal +32.95%）但 **verdict = NOT-ACCEPTANCE-EVIDENCE**（r41，五条原因）
  - [ ] 九宫格 ≥13/16：**当前 4/16**（缺 W3–W7 + W1/W2 的 DC 列）
  - [ ] 跨机迁移（P5）；影子五门禁 + 48h 金丝雀（P6/P7）；论文初稿 + 答辩演示

## 2. 背景与现状

- 旧项目冻结于 tag `legion-legacy-b2`；A 机 Y7000 2025（255HX / RTX 5060 Laptop / 驱动 617.14），B 机待上线。
- 路线：A 方案（监督代理 + 约束 BO）→ B 方案（离线 RL，主 IQL）；M5 负载预测叠加。
- 当前数据与实测（r41）：
  - **数据量**：`rows 56966`，覆盖 **4/16**（W0/AC 35172、W0/DC 438、W1/AC 8616、W2/AC 12740），interactive **0.151**。
  - **真档位标签**：part5 起为真读（Quiet 104 / Balance 1125 / Beast 6860 / mode:2 124）；
    part1–4 的 48753 行 gear 为常量（不构成档位观测，r30 审计，不回填）。
  - **环境变量**：Windows 电源方案独立于档位（12:30:40 节能→高性能被逐 tick 捕获）；CSV 自 r36 含 `scheme` 列。
    已形成对照组：part6（W1×Balance×节能）vs part9（W1×Beast×高性能）。
  - **真数模型（r40）**：组 A 遥测 56966 行 → LGB power RMSE 11.660（基线 54.654，−78.7%）、temp 17.494（−22.1%）；
    组 B 帧标 6135 行 → LGB fps 7.478 / power 3.122（−76.2%）/ temp 1.131（−79.4%）；
    **fps 头三模型全部输给均值基线 5.338（负结果，如实记）**。
  - **真数 Return 回放（r41）**：mean 94.98 / p50 100 / p90 100，nominal +32.95%，
    但 **perf 饱和 86.8%**（目标帧 120 < 实测 ~159fps）+ dry-run 无作动 + 跨源 + 环境不匹配 + shield 仅 GPU
    → `NOT-ACCEPTANCE-EVIDENCE`，**不构成 +10% 证据**。
  - **已修的口径/证据问题（6 个）**：r27 rollup 双计、r33 c3、r34 插拔 vs 电量、r36 方案缺列、
    r37 帧标零匹配 + 覆盖时长双计、r41 perf 换算未按 work 分类（全部记入 `docs/p4-gate-report.md` §8–§18）。
  - 立案（P6）：Beast 档高压游戏 L1 触发率 46%（`TEMP_L1_GPU=85°C`，峰值 87°C，L2=0）—— 待判阈值过紧 vs 真实过热。
  - 已知局限（逐行标注）：`GetCPUTemp/GetGPUTemp`=0 → `cpu_temp_src="proxy-gpu"`；`policy_ver=stub-1`；
    State48 fill_rate 0.125；live 因 E4/E5 门禁继续锁定。
- 约束：全程 dry-run 默认；门禁不过不真实下发；公开仓库，禁 force-push。

## 3. 总体计划

1. P0–P3 已封版 → P4（进行中）→ P5 迁移 → P6 离线 RL + 影子五门禁 → P7 金丝雀 + 论文答辩
2. Done 六件套：代码 + 单测绿 + 文档同步 + 产物归档 + V 格记录 + commit 已推

## 4. 团队模式

- 当前 **单 Agent 执行**；历史团队（只读分析 / 开工准备）已完成并归档删除。需要并行（如 P6 多算法）时新建，任务 id 重编。

## 5. 步骤规划

| # | 步骤 | 负责人 | 状态 | 备注 |
|---|------|--------|------|------|
| 1–18 | 只读分析 → P0–P3 → P4 合成链/干等价 → r27–r37（口径/帧标/档位/标签审计/DC/游戏窗口） | 单 Agent(+用户) | 已完成 | 见 §6 与 git log |
| 19 | P4 part9 交互补采（interactive 达标） | 用户 + 单 Agent | 已完成（r39） | W1×Beast×高性能 1027 行；0.151 |
| 20 | P4 真数模型 pilot + 真数三模型对比 + 真数 ONNX | 单 Agent | 已完成（r40） | commits ae40ac2/9aebf4a/c11d4cb |
| 21 | P4 真数 Return 回放（量级参考，拒绝当证据） | 单 Agent | 已完成（r41） | commit c8ec7fc |
| 22 | P4 **九宫格补齐**（W3/W4/W5/W6/W7 各 AC，W1/W2 DC） | 用户 + 单 Agent | **待办（下一步）** | 每格真实负载，新 schema `--sense-gear` |
| 23 | P4 Return 验收（需有作动回放或 E5 live）→ tag phase-04-done | 单 Agent | 待办 | 依赖 22 + E5 |
| 24 | P5–P7 | 待定 | 待办 | 见 plans/ |

## 6. 已完成步骤（已验证事实）

- [x] 只读分析 / 开工准备 / 根目录清理（6111aef）/ AGENTS+CLAUDE（53be743）/ P0（535081a + tag）
- [x] P1 E2 探针（775 samples/780s）；P2 E3 双重启 + LKG 2/2 <60s（e356fa8/ecbd6cb）
- [x] P3 HAL/State48/BlackBox/护栏/dry-run V01–V09（1562a62 + tag phase-03-done，45 单测绿）
- [x] P4 合成链 / B2 锚 71.4 / 干等价 4/4 / 工具链 / 实试点 / 压测 / 证据索引（至 a7e19eb 系列）
- [x] requirements：lightgbm 4.7.0 + onnx 1.23.0 + onnxscript
- [x] r27：coverage 只读分片、nvidia-smi DriverStore 回落、PresentMon+fps_join、真数 n12081 诚实入库
- [x] r28：E4 影子链路（shadow_run + e4_shadow_report）
- [x] r29：档位真读（GetThermalMode，只 Get*/Is*）+ `--sense-gear` + c1 口径修正
- [x] r30：四档映射齐全（1/2/3/224）+ 档位标签审计
- [x] r31：一键同窗（run_shadow_window）
- [x] r32/r33：coverage 档位维度；c3 口径归位（dry-run 不可测）
- [x] r34：插拔判据收紧（只认 status 切换）
- [x] r35：DC 段 438 行（第 4 格）+ 真插拔事件
- [x] r36：Windows 方案入 CSV + schema 守卫 + 切换实测
- [x] r37：游戏窗口帧标救回（5703/5719）+ `_app_match` + 覆盖去双计
- [x] r39：part9 交互补采 → interactive 0.151（达标恢复）
- [x] r40：真数模型 pilot + 真数三模型（含 fps 负结果）+ 真数 ONNX（+侧车）
- [x] r41：真数 Return 回放（verdict NOT-ACCEPTANCE-EVIDENCE，五条原因）

## 7. 进行中 / 下一步（新对话先干这个）

- 当前卡点：① **九宫格 4/16**（缺 W3–W7 与 W1/W2 DC）② Return 验收需**有作动回放或 E5 live**
  ③ c1 需 P6 第二策略 ④ L1 阈值校准待 P6 立案 ⑤ fps 头负结果待 P5/P6 补特征。
- 下一步动作：
  1. **九宫格补齐（用户配合真实负载，每格 ≥80 秒即可，建议各 5–10 分钟）**：
     ```powershell
     cd D:\LegionOptimization
     python tools\collect_shadow.py --seconds 600 --work W3 --acdc AC --sense-gear --out artifacts\datasets\D_safe_shadow_A_part10.csv
     ```
     依次替换 `--work`：W3 编译 / W4 视频会议 / W5 渲染 / W6 浏览器 / W7 插拔 flap；
     DC 列用 `--acdc DC`（拔电采 W1、W2）。
  2. 每轮采完 `python tools\coverage_report.py` 看格数；达到 13/16 后进入 Return 验收准备。
  3. **Return 验收路径**（二选一）：① 有作动回放（构造会下发 setpoints 的策略版本，仍在 dry-run 边界内只算不写）
     ② E5 金丝雀（真实小步下发）。两者都需要先过 E4 记录。
  4. 真数三模型 ↔ 合成对比写进论文方法章（LGB 两轮均胜 MLP；fps 头负结果作为特征工程依据）。
- 待验证假设：B 机 BIOS 未锁欠压；B 机 WMI Extreme mode 值（本机 3=Beast/224=Extreme 可参照）。

## 8. 待办步骤

- [ ] 九宫格补齐：W3/W4/W5/W6/W7（AC）+ W1/W2（DC）
- [ ] Return 验收（有作动回放或 E5 live）→ 冻结 D_safe → tag phase-04-done
- [ ] P6：L1 阈值专项 + 影子五门禁 + 第二策略（解锁 c1）+ fps 头特征工程
- [ ] E5 金丝雀（解锁 c3）→ 小步 live（ΔPL≤5W / Δfreq≤100MHz / UV≤5mV）
- [ ] P5 跨机迁移（需 B 机上线）
- [ ] 附带小事：`watcher.lock` 随手删；LICENSE 权利人占位 `yyhhqq1234`；
      `tools/presentmon/*.exe`、`artifacts/samples/pm_*.csv`、`e4_shadow_*.jsonl` 未入库（已 ignore）；
      ONNX `.data` 侧车已入库（缺它模型无法加载）

## 9. 雷区（进行时必须避开）

- 基础类：`watcher.lock` 不硬删；`schtasks` 需 UAC；路径禁空格/中文；外部参照只读；温度禁硬编码；
  G0–G4（**G5 禁词**）；B2 只用 worktree；edit 前先 read；CRLF 不"修复"；pwsh5.1 无 `&&`；源码/测试全 ASCII；
  python 内 open()；pip 只记新增；`chcp 65001`；502 等 60s；混列走 repair；锁文件换新 part；
  合成行写 D_stress_* 不进覆盖 glob；单格窄分布不冒充。
- **coverage 口径**：只读 `*_part*.csv`；**覆盖时长不得把采集 CSV 与影子 JSONL 相加**（r37 双计：2h 报 5.13h）。
- **PresentMon**：录制期独占 CSV → 停后回填；用 `--timed`；`--date_time` 恒偏 −28796.9s；
  **`Application` 列含扩展名**（传主干名会整窗零帧标，r37）；2h 全进程 CSV ≈ 400MB（ignore）。
- **Windows 电源方案是独立变量**：Fn+Q 不切方案；方案切换会改画像；CSV 自 r36 记 `scheme`；part1–8 无该列须声明。
- **schema 变更**：加列后不得向旧文件追加（守卫拒绝）；旧数据不回填、不冒充"有该维度"。
- **插拔事件**：只认 `BatteryStatus` 切换；电量漂移不算（r34）。
- **档位通道**：`GetThermalMode` **空参**调用；`Set*` 永不调用；part1–4 的 gear 是常量不许当观测。
- **E4 判据**：c1 无第二策略一律 BLOCKED；c3 在 dry-run 阶段原理上不可测；`e4_ready` 只在四项全 PASS 且覆盖/插拔达标为 true；
  CPU 温度 proxy 逐行标注；`l2_mutex.actuate(dry_run=False)` 直接 raise。
- **perf/Return 口径（r41）**：perf 必须**按 work 分类**定义（游戏=帧率、非游戏=响应性）；
  统一 `fps/目标帧` 会饱和（实测 86.8% 行 perf=100）与误判办公类；**Return 验收必须用有作动回放或 live**，
  跨源/跨环境数字只能作量级参考（不得写进验收结论）。
- **fps 头负结果**：当前特征下模型输给均值基线，不得包装成"性能预测达标"；补特征或改分位/分类建模。
- **L1 阈值**：Beast 档 46% 触发已立案；改阈值属 L 级提案，不得先改后报。

## 10. 关键文件与修改

- 协议/规格：`AGENTS.md`、`CLAUDE.md`、`specs/SYSTEM_SPEC_DRAFT_v1.0.md`、`docs/safety-fence-spec.md`、`docs/thesis-proposal-outline.md`
- 核心模块：`src/state/state48.py`、`src/blackbox/log.py`、`src/actuate/{hal_map,l2_mutex}.py`、`src/guard/*`、`src/policy/{surrogate,stub}.py`
- 传感：`src/sense/lenovo_wmi.py`（档位真读）、`src/sense/nvidia_poll.py`、`src/sense/wmi_events.py`
- 工具链：`tools/shadow_run.py`、`tools/e4_shadow_report.py`、`tools/run_shadow_window.py`、`tools/collect_shadow.py`、
  `tools/gear_probe.py`、`tools/fps_join.py`、`tools/coverage_report.py`、`tools/plug_watch.py`、`tools/replay_real.py`、
  `tools/pilot_real_train.py`、`tools/train_real_models.py`、`tools/train_p4_full.py`、`tools/reward_baseline_B2.py`、
  `tools/make_dsafe_synth*.py`、`tools/bo_p4_synth.py`、`tools/cross_AB_synth.py`、`tools/gpu_stress.py`、
  `tools/interactive_probe.py`、`tools/run_p3_dryrun.py`、`tools/presentmon/README.md`
- 文档链：`docs/p4-gate-report.md`（§8–§18 为本轮口径与实测全记录）、`docs/p4-evidence-index.md`、
  `docs/p4-collection-protocol.md`、`docs/p4-progress-synth.md`、`docs/p2-e3-drill-report.md`、`docs/p3-gate-report.md`
- 产物：`artifacts/samples/`（real_models.json、real_three_model.json、replay_real.json、predictor_real_*.onnx(+.data)、
  reward_baseline_B2.csv、各 E4 报告 JSON；`pm_*.csv`/`e4_shadow_*.jsonl` ignore）；
  `artifacts/datasets/`（part1–9、plug_events、gear_probe、D_stress，全部 ignore）

## 11. 验证方式

- `git status --porcelain` 空；`pytest tests/` 45 绿；`git push origin master` 通。
- 覆盖：`python tools/coverage_report.py`；门禁：`python tools/e4_shadow_report.py --glob "artifacts/samples/e4_shadow_*.joined.jsonl"`
  （exit 2 = 未就绪，属正常）。
- 模型：`python tools/train_real_models.py`；回放：`python tools/replay_real.py`（verdict 字段即以结论为准）。
- 档位：`python -c "import sys;sys.path.insert(0,'src');import sense.lenovo_wmi as lw;print(lw.read_gear())"`。

## 12. 恢复指令

- 新对话打开本项目后执行 `/resume`，Agent 读取本文件并从「§7 下一步」继续。

---

- 更新历史：
  - 2026-09-16 初建 → 2026-09-22 P1–P3 封版 + P4 合成/实采
  - 2026-10-14 11:05–11:45 r27–r31（口径/帧标/档位/标签审计/一键同窗）
  - 2026-10-14 12:00–14:45 r32–r37（DC + 插拔 + 游戏窗口 + Windows 方案变量 + 帧标救回）
  - 2026-10-14 14:37–15:35 r38–r41：part9 交互达标、真数模型 pilot、真数三模型（含 fps 负结果）、
    真数 ONNX、真数 Return 回放（拒绝当验收证据）；**E4 覆盖面全绿，九宫格仍 4/16，Return 待有作动回放或 live**。
