# TASKPOINT — 项目级任务断点

> 保存时间：2026-09-16（UTC+8）
> 项目根目录：D:\LegionOptimization
> 分支/版本：master @ 535081a（远端已同步；tags：legion-legacy-b2、phase-00-done）

## 1. 任务目标

- 一句话目标：推翻旧 Lenovo 静态调优胶水项目，重构为**通用笔记本功耗自适应调优系统**（Intel HX 全系 + RTX 40/50 Laptop，本地自训练小模型实时调优），作为人工智能专业毕设，约 16 周交付。
- 验收标准：
  - [ ] P0–P7 阶段计划全部按验收 checklist 关闭（当前：P0 已执行，待用户签字）
  - [ ] 相对 B2 基线 Return +10% 且 shield 不上升（P4 回放验收）
  - [ ] 跨机迁移：B 机 200 条 fine-tune 达从零训 90%（P5）
  - [ ] 影子五门禁 + 48h 金丝雀通过（P6/P7），论文初稿 + 答辩演示

## 2. 背景与现状

- 旧项目：Lenovo Legion Fn+Q 档位经 LLT + ThrottleStop 拷 INI + powercfg 的静态调优，
  已整体删除，冻结于 tag `legion-legacy-b2`（commit dc1dd67，可 `git show` 恢复，不可复活进工作树）。
- 验证双机：A 机本机 Y7000 2025（U7 255HX，TJMax=105°C 已确认 / RTX 5060 Laptop / torch 2.11+cu128 sm_120 可用）；
  B 机待冻结（i9 14900HX + 5060，E2 探测：BIOS 欠压锁状态、WMI mode 值、TJMax 实测未知）。
- 路线锁定：A 方案（监督代理模型 + 约束 BO，打底攒数据）→ B 方案（离线 RL，主 IQL，拔高）；
  M5 负载预测叠加；导师偏算法，方法章需 5 件套全厚度。
- 当前状态：前期准备 + 仓库初始化 + **P0 已执行完毕待签字**；V09+ 排期资格待签字解锁，G4 真实下发继续锁定。
- 约束：全程 dry-run 默认；门禁不过不真实下发；公开仓库（github.com/yyhhqq1234/LegionOptimization），禁 force-push。

## 3. 总体计划

1. P0 E0/E1 评审锁 v1.0（已执行，待签字）→ 解锁 V09+
2. P1 E2：B 机冻结 + 只读探针 + requirements.txt（B 机需上线 1–2 天）→ 解锁 B 列
3. P2 E3：新开机时序 + LKG 回滚演练（A2 <60s）→ 解锁 V22–V24
4. P3：HAL L0–L3 + 采集器 + State48/Action7，V01–V09 dry-run（零真实写入）
5. P4：D_safe（双机 2000–4000 条/机）+ 三模型对比 + 约束 BO，Return +10%
6. P5：跨微架构迁移实验，200 条达 90%，迁移效率曲线（论文图）
7. P6：五算法离线 RL 对比 + OPE + 影子五门禁 + M5 预测器
8. P7：48h 金丝雀 + B 机 24h 交叉 + V closure + 论文答辩（G4 真实下发最后放行）

## 4. 团队模式

- 是否采用团队模式：**否（当前单 Agent 执行）**。
- 历史团队（均已完成并归档删除，无需唤醒）：
  - `legion-readonly-analysis`（只读分析：arch-mapper/t1 架构、script-auditor/t2 脚本审计、
    config-checker/t3 配置核对、risk-reviewer/t4 风险、t5 汇总；结论已沉淀进规格与汇总文档）
  - `legion-rebuild-prep`（开工准备：spec-architect/p-spec、thesis-writer/p-thesis、
    env-auditor/p-env、safety-planner/p-safety、p-synth 汇总；交付物为 specs/docs 现有文件）
- 后续如需并行（如 P3 多模块实现、P6 多算法训练），新建团队，任务 id 重新编号（旧 id 不复用）。

## 5. 步骤规划

| # | 步骤 | 负责人 | 状态 | 备注 |
|---|------|--------|------|------|
| 1 | 只读分析旧项目 | 单 Agent + 团队 | 已完成 | 结论沉淀规格/汇总 |
| 2 | 开工准备 4 交付（规格/大纲/环境/围栏+汇总） | 团队 | 已完成 | specs/docs 现有文件 |
| 3 | 根目录清理 + tag + push + 删 4 尸体任务 | 单 Agent | 已完成 | commit 6111aef；任务已删 |
| 4 | AGENTS/CLAUDE + 仓库初始化（README/LICENSE/PR模板/description/topics/里程碑P0-P7） | 单 Agent | 已完成 | commit 53be743 |
| 5 | P0 执行（Step 0-1/0-2/0-3，规格 v1.0 冻结） | 单 Agent | **进行中（待用户签字）** | commit 535081a + tag phase-00-done 已推 |
| 6 | P1 E2 探针 | 待定 | 待办 | 需 B 机上线 1–2 天 |
| 7 | P2 E3 时序+LKG | 待定 | 待办 | — |
| 8 | P3–P7 构建训练放量论文 | 待定 | 待办 | 见 plans/ 各文件 |

## 6. 已完成步骤（已验证事实）

- [x] 只读分析：Fn+Q 双触发链、Boot 双轨、FIVR 五步、配置对照表（FIVR 解码吻合）、风险 Top（Session0/竞态/静默失败实证）；验证：t1–t5 报告归档，团队已删。
- [x] 开工准备 4 交付：`specs/SYSTEM_SPEC_DRAFT_v1.0.md`（后由 P0 更名冻结）、
  `docs/thesis-proposal-outline.md`、`docs/safety-fence-spec.md`、`docs/kickoff-readiness-summary.md`；验证：文件在仓。
- [x] 根目录清理：删全部 legacy（.bat×7/.ps1×7/ThrottleStop/配置/automation.template/README/TASK_PROGRESS/日志）；
  改动：commit 6111aef（27 files，-2543 行）；验证：`git ls-files` 仅 5 项，`git push` 远端确认，tag legion-legacy-b2 可 `git show` 取回。
- [x] 删 4 Disabled 尸体任务（LegionProfile/LegionUpdate/LegionGpuSwitch/ThrottleStop_NoUAC）；
  改动：提权 shell `schtasks /delete`；验证：复查查询零残留。
- [x] AGENTS.md/CLAUDE.md/README.md/LICENSE(MIT)/.gitattributes/PR 模板；改动：commit 53be743；
  验证：已推远端；`gh repo view` 确认简介 + 7 topics；8 个 milestone（P0–P7）已建。
- [x] P0 执行：W 命名零残留、G5 清零 5 处、正交视图补 G0（30 格）、Reward 补 `−w_burst·B_viol`、
  Burst 通用值作废、C5 关闭、E1-1–E1-6 全勾、规格更名 v1.0 冻结；
  改动：commit 535081a（7 files，含 rename 94%）+ tag phase-00-done；验证：双双 `ls-remote` 在远端，工作树干净。

## 7. 进行中 / 下一步（新对话先干这个）

- 当前卡点：P0 验收单最后一项“验收人签字（用户本人）”未签；V09+ 仍冻结，G4 真实下发锁定。
- 下一步动作（可直接执行）：用户回复“签/确认”后——
  1. 把 `plans/PHASE-00-e0e1-review.md` §4 剩余两框打勾（含 tag 已存在证据），commit + push；
  2. 宣布 V09+ 解锁，按 `plans/PHASE-01-e2-probes.md` Step 1-1 启动 P1（先要 B 机上线）。
- 待验证假设：B 机 BIOS 未锁欠压（若锁则 B 机 mask 电压维，P5 改子空间迁移，结论照写）；
  B 机 WMI Extreme mode 值是否为 224（若不是则 R4 预案）。

## 8. 待办步骤

- [ ] P0 签字关闭（见 §7）
- [ ] P1 E2：B 机冻结建档、WMI 抓包、FIVR/MSR 只读探针、GPU 基线、requirements.txt（`docs/env-inventory.md` 落盘）
- [ ] P2 E3：新开机时序、LKG staging 恢复演练（A2 <60s）、V23 烟囱重写
- [ ] P3–P7：见 `plans/` 各文件验收单
- [ ] 附带小事：`watcher.lock`（0 字节，被 Session-0 未知进程持有）重启后随手删；
  LICENSE 权利人占位 `yyhhqq1234`，毕设要真名则改。

## 9. 雷区（进行时必须避开）

- 现象/坑：`watcher.lock` 删不掉（"used by another process"）；原因：被某 Session-0 进程长期持有，
  跨会话 cmdline 不可见无法坐实（候选 Steam++ 7:05 拉起的 powershell）；正确做法：不管它（已 gitignore），
  新实现禁用旧锁名换 `hal-actuation.lock` + PID 存活校验，禁止抢锁失败静默 exit 0。
- 现象/坑：`schtasks /delete` 报 Access denied；原因：当前 shell 非提权；正确做法：走 `-Verb RunAs` 弹 UAC，
  用户点“是”（已验证可行），输出重定向到 %TEMP% 再读回。
- 现象/坑：计划任务路径禁空格；原因：`IntelUndervoltApply` 的 `D:\Intel降压定频 .exe` 被 XML 按空格截断，
  常年 0x80070002 跑不起来；正确做法：新项目一切路径/文件名禁空格禁中文。
- 现象/坑：误删外部参照；原因：`D:\Intel降压定频 .exe` + `D:\undervolt_config.json` 是用户定的手动对比基线；
  正确做法：只读不碰，E2 登记为外部 MSR 写入者（其 -50mV 恰与 G1 同值，有参照意义）。
- 现象/坑：温度阈值写死会跨机翻车；原因：255HX TJMax=105，14900HX 未知；正确做法：运行时读 MSR 0x1A2 生成相对偏移。
- 现象/坑：术语混淆导致矩阵无法排期（已踩过两轮）；原因：大小写/维度口径；正确做法：W0–W7 负载 ≠ M1–M8 模块，
  G0–G4 唯一档，DC 永远正交，**G5 是禁词**。
- 现象/坑：B2 基线复活污染工作树；原因：验证需要旧脚本；正确做法：只许 `git worktree add`/`git archive` 到 staging 临时目录，
  用完删除，复核 `git status` 干净。
- 现象/坑：edit 报 "file has not been read"；原因：工具要求本会话先 read；正确做法：先 read（可 limit/offset）再 edit。
- 现象/坑：`present` 一次最多 8 个文件；原因：工具限制；正确做法：分批 present。
- 现象/坑：CRLF warning 刷屏；原因：跨平台换行；正确做法：已有 `.gitattributes text=auto`，不许全仓改行尾。
- 现象/坑：LLT 的 `automation.json` 含旧路径引用；原因：历史导入残留；正确做法：它 `IsEnabled=False` 且 LLT 未运行，
  不碰；V23 烟囱含义 P2 重写时一并处理。

## 10. 关键文件与修改

- `AGENTS.md`：新建，agent 工作协议（canonical）。
- `CLAUDE.md`：新建，Claude 专属约定（指向 AGENTS.md）。
- `README.md`：重写，重构愿景 + 状态 + 结构（旧版随 legacy 删除）。
- `LICENSE`：新建，MIT（权利人暂填 yyhhqq1234，占位）。
- `.gitattributes` / `.gitignore` / `.github/pull_request_template.md`：新建/更新（换行、pid、.agent-teams）。
- `specs/SYSTEM_SPEC_DRAFT_v1.0.md`：由 v0.1 更名冻结；P0 增补 burst 惩罚项、作废通用 Burst 值、G4=95、TJMax 条款。
- `docs/thesis-proposal-outline.md`：P0 补丁（G5→DC正交 5 处、正交视图 30 格、C5 关闭）。
- `docs/safety-fence-spec.md`：头注 v1.0 冻结。
- `docs/kickoff-readiness-summary.md`：§5 索引更新 + §6 清理决策追记。
- `plans/README.md` + `plans/PHASE-00..07`：新建，阶段计划（P0 的 E1 表已全勾）。
- 已废弃（tag 可取回，不在工作树）：全部旧 `.bat/.ps1`、`ThrottleStop/`、`automation.template.json`、旧 README/TASK_PROGRESS。

## 11. 验证方式

- 仓库干净：`git status --porcelain` 空；远端同步：`git ls-remote origin` 含 master 与 tag（legion-legacy-b2、phase-00-done）。
- 阶段验收：严格按 `plans/PHASE-0x` §4 checklist 逐项贴证据，不许空勾；产物缺失 = 该格未执行。
- 门禁：影子≥8h/金丝雀48h/自动回滚五触发/LKG 60s，细则见围栏规格 §5–§6。
- 模型指标：回放 Return +10%（P4）、迁移 200 条达 90%（P5）、影子五门禁（P6），见各阶段文件。

## 12. 恢复指令

- 新对话打开本项目后执行 `/resume`，Agent 将读取本文件并从"§7 下一步"继续。
