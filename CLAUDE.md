# Jam Deck for OBS: Dev Reference Guide

## Project Structure
- `music_server.py` - Python server that exposes now-playing data and serves the overlay
- `overlay.html` - HTML/CSS/JS for the browser source display
- `app_windows.py` - Windows tray application (pystray) for starting/stopping server and scene management
- `app.py` - (deprecated) original macOS menu bar app; replaced by `app_windows.py` in this fork
- `collect_zmq.py` - Helper for ZeroMQ libraries bundling
- Browser source URL: http://localhost:<port>/ (use tray “Copy Scene URL”)

## Commands
- Start server (Windows): `python music_server.py [--port N] [--debug]`
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
- Server uses Windows SMTC (winrt) to read media sessions (Apple Music UWP). macOS AppleScript support is removed in this fork.
- Overlay connects to server API endpoint: `/nowplaying`
- Album artwork served via `/artwork` endpoint
- Static assets served via `/assets/fonts/` and `/assets/images/`
- Ten themes available: 5 rounded (Natural, Twitch, Dark, Pink, Light) and 5 square (Transparent, Neon, Terminal, Retro, High Contrast)

## Troubleshooting
- Overlay debug UI: append `?debug=true` to the overlay URL to show the debug panel.
- Logs: run the server with `--debug` or set `JAMDECK_DEBUG=1`; see logs/overlay.log.
- SMTC: ensure Apple Music (Microsoft Store UWP) publishes a media session; test with another UWP player if needed.
- Ports: default 8080; if busy the server auto-selects the next free port. Use `--port N` to prefer a specific port or set "preferred_port" in %USERPROFILE%\.jamdeck_config.json.

## Русская версия (Dev Guide)

### Структура проекта
- `music_server.py` — HTTP‑сервер: эндпоинты `/`, `/nowplaying`, `/artwork`, статика `assets/*`
- `overlay.html`/`overlay.css`/`overlay.js` — оверлей для источника Browser
- `app_windows.py` — трэй‑приложение (pystray) для запуска/остановки сервера и управления сценами
- `collect_zmq.py` — вспомогательный скрипт сборки ZeroMQ
- URL источника: http://localhost:<port>/ (копируйте через “Copy Scene URL” в трее)

### Команды
- Запуск сервера (Windows): `python music_server.py [--port N] [--debug]`
- Сборка (Windows): `.\build_windows.ps1 -version "1.0.0"`
- Версия приложения: обновляйте VERSION в `music_server.py`

### Заметки по архитектуре
- Используется Windows SMTC (winrt) для получения метаданных текущего медиасеанса (Apple Music UWP). Поддержка AppleScript/macOS удалена в этом форке.
- Оверлей обращается к `/nowplaying`; обложка — `/artwork`; шрифты/изображения — `/assets/fonts`, `/assets/images`.
- Темы: 10 штук (5 скруглённых + 5 квадратных). Настройки и ширина сохраняются в localStorage с привязкой к scene.

### Диагностика
- Включите отладку интерфейса: `?debug=true` в URL.
- Логи сервера: `--debug` или `JAMDECK_DEBUG=1` → файл logs/overlay.log.
- Проверяйте доступность SMTC‑сессий и корректность установленного пакета winrt/pywinrt.