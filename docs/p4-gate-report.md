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

## 8. r29：档位真读打通（Lenovo ACPI-WMI）+ c1 口径修正

### 8.1 实测（决定性）

- 现象：机器在**野兽模式**，但 `powercfg /GETACTIVESCHEME` 仍报 **"节能"**（d509f0cb-…）
  → Fn+Q 档位不跟随 Windows 电源方案，r28 的 `scheme → gear --gear-map` 路线作废。
- 解法：`root\WMI: LENOVO_GAMEZONE_DATA` 暴露 **out 参数**类方法，**空参数**调用即返回机器真实状态：

| 方法（空参调用） | 返回 | 含义 |
|---|---|---|
| `GetThermalMode` | **3** | 操作者确认当前为野兽模式 → **3 = Beast** |
| `GetSmartFanMode` | 3 | 与档位联动 |
| `GetCpuFrequency` | 340792400 | ×10 = **3.407924 GHz** |
| `GetProductInfo` / `GetVersion` / `GetPowerChargeMode` | 100 / 17 / 1 | 机型 ID / 固件版本 / 充电模式 |
| `GetCPUTemp` / `GetGPUTemp` | 0 | ACPI 未提供 → **不可当温度用**（CPU proxy 局限仍在） |

- 传 `Data` 参数会报"无效的参数"（该参数 qualifier `out=True`，ID=0，Description="Real Thremal Mode"）。
- `GetThermalMode` 连读 3 次稳定；COM(win32com) 单次 ≈263ms，PowerShell 回退 ≈320ms；`read_all()` 十项 ≈2.6s（故影子每 tick 只读档位，CPU 频率每 10 tick 一次）。
- 只读边界：本类同时存在 `Set*`（SetSmartFanMode / SetFanCooling / SetBIOSOC …），**本项目一律不调用**，新增 `src/sense/lenovo_wmi.py` 只封装 Get*/Is*。
- 新增映射表 `MODE_TO_GEAR={3:"Beast"}`，未映射档位原样写 `mode:<n>`（不猜）。

### 8.2 数据标签质量修复

- 此前 `gear_readonly` 列写的是**命令行硬标签**（`Balance-readonly`），与真实档位无关 ——
  这会污染 D_safe 标签与 E4 证据。
- 现 `collect_shadow.py --sense-gear` 写入真读档位；实测：`W0 | AC | Beast`。

### 8.3 c1 口径修正（诚实性）

- fence §5.3 原文：一致率 = **影子策略 vs 在运策略**（同一状态下档位输出），不是"vs 机器人工档位"。
- 本机只有一个策略版本（stub-1），自比无意义 → c1 = `BLOCKED-no-second-policy`（P6 引入新逻辑后才可算）。
- "策略建议 vs 人工档位"降级为观察项 **c1b**（`OBSERVED`，不计入 `e4_ready`）：实测 6 行 rate 0.0（stub 建议 Balance vs 人工 Beast）。

### 8.4 校准走档（2026-10-14 完成，四档齐全）

操作者按 Fn+Q 走一圈 + 即时读数，实测映射（每档连读 3 次稳定，probe 日志同步无丢点）：

| thermal_mode | gear | 官方叫法 |
|---|---|---|
| 1 | Quiet | 安静模式 |
| 2 | Balance | 均衡模式 |
| 3 | Beast | 野兽模式 |
| 224 (0xE0) | Extreme | 超能模式（官方自定义） |

- `part5` 有 26 行在映射补全前写入 `mode:2`（原始值记录，按"数据只追加"不回写；语义等价 `Balance`）。
- 复现：`python tools\gear_probe.py --seconds 120`，窗口内按 Fn+Q；或
  `python tools\gear_probe.py --from-log artifacts\datasets\gear_probe.jsonl` 看历史序列。

## 9. r30：档位标签审计（数据质量，实测）

逐 part 统计 `gear_readonly` 列（2026-10-14 实测）：

| part | 行数 | 档位标签分布 |
|---|---|---|
| part1 | 508 | `Balance-readonly` × 508 |
| part2 | 34436 | `Balance-readonly` × 34436 |
| part3 | 6902 | `Balance-readonly` × 6902 |
| part4 | 6907 | `Balance-readonly` × 6907 |
| **part1–4 合计** | **48753** | **`Balance-readonly` 48753 / 48753 = 100%（常量）** |
| part5（r29 起，`--sense-gear`） | 64+ | `Quiet`（真读） |

结论（诚实声明，须进论文数据质量节）：

1. **part1–4 的档位维度是常量，不是档位观测** —— 不能用于"档位 × 负载"分组的监督样本，
   也不能作为包络四档的真数证据（B2 四档目前仍只有干等价）。
2. `work` 标签同为人工命令行参数，无独立佐证，只能声明为"采集时会话标注"。
3. 真档位标签自 **part5** 起生效（`GetThermalMode` 真读）；未映射档位写 `mode:<n>`（不猜）。
4. 档位切换事件可捕获（probe 实测 11:18:19→3、11:26:52→224、11:29:25→1，无丢点），
   故"切换时刻即标签边界"这一约束在后续采集里可自动化。
5. 补救路径：后续采集一律带 `--sense-gear`；若要档位分组的真数，需按 G×W 组合补采
   （成本高，P4 内优先保证关键档位有真标签样本：G0 Quiet / G2 Beast / G4 Extreme）。
6. `tools/coverage_report.py` 自 r32 起额外输出 `gear_distribution`，使档位维度的真实覆盖可见
   （当轮实测：`Balance-readonly` 48753 常量 / `mode:2` 124 / `Quiet` 104 / `Balance` 46 真标签）。

## 10. r33：c3 口径修正 + 办公窗口实测（900s，2026-10-14 11:42–11:57）

命令：`python tools\run_shadow_window.py --seconds 900 --work W1 --process msedge.exe --report`

| 项 | 实测值 |
|---|---|
| ticks / BlackBox | 669 / **669 complete** |
| errors / timeouts | 0 / 0 |
| 帧标回填 | 417/669 行（msedge.exe；偏移 −28796.9s 自动重定基） |
| 覆盖 | W0/AC 9.77h PASS、**W1/AC 2.29h PASS**、W2/AC 1.92h SHORT、plug 0 |
| c1 | BLOCKED（无第二策略版本） |
| **c1b** | **OBSERVED rate 1.00**（669/669：stub 建议 Balance，操作者当时为均衡模式） |
| c2 | PASS（levels 全 OK，L2+ = 0） |
| c3 | 由 FAIL **改为 BLOCKED**（口径修正，见下） |
| c4 | PASS（errors 0） |
| c3b（新增观察项） | 窗口最早 20% p95 22.05ms → 全段中位 37.98ms（+72%） |

**c1b=1.00 的读法（防误读）**：stub 是静态包络（恒返回 Balance），而操作者当时恰在均衡模式，
两者一致是巧合，**不构成策略性能证据**；只有在 P6 引入真策略后，c1b 才具备诊断意义。

**c3 口径修正（与 c1 同源）**：

- fence §5.3 要求「影子窗口 p95 / 1% Low 与**同期实际**差值在 ±5% 内」——"同期实际"= 在运版本的同期帧记录。
- 本机只有一个策略版本，也没有在运版本的帧记录；用"同一窗口最早 20%"当基线**不成立**
  （那是窗口内负载漂移，不是影子 vs 在运对比）。
- 处置：`c3 = BLOCKED-no-in-service-frame-baseline`；窗口内漂移降级为 **c3b**（OBSERVED，不计入 `e4_ready`）。
- 解锁路径：P6 影子阶段与在运版本**并行**采集同期帧标（同窗口双版本），或先给在运版本建立帧基线。
- **更准确的定性（r33 补充）**：E4 影子是 **dry-run 零作动**，影子与在运版本的物理状态完全相同，
  因此 c3 在 E4 阶段**原理上不可产生差异**；该判据真正可测的时点是 **E5 金丝雀（有真实下发）**。
  故 c3 的正确状态是 `BLOCKED`（不适用），而不是 FAIL —— 本判据在 P4 内不应被当作可过项。

**副产品（有诊断价值）**：办公/浏览类别在同一 15 分钟窗口内 p95 从 22ms 漂到 38ms，
说明该类别窗口内负载不平稳 —— 后续 c3 的"同应用类别"分层必须在**同一时间片内**对比，不能跨时段取基线。

## 11. r34：插拔事件判据收紧（防假达标）

现象：r33 时代的 `plug_watch.py` 把电量波动也写成 `power-change`，而
`e4_shadow_report.plug_events()` 把所有非 `watch-start` 行都计为插拔事件
→ **电量掉 1% 就能满足 fence 的"≥1 次插拔电"**，属假达标。

实测（2026-10-14 拔电后启动 watcher）：

```
2026-09-22T15:36:05.422,watch-start,2,95    ← 9-22 AC 状态（上一次 watcher 运行）
2026-10-14T12:00:58.629,watch-start,1,96    ← 今日 DC（拔电）状态
2026-10-14T12:01:04.154,power-change,1,95   ← 仅电量 96→95，**非插拔**
```

修正：

1. `tools/plug_watch.py`：只把 `Win32_Battery.BatteryStatus` 的**状态切换**记为事件
   （`plug-in` = 出现 AC/status 2；`unplug` = 落到 DC/status 1）；电量漂移单独记为 `charge-change`。
2. `tools/e4_shadow_report.py` `plug_events()`：只统计 `plug-in / unplug / ac-lost / ac-restored`；
   `charge-change` / `power-change` 一行都不算入插拔证据。
3. 诚实标注：9-22 至今日之间的那次拔电**未被记录**（当时 watcher 未运行），不计入证据；
   有效插拔事件自本次新 watcher 起记录。

DC 段实测（本轮）：`part7` 行 `W0,DC,Balance,...`（真读 4.78W/43°C）；影子侧 `acdc_sensed=DC`、`soc 96`、围栏 OK。

## 12. E4 覆盖面清单（2026-10-14 实测）

| fence E4 要求 | 实测 | 判定 |
|---|---|---|
| idle ≥1h | W0/AC 9.77h + W0/DC 438 行 → W0 **10.01h** | ✅ |
| 办公 ≥2h | W1/AC **2.11h** | ✅ |
| 游戏 ≥2h | W2/AC **1.92h** | ❌ 差 ~5 分钟（~290 行） |
| ≥1 次插拔电 | `plug-in` **2026-10-14T12:11:13**（status 1→2，电池 84%） | ✅ |

- 九宫格：**4/16**（W0/AC、W0/DC、W1/AC、W2/AC 各 ≥80 行），coverage **0.25**，interactive **0.151**。
- DC 段：`part7` = 438 行 `W0,DC,Balance`（真档位标签）；影子 DC 段 438/438 BlackBox、errors 0。
- 插拔判据（r34 收紧后）：`plug_events = 1`；旧 watcher 写下的 `power-change` 噪声行一律不计入。
- 剩余缺项：**W2 游戏时长 5 分钟**；W3–W7 与其余 DC 列为加分项（非 E4 硬要求）。

**c1/c3 在 P4 内的正确状态**：`BLOCKED`（c1 缺第二策略版本；c3 因 dry-run 零作动无可比对象），
两者均属 P6 影子阶段 / E5 金丝雀阶段判据，不得在 P4 内报 PASS 或 FAIL。



