# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for RestimFunscriptProcessor (Windows).

Bundles libmpv only (libmpv-2.dll) for self-contained video playback.
No VLC.

Build machine needs the DLL at one of:
  - %MPV_DIR%\\libmpv-2.dll
  - third_party\\mpv\\libmpv-2.dll
  - .\\libmpv-2.dll

Download: shinchiro mpv-dev-x86_64-*.7z from
https://github.com/shinchiro/mpv-winbuild-cmake/releases
Extract libmpv-2.dll into third_party/mpv/

Uses onefile mode — single portable executable.
"""
import os
import re
from PyInstaller.utils.hooks import collect_all

# ---------------------------------------------------------------------------
# Version (read from version.py without importing the whole app)
# ---------------------------------------------------------------------------
with open('version.py', encoding='utf-8') as _f:
    _m = re.search(r'__version__\s*=\s*"([^"]+)"', _f.read())
_version = _m.group(1) if _m else 'unknown'
_exe_name = f'RestimFunscriptProcessor-v{_version}'

# ---------------------------------------------------------------------------
# libmpv (required for Windows video preview)
# ---------------------------------------------------------------------------
_SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))


def _find_mpv_dir():
    candidates = []
    env = os.environ.get('MPV_DIR')
    if env:
        candidates.append(env)
    candidates.extend([
        os.path.join(_SPEC_DIR, 'third_party', 'mpv'),
        _SPEC_DIR,
        r'C:\mpv',
    ])
    for d in candidates:
        if os.path.isfile(os.path.join(d, 'libmpv-2.dll')):
            return d
        if os.path.isfile(os.path.join(d, 'mpv-2.dll')):
            return d
    return None


MPV_DIR = _find_mpv_dir()

datas = [('config.event_definitions.yml', '.')]
# Do not bundle config.json — user settings live next to the exe and must not
# be overwritten by a packaged copy.

binaries = []
_upx_exclude = []

if not MPV_DIR:
    raise SystemExit(
        'ERROR: libmpv-2.dll not found. Place it in third_party/mpv/ '
        'or set MPV_DIR. See third_party/mpv/README.md'
    )

for dll_name in ('libmpv-2.dll', 'mpv-2.dll'):
    src = os.path.join(MPV_DIR, dll_name)
    if os.path.exists(src):
        binaries.append((src, '.'))
        _upx_exclude.append(dll_name)
        print(f'Bundling mpv DLL: {src} ({os.path.getsize(src) / (1024 * 1024):.1f} MB)')
        break

# ---------------------------------------------------------------------------
# Python packages
# ---------------------------------------------------------------------------
hiddenimports = [
    'tkinter',
    'numpy',
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.backends.backend_tkagg',
    'matplotlib.figure',
    'matplotlib.patches',
    'json',
    'pathlib',
    'processing.linear_mapping',
    'processing.motion_axis_generation',
    'mpv',
]

for _pkg in ('ui', 'processing'):
    _r = collect_all(_pkg)
    datas    += _r[0]
    binaries += _r[1]
    hiddenimports += _r[2]

# sv_ttk (optional dark theme — include if installed)
try:
    _r = collect_all('sv_ttk')
    datas    += _r[0]
    binaries += _r[1]
    hiddenimports += _r[2]
except Exception:
    pass

# tkinterdnd2 (optional drag-and-drop — include if installed)
try:
    _r = collect_all('tkinterdnd2')
    datas    += _r[0]
    binaries += _r[1]
    hiddenimports += _r[2]
except Exception:
    pass

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook_mpv.py'],
    excludes=['vlc'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ---------------------------------------------------------------------------
# Onefile EXE — binaries and datas packed directly in; no COLLECT step
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=_exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=_upx_exclude or ['libmpv-2.dll'],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
