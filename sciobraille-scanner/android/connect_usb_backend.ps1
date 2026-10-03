param(
    [switch]$InstallApk
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adb)) {
    throw "ADB was not found at $adb. Install Android SDK Platform Tools first."
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8088/api/health" -TimeoutSec 5
    if (-not $health.ok) {
        throw "Backend health response was not OK."
    }
} catch {
    throw "Sciobraille backend is not reachable on laptop port 8088. Start backend\start_backend.bat first."
}

& $adb start-server | Out-Null
$deviceLines = & $adb devices
$authorizedDevices = @(
    $deviceLines |
        Select-Object -Skip 1 |
        Where-Object { $_ -match "\tdevice$" } |
        ForEach-Object { ($_ -split "\t")[0] }
)
$unauthorizedDevices = @($deviceLines | Where-Object { $_ -match "\tunauthorized$" })

if ($unauthorizedDevices.Count -gt 0) {
    throw "Phone is connected but unauthorized. Unlock it and accept the USB debugging prompt."
}
if ($authorizedDevices.Count -eq 0) {
    throw "No authorized Android phone found. Enable Developer options and USB debugging, then reconnect the data cable."
}
if ($authorizedDevices.Count -gt 1) {
    throw "More than one Android device is connected. Disconnect the extra device and run this again."
}

$serial = $authorizedDevices[0]

if ($InstallApk) {
    $apk = (Resolve-Path (Join-Path $PSScriptRoot "..\releases\Sciobraille-v1.1.9-USB.apk")).Path
    Write-Host "Installing USB APK..."
    & $adb -s $serial install -r $apk
    if ($LASTEXITCODE -ne 0) {
        throw "APK installation failed. If Android reports an incompatible signature, uninstall the old Sciobraille app and run this again."
    }
}

$existingReverseList = & $adb -s $serial reverse --list
if ($existingReverseList -match "tcp:8000\s+") {
    & $adb -s $serial reverse --remove "tcp:8000" | Out-Null
}
& $adb -s $serial reverse "tcp:8000" "tcp:8088" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "ADB reverse failed. Reconnect the phone and confirm USB debugging authorization."
}

$reverseList = & $adb -s $serial reverse --list
if ($reverseList -notmatch "tcp:8000\s+tcp:8088") {
    throw "ADB did not report the expected tcp:8000 to tcp:8088 tunnel."
}

Write-Host ""
Write-Host "Sciobraille USB backend connection is ready." -ForegroundColor Green
Write-Host "Phone:   $serial"
Write-Host "Android: http://127.0.0.1:8000"
Write-Host "Laptop:  http://127.0.0.1:8088"
Write-Host "Model:   $($health.model)"
Write-Host ""
Write-Host "Keep this USB cable connected. Run this script again after reconnecting or restarting the phone."
