#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import json
from urllib.parse import parse_qs, urlparse, unquote
import os
import sys
import zmq
import signal
import atexit
import socket
import argparse # Import argparse
import tempfile
import platform

# Version information
VERSION = "1.1.3"

# --- Debug/logging & runtime paths ---
import time

# Enable debug via env or --debug flag (set later)
DEBUG_ENABLED = str(os.environ.get("JAMDECK_DEBUG", "")).strip().lower() in ("1", "true", "yes", "on")

def _project_base_dir():
    try:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.realpath(__file__))
    except Exception:
        return os.getcwd()

def _ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass

def _logs_dir():
    d = os.path.join(_project_base_dir(), "logs")
    _ensure_dir(d)
    return d

def _overlay_log_path():
    return os.path.join(_logs_dir(), "overlay.log")

def _runtime_dir():
    # Override via env
    env_dir = os.environ.get("JAMDECK_RUNTIME_DIR")
    if env_dir:
        try:
            _ensure_dir(env_dir)
            return env_dir
        except Exception:
            pass
    # In production builds (PyInstaller), use local project dir
    try:
        if getattr(sys, "frozen", False):
            d = os.path.join(_project_base_dir(), "runtime")
            _ensure_dir(d)
            return d
    except Exception:
        pass
    # Fallback to temp for dev
    return tempfile.gettempdir()

def _debug_write(msg):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = msg.rstrip("\n")
        with open(_overlay_log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {line}\n")
    except Exception:
        pass

class _DebugStdoutProxy:
    """Redirect lines starting with [SMTC DEBUG] / [SMTC DEBUG LOG] to overlay.log when DEBUG is enabled.
       Suppresses them from console to avoid spam. Other output passes through."""
    def __init__(self, real):
        self._real = real
    def write(self, s):
        try:
            if ("[SMTC DEBUG" in s):
                if DEBUG_ENABLED:
                    for ln in s.splitlines():
                        if ln.strip():
                            _debug_write(ln)
                return
            self._real.write(s)
        except Exception:
            try:
                self._real.write(s)
            except Exception:
                pass
    def flush(self):
        try:
            self._real.flush()
        except Exception:
            pass

def _smtc_debug_log(prefix, payload=None, session=None, control=None, playback_status=None):
    """Write detailed SMTC debug info to logs/overlay.log if DEBUG is enabled."""
    if not DEBUG_ENABLED:
        return
    try:
        _debug_write(f"[SMTC DEBUG LOG] {prefix}")
        if session is not None:
            try:
                _debug_write(f"[SMTC DEBUG LOG]  session repr: {repr(session)}")
            except Exception:
                _debug_write(f"[SMTC DEBUG LOG]  session repr: <unprintable>")
        if playback_status is not None:
            try:
                _debug_write(f"[SMTC DEBUG LOG]  playback_status: {playback_status}")
            except Exception:
                _debug_write(f"[SMTC DEBUG LOG]  playback_status: <unprintable>")
        if control is not None:
            try:
                _debug_write(f"[SMTC DEBUG LOG]  control repr: {repr(control)}")
            except Exception:
                _debug_write(f"[SMTC DEBUG LOG]  control repr: <unprintable>")
        if payload is not None:
            try:
                _debug_write(f"[SMTC DEBUG LOG]  payload: {json.dumps(payload)}")
            except Exception:
                try:
                    _debug_write(f"[SMTC DEBUG LOG]  payload repr: {repr(payload)}")
                except Exception:
                    _debug_write(f"[SMTC DEBUG LOG]  payload: <unprintable>")
    except Exception as e:
        _debug_write(f"[SMTC DEBUG LOG] logging failed: {e}")

# Set starting port for the server
START_PORT = 8080
MAX_PORT_ATTEMPTS = 10 # Limit how many ports we try

# Initialize ZMQ context as None - we'll create it when needed and clean it up on exit
zmq_context = None
# Cache of last known metadata (by appId)
LAST_KNOWN_META = {}
# Cache of last known metadata (by appId)
LAST_KNOWN_META = {}
# Cache of last known metadata (by appId)
LAST_KNOWN_META = {}

# Function to clean up resources on exit
def cleanup():
    global zmq_context
    if zmq_context:
        print("Closing ZMQ context...")
        zmq_context.term()
        zmq_context = None
        print("ZMQ context closed")

# Register cleanup function to run on exit
atexit.register(cleanup)

# Handle signals for clean shutdown
def signal_handler(sig, frame):
    print("\nShutting down server...")
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# macOS AppleScript helper removed in Windows fork.
# This repository fork no longer depends on osascript/AppleScript.
# Windows builds use SMTC (via pywinrt) through get_windows_smtc_track().
# If macOS AppleScript support is required, restore it from upstream history.
 
# ---------------------------------------------------------
# Windows: System Media Transport Controls (SMTC) access

def _get_media_properties(session):
    """Return media properties object using the best available SMTC API."""
    # Try common API names exposed by different winrt bindings
    for name in ("try_get_media_properties_async", "get_media_properties_async", "get_current_media_properties"):
        try:
            method = getattr(session, name, None)
            if not method:
                continue
            props = method()
            # If it's an async operation, it should expose .get() to wait
            try:
                return props.get()
            except Exception:
                # If not async or .get() not present, assume props is already the result
                return props
        except Exception:
            # Try next API name
            continue
    # If nothing worked, raise to allow caller to fallback to minimal payload
    raise Exception("No media properties API available")

def _get_session_app_id(session):
    """Extract AUMID/AppId from a SMTC session."""
    for name in ("source_app_user_model_id", "app_id", "app_user_model_id", "SourceAppUserModelId"):
        try:
            val = getattr(session, name, None)
            if val:
                return val
        except Exception:
            continue
    return None

def _extract_thumbnail_to_file(control):
    """Extract SMTC thumbnail to a temp JPEG file. Returns file path or None."""
    try:
        thumb = getattr(control, "thumbnail", None)
        if not thumb:
            return None

        # Open the WinRT stream for the thumbnail
        stream = thumb.open_read_async().get()

        # Prefer DataReader to read the bytes from the IInputStream
        try:
            from winrt.windows.storage.streams import DataReader, InputStreamOptions
        except Exception:
            DataReader = None  # If DataReader cannot be imported, we'll fail back to None

        tmp_file = os.path.join(_runtime_dir(), "harmony_deck_cover.jpg")

        if DataReader is not None and stream:
            try:
                # Some runtimes provide a 'size' property; if not, load up to 10MB
                size = getattr(stream, "size", 0)
                try:
                    size = int(size) if size else 0
                except Exception:
                    size = 0

                max_bytes = 10 * 1024 * 1024  # 10MB safety cap
                to_load = min(size if size else max_bytes, max_bytes)

                reader = DataReader(stream)
                try:
                    reader.input_stream_options = InputStreamOptions.READ_AHEAD
                except Exception:
                    pass

                loaded = reader.load_async(to_load).get()
                buf = bytearray(loaded)
                reader.read_bytes(buf)

                with open(tmp_file, "wb") as f:
                    f.write(buf)

                try:
                    reader.detach_stream()
                except Exception:
                    pass
                try:
                    reader.close()
                except Exception:
                    pass

                if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 0:
                    return tmp_file
            except Exception:
                # Fall through to return None
                pass

        return None
    except Exception:
        return None

def _normalize_playback_status(playback_status):
    """Normalize playback status to a lowercase string."""
    try:
        name = getattr(playback_status, "name", None)
        if isinstance(name, str) and name:
            return name.lower()
    except Exception:
        pass
    try:
        ps_int = int(playback_status)
        mapping = {
            0: "closed",
            1: "opened",
            2: "changing",
            3: "stopped",
            4: "playing",
            5: "paused",
        }
        return mapping.get(ps_int, str(ps_int))
    except Exception:
        try:
            return str(playback_status).lower()
        except Exception:
            return "unknown"

def get_windows_smtc_track():
    """Attempt to read current media session via Windows SMTC (supports UWP/Store apps like Apple Music)."""
    # Ensure the stdlib 'uuid' module is available for any runtime imports (some winrt bindings
    # perform dynamic imports that PyInstaller can miss). Explicit import here helps bundled EXEs.
    try:
        import uuid  # explicit import to ensure inclusion in frozen builds
    except Exception:
        # If uuid truly isn't available, continue — error will be reported by the caller
        pass
    try:
        # Lazy import winrt to avoid hard dependency on non-Windows platforms
        try:
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SMTCManager
        except Exception as imp_e:
            payload = {"playing": False, "error": f"winrt import failed: {imp_e}"}
            _smtc_debug_log("winrt import failed", payload, session=None)
            return json.dumps(payload)
 
        try:
            mgr = SMTCManager.request_async().get()
            # Ensure we materialize sessions into a list once to avoid exhausting iterators.
            try:
                sessions_list = list(mgr.get_sessions())
            except Exception:
                # Fallback to manual list construction
                sessions_list = [s for s in mgr.get_sessions()]
        except Exception as e:
            payload = {"playing": False, "error": f"SMTC request failed: {e}"}
            _smtc_debug_log("SMTC request failed", payload, session=None)
            return json.dumps(payload)

        # Debugging: enumerate sessions and print details to help diagnose "No active media session"
        try:
            sess_count = len(sessions_list)
            print(f"[SMTC DEBUG] Retrieved {sess_count} session(s)")
        except Exception as dbg_e:
            print(f"[SMTC DEBUG] Could not determine session count: {dbg_e}")

        # Iterate with index — some session objects are lazy / proxy objects so wrap attribute access
        idx = 0
        for session in sessions_list:
            try:
                print(f"[SMTC DEBUG] Session #{idx}: {repr(session)}")
                # Try common attribute/property names for app identifier
                app_id = None
                for name in ("source_app_user_model_id", "source_app_user_model_id", "app_id", "app_user_model_id", "SourceAppUserModelId"):
                    try:
                        val = getattr(session, name, None)
                        if val:
                            app_id = val
                            break
                    except Exception:
                        continue
                print(f"[SMTC DEBUG]  app_id: {app_id}")

                # Try to get playback info (may be a callable)
                playback_status = None
                try:
                    get_playback = getattr(session, "get_playback_info", None)
                    if callable(get_playback):
                        pi = get_playback()
                        playback_status = getattr(pi, "playback_status", getattr(pi, "playbackStatus", None))
                    else:
                        # Some bindings expose a property instead
                        pi = getattr(session, "playback_info", None) or getattr(session, "playbackInfo", None)
                        if pi:
                            playback_status = getattr(pi, "playback_status", getattr(pi, "playbackStatus", None))
                except Exception as p_e:
                    # Fallback: attempt to access simple properties if available
                    try:
                        playback_status = getattr(session, "playback_status", None) or getattr(session, "playbackStatus", None)
                    except Exception:
                        playback_status = None
                print(f"[SMTC DEBUG]  playback_status: {playback_status}")

                # Note: do not fail here — continue to existing logic below that reads media properties
            except Exception as e:
                print(f"[SMTC DEBUG] Exception inspecting session #{idx}: {e}")
            idx += 1
 
        # Prefer the first session that reports a playing state.
        # Use playback status when available, but still attempt to read metadata
        # because some players may report playback state without exposing title/artist.

        # Attempt to prefer Apple Music session if present (AppUserModelID starts with this prefix)
        apple_prefix = "AppleInc.AppleMusicWin_"
        apple_idx = None
        for i, s in enumerate(sessions_list):
            try:
                app_id = None
                for name in ("source_app_user_model_id", "app_id", "app_user_model_id", "SourceAppUserModelId"):
                    try:
                        val = getattr(s, name, None)
                        if val:
                            app_id = val
                            break
                    except Exception:
                        continue
                if app_id and isinstance(app_id, str) and app_id.startswith(apple_prefix):
                    apple_idx = i
                    print(f"[SMTC DEBUG] Preferred Apple Music session found at index {i}: {app_id}")
                    break
            except Exception:
                continue
        if apple_idx is not None and apple_idx != 0:
            # Move the preferred session to the front so selection logic picks it first.
            sessions_list.insert(0, sessions_list.pop(apple_idx))

        for session in sessions_list:
            try:
                # Determine playback status robustly
                playback_status = None
                try:
                    get_playback = getattr(session, "get_playback_info", None)
                    if callable(get_playback):
                        pi = get_playback()
                        playback_status = getattr(pi, "playback_status", getattr(pi, "playbackStatus", None))
                    else:
                        pi = getattr(session, "playback_info", None) or getattr(session, "playbackInfo", None)
                        if pi:
                            playback_status = getattr(pi, "playback_status", getattr(pi, "playbackStatus", None))
                except Exception:
                    try:
                        playback_status = getattr(session, "playback_status", None) or getattr(session, "playbackStatus", None)
                    except Exception:
                        playback_status = None

                # Normalize playback status to decide if session is playing — robust fallback
                is_playing = False
                try:
                    # If playback_status exposes a 'name' (enum), check for 'playing'
                    ps_name = getattr(playback_status, "name", None)
                    if ps_name and isinstance(ps_name, str) and ps_name.lower() == "playing":
                        is_playing = True
                    else:
                        # Try numeric conversion
                        try:
                            ps_int = int(playback_status)
                            if ps_int in (4, 5):
                                is_playing = True
                        except Exception:
                            # Fallback: string content may contain enum name or numeric literal
                            try:
                                ps_str = str(playback_status).lower()
                                if "playing" in ps_str or "paused" in ps_str or "4" in ps_str or "5" in ps_str:
                                    is_playing = True
                            except Exception:
                                pass

                    # Heuristic: if this session belongs to Apple Music, prefer treating it as playing
                    # when a playback_status is present but metadata might be inaccessible in this runtime.
                    try:
                        app_id = None
                        for name in ("source_app_user_model_id", "app_id", "app_user_model_id", "SourceAppUserModelId"):
                            try:
                                val = getattr(session, name, None)
                                if val:
                                    app_id = val
                                    break
                            except Exception:
                                continue
                        if not is_playing and app_id and isinstance(app_id, str) and app_id.startswith("AppleInc.AppleMusicWin") and playback_status is not None:
                            # Attempt to read metadata; if that fails, return a minimal playing payload for Apple Music.
                            try:
                                control = _get_media_properties(session)
                                title = getattr(control, "title", "") or ""
                                artist = getattr(control, "artist", "") or ""
                                album = getattr(control, "album_title", "") or getattr(control, "album", "") or ""
                                if title or artist:
                                    # Return full metadata if available
                                    payload = {"playing": True, "title": title, "artist": artist, "album": album, "appId": app_id, "status": _normalize_playback_status(playback_status)}
                                    _smtc_debug_log("Returning Apple full metadata", payload, session=session, control=control, playback_status=playback_status)
                                    return json.dumps(payload)
                                # If metadata empty but we have a playback status, return minimal payload
                                print(f"[SMTC DEBUG] Returning minimal playing payload for Apple Music (app_id: {app_id}, playback_status: {playback_status})")
                                payload = {"playing": True, "title": "", "artist": "", "album": "", "appId": app_id, "status": _normalize_playback_status(playback_status)}
                                _smtc_debug_log("Returning Apple minimal payload", payload, session=session, control=control, playback_status=playback_status)
                                return json.dumps(payload)
                            except Exception as e:
                                print(f"[SMTC DEBUG] Apple metadata read failed: {e}; returning minimal payload")
                                payload = {"playing": True, "title": "", "artist": "", "album": "", "appId": app_id, "status": _normalize_playback_status(playback_status)}
                                _smtc_debug_log("Apple metadata read failed; returning minimal payload", payload, session=session, control=None, playback_status=playback_status)
                                return json.dumps(payload)
                    except Exception:
                        pass
                except Exception:
                    pass

                # Attempt to read media properties for non-Apple sessions or when Apple early-return not taken
                app_id = _get_session_app_id(session)
                try:
                    control = _get_media_properties(session)
                except Exception as e:
                    # If we cannot read metadata but playback indicates active, return minimal payload (with diagnostics)
                    if is_playing:
                        payload = {
                            "playing": True,
                            "title": "",
                            "artist": "",
                            "album": "",
                            "appId": app_id,
                            "status": _normalize_playback_status(playback_status),
                        }
                        _smtc_debug_log(f"Metadata read failed; returning minimal payload: {e}", payload, session=session, control=None, playback_status=playback_status)
                        return json.dumps(payload)
                    # Otherwise skip this session
                    continue
                # Some sessions expose title/artist/album differently; use getattr for resilience
                title = getattr(control, "title", "") or ""
                artist = getattr(control, "artist", "") or ""
                album = getattr(control, "album_title", "") or getattr(control, "album", "") or ""

                # Try to extract thumbnail (may not be available)
                artwork_path = None
                try:
                    thumb = getattr(control, "thumbnail", None)
                    if thumb:
                        path = _extract_thumbnail_to_file(control)
                        if path and os.path.isfile(path):
                            artwork_path = path
                except Exception:
                    artwork_path = None

                # If the session is playing, return it even if metadata is sparse.
                if is_playing or title or artist:
                    app_id = _get_session_app_id(session)
                    data = {
                        "playing": True if is_playing else False,
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "appId": app_id,
                        "status": _normalize_playback_status(playback_status),
                    }
                    if artwork_path:
                        try:
                            ts = int(os.path.getmtime(artwork_path))
                            data["artworkPath"] = f"/artwork?t={ts}"
                        except Exception:
                            pass
                    # Cache last known non-empty metadata for this app
                    try:
                        if (title or artist) and app_id:
                            LAST_KNOWN_META[app_id] = {"title": title, "artist": artist, "album": album}
                    except Exception:
                        pass
                    _smtc_debug_log("Returning session payload", data, session=session, control=control, playback_status=playback_status)
                    return json.dumps(data)
            except Exception:
                # If any session fails, continue to next
                continue

        payload = {"playing": False, "error": "No active media session"}
        _smtc_debug_log("No active media session", payload, session=None)
        return json.dumps(payload)
    except Exception as e:
        return json.dumps({"playing": False, "error": f"Unexpected SMTC error: {e}"})
 
# Cross-platform wrapper used by the server
def get_now_playing():
    """Return JSON string describing current playback; dispatches per-platform."""
    try:
        pf = platform.system()
        if pf == "Windows":
            return get_windows_smtc_track()
        else:
            # macOS AppleScript support removed in this Windows-focused fork
            return json.dumps({"playing": False, "error": f"Unsupported platform for this fork: {pf}"})
    except Exception as e:
        return json.dumps({"playing": False, "error": f"Now playing wrapper error: {e}"})

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
        
        # Serve static files (HTML, CSS, JS)
        if path == '/' or path.endswith('.html') or path.endswith('.css') or path.endswith('.js'):
            # If path is just '/', serve overlay.html
            if path == '/':
                file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'overlay.html')
            else:
                # Remove leading slash and get the file from current directory
                file_name = path.lstrip('/')
                file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)
            
            # Add debugging for file resolution
            print(f"Static file requested: {path}")
            print(f"Resolving to path: {file_path}")
            print(f"File exists: {os.path.exists(file_path)}")
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                # Set correct content type based on file extension
                if path.endswith('.html'):
                    content_type = 'text/html'
                elif path.endswith('.css'):
                    content_type = 'text/css'
                elif path.endswith('.js'):
                    content_type = 'text/javascript'
                else:
                    content_type = 'text/html'  # default for '/' path
                
                content_length = len(content)
                print(f"Serving {path} ({content_length} bytes) as {content_type}")
                
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(content_length))
                self.send_header('Cache-Control', 'no-cache, must-revalidate')
                self.end_headers()
                self.wfile.write(content)
                return
            except FileNotFoundError:
                print(f"ERROR: File not found: {file_path}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
                return
            except Exception as e:
                print(f"ERROR serving {path}: {str(e)}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode())
                return
        
        # Route requests
        if path == '/nowplaying':
            print("Handling /nowplaying request")
            music_data = get_now_playing()
            
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
            # Fixed path to the artwork file (use OS temp directory)
            artwork_path = os.path.join(_runtime_dir(), "harmony_deck_cover.jpg")
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
                
        elif path.startswith('/assets/fonts/'):
            # Extract the filename from the path
            font_file = path.split('/')[-1]
            font_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets', 'fonts', font_file)
            
            print(f"Serving font file: {font_path}")
            
            try:
                # Open in binary mode for font files
                with open(font_path, 'rb') as f:
                    file_data = f.read()
                
                self.send_response(200)
                # Set the correct MIME type for TTF fonts
                self.send_header('Content-type', 'font/ttf')
                # Allow caching for fonts (unlike dynamic content)
                self.send_header('Cache-Control', 'max-age=86400')  # Cache for 24 hours
                self.end_headers()
                self.wfile.write(file_data)
                print(f"Font file '{font_file}' served successfully")
                
            except Exception as e:
                print(f"Error serving font file: {e}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Font file not found: {str(e)}'.encode())
                
        elif path.startswith('/assets/images/'):
            # Extract the filename from the path
            image_file = path.split('/')[-1]
            image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets', 'images', image_file)
            
            print(f"Serving image file: {image_path}")
            
            try:
                # Open in binary mode for image files
                with open(image_path, 'rb') as f:
                    file_data = f.read()
                
                self.send_response(200)
                # Set content type based on file extension
                if image_file.lower().endswith('.png'):
                    content_type = 'image/png'
                elif image_file.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif image_file.lower().endswith('.gif'):
                    content_type = 'image/gif'
                elif image_file.lower().endswith('.svg'):
                    content_type = 'image/svg+xml'
                else:
                    content_type = 'application/octet-stream'
                
                self.send_header('Content-type', content_type)
                self.send_header('Cache-Control', 'max-age=86400')  # Cache for 24 hours
                self.end_headers()
                self.wfile.write(file_data)
                print(f"Image file '{image_file}' served successfully")
                
            except Exception as e:
                print(f"Error serving image file: {e}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Image file not found: {str(e)}'.encode())
                
        else:
            print(f"404 Not Found: {path}")
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"404 Not Found")

# Start the web server, finding an available port
def run_server(preferred_port=None): # Accept preferred_port argument
    global zmq_context # Declare zmq_context as global for this function's scope
    httpd = None
    actual_port = -1
    port_found = False

    # 1. Try the preferred port first if provided
    if preferred_port:
        print(f"Attempting to use preferred port: {preferred_port}")
        try:
            # Initialize ZMQ context if needed (now using function-scoped global)
            if zmq_context is None:
                zmq_context = zmq.Context()
                print("ZMQ context initialized")
    
            server_address = ('', preferred_port)
            httpd = HTTPServer(server_address, MusicHandler)
            actual_port = preferred_port
            port_found = True # Mark as found
            # Always print the chosen port in a machine-readable form so parent processes
            # (like the tray app) can parse it reliably.
            print(f"JAMDECK_PORT={actual_port}")
            sys.stdout.flush()
            print(f"Successfully bound to preferred port {actual_port}")

        except socket.error as e:
            if e.errno == socket.errno.EADDRINUSE:
                print(f"Preferred port {preferred_port} already in use. Falling back to automatic detection.")
            else:
                print(f"Error trying preferred port {preferred_port}: {e}")
                # Don't immediately exit, allow fallback to automatic detection
        except Exception as e:
            print(f"Server setup error on preferred port {preferred_port}: {e}")
            # Don't immediately exit, allow fallback to automatic detection

    # 2. If preferred port failed or wasn't provided, try automatic detection
    if not port_found:
        print("Attempting automatic port detection...")
        for i in range(MAX_PORT_ATTEMPTS):
            port_to_try = START_PORT + i
            # Skip the preferred port if it was already tried and failed
            if preferred_port and port_to_try == preferred_port:
                continue

            try:
                # Initialize ZMQ context if needed (now using function-scoped global)
                if zmq_context is None:
                    zmq_context = zmq.Context()
                    print("ZMQ context initialized") # Keep this informational message

                server_address = ('', port_to_try)
                httpd = HTTPServer(server_address, MusicHandler)
                actual_port = port_to_try

                # IMPORTANT: Print the port for the parent process BEFORE other messages
                print(f"JAMDECK_PORT={actual_port}")
                sys.stdout.flush() # Ensure it's sent immediately
                
                print(f"Starting music server on port {actual_port}...")
                print(f"Open http://localhost:{actual_port}/ in your browser or OBS")
                print(f"Press Ctrl+C to stop the server")
                port_found = True # Mark as found
                break # Port found, exit loop
                
            except socket.error as e:
                if e.errno == socket.errno.EADDRINUSE:
                    print(f"Port {port_to_try} is busy, trying next...")
                    continue # Try next port (Now correctly indented)
                else: # This else correctly handles other socket errors
                    print(f"Server error on port {port_to_try}: {e}")
                    cleanup()
                    return # Exit if other socket error
            except Exception as e: # This except handles non-socket errors from the try block
                print(f"Server setup error on port {port_to_try}: {e}")
                cleanup()
            return # Exit on other setup errors

    # Check if a port was successfully found either way
    if not port_found or httpd is None:
        # Construct a more informative error message
        error_message = f"Could not bind to the preferred port ({preferred_port}) " if preferred_port else ""
        error_message += f"or find an available port in the range {START_PORT}-{START_PORT + MAX_PORT_ATTEMPTS - 1}."
        print(error_message)
        cleanup()
        return

    try:
        # Test the now-playing interface before starting the server (only if server started)
        print("\nTesting now-playing interface...")
        test_result = get_now_playing()
        print(f"Test result: {test_result}")
        print("\nServer ready!")

        # Start server
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
        if httpd:
            httpd.server_close()
        cleanup()
        print("Server stopped")
    except Exception as e:
        print(f"Server runtime error: {e}")
        if httpd:
            httpd.server_close()
        cleanup()

if __name__ == '__main__':
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Jam Deck Music Server")
    parser.add_argument('--port', type=int, help='Preferred port number to start the server on.')
    parser.add_argument('--debug', action='store_true', help='Enable verbose debug logging to logs/overlay.log')
    args = parser.parse_args()
    # --- End Argument Parsing ---

    # Force output buffering off for better debugging
    try:
        if getattr(sys, "stdout", None) and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(line_buffering=True)
        else:
            # Fallback: ensure stdout is a text wrapper with line buffering (fd=1)
            import io
            try:
                sys.stdout = io.TextIOWrapper(open(1, "wb", 0), encoding="utf-8", line_buffering=True)
            except Exception:
                # If creating a new TextIOWrapper fails, ignore and continue
                pass
    except Exception:
        # If any unexpected error happens while configuring stdout, ignore and continue
        pass
    # Apply debug flag from CLI
    try:
        if args.debug:
            DEBUG_ENABLED = True
    except Exception:
        pass

    # Wrap stdout to route SMTC debug lines into logs/overlay.log
    try:
        sys.stdout = _DebugStdoutProxy(sys.stdout)
    except Exception:
        pass

    print(f"Jam Deck v{VERSION} - Music Now Playing Server")
    run_server(preferred_port=args.port) # Pass preferred port to run_server
