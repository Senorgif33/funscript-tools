"""
PyInstaller runtime hook — put bundled libmpv on the Windows DLL search path.

Frozen onefile extracts to sys._MEIPASS; onedir uses the exe directory.
python-mpv looks for libmpv-2.dll / mpv-2.dll via PATH / cwd / add_dll_directory.
"""
import os
import sys

if hasattr(sys, '_MEIPASS'):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(sys.executable))

# Prefer bundled DLL over any system install.
try:
    os.add_dll_directory(_base)
except (AttributeError, OSError):
    pass

_path = os.environ.get('PATH', '')
if _base not in _path.split(os.pathsep):
    os.environ['PATH'] = _base + os.pathsep + _path
