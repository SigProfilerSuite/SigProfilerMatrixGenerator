import subprocess

import pytest

from SigProfilerMatrixGenerator.web import native_dialog


class _FakeCompleted:
    def __init__(self, stdout):
        self.stdout = stdout


def test_choose_rejects_unknown_kind():
    with pytest.raises(native_dialog.DialogError):
        native_dialog.choose("city")


def test_macos_folder_dialog_uses_osascript(monkeypatch):
    monkeypatch.setattr(native_dialog.sys, "platform", "darwin")
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return _FakeCompleted("/Users/mishugeb/data\n")

    monkeypatch.setattr(native_dialog.subprocess, "run", fake_run)

    result = native_dialog.choose("folder", title="Pick input")

    assert result == "/Users/mishugeb/data"
    assert captured["args"][0] == "osascript"
    assert "choose folder" in captured["args"][2]
    assert "Pick input" in captured["args"][2]


def test_macos_file_dialog_uses_choose_file(monkeypatch):
    monkeypatch.setattr(native_dialog.sys, "platform", "darwin")
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return _FakeCompleted("/Users/mishugeb/data.vcf\n")

    monkeypatch.setattr(native_dialog.subprocess, "run", fake_run)

    result = native_dialog.choose("file", title="Pick a VCF")

    assert result == "/Users/mishugeb/data.vcf"
    assert "choose file" in captured["args"][2]


def test_cancelled_dialog_returns_none(monkeypatch):
    monkeypatch.setattr(native_dialog.sys, "platform", "darwin")
    monkeypatch.setattr(
        native_dialog.subprocess, "run", lambda args, **kwargs: _FakeCompleted("")
    )

    assert native_dialog.choose("folder") is None


def test_windows_folder_dialog_uses_powershell(monkeypatch):
    monkeypatch.setattr(native_dialog.sys, "platform", "win32")
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return _FakeCompleted("C:\\data\n")

    monkeypatch.setattr(native_dialog.subprocess, "run", fake_run)

    result = native_dialog.choose("folder", title="Pick input")

    assert result == "C:\\data"
    assert captured["args"][0] == "powershell"
    assert "FolderBrowserDialog" in captured["args"][-1]


def test_subprocess_failure_raises_dialog_error(monkeypatch):
    monkeypatch.setattr(native_dialog.sys, "platform", "darwin")

    def fake_run(args, **kwargs):
        raise OSError("osascript not found")

    monkeypatch.setattr(native_dialog.subprocess, "run", fake_run)

    with pytest.raises(native_dialog.DialogError):
        native_dialog.choose("folder")


def test_linux_prefers_zenity_when_available(monkeypatch):
    monkeypatch.setattr(native_dialog.sys, "platform", "linux")
    monkeypatch.setattr(native_dialog.shutil, "which", lambda name: "/usr/bin/zenity" if name == "zenity" else None)
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return _FakeCompleted("/home/user/data\n")

    monkeypatch.setattr(native_dialog.subprocess, "run", fake_run)

    result = native_dialog.choose("folder", title="Pick input")

    assert result == "/home/user/data"
    assert captured["args"][0] == "zenity"
    assert "--directory" in captured["args"]


def test_linux_falls_back_to_kdialog_when_zenity_absent(monkeypatch):
    monkeypatch.setattr(native_dialog.sys, "platform", "linux")
    monkeypatch.setattr(
        native_dialog.shutil, "which", lambda name: "/usr/bin/kdialog" if name == "kdialog" else None
    )
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return _FakeCompleted("/home/user/data\n")

    monkeypatch.setattr(native_dialog.subprocess, "run", fake_run)

    result = native_dialog.choose("folder")

    assert result == "/home/user/data"
    assert captured["args"][0] == "kdialog"
