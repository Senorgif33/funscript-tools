# Windows libmpv for frozen builds

The Windows PyInstaller spec **requires** `libmpv-2.dll` from this folder (or `%MPV_DIR%`).
No VLC fallback.

## Setup (build machine only)

1. Download **mpv-dev-x86_64-*.7z** from  
   https://github.com/shinchiro/mpv-winbuild-cmake/releases
2. Extract `libmpv-2.dll` into this directory:
   `third_party/mpv/libmpv-2.dll`
3. Build: `pyinstaller funscript_processor.spec`

End users do **not** need mpv installed — the DLL is packed into the exe.

## Notes

- Prefer the `mpv-dev` package (has `libmpv-2.dll`), not only the player zip.
- Spec bundles **only** that one DLL (codecs linked inside).
- AV1 decode is included in typical shinchiro builds (dav1d/ffmpeg).
