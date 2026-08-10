# check_update.ps1 — Lenovo Legion Toolkit Auto-Update
# Checks GitHub for latest release, installs silently if newer
# Preserves automation.json (user data in AppData)
# Runs weekly via LegionUpdate scheduled task (HIGHEST privilege)

$scriptDir = $PSScriptRoot
$logFile = "$scriptDir\update_log.txt"
$installerPath = "$env:TEMP\LLT_Setup.exe"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
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

Write-Log "=== Update check started ==="

# ============================================================
# 1. Get installed version
# ============================================================
$installedExe = "C:\Program Files\LenovoLegionToolkit\Lenovo Legion Toolkit.exe"

if (-not (Test-Path $installedExe)) {
    Write-Log "ERROR: LLT not installed at $installedExe"
    exit 1
}

try {
    $installedVersion = [Version]((Get-Item $installedExe).VersionInfo.FileVersion)
    Write-Log "Installed version: $installedVersion"
} catch {
    Write-Log "ERROR: Cannot read installed version: $_"
    exit 1
}

# ============================================================
# 2. Check GitHub API for latest release
# ============================================================
try {
    # Use Invoke-RestMethod with timeout and user-agent (GitHub API requires User-Agent)
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/LenovoLegionToolkit-Team/LenovoLegionToolkit/releases/latest" `
        -TimeoutSec 30 `
        -Headers @{ "User-Agent" = "LegionOptimization-Updater/1.0" } `
        -ErrorAction Stop

    $tagName = $release.tag_name
    Write-Log "Latest release tag: $tagName"

    # Parse version from tag_name (e.g., "v2.34.0.0" → "2.34.0.0")
    $latestVersionStr = $tagName -replace '^v', ''
    $latestVersion = [Version]$latestVersionStr
    Write-Log "Latest version: $latestVersion"
} catch {
    Write-Log "WARNING: Cannot check GitHub API: $_"
    Write-Log "Skipping update check (network or API issue)."
    exit 0
}

# ============================================================
# 3. Compare versions
# ============================================================
if ($latestVersion -le $installedVersion) {
    Write-Log "Already up to date ($installedVersion >= $latestVersion). Nothing to do."
    exit 0
}

Write-Log "New version available: $latestVersion > $installedVersion"
Write-Log "Starting update..."

# ============================================================
# 4. Download installer
# ============================================================
$downloadUrl = $null
foreach ($asset in $release.assets) {
    $name = $asset.name
    # Match installer .exe (e.g., "LenovoLegionToolkitSetup_2.34.0.0.exe")
    if ($name -match '\.exe$' -and $name -match 'setup', 'Setup', 'install', 'Install') {
        $downloadUrl = $asset.browser_download_url
        Write-Log "Found installer: $name"
        break
    }
}

# Fallback: any .exe asset
if (-not $downloadUrl) {
    foreach ($asset in $release.assets) {
        if ($asset.name -match '\.exe$') {
            $downloadUrl = $asset.browser_download_url
            Write-Log "Fallback installer: $($asset.name)"
            break
        }
    }
}

if (-not $downloadUrl) {
    Write-Log "ERROR: No installer .exe found in GitHub release assets."
    exit 1
}

Write-Log "Downloading: $downloadUrl"
try {
    # Clean up old installer
    if (Test-Path $installerPath) { Remove-Item $installerPath -Force }

    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -TimeoutSec 300 -ErrorAction Stop
    Write-Log "Downloaded to: $installerPath"
    Write-Log "File size: $((Get-Item $installerPath).Length) bytes"
} catch {
    Write-Log "ERROR: Download failed: $_"
    exit 1
}

# ============================================================
# 5. Verify automation.json exists before update
# ============================================================
$automationJson = "$env:LOCALAPPDATA\LenovoLegionToolkit\automation.json"
$autoExistedBefore = Test-Path $automationJson
Write-Log "automation.json exists before update: $autoExistedBefore"
if ($autoExistedBefore) {
    $autoBackup = "$scriptDir\automation.backup.json"
    Copy-Item $automationJson $autoBackup -Force
    Write-Log "Backed up automation.json to $autoBackup"
}

# ============================================================
# 6. Run installer silently
# ============================================================
Write-Log "Running installer silently..."
try {
    $proc = Start-Process -FilePath $installerPath `
        -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS" `
        -Wait -PassThru -NoNewWindow

    $exitCode = $proc.ExitCode
    Write-Log "Installer exited with code: $exitCode"

    if ($exitCode -ne 0) {
        Write-Log "WARNING: Installer returned non-zero exit code: $exitCode"
    }
} catch {
    Write-Log "ERROR: Installer failed: $_"
    exit 1
}

# ============================================================
# 7. Post-update verification
# ============================================================
Write-Log "=== Post-update verification ==="

# Check new version
if (Test-Path $installedExe) {
    $newVersion = [Version]((Get-Item $installedExe).VersionInfo.FileVersion)
    Write-Log "New installed version: $newVersion"
    if ($newVersion -ge $latestVersion) {
        Write-Log "Version check: OK — updated to $newVersion"
    } else {
        Write-Log "WARNING: Version mismatch — expected $latestVersion, got $newVersion"
    }
} else {
    Write-Log "ERROR: LLT exe missing after update!"
}

# Check automation.json
$autoExistedAfter = Test-Path $automationJson
Write-Log "automation.json exists after update: $autoExistedAfter"

if ($autoExistedBefore -and -not $autoExistedAfter) {
    Write-Log "WARNING: automation.json lost! Restoring from backup..."
    Copy-Item $autoBackup $automationJson -Force
    Write-Log "Restored automation.json from backup."
}

# Clean up
if (Test-Path $installerPath) {
    Remove-Item $installerPath -Force
    Write-Log "Cleaned up installer file."
}
if (Test-Path $autoBackup) {
    Remove-Item $autoBackup -Force
}

# ============================================================
# 8. Restart LLT
# ============================================================
Write-Log "Starting LLT..."
Start-Process -FilePath $installedExe -WindowStyle Hidden
Write-Log "LLT restarted."

Write-Log "=== Update check completed ==="
exit 0
