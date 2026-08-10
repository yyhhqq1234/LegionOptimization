# 任务进度断点 (Task Progress Checkpoint)

> 跨会话任务续传。新会话首条消息发 `/resume` 即可无缝衔接。

---

## 当前状态：✅ 项目完成 — 官方 LLT + 自动更新 + 无弹窗

**更新时间**：2026-08-10 17:45

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
  Logon → LegionLLT 计划任务 → start_llt.bat → LLT (系统托盘, 无弹窗) + PowerModeWatcher.ps1
  Logon +30s → LegionProfile 计划任务 → startup_inject.bat → 初始 FIVR 注入
  Weekly Sun 3AM → LegionUpdate → check_update.ps1 → 检查 GitHub → 静默更新
```

### 关键变更：切换到官方 LLT

- **LLT 来源**：官方 GitHub 发布版 v2.34.0.0（`C:\Program Files\LenovoLegionToolkit\`）
- **不再需要**: 自编译 LLT (`llt-build/`)，源码补丁 (`llt-patches/`)
- **原因**: `PowerModeWatcher.ps1` 独立处理超能模式，不依赖 LLT 源码修改
- **好处**: 
  - ✅ 无 .NET host 弹窗（官方 .exe 是 GUI 应用，非控制台）
  - ✅ 支持官方自动更新
  - ✅ 仓库减小 ~57 MB

### 已完成

- ✅ 所有脚本使用 `%~dp0` / `$PSScriptRoot` 相对路径
- ✅ LLT 切换到官方版本，无启动弹窗
- ✅ `check_update.ps1` 自动更新脚本（GitHub API → 下载 → 静默安装 → 验证 automation.json）
- ✅ `LegionUpdate` 计划任务（每周日凌晨 3:00）
- ✅ 删除 `llt-build/`, `llt-patches/`, 调试文件, 废弃脚本
- ✅ Git 仓库整洁，`.gitignore` 已更新
- ✅ `README.md` 完整说明，含自动更新文档

### 计划任务（4 个）

| 任务名 | 触发 | 运行 |
|--------|------|------|
| `LegionLLT` | 登录时 | `start_llt.bat` (启动 LLT+Watcher) |
| `LegionProfile` | 登录+30s | `startup_inject.bat` (初始 FIVR) |
| `ThrottleStop_NoUAC` | 手动 (`schtasks /run`) | `ThrottleStop.exe` (绕过 UAC) |
| `LegionUpdate` | 每周日 3:00 AM | `check_update.ps1` (检查+安装更新) |

### 迁移到其他拯救者电脑

1. 复制整个文件夹到 `D:\LegionOptimization`
2. 从 GitHub 安装最新 LLT: https://github.com/LenovoLegionToolkit-Team/LenovoLegionToolkit/releases
3. 以管理员运行 `setup_startup.bat`
4. 在 LLT 中导入 `automation.template.json`
5. 运行 `configure.bat` 更新路径
6. 根据目标 CPU 调整电压/频率值
7. 重启测试

### 已知限制

- 超能模式 WMI 事件通过独立 watcher 解决（SmartFanModeEvent 在 Y7000 2025 IAX10 上不触发第 4 档）
- TS 弹窗暂时无法完全隐藏（MiniMode+SuperMiniMode 最小化但非隐藏）
- GitHub API 不可用时更新检查静默跳过（不报错）
- `automation.json` 在 LLT 更新后自动保留（Inno Setup 不删除 AppData）
