"""Open the operating system's own file/folder picker.

A browser page cannot hand a server a real filesystem path (the File API
only exposes file contents, not locations), so when the user needs to point
the dashboard at an existing folder or file on this machine, the server
opens a native dialog instead of asking the page to fake one.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

PICK = ("folder", "file")


class DialogError(RuntimeError):
    pass


def _run(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=300
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DialogError(str(exc)) from exc
    return completed.stdout.strip()


def _macos(kind: str, title: str) -> str | None:
    if kind == "folder":
        script = f'POSIX path of (choose folder with prompt "{title}")'
    else:
        script = f'POSIX path of (choose file with prompt "{title}")'
    output = _run(["osascript", "-e", script])
    return output or None


def _windows(kind: str, title: str) -> str | None:
    if kind == "folder":
        script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog;"
            f'$f.Description = "{title}";'
            "if ($f.ShowDialog() -eq 'OK') { Write-Output $f.SelectedPath }"
        )
    else:
        script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$f = New-Object System.Windows.Forms.OpenFileDialog;"
            f'$f.Title = "{title}";'
            "if ($f.ShowDialog() -eq 'OK') { Write-Output $f.FileName }"
        )
    output = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
    return output or None


def _linux(kind: str, title: str) -> str | None:
    flag = "--directory" if kind == "folder" else ""
    if shutil.which("zenity"):
        args = ["zenity", "--file-selection", f"--title={title}"]
        if flag:
            args.append(flag)
        output = _run(args)
        return output or None
    if shutil.which("kdialog"):
        args = ["kdialog", "--getexistingdirectory" if kind == "folder" else "--getopenfilename"]
        output = _run(args)
        return output or None
    try:
        import tkinter
        import tkinter.filedialog
    except ImportError as exc:
        raise DialogError(
            "no native file picker available (install zenity, kdialog, or "
            "a tkinter-enabled Python)"
        ) from exc
    root = tkinter.Tk()
    root.withdraw()
    try:
        if kind == "folder":
            selected = tkinter.filedialog.askdirectory(title=title)
        else:
            selected = tkinter.filedialog.askopenfilename(title=title)
    finally:
        root.destroy()
    return selected or None


def choose(kind: str, title: str = "Choose a location") -> str | None:
    """Open a native folder/file picker. Returns the chosen path, or None if cancelled."""
    if kind not in PICK:
        raise DialogError(f"kind must be one of {PICK}, got {kind!r}")
    if sys.platform == "darwin":
        return _macos(kind, title)
    if sys.platform == "win32":
        return _windows(kind, title)
    return _linux(kind, title)
