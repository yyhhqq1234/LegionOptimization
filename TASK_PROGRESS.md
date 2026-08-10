# 任务进度断点 (Task Progress Checkpoint)

> 跨会话任务续传。新会话首条消息发 `/resume` 即可无缝衔接。

---

## 当前状态：🔧 发现 Session 0 隔离问题，已修复

**更新时间**：2026-08-10 18:20

### 根因分析：为什么 LLT 托盘图标不显示

**问题**：计划任务 `LegionLLT` 使用 `/rl HIGHEST`（SYSTEM 权限）启动 LLT GUI
**根因**：Windows Session 0 隔离 —— SYSTEM 账户启动的 GUI 应用运行在 Session 0，无法在用户桌面（Session ≥1）显示托盘图标
**表现**：
- Watcher 能启动（后台进程，不需要 GUI）✅
- LLT 服务能运行（Windows Service，Session 0）✅
- LLT 主程序启动了但看不到（GUI 被隔离在 Session 0）❌

### 修复方案

| 组件 | 之前 | 之后 | 原因 |
|------|------|------|------|
| **LLT 启动** | 计划任务 (SYSTEM) | 注册表 Run 键 (用户) | 用户上下文 = GUI 可显示 |
| **FIVR 注入** | 计划任务 (SYSTEM) | 计划任务 (SYSTEM) | 不变（需要 SYSTEM 杀 TS） |
| **TS 免 UAC** | 计划任务 (SYSTEM) | 计划任务 (SYSTEM) | 不变 |
| **更新检查** | 计划任务 (SYSTEM) | 计划任务 (SYSTEM) | 不变 |

### 启动脚本

| 文件 | 用途 | 调用者 |
|------|------|--------|
| `start_llt.ps1` | 静默启动 LLT + PowerModeWatcher | 注册表 Run 键（用户登录时） |
| `startup.ps1` | 开机 FIVR 注入（启动→等5s→kill） | LegionProfile 计划任务 |
| `PowerModeWatcher.ps1` | WMI 监听 Fn+Q → 触发 custom.bat | start_llt.ps1 启动 |
| `check_update.ps1` | 每周检查 GitHub release → 自动更新 | LegionUpdate 计划任务 |

### 计划任务（3 个，LegionLLT 已废弃）

| 任务名 | 动作 | 权限 |
|--------|------|------|
| `LegionProfile` | `powershell -WindowStyle Hidden -File startup.ps1` | SYSTEM (+30s) |
| `ThrottleStop_NoUAC` | `ThrottleStop.exe` (手动触发) | SYSTEM |
| `LegionUpdate` | `powershell -WindowStyle Hidden -File check_update.ps1` | SYSTEM (每周日 3AM) |
| ~~`LegionLLT`~~ | ~~已废弃~~ → 改为注册表 Run 键 | - |

### ⚠️ 下一步（必须执行）

**第一步（无需管理员）**：双击运行
```
D:\LegionOptimization\fix_tray.bat
```
这会：添加注册表 Run 键 + 立即启动 LLT + 启动 watcher

**第二步（需要管理员）**：右键 → 以管理员身份运行
```bat
D:\LegionOptimization\setup_startup.bat
```
这会：清理旧的 LegionLLT 任务 + 更新所有计划任务

**第三步**：重启验证
- 无命令行弹窗
- LLT 在系统托盘
- Fn+Q 4 个模式全部正常工作

### 辅助脚本

| 文件 | 用途 |
|------|------|
| `fix_tray.bat` | 快速修复：加 Run 键 + 启动 LLT（无需管理员） |
| `setup_startup.bat` | 完整配置：计划任务 + 注册表（需要管理员） |
