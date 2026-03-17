Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

# Build a Windows executable with config files next to the .exe
uv run --with pyinstaller pyinstaller `
  --noconfirm `
  --clean `
  --name RD_Blink `
  --onedir `
  --collect-all mediapipe `
  --collect-all cv2 `
  main.py

$distDir = Join-Path $PSScriptRoot "dist\RD_Blink"
$configSource = Join-Path $PSScriptRoot "config"
$configTarget = Join-Path $distDir "config"

if (Test-Path $configTarget) {
  Remove-Item $configTarget -Recurse -Force
}

Copy-Item $configSource $configTarget -Recurse -Force

Write-Host "Build termine. Executable: $PSScriptRoot\dist\RD_Blink\RD_Blink.exe"