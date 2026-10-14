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

## 13. r36：Windows 电源方案 = 独立混淆变量（实测捕获）+ 首次 L1 试算触发

### 13.1 事件

操作者于 **2026-10-14 12:30** 将 Windows 电源计划由「节能」切换为「高性能」。
影子链路的 `scheme_guid` / `scheme_name` 逐 tick 记录**精确捕获**了该切换：

```
12:19:36.437  scheme=节能    gear=Beast temp 78.0C power 90.88W fence OK
12:30:40.722  scheme=高性能   gear=Beast temp 73.0C power 80.75W fence OK
当前方案 GUID 75398c75-9ec9-4f80-b35e-359ec1ea5d6a (高性能)
```

### 13.2 影响与处置

- `scheme`（Windows 电源方案）**不在** G0–G4 档位维度内（档位是 Legion EC 侧，二者正交），
  但它真实影响 CPU/GPU 行为（实测切换前后功耗/温度即变）→ 属**独立混淆变量**。
- 缺陷：`collect_shadow.py` 的 CSV 自 part1 起**没有 scheme 列** → 数据集缺该维度，
  part1–8 的数据无法按电源方案分层。**如实声明，不回填**。
- 处置（r36）：CSV 追加 `scheme` 列（每 tick 经 powercfg 读取），并加 **schema 错位守卫** ——
  若目标文件表头列数不匹配则拒绝追加并要求换新 part 文件（防重踩旧「混列」坑）。
- 论文层面：环境叙述必须包含「Windows 电源方案未锁定，采集中途发生过一次切换」，
  训练/评估可按 scheme 分层或作为协变量。

### 13.3 真实游戏负载下的围栏行为（首次进入裁剪区）

`Final Fantasy VII Rebirth`（2h 窗口前 502 ticks，Beast 档，AC）：

| 指标 | 实测 |
|---|---|
| 围栏分布 | OK **421** / WARN **80** / **L1 1** / L2 0 / L3 0 |
| 温度范围 | **68–85°C**（峰值 85°C 恰为 `TEMP_L1_GPU`） |
| 功耗范围 | 27.73–**99.08W** |
| c2 判据（L2+ 必须 0） | **仍 PASS**（L2/L3 均 0；L1 允许，属正常软裁剪） |

结论：真实高负载会把 GPU 顶到 L1 阈值（85°C）并触发**一次**软裁剪试算，但未触及 L2(88°C)。
这是 E4 判据在真实压力下的首个有效样本；若后续窗口出现 L2+，须按「阈值过紧 vs 真实过热」立案分析，不得掩盖。

## 14. r37：游戏窗口帧标救回 + 真实游戏画像（2h，FF7 Rebirth）

### 14.1 帧标差点全丢（已救回）

`run_shadow_window --process ff7rebirth_` 回填 **0 行**：PresentMon 的 `Application` 列是**含扩展名的文件名**
（实测 `ff7rebirth_.exe` 357357 / `msedge.exe` 23293 / `dwm.exe` 14346），传不带 `.exe` 的值即零匹配。
（早先 dwm 窗口能成功，只因当时传的是 `dwm.exe`。）

处置：

1. **数据救回**：PM CSV 完好（396.6MB），用 `ff7rebirth_.exe` 重跑回填 → **5703/5719 行（99.7%）**，耗时 367s。
2. **工具加固（r37）**：`collect_shadow._app_match()` 接受三形态（全名 / 带 `.exe` / 去扩展名主干），
   过滤点已切换到该函数，避免再次出现「整窗零帧标」。

### 14.2 真实游戏画像（5719 ticks，Beast + 高性能方案，AC）

| 指标 | 实测 |
|---|---|
| 帧率 | p95 中位 **6.28ms ≈ 159fps**（窗口最早 20% 段 5.28ms ≈ 189fps） |
| 温度 | 57–86°C（part8 CSV 峰值 87°C） |
| 功耗 | 4.74–127.62W（CSV 峰值 131.65W，中位 102.6W） |
| GPU util | 中位 99% |
| 围栏 | OK 877 / WARN 2210 / **L1 2632（46%）** / L2 0 / L3 0 |
| BlackBox | 5719/5719 complete，errors 0，scheme 切换 1 次 |

### 14.3 立案：Beast 档高压下围栏 L1 触发率 46%

- 阈值：`TEMP_L1_GPU = 85°C`、`TEMP_L2_GPU = 88°C`；该游戏实测长期 84–86°C、峰值 87°C。
- c2 判据「L2+ 试算 = 0」仍 **PASS**，但**近半数 tick 进入 L1 软裁剪**；若影子真实下发，
  会持续降 PL / 降频 → 直接影响游戏性能与返利。
- 待判：**阈值过紧**（5060 Laptop 在 Beast 档 85°C 属常见工作温度）**vs 真实过热风险**。
- 处置：P6 影子标定时出具专项分析；改阈值属 **L 级提案**（需操作者确认），P4 内不动。

### 14.4 顺带：`interactive_ratio` 跌回门槛以下

游戏行（5833）稀释后 interactive = **0.136 < 0.15** → 按项目规则「<15% 不许报采集达标」，
需补约 **16 分钟**交互类（W1/W6）方可恢复达标。补采须用**新 part9**（带 `scheme` 列的新 schema）。

### 14.5 r37 修正：E4 覆盖时长双计（与 r27 rollup 双计同类）

`run_shadow_window` 让采集器与影子**同时**以 1Hz 记录同一段时间，而 `cell_hours()` 把两者相加
→ 2h 游戏窗口被报成 **W2/AC 5.13h**（实际 **3.54h**）。

处置：`cell_hours()` 默认**只用采集 CSV（part 文件）**作为覆盖来源；影子 JSONL 仅用于判据统计
（c1/c1b/c2/c3b/c4）。新增 `--include-jsonl-hours` 供"只跑影子、未跑采集器"的场景显式开启。

修正后覆盖：**W0 9.89h / W1 2.11h / W2 3.54h** —— 三项仍全部 PASS（结论不变，数字归真）。

## 15. r38：真数三模型起步（`pilot_real_train.py` 升级，M 级先记后做）

### 15.1 为什么必须改

原 `pilot_real_train.py` 已过期：**硬编码只读 part1+part2**、特征仅 2 维（util, mhz）、
`perf_head` 恒写 `BLOCKED-no-frame-labels`、`grid` 恒写 `W0/AC-only`。
而 r37 之后已有：真档位标签（part5+）、游戏/办公帧标（影子 JSONL）、DC 段、插拔事件。

### 15.2 数据源口径（两个集合，分开报，不混算）

| 集合 | 来源 | 行数（当轮） | 可用特征 | 目标头 |
|---|---|---|---|---|
| A：遥测全量 | `artifacts/datasets/D_safe_shadow_A_part*.csv` | 55939 | util、mhz | power、temp |
| B：帧标子集 | `artifacts/samples/e4_shadow_*.jsonl`（含 `frames`） | 6120 | util、mhz、**真档位** | **perf（p95/fps）** |

- 集合 A 含 part1–4 的 48753 行（gear 为常量、无档位信息）：**只用其遥测特征**，不声称有档位维度。
- 集合 B 源自同窗影子运行，**每行都带真档位与帧标**；但其窗口有限（游戏 2h + 办公 15min）。
- 诚实标注：这是「状态→观测量」的关联模型，**不是** f(s,a)（采集期无动作变量，Action7 只在影子试算里生成）。

### 15.3 产出

`artifacts/samples/real_models.json`：两组模型的 RMSE + 均值基线 + 行数 + 分层（按 work/gear），
替代旧的 `real_pilot.json` 单向记录（旧文件保留为历史）。

## 16. r39：part9（W1 × Beast × 高性能）入库 —— 采集达标恢复

| 项 | 值 |
|---|---|
| part9 | **1027 行** `W1/AC/Beast/高性能`（14:37–14:57） |
| W1/AC 累计 | **8616 行 = 2.39h** |
| rows 总计 | 56966 |
| **interactive_ratio** | **0.151 ≥ 0.15** ✅ 采集达标恢复 |
| 九宫格 | 4/16（coverage 0.25） |
| gear 分布 | Beast 6860 / Balance 1125 / mode:2 124 / Quiet 104 / `Balance-readonly` 48753（常量） |

**对照组价值**：part9（W1 × Beast × 高性能）与 part6（W1 × Balance × 节能）构成
**同负载跨档位/跨电源方案**样本对，可直接用于论文的「环境协变量」与包络交叉验证章节。

## 17. r40：真数三模型对比（MLP / LightGBM / 5-Ensemble），含一个诚实的负结果

- 工具：`tools/train_real_models.py`（真数特征，非合成；7:1:2 划分；两组分开训练与报告）
- 产物：`artifacts/samples/real_three_model.json`、`predictor_real_A_telemetry.onnx`、`predictor_real_B_framelabel.onnx`
- 特征现实（已在代码与产物中标注）：`cpu_util` 真数**缺失**（pre-E5 无通道）；`pl1_w` 未直采，
  组 B 用 `GEAR_PL_W[gear]` 作**档位换算代理**；perf 头用**帧标 fps**（真数无 `perf_score`）；
  gear 为常量的旧行按构造被排除出组 B。

### 组 A：遥测全量 56966 行 → (power, temp)

| 模型 | RMSE power / temp |
|---|---|
| MLP | 39.642 / 14.831 |
| **LightGBM** | **11.660 / 17.494** |
| Ensemble5 | 35.946 / 13.044 |
| 均值基线 | 54.654 / 22.462 |

→ LGB 在 power 上降 **78.7%**；temp 仅降 **22.1%**（弱）。MLP 在 4 维特征 + rank_loss 下明显欠拟合。

### 组 B：帧标子集 6135 行 → (fps, power, temp)

| 模型 | RMSE fps / power / temp |
|---|---|
| MLP | 25.757 / 3.283 / 1.389 |
| **LightGBM** | **7.478 / 3.122 / 1.131** |
| Ensemble5 | 18.112 / 6.394 / 2.285 |
| 均值基线 | **5.338** / 13.115 / 5.504 |

- power：三模型全胜基线（LGB 降 **76.2%**）
- temp：三模型全胜基线（LGB 降 **79.4%**）
- **fps：三模型全部输给均值基线（5.338 < 7.478）—— 负结果，如实记录。**
  判读：游戏窗口帧 p95 高度稳定（中位 6.28ms），**均值即强预测器**；模型缺"应用/场景/画质/CPU"等未采变量。
  不得拿它当"性能预测已达标"的证据；P5/P6 需引入帧率相关特征或改用分位/分类建模。

### ONNX（真数版）

`predictor_real_A_telemetry.onnx` **0.02MB / 0.019ms**；`predictor_real_B_framelabel.onnx` **0.02MB / 0.013ms**
→ 均满足 <10MB / <5ms（仍是"状态→观测量关联模型"，非 f(s,a)，见 §15.2）。

## 18. r41：真数 Return 回放（`tools/replay_real.py`）—— 算出数字，但明确拒绝当验收证据

reward 形式与 `reward_baseline_B2.py` 一致（`perf - 2·shield·100 - 1·clamp·100`，逐行，
以便与 B2 锚至少"同一算法"；非 `train_p4_full.py` 的含 std 惩罚版本）。

| 项 | 真数（6135 帧标行） | B2 proxy 锚（32 行） |
|---|---|---|
| Return mean | **94.98** | 71.44 |
| p10 / p50 / p90 | 92.5 / **100.0** / **100.0** | 59.4 / 73.99 / 76.31 |
| nominal_gain | **+32.95%** | — |
| shield / clamp 行 | 0 / 0 | 0 / 0 |

分组：W2 98.59（5703 行，p50=p90=100）｜W1 45.53（417 行，p50 37.92）｜Beast 98.59｜Balance 47.27

**`verdict = NOT-ACCEPTANCE-EVIDENCE`（五条原因，脚本自带）：**

1. **perf 饱和**：**5324/6135 行（86.8%）perf = 100** —— 目标帧 120 低于实测 ~159fps，
   gain 主要来自饱和项而非策略价值；
2. **dry-run 无作动**（与 c3 同源）：无法把策略贡献与环境分离；
3. **跨源比较**：真数 perf 由 fps 换算，B2 锚是代理模型预测 —— 二者不是同一量；
4. **环境不匹配**：真数为 Beast + 高性能方案，B2 锚不含该状态；
5. **shield 只看得见 GPU**（CPU 通道缺失）→ shield 项只是下界。

### 方法论结论（第 6 个口径问题，已记账）

- perf 换算**必须按 work 类别分别定义**（spec：游戏用帧率、非游戏用响应性 `1 − idle_excess`）；
  统一 `fps/120` 会让办公类失真（W1 组 p50 仅 37.92 即此因）。
- **目标帧应取显示器刷新率或按 work 设定**（120 对 Beast 档游戏偏低，导致饱和）。
- **Return 验收需要「有作动的回放」或 live 金丝雀**；本脚本只在量级层面提供参考，
  **不构成 +10% 证据**（与 c3 同源结论）。

## 19. r42：CPU 通道补齐 + 编译负载强度校准（W3 格）

### 19.1 发现：CPU 型负载在 GPU-only 通道下与 idle 不可分

W3 编译首次采集（part10）实测：`GPU util 0% / 180MHz / 4.36W / 51°C`，与 W0 idle 几乎相同
—— 编译负载在 CPU 侧，而采集器只读 nvidia-smi。若不补通道，W3/W4/W7 等 **CPU 型格子在特征上等同于 W0**
（无法分类、无法建模，等于"格子填了但没信息"）。

### 19.2 处置：CPU 利用率是**无需驱动**可得通道

`Win32_PerfFormattedData_PerfOS_Processor`（`Name='_Total'`）→ CSV 新增 `cpu_util` 列
（r42，第 16 列；schema 守卫同步更新）。`cpu_temp_c` 仍无通道（pre-E5），**不伪造**。

### 19.3 负载强度校准（教训：不能"跑个 build"就算负载）

| 阶段 | 负载形态 | 实测 CPU |
|---|---|---|
| 首版（60 个 .cs，`dotnet build -t:Rebuild` 循环） | 时间耗在 dotnet CLI 启停 | **0.23 核 / 7.1%** |
| 扩容（460 个 .cs ≈ 3.6MB 源码，`-m:8` 多核） | 真正的多核编译 | **5.67 核 / 37.4%** |

- 读数可信度：`Get-Process` 的 CPU 时间增量（34.02s/6s = 5.67 核）与 `Get-Counter` 的 37.4% 两条独立路径互证。
- **方法论**：编译类负载必须校准强度，否则采到的是"进程启停"而非"编译压力"；
  该校准法（CPU 时间增量 ÷ 采样秒数 = 占用核数）可直接复用于 W4/W5/W7 各格。
- 负载形态记录：`artifacts/build_load/app`（460 个 C# 编译单元，工作区内自建，可复现）。

### 19.4 W3/AC 采集（part11）

`--work W3 --acdc AC --sense-gear` 与强编译负载同窗；行含 `cpu_util`、`gear=Beast`、`scheme=高性能`。

## 20. r43：采样率修复 + 两个平台性发现（iGPU 分流 / 独显被第三方占用）

### 20.1 采样率退化（已修）

加入 `cpu_util` 后，每 tick 多一次 powershell 调用（~0.4s）+ `scheme`（~0.4s）
→ 实测 600s 只产出 **335 行（0.56Hz，而非 1Hz）**，会破坏与早期 1Hz 数据的可比性。

处置：慢变量改为**缓存轮询**（`scheme` 每 10 tick、`cpu` 每 5 tick）→ 每 tick 只剩 nvidia-smi（~60ms），恢复 ~1Hz。
（`--no-scheme` / `--no-cpu` 仍可完全关闭。）

### 20.2 平台性发现①：浏览器/轻负载走 iGPU，独显遥测看不见

WebGL 持续渲染页实测：msedge CPU 0.34 核（静态页仅 0.05 核），而 `nvidia-smi` 恒为
`0% / 4.56W / 56°C / 180MHz`；`nvidia-smi --query-compute-apps` 的独显进程列表中**没有 msedge**。

含义：**W1/W3/W6/W7 等轻 GPU 格子在独显通道上缺乏分辨力** —— 其可用特征主要是 `cpu_util` 与交互指标。
论文「传感通道局限」章节必须写明这一点，并说明何类负载才激活独显（W2 游戏 / W4 会议 / W5 渲染）。
这也是 W1（part6，power 3.9–4.0W）与 W0（4.3–4.8W）在 GPU 侧几乎相同的真实原因，不是采集错误。

### 20.3 平台性发现②：第三方程序持有独显上下文

`nvidia-smi --query-compute-apps` 里出现 **LM Studio**（PID 20252），非本项目负载，
但会占用独显上下文/显存，可能干扰 GPU 遥测（尤以低负载区与显存读数为主）。

处置：记录为环境干扰项；采集出现异常值时先排查它；**不擅自终止用户进程**。

### 20.4 W6/AC 采集（part12）

`--work W6 --acdc AC --sense-gear`，与浏览器持续渲染负载同窗；标签真读（`gear=Beast`、`scheme=高性能`）。

## 21. r44：补格进度 6/16 与「格子数 ≠ 信息量」的诚实判定

### 21.1 覆盖进展

W0/AC、W0/DC、W1/AC、W2/AC、**W3/AC**（802 行）、**W6/AC**（463 行） = **6/16**（coverage 0.375）；
`interactive_ratio` 0.149 → **0.156**（W6 计入交互类，回到门槛以上）。

### 21.2 `cpu_util` 分辨力分析（按分位数，不看中位数）

| 负载 | n | p10 | p50 | p90 | p99 | 占比 ≥30% |
|---|---|---|---|---|---|---|
| W3 编译 | 335 | 3 | 9 | **59** | **72** | **0.31** |
| W6 浏览器 | 463 | 0 | 2 | 7 | 31 | 0.02 |
| W0 idle | 47 | 0 | 5 | 7 | 8 | 0.00 |

- **W3 可分**（高阶分位与占比同时拉开）；**W6 与 W0 基本不可分**（p90 同为 7；占比 0.02 vs 0.00）。
- W6 前/后半段：前半 max 36 / 后半 max 9 → 浏览器**后台节流**确认，负载未能持续。
- W0 对照被**测量工具自身污染**（边跑统计脚本边采），p50 = 5 反而高于 W6 的 2 ——
  对照采样必须"只采不动手"，本轮认账，后续重采干净版。

### 21.3 结论（方法论，写进论文）

1. 九宫格是**覆盖度**指标（每格 ≥80 行），**不等于可辨识度**。W1/W6/W7 这类轻负载在现有双通道
   （GPU 遥测 + CPU 总利用率）下与 idle 分辨力低 → 补格可过覆盖门禁，但**不得**据此声称这些格"有信息量"。
2. 提升分辨力的正路：①**持续型**负载（前台活动 / 视频 / JS 密集页）②引入**交互指标**
   （`tools/interactive_probe.py` 冷/热启动延迟，已有 608ms / 88ms 实测）作为 W1/W6 的特征
   ③ CPU 温度通道（需驱动，pre-E5 不可得）。
3. 采集纪律：对照格（如 W0）必须在**无工具干扰**下采集，否则读数被自身测量污染。



