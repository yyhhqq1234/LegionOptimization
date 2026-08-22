# enable.ps1 — 一键启用 LegionOptimization 全部功能
# 以管理员身份运行，恢复所有自启、计划任务、LLT 自动化
# 双击 enable.bat 也可触发（自动提权）

# --- Auto-elevate ---
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "[INFO] Not Administrator, re-launching with elevation..."
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit 0
}

$scriptDir = $PSScriptRoot
$logFile   = "$scriptDir\switch_log.txt"
$tsDir     = "$scriptDir\ThrottleStop"
$lltExe    = "C:\Program Files\LenovoLegionToolkit\Lenovo Legion Toolkit.exe"
$autoJson  = "$env:LOCALAPPDATA\LenovoLegionToolkit\automation.json"
$pidFile   = "$scriptDir\watcher.pid"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Write-Host $line
    try { $line | Out-File $logFile -Append -Encoding UTF8 -ErrorAction Stop } catch {}
}

Write-Host "============================================================"
Write-Host "  LegionOptimization — Enable (一键启用)"
Write-Host "============================================================"
Write-Host ""

# --- 1. Scheduled Tasks ---
Write-Host "[1/4] Enabling scheduled tasks..."

$tasks = @(
    @{ Name="LegionProfile";      Desc="FIVR injection at logon (+30s)" },
    @{ Name="ThrottleStop_NoUAC"; Desc="ThrottleStop launcher without UAC" },
    @{ Name="LegionUpdate";       Desc="Weekly LLT update check" }
)

$needSetup = $false
foreach ($t in $tasks) {
    $task = Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue
    if ($task) {
        if ($task.Settings.Enabled -eq $false -or $task.State -eq "Disabled") {
            Enable-ScheduledTask -TaskName $t.Name | Out-Null
            Write-Log "  [OK] $($t.Name) — enabled"
        } else {
            & schtasks.exe /change /tn $t.Name /enable 2>$null | Out-Null
            Write-Log "  [OK] $($t.Name) — already enabled"
        }
        try {
            $t2 = Get-ScheduledTask -TaskName $t.Name
            if ($t2.Settings.DisallowStartIfOnBatteries -or $t2.Settings.StopIfGoingOnBatteries) {
                $t2.Settings.DisallowStartIfOnBatteries = $false
                $t2.Settings.StopIfGoingOnBatteries = $false
                Set-ScheduledTask -InputObject $t2 | Out-Null
            }
        } catch {}
    } else {
        Write-Log "  [MISS] $($t.Name) — not found, will recreate via setup_startup.ps1"
        $needSetup = $true
    }
}

if ($needSetup) {
    Write-Host ""
    Write-Host "  Some tasks missing, running setup_startup.ps1 to recreate..."
    $setupScript = "$scriptDir\setup_startup.ps1"
    if (Test-Path $setupScript) {
        "" | & powershell -NoProfile -ExecutionPolicy Bypass -File $setupScript
    } else {
        Write-Log "  [WARN] setup_startup.ps1 not found, cannot recreate tasks"
    }
}

# Also re-enable legacy LegionGpuSwitch (orphan: points to missing switch_gpu.ps1)
$legacyTask = Get-ScheduledTask -TaskName "LegionGpuSwitch" -ErrorAction SilentlyContinue
if ($legacyTask) {
    try { Enable-ScheduledTask -TaskName "LegionGpuSwitch" | Out-Null; Write-Log "  [OK] LegionGpuSwitch (legacy) — re-enabled" } catch { & schtasks.exe /change /tn LegionGpuSwitch /enable 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { Write-Log "  [OK] LegionGpuSwitch (legacy) — re-enabled (schtasks)" } }
}

# --- 2. Registry Run key (LLT + Watcher at logon) ---
Write-Host ""
Write-Host "[2/4] Restoring Registry Run key..."
$regPath  = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regName  = "LegionOptimization"
$regValue = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptDir\start_llt.ps1`""
try {
    Set-ItemProperty -Path $regPath -Name $regName -Value $regValue -Type String -Force
    Write-Log "  [OK] Registry Run key restored"
    Write-Log "       -> $regValue"
} catch {
    Write-Log "  [FAIL] Registry Run key: $_"
}

# --- 3. LLT automation.json IsEnabled ---
Write-Host ""
Write-Host "[3/4] Enabling LLT automation..."
if (Test-Path $autoJson) {
    try {
        $json = Get-Content -Path $autoJson -Raw -Encoding UTF8
        $obj  = $json | ConvertFrom-Json
        if ($obj.IsEnabled -ne $true) {
            $obj.IsEnabled = $true
            $out = $obj | ConvertTo-Json -Depth 20
            Set-Content -Path $autoJson -Value $out -Encoding UTF8 -NoNewline
            Write-Log "  [OK] automation.json IsEnabled -> true"
        } else {
            Write-Log "  [OK] automation.json already enabled"
        }
    } catch {
        try {
            $raw = Get-Content -Path $autoJson -Raw -Encoding UTF8
            $new = $raw -replace '"IsEnabled"\s*:\s*false', '"IsEnabled": true'
            if ($new -ne $raw) {
                Set-Content -Path $autoJson -Value $new -Encoding UTF8 -NoNewline
                Write-Log "  [OK] automation.json IsEnabled -> true (regex)"
            } else {
                Write-Log "  [WARN] Could not update automation.json: $_"
            }
        } catch {
            Write-Log "  [FAIL] automation.json update failed: $_"
        }
    }
} else {
    Write-Log "  [SKIP] automation.json not found: $autoJson"
    Write-Log "         Please import automation.template.json in LLT first"
}

# --- 4. Launch LLT + Watcher if not running ---
Write-Host ""
Write-Host "[4/4] Launching LLT + Watcher..."

$lltRunning = Get-Process -Name "Lenovo Legion Toolkit" -ErrorAction SilentlyContinue
if ($lltRunning) {
    Write-Log "  [OK] LLT already running (PID=$($lltRunning.Id))"
} else {
    if (Test-Path $lltExe) {
        $startScript = "$scriptDir\start_llt.ps1"
        if (Test-Path $startScript) {
            Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`"" -WindowStyle Hidden
            Write-Log "  [OK] start_llt.ps1 launched (LLT + Watcher)"
        } else {
            Start-Process -FilePath $lltExe -WindowStyle Hidden
            Write-Log "  [OK] LLT launched directly"
        }
    } else {
        Write-Log "  [WARN] LLT not found at: $lltExe"
    }
}

# Ensure watcher is running — prefer PID file check (reliable without admin), fall back to WMI
$watcherRunning = $false
if (Test-Path $pidFile) {
    try {
        $wpid = [int]((Get-Content $pidFile -Raw -Encoding ASCII).Trim())
        if (Get-Process -Id $wpid -ErrorAction SilentlyContinue) { $watcherRunning = $true }
        else { Remove-Item $pidFile -Force -ErrorAction SilentlyContinue }  # stale
    } catch {}
}
if (-not $watcherRunning) {
    try {
        $w = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*PowerModeWatcher.ps1*" }
        if ($w) { $watcherRunning = $true }
    } catch {}
}

if (-not $watcherRunning) {
    $watcherScript = "$scriptDir\PowerModeWatcher.ps1"
    if (Test-Path $watcherScript) {
        Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watcherScript`"" -WindowStyle Hidden
        Write-Log "  [OK] PowerModeWatcher launched"
    }
} else {
    Write-Log "  [OK] PowerModeWatcher already running"
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  Enable complete. All features restored."
Write-Host "  Reboot or press Fn+Q to test."
Write-Host "============================================================"
Write-Log "[enable] Done"
Read-Host "Press Enter to exit"
