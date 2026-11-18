"""
Global dark/light theme manager.

Usage:
    import ui.theme as theme

    theme.apply(dark)     # set theme (call once after Tk root created to initialise)
    theme.toggle()        # flip dark ↔ light
    theme.is_dark()       # current state
    theme.register(cb)    # callback(dark: bool) called on every change
    theme.unregister(cb)  # remove callback
"""

_dark: bool = False
_listeners: list = []
_native_body_size: int = -12   # TkDefaultFont pixel size captured before sv_ttk loads
_sv_ttk_available: bool | None = None  # None = not yet checked


def _check_sv_ttk() -> bool:
    global _sv_ttk_available
    if _sv_ttk_available is None:
        try:
            import sv_ttk  # noqa: F401
            _sv_ttk_available = True
        except ImportError:
            _sv_ttk_available = False
    return _sv_ttk_available


def _apply_fallback_theme(dark: bool) -> None:
    """Basic dark/light fallback using ttk's built-in clam theme when sv_ttk is absent."""
    try:
        import tkinter.ttk as ttk
        style = ttk.Style()
        if dark:
            style.theme_use('clam')
            style.configure('.', background='#2d2d2d', foreground='#e0e0e0',
                            fieldbackground='#3c3c3c', bordercolor='#555555',
                            troughcolor='#3c3c3c', selectbackground='#4a6fa5',
                            selectforeground='#ffffff', insertcolor='#e0e0e0')
            style.configure('TEntry',     fieldbackground='#3c3c3c', foreground='#e0e0e0')
            style.configure('TCombobox',  fieldbackground='#3c3c3c', foreground='#e0e0e0')
            style.configure('TSpinbox',   fieldbackground='#3c3c3c', foreground='#e0e0e0')
            style.configure('TNotebook',  background='#2d2d2d')
            style.configure('TNotebook.Tab', background='#3c3c3c', foreground='#e0e0e0',
                            padding=[8, 2])
            style.map('TNotebook.Tab',
                      background=[('selected', '#4a4a4a')],
                      foreground=[('selected', '#ffffff')])
            style.configure('TLabelframe',       background='#2d2d2d', foreground='#e0e0e0')
            style.configure('TLabelframe.Label', background='#2d2d2d', foreground='#e0e0e0')
            style.configure('TCheckbutton', background='#2d2d2d', foreground='#e0e0e0')
            style.configure('TRadiobutton', background='#2d2d2d', foreground='#e0e0e0')
            style.configure('TButton',      background='#3c3c3c', foreground='#e0e0e0')
            style.configure('TLabel',       background='#2d2d2d', foreground='#e0e0e0')
            style.configure('TFrame',       background='#2d2d2d')
            style.configure('TSeparator',   background='#555555')
            style.configure('TScrollbar',   background='#3c3c3c', troughcolor='#2d2d2d',
                            arrowcolor='#e0e0e0')
            style.map('TButton',
                      background=[('active', '#505050'), ('pressed', '#606060')])
        else:
            style.theme_use('vista' if 'vista' in ttk.Style().theme_names() else 'clam')
    except Exception:
        pass


def _capture_native_size():
    """Snapshot TkDefaultFont size before sv_ttk changes it.

    On Linux, the desktop default is often 11pt (larger than Windows' ~9pt).
    Cap to 9pt so the UI matches Windows visual density.
    """
    global _native_body_size
    try:
        import sys
        import tkinter.font as tkfont
        size = tkfont.nametofont('TkDefaultFont').actual()['size']
        if sys.platform.startswith('linux'):
            # Prefer positive points; Linux reports 11, Windows-like target is 9
            size = 9 if abs(size) > 9 else size
        _native_body_size = size
    except Exception:
        pass


def _restore_sv_font_sizes():
    """Bring named fonts back down to the captured/capped body size."""
    try:
        import tkinter.font as tkfont
        size = _native_body_size
        for name in ('SunValleyBodyFont', 'SunValleyCaptionFont',
                     'TkDefaultFont', 'TkTextFont', 'TkFixedFont',
                     'TkMenuFont', 'TkHeadingFont', 'TkSmallCaptionFont'):
            try:
                tkfont.nametofont(name).configure(size=size)
            except Exception:
                pass  # SunValley names absent until sv_ttk loads
    except Exception:
        pass


def is_dark() -> bool:
    return _dark


def toggle() -> None:
    apply(not _dark)


def apply(dark: bool) -> None:
    global _dark
    _dark = dark
    _capture_native_size()
    if _check_sv_ttk():
        try:
            import sv_ttk
            sv_ttk.set_theme('dark' if dark else 'light')
        except Exception:
            _apply_fallback_theme(dark)
    else:
        _apply_fallback_theme(dark)
    _restore_sv_font_sizes()
    for cb in list(_listeners):
        try:
            cb(dark)
        except Exception:
            pass


def register(cb) -> None:
    if cb not in _listeners:
        _listeners.append(cb)


def unregister(cb) -> None:
    try:
        _listeners.remove(cb)
    except ValueError:
        pass
