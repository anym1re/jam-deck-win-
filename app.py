#!/usr/bin/env python3
import rumps
import subprocess
import sys
import os
import threading
import time

class JamDeckApp(rumps.App):
    def __init__(self):
        # Path to app icon (template means it adapts to light/dark mode)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jamdeck.icns")
        
        super(JamDeckApp, self).__init__("Jam Deck", icon=icon_path, template=True)
        
        # Set up menu items
        self.server_running = False
        self.server_process = None
        self.server_thread = None
        
        # Configure menu items
        self.menu = [
            rumps.MenuItem("Start Server", callback=self.toggle_server),
            None,  # Separator
            rumps.MenuItem("Open in Browser", callback=self.open_browser),
            rumps.MenuItem("Copy Source URL", callback=self.copy_source_url),
            None,  # Separator
            rumps.MenuItem("About", callback=self.show_about)
        ]
        
        # Update menu text based on current state
        self.update_menu_state()

    def update_menu_state(self):
        """Update the menu items based on server state"""
        if self.server_running:
            self.menu["Start Server"].title = "Stop Server"
            self.menu["Open in Browser"].set_callback(self.open_browser)
        else:
            self.menu["Start Server"].title = "Start Server"
            self.menu["Open in Browser"].set_callback(self.server_not_running)

    def toggle_server(self, sender):
        """Toggle server on/off"""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        """Start the music server"""
        if not self.server_running:
            try:
                # Get the directory of the current script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                server_path = os.path.join(script_dir, "music_server.py")
                
                # Use Python from the current executable
                python_path = sys.executable
                
                # Start the server in a separate process
                self.server_process = subprocess.Popen(
                    [python_path, server_path],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # Monitor the server output in a separate thread
                self.server_thread = threading.Thread(target=self.monitor_server)
                self.server_thread.daemon = True
                self.server_thread.start()
                
                # Give server a moment to start
                time.sleep(1)
                
                # Update state
                self.server_running = True
                self.update_menu_state()
                
                # Notify user
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Server Started", 
                    message="Now playing overlay is active!"
                )
            except Exception as e:
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Error Starting Server", 
                    message=str(e)
                )

    def stop_server(self):
        """Stop the music server"""
        if self.server_running and self.server_process:
            try:
                # Terminate the server process
                self.server_process.terminate()
                self.server_process = None
                self.server_running = False
                self.update_menu_state()
                
                # Notify user
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Server Stopped", 
                    message="Overlay is no longer available."
                )
            except Exception as e:
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Error Stopping Server", 
                    message=str(e)
                )

    def monitor_server(self):
        """Monitor server output and handle process exit"""
        while self.server_process:
            # Read output line by line
            output = self.server_process.stdout.readline()
            if output:
                print(f"Server: {output.strip()}")
            
            # Check if process has exited
            if self.server_process.poll() is not None:
                # Process has terminated
                if self.server_running:
                    # If we thought it was running, it crashed
                    self.server_running = False
                    
                    # Update UI on main thread
                    rumps.App.notification(
                        title="Jam Deck",
                        subtitle="Server Stopped Unexpectedly", 
                        message="Check log for details."
                    )
                    
                    # Update menu state on main thread
                    def update():
                        self.update_menu_state()
                    rumps.Timer(0, update).start()
                break

    def open_browser(self, _):
        """Open overlay in default browser"""
        try:
            subprocess.run(["open", "http://localhost:8080"])
        except Exception as e:
            rumps.notification(
                title="Jam Deck",
                subtitle="Error", 
                message=f"Could not open browser: {str(e)}"
            )

    def server_not_running(self, _):
        """Display message when server is not running"""
        rumps.notification(
            title="Jam Deck",
            subtitle="Server Not Running", 
            message="Start the server first."
        )

    def copy_source_url(self, _):
        """Copy source URL to clipboard"""
        try:
            import subprocess
            # Copy URL to clipboard using pbcopy
            url = "http://localhost:8080"
            subprocess.run("pbcopy", text=True, input=url)
            rumps.notification(
                title="Jam Deck",
                subtitle="URL Copied",
                message="OBS source URL copied to clipboard"
            )
        except Exception as e:
            rumps.notification(
                title="Jam Deck",
                subtitle="Error",
                message=f"Could not copy URL: {str(e)}"
            )

    def show_about(self, _):
        """Show about dialog"""
        rumps.alert(
            title="About Jam Deck",
            message=(
                "Jam Deck for OBS\n"
                "Version 1.0.0\n\n"
                "Display your Apple Music tracks in OBS.\n\n"
                "For OBS: Add Browser Source with URL http://localhost:8080\n"
                "Width: Recommended minimum 400px, Height: 140px\n\n"
                "© 2025 Henry Manes"
            )
        )

if __name__ == "__main__":
    app = JamDeckApp()
    # Auto-start server when app launches
    app.start_server()
    app.run()