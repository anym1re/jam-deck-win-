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
            pystray.MenuItem(lambda item: f"Server URL: http://localhost:{self.actual_port}", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Copy Scene URL", pystray.Menu(*self.build_copy_menu())),
            pystray.MenuItem("Manage Scenes", pystray.Menu(*self.build_manage_menu())),
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

        # Candidate directories to search (in order)
        candidates = []
        try:
            if sys.argv and sys.argv[0]:
                candidates.append(os.path.dirname(os.path.abspath(sys.argv[0])))
        except Exception:
            pass
        try:
            candidates.append(os.path.dirname(os.path.abspath(sys.executable)))
        except Exception:
            pass
        try:
            candidates.append(os.path.dirname(os.path.abspath(__file__)))
        except Exception:
            pass

        # Deduplicate preserving order
        seen = set(); dirs = []
        for d in candidates:
            if d and d not in seen:
                seen.add(d); dirs.append(d)

        server_py_name = "music_server.py"
        server_exe_name = "music_server.exe"

        debug_log = os.path.join(tempfile.gettempdir(), "jamdeck_debug.log")
        def dbg(msg):
            try:
                with open(debug_log, "a", encoding="utf-8") as lf:
                    lf.write(f"[start_server] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
            except Exception:
                pass

        cmd = None
        chosen_cwd = None

        for d in dirs:
            cand_exe = os.path.join(d, server_exe_name)
            cand_py = os.path.join(d, server_py_name)
            try:
                if os.path.exists(cand_exe) and os.path.isfile(cand_exe):
                    # Avoid launching the same file as this process
                    try:
                        if os.path.realpath(cand_exe) == os.path.realpath(sys.executable):
                            dbg(f"Skipping exe equal to sys.executable: {cand_exe}")
                        else:
                            cmd = [cand_exe, "--port", str(self.preferred_port)]
                            chosen_cwd = d
                            dbg(f"Selected exe: {cmd} (cwd={d})")
                            break
                    except Exception as e:
                        dbg(f"Path compare error: {e}")
                if cmd is None and os.path.exists(cand_py) and os.path.isfile(cand_py):
                    python_path = sys.executable or "python"
                    cmd = [python_path, cand_py, "--port", str(self.preferred_port)]
                    chosen_cwd = d
                    dbg(f"Selected script: {cmd} (cwd={d})")
                    break
            except Exception as e:
                dbg(f"Exception checking {d}: {e}")

        if cmd is None:
            # Fallback to script next to source
            try:
                fallback_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), server_py_name)
                cmd = [sys.executable or "python", fallback_py, "--port", str(self.preferred_port)]
                chosen_cwd = os.path.dirname(os.path.abspath(__file__))
                dbg(f"Fallback to: {cmd} (cwd={chosen_cwd})")
            except Exception as e:
                dbg(f"No server candidate found: {e}")
                self.notify("Jam Deck", "Could not locate music_server to run.")
                return

        # Safety: avoid spawning ourself
        try:
            if os.path.realpath(cmd[0]) == os.path.realpath(sys.executable):
                dbg(f"Refusing to spawn self ({cmd[0]}). Switching to script fallback.")
                fallback_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), server_py_name)
                cmd = [sys.executable or "python", fallback_py, "--port", str(self.preferred_port)]
                chosen_cwd = os.path.dirname(os.path.abspath(__file__))
                dbg(f"Switched to: {cmd}")
        except Exception as e:
            dbg(f"Self-check error: {e}")

        # Spawn process
        try:
            dbg(f"Spawning: {cmd}, cwd={chosen_cwd}")
            self.server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', cwd=chosen_cwd)
        except Exception as e:
            dbg(f"Failed to spawn: {e}")
            self.notify("Jam Deck", f"Failed to start server: {e}")
            return

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
        debug_log = os.path.join(tempfile.gettempdir(), "jamdeck_debug.log")
        def dbg(msg):
            try:
                with open(debug_log, "a", encoding="utf-8") as lf:
                    lf.write(f"[monitor_server] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
            except Exception:
                pass

        while proc and proc.poll() is None:
            try:
                line = proc.stdout.readline()
                if line:
                    line = line.strip()
                    print(f"Server: {line}")
                    dbg(f"Server output: {line}")
                    if line.startswith("JAMDECK_PORT="):
                        try:
                            port = int(line.split("=")[1])
                            self.actual_port = port
                            self.icon.menu = self.build_menu()
                            dbg(f"Detected port: {port}")
                        except Exception as e:
                            dbg(f"Port parse error: {e}")
            except Exception as e:
                dbg(f"Exception reading output: {e}")
                break

        # Process ended
        exit_code = None
        try:
            exit_code = proc.returncode
        except Exception:
            pass
        dbg(f"Server exited with code: {exit_code}")
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
            # Ask for confirmation using tkinter; if tkinter is unavailable, fall back to deleting
            confirm = True
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                confirm = messagebox.askokcancel("Confirm Deletion", f"Are you sure you want to delete the scene '{scene}'?")
                root.destroy()
            except Exception:
                # If tkinter is not available, proceed with deletion to preserve previous behavior
                pass

            if confirm:
                self.scenes.remove(scene)
                save_config(self.scenes, self.preferred_port)
                self.icon.menu = self.build_menu()
                self.notify("Jam Deck", f"Deleted '{scene}'")

    def open_documentation(self, icon=None, item=None):
        webbrowser.open("https://github.com/detekoi/jam-deck/blob/main/README.md")

    def show_about(self, icon=None, item=None):
        info = (
            "Jam Deck for OBS\n"
            f"Version {VERSION}\n\n"
            "Display your Apple Music tracks in OBS.\n\n"
            "GitHub: https://github.com/detekoi/jam-deck\n"
            "© 2025 Henry Manes"
        )
        # Try a modal dialog to ensure the user sees it (toast may be suppressed on some systems)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("About Jam Deck", info)
            root.destroy()
        except Exception:
            # Fallback to toast notification
            self.notify("Jam Deck", info.replace("\n", " "))

    def quit(self, icon=None, item=None):
        if self.server_running:
            self.stop_server()
        self.icon.stop()

    def run(self):
        self.icon.run()

if __name__ == "__main__":
    tray = JamDeckTray()
    tray.run()