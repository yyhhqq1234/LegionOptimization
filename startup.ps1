# startup.ps1 — Boot-time FIVR injection (fire-and-forget)
# Called by LegionProfile scheduled task at logon+30s (HIGHEST privilege)
$scriptDir = $PSScriptRoot
$logFile = "$scriptDir\switch_log.txt"
$tsDir = "$scriptDir\ThrottleStop"
$tsIni = "$tsDir\ThrottleStop.ini"

"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] startup.ps1: checking power source..." | Out-File $logFile -Append -Encoding UTF8

# Detect AC vs Battery
$battery = Get-WmiObject Win32_Battery -ErrorAction SilentlyContinue
if ($battery -and $battery.BatteryStatus -eq 1) {
    # On battery — force Quiet profile for battery life + responsiveness
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] On battery — applying Quiet profile" | Out-File $logFile -Append -Encoding UTF8

    $quietIni = "$scriptDir\ThrottleStop_profiles\quiet.ini"
    if (Test-Path $quietIni) {
        Copy-Item -Path $quietIni -Destination $tsIni -Force

        # Balanced plan + Efficient Turbo, AC+DC (match quiet.bat)
        powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e
        powercfg /setacvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 2
        powercfg /setdcvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 2
        powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 3800
        powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 3800
        powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 3800
        powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 3800
        powercfg /setactive scheme_current

        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] Quiet.ini copied, Balanced+Efficient Turbo activated" | Out-File $logFile -Append -Encoding UTF8
    }
} else {
    # On AC — keep whatever profile was last used
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] On AC — using last profile" | Out-File $logFile -Append -Encoding UTF8
}

$tsRunning = Get-Process -Name "ThrottleStop" -ErrorAction SilentlyContinue

if (-not $tsRunning) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS not running, launching via schtasks..." | Out-File $logFile -Append -Encoding UTF8

    Start-Process -FilePath "schtasks.exe" -ArgumentList "/run /tn ThrottleStop_NoUAC" -WindowStyle Hidden -Wait
    Start-Sleep -Seconds 3

    # Verify TS actually started
    $tsProc = Get-Process -Name "ThrottleStop" -ErrorAction SilentlyContinue
    if ($tsProc) {
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS started, waiting 2s for FIVR..." | Out-File $logFile -Append -Encoding UTF8
        Start-Sleep -Seconds 2
    } else {
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS FAILED to start!" | Out-File $logFile -Append -Encoding UTF8
    }

    # Kill TS — FIVR MSR values persist after process exit
    & taskkill /f /t /im ThrottleStop.exe 2>&1 | Out-File $logFile -Append -Encoding UTF8
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS killed, FIVR injection complete." | Out-File $logFile -Append -Encoding UTF8
} else {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS already running, skip." | Out-File $logFile -Append -Encoding UTF8
}
