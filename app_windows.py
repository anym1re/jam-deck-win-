#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import time
import json
import webbrowser
import tempfile
from PIL import Image
import pystray
import pyperclip
try:
    from win10toast import ToastNotifier
except Exception:
    ToastNotifier = None

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from music_server import VERSION

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".jamdeck_config.json")
DEFAULT_PORT = 8080
OLD_SCENES_FILE = os.path.join(os.path.expanduser("~"), ".jamdeck_scenes")

def load_config():
    scenes = ["default"]
    preferred_port = DEFAULT_PORT
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE,"r") as f:
                cfg = json.load(f)
                js = cfg.get("scenes", ["default"])
                if isinstance(js,list) and js:
                    scenes = js
                if "default" not in scenes:
                    scenes.insert(0,"default")
                jp = cfg.get("preferred_port", DEFAULT_PORT)
                if isinstance(jp,int):
                    preferred_port = jp
    except Exception:
        pass
    # migrate old scenes if present
    try:
        if os.path.exists(OLD_SCENES_FILE):
            with open(OLD_SCENES_FILE,"r") as f:
                old = [line.strip() for line in f if line.strip()]
            added = False
            sset = set(scenes)
            for sc in old:
                if sc not in sset:
                    scenes.append(sc); sset.add(sc); added=True
            if added:
                save_config(scenes, preferred_port)
                try: os.remove(OLD_SCENES_FILE)
                except OSError: pass
    except Exception:
        pass
    return scenes, preferred_port

def save_config(scenes, preferred_port):
    cfg = {"scenes": scenes, "preferred_port": preferred_port}
    try:
        with open(CONFIG_FILE,"w") as f:
            json.dump(cfg,f,indent=4)
    except Exception:
        pass

class JamDeckTray:
    def __init__(self):
        self.scenes, self.preferred_port = load_config()
        self.actual_port = self.preferred_port
        self.server_process = None
        self.server_thread = None
        self.server_running = False
        # Prefer .ico icon if present for better Windows taskbar/tray rendering
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images")
        png_icon = os.path.join(icon_dir, "jamdeck-template.png")
        ico_icon = os.path.join(icon_dir, "jamdeck.ico")
        try:
            if os.path.exists(ico_icon):
                self.icon_image = Image.open(ico_icon)
            else:
                self.icon_image = Image.open(png_icon)
        except Exception:
            # Fallback to a simple generated 16x16 image if loading fails
            self.icon_image = Image.new("RGBA", (16, 16), (255, 0, 0, 0))
        self.notifier = ToastNotifier() if ToastNotifier else None
        self.icon = pystray.Icon("Jam Deck", self.icon_image, "Jam Deck", menu=self.build_menu())

    def build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(lambda item: "Stop Server" if self.server_running else "Start Server", self.toggle_server),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Server URL", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Copy Scene URL", lambda: None, submenu=self.build_copy_menu()),
            pystray.MenuItem("Manage Scenes", lambda: None, submenu=self.build_manage_menu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open in Browser", self.open_browser),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Documentation", self.open_documentation),
            pystray.MenuItem("About", self.show_about),
            pystray.MenuItem("Quit", self.quit)
        )

    def build_copy_menu(self):
        items = []
        if not self.scenes:
            items.append(pystray.MenuItem("No scenes defined", lambda : None, enabled=False))
        else:
            for s in self.scenes:
                items.append(pystray.MenuItem(s, lambda _, s=s: self.copy_scene_url(s)))
        return tuple(items)

    def build_manage_menu(self):
        items = []
        items.append(pystray.MenuItem("Add New Scene...", self.add_new_scene))
        items.append(pystray.Menu.SEPARATOR)
        for s in self.scenes:
            if s=="default":
                items.append(pystray.MenuItem(s, lambda : None, enabled=False))
            else:
                items.append(pystray.MenuItem(s, pystray.Menu(
                    pystray.MenuItem("Rename...", lambda _, s=s: self.rename_scene(s)),
                    pystray.MenuItem("Delete", lambda _, s=s: self.delete_scene(s))
                )))
        return tuple(items)

    def toggle_server(self, icon=None, item=None):
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self, icon=None, item=None):
        if self.server_running:
            return
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(script_dir, "music_server.py")
        python_path = sys.executable
        cmd = [python_path, server_path, "--port", str(self.preferred_port)]
        self.server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        self.server_thread = threading.Thread(target=self.monitor_server, daemon=True)
        self.server_thread.start()
        time.sleep(1)
        self.server_running = True
        self.actual_port = self.preferred_port
        self.icon.menu = self.build_menu()
        self.notify("Jam Deck", "Server Started — overlay is active")

    def stop_server(self, icon=None, item=None):
        if not self.server_running:
            return
        proc = self.server_process
        self.server_running = False
        self.server_process = None
        try:
            proc.terminate()
        except Exception:
            pass
        self.icon.menu = self.build_menu()
        self.notify("Jam Deck", "Server Stopped")

    def monitor_server(self):
        proc = self.server_process
        while proc and proc.poll() is None:
            try:
                line = proc.stdout.readline()
                if line:
                    line=line.strip()
                    print(f"Server: {line}")
                    if line.startswith("JAMDECK_PORT="):
                        try:
                            port = int(line.split("=")[1])
                            self.actual_port = port
                            self.icon.menu = self.build_menu()
                        except Exception:
                            pass
            except Exception:
                break
        if self.server_running:
            self.server_running = False
            self.icon.menu = self.build_menu()
            self.notify("Jam Deck", "Server stopped unexpectedly")

    def open_browser(self, icon=None, item=None):
        if not self.server_running:
            self.notify("Jam Deck", "Server not running")
            return
        url = f"http://localhost:{self.actual_port}"
        try:
            webbrowser.open(url)
        except Exception as e:
            self.notify("Jam Deck", f"Could not open browser: {e}")

    def notify(self, title, msg):
        if self.notifier:
            try:
                self.notifier.show_toast(title, msg, threaded=True, icon_path=None, duration=3)
            except Exception:
                pass

    def copy_scene_url(self, scene):
        if not self.server_running:
            self.notify("Jam Deck", "Server not running")
            return
        base = f"http://localhost:{self.actual_port}"
        if scene and scene!="default":
            url = f"{base}/?scene={scene}"
        else:
            url = base
        try:
            pyperclip.copy(url)
            self.notify("Jam Deck", f"Copied URL for scene '{scene}'")
        except Exception as e:
            self.notify("Jam Deck", f"Could not copy URL: {e}")

    def add_new_scene(self, icon=None, item=None):
        # Prompt user for a scene name using tkinter; fallback to auto name if cancelled
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            name = simpledialog.askstring("Add New Scene", "Enter name for the new scene:")
            root.destroy()
        except Exception:
            name = None
        if name and name.strip():
            scene_name = "".join(c if c.isalnum() else "-" for c in name.strip())
            if scene_name in self.scenes:
                self.notify("Jam Deck", f"Scene '{scene_name}' already exists")
                return
            self.scenes.append(scene_name)
            save_config(self.scenes, self.preferred_port)
            self.icon.menu = self.build_menu()
            self.notify("Jam Deck", f"Added scene '{scene_name}'")
        else:
            # Fallback: generate a unique scene name
            new_name = f"scene-{int(time.time())}"
            self.scenes.append(new_name)
            save_config(self.scenes, self.preferred_port)
            self.icon.menu = self.build_menu()
            self.notify("Jam Deck", f"Added scene '{new_name}' (auto)")

    def rename_scene(self, scene):
        # Prompt user for new scene name using tkinter
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            new_name = simpledialog.askstring("Rename Scene", f"Enter new name for '{scene}':")
            root.destroy()
        except Exception:
            new_name = None
        if new_name and new_name.strip():
            sanitized_name = "".join(c if c.isalnum() else "-" for c in new_name.strip())
            if sanitized_name in self.scenes:
                self.notify("Jam Deck", f"Scene '{sanitized_name}' already exists")
                return
            if scene in self.scenes:
                idx = self.scenes.index(scene)
                self.scenes[idx] = sanitized_name
                save_config(self.scenes, self.preferred_port)
                self.icon.menu = self.build_menu()
                self.notify("Jam Deck", f"Renamed '{scene}' to '{sanitized_name}'")

    def delete_scene(self, scene):
        if scene in self.scenes:
            self.scenes.remove(scene)
            save_config(self.scenes, self.preferred_port)
            self.icon.menu = self.build_menu()
            self.notify("Jam Deck", f"Deleted '{scene}'")

    def open_documentation(self, icon=None, item=None):
        webbrowser.open("https://github.com/detekoi/jam-deck/blob/main/README.md")

    def show_about(self, icon=None, item=None):
        self.notify("Jam Deck", f"Jam Deck for OBS\nVersion {VERSION}")

    def quit(self, icon=None, item=None):
        if self.server_running:
            self.stop_server()
        self.icon.stop()

    def run(self):
        self.icon.run()

if __name__ == "__main__":
    tray = JamDeckTray()
    tray.run()