# -*- mode: python -*-
# PyInstaller spec for music_server
# Usage: pyinstaller music_server.spec

block_cipher = None

a = Analysis(
    ['music_server.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('overlay.html', '.'),
        ('overlay.css', '.'),
        ('overlay.js', '.'),
        ('assets', 'assets'),
    ],
    hiddenimports=[],
    hookspath=['.'],  # allow local hooks (hook-pyzmq.py)
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='music_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)