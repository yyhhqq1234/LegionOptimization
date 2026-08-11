# setup_startup.ps1 - LegionOptimization Startup Setup
# Run as Administrator:
#   Right-click Start -> Terminal (Admin), paste:
#   powershell -ExecutionPolicy Bypass -File "D:\LegionOptimization\setup_startup.ps1"

# Auto-elevate if not admin
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "[INFO] Not running as Administrator. Re-launching with elevation..."
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit 0
}

$scriptDir = $PSScriptRoot
$lltExe = "C:\Program Files\LenovoLegionToolkit\Lenovo Legion Toolkit.exe"
$tsDir = "$scriptDir\ThrottleStop"

Write-Host "============================================================"
Write-Host "  LegionOptimization - Startup Setup"
Write-Host "============================================================"
Write-Host ""
Write-Host "This will configure:"
Write-Host "  1. Registry Run key   -> LLT to tray at logon (user)"
Write-Host "  2. LegionProfile      -> FIVR injector on boot (+30s)"
Write-Host "  3. ThrottleStop_NoUAC -> TS launcher without UAC"
Write-Host "  4. LegionUpdate       -> Weekly update (Sun 3AM)"
Write-Host ""
Write-Host "  GPU mode: use NVIDIA App to switch manually (iGPU/Hybrid/dGPU)"
Write-Host "============================================================"
Write-Host ""

# === File Verification ===
Write-Host "--- File Verification ---"
$files = @(
    @("LLT", $lltExe),
    @("ThrottleStop", "$tsDir\ThrottleStop.exe"),
    @("start_llt.ps1", "$scriptDir\start_llt.ps1"),
    @("startup.ps1", "$scriptDir\startup.ps1"),
    @("PowerModeWatcher.ps1", "$scriptDir\PowerModeWatcher.ps1"),
    @("check_update.ps1", "$scriptDir\check_update.ps1")
)

$allOk = $true
foreach ($f in $files) {
    if (Test-Path $f[1]) {
        Write-Host "  [OK] $($f[0])"
    } else {
        Write-Host "  [MISSING] $($f[0]) : $($f[1])"
        $allOk = $false
    }
}

if (-not $allOk) {
    Write-Host ""
    Write-Host "[ERROR] Some files missing."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  All files found."
Write-Host ""

# === Task 1: Registry Run key ===
Write-Host "[1/4] LLT auto-start (Registry Run key)..."

# Delete old LegionLLT scheduled task
& schtasks.exe /delete /tn "LegionLLT" /f 2>$null

# Add registry Run key (user context -> GUI visible)
$regValue = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptDir\start_llt.ps1`""
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
    -Name "LegionOptimization" -Value $regValue -Type String -Force
Write-Host "  [OK] Registry Run key added"
Write-Host "       -> starts LLT (tray) + Watcher at every logon"

# === Task 2: LegionProfile ===
Write-Host ""
Write-Host "[2/4] LegionProfile (FIVR inject +30s)..."

& schtasks.exe /delete /tn "LegionProfile" /f 2>$null
$tr2 = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptDir\startup.ps1`""
& schtasks.exe /create /tn "LegionProfile" /tr $tr2 /sc ONLOGON /delay 0000:30 /rl HIGHEST /f
if ($LASTEXITCODE -eq 0) {
    # Allow running on battery (scheduled tasks block battery by default)
    $lpTask = Get-ScheduledTask -TaskName "LegionProfile"
    $lpTask.Settings.DisallowStartIfOnBatteries = $false
    $lpTask.Settings.StopIfGoingOnBatteries = $false
    Set-ScheduledTask -InputObject $lpTask | Out-Null
    Write-Host "  [OK] LegionProfile created (battery allowed)"
} else {
    Write-Host "  [FAILED] Exit code: $LASTEXITCODE"
}

# === Task 3: ThrottleStop_NoUAC ===
Write-Host ""
Write-Host "[3/4] ThrottleStop_NoUAC..."

& schtasks.exe /delete /tn "ThrottleStop_NoUAC" /f 2>$null
$tsExe = "$tsDir\ThrottleStop.exe"
& schtasks.exe /create /tn "ThrottleStop_NoUAC" /tr $tsExe /sc ONCE /st 00:00 /rl HIGHEST /f
if ($LASTEXITCODE -eq 0) {
    # Allow running on battery (scheduled tasks block battery by default)
    $tsTask = Get-ScheduledTask -TaskName "ThrottleStop_NoUAC"
    $tsTask.Settings.DisallowStartIfOnBatteries = $false
    $tsTask.Settings.StopIfGoingOnBatteries = $false
    Set-ScheduledTask -InputObject $tsTask | Out-Null
    Write-Host "  [OK] ThrottleStop_NoUAC created (battery allowed)"
} else {
    Write-Host "  [FAILED] Exit code: $LASTEXITCODE"
}

# === Task 4: LegionUpdate ===
Write-Host ""
Write-Host "[4/4] LegionUpdate (weekly update check)..."

& schtasks.exe /delete /tn "LegionUpdate" /f 2>$null
$tr4 = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptDir\check_update.ps1`""
& schtasks.exe /create /tn "LegionUpdate" /tr $tr4 /sc WEEKLY /d SUN /st 03:00 /rl HIGHEST /f
if ($LASTEXITCODE -eq 0) {
    # Allow running on battery (scheduled tasks block battery by default)
    $luTask = Get-ScheduledTask -TaskName "LegionUpdate"
    $luTask.Settings.DisallowStartIfOnBatteries = $false
    $luTask.Settings.StopIfGoingOnBatteries = $false
    Set-ScheduledTask -InputObject $luTask | Out-Null
    Write-Host "  [OK] LegionUpdate created (battery allowed)"
} else {
    Write-Host "  [FAILED] Exit code: $LASTEXITCODE"
}

# === Verification ===
Write-Host ""
Write-Host "=== Verification ==="
Write-Host ""

Write-Host "[Registry] HKCU:\...\Run\LegionOptimization:"
$reg = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
    -Name "LegionOptimization" -ErrorAction SilentlyContinue
if ($reg) {
    Write-Host "  $($reg.LegionOptimization)"
} else {
    Write-Host "  NOT FOUND"
}

Write-Host ""
Write-Host "[Scheduled Tasks]"
@("LegionProfile", "ThrottleStop_NoUAC", "LegionUpdate") | ForEach-Object {
    $task = Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue
    if ($task) {
        $action = $task.Actions[0]
        Write-Host "  $_ : $($task.State)"
        Write-Host "    Run: $($action.Execute) $($action.Arguments)"
    } else {
        Write-Host "  $_ : NOT FOUND"
    }
}

# Warn about old LegionGpuSwitch task if it still exists
$oldGpuTask = Get-ScheduledTask -TaskName "LegionGpuSwitch" -ErrorAction SilentlyContinue
if ($oldGpuTask) {
    Write-Host ""
    Write-Host "  [!] LegionGpuSwitch still exists (from previous setup)."
    Write-Host "      Run: schtasks /delete /tn LegionGpuSwitch /f"
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  Setup complete. Reboot to test."
Write-Host "  GPU mode: switch manually in NVIDIA App (no auto-switching)"
Write-Host "============================================================"
Read-Host "Press Enter to exit"
