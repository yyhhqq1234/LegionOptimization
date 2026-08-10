# PowerModeWatcher.ps1 — Standalone WMI Power Mode Monitor
# Handles 超能/Extreme mode (WMI mode=224)
# Uses file lock to prevent duplicate instances

$scriptDir = $PSScriptRoot
$logFile = "$scriptDir\watcher_log.txt"
$lockFile = "$scriptDir\watcher.lock"

# File lock: prevent duplicate instances
try {
    $lock = [System.IO.File]::Open($lockFile, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    $lock.Lock(0, 1) | Out-Null
} catch {
    exit 0
}

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'HH:mm:ss.fff') $msg"
    $retry = 0
    while ($retry -lt 3) {
        try {
            $line | Out-File $logFile -Append -Encoding UTF8 -ErrorAction Stop
            break
        } catch {
            $retry++
            Start-Sleep -Milliseconds 100
        }
    }
}

Write-Log "=== Watcher v2 started (PID=$pid) ==="
Write-Log "Listening for 超能/Extreme (mode=224)..."

$scope = New-Object System.Management.ManagementScope("\\.\root\WMI")
$query = New-Object System.Management.WqlEventQuery("SELECT * FROM LENOVO_GAMEZONE_THERMAL_MODE_EVENT")
$watcher = New-Object System.Management.ManagementEventWatcher($scope, $query)

$watcher.Start()

while ($true) {
    try {
        $evt = $watcher.WaitForNextEvent()
        $raw = [string]$evt.Properties["mode"].Value
        Write-Log "Event: mode=$raw"

        if ($raw -eq '224') {
            Write-Log "超能 mode detected - running custom.bat"
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$scriptDir\custom.bat`"" -WindowStyle Hidden
        } else {
            Write-Log "Skipping mode=$raw (LLT handles it)"
        }
    } catch {
        Write-Log "Loop error: $($_.Exception.Message)"
        Start-Sleep -Seconds 2
    }
}

# Never reached unless loop breaks
$watcher.Stop()
$lock.Close()
Write-Log "=== Watcher stopped ==="
