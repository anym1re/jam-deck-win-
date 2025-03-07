#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import json
from urllib.parse import parse_qs, urlparse, unquote
import os
import sys
import zmq

# Set port for the server
PORT = 8080

# Function to get current Apple Music track via AppleScript
def get_apple_music_track():
    script = '''
    tell application "Music"
        if player state is playing then
            set currentTrack to current track
            set songName to name of currentTrack
            set artistName to artist of currentTrack
            set albumName to album of currentTrack
            
            -- Try to get album artwork
            set hasArtwork to false
            
            try
                -- Get artwork from current track
                set myArtwork to artwork 1 of currentTrack
                
                -- Set file path - use a fixed location in /tmp
                set artworkFile to "/tmp/harmony_deck_cover.jpg"
                
                -- Get artwork data and write to file
                if format of myArtwork is JPEG picture then
                    set myPicture to data of myArtwork
                    
                    -- Write to file
                    set myFile to (open for access (POSIX file artworkFile) with write permission)
                    set eof of myFile to 0
                    write myPicture to myFile
                        try
                            close access (POSIX file artworkFile)
                        end try



                    
                    set hasArtwork to true
                end if
                
            on error errMsg
                -- Log error but continue
                do shell script "echo 'Artwork error: " & errMsg & "' >> /tmp/harmony-deck-log.txt"
            end try
            
            -- Return JSON with artwork path if artwork was successfully saved
            if hasArtwork then
                return "{\\\"playing\\\": true, \\\"title\\\": \\\"" & songName & "\\\", \\\"artist\\\": \\\"" & artistName & "\\\", \\\"album\\\": \\\"" & albumName & "\\\", \\\"artworkPath\\\": \\\"/artwork?t=" & (do shell script "date +%s") & "\\\"}"
            else
                return "{\\\"playing\\\": true, \\\"title\\\": \\\"" & songName & "\\\", \\\"artist\\\": \\\"" & artistName & "\\\", \\\"album\\\": \\\"" & albumName & "\\\"}"
            end if
        else
            return "{\\\"playing\\\": false}"
        end if
    end tell
    '''
    
    try:
        # Debug info
        print("Executing AppleScript...")
        
        # Run the AppleScript
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        
        # Print the raw output for debugging
        print(f"AppleScript raw output: {result.stdout}")
        print(f"AppleScript error output: {result.stderr}")
        
        # Make sure we actually have output
        if not result.stdout.strip():
            print("Warning: Empty response from AppleScript")
            return json.dumps({"playing": False, "error": "Empty response from AppleScript"})
        
        # Try to parse as JSON to verify it's valid
        try:
            json_obj = json.loads(result.stdout.strip())
            return result.stdout.strip()
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Invalid JSON: {result.stdout.strip()}")
            # Return a fallback JSON if the AppleScript output isn't valid JSON
            return json.dumps({"playing": False, "error": "Invalid JSON from AppleScript"})
    except Exception as e:
        print(f"Error executing AppleScript: {e}")
        return json.dumps({"playing": False, "error": str(e)})

# Create custom HTTP request handler
class MusicHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Print to stdout instead of stderr for better visibility
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}")
    
    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        print(f"Request received: {path}")
        
        # Route requests
        if path == '/nowplaying':
            print("Handling /nowplaying request")
            music_data = get_apple_music_track()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.end_headers()
            
            # Debug the output we're sending
            print(f"Sending JSON response: {music_data}")
            
            # Always ensure we send valid JSON
            self.wfile.write(music_data.encode())
            
        elif path == '/artwork' or path.startswith('/artwork?'):
            # Fixed path to the artwork file
            artwork_path = "/tmp/harmony_deck_cover.jpg"
            print(f"Serving artwork from: {artwork_path}")
            
            try:
                # Read the file
                with open(artwork_path, 'rb') as f:
                    file_data = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.send_header('Cache-Control', 'no-cache')  # Prevent caching
                self.end_headers()
                self.wfile.write(file_data)
                print("Artwork served successfully")
                
            except Exception as e:
                print(f"Error serving artwork: {e}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Artwork not found')
                
        elif path == '/' or path == '/index.html':
            print("Serving HTML overlay page")
            # Serve the HTML page for the overlay
            try:
                with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'overlay.html'), 'r', encoding='utf-8') as file:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                    self.end_headers()
                    self.wfile.write(file.read().encode('utf-8'))
            except Exception as e:
                print(f"Error serving HTML: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error reading HTML file: {str(e)}".encode())
        else:
            print(f"404 Not Found: {path}")
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"404 Not Found")

# Start the web server
def run_server():
    try:
        server_address = ('', PORT)
        httpd = HTTPServer(server_address, MusicHandler)
        print(f"Starting music server on port {PORT}...")
        print(f"Open http://localhost:{PORT}/ in your browser or OBS")
        print(f"Press Ctrl+C to stop the server")
        
        # Test the AppleScript before starting the server
        print("\nTesting AppleScript...")
        test_result = get_apple_music_track()
        print(f"Test result: {test_result}")
        print("\nServer ready!")
        
        # Start server
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()
        print("Server stopped")
    except Exception as e:
        print(f"Server error: {e}")

if __name__ == '__main__':
    # Force output buffering off for better debugging
    sys.stdout.reconfigure(line_buffering=True)
    print("Music Now Playing Server (Debug Mode)")
    run_server()