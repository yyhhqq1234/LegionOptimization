# start_llt.ps1 — Silent LLT + Watcher launcher
# Runs at user logon via registry Run key (user context = GUI access)
$scriptDir = $PSScriptRoot
$logFile = "$scriptDir\switch_log.txt"

"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [startup] Launching LLT..." | Out-File $logFile -Append -Encoding UTF8

# Launch LLT — WPF app explicitly shows window, so we minimize it after launch
$lltExe = "C:\Program Files\LenovoLegionToolkit\Lenovo Legion Toolkit.exe"
Start-Process -FilePath $lltExe -WindowStyle Hidden

# Wait for LLT window to appear, then force-minimize to tray
# LLT has MinimizeToTray=true but the window still shows briefly at startup
Start-Sleep -Seconds 3
Add-Type -Name "MinimizeWindow" -Namespace "Win32" -MemberDefinition @'
[DllImport("user32.dll")]
public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
'@ -ErrorAction SilentlyContinue

$llt = Get-Process -Name "Lenovo Legion Toolkit" -ErrorAction SilentlyContinue
if ($llt -and $llt.MainWindowHandle -ne [IntPtr]::Zero) {
    # SW_MINIMIZE = 6, minimizes window; LLT's MinimizeToTray sends it to tray
    [Win32.MinimizeWindow]::ShowWindowAsync($llt.MainWindowHandle, 6) | Out-Null
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [startup] LLT minimized to tray." | Out-File $logFile -Append -Encoding UTF8
}

# Wait a bit more for LLT to fully initialize before starting watcher
Start-Sleep -Seconds 2

# Launch WMI watcher for 超能 mode (file-locked, only one instance runs)
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptDir\PowerModeWatcher.ps1`"" -WindowStyle Hidden

"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [startup] LLT + Watcher launched." | Out-File $logFile -Append -Encoding UTF8
