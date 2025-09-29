# Build script for Jam Deck (Windows)
# Usage: Open PowerShell, run: .\build_windows.ps1 -version "1.0.0"
param([string]$version = "1.0.0")
$ErrorActionPreference = "Stop"

Write-Host "Building Jam Deck Windows release, version $version"

# Ensure Python and pip are available (will error if not)
python --version

Write-Host "Installing build dependencies..."
pip install --upgrade pip
pip install pyinstaller pystray pillow pyperclip pyzmq win10toast

# Optional: winrt installation may require separate steps
Write-Host "Note: If you plan to use SMTC via winrt, install pywinrt with 'pip install pywinrt' and follow its installation instructions."

# Run collect_zmq if present to prepare native libs
if (Test-Path ".\collect_zmq.py") {
  Write-Host "Running collect_zmq.py to gather ZMQ binaries..."
  python .\collect_zmq.py
}

$iconPath = ".\assets\images\jamdeck.ico"
if (-not (Test-Path $iconPath)) { $iconPath = "" }

# Data files to include (source;destination)
$dataArgs = @(
  "--add-data", "overlay.html;.",
  "--add-data", "overlay.css;.",
  "--add-data", "overlay.js;.",
  "--add-data", "assets;assets"
)

# Common pyinstaller args
$common = @("--noconfirm", "--clean", "--onefile", "--windowed")
if ($iconPath) { $common += @("--icon", $iconPath) }
$common += $dataArgs

Write-Host "Building music_server.exe..."
pyinstaller @common --name "music_server" music_server.py

Write-Host "Building Jam Deck tray app (JamDeckTray.exe)..."
pyinstaller @common --name "JamDeckTray" app_windows.py

# Prepare installer staging directory
$staging = ".\dist_installer"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

# Copy built files and assets to staging
Copy-Item ".\dist\music_server.exe" $staging -ErrorAction SilentlyContinue
Copy-Item ".\dist\JamDeckTray.exe" $staging -ErrorAction SilentlyContinue
Copy-Item ".\assets" (Join-Path $staging "assets") -Recurse -Force
Copy-Item "overlay.html" $staging -ErrorAction SilentlyContinue
Copy-Item "overlay.css" $staging -ErrorAction SilentlyContinue
Copy-Item "overlay.js" $staging -ErrorAction SilentlyContinue

Write-Host "Staging completed at $staging"

# Create NSIS installer if makensis is available
if (Get-Command makensis -ErrorAction SilentlyContinue) {
  Write-Host "Found makensis - building installer using installer.nsi"
  & makensis "./installer.nsi"
} else {
  Write-Host "makensis not found. Please install NSIS and run 'makensis installer.nsi' to create the installer."
}

Write-Host "Build script finished. Check the 'dist' and 'dist_installer' folders."