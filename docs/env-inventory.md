# 环境清单（Environment Inventory）— P1 E2 产物

> 状态：A 机部分已落（2026-09-16）；B 机部分 TBD（暂缓待上线，见
> `docs/b-machine-env-requirements.md`）。上游 `plans/PHASE-01-e2-probes.md`。

## 1. A 机档案（Y7000 2025，实测）

| 项 | 值 |
|----|----|
| CPU | Intel Core Ultra 7 255HX，20 核 / 20 线程 |
| BIOS | LENOVO `S2CN23WW`（2025/11/03）；欠压锁菜单待拍照确认 |
| 主板 | `LNVNB161216` |
| GPU | RTX 5060 Laptop，8151 MiB，驱动 616.92；`power.limit` 查询 `[N/A]`（GPU 基线时复核） |
| 系统 | Win10 Pro 显示名 / HAL 10.0.22621.2506（输出原文，不推断） |
| PowerShell | 5.1.22621.6060 |
| 电源方案 | 现用“高性能”；另有平衡 / 高性能 / 节能 / GamePP |
| WMI | GAMEZONE 类齐备（含双事件类）；mode 值待抓包 |
| Python | 3.12.10；torch 2.11.0+cu128；numpy 1.26.4；psutil 7.2.2；onnxruntime 1.26.0（仅 CPU/Azure EP） |

## 2. TJMax 与 MSR 通道（A 机）

- 用户确认值：105°C；MSR `0x1A2` 复核待探针通道。
- 通道现状：发现残留注册 `WinRing0_1_2_0`（DEMAND_START，已停止），
  文件 `%TEMP%\7zEAFF6774\WinRing0x64.sys` 存在，签名 Valid
 （2018 交叉签名）。Win11 下能否加载未知——**未启动、未加载、未评估加载**，
  只读登记为候选通道；是否启用走 P1 Step 1-3 签名与回滚评估，不硬上。
- B 机：TBD（`0x1A2` 实测值即 14900HX 答案）。

## 3. 工具链缺口声明（P1-5，A 机）

无 pynvml（M1 走 nvidia-smi CSV，不阻塞）/ 无 onnx 包（ORT 仅 CPU，
M8 导出验证 V22–V24 记缺失）/ 无 lightgbm（P4 前补，owner：P4）/
无 nvcc（不阻塞）。详见 `requirements.txt` 注释。

## 4. 探针结论（A 机）

- `gpu_baseline_A.csv`：已跑通（2026-09-16，775 samples / 780s，本地 `artifacts/`，
  gitignore 不进仓）。idle 段 405 条（util 4.7%，49°C，15W，含开头 Fn+Q 扰动）；
  load 段 370 条（util 均值 53.7% / 峰值 99%，66.9°C / 峰值 81°C，63.6W / 峰值
  112.6W）。四字段可用；`power.limit` 持续 `[N/A]`，定为驱动 / EC 限制（非查询姿势问题）。
- `wmi_trace_A.csv`：事件订阅机制 0 触发（非提权会话，DATA 类拒绝访问已佐证），
  已切提权轮询方案，待用户回传提权终端 `LENOVO_GAMEZONE_DATA` 输出后抓包。

## 5. B 机部分：TBD（暂缓）

建档、WMI 抓包、MSR 只读、GPU 基线四项回传后合订至此。TJMax 双机实测值、
UV 锁状态（决定 B 机 Action 掩码）、R4 备注届时补齐。
