# Jam Deck for OBS: Dev Reference Guide

## Project Structure
- `music_server.py` - Python server that communicates with Apple Music and serves data
- `overlay.html` - HTML/CSS/JS for the browser source display
- Browser source URL: http://localhost:8080/

## Commands
- Start server: `./music_server.py` or `python3 music_server.py`
- Install requirements: Python 3.6+ (no additional packages needed)
- No build/linting commands (simple Python/HTML project)

## Code Style Guidelines
- **Python**: 
  - Use descriptive variable/function names
  - Comment complex logic sections
  - Handle errors with try/except blocks
  - Follow PEP 8 spacing and indentation
  - Print debug statements for troubleshooting
- **HTML/CSS/JS**:
  - Use camelCase for JS variables and functions
  - CSS classes use kebab-case
  - Organize CSS logically by component/theme
  - Transitions and animations for UI elements
  - Use localStorage for persistent settings

## Architecture Notes
- Server uses AppleScript to get music data from Apple Music
- Overlay connects to server API endpoint: `/nowplaying`
- Album artwork served via `/artwork` endpoint
- Five themes available: Polar Bear Cafe, Twitch, Dark, Pink, Light

## Troubleshooting
- Check `debugMode` in overlay.html (set to true for visible errors)
- Look for error logs in Terminal
- System Preferences → Security & Privacy → Automation permissions