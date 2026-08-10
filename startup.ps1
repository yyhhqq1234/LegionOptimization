# startup.ps1 — Boot-time FIVR injection (fire-and-forget)
# Called by LegionProfile scheduled task at logon+30s (HIGHEST privilege)
$scriptDir = $PSScriptRoot
$logFile = "$scriptDir\switch_log.txt"

"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] startup.ps1: checking TS..." | Out-File $logFile -Append -Encoding UTF8

$tsRunning = Get-Process -Name "ThrottleStop" -ErrorAction SilentlyContinue

if (-not $tsRunning) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS not running, launching via schtasks..." | Out-File $logFile -Append -Encoding UTF8

    Start-Process -FilePath "schtasks.exe" -ArgumentList "/run /tn ThrottleStop_NoUAC" -WindowStyle Hidden -Wait

    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS started, waiting 5s for FIVR..." | Out-File $logFile -Append -Encoding UTF8
    Start-Sleep -Seconds 5

    # Kill TS — FIVR MSR values persist after process exit
    & taskkill /f /t /im ThrottleStop.exe 2>&1 | Out-File $logFile -Append -Encoding UTF8
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS killed, FIVR injection complete." | Out-File $logFile -Append -Encoding UTF8
} else {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [boot] TS already running, skip." | Out-File $logFile -Append -Encoding UTF8
}
