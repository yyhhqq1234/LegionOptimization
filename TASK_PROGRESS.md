# 任务进度断点 (Task Progress Checkpoint)

> 跨会话任务续传。新会话首条消息发 `/resume` 即可无缝衔接。

---

## 当前状态：✅ 项目完成 — 可迁移 & 重启后完全生效

**更新时间**：2026-08-10 17:30

### 4 档模式覆盖

| 档位 | Fn+Q 触发 | 频率 | 电压 | PL1 | 触发方式 |
|------|----------|------|------|-----|---------|
| 安静 (Quiet) | ✅ | 3.8GHz | -70mV | 25W | LLT Automation |
| 均衡 (Balance) | ✅ | 4.8GHz | -65mV | 40W | LLT Automation |
| 野兽 (Beast) | ✅ | 5.0GHz | -55mV | 65W | LLT Automation |
| 超能 (Extreme) | ✅ | 5.2GHz | -45mV | 65W | PowerModeWatcher.ps1 |

### 架构

```
Fn+Q →
  Quiet/Balance/Beast → LLT Automation (PowerModeAutomationPipelineTrigger)
  Extreme/超能 → PowerModeWatcher.ps1 (LENOVO_GAMEZONE_THERMAL_MODE_EVENT)

每个 bat 执行：kill TS → copy INI → powercfg → TS 注入 → 等5s → kill TS

开机链：
  Logon → LegionLLT 计划任务 → start_llt.bat → LLT (系统托盘) + PowerModeWatcher.ps1
  Logon +30s → LegionProfile 计划任务 → startup_inject.bat → 初始 FIVR 注入
```

### 已完成的清理 & 可移植化

- ✅ 所有脚本使用 `%~dp0` / `$PSScriptRoot` 相对路径（可迁移到任意目录）
- ✅ 删除调试文件：`debug_wmi.ps1`, `debug_wmi_capture.ps1`, `query_wmi.ps1`
- ✅ 删除废弃文件：`hotkey_switch.ps1`, `start_ts_hidden.ps1`, `FivrInjector/`
- ✅ 删除冗余文件：`setup_ts_nouac.bat`, `run_llt_admin.bat`, `create_watcher_task.bat`, `setup_watcher.ps1`
- ✅ 删除测试文件：`test_pause.bat`
- ✅ LLT 编译后文件移到 `llt-build/`，源码补丁在 `llt-patches/`
- ✅ LLT 完整源码树已删除（38项目，不需要）
- ✅ Git 仓库已初始化，`.gitignore` 已配置
- ✅ `README.md` 含完整中英文说明
- ✅ `configure.bat` 用于在其他机器上更新 automation.json 路径

### 计划任务（3 个）

| 任务名 | 触发 | 运行 |
|--------|------|------|
| `LegionLLT` | 登录时 | `start_llt.bat` (启动 LLT+Watcher) |
| `LegionProfile` | 登录+30s | `startup_inject.bat` (初始 FIVR) |
| `ThrottleStop_NoUAC` | 手动 (`schtasks /run`) | `ThrottleStop.exe` (绕过 UAC) |

### 迁移到其他拯救者电脑

1. 复制整个文件夹到 `D:\LegionOptimization`
2. 以管理员运行 `setup_startup.bat`
3. 在 LLT 中导入 `automation.template.json`
4. 运行 `configure.bat` 更新路径
5. 根据目标 CPU 调整 `ThrottleStop_profiles/*.ini` 和 `*.bat` 中的电压/频率值
6. 重启测试

### LLT 源码修复（llt-patches/）

1. `PowerModeListener.cs` — GetValue: 添加 WMI value 4→Extreme
2. `ThermalModeListener.cs` — GetValue: 添加 WMI value 4→Extreme
3. `AutomationProcessor.cs` — 添加 ThermalModeListener 订阅 → PowerModeAutomationEvent

### 已知限制

- 超能模式 WMI 事件通过独立 watcher 解决（SmartFanModeEvent 在 Y7000 2025 IAX10 上不触发第 4 档）
- TS 弹窗暂时无法完全隐藏（MiniMode+SuperMiniMode 最小化但非隐藏）
- 旧 LLT 进程 (PID 19180) 下次重启后自动清除
- `watcher.lock` 被 SYSTEM 级 watcher 进程锁定，重启后自动清除
