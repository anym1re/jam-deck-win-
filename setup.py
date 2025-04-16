# setup.py (CORRECTED)
from setuptools import setup
import os
import shutil
import glob

# Copy libffi.8.dylib to the current directory if it exists
libffi_source = '/opt/homebrew/Cellar/libffi/3.4.7/lib/libffi.8.dylib'
libffi_dest = 'libffi.8.dylib'
if os.path.exists(libffi_source) and not os.path.exists(libffi_dest):
    shutil.copy2(libffi_source, libffi_dest)
    print(f"Copied {libffi_source} to {libffi_dest}")

APP = ['app.py']
DATA_FILES = [
    ('', ['overlay.html', 'music_server.py']),  # Required files
    ('assets/images', ['assets/images/jamdeck.icns', 'assets/images/jamdeck-template.png']),  # Image assets
    ('assets/fonts', glob.glob('assets/fonts/*.ttf')), # Include all TTF fonts
    ('Frameworks', ['libffi.8.dylib']),  # Include libffi in the Frameworks directory
]
OPTIONS = {
    'argv_emulation': True,
    'packages': ['zmq', 'ctypes', 'rumps'],  # Explicitly include required packages
    'includes': ['_ctypes'],  # Include _ctypes module
    'frameworks': ['/opt/homebrew/Cellar/libffi/3.4.7/lib/libffi.8.dylib'],  # Include libffi as a framework
    'dylib_excludes': ['libffi.dylib'],  # Exclude any old libffi versions
    'plist': {
        'CFBundleName': 'Jam Deck',
        'CFBundleDisplayName': 'Jam Deck for OBS',
        'CFBundleIdentifier': 'com.jamdeck.app',
        'CFBundleVersion': '1.1.3',
        'CFBundleShortVersionString': '1.1.2',
        'NSAppleEventsUsageDescription': 'This app requires access to Apple Music to display current track information.',
        'NSHumanReadableCopyright': '© 2025 Henry Manes',
        'LSUIElement': True,  # Makes the app a background agent with no dock icon
        'LSBackgroundOnly': False,  # Allows menu bar icon
    },
    'iconfile': 'assets/images/jamdeck.icns',
    'extra_scripts': ['collect_zmq.py'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    name='Jam Deck',
)
