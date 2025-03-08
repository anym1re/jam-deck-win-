# Jam Deck for OBS: Apple Music Stream Display

A customizable Apple Music now playing display for macOS.

![Jam Deck](preview.png)

## Features

- Shows currently playing Apple Music track on your stream
- Five beautiful themes (Natural, Twitch, Dark, Pink, Light)
- Adaptive or Fixed width display options
- Automatically hides when no music is playing
- Support for album artwork
- Clean animated transitions between songs
- Font changes with each theme for a complete visual experience
- Settings menu appears only on hover (invisible to viewers)
- Scene-specific settings saved between sessions (use ?scene=scenename in URL)

## Requirements

- macOS (uses AppleScript to communicate with Apple Music)
- Python 3.6 or later
- OBS Studio or similar streaming software with browser source support

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/jam-deck.git
   cd jam-deck
   ```

2. Make sure the Python script is executable:
   ```
   chmod +x music_server.py
   ```

3. Start the server:
   ```
   ./music_server.py
   ```

4. Add a Browser Source in OBS:
   - URL: `http://localhost:8080/` or `http://localhost:8080/?scene=scenename` for scene-specific settings
   - Width: 400 (recommended minimum)
   - Height: 140
   - Check "Refresh browser when scene becomes active"

## Usage

Once installed, the overlay will automatically display your currently playing Apple Music tracks.


### Theme Selection

Hover over the overlay to reveal the settings menu at the bottom:

- **Natural** (default): Soft green theme with rounded corners
- **Twitch**: Dark purple theme that matches Twitch aesthetics
- **Dark**: Sleek black theme with cyan accents
- **Pink**: Vibrant pink theme with friendly typography
- **Light**: Clean white theme with blue accents

### Width Options

In the settings menu:

- **A**: Adaptive width (only as wide as needed for the text)
- **F**: Fixed width (expands to fill the entire browser source width, default)


## Troubleshooting

**No music information appears:**
- Make sure Apple Music is running
- Check Terminal for error messages
- Try playing/pausing music to trigger an update

**Permission errors:**
- macOS may need permission to control Apple Music
- Go to System Preferences → Security & Privacy → Automation
- Ensure Terminal (or whatever app runs the script) has permission to control Apple Music

## Auto-Start on Boot

To make the server start automatically when you boot your Mac:

1. Create an Automator application:
   - Open Automator
   - Create a new Application
   - Add a "Run Shell Script" action
   - Enter: `cd /path/to/jam-deck && ./music_server.py`
   - Save as "Start Jam Deck"

2. Add to Login Items:
   - System Preferences → Users & Groups → Login Items
   - Add the Automator application you created

## Customization

Advanced users can modify the CSS in `overlay.html` to create custom themes or change the layout.

### Changing the Port

By default, the server runs on port 8080. To change this:

1. Open `music_server.py` in a text editor
2. Find the line near the top that says `PORT = 8080`
3. Change `8080` to your desired port number
4. Save the file and restart the server
5. Update your browser source URL in OBS to use the new port

## License

[MIT License](LICENSE)

## Acknowledgements

- "Natural" theme (formerly "Polar Bear Cafe") is inspired by natural, earthy aesthetics
- Created as a lightweight alternative to other music display solutions
