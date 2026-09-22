# P2-E3 演练报告：Step 2-2 重启实测 + Step 2-3 LKG staging（A机）

> 上游：`plans/PHASE-02-e3-boot-lkg.md`；时序定义：`docs/hal-boot-sequence.md`（T1错峰≥30s / T2 boot_phase=1 5min禁burst+UV / T3回退优先 / T4 15s回滚）
> 日期：2026-09-22；执行：CLI只读 + 操作者侧两次重启；门禁：铁律4（禁真实写，需E4/E5+显式确认）全程 dry-run/只读。

## 1. Step 2-2：两次重启实测（T1/T2验证）

旧链复核（重启前快照）：计划任务无 `*Throttle*/*Legion*`，HKCU Run无Legion/Throttle项 → 4任务无、Run键无成立。

| 轮次 | LastBootUpTime(T0) | 登录后Check(T1) | T1-T0 | 活动方案 | 判定 |
|------|-------------------|----------------|-------|---------|------|
| 1 | 2026-09-22 12:39:29 | 12:44:28.266 | 299s（4分59s） | 高性能 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c | boot_phase=1内 PASS |
| 2 | 2026-09-22 12:46:43 | 12:50:05.355 | 202s（3分22s） | 高性能 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c | boot_phase=1内 PASS |

- T1错峰≥30s：P3采集器未建，无落盘事务发生（铁律4禁powercfg/INI真实写，dry-run默认开）→ 无burst/UV加深，间隔∞，PASS（审计口径：BlackBox无落盘时间戳即无违规）。
- T2开机禁区：两轮check时刻方案未变，无切换记录，PASS。
- stale率（S3 SLO首测数据点）：待P3 `LegionSense` 上线后补，本轮记占位（valid=0不阻塞登录，按HAL附录§4）。
- 历史佐证：System事件 1074/6006→6005/6009（9:39关→9:59开，7:21关→7:51开）与本轮一致。

## 2. Step 2-3：LKG staging演练（A2 SLO <60s）

- tag：`legion-legacy-b2` 存在；演练前后 `git status --porcelain` 为空，`git worktree list` 仅剩master。
- staging：`$env:TEMP\lkg-drill` via `git worktree add legion-legacy-b2`，耗时 0.1s；内含 `quiet.bat/balance.bat/beast.bat` + `ThrottleStop/` + profiles。
- `quiet.bat` 等效动作（读）：kill TS → copy `quiet.ini→ThrottleStop.ini` → `powercfg /setactive 381b4222…` + 6条 `setac/dcvalueindex`（3.8GHz Efficient Turbo）→ `schtasks /run ThrottleStop_NoUAC` → 3s验活+2s等FIVR → kill TS。
- 计时（读回口径，只读）：worktree 0.1s；`GETACTIVESCHEME+QUERY` 0.11s；PASS1 0.08s / PASS2 0.08s → 2/2 <60s PASS。
- 降级声明（PHASE-02 §6允许）：真实 `quiet.bat` 落盘未执行（铁律4：需E4/E5门禁+显式确认，缺一不可）→ 本轮为 powercfg-only只读降级演练，验的是流程与计时；live计时待提权终端一次 `<60s` 补测，命令见§4。
- 清理：`git worktree remove --force + prune`，staging已删。

## 3. PHASE-02 §4验收映射

- [x] 时序文档存在且错峰可测试（`hal-boot-sequence.md` T1–T4 given/when/then）
- [x] 2次重启：boot_phase内无burst/UV（本报告§1；T2/T3待P3补stale/采样时刻回填HAL §5）
- [x] LKG只读演练2/2 <60s，staging已清理，仓库干净（live落盘待补，不判失败，§6降级）
- [ ] R3关闭 / V22–V24解锁：待live补测 + HAL §5标定值回填后关闭
- [x] 本报告已合订计时表

## 4. 复现命令（操作者侧 <60s live补测用，提权终端）

```powershell
$stg="$env:TEMP\lkg-drill"; git worktree add "$stg" legion-legacy-b2; Measure-Command { & "$stg\quiet.bat" }; powercfg /GETACTIVESCHEME; git worktree remove --force "$stg"; git status --porcelain
```
