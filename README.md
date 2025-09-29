# Jam Deck for OBS: Apple Music Stream Display

A customizable Apple Music now playing display for Windows.

![Preview of Jam Deck overlay](assets/images/preview.png)

## Quick Links
- [Download](https://github.com/detekoi/jam-deck/releases/)
- [Installation](#installation)
- [Setting Up OBS](#setting-up-obs)
- [Theme Selection](#theme-selection)

## Features

- Shows currently playing Apple Music track on your stream with artwork.
- Ten versatile themes (5 rounded: Natural, Twitch, Dark, Pink, Light and 5 square: Transparent, Neon, Terminal, Retro, High Contrast).
- Adaptive or Fixed width display options.
- Automatically hides when no music is playing.
- Clean animated transitions between songs.
- Theme menu appears only on hover (invisible to viewers).
- Scene-specific settings saved between sessions.
- Menu bar app for easy access to server controls and scene management.
- One-click scene URL copying for easy OBS setup.
- Scrolling text marquee effect for long song/artist names.
- Automatic port selection if default port (8080) is in use.

## Requirements

- Windows 10/11 (SMTC-based Apple Music from Microsoft Store).
- OBS Studio or similar streaming software with browser source support.

### Windows-specific notes
- On Windows the Apple Music app is a Microsoft Store UWP app. This fork supports Windows via the System Media Transport Controls (SMTC) where available.
- Recommended Python packages for Windows:
  - python >= 3.8
  - pywinrt (winrt) — for SMTC access (pip install pywinrt)
  - pystray — system tray icon (pip install pystray pillow)
  - pyperclip — clipboard handling (pip install pyperclip)
  - win10toast or plyer — native notifications (pip install win10toast)
  - pyzmq — ZeroMQ support (pip install pyzmq)
  - pyinstaller — for creating .exe builds (pip install pyinstaller)

## Installation

### Recommended: Tray App

1. Download the latest Jam Deck Windows release from the [Releases](https://github.com/detekoi/jam-deck/releases/) page.
2. Run the installer or extract the archive to a chosen folder.
3. Launch Jam Deck; it will appear in the system tray (notification area).
4. The server starts automatically when you launch the app.

To continue, jump to [Tray App](#tray-app).

<details>
<summary><h3>Advanced: Manual Installation (Windows)</h3></summary>

**Requirements:**
- Python 3.8 or later

Steps:
1. Clone this repository:
   ```powershell
   git clone https://github.com/yourusername/jam-deck.git
   cd jam-deck
   ```

2. Install required Python packages:
   ```powershell
   pip install pywinrt pystray pyperclip pyzmq pillow win10toast
   ```

3. Start the server:
   ```powershell
   python music_server.py
   ```

</details>

## Usage

Once installed, the overlay will automatically display your currently playing Apple Music tracks.

### Tray App

Jam Deck's tray app provides easy access to all features directly from your system tray (notification area):

1. **Server Control**
   - Click "Start Server" to begin displaying your music.
   - Click "Stop Server" when you're done streaming.

2. **Scene Management**
   - Under "Copy Scene URL," select any scene to copy its URL to the clipboard.
   - Each scene can have unique theme and width settings.
   - Use "Add New Scene..." to create custom scenes for different parts of your stream.
   - Use "Manage Scenes..." to rename or delete existing scenes.

3. **Browser Integration**
   - Click "Open in Browser" to preview how the default overlay looks.

## Setting Up OBS

To add Jam Deck to your OBS scene:

1. In OBS Studio, select the scene where you want to display your music.
2. In the Sources panel, click the `+` button.
3. Select `Browser` from the list of sources.
4. Choose `Create New` and give it a name (e.g., "Now Playing Music").
5. Click `OK`.
6. In the Browser Source properties:
   - URL: Use the app to copy a scene-specific URL. The default URL is `http://localhost:8080/`
   - Width: 400 (recommended minimum)
   - Height: 140
   - Check "Refresh browser when scene becomes active."
7. Click `OK` to add the browser source.

### Theme Selection

Hover over the overlay and right-click > Interact, or select the Source and press the Interact button below the preview to reveal the settings menu:

#### Rounded Themes
- **Natural** (default): Soft green theme with rounded corners.
- **Twitch**: Dark purple theme that matches Twitch aesthetics.
- **Dark**: Sleek black theme with cyan accents.
- **Pink**: Vibrant pink theme with friendly typography.
- **Light**: Clean white theme with blue accents.

#### Square Themes
- **Transparent**: Minimalist theme with no background, just text and artwork.
- **Neon**: Cyberpunk-inspired theme with glowing cyan text on black background.
- **Terminal**: Green-on-black theme reminiscent of classic computer terminals.
- **Retro**: Blue and yellow theme using pixel-style Press Start 2P font.
- **High Contrast**: Black and white theme with Atkinson Hyperlegible font optimized for maximum readability.

**Note about Settings Storage**: Theme and width preferences are stored separately in each browser's local storage. This means settings selected in your regular browser (Chrome, Safari, etc.) won't automatically appear in OBS. You'll need to configure your preferred settings once in each environment where you use Jam Deck.

### Width Options

In the settings menu:

- **A**: Adaptive width (only as wide as needed for the text).
- **F**: Fixed width (expands to fill the entire browser source width, default).

## Troubleshooting

<details>
<summary>No music information appears</summary>

- Make sure the server is running.
- Make sure Apple Music is running.
- Try playing/pausing music to trigger an update.

</details>

<details>
<summary>Permission errors</summary>

- Windows requires that the Apple Music (Microsoft Store) app expose playback through the System Media Transport Controls (SMTC). If now-playing information does not appear, make sure the media app is running and playing.
- If SMTC data is not available for Apple Music, try playing media in another app that supports SMTC (e.g., Groove, Spotify UWP) to verify SMTC access.
- If you see permission-related behavior from antivirus or UWP settings, ensure the media app is allowed to report media sessions.

</details>

## Auto-Start on Boot

<details>
<summary>Auto-start on Windows</summary>

Using the Tray App:
1. Create a shortcut to the Jam Deck executable and place it in the user's Startup folder:
   - Press Win+R, enter: shell:startup
   - Paste the Jam Deck shortcut into that folder.

Using Task Scheduler (optional, more control):
1. Open Task Scheduler and create a new task.
2. Configure it to run at user logon and point the action to the Jam Deck executable.
3. Set "Run only when user is logged on" (or configure otherwise as needed).

Using Manual Installation:
1. Create a shortcut that runs: `python C:\path\to\jam-deck\music_server.py`
2. Place that shortcut in the Startup folder or configure a Task Scheduler task.

</details>

## Customization

Advanced users can modify the CSS in `overlay.css` to create custom themes or change the layout.

### Changing the Port

The server automatically starts on port 8080. If this port is already in use, it will automatically find and use the next available port. The selected port will be displayed in the menu bar app and system notifications.

If you need to manually specify a different port (Manual installation only):

1. Open `music_server.py` in a text editor.
2. Find the line near the top that says `PORT = 8080`
3. Change `8080` to your desired port number.
4. Save the file and restart the server.
5. Update your browser source URL in OBS to use the new port.

## Building from Source

**Requirements:**
- Python 3.8 or later
- Windows 10 or 11
- pyinstaller (for creating .exe builds)
- NSIS or Inno Setup (for building installers)

If you want to build the Jam Deck menu bar app from source:

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/jam-deck.git
   cd jam-deck
   ```

Note: macOS py2app packaging is no longer the primary build flow for this fork.
If you need to produce macOS bundles you can re-enable py2app on a macOS build host,
but for Windows builds please use the instructions in "Windows build notes" above.

To build for Windows, use the provided PowerShell helper or PyInstaller spec files:
- PowerShell automated build: `.\build_windows.ps1 -version "1.0.0"`
- Or run PyInstaller manually:
  - pip install pyinstaller
  - pyinstaller --onefile --add-data "overlay.html;." --add-data "overlay.css;." --add-data "overlay.js;." music_server.py
  - pyinstaller --onefile --add-data "overlay.html;." --add-data "overlay.css;." --add-data "overlay.js;." app_windows.py

### Build Scripts

- `build.sh`: Automated build script for building the packaged application.
- `collect_zmq.py`: Helper script to ensure ZeroMQ libraries are properly included in the build.

Windows build notes:
- This repository includes a Windows-friendly tray app `app_windows.py` and a cross-platform server `music_server.py`.
- To build a Windows executable, use PyInstaller and then create an installer with NSIS or Inno Setup. Example commands:
  - pip install pyinstaller
  - pyinstaller --onefile --add-data "overlay.html;." --add-data "overlay.css;." --add-data "overlay.js;." music_server.py
  - Package the resulting .exe with NSIS or Inno Setup to create an installer.

### Script/Build Permissions
 
On Windows, ensure you run PowerShell or the Command Prompt with sufficient privileges when creating installers or writing files to protected locations. For PyInstaller builds, run from a normal user shell; for installer creation with NSIS/Inno, elevated privileges may be required to place files in Program Files when testing installation.

### Environment Considerations
 
Make sure that the necessary Windows tools and Python packages are installed and accessible in your system's PATH. Important items:
- Python and pip
- pywinrt (winrt) for SMTC access
- pyinstaller for creating executables
- NSIS or Inno Setup for creating installers
- Pillow, pystray, pyperclip, pyzmq and win10toast (or plyer) as runtime dependencies

## Font Attribution

- The Retro theme uses Press Start 2P font by CodeMan38 (licensed under SIL Open Font License), with Retro Gaming font by Daymarius as fallback.
- The High Contrast theme uses Atkinson Hyperlegible font designed by the Braille Institute for improved readability.
- JetBrains Mono font is used as a monospaced font for the Terminal theme.

All fonts are licensed under the [SIL Open Font License](assets/fonts/LICENSES.md).

## License

[BSD 2-Clause License](LICENSE.md)