# 任务进度断点 (Task Progress Checkpoint)

> 跨会话任务续传。新会话首条消息发 `/resume` 即可无缝衔接。

---

## 当前状态：全部 4 档 Fn+Q 模式正常触发

**更新时间**：2026-08-10 17:15

### 4 档模式覆盖

| 档位 | Fn+Q 触发 | 频率 | 电压 | PL1 | 触发方式 |
|------|----------|------|------|-----|---------|
| 安静 (Quiet) | ✅ | 3.8GHz | -70mV | 25W | LLT Automation |
| 均衡 (Balance) | ✅ | 4.8GHz | -65mV | 40W | LLT Automation |
| 野兽 (Beast) | ✅ | 5.0GHz | -55mV | 65W | LLT Automation |
| 超能 (Extreme) | ✅ | 5.2GHz | -45mV | 65W | PowerModeWatcher.ps1 |

### 架构

- **LLT Automation** (`automation.json`): 4 条 pipeline，其中 Quiet/Balance/Beast 通过 `PowerModeAutomationPipelineTrigger` 触发
- **PowerModeWatcher.ps1**: 独立 WMI 后台监听器，监听 `LENOVO_GAMEZONE_THERMAL_MODE_EVENT`，只处理 mode=224 (超能/Extreme)，在 `start_llt.bat` 中随 LLT 一起启动
- **批处理脚本**: `quiet.bat` / `balance.bat` / `beast.bat` / `custom.bat` — 每个脚本执行：kill TS → 复制 INI → powercfg 设频率 → 启动 TS → 等5秒 → kill TS
- **ThrottleStop**: 启→注入 FIVR→杀进程 ("fire-and-forget")
- **计划任务**: `LegionLLT` (启动 LLT+Watcher), `LegionProfile` (启动时注入), `ThrottleStop_NoUAC` (无 UAC 启动 TS)

### 关键发现

`LENOVO_GAMEZONE_SMART_FAN_MODE_EVENT` 在 Y7000 2025 IAX10 上**不会**为第4档 (超能) 触发，只有前3档。
`LENOVO_GAMEZONE_THERMAL_MODE_EVENT` 对全部4档都触发，超能对应 mode=224。

### LLT 源码修改

1. `PowerModeListener.cs` — `GetValue()`: 添加 value=4 → Extreme 映射（备用）
2. `ThermalModeListener.cs` — `GetValue()`: 添加 value=4 → Extreme 映射（备用）
3. `AutomationProcessor.cs` — 添加 `ThermalModeListener` 订阅，映射 ThermalModeState → PowerModeState → PowerModeAutomationEvent

### 待解决

- 旧 LLT 进程 (PID 19180) 无法终止，使用旧代码。重启系统后新 LLT 生效。
- TS 弹窗暂时无法完全隐藏（TS 是 GUI 应用），但 MiniMode 下窗口很小。
