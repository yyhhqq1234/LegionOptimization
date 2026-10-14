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

## 6. E4 影子链路（r28 已实现，实测证据）

两个新工具把 E4 从"只能判时长"变成"能判四项判据"：

| 工具 | 职责 | 实测证据 |
|---|---|---|
| `tools/shadow_run.py` | 每 tick：① nvidia-smi 遥测 ② **真读** AC/DC（`GetSystemPowerStatus`，非标签）③ powercfg 活动方案（在运基线信号）④ State48 ⑤ stub 策略 → Action7（`hal_map`）⑥ 围栏试算（`shields.judge`）⑦ `l2_mutex.actuate(dry_run=True)`——唯一路径，live 直接 raise ⑧ BlackBox 12 字段 + JSONL/summary | 10 ticks：`blackbox 10/10 complete`、`errors 0`、`timeouts 0`、围栏 OK×10（0.0103ms）、`l2_mode="dry-run"`、`acdc="AC"`(真读) `soc 96%` `scheme="节能"` |
| `tools/e4_shadow_report.py` | 四项判据（一致率 / L1+/L2+ 试算 / p95±5% / 零崩溃）+ E4 覆盖矩阵与插拔计数 + `open_items` | 见下 |

**判据实测（smoke，非有效样本）**

| 判据 | 结果 |
|---|---|
| c1 动作一致率 ≥85% | 无映射 → `BLOCKED`（宁可 BLOCKED 不假 PASS）；带 `--gear-map "节能=Quiet,平衡=Balance"` → `FAIL, agreement_rate 0.0, counted_rows 6`——影子建议 Balance，在运为 Quiet（真实分歧，正是 E4 要看的东西） |
| c2 试算跳闸（L2+ 必须 0） | `PASS`，L2+ = 0，L1+ rate 0.0 |
| c3 流畅中性 p95±5% | `BLOCKED`（影子行无帧标；需 `--fps-file` 同窗） |
| c4 零崩溃 | `PASS`，errors 0 / 预算超时 0 / 慢 tick 0 |
| 覆盖矩阵 | idle W0/AC 9.71h `PASS`；办公 W1 1.92h / 游戏 W2 1.92h `SHORT`；插拔 0 |
| `e4_ready` | `false`，`open_items = [c1, c3, coverage/plug hours short]` |

**诚实标注（写进每一行，不补齐）**：CPU 温度通道 pre-E5 不存在 → 围栏输入用 GPU 温度作 `cpu_temp_src="proxy-gpu"` 代理；
`gear_actual="uncalibrated-scheme-only"`；`policy_ver="stub-1"`（无策略权重，请求 `--policy surrogate` 记 `BLOCKED-no-policy-weights`）；
State48 `fill_rate 0.125`（只剩 GPU 侧有效位，CPU/mem 标缺失 valid=0）。

## 7. 剩余解锁路径（E4 从 false 到 true）

```powershell
# ① 校准 scheme -> gear 映射（用户按 Fn+Q 循环四档，同时跑这条看方案名）
1..40 | ForEach-Object { $s=(powercfg /GETACTIVESCHEME); $s.Substring($s.IndexOf('(')+1).TrimEnd(')'); Start-Sleep 2 }
#    拿到四档方案名后： --gear-map "节能=Quiet,平衡=Balance,性能=Beast,极致=Extreme"

# ② 影子 run + 帧标同窗（PresentMon 并行，见 §3）
$pmCsv='artifacts\datasets\pm_shadow_W2.csv'
Start-Process .\tools\presentmon\PresentMon-2.6.0-x64.exe -ArgumentList '--timed','7200',
  '--session_name','PMSh','--output_file',$pmCsv,'--date_time','--terminate_after_timed','--no_console_stats' -WindowStyle Hidden
python tools\shadow_run.py --seconds 7200 --work W2 --fps-file $pmCsv --fps-process <game.exe> `
  --out artifacts\samples\e4_shadow_W2_20261014.jsonl
python tools\fps_join.py  --shadow artifacts\datasets\D_safe_shadow_A_part5.csv --pm $pmCsv --process <game.exe>
python tools\e4_shadow_report.py --gear-map "节能=Quiet,平衡=Balance,性能=Beast,极致=Extreme" `
  --baseline-p95 <只读基线窗口的 p95>
```

- [ ] Fn+Q 四档校准走一遍（拿到 scheme→gear 映射，解锁 c1）
- [ ] 影子 run 与 PresentMon 同窗（解锁 c3）
- [ ] 补 W1/W2 各 5 分钟 + DC 列 + 真实插拔事件（覆盖与插拔项，`tools/plug_watch.py` 已就绪）
- [ ] CPU 温度通道（MSR/签名驱动）——pre-E5 只能 proxy，属已知局限，E5 前不解除

