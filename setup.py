"""
Setup script for py2app to create a standalone macOS app
"""
from setuptools import setup

APP = ['music_server.py']
DATA_FILES = [
    ('', ['overlay.html', 'preview.png']),
]
OPTIONS = {
    'argv_emulation': True,
    'packages': [],
    'plist': {
        'CFBundleName': 'Jam Deck',
        'CFBundleDisplayName': 'Jam Deck (for OBS)',
        'CFBundleIdentifier': 'com.jamdeck.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025',
    },
    'iconfile': 'preview.png',  # Optionally, if you have an icon file
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    name='Jam Deck',
)