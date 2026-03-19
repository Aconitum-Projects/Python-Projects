Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$mainIconPng = Join-Path $PSScriptRoot "icons\Main.png"
$mainIconIco = Join-Path $PSScriptRoot "icons\Main.ico"

if (Test-Path $mainIconPng) {
  uv run python -c "from PIL import Image; img = Image.open(r'$mainIconPng').convert('RGBA'); img.save(r'$mainIconIco', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
} else {
  Write-Warning "Icone principale introuvable: $mainIconPng"
}

# Build a Windows executable with config files next to the .exe
$buildRoot = Join-Path $PSScriptRoot "build"
$distRoot = Join-Path $buildRoot "dist"
$workRoot = Join-Path $buildRoot "work"
$specRoot = Join-Path $buildRoot "spec"

if (-not (Test-Path $distRoot)) {
  New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
}

if (-not (Test-Path $workRoot)) {
  New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
}

if (-not (Test-Path $specRoot)) {
  New-Item -ItemType Directory -Path $specRoot -Force | Out-Null
}

uv run --with pyinstaller pyinstaller `
  --noconfirm `
  --clean `
  --name Blink_Doctor `
  --onedir `
  --windowed `
  --distpath "$distRoot" `
  --workpath "$workRoot" `
  --specpath "$specRoot" `
  --icon "$mainIconIco" `
  --collect-all mediapipe `
  --collect-all cv2 `
  main.py

$distDir = Join-Path $distRoot "Blink_Doctor"
$configSource = Join-Path $PSScriptRoot "config"
$configTarget = Join-Path $distDir "config"
$iconsSource = Join-Path $PSScriptRoot "icons"
$iconsTarget = Join-Path $distDir "icons"
$soundsSource = Join-Path $PSScriptRoot "sounds"
$soundsTarget = Join-Path $distDir "sounds"

if (Test-Path $configTarget) {
  Remove-Item $configTarget -Recurse -Force
}

Copy-Item $configSource $configTarget -Recurse -Force

if (Test-Path $iconsTarget) {
  Remove-Item $iconsTarget -Recurse -Force
}

Copy-Item $iconsSource $iconsTarget -Recurse -Force

if (Test-Path $soundsTarget) {
  Remove-Item $soundsTarget -Recurse -Force
}

if (Test-Path $soundsSource) {
  Copy-Item $soundsSource $soundsTarget -Recurse -Force
} else {
  Write-Warning "Dossier sounds introuvable: $soundsSource"
}

Write-Host "Build termine. Executable: $distRoot\Blink_Doctor\Blink_Doctor.exe"