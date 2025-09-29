#!/usr/bin/env python3
"""
setup.py — cross-platform helper for Jam Deck packaging.

This file no longer forces macOS-only py2app packaging. For Windows packaging
we provide PyInstaller spec files and a PowerShell build script:
  - build_windows.ps1
  - music_server.spec
  - app_windows.spec

If you need to create a macOS bundle using py2app, re-enable the py2app options
manually on a macOS machine and install py2app there.

The setup below registers the package metadata and includes static data files.
"""
from setuptools import setup
import glob
import os

APP = ['app.py']
DATA_FILES = [
    ('', ['overlay.html', 'overlay.js', 'overlay.css', 'music_server.py']),
    ('assets/images', glob.glob('assets/images/*')),
    ('assets/fonts', glob.glob('assets/fonts/*.ttf')),
]

setup(
    name='Jam Deck',
    version='1.1.3',
    description='Apple Music Now Playing overlay for OBS (Windows fork)',
    packages=[],
    scripts=APP,
    data_files=DATA_FILES,
)
