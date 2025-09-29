# Build script for Jam Deck (Windows)
# Usage: Open PowerShell, run: .\build_windows.ps1 -version "1.0.0"
param([string]$version = "1.0.0")
$ErrorActionPreference = "Stop"

Write-Host "Building Jam Deck Windows release, version $version"

# Ensure Python and pip are available (will error if not)
python --version

Write-Host "Installing build dependencies..."
pip install --upgrade pip
pip install pyinstaller pystray pillow pyperclip pyzmq modulegraph win10toast winrt-runtime winrt-Windows.Media.Control winrt-Windows.Foundation winrt-Windows.Foundation.Collections winrt-Windows.Storage winrt-Windows.Storage.Streams 

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
# Separate args for server (console) and tray (windowed) so logs are visible for the server.
$commonBase = @("--noconfirm", "--clean", "--onefile")
# Build the tray app as windowed (no console)
$trayArgs = $commonBase + @("--windowed")
# Build the server as windowed (no console). Debug lines are written to logs/overlay.log when enabled.
$serverArgs = $commonBase + @("--windowed")
if ($iconPath) {
  $trayArgs += @("--icon", $iconPath)
  $serverArgs += @("--icon", $iconPath)
}
# Include data files for both builds
# Ensure hidden imports for modules that may be dynamically imported at runtime
# (PyInstaller sometimes misses stdlib or dynamically imported modules such as 'uuid' or
# packages like 'winrt' used via runtime bindings). Adding them explicitly prevents
# "No module named 'uuid'" or missing winrt submodule errors in the bundled executable.
$hiddenImports = @(
  "--hidden-import", "winrt.windows.media.control",
  "--hidden-import", "winrt.windows.foundation",
  "--hidden-import", "winrt.windows.foundation.collections",
  "--hidden-import", "winrt.windows.storage.streams"
)
$trayArgs += $hiddenImports
$serverArgs += $hiddenImports
$trayArgs += $dataArgs
$serverArgs += $dataArgs

# Build both the headless server and the tray app:
# - music_server.exe: the HTTP server that serves the overlay and reads SMTC information.
# - JamDeckTray.exe: the Windows system-tray GUI which can launch/control the server as a subprocess.
# We intentionally build both executables so users can either run the server standalone
# or use the tray app which manages the server and provides an easy UI.
# After building we copy both .exe files into the staging folder `dist_installer`.
Write-Host "Building music_server.exe (windowed)..."
pyinstaller @serverArgs --name "music_server" music_server.py

Write-Host "Building Jam Deck tray app (JamDeckTray.exe) (windowed)..."
pyinstaller @trayArgs --name "JamDeckTray" app_windows.py

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