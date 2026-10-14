# P4 Gate Report — r27（2026-10-14）

> 本文件按 AGENTS §9.2（M 级改动：先记后做）记录本轮工具/口径改动与前后对比数据。
> 涉及工具：`tools/coverage_report.py`、`tools/collect_shadow.py`、`tools/fps_join.py`（新增）。

## 1. 口径修正：coverage 双计（先记后做，已做）

- 现象：`coverage_report.py:14` 的 glob `D_safe_shadow_A*.csv` 同时匹配分片与历史总表。
- 前：`rows 83234`（分片 48753 + 总表 34481，其中 10352 个 (ts,work,acdc) 键重复）→ 虚增 70.7%。
- 后：分片净行 **48753**；`interactive_ratio` 0.083 → **0.142**（重复的 W0 行不再稀释分母）。
- 处置：总表移入 `artifacts/datasets/archive/D_safe_shadow_A_tot_20260922.csv`（15:18–20:26，非独立采集）；
  统计器改为只读 `*_part*.csv`，顶层再出现 rollup 时打印 WARN 并排除（防回归）。
- 影响 V 格：D_safe 规模口径（§2 数据量），不影响 3/16 格数与任何门禁阈值。

## 2. 工具修复（已做，前后数据）

| 项 | 前 | 后 |
|---|---|---|
| nvidia-smi 采集 | `which` 失败（617.14 驱动刷新后离开 PATH）→ 续采将写入空值行 | `find_nvidia_smi()` 回落 DriverStore（`nvlti.inf_amd64_...\nvidia-smi.exe`，驱动 617.14，实测读 util/clocks/power/temp 正常） |
| 顶层 rollup 误计 | 无告警，静默双计 | WARN + 排除 |
| 帧标入口 | 注释声称有 `--fps-file`，实际未实现（注释≠代码） | 已实现 `--fps-file/--fps-process/--fps-reload` + 新增 `tools/fps_join.py` |

## 3. 帧标链路（本轮打通，可复现证据）

- 工具：PresentMon **2.6.0** 便携 exe（`tools/presentmon/PresentMon-2.6.0-x64.exe`，980KB，**不装系统**，gitignore）。
- 约束（路径记录）：PresentMon 录制期**独占**输出 CSV，并发读报 `[Errno 13] Permission denied`；
  改走等价路径 = 录制期并行采集（fps 留空）+ 停止后离线回填。
- 实测（smoke，未进真数）：`fps_join.py` 回填 **16/16 行**，`fps 45.5–178.0`、`p95 6.0–6.1ms`、
  `power 4.00–4.03W`、`temp 41C`（dwm 桌面合成帧）。
- 已知偏移：PresentMon `--date_time` 在本机恒定 `-28796.9s`（+8h 时钟偏移），由"重定基到采集起点"抵消；
  `fps_join.py` 会打印偏移量，偏移异常（非同时启动）时可 `--offset` 手工校正。
- 生产命令：`--fps-process game.exe` 必填，避免 dwm.exe 桌面帧污染游戏格。

## 4. E4 缺口矩阵（影子门禁：≥8h 有效覆盖 = 游戏≥2h + 办公≥2h + idle≥1h + ≥1 次插拔电）

| 要求 | 实测现状 | 判定 |
|---|---|---|
| idle ≥1h | W0/AC 34944 行 = **9.71h** | ✅ |
| 办公 ≥2h | W1/AC 6902 行 = **1.92h** | ⚠️ 差 ~5 分钟 |
| 游戏 ≥2h | W2/AC 6907 行 = **1.92h** | ⚠️ 差 ~5 分钟 |
| ≥1 次插拔电 | `plug_events.csv` 仅 `watch-start`（status2/95%），无真实插拔事件 | ❌ 缺 |
| 影子 run（策略只推理不下发 + 围栏试算 + BlackBox 全记） | 采集器仅记遥测；`shadow_pilot.json` 只有 util/power/temp 统计，无一致率/跳闸/流畅判据 | ❌ **未实现（本缺口不是靠继续采集能补的）** |
| E4 四项判据（一致率≥85% / L2+试算=0 / p95±5% / 零崩溃） | 无统计脚本与产物 | ❌ 缺 |

结论：**E4 的瓶颈从"采集时长"转为"影子 run 链路未实现"**。W1/W2 各差 5 分钟属用户侧举手之劳，
但即使时长齐、格齐，没有影子 run + 四项判据脚本仍过不了 E4。

## 5. 下一步命令（可直接执行）

```powershell
# ① 帧标采集（三位一体：PresentMon 并行 + 采集器 + 回填）
$pm  = '.\tools\presentmon\PresentMon-2.6.0-x64.exe'
$pmcsv = 'artifacts\datasets\pm_W2_<date>.csv'
Start-Process $pm -ArgumentList '--timed','7200','--session_name','PMW2','--output_file',$pmcsv,
  '--date_time','--terminate_after_timed','--no_console_stats' -WindowStyle Hidden
python tools\collect_shadow.py --seconds 7200 --work W2 --acdc AC `
  --out artifacts\datasets\D_safe_shadow_A_part5.csv
& $pm --terminate_existing_session --session_name PMW2        # 或等 --timed 自然结束
python tools\fps_join.py --shadow artifacts\datasets\D_safe_shadow_A_part5.csv `
  --pm $pmcsv --process <game.exe>

# ② 办公格补 5 分钟 + 新格轮转（W3 compile / W4 video-call / W5 render / W6 browser / W7 plug-flap）
python tools\collect_shadow.py --seconds 600 --work W1 --acdc AC --out artifacts\datasets\D_safe_shadow_A_part5.csv

# ③ DC 列（正交维度，需真拔电；顺带满足 E4 的"≥1 次插拔电"）
python tools\collect_shadow.py --seconds 3600 --work W0 --acdc DC --out artifacts\datasets\D_safe_shadow_A_part6.csv

# ④ 覆盖复核（口径已修）
python tools\coverage_report.py
```

## 6. 待办（下一轮，E4 实质缺口）

- [ ] `tools/shadow_run.py`：每 tick 同时 ① 遥测 ② surrogate 策略推理（`src/policy/surrogate.py`）
      ③ 围栏试算（`src/guard/*`）④ BlackBox 记录（`src/blackbox/log.py`）—— 全程 dry-run，不下发。
- [ ] `tools/e4_shadow_report.py`：一致率 / L2+ 试算触发 / p95 差 ±5% / 零崩溃 四项统计。
- [ ] 补 W1/W2 各 5 分钟 + DC 列 + 真实插拔事件（`tools/plug_watch.py` 已就绪）。
