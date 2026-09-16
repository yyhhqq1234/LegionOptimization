# PHASE-01：E2 环境探针与工具链（只读 ops，W1–W2）

> 执行顺序调整（2026-09-16，用户指令）：B 机侧暂缓为待完成项，先闭环 A 机侧。
> B 机上线后恢复执行 B 项（见 §4 标注）。调整不改变验收口径，只改执行顺序。

## 1. 阶段目标

冻结 B 机型号，完成双机只读探针（WMI 事件 / FIVR 兼容 / TJMax / GPU 传感基线），
补齐 `requirements.txt` 锁文件，关闭 P1-3/P1-5。解锁全部 V 格的 B 列执行资格。

## 2. 前置依赖

- PHASE-00 完成（V09+ 排期资格已有；本阶段自身只做只读探针，不依赖 V09+）
- B 机（i9 14900HX + 5060）可上线 1–2 天

## 3. 详细步骤

### Step 1-1：B 机冻结与建档（0.5 天）
1. 记录 B 机：精确 CPU 型号/步进、BIOS 版本、GPU 型号/驱动版本、EC/散热规格。
2. 确认 B 机 BIOS 是否锁欠压（0x104 / Overclocking Lock），结论记入档案（决定 B 机 Action 掩码）。
3. 落盘 `docs/env-inventory.md`（A 机 t3 结论 + B 机档案二合一）。

### Step 1-2：WMI 事件抓包（0.5 天/机）
1. 双机分别订阅 `LENOVO_GAMEZONE_SMART_FAN_MODE_EVENT` 与 `LENOVO_GAMEZONE_THERMAL_MODE_EVENT`，
   Fn+Q 循环两轮，记录每档 mode 值（验证 B 机是否为 224 / 行为差异记为 R4 输入）。
2. 产物：`artifacts/wmi_trace_A.csv`、`artifacts/wmi_trace_B.csv`。

### Step 1-3：FIVR/MSR 只读兼容探针（1 天）
1. 双机只读：MSR `IA32_TEMPERATURE_TARGET (0x1A2)` 读 TJMax（A 机预期 105，与用户确认值核对；
   B 机实测值即 14900HX 答案，写回规格 §8）。
2. 只读探测超频锁存器（OC Lock / UV 保护位），不写任何 MSR。
3. B 机若 FIVR 不兼容 → 按预案降级为 powercfg-only 对照并备注（t2 §5.2 已预置），不阻塞。
4. 需要 подписал WinRing0 类驱动时：先评估签名与回滚，拿不准则本阶段只做 NVML/powercfg 侧，
   MSR 读探针顺延至 P3（文档中显式标记）。

### Step 1-4：GPU 传感基线（0.5 天/机）
1. 双机 `nvidia-smi` 1Hz 轮询 10 分钟（待机+短烤机），确认 util/freq/power/temp/功耗墙字段可用性。
2. `pynvml` 列为可选优化，缺失不阻塞（M1 先走 nvidia-smi CSV）。
3. 产物：`artifacts/gpu_baseline_A.csv`、`artifacts/gpu_baseline_B.csv`。

### Step 1-5：工具链锁文件（0.5 天）
1. 本机生成 `requirements.txt`（Python 3.12.10 / torch 2.11.0+cu128 / psutil 等实测版本 pin）。
2. 明确缺口声明：无 pynvml、无 onnx 包、无 nvcc、无 CUDA EP（ORT 仅 CPU）→ M8 导出验证 V22–V24 先记缺失声明。
3. 外部参照登记：`D:\Intel降压定频 .exe` 登记为外部 MSR 写入者（E2 互斥设计输入）。

## 4. 阶段验收方法

- [ ] `docs/env-inventory.md` 存在：A 机档案先行（B 机部分 TBD）；TJMax/UV 锁分机记录；工具链缺口声明
- [ ] `artifacts/wmi_trace_A.csv`（A 机先行）/ `wmi_trace_B.csv`（暂缓待 B 机）存在且覆盖 4 档事件；B 机差异 R4 备注（暂缓）
- [ ] `requirements.txt` 存在且 `pip install -r requirements.txt --dry-run`（或等价校验）通过（A 机先行，无 B 机依赖）
- [ ] P1-3 抽样比排期表先写（A 机先行，B 列执行待 B 机）；P1-5 缺口有 owner 与顺延标记（A 机先行）
- [ ] 验收：B 列执行资格解锁（暂缓待 B 机）；MSR 写操作零发生（全程有效：本阶段无任何写入类命令记录）

## 5. 产物清单

`docs/env-inventory.md` / `requirements.txt` / `artifacts/wmi_trace_*.csv` /
`artifacts/gpu_baseline_*.csv` / B 列排期表（V01–V24 每格 B 动作填满）

## 6. 风险与回退

- B 机 WMI 行为差异（R4）：降级对照，不返工。
- MSR 驱动签名风险：探针顺延 P3，本阶段判“有条件通过”，不锁死。
