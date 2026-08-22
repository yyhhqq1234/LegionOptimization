# disable.ps1 — 一键禁用 LegionOptimization 全部功能
# 以管理员身份运行，暂停所有自启、计划任务、LLT 自动化、Watcher
# 不会卸载 LLT / ThrottleStop，也不会删除配置文件，enable.ps1 可一键恢复
# 双击 disable.bat 也可触发（自动提权）

# --- Auto-elevate ---
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "[INFO] Not Administrator, re-launching with elevation..."
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit 0
}

$scriptDir = $PSScriptRoot
$logFile   = "$scriptDir\switch_log.txt"
$autoJson  = "$env:LOCALAPPDATA\LenovoLegionToolkit\automation.json"
$pidFile   = "$scriptDir\watcher.pid"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Write-Host $line
    try { $line | Out-File $logFile -Append -Encoding UTF8 -ErrorAction Stop } catch {}
}

Write-Host "============================================================"
Write-Host "  LegionOptimization — Disable (一键禁用)"
Write-Host "============================================================"
Write-Host ""
Write-Host "  将禁用以下功能（不会删除文件，可用 enable 恢复）:"
Write-Host "    - 计划任务 LegionProfile / ThrottleStop_NoUAC / LegionUpdate"
Write-Host "    - 注册表自启 LegionOptimization (LLT + Watcher)"
Write-Host "    - LLT 自动化 (automation.json IsEnabled)"
Write-Host "    - 正在运行的 PowerModeWatcher"
Write-Host ""

# --- 1. Disable Scheduled Tasks (not delete, so enable can restore) ---
Write-Host "[1/4] Disabling scheduled tasks..."

$tasks = @("LegionProfile", "ThrottleStop_NoUAC", "LegionUpdate")
foreach ($name in $tasks) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        try {
            Disable-ScheduledTask -TaskName $name | Out-Null
            Write-Log "  [OK] $name — disabled"
        } catch {
            & schtasks.exe /change /tn $name /disable 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Log "  [OK] $name — disabled (schtasks)"
            } else {
                Write-Log "  [FAIL] $name — $_"
            }
        }
    } else {
        Write-Log "  [SKIP] $name — not found"
    }
}

# Legacy orphan task: switch_gpu.ps1 doesn't exist anymore, disable it too if present
$legacyTask = Get-ScheduledTask -TaskName "LegionGpuSwitch" -ErrorAction SilentlyContinue
if ($legacyTask) {
    try { Disable-ScheduledTask -TaskName "LegionGpuSwitch" | Out-Null; Write-Log "  [OK] LegionGpuSwitch (legacy) — disabled" } catch { & schtasks.exe /change /tn LegionGpuSwitch /disable 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { Write-Log "  [OK] LegionGpuSwitch (legacy) — disabled (schtasks)" } }
}

# --- 2. Remove Registry Run key ---
Write-Host ""
Write-Host "[2/4] Removing Registry Run key..."
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regName = "LegionOptimization"
try {
    $existing = Get-ItemProperty -Path $regPath -Name $regName -ErrorAction SilentlyContinue
    if ($null -ne $existing -and $null -ne $existing.$regName) {
        Remove-ItemProperty -Path $regPath -Name $regName -Force
        Write-Log "  [OK] Registry Run key removed"
    } else {
        Write-Log "  [SKIP] Registry Run key not present"
    }
} catch {
    Write-Log "  [FAIL] Registry Run key: $_"
}

# --- 3. Disable LLT automation.json IsEnabled ---
Write-Host ""
Write-Host "[3/4] Disabling LLT automation..."
if (Test-Path $autoJson) {
    try {
        $json = Get-Content -Path $autoJson -Raw -Encoding UTF8
        $obj  = $json | ConvertFrom-Json
        if ($obj.IsEnabled -ne $false) {
            $obj.IsEnabled = $false
            $out = $obj | ConvertTo-Json -Depth 20
            Set-Content -Path $autoJson -Value $out -Encoding UTF8 -NoNewline
            Write-Log "  [OK] automation.json IsEnabled -> false"
        } else {
            Write-Log "  [OK] automation.json already disabled"
        }
    } catch {
        try {
            $raw = Get-Content -Path $autoJson -Raw -Encoding UTF8
            $new = $raw -replace '"IsEnabled"\s*:\s*true', '"IsEnabled": false'
            if ($new -ne $raw) {
                Set-Content -Path $autoJson -Value $new -Encoding UTF8 -NoNewline
                Write-Log "  [OK] automation.json IsEnabled -> false (regex)"
            } else {
                Write-Log "  [WARN] Could not update automation.json: $_"
            }
        } catch {
            Write-Log "  [FAIL] automation.json update failed: $_"
        }
    }
} else {
    Write-Log "  [SKIP] automation.json not found: $autoJson"
}

# --- 4. Kill running PowerModeWatcher ---
Write-Host ""
Write-Host "[4/4] Stopping PowerModeWatcher..."

$killed = 0

# 4a. Preferred: PID file (reliable even when WMI CommandLine is not visible to non-admin)
if (Test-Path $pidFile) {
    try {
        $watcherPid = [int]((Get-Content $pidFile -Raw -Encoding ASCII).Trim())
        $proc = Get-Process -Id $watcherPid -ErrorAction SilentlyContinue
        if ($proc) {
            try {
                Stop-Process -Id $watcherPid -Force -ErrorAction Stop
                Write-Log "  [OK] Watcher PID=$watcherPid killed (via pid file)"
                $killed++
            } catch {
                # Fallback: WMI terminate (may have higher privilege)
                try { (Get-WmiObject Win32_Process -Filter "ProcessId=$watcherPid" -ErrorAction SilentlyContinue).Terminate() | Out-Null; Write-Log "  [OK] Watcher PID=$watcherPid terminated (WMI)"; $killed++ } catch { Write-Log "  [FAIL] Kill PID=$watcherPid : $_" }
            }
        } else {
            Write-Log "  [SKIP] PID file points to $watcherPid but process not running (stale)"
        }
    } catch {
        Write-Log "  [WARN] PID file read failed: $_"
    }
}

# 4b. Fallback: CIM/WMI CommandLine search (for old watcher without pid file)
if ($killed -eq 0) {
    try {
        $watchers = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*PowerModeWatcher.ps1*" }
        foreach ($w in $watchers) {
            try {
                Stop-Process -Id $w.ProcessId -Force -ErrorAction Stop
                Write-Log "  [OK] Watcher PID=$($w.ProcessId) killed (CIM)"
                $killed++
            } catch {
                Write-Log "  [FAIL] Kill PID=$($w.ProcessId): $_"
            }
        }
        if ($killed -eq 0 -and $watchers) { Write-Log "  [SKIP] No watcher matched CIM filter" }
    } catch {
        Write-Log "  [WARN] CIM enumerate failed: $_"
    }
}
if ($killed -eq 0) {
    try {
        $procs = Get-WmiObject Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*PowerModeWatcher*" }
        foreach ($p in $procs) {
            try { $p.Terminate() | Out-Null; Write-Log "  [OK] Watcher PID=$($p.ProcessId) terminated (WMI)"; $killed++ } catch {}
        }
        if ($killed -eq 0 -and -not (Test-Path $pidFile)) {
            Write-Log "  [SKIP] No running Watcher found"
        } elseif ($killed -eq 0 -and (Test-Path $pidFile)) {
            # pid file existed but kill via CIM/WMI also failed; still report
            Write-Log "  [SKIP] No running Watcher found via WMI"
        }
    } catch {}
}

# Clean up pid file
if (Test-Path $pidFile) {
    try { Remove-Item $pidFile -Force -ErrorAction Stop; Write-Log "  [OK] watcher.pid removed" } catch { Write-Log "  [WARN] watcher.pid remove failed: $_" }
}

# Remove stale lock file so next enable starts cleanly
$lockFile = "$scriptDir\watcher.lock"
if (Test-Path $lockFile) {
    try {
        $fs = [System.IO.File]::Open($lockFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        $fs.Close()
        Remove-Item $lockFile -Force -ErrorAction Stop
        Write-Log "  [OK] Stale watcher.lock removed"
    } catch {
        Write-Log "  [SKIP] watcher.lock still locked or in use, kept"
    }
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  Disable complete. All auto-tuning paused."
Write-Host "  - Fn+Q 将不再触发 CPU 调优"
Write-Host "  - 开机不再自动启动 LLT + Watcher"
Write-Host "  - 计划任务已禁用（未删除）"
Write-Host ""
Write-Host "  恢复方法: 右键以管理员身份运行 enable.ps1 / enable.bat"
Write-Host "============================================================"
Write-Log "[disable] Done"
Read-Host "Press Enter to exit"
