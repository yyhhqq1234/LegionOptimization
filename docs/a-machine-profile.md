# 本机（A 机）定位与档案

> 更新：2026-09-16 实测建档（全只读命令）| 上游：`plans/PHASE-01..07`
> 产物去向：`docs/env-inventory.md`（P1 落盘双机档案合订）
> 姊妹篇：`docs/b-machine-env-requirements.md`（B 机上线清单）

## 0. 一句话定位

本机 = **基准机 + 主力开发机 + A 方案训练源域 + P5 迁移源 + P7 金丝雀本机**。

一切回放与对比的锚点是 `legion-legacy-b2` tag，一切训练、影子、放量的
主场是本机。B 机是独立对照与迁移目标，不是本机的替补。

## 1. 实测档案（2026-09-16，只读命令输出原文）

| # | 项 | 实测值 |
|---|----|--------|
| A-1 | 机型 | Lenovo Y7000 2025（主板 `LNVNB161216`） |
| A-2 | CPU | Intel Core Ultra 7 255HX，20 核 / 20 线程（8P+12E，无超线程） |
| A-3 | BIOS | LENOVO `S2CN23WW`，2025/11/03 |
| A-4 | GPU | NVIDIA GeForce RTX 5060 Laptop，显存 8151 MiB，驱动 616.92 |
| A-5 | 系统 | `Get-ComputerInfo` 报 Windows 10 Pro / 2009 / HAL 10.0.22621.2506 |
| A-6 | PowerShell | 5.1.22621.6060 |
| A-7 | 电源方案 | 现用“高性能”（`8c5e7fda…`）；另有平衡 / 高性能 / 节能 / **GamePP** |
| A-8 | WMI | `root/wmi` 下 GAMEZONE 类齐备，含 `SMART_FAN_MODE_EVENT` 与 `THERMAL_MODE_EVENT`（另有 CPU/GPU OC DATA、FAN COOLING、CHARGE MODE 类） |
| A-9 | 深度学习 | Python 3.12.10，torch 2.11.0+cu128（sm_120）可用 |

诚实备注两则（不推断，只记录）：

1. A-5 显示名（Win10 Pro）与内核号（22621 系）口径不一致，以输出原文为准，
   P1 建档时原样记入 `env-inventory.md`，不做“其实是 Win11”的推断。
2. A-4 中 `power.limit` 本次查询为 `[N/A]`——EGM 功耗墙字段可用性存疑，
   P1 Step 1-4 做 10 分钟基线时复核是查询姿势问题还是驱动 / EC 限制
   （`utilization / clocks / power.draw / temperature` 同批复核）。

## 2. 在各阶段的职责

- P0：已关闭（评审在本机执行，`tag phase-00-done`）。
- P1 E2（A 机侧）：WMI 抓包 `wmi_trace_A.csv`；MSR `0x1A2` 复核 TJMax；
  GPU 10min 基线 `gpu_baseline_A.csv`；`requirements.txt` 在本机生成。
- P2 E3：新开机时序实测（2 次重启）+ LKG staging 演练 + A2 首测，主场。
- P3：HAL L0–L3 + 采集器实现与 dry-run，V01–V09 全跑通，主场。
- P4：`D_safe_A` 主力采集（2000–4000 条，九宫格 ≥80%）+ 三模型本地训练 +
  约束 BO + ONNX v1，**源域**。
- P5：A 机 Ensemble 冻结为迁移源（零样本起点）；对照组外推不足时 A 机补位。
- P6：`D_safe` 冻结为 Replay Buffer；五算法本地训练（种子 ×3）+ 84h 影子。
- P7：48h 本机金丝雀（时间片 A/B 对 LKG）+ V22–V24 + 演示三件套实拍。

## 3. 不是什么（消歧）

- 不是 B 机对照：B 机（14900HX）独立建档对照，见姊妹篇。
- 不是外部参照：外部手动基线是 `D:\Intel降压定频 .exe`（−50mV 恰与 G1
  同值，有参照意义），只读不碰。
- B2 基线 ≠ 本机现状：B2 是本机旧项目的冻结 tag（`legion-legacy-b2`），
  本机工作树早已干净；回放锚点用 tag log，只许 worktree / archive 到
  staging，用完删除。
- 不是放量终点：放量须加 B 机 24h 交叉（P7），本机 48h 只是第一站。

## 4. 已确认 vs 待补

已确认：TJMax = 105（用户确认值）；torch cu128 可用；WMI 双事件类存在；
powercfg 含 GamePP 方案；Fn+Q 四档可切（抓包时复验）。

待补（P1 进 `env-inventory.md`）：TJMax 的 MSR `0x1A2` 复核值；`power.limit`
N/A 原因；WMI mode 值（`wmi_trace_A.csv`，验证是否为 224 系）；
`gpu_baseline_A.csv`；适配器功率；BIOS 欠压锁状态（S2CN23WW 菜单拍照）。

## 5. 红线（本机侧铁律）

- `D:\Intel降压定频 .exe` + `D:\undervolt_config.json` 只读；`D:\` 其他不碰。
- `watcher.lock`（0 字节，被 Session-0 进程持有）不管；新锁只用
  `hal-actuation.lock` + PID 校验。
- 新项目一切路径 / 文件名禁空格禁中文；CRLF warning 不处理。
- 全程 dry-run 默认；G4 真实下发锁定（待 E5）；V09+ 已解锁（P0 已签）。
