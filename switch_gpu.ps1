# switch_gpu.ps1 — Apply GPU working mode via WMI (runs as SYSTEM via scheduled task)
# Reads mode from gpu_mode.tmp, writes result to switch_log.txt
#
# GPU Mode mapping (confirmed on Y7000 2025 IAX10 / RTX 5060):
#   0 = Hybrid Auto — Optimus auto-switch, display on iGPU, dGPU available
#   1 = dGPU Only   — RTX 5060 drives display directly (Advanced Optimus MUX)
#   2 = iGPU Only   — dGPU disabled for power saving
#
# WMI methods used:
#   SetIGPUModeStatus(mode=0|1) — 0=Hybrid(dGPU enabled), 1=iGPU Only(dGPU disabled)
#   SetDDSControlOwner(Data=0|1) — 0=iGPU drives display, 1=dGPU drives display

$scriptDir = $PSScriptRoot
$tmpFile = "$scriptDir\gpu_mode.tmp"
$logFile = "$scriptDir\switch_log.txt"

if (-not (Test-Path $tmpFile)) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [gpu] No gpu_mode.tmp found, skipping" | Out-File $logFile -Append -Encoding UTF8
    exit 0
}

try {
    $mode = [int](Get-Content $tmpFile -Raw).Trim()
} catch {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [gpu] Failed to read mode from $tmpFile" | Out-File $logFile -Append -Encoding UTF8
    exit 1
}

$modeNames = @{0="Hybrid (Auto)"; 1="dGPU Only"; 2="iGPU Only"}
$modeName = if ($modeNames.ContainsKey($mode)) { $modeNames[$mode] } else { "Unknown($mode)" }

try {
    $gz = Get-WmiObject -Namespace root\WMI -Class LENOVO_GAMEZONE_DATA -ErrorAction Stop

    # Step A: Set IGPU mode (controls dGPU availability)
    $igpuP = $gz.GetMethodParameters('SetIGPUModeStatus')
    # Step B: Set DDS owner (controls which GPU drives the display)
    $ddsP = $gz.GetMethodParameters('SetDDSControlOwner')

    if ($mode -eq 2) {
        # === iGPU Only: display on iGPU, dGPU disabled ===
        $ddsP.Data = 0;  $gz.InvokeMethod('SetDDSControlOwner', $ddsP, $null) | Out-Null
        Start-Sleep -Milliseconds 500
        $igpuP.mode = 1; $gz.InvokeMethod('SetIGPUModeStatus', $igpuP, $null) | Out-Null
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [gpu] GPU → iGPU Only (DDS=iGPU, IGPU=disabled-dGPU) [OK]" | Out-File $logFile -Append -Encoding UTF8

    } elseif ($mode -eq 0) {
        # === Hybrid Auto: display on iGPU, dGPU available via Optimus ===
        $ddsP.Data = 0;  $gz.InvokeMethod('SetDDSControlOwner', $ddsP, $null) | Out-Null
        Start-Sleep -Milliseconds 500
        $igpuP.mode = 0; $gz.InvokeMethod('SetIGPUModeStatus', $igpuP, $null) | Out-Null
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [gpu] GPU → Hybrid Auto (DDS=iGPU, IGPU=Hybrid) [OK]" | Out-File $logFile -Append -Encoding UTF8

    } elseif ($mode -eq 1) {
        # === dGPU Only: dGPU drives display directly (Advanced Optimus MUX) ===
        $igpuP.mode = 0; $gz.InvokeMethod('SetIGPUModeStatus', $igpuP, $null) | Out-Null
        Start-Sleep -Milliseconds 500
        $ddsP.Data = 1;  $gz.InvokeMethod('SetDDSControlOwner', $ddsP, $null) | Out-Null
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [gpu] GPU → dGPU Only (DDS=dGPU, IGPU=Hybrid) [OK]" | Out-File $logFile -Append -Encoding UTF8
    }

    Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
    exit 0

} catch {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [gpu] GPU WMI error: $($_.Exception.Message)" | Out-File $logFile -Append -Encoding UTF8
    Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
    exit 1
}
