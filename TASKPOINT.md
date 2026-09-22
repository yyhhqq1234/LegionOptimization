# TASKPOINT — 项目级任务断点

> 保存时间：2026-09-22 16:01（UTC+8）
> 项目根目录：D:\LegionOptimization
> 分支/版本：master @ a7e19eb（远端已同步；tags：legion-legacy-b2、phase-00-done、phase-03-done）

## 1. 任务目标

- 一句话目标：推翻旧 Lenovo 静态调优胶水项目，重构为**通用笔记本功耗自适应调优系统**（Intel HX 全系 + RTX 40/50 Laptop，本地自训练小模型实时调优），作为人工智能专业毕设，约 16 周交付。
- 当前子目标（P4 A方案落地）：D_safe≥2000/机九宫格≥80% + 三模型对比 + 回放Return+10% shield不升 + ONNXv1<10MB<5ms + tag phase-04-done。
- 验收标准：
  - [x] P0 锁 v1.0（待签字项已过，P1–P3 实际已执行完毕）
  - [x] P1 E2 只读探针（gpu_baseline_A 775samples/780s）
  - [x] P2 E3 新开机时序（299s+202s 双轮）+ LKG staging（2/2 <60s，只读）
  - [x] P3 HAL L0–L3 + State48/Action7 + dry-run 45单测绿 + tag phase-03-done
  - [ ] P4 回放验收：相对 B2 基线 Return +10% 且 shield 不上升（合成BO仅+1.3%，真值待多格+perf标+E4/E5 live）
  - [ ] P4 九宫格≥80%（当前 1/16 W0/AC，全idle窄分布）
  - [ ] 跨机迁移：B 机 200 条 fine-tune 达从零训 90%（P5）
  - [ ] 影子五门禁 + 48h 金丝雀通过（P6/P7），论文初稿 + 答辩演示

## 2. 背景与现状

- 旧项目：Lenovo Legion Fn+Q 档位经 LLT + ThrottleStop 拷 INI + powercfg 的静态调优，
  已整体删除，冻结于 tag `legion-legacy-b2`（commit dc1dd67，可 `git show` 恢复，不可复活进工作树）。
- 验证双机：A 机本机 Y7000 2025（U7 255HX，TJMax=105°C / RTX 5060 Laptop / torch 2.11+cu128 sm_120）；
  B 机待上线（i9 14900HX + 5060）。
- 路线锁定：A 方案（监督代理模型 + 约束 BO，打底攒数据）→ B 方案（离线 RL，主 IQL，拔高）；
  M5 负载预测叠加；导师偏算法，方法章需 5 件套全厚度。
- 当前状态：P3 已封 tag，P4 合成链全通 + 影子实采进行中（part1 508 + part2 ~2327 + 锁文件，W0/AC单格）；
  live 因 E4/E5 门禁缺失继续锁定（用户小步确认 ΔPL≤5W/Δfreq≤100MHz 已记录，但铁律3要求门禁+确认双齐）。
- 约束：全程 dry-run 默认；门禁不过不真实下发；公开仓库，禁 force-push。
- 变更记录：2026-09-22 P4 从"合成验证"推进到"影子实采+合成压测"，STRESS合成行明确不进九宫格。

## 3. 总体计划

1. P0 E0/E1 评审锁 v1.0（已执行）→ P1–P3 已封版
2. P4（进行中）：D_safe 实采补格 + 三模型真数重训 + 回放Return+10% + ONNXv1 + tag phase-04-done
3. P5：跨微架构迁移实验，200 条达 90%，迁移效率曲线（论文图）
4. P6：五算法离线 RL 对比 + OPE + 影子五门禁 + M5 预测器
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
| 11 | P4 影子实采（采集中） | 单 Agent + 用户用机 | 进行中 | part1 508+part2 ~2327，1/16格；job活 |
| 12 | P4 补格/perf标/E4→Return+10%→tag | 用户 + 单 Agent | 待办 | 需真用机+拔电+E4/E5 |
| 13 | P5–P7 | 待定 | 待办 | 见 plans/ 各文件 |

## 6. 已完成步骤（已验证事实）

- [x] 只读分析：Fn+Q 双触发链、Boot 双轨、FIVR 五步、配置对照表、风险 Top；验证：t1–t5 报告归档，团队已删。
- [x] 开工准备 4 交付：规格/大纲/围栏/kickoff；验证：文件在仓。
- [x] 根目录清理：commit 6111aef（27 files，-2543 行）；验证：`git ls-files` 仅 5 项，tag legion-legacy-b2 可取回。
- [x] 删 4 Disabled 尸体任务；验证：复查零残留。
- [x] AGENTS/CLAUDE/README/LICENSE/.gitattributes/PR 模板；验证：commit 53be743 已推，8 milestone 已建。
- [x] P0 执行：G5 清零 5 处、正交 30 格、Reward 补 burst 惩罚；验证：commit 535081a + tag phase-00-done 双双在远端。
- [x] P1 E2：GPU 基线 775 samples/780s 只读；验证：artifacts/gpu_baseline_A.csv，P3回放50行零L2+误放行。
- [x] P2 E3：双重启 299s+202s PASS + LKG worktree 0.1s/readback 0.11s/PASS 0.08s 2/2 <60s（只读，quiet.bat未执行）；验证：commits e356fa8/ecbd6cb，docs/p2-e3-drill-report.md。
- [x] P3：State48/BlackBox/HAL_MAP/L2互斥/护栏/ACDC/MLP+Ensemble/dry-run V01-V09 p99 0.002ms；验证：pytest 45绿，commit 1562a62 + tag phase-03-done 已推。
- [x] P4 合成：A2000 16/16 + B1200 + 三模型（LGB 2.88/2.11/1.70 胜 MLP 3.23/2.94/1.74，ENS欠训如实记）+ ONNX 0.02MB/0.02ms + BO +1.3% shield平 + cross-AB；验证：commits 至 6e5e96a，samples 内JSON齐。
- [x] P4 B2锚：tag worktree只读提值，四bat+INI（worktree已清防污染），冻结值×代理算锚 mean71.4 p50 74.9，B0/B1实log缺记blocked；验证：commit ce69a6a，samples/reward_baseline_B2.csv 32行。
- [x] P4 干等价：B2四档全OK违例0 BlackBox 4/4；验证：commit fa54b88，samples/envelope_B2_dryrun.json。
- [x] P4 工具链：shadow 1Hz采集器（零写）+ 16格覆盖监测 + fps/p95预留（presentmon缺如实空）+ 交互探针（冷608ms/热88ms）+ 插拔watcher（status2/95%）；验证：commits 9dab39f/776e5ce/2217be7/cd1b2bd/0203702/c4d5b24。
- [x] P4 实试点：600行power0.19胜均值；n1147复跑power0.24输均值（窄idle天花板实证）；验证：commits 26c64d1/eb744c4/794c1d0，samples/real_pilot.json。
- [x] P4 合成压测：180s torch matmul有界，192行STRESS标 util3-100% power18.9-116W temp51-85C（峰值自限，已冷56C），实采暂停后已续，STRESS文件不进九宫格；验证：commit a7e19eb，datasets/D_stress_synth.csv（已ignore）。
- [x] P4 证据索引 + r26门禁对账；验证：commits 29c32ab/143b67a，docs/p4-evidence-index.md。
- [x] requirements 锁定：lightgbm 4.7.0 + onnx 1.23.0 + onnxscript；验证：pip安装成功，ONNX导出通。

## 7. 进行中 / 下一步（新对话先干这个）

- 当前卡点：实采全idle单格（1/16），无perf标（帧探针缺），E4/E5门禁缺 → live锁，Return真值待定。
- 下一步动作（可直接执行）：
  1. 用户真用机（游戏/办公/浏览器）+ 真拔电一次 → 覆盖率 `python tools/coverage_report.py` 看格数涨；
  2. 格≥13/16且perf标齐后，重跑 `tools/pilot_real_train.py` + 三模型真数对比；
  3. E4（影子≥8h有效覆盖）通过 + 用户确认 → 小步live（ΔPL≤5W/Δfreq≤100MHz/UV≤5mV）；
  4. Return+10% shield平 → 冻结D_safe快照 → tag phase-04-done。
- 待验证假设：B 机 BIOS 未锁欠压（若锁则P5改子空间迁移）；B 机 WMI Extreme mode 值（R4预案）。

## 8. 待办步骤

- [ ] 用户补格（W1–W7×AC/DC）+ 插拔事件 + PresentMon帧标
- [ ] E4影子门禁（≥8h有效覆盖）→ E5金丝雀 → 小步live
- [ ] 真数三模型重训 + Return+10%回放验证 + tag phase-04-done
- [ ] P5 跨机迁移（需B机上线）→ P6 离线RL → P7 金丝雀+论文
- [ ] 附带小事：`watcher.lock`（0字节）重启后随手删；LICENSE权利人占位 `yyhhqq1234`，毕设要真名则改。

## 9. 雷区（进行时必须避开）

- 现象/坑：`watcher.lock` 删不掉；原因：被 Session-0 进程长期持有；正确做法：不管它（已 gitignore），新实现用 `hal-actuation.lock` + PID 校验。
- 现象/坑：`schtasks /delete` 报 Access denied；原因：shell 非提权；正确做法：`-Verb RunAs` 弹 UAC 用户点是。
- 现象/坑：计划任务路径禁空格；原因：`D:\Intel降压定频 .exe` 被截断致 0x80070002；正确做法：新项目路径/文件名禁空格禁中文。
- 现象/坑：误删外部参照；原因：`D:\Intel降压定频 .exe` + `D:\undervolt_config.json` 是手动对比基线；正确做法：只读不碰。
- 现象/坑：温度阈值写死跨机翻车；原因：255HX TJMax=105，14900HX 未知；正确做法：运行时读 MSR 0x1A2 生成相对偏移。
- 现象/坑：术语混淆（已踩两轮）；原因：口径；正确做法：W0–W7负载 ≠ M1–M8模块，G0–G4唯一档，DC正交，**G5禁词**。
- 现象/坑：B2 基线复活污染工作树；原因：验证需旧脚本；正确做法：只许 worktree/archive 到临时目录，用完删，`git status` 复核。
- 现象/坑：edit 报 "file has not been read"；原因：工具要求本会话先 read；正确做法：先 read 再 edit。
- 现象/坑：CRLF warning 刷屏；原因：跨平台换行；正确做法：`.gitattributes text=auto`，不许全仓改行尾。
- 现象/坑：pwsh5.1 不支持 `&&`；原因：旧版语法；正确做法：用 `;` 连接，`Select-Object` 收尾。
- 现象/坑：中文被 dotNET UTF8 改写 corrup（U+FF1A SyntaxError）；原因：pwsh 写文件编码；正确做法：源码/测试全ASCII，中文只进文档。
- 现象/坑：`cat file | python` JSONDecodeError；原因：pwsh cat 出对象非纯文本；正确做法：python内 open() 读。
- 现象/坑：pip resolver 冲突（numpy 2.5.3 vs albucore/paddleocr系）；原因：旧依赖钉死；正确做法：pip直接装（lgbm/onnx成功），requirements只记新增。
- 现象/坑：torch.onnx导出报 gbk 编码错；原因：控制台代码页；正确做法：`chcp 65001` + PYTHONUTF8=1。
- 现象/坑：pip install 卡代理502；原因：github→127.0.0.1本地代理阵发；正确做法：等60s重推即通，本地commit排队不丢。
- 现象/坑：影子CSV混列（70行错位）；原因：杀job后句柄未放+双写；正确做法：repair脚本按header宽过滤归档part1，新schema另起part2（`--out`）。
- 现象/坑：锁文件删不掉（WinError 32）；原因：残留句柄；正确做法：不硬删，换新文件续采（part2），旧文件冻结。
- 现象/坑：合成行污染真数；原因：压测时实采job在跑；正确做法：压测前停实采job，合成行写D_stress_*（STRESS标，不进覆盖glob），事后声明+重启实采。
- 现象/坑：单格窄分布训不出东西（n1147输均值）；原因：idle方差太小；正确做法：多格是硬需，不拿合成冒充。

## 10. 关键文件与修改

- `AGENTS.md` / `CLAUDE.md`：agent 协议（canonical + Claude约定）。
- `specs/SYSTEM_SPEC_DRAFT_v1.0.md`：HAL/State48/Action7/Reward/包络（v1.0冻结）。
- `docs/safety-fence-spec.md`：门禁细则；`docs/thesis-proposal-outline.md`：V01–V24矩阵。
- `src/state/state48.py`：State48构建（fill 0.167实测）；`src/blackbox/log.py`：BlackBox环。
- `src/actuate/hal_map.py` + `src/actuate/l2_mutex.py`：档位换算 + 互斥（live门禁前拒绝）。
- `src/guard/`：burst/shields/acdc；`src/policy/surrogate.py`：MLP+Ensemble（ASCII）。
- `tools/run_p3_dryrun.py`：V01–V09；`tools/collect_shadow.py`：影子1Hz（15列，fps/p95预留，`--out`）。
- `tools/coverage_report.py`：16格监测（读全parts）；`tools/repair_shadow.py`：混列修复归档。
- `tools/make_dsafe_synth*.py` + `tools/train_p4_*.py` + `tools/bo_p4_synth.py` + `tools/cross_AB_synth.py`：合成链。
- `tools/reward_baseline_B2.py`：V12 B2代理锚；`tools/pilot_real_train.py`：实试点。
- `tools/gpu_stress.py`：有界合成负载（STRESS标，off-grid）；`tools/interactive_probe.py`：交互探针；`tools/plug_watch.py`：插拔watcher。
- `docs/p4-collection-protocol.md` + `docs/p4-progress-synth.md` + `docs/p4-evidence-index.md` + `docs/p4-gate-report.md`：P4文档链。
- `docs/p2-e3-drill-report.md` + `docs/hal-boot-sequence.md`：P2证据。
- `artifacts/samples/`：合成AB、对比JSON、ONNX(0.02MB)、B2锚、包络、pilot等小样例（可进仓）。
- `artifacts/datasets/`：实采大CSV（已ignore，永不进仓）：part1/part2/锁文件/D_stress。
- 已废弃（tag可取回）：全部旧 `.bat/.ps1`、`ThrottleStop/` 等 legacy。

## 11. 验证方式

- 仓库干净：`git status --porcelain` 空；远端同步：`git push` 通（502阵发则等60s重推）。
- 阶段验收：按 `plans/PHASE-0x` §4 checklist 逐项贴证据，不许空勾；产物缺失 = 该格未执行。
- 测试：`pytest tests/` 45绿；覆盖：`python tools/coverage_report.py` 看16格。
- 门禁：影子≥8h/金丝雀48h/自动回滚五触发/LKG 60s；live需门禁+用户确认双齐。
- 模型指标：回放 Return +10%（P4）、迁移 200 条达 90%（P5）。

## 12. 恢复指令

- 新对话打开本项目后执行 `/resume`，Agent 将读取本文件并从"§7 下一步"继续。

---

- 更新历史：
  - 2026-09-16：初建（P0待签字）。
  - 2026-09-22 16:01：大更新——P1/P2/P3封版（tags+03），P4合成链+实采+压测，门禁对账（rows-OK/grid-OPEN），live锁E4/E5。
