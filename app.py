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
        
        # Load saved scenes
        self.scenes = self.load_scenes()
        
        # Configure all menu items at once
        server_item = rumps.MenuItem("Start Server", callback=self.toggle_server)
        copy_scenes_menu = self.create_copy_scenes_menu()
        
        self.menu = [
            server_item,
            None,  # Separator
            copy_scenes_menu,
            None,  # Separator
            rumps.MenuItem("Open in Browser", callback=self.open_browser),
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
                    text=True,
                    encoding='utf-8'
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
    
    def load_scenes(self):
        """Load saved scenes from config file"""
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".jamdeck_scenes")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    scenes = [line.strip() for line in f.readlines() if line.strip()]
                    if not scenes:
                        return ["default"]
                    return scenes
            return ["default"]
        except Exception:
            return ["default"]

    def save_scenes(self):
        """Save scenes to config file"""
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".jamdeck_scenes")
            with open(config_path, "w") as f:
                for scene in self.scenes:
                    f.write(f"{scene}\n")
        except Exception as e:
            rumps.notification("Jam Deck", "Error", f"Could not save scenes: {str(e)}")

    def create_copy_scenes_menu(self):
        """Create the copy scenes submenu"""
        # Create copy scenes submenu
        copy_scenes_menu = rumps.MenuItem("Copy Scene URL")
        
        # Add each scene as a menu item
        for scene in self.scenes:
            item = rumps.MenuItem(scene, callback=self.copy_scene_url)
            copy_scenes_menu.add(item)
        
        # Add separator and management options
        copy_scenes_menu.add(None)  # Separator
        copy_scenes_menu.add(rumps.MenuItem("Add New Scene...", callback=self.add_new_scene))
        copy_scenes_menu.add(rumps.MenuItem("Manage Scenes...", callback=self.manage_scenes))
        
        return copy_scenes_menu
        
    def rebuild_copy_scenes_menu(self):
        """Rebuild the copy scenes menu after changes"""
        if "Copy Scene URL" in self.menu:
            # Create new copy scenes menu
            new_copy_scenes_menu = self.create_copy_scenes_menu()
            
            # Replace existing menu
            index = self.menu._menu.indexOfItemWithTitle_("Copy Scene URL")
            if index != -1:
                self.menu._menu.removeItemAtIndex_(index)
                self.menu._menu.insertItem_atIndex_(new_copy_scenes_menu._menuitem, index)
    
    def copy_scene_url(self, sender):
        """Copy the URL for the selected scene to clipboard"""
        try:
            import subprocess
            # Base URL
            base_url = "http://localhost:8080"
            
            # Add scene parameter if not default
            scene_name = sender.title
            if scene_name and scene_name != "default":
                url = f"{base_url}/?scene={scene_name}"
            else:
                url = base_url
            
            # Copy URL to clipboard using pbcopy
            subprocess.run("pbcopy", text=True, input=url)
            
            rumps.notification(
                title="Jam Deck",
                subtitle="URL Copied",
                message=f"OBS source URL for scene '{scene_name}' copied to clipboard"
            )
        except Exception as e:
            rumps.notification(
                title="Jam Deck",
                subtitle="Error",
                message=f"Could not copy URL: {str(e)}"
            )

    def add_new_scene(self, _):
        """Show dialog to add a new scene"""
        response = rumps.Window(
            title="Add New Scene",
            message="Enter a name for the new scene:",
            dimensions=(300, 20)
        ).run()
        
        if response.clicked and response.text:
            # Sanitize name for URL (replace spaces with hyphens, remove special chars)
            scene_name = "".join(c if c.isalnum() else "-" for c in response.text)
            
            # Check if name exists
            if scene_name in self.scenes:
                rumps.alert("Scene Error", f"Scene '{scene_name}' already exists.")
                return
            
            # Add the new scene
            self.scenes.append(scene_name)
            self.save_scenes()
            
            # Rebuild copy scenes menu
            self.rebuild_copy_scenes_menu()

    def manage_scenes(self, _):
        """Open scene management window"""
        # This would ideally use a custom window with a list
        # Since rumps doesn't support complex UI, we'll use multiple simple dialogs
        
        i = 0
        while i < len(self.scenes):
            scene = self.scenes[i]
            
            # Skip default scene (always present)
            if scene == "default":
                i += 1
                continue
            
            # First, ask if user wants to modify this scene
            should_modify = rumps.alert(
                title=f"Scene: {scene}",
                message="Do you want to modify this scene?",
                ok="No, Keep It",
                cancel="Yes, Modify It"
            )
            
            # If user wants to keep it, move to next scene
            if should_modify == 1:  # OK button ("No, Keep It")
                i += 1
                continue
            
            # Ask what modification to make
            action = rumps.alert(
                title=f"Modify Scene: {scene}",
                message="What would you like to do with this scene?",
                ok="Rename",
                cancel="Delete"
            )
            
            if action == 1:  # OK button ("Rename")
                # Ask for new name
                new_name = rumps.Window(
                    title="Rename Scene",
                    message=f"Enter new name for '{scene}':",
                    dimensions=(300, 20)
                ).run()
                
                if new_name.clicked and new_name.text:
                    # Sanitize name
                    sanitized_name = "".join(c if c.isalnum() else "-" for c in new_name.text)
                    
                    # Update scene name
                    self.scenes[i] = sanitized_name
                    self.save_scenes()
                    
                    i += 1
            else:  # Cancel button ("Delete")
                # Confirm deletion
                confirm = rumps.alert(
                    title="Confirm Deletion",
                    message=f"Are you sure you want to delete the scene '{scene}'?",
                    ok="No, Keep It",
                    cancel="Yes, Delete It"
                )
                
                if confirm != 1:  # Not OK button (so "Yes, Delete It")
                    # Remove the scene
                    self.scenes.remove(scene)
                    self.save_scenes()
                    # Don't increment i since we removed an item
                else:
                    i += 1  # Skip to next item if not deleting
            
            # If we didn't delete, we need to move to the next scene
            if i < len(self.scenes) and scene == self.scenes[i]:
                i += 1
        
        # Rebuild copy scenes menu
        self.rebuild_copy_scenes_menu()

if __name__ == "__main__":
    app = JamDeckApp()
    # Auto-start server when app launches
    app.start_server()
    app.run()