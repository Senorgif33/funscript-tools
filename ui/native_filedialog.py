"""
Native-ish file dialogs.

On Linux, prefer xdg-desktop-portal FileChooser so the dialog matches
the user's desktop portal backend (GNOME/KDE/GTK/etc). Fall back to
zenity/kdialog, then tkinter.filedialog.

Windows and macOS use tkinter.filedialog (native-like there).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)

FileTypes = Sequence[Tuple[str, str]]

_PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
_PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
_PORTAL_IFACE = "org.freedesktop.portal.FileChooser"
_REQUEST_IFACE = "org.freedesktop.portal.Request"


def askopenfilename(**kwargs) -> str:
    paths = _open(multiple=False, directory=False, **kwargs)
    return paths[0] if paths else ""


def askopenfilenames(**kwargs) -> Union[Tuple[str, ...], Tuple[()]]:
    paths = _open(multiple=True, directory=False, **kwargs)
    return tuple(paths) if paths else ()


def asksaveasfilename(**kwargs) -> str:
    path = _save(**kwargs)
    return path or ""


def askdirectory(**kwargs) -> str:
    paths = _open(multiple=False, directory=True, **kwargs)
    return paths[0] if paths else ""


def _open(*, multiple: bool, directory: bool, **kwargs) -> List[str]:
    title = kwargs.get("title") or ("Select Folder" if directory else "Select File")
    filetypes = kwargs.get("filetypes")
    initialdir = kwargs.get("initialdir")
    parent = kwargs.get("parent")

    if sys.platform.startswith("linux"):
        paths = _linux_open(
            title=title,
            filetypes=None if directory else filetypes,
            initialdir=initialdir,
            multiple=multiple,
            directory=directory,
            parent=parent,
        )
        if paths is not None:
            return paths

    from tkinter import filedialog

    if directory:
        chosen = filedialog.askdirectory(
            title=title,
            initialdir=initialdir,
            parent=parent,
        )
        return [chosen] if chosen else []

    if multiple:
        chosen = filedialog.askopenfilenames(
            title=title,
            filetypes=filetypes or [("All files", "*.*")],
            initialdir=initialdir,
            parent=parent,
        )
        return list(chosen) if chosen else []

    chosen = filedialog.askopenfilename(
        title=title,
        filetypes=filetypes or [("All files", "*.*")],
        initialdir=initialdir,
        parent=parent,
    )
    return [chosen] if chosen else []


def _save(**kwargs) -> Optional[str]:
    title = kwargs.get("title") or "Save File"
    filetypes = kwargs.get("filetypes")
    initialdir = kwargs.get("initialdir")
    initialfile = kwargs.get("initialfile")
    defaultextension = kwargs.get("defaultextension")
    parent = kwargs.get("parent")

    initial_name = initialfile
    if not initial_name and defaultextension:
        initial_name = f"untitled{defaultextension}"

    if sys.platform.startswith("linux"):
        path = _linux_save(
            title=title,
            filetypes=filetypes,
            initialdir=initialdir,
            initialfile=initial_name,
            parent=parent,
        )
        if path is not None:
            if path and defaultextension and not Path(path).suffix:
                path = path + defaultextension
            return path

    from tkinter import filedialog

    return filedialog.asksaveasfilename(
        title=title,
        filetypes=filetypes or [("All files", "*.*")],
        initialdir=initialdir,
        initialfile=initialfile,
        defaultextension=defaultextension,
        parent=parent,
    ) or None


def _linux_open(
    *,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    multiple: bool,
    directory: bool,
    parent,
) -> Optional[List[str]]:
    paths = _portal_file_chooser(
        mode="open",
        title=title,
        filetypes=filetypes,
        initialdir=initialdir,
        initialfile=None,
        multiple=multiple,
        directory=directory,
        parent=parent,
    )
    if paths is not None:
        return paths

    paths = _cli_file_chooser(
        mode="open",
        title=title,
        filetypes=filetypes,
        initialdir=initialdir,
        initialfile=None,
        multiple=multiple,
        directory=directory,
    )
    return paths


def _linux_save(
    *,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    initialfile: Optional[str],
    parent,
) -> Optional[str]:
    paths = _portal_file_chooser(
        mode="save",
        title=title,
        filetypes=filetypes,
        initialdir=initialdir,
        initialfile=initialfile,
        multiple=False,
        directory=False,
        parent=parent,
    )
    if paths is not None:
        return paths[0] if paths else ""

    paths = _cli_file_chooser(
        mode="save",
        title=title,
        filetypes=filetypes,
        initialdir=initialdir,
        initialfile=initialfile,
        multiple=False,
        directory=False,
    )
    if paths is None:
        return None
    return paths[0] if paths else ""


def _portal_file_chooser(
    *,
    mode: str,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    initialfile: Optional[str],
    multiple: bool,
    directory: bool,
    parent,
) -> Optional[List[str]]:
    """
    Call xdg-desktop-portal FileChooser.

    Returns:
      list of paths on success (empty list if user cancelled),
      None if portal unavailable / failed (caller should fall back).
    """
    # Prefer in-process dbus when available (dev installs / host python).
    result = _portal_via_dbus(
        mode=mode,
        title=title,
        filetypes=filetypes,
        initialdir=initialdir,
        initialfile=initialfile,
        multiple=multiple,
        directory=directory,
        parent=parent,
    )
    if result is not None:
        return result

    # Frozen AppImage: host python3 often has dbus+gi; our embed may not.
    result = _portal_via_host_python(
        mode=mode,
        title=title,
        filetypes=filetypes,
        initialdir=initialdir,
        initialfile=initialfile,
        multiple=multiple,
        directory=directory,
    )
    return result


def _parent_window_hint(parent) -> str:
    """Portal parent window identifier (x11:WID) when possible."""
    if parent is None:
        return ""
    try:
        parent.update_idletasks()
        wid = int(parent.winfo_id())
        return f"x11:{wid:x}"
    except Exception:
        return ""


def _filters_for_portal(filetypes: Optional[FileTypes]):
    """Convert tk filetypes to portal a(sa(us))."""
    import dbus

    filters = dbus.Array([], signature="(sa(us))")
    if not filetypes:
        filters.append(("All files", dbus.Array([(0, "*")], signature="(us)")))
        return filters

    for name, pattern in filetypes:
        globs = []
        for part in str(pattern).replace(";", " ").split():
            part = part.strip()
            if not part:
                continue
            globs.append((0, part))
        if not globs:
            globs.append((0, "*"))
        filters.append((name, dbus.Array(globs, signature="(us)")))
    return filters


def _normalize_initialdir(initialdir: Optional[str]) -> Optional[str]:
    """Absolute existing directory for choosers; trailing slash avoids GTK parent quirk."""
    if not initialdir:
        return None
    try:
        path = os.path.abspath(os.path.expanduser(str(initialdir)))
    except Exception:
        return None
    if not os.path.isdir(path):
        return None
    if not path.endswith(os.sep):
        path = path + os.sep
    return path


def _path_to_ay(path: str):
    """Null-terminated bytes for portal current_folder."""
    import dbus

    # Keep trailing slash — some GTK portals treat bare dir as "select this entry"
    # and open the parent instead.
    folder = _normalize_initialdir(path) or (os.path.abspath(path) + os.sep)
    raw = os.fsencode(folder) + b"\x00"
    return dbus.Array(raw, signature="y")


def _uris_to_paths(uris: Iterable[str]) -> List[str]:
    paths: List[str] = []
    for uri in uris:
        parsed = urlparse(str(uri))
        if parsed.scheme != "file":
            continue
        paths.append(unquote(parsed.path))
    return paths


def _portal_via_dbus(
    *,
    mode: str,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    initialfile: Optional[str],
    multiple: bool,
    directory: bool,
    parent,
) -> Optional[List[str]]:
    try:
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        from gi.repository import GLib
    except Exception as exc:
        logger.debug("Portal dbus stack unavailable: %s", exc)
        return None

    try:
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        portal = bus.get_object(_PORTAL_BUS_NAME, _PORTAL_OBJECT_PATH)
        iface = dbus.Interface(portal, _PORTAL_IFACE)

        options = {
            "modal": dbus.Boolean(True),
        }
        if mode == "open":
            options["multiple"] = dbus.Boolean(multiple)
            options["directory"] = dbus.Boolean(directory)
        if filetypes:
            options["filters"] = _filters_for_portal(filetypes)
        initialdir = _normalize_initialdir(initialdir)
        if initialdir:
            options["current_folder"] = _path_to_ay(initialdir)
        if mode == "save" and initialfile:
            options["current_name"] = str(initialfile)

        parent_hint = _parent_window_hint(parent)
        loop = GLib.MainLoop()
        result_box: dict = {"done": False, "paths": None, "failed": False}

        def _on_response(response, results):
            try:
                if int(response) != 0:
                    result_box["paths"] = []
                else:
                    uris = results.get("uris", [])
                    result_box["paths"] = _uris_to_paths(uris)
            except Exception:
                logger.exception("Portal response parse failed")
                result_box["failed"] = True
            finally:
                result_box["done"] = True
                loop.quit()

        if mode == "save":
            request_path = iface.SaveFile(parent_hint, title, options)
        else:
            request_path = iface.OpenFile(parent_hint, title, options)

        request = bus.get_object(_PORTAL_BUS_NAME, request_path)
        request_iface = dbus.Interface(request, _REQUEST_IFACE)
        request_iface.connect_to_signal("Response", _on_response)

        # Safety timeout so a broken portal cannot hang the UI forever.
        GLib.timeout_add_seconds(300, loop.quit)
        loop.run()

        if not result_box["done"] or result_box["failed"]:
            return None
        return result_box["paths"]
    except Exception as exc:
        logger.debug("Portal FileChooser failed: %s", exc)
        return None


_HOST_PORTAL_SCRIPT = r"""
import os, sys, json
from urllib.parse import unquote, urlparse

mode = sys.argv[1]
title = sys.argv[2]
multiple = sys.argv[3] == "1"
directory = sys.argv[4] == "1"
initialdir = sys.argv[5] or None
initialfile = sys.argv[6] or None
filters_json = sys.argv[7]

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
portal = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
iface = dbus.Interface(portal, "org.freedesktop.portal.FileChooser")

options = {"modal": dbus.Boolean(True)}
if mode == "open":
    options["multiple"] = dbus.Boolean(multiple)
    options["directory"] = dbus.Boolean(directory)

filetypes = json.loads(filters_json)
filters = dbus.Array([], signature="(sa(us))")
for name, pattern in filetypes:
    globs = []
    for part in str(pattern).replace(";", " ").split():
        part = part.strip()
        if part:
            globs.append((0, part))
    if not globs:
        globs.append((0, "*"))
    filters.append((name, dbus.Array(globs, signature="(us)")))
if filters:
    options["filters"] = filters

if initialdir:
    folder = os.path.abspath(os.path.expanduser(initialdir))
    if os.path.isdir(folder):
        if not folder.endswith(os.sep):
            folder = folder + os.sep
        raw = os.fsencode(folder) + b"\x00"
        options["current_folder"] = dbus.Array(raw, signature="y")
if mode == "save" and initialfile:
    options["current_name"] = str(initialfile)

loop = GLib.MainLoop()
out = {"paths": None, "ok": False}

def on_response(response, results):
    try:
        if int(response) != 0:
            out["paths"] = []
        else:
            paths = []
            for uri in results.get("uris", []):
                p = urlparse(str(uri))
                if p.scheme == "file":
                    paths.append(unquote(p.path))
            out["paths"] = paths
        out["ok"] = True
    finally:
        loop.quit()

if mode == "save":
    req_path = iface.SaveFile("", title, options)
else:
    req_path = iface.OpenFile("", title, options)
req = bus.get_object("org.freedesktop.portal.Desktop", req_path)
dbus.Interface(req, "org.freedesktop.portal.Request").connect_to_signal("Response", on_response)
GLib.timeout_add_seconds(300, loop.quit)
loop.run()
if not out["ok"]:
    sys.exit(2)
print(json.dumps(out["paths"]))
"""


def _portal_via_host_python(
    *,
    mode: str,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    initialfile: Optional[str],
    multiple: bool,
    directory: bool,
) -> Optional[List[str]]:
    host_python = "/usr/bin/python3"
    if not os.path.isfile(host_python):
        host_python = shutil.which("python3") or ""
    if not host_python:
        return None

    # Avoid recursion if we are already host python without dbus.
    if not getattr(sys, "frozen", False):
        # In-process path already tried; only useful when frozen.
        return None

    import json

    filters = list(filetypes) if filetypes else [("All files", "*.*")]
    try:
        proc = subprocess.run(
            [
                host_python,
                "-c",
                _HOST_PORTAL_SCRIPT,
                mode,
                title,
                "1" if multiple else "0",
                "1" if directory else "0",
                initialdir or "",
                initialfile or "",
                json.dumps(filters),
            ],
            capture_output=True,
            text=True,
            timeout=320,
            check=False,
            env=os.environ.copy(),
        )
    except Exception as exc:
        logger.debug("Host-python portal helper failed: %s", exc)
        return None

    if proc.returncode != 0:
        logger.debug(
            "Host-python portal helper exit %s: %s",
            proc.returncode,
            (proc.stderr or "").strip(),
        )
        return None

    try:
        import json as _json

        data = _json.loads((proc.stdout or "").strip() or "[]")
        if not isinstance(data, list):
            return None
        return [str(p) for p in data]
    except Exception:
        return None


def _desktop_hint() -> str:
    parts = []
    for key in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "XDG_SESSION_DESKTOP"):
        val = os.environ.get(key, "")
        if val:
            parts.append(val.lower())
    return ":".join(parts)


def _cli_file_chooser(
    *,
    mode: str,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    initialfile: Optional[str],
    multiple: bool,
    directory: bool,
) -> Optional[List[str]]:
    desktop = _desktop_hint()
    prefer_kdialog = any(x in desktop for x in ("kde", "plasma"))

    order = ["kdialog", "zenity"] if prefer_kdialog else ["zenity", "kdialog"]
    for tool in order:
        if not shutil.which(tool):
            continue
        try:
            if tool == "zenity":
                return _zenity(
                    mode=mode,
                    title=title,
                    filetypes=filetypes,
                    initialdir=initialdir,
                    initialfile=initialfile,
                    multiple=multiple,
                    directory=directory,
                )
            return _kdialog(
                mode=mode,
                title=title,
                filetypes=filetypes,
                initialdir=initialdir,
                initialfile=initialfile,
                multiple=multiple,
                directory=directory,
            )
        except Exception as exc:
            logger.debug("%s file chooser failed: %s", tool, exc)
            continue
    return None


def _zenity_filter_args(filetypes: Optional[FileTypes]) -> List[str]:
    args: List[str] = []
    if not filetypes:
        return args
    for name, pattern in filetypes:
        # zenity: --file-filter=Name | *.ext *.ext2
        patterns = " ".join(str(pattern).replace(";", " ").split())
        args.append(f"--file-filter={name} | {patterns}")
    return args


def _zenity(
    *,
    mode: str,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    initialfile: Optional[str],
    multiple: bool,
    directory: bool,
) -> Optional[List[str]]:
    cmd = ["zenity", "--file-selection", f"--title={title}"]
    if mode == "save":
        cmd.append("--save")
        cmd.append("--confirm-overwrite")
    if directory:
        cmd.append("--directory")
    if multiple:
        cmd.append("--multiple")
        cmd.append("--separator=\n")
    initialdir = _normalize_initialdir(initialdir)
    if initialdir:
        # Trailing slash / explicit dir start keeps zenity inside the folder.
        filename = initialfile if initialfile else ""
        cmd.append(f"--filename={os.path.join(initialdir, filename)}")
    elif initialfile:
        cmd.append(f"--filename={initialfile}")
    if not directory:
        cmd.extend(_zenity_filter_args(filetypes))

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # Cancel is also non-zero; treat as empty selection when stderr empty-ish.
        if proc.returncode == 1:
            return []
        return None
    out = (proc.stdout or "").strip("\n")
    if not out:
        return []
    if multiple:
        return [line for line in out.split("\n") if line]
    return [out]


def _kdialog_filter(filetypes: Optional[FileTypes]) -> str:
    if not filetypes:
        return ""
    # kdialog: "Name (*.ext *.ext2)"
    parts = []
    for name, pattern in filetypes:
        patterns = " ".join(str(pattern).replace(";", " ").split())
        parts.append(f"{name} ({patterns})")
    return "\n".join(parts)


def _kdialog(
    *,
    mode: str,
    title: str,
    filetypes: Optional[FileTypes],
    initialdir: Optional[str],
    initialfile: Optional[str],
    multiple: bool,
    directory: bool,
) -> Optional[List[str]]:
    start = ""
    initialdir = _normalize_initialdir(initialdir)
    if initialdir:
        start = os.path.join(initialdir, initialfile or "")
    elif initialfile:
        start = initialfile

    if directory:
        cmd = ["kdialog", "--getexistingdirectory", start or os.path.expanduser("~"), "--title", title]
    elif mode == "save":
        cmd = ["kdialog", "--getsavefilename", start or os.path.expanduser("~"), "--title", title]
        filt = _kdialog_filter(filetypes)
        if filt:
            cmd.append(filt)
    elif multiple:
        cmd = ["kdialog", "--getopenfilename", "--multiple", "--separate-output", start or "", "--title", title]
        filt = _kdialog_filter(filetypes)
        if filt:
            cmd.append(filt)
    else:
        cmd = ["kdialog", "--getopenfilename", start or "", "--title", title]
        filt = _kdialog_filter(filetypes)
        if filt:
            cmd.append(filt)

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        if proc.returncode == 1:
            return []
        return None
    out = (proc.stdout or "").strip("\n")
    if not out:
        return []
    if multiple:
        return [line for line in out.split("\n") if line]
    return [out]
