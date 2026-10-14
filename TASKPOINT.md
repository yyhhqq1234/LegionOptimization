# TASKPOINT — 项目级任务断点

> 保存时间：2026-10-14 11:45（UTC+8）
> 项目根目录：D:\LegionOptimization
> 分支/版本：master @ 0237359（+ 本次断点提交；tags：legion-legacy-b2、phase-00-done、phase-03-done）

## 1. 任务目标

- 一句话目标：推翻旧 Lenovo 静态调优胶水项目，重构为**通用笔记本功耗自适应调优系统**（Intel HX 全系 + RTX 40/50 Laptop，本地自训练小模型实时调优），作为人工智能专业毕设，约 16 周交付。
- 当前子目标（P4 A方案落地）：D_safe≥2000/机九宫格≥80% + 三模型对比 + 回放Return+10% shield不升 + ONNXv1<10MB<5ms + tag phase-04-done。
- 验收标准：
  - [x] P0 锁 v1.0（待签字项已过，P1–P3 实际已执行完毕）
  - [x] P1 E2 只读探针（gpu_baseline_A 775samples/780s）
  - [x] P2 E3 新开机时序（299s+202s 双轮）+ LKG staging（2/2 <60s，只读）
  - [x] P3 HAL L0–L3 + State48/Action7 + dry-run 45单测绿 + tag phase-03-done
  - [x] P4 perf 标链路（PresentMon + fps_join 回填，16/16 实测，r27）
  - [x] P4 E4 影子链路（shadow_run 六步 + e4_shadow_report 四判据，r28）
  - [x] P4 档位真读通道 + 四档映射齐全（LENOVO_GAMEZONE_DATA，r29/r30）
  - [x] P4 一键同窗脚本（PresentMon+影子+回填+报告，c3 通道验证 PASS，r31）
  - [ ] P4 回放验收：相对 B2 基线 Return +10% 且 shield 不上升（合成BO仅+1.3%；真值待多格+perf标+E4/E5 live）
  - [ ] P4 九宫格≥80%（当前 3/16：W0/W1/W2 仅 AC）
  - [ ] E4 影子门禁通过：覆盖（游戏≥2h + 办公≥2h + idle≥1h + ≥1 插拔电）+ 判据（c1 需第二策略 / c2 ✓ / c3 通道 ✓ / c4 ✓）
  - [ ] 跨机迁移：B 机 200 条 fine-tune 达从零训 90%（P5）
  - [ ] 影子五门禁 + 48h 金丝雀通过（P6/P7），论文初稿 + 答辩演示

## 2. 背景与现状

- 旧项目：Lenovo Legion Fn+Q 档位经 LLT + ThrottleStop 拷 INI + powercfg 的静态调优，
  已整体删除，冻结于 tag `legion-legacy-b2`（commit dc1dd67，可 `git show` 恢复，不可复活进工作树）。
- 验证双机：A 机本机 Y7000 2025（U7 255HX，TJMax=105°C / RTX 5060 Laptop，驱动 617.14 / torch 2.11+cu128 sm_120）；
  B 机待上线（i9 14900HX + 5060）。
- 路线锁定：A 方案（监督代理模型 + 约束 BO，打底攒数据）→ B 方案（离线 RL，主 IQL，拔高）；
  M5 负载预测叠加；导师偏算法，方法章需 5 件套全厚度。
- 当前状态（r31，2026-10-14 实测）：
  - **档位映射 4/4 齐全**（操作者 Fn+Q 走档 + 即时读数，每档连读 3 次稳定 + probe 无丢点）：
    `1=Quiet(安静)`、`2=Balance(均衡)`、`3=Beast(野兽)`、`224=Extreme(超能)`。
  - **档位真读**：`src/sense/lenovo_wmi.py` 经 `root\WMI:LENOVO_GAMEZONE_DATA` **空参**调用 `GetThermalMode`
    （COM 优先 ≈263ms；传 Data 报"无效的参数"）；实测证实 **Fn+Q 不切 Windows 电源方案**（野兽模式下 scheme 仍"节能"）。
    只封装 `Get*/Is*`；该类存在 `Set*`（SetSmartFanMode/SetFanCooling/SetBIOSOC…）**一律不调用**。
  - **标签修复 + 审计（r30）**：`collect_shadow --sense-gear` 写真档位；
    逐 part 实测 part1–4 **48753/48753 行 gear 列是常量 `Balance-readonly`** → 该批数据不构成档位观测
    （不能做档位×负载分组监督，也不能当包络四档真数证据）；`work` 列同为人工参数、无独立佐证。
    真标签自 part5 起；`part5 = 228 行`（W0/AC；`Quiet` 104 + `mode:2` 124，后者是映射补全前的原始值，语义 = Balance，按只追加不回写）。
  - **一键同窗脚本（r31）**：`tools/run_shadow_window.py` = PresentMon 录制 + shadow_run + fps 回填 + E4 报告；
    smoke（W0，process=dwm.exe，20s）：回填 **15/15** 行、偏移 −28796.9s 自动重定基、
    报告 **c3 PASS**（baseline p95 5.82ms vs 影子中位 6.01ms，偏差 3.26%）、c2 PASS（L2+=0）、c4 PASS（errors 0）、
    c1 BLOCKED（需第二策略）、`e4_ready=false`。（dwm 目标仅通道验证，不作 E4 正式证据。）
  - 实采累计：**48979 行 / 约 13.6h**，覆盖 **3/16**，interactive **0.141**（口径只读 `*_part*.csv`）。
  - 已知局限（逐行标注）：`GetCPUTemp/GetGPUTemp` 返回 0（ACPI 未提供）→ 围栏输入仍 `cpu_temp_src="proxy-gpu"`；
    `policy_ver=stub-1`（无策略权重）；State48 `fill_rate 0.125`。
  - live 因 E4/E5 门禁缺失继续锁定（用户小步确认已记录，铁律3要求门禁+确认双齐）。
- 约束：全程 dry-run 默认；门禁不过不真实下发；公开仓库，禁 force-push。
- 变更记录：2026-09-22 P4 合成链+实采+压测；10-14 r27 口径+帧标；r28 E4 影子链路；r29 档位真读；
  r30 标签审计；r31 一键同窗脚本。

## 3. 总体计划

1. P0 E0/E1 评审锁 v1.0（已执行）→ P1–P3 已封版
2. P4（进行中）：D_safe 实采补格 + perf 标 + 三模型真数重训 + 回放Return+10% + ONNXv1 + tag phase-04-done
3. P5：跨微架构迁移实验，200 条达 90%，迁移效率曲线（论文图）
4. P6：五算法离线 RL 对比 + OPE + 影子五门禁 + M5 预测器（同时给 E4 c1 引入第二策略）
5. P7：48h 金丝雀 + B 机 24h 交叉 + V closure + 论文答辩（G4 真实下发最后放行）
6. B 机上线后补 B 列复测与跨机（cross_AB 合成先行：A→B RMSE 3.33/2.66/1.74 vs 同机 3.10/2.69/1.66）
7. 每阶段：代码+单测绿+文档同步+产物归档+V格记录+commit已推（Done六件套）

## 4. 团队模式

- 是否采用团队模式：**否（当前单 Agent 执行）**。
- 历史团队（均已完成并归档删除，无需唤醒）：
  - `legion-readonly-analysis`（只读分析：arch-mapper/t1 架构、script-auditor/t2 脚本审计、
    config-checker/t3 配置核对、risk-reviewer/t4 风险、t5 汇总；结论已沉淀进规格与汇总文档）
  - `legion-rebuild-prep`（开工准备：spec-architect/p-spec、thesis-writer/p-thesis、
    env-auditor/p-env、safety-planner/p-safety、p-synth 汇总；交付物为 specs/docs 现有文件）
- 后续如需并行（如 P6 多算法训练），新建团队，任务 id 重新编号（旧 id 不复用）。

## 5. 步骤规划

| # | 步骤 | 负责人 | 状态 | 备注 |
|---|------|--------|------|------|
| 1 | 只读分析旧项目 | 单 Agent + 团队 | 已完成 | 结论沉淀规格/汇总 |
| 2 | 开工准备 4 交付（规格/大纲/环境/围栏+汇总） | 团队 | 已完成 | specs/docs 现有文件 |
| 3 | 根目录清理 + tag + push + 删 4 尸体任务 | 单 Agent | 已完成 | commit 6111aef |
| 4 | AGENTS/CLAUDE + 仓库初始化 | 单 Agent | 已完成 | commit 53be743 |
| 5 | P0 执行（规格 v1.0 冻结） | 单 Agent | 已完成 | commit 535081a + tag phase-00-done |
| 6 | P1 E2 探针（GPU基线775/780s，只读） | 单 Agent | 已完成 | artifacts/gpu_baseline_A.csv |
| 7 | P2 E3 双重启实测 + LKG staging | 单 Agent + 用户重启 | 已完成 | 299s+202s；LKG 2/2 <60s；commit e356fa8/ecbd6cb |
| 8 | P3 HAL/State48/BlackBox/dry-run + tag | 单 Agent | 已完成 | 45单测绿；commit 1562a62 + tag phase-03-done |
| 9 | P4 合成链（AB合成/三模型/ONNX/BO/cross） | 单 Agent | 已完成 | LGB胜MLP诚实记录；BO+1.3%；ONNX 0.02MB/0.02ms |
| 10 | P4 B2锚/V12/包络干等价 | 单 Agent | 已完成 | B2 proxy锚71.4；四档4/4零违例；live锁E4/E5 |
| 11 | P4 影子实采 part1–5 | 单 Agent + 用户用机 | 进行中（3/16格，48979行） | part5 起带真档位标签 |
| 12 | P4 口径修正 + perf 标链路 | 单 Agent | 已完成（r27） | commit 7bdf99f；fps_join 16/16 实测 |
| 13 | P4 E4 影子链路（shadow_run + e4_shadow_report） | 单 Agent | 已完成（r28） | commit 055392a；BlackBox 10/10、四判据可判 |
| 14 | P4 档位真读通道 | 单 Agent | 已完成（r29） | commit 681be77；GetThermalMode=3=Beast 实测 |
| 15 | P4 档位四档映射齐全 + 标签审计 | 单 Agent + 用户按 Fn+Q | 已完成（r30） | commits 4bebee2/154a5d1/508a17e/4f794a3；1/2/3/224 |
| 16 | P4 一键同窗脚本（c3 通道验证 PASS） | 单 Agent | 已完成（r31） | commit 0237359；回填 15/15、c3 PASS 3.26% |
| 17 | P4 E4 解锁：真负载同窗采 W2 + 补 W1/DC/插拔 | 用户 + 单 Agent | 待办 | 命令见 §7 |
| 18 | P4 真数三模型 + Return+10% → tag phase-04-done | 单 Agent | 待办 | 依赖 11+17 |
| 19 | P5–P7 | 待定 | 待办 | 见 plans/ 各文件 |

## 6. 已完成步骤（已验证事实）

- [x] 只读分析：Fn+Q 双触发链、Boot 双轨、FIVR 五步、配置对照表、风险 Top；验证：t1–t5 报告归档，团队已删。
- [x] 开工准备 4 交付：规格/大纲/围栏/kickoff；验证：文件在仓。
- [x] 根目录清理：commit 6111aef（27 files，-2543 行）；验证：`git ls-files` 仅 5 项，tag legion-legacy-b2 可取回。
- [x] 删 4 Disabled 尸体任务；验证：复查零残留。
- [x] AGENTS/CLAUDE/README/LICENSE/.gitattributes/PR 模板；验证：commit 53be743 已推，8 milestone 已建。
- [x] P0 执行：G5 清零 5 处、正交 30 格、Reward 补 burst 惩罚；验证：commit 535081a + tag phase-00-done 双双在远端。
- [x] P1 E2：GPU 基线 775 samples/780s 只读；验证：artifacts/gpu_baseline_A.csv，P3回放50行零L2+误放行。
- [x] P2 E3：双重启 299s+202s PASS + LKG 2/2 <60s（只读）；验证：commits e356fa8/ecbd6cb，docs/p2-e3-drill-report.md。
- [x] P3：State48/BlackBox/HAL_MAP/L2互斥/护栏/ACDC/MLP+Ensemble/dry-run V01-V09 p99 0.002ms；验证：pytest 45绿，commit 1562a62 + tag phase-03-done。
- [x] P4 合成：A2000 16/16 + B1200 + 三模型（LGB 胜 MLP）+ ONNX 0.02MB/0.02ms + BO +1.3% shield平 + cross-AB；验证：commits 至 6e5e96a。
- [x] P4 B2锚：mean71.4 p50 74.9（冻结值×代理，B0/B1实log缺记blocked）；验证：commit ce69a6a，samples/reward_baseline_B2.csv。
- [x] P4 干等价：B2四档全OK违例0 BlackBox 4/4；验证：commit fa54b88。
- [x] P4 工具链：shadow 1Hz采集器 + 16格覆盖监测 + 交互探针（冷608ms/热88ms）+ 插拔watcher；验证：commits 9dab39f…c4d5b24。
- [x] P4 实试点：600行power0.19胜均值；n1147复跑输均值（窄idle实证）；验证：commits 26c64d1/eb744c4/794c1d0。
- [x] P4 合成压测：180s torch matmul有界，STRESS标不进九宫格；验证：commit a7e19eb。
- [x] P4 证据索引 + r26门禁对账；验证：commits 29c32ab/143b67a。
- [x] requirements 锁定：lightgbm 4.7.0 + onnx 1.23.0 + onnxscript；验证：pip安装成功，ONNX导出通。
- [x] P4 r27：coverage 只读分片（48753 真实行）；nvidia-smi 回落；PresentMon + fps_join（16/16）；真数 n12081 诚实入库；验证：7bdf99f/a02249d/7bdfeb2。
- [x] P4 r28：E4 影子链路（BlackBox 10/10、errors 0、围栏 OK×10 0.0103ms、l2 dry-run）；验证：055392a。
- [x] P4 r29：档位真读（GetThermalMode=3=Beast；COM 263ms；Set* 不调用）+ `--sense-gear` 标签修复 + c1 口径修正（影子 vs 在运策略）+ c1b 观察项；验证：681be77/36ac69f。
- [x] P4 r30：四档映射齐全（1=Quiet/2=Balance/3=Beast/224=Extreme，各连读 3 次稳定 + probe 无丢点）+ 标签审计（part1–4 gear 列 48753/48753 常量）；验证：4bebee2/154a5d1/508a17e/4f794a3。
- [x] P4 r31：一键同窗脚本 `tools/run_shadow_window.py`（PresentMon+影子+回填+报告），smoke 回填 15/15、**c3 PASS**（5.82→6.01ms，3.26%）、c2/c4 PASS、c1 BLOCKED；验证：0237359，pytest 45绿。

## 7. 进行中 / 下一步（新对话先干这个）

- 当前卡点（r35 实测更新）：① **E4 覆盖只剩游戏 ≥2h**（W2/AC 1.92h，差 ~5 分钟）；idle ✅ 10.01h、办公 ✅ 2.11h、插拔 ✅ 1 次（12:11:13 `plug-in`）
  ② 九宫格 4/16（coverage 0.25，interactive 0.151）③ c1/c3 属 P6/E5 判据（E4 dry-run 阶段原理上不可测）。
- 下一步动作（① 是用户动作，其余可并行；命令已就绪）：
  1. **跑真负载时一键同窗**（游戏/渲染，解锁 c3 正式证据 + 补 W2/W5 格）：
     `python tools\run_shadow_window.py --seconds 1800 --work W2 --process <game.exe> --report`
  2. **办公/浏览补格**（补 W1/W6 与 2h 门槛）：
     `python tools\collect_shadow.py --seconds 600 --work W1 --acdc AC --sense-gear --out artifacts\datasets\D_safe_shadow_A_part6.csv`
  3. **拔电一次**（DC 列 + 插拔事件；watcher 已在）：
     `python tools\collect_shadow.py --seconds 1800 --work W0 --acdc DC --sense-gear --out artifacts\datasets\D_safe_shadow_A_part7.csv`
  4. **E4 复核**：`python tools\e4_shadow_report.py --glob "artifacts/samples/e4_shadow_*.joined.jsonl"`
  5. **真数三模型**：格 ≥13/16 且 perf 标齐 → `tools/pilot_real_train.py` → Return+10% shield平 → 冻结 D_safe → tag phase-04-done。
- 待验证假设：B 机 BIOS 未锁欠压（若锁则P5改子空间迁移）；B 机 WMI Extreme mode 值（本机 3=Beast/224=Extreme 可作参照）。

## 8. 待办步骤

- [ ] 真负载同窗采（游戏/渲染）→ c3 正式证据
- [ ] 补格：W1/W2 各 ~5 分钟 + W3–W7 + DC 列（拔电）
- [ ] E4 判据复核 → E5 金丝雀 → 小步 live
- [ ] 真数三模型重训 + Return+10% 回放验证 + tag phase-04-done
- [ ] P5 跨机迁移（需B机上线）→ P6 离线RL（同时给 c1 引入第二策略）→ P7 金丝雀+论文
- [ ] 附带小事：`watcher.lock`（0字节）重启后随手删；LICENSE权利人占位 `yyhhqq1234`，毕设要真名则改；
      `tools/presentmon/PresentMon-2.6.0-x64.exe` 与 `artifacts/samples/pm_*.csv` 未入库（已 ignore），换机按 README 重下。

## 9. 雷区（进行时必须避开）

- 现象/坑：`watcher.lock` 删不掉；原因：被 Session-0 进程长期持有；正确做法：不管它（已 gitignore），新实现用 `hal-actuation.lock` + PID 校验。
- 现象/坑：`schtasks /delete` 报 Access denied；原因：shell 非提权；正确做法：`-Verb RunAs` 弹 UAC 用户点是。
- 现象/坑：计划任务路径禁空格；原因：`D:\Intel降压定频 .exe` 被截断致 0x80070002；正确做法：新项目路径/文件名禁空格禁中文。
- 现象/坑：误删外部参照；原因：`D:\Intel降压定频 .exe` + `D:\undervolt_config.json` 是手动对比基线；正确做法：只读不碰。
- 现象/坑：温度阈值写死跨机翻车；原因：255HX TJMax=105，14900HX 未知；正确做法：运行时读 MSR 0x1A2 生成相对偏移。
- 现象/坑：术语混淆（已踩两轮）；原因：口径；正确做法：W0–W7负载 ≠ M1–M8模块，G0–G4唯一档，DC正交，**G5禁词**。
- 现象/坑：B2 基线复活污染工作树；原因：验证需旧脚本；正确做法：只许 worktree/archive 到临时目录，用完删。
- 现象/坑：edit 报 "file has not been read"；正确做法：先 read 再 edit。
- 现象/坑：CRLF warning 刷屏；正确做法：`.gitattributes text=auto`，不许全仓改行尾。
- 现象/坑：pwsh5.1 不支持 `&&`；正确做法：用 `;` 连接。
- 现象/坑：中文被 dotNET UTF8 改写 corrup；正确做法：源码/测试全ASCII，中文只进文档。
- 现象/坑：`cat file | python` JSONDecodeError；正确做法：python内 open() 读。
- 现象/坑：pip resolver 冲突；正确做法：pip直接装，requirements只记新增。
- 现象/坑：torch.onnx导出 gbk 编码错；正确做法：`chcp 65001` + PYTHONUTF8=1。
- 现象/坑：pip install 卡代理502；正确做法：等60s重推。
- 现象/坑：影子CSV混列；正确做法：repair脚本按header宽过滤归档，新schema另起 part。
- 现象/坑：锁文件删不掉（WinError 32）；正确做法：不硬删，换新文件续采。
- 现象/坑：合成行污染真数；正确做法：压测前停实采，合成行写 D_stress_*（不进覆盖 glob）。
- 现象/坑：单格窄分布训不出东西；正确做法：多格是硬需，不拿合成冒充。
- 现象/坑：coverage 数字虚高（83234）；原因：glob 吃到 rollup 总表；正确做法：只读 `*_part*.csv`，采集一律 `--out ..._part<N>.csv`。
- 现象/坑：续采写入空值行；原因：nvidia-smi 离开 PATH；正确做法：采集器回落 DriverStore 路径。
- 现象/坑：PresentMon 录制期读其 CSV 报 `[Errno 13]`；正确做法：录制期只并行采集，停后回填（`fps_join` 或 `run_shadow_window`）；2.6.0 无 `--capture_seconds`，用 `--timed`。
- 现象/坑：PresentMon `--date_time` 时间戳偏 +8h（−28796.9s）；正确做法：join 自动重定基。
- 现象/坑：dwm.exe 桌面合成帧混进游戏格；正确做法：`--process_name` / `--process <game.exe>` 过滤。
- 现象/坑：PresentMon 原始 CSV 近 2MB/窗口进仓；正确做法：`artifacts/samples/pm_*.csv` 已 ignore。
- 现象/坑：`git commit -m` 里嵌双引号被 shell 拆成 pathspec（本轮踩到）；正确做法：提交消息避免内嵌引号或用单引号/文件。
- 现象/坑：E4 判据假 PASS；正确做法：c1 无第二策略一律 BLOCKED，`e4_ready` 只在四项全 PASS 且覆盖/插拔达标时为 true。
- 现象/坑：CPU 温度 proxy 当真实值；原因：`GetCPUTemp/GetGPUTemp` 返回 0；正确做法：逐行写 `cpu_temp_src="proxy-gpu"`。
- 现象/坑：shadow_run 误走 live；正确做法：`l2_mutex.actuate` dry_run=False 直接 raise，不得放宽（铁律 4）。
- 现象/坑：以为 Fn+Q 会切 Windows 电源方案；原因：实测野兽模式下 scheme 仍"节能"；正确做法：档位只读 `GetThermalMode`（**空参**调用）。
- 现象/坑：gear 列写死命令行标签当真实档位（part1–4 全是常量）；正确做法：采集加 `--sense-gear`，未映射写 `mode:<n>`，旧数据不许回写成"有档位"。
- 现象/坑：误调 `LENOVO_GAMEZONE_DATA` 的 `Set*`；正确做法：只封装 Get*/Is*，下发只走 L2 且需门禁。

## 10. 关键文件与修改

- `AGENTS.md` / `CLAUDE.md`：agent 协议。
- `specs/SYSTEM_SPEC_DRAFT_v1.0.md`：HAL/State48/Action7/Reward/包络（v1.0冻结）。
- `docs/safety-fence-spec.md`：门禁细则（§5.2/§5.3 E4 四项判据）；`docs/thesis-proposal-outline.md`：V01–V24矩阵。
- `src/state/state48.py`：State48；`src/blackbox/log.py`：BlackBox环。
- `src/actuate/hal_map.py` + `src/actuate/l2_mutex.py`：档位换算 + 互斥（live 门禁前 raise）。
- `src/guard/`：burst/shields/acdc；`src/policy/surrogate.py`：MLP+Ensemble；`src/policy/stub.py`：静态包络策略。
- `src/sense/lenovo_wmi.py`（r29/r30）：档位真读（四档映射齐全，只 Get*/Is*）。
- `src/sense/nvidia_poll.py` + `src/sense/wmi_events.py`：GPU 轮询与 WMI 事件名。
- `tools/shadow_run.py`：E4 影子 run（遥测+真档位+策略+围栏试算+BlackBox+L2 dry-run）。
- `tools/e4_shadow_report.py`：四判据（c1/c1b/c2/c3/c4）+ 覆盖矩阵 + open_items。
- `tools/run_shadow_window.py`（r31）：一键同窗（PresentMon + 影子 + 回填 + 报告）。
- `tools/gear_probe.py`：Fn+Q 校准走档；`tools/collect_shadow.py`：1Hz 采集（`--sense-gear`/`--fps-file`）。
- `tools/fps_join.py`：帧标离后回填；`tools/presentmon/README.md`（exe 不入库）。
- `tools/coverage_report.py`：16格监测（只读 `*_part*.csv`）；`tools/repair_shadow.py`：混列修复。
- `tools/run_p3_dryrun.py`：V01–V09；`tools/reward_baseline_B2.py`：V12 B2锚；`tools/pilot_real_train.py`：实试点。
- `tools/make_dsafe_synth*.py` + `tools/train_p4_*.py` + `tools/bo_p4_synth.py` + `tools/cross_AB_synth.py`：合成链。
- `tools/gpu_stress.py`：有界合成负载；`tools/interactive_probe.py`：交互探针；`tools/plug_watch.py`：插拔watcher。
- `docs/p4-collection-protocol.md` + `docs/p4-progress-synth.md` + `docs/p4-evidence-index.md` + `docs/p4-gate-report.md`（§8=r29，§9=r30）：P4文档链。
- `docs/p2-e3-drill-report.md` + `docs/hal-boot-sequence.md` + `docs/p3-gate-report.md`：P2/P3证据。
- `artifacts/samples/`：合成AB、ONNX、B2锚、包络、pilot、E4 影子 JSONL 与报告（小样例可进仓；`pm_*.csv` 已 ignore）。
- `artifacts/datasets/`：实采大CSV（已ignore）：part1–5/锁文件/D_stress/gear_probe。
- 已废弃（tag可取回）：全部旧 `.bat/.ps1`、`ThrottleStop/` 等 legacy。

## 11. 验证方式

- 仓库干净：`git status --porcelain` 空；`git push` 通（502阵发等60s重推）。
- 阶段验收：按 `plans/PHASE-0x` §4 checklist 逐项贴证据，不许空勾。
- 测试：`pytest tests/` 45绿；覆盖：`python tools/coverage_report.py`。
- 门禁：`python tools/e4_shadow_report.py`（exit 2 = 未就绪，属正常）；影子≥8h有效覆盖（游戏≥2h+办公≥2h+idle≥1h+≥1插拔电）。
- 档位：`python -c "import sys;sys.path.insert(0,'src');import sense.lenovo_wmi as lw;print(lw.read_gear())"`（当前机器实测值）。
- 模型指标：回放 Return +10%（P4）、迁移 200 条达 90%（P5）。
- 帧标：`run_shadow_window.py --report` 后看回填行数与偏移打印。

## 12. 恢复指令

- 新对话打开本项目后执行 `/resume`，Agent 将读取本文件并从"§7 下一步"继续。

---

- 更新历史：
  - 2026-09-16：初建（P0待签字）。
  - 2026-09-22 16:01：P1/P2/P3封版（tags+03），P4合成链+实采+压测，live锁E4/E5。
  - 2026-10-14 11:05：r27——口径修正、nvidia-smi 回落、perf 标链路、真数 n12081 诚实入库。
  - 2026-10-14 11:15：r28——E4 影子链路落地。 11:25：r29——档位真读 + 标签修复 + c1 口径修正。
  - 2026-10-14 11:45：r30/r31——四档映射齐全（1/2/3/224）、档位标签审计（part1–4 为常量）、一键同窗脚本（c3 通道 PASS 3.26%）；commits 4bebee2/154a5d1/508a17e/4f794a3/0237359。
