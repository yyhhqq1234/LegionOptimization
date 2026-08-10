# 任务进度断点 (Task Progress Checkpoint)

> 跨会话任务续传。新会话首条消息发 `/resume` 即可无缝衔接。

---

## 当前状态：✅ 修复完成，待重新执行 setup_startup.bat 并重启验证

**更新时间**：2026-08-10 18:05

### 修复了重启后的 3 个问题

1. **命令行弹窗 "不是内部命令"** → 计划任务改用 `.ps1` 而非 `.bat`
   - `.bat` 运行时 cmd.exe 会弹窗，且 SYSTEM 账户 PATH 可能不同
   - `.ps1` 通过 `powershell -WindowStyle Hidden` 运行，零弹窗
2. **LLT 没启动** → 同上述修复，`start_llt.ps1` 静默启动 LLT
3. **TS 启动但没被杀** → `startup_inject.bat` 原来只启动不杀
   - 新 `startup.ps1`：启动 TS → 等 5 秒 → kill（含日志）

### 新启动脚本

| 文件 | 用途 | 调用者 |
|------|------|--------|
| `start_llt.ps1` | 静默启动 LLT + PowerModeWatcher | LegionLLT 计划任务 |
| `startup.ps1` | 开机 FIVR 注入（启动→等5s→kill） | LegionProfile 计划任务 |

### 计划任务（4 个）

| 任务名 | 动作 |
|--------|------|
| `LegionLLT` | `powershell -WindowStyle Hidden -File start_llt.ps1` |
| `LegionProfile` | `powershell -WindowStyle Hidden -File startup.ps1` |
| `ThrottleStop_NoUAC` | `ThrottleStop.exe` (手动触发) |
| `LegionUpdate` | `powershell -WindowStyle Hidden -File check_update.ps1` (每周日 3AM) |

### ⚠️ 下一步（必须执行）

以**管理员身份**运行：
```bat
D:\LegionOptimization\setup_startup.bat
```
然后重启验证。

### 注意
- 旧的 `start_llt.bat` 和 `startup_inject.bat` 保留在项目中但不再使用
- SYSTEM 权限进程（旧 LLT PID 3740 / TS PID 16488）无法从用户终端杀，重启自动清理
