# PyInstaller hook for pyzmq / zmq
# Collects dynamic libs (libzmq) and data files so PyInstaller bundles them correctly.
# Place this file in the project root so PyInstaller picks it up via its default hook search path,
# or pass --additional-hooks-dir=. when invoking pyinstaller.

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files, collect_submodules

# Collect libzmq dynamic libraries (DLL/.so/.dylib) used by pyzmq
binaries = collect_dynamic_libs('zmq')

# Collect package data (if any)
datas = collect_data_files('zmq')

# Ensure all zmq submodules are available
hiddenimports = collect_submodules('zmq')