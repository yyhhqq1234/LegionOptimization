# B 机上线环境需求（P1 E2 前置）

> 状态：待执行 | 时间盒：B 机 1–2 天 | 上游：`plans/PHASE-01-e2-probes.md`
> 产物去向：`docs/env-inventory.md`（A 机 t3 结论 + B 机档案二合一）
> 铁律映射：全程 dry-run；门禁通过前零真实写入；路径禁空格禁中文。

## 0. 结论先行

1. **不需要把项目完整部署到 B 机**。P1 E2 是只读探针，B 机侧只需执行
   §2 的命令清单（建档 + WMI 抓包 + GPU 基线），探针脚本用 U 盘 / zip
   拷贝或照抄命令执行即可；`git clone` 整仓可选（为保证脚本版本一致，
   推荐但非强制）。
2. **B 机暂不需要 Python / torch 环境**。`requirements.txt` 在 A 机生成
   （P1 Step 1-5）；B 机配完整 Python 环境是 P5（跨机训练）的事，
   届时按 `requirements.txt` 实测 pin 来（Python 3.12.10 / torch 2.11.0+cu128）。
3. **全程零写入**：禁 MSR 写、禁 powercfg 写、禁 BIOS 改动、禁装未知来源驱动。
   MSR 读探针若缺签名驱动，记缺失顺延 P3，不硬装（见 §2.3）。

## 1. B 机基线要求

| # | 项 | 要求 | 验证 |
|---|----|------|------|
| B-1 | 机型 | Lenovo Legion，CPU i9-14900HX，GPU RTX 5060 Laptop | §2.1 建档命令 |
| B-2 | 系统 | Windows 11（记录版本）；PowerShell 可用（记录 `$PSVersionTable`） | `Get-ComputerInfo` |
| B-3 | 显卡驱动 | 含 `nvidia-smi` 且有输出（记录驱动版本） | `nvidia-smi` |
| B-4 | Legion WMI | `root/wmi` 下 GAMEZONE 类存在；Fn+Q 四档切换正常 | §2.2 第一条命令 |
| B-5 | 权限 | 管理员终端可用（UAC 可点“是”；`schtasks` 类操作沿用提权流程） | 弹 UAC 确认一次 |
| B-6 | 磁盘 | 探针目录如 `C:\Probe\`（ASCII、无空格无中文）；产物 <50MB | — |
| B-7 | 网络 | 不需要（全本地操作；回传产物用 U 盘 / 局域网均可） | — |

## 2. 操作清单（只读，按 PHASE-01 Step 顺序）

### Step 1-1：B 机冻结与建档（0.5 天）

```powershell
mkdir C:\Probe\
Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,Stepping,MaxClockSpeed
Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion,ReleaseDate  # 序列号不回传
Get-ComputerInfo | Select-Object WindowsProductName,WindowsVersion,OsHardwareAbstractionLayer
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
powercfg /list
$PSVersionTable
```

另需人工记录（拍照即可）：BIOS 版本号界面；EC / 散热规格 / 适配器功率
（铭牌或 Legion 说明页）；BIOS 内欠压相关项（Overclocking Lock /
Undervolt Protection，有无该菜单均如实记录——决定 B 机 Action 掩码，
若锁则 P5 改子空间迁移，结论照写）。

产物：`C:\Probe\bringup_B.txt`（上述输出粘贴）+ BIOS 照片。

### Step 1-2：WMI 事件抓包（0.5 天）

```powershell
# 1) 先确认 provider 与类名（输出贴回 A 机；若与 A 机 t3 结论不一致，先贴输出，不硬套）
Get-CimClass -Namespace root/wmi | Where-Object {$_.CimClassName -match 'GAMEZONE'} | Select-Object CimClassName

# 2) 订阅（类名以前一步输出为准；Fn+Q 循环两轮，每档停留约 5s）
Register-CimIndicationEvent -Namespace root/wmi -ClassName '<上一步确认的THERMAL类名>' -SourceIdentifier GZ-Thermal -Action { $Event.SourceEventArgs.NewEvent | Export-Csv C:\Probe\wmi_trace_B.csv -Append -NoTypeInformation }
Register-CimIndicationEvent -Namespace root/wmi -ClassName '<上一步确认的FAN类名>' -SourceIdentifier GZ-Fan -Action { $Event.SourceEventArgs.NewEvent | Export-Csv C:\Probe\wmi_trace_B.csv -Append -NoTypeInformation }
# ... Fn+Q 循环两轮 ...
Unregister-Event GZ-Thermal; Unregister-Event GZ-Fan
```

产物：`C:\Probe\wmi_trace_B.csv`（覆盖 4 档事件；B 机 mode 值是否为 224
如实记录，若不是则记 R4 输入）。

### Step 1-3：FIVR / MSR 只读兼容探针（有条件，1 天）

- 目标读数：MSR `IA32_TEMPERATURE_TARGET (0x1A2)` 的 TJMax（B 机实测值即
  14900HX 答案，写回规格 §8）；超频锁存器（OC Lock / UV 保护位）只读。
- 前置：需已签名 WinRing0 类驱动。**若无可用签名驱动，本项记“缺失，
  顺延 P3”，转做 NVML / powercfg 侧（`nvidia-smi` + `powercfg /query` 只读），
  不安装未知来源驱动**（风险见 PHASE-01 §6）。
- B 机若 FIVR 不兼容 → 按预案降级为 powercfg-only 对照并备注，不阻塞。

### Step 1-4：GPU 传感基线（0.5 天）

```powershell
# 10 分钟 1Hz：前 5min 待机，后 5min 日常短负载（常玩游戏即可，不引入新烤机工具）
$job = Start-Job { nvidia-smi --query-gpu=timestamp,utilization.gpu,clocks.sm,power.draw,temperature.gpu,power.limit --format=csv -l 1 -f C:\Probe\gpu_baseline_B.csv }
# ... 待机5min + 短负载5min ...
Stop-Job $job; Remove-Job $job
# 若 -l/-f 联用在该驱动不支持，改用循环版（行为以 B 机实测为准）：
# 1..600 | ForEach-Object { nvidia-smi --query-gpu=timestamp,utilization.gpu,clocks.sm,power.draw,temperature.gpu,power.limit --format=csv,noheader >> C:\Probe\gpu_baseline_B.csv; Start-Sleep 1 }
```

产物：`C:\Probe\gpu_baseline_B.csv`（确认 util / freq / power / temp /
功耗墙字段可用性；`pynvml` 缺失不阻塞，M1 先走 nvidia-smi CSV）。

## 3. 禁止事项（B 机侧铁律）

- 禁真实写 MSR / `powercfg /set` 系 / ThrottleStop 落盘 / BIOS 欠压设置。
- 禁装未知来源 MSR 驱动；签名与回滚拿不准就顺延 P3 并显式标记。
- 禁改动 B 机现有调优 / 降压配置（如有，先拍照记录现状）。
- B 机若也有外部手动基线（如降压工具），只读登记为外部 MSR 写入者，不碰。
- 探针目录用完可删；回传产物不含序列号等隐私；CRLF warning 不处理。

## 4. 产物回传与落盘

回传 A 机：`bringup_B.txt` + `wmi_trace_B.csv` + `gpu_baseline_B.csv` +
BIOS 照片 + MSR 项结论（实测值 / 缺失顺延二选一）。
A 机落盘 `docs/env-inventory.md` 后，P1 §4 验收：
B 列执行资格解锁；本阶段审计必须显示 MSR 写操作零发生。

## 5. 风险与降级（不判失败项）

- B 机 WMI 行为差异（R4）：降级对照，不返工。
- MSR 驱动签名风险：本阶段判“有条件通过”，不锁死。
- B 机 UV 锁：mask 电压维，只迁 PL / 频墙子空间（P5 预案）。
