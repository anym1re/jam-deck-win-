# Jam Deck for OBS: Dev Reference Guide

## Project Structure
- `music_server.py` - Python server that exposes now-playing data and serves the overlay
- `overlay.html` - HTML/CSS/JS for the browser source display
- `app_windows.py` - Windows tray application (pystray) for starting/stopping server and scene management
- `app.py` - (deprecated) original macOS menu bar app; replaced by `app_windows.py` in this fork
- `collect_zmq.py` - Helper for ZeroMQ libraries bundling
- Browser source URL: http://localhost:8080/

## Commands
- Start server: `./music_server.py` or `python3 music_server.py`
- Build app (Windows): use the provided PyInstaller specs or PowerShell helper; see README for details.
- Version updates: Update VERSION in `music_server.py`
- No linting commands (simple Python/HTML project)

## Code Style Guidelines
- **Python**: 
  - Use descriptive variable/function names
  - Comment complex logic sections
  - Handle errors with try/except blocks with specific error types
  - Follow PEP 8 spacing and indentation
  - Print debug statements for troubleshooting
- **HTML/CSS/JS**:
  - Use camelCase for JS variables and functions
  - CSS classes use kebab-case
  - Organize CSS logically by component/theme
  - Transitions and animations for UI elements
  - Use localStorage for persistent settings with scene-specific context

## Architecture Notes
- Server uses AppleScript to get music data from Apple Music
- Overlay connects to server API endpoint: `/nowplaying`
- Album artwork served via `/artwork` endpoint
- Static assets served via `/assets/fonts/` and `/assets/images/`
- Ten themes available: 5 rounded (Natural, Twitch, Dark, Pink, Light) and 5 square (Transparent, Neon, Terminal, Retro, High Contrast)

## Troubleshooting
- Check `debugMode` in overlay.html (set to true for visible errors)
- Look for error logs in Terminal
- System Preferences → Security & Privacy → Automation permissions