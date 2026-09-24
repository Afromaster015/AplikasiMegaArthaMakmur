from pathlib import Path
from zipfile import ZipFile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_launcher_is_crlf_and_uses_only_portable_runtime():
    raw = (ROOT / "jalankan.bat").read_bytes()
    assert raw.startswith(b"@echo off\r\n")
    assert b"runtime\\python.exe server.py" in raw
    assert b"pip install" not in raw.lower()
    text = raw.decode("utf-8")
    labels = {line[1:].strip() for line in text.splitlines() if line.startswith(":")}
    targets = {line.split()[1].strip() for line in text.splitlines() if line.strip().lower().startswith("goto ")}
    assert targets <= labels


def test_windows_runtime_and_frontend_are_complete():
    for name in ["python.exe", "pythonw.exe", "python38.dll", "python38._pth"]:
        assert (ROOT / "runtime" / name).is_file()
    assert (ROOT / "runtime/Lib/site-packages/openpyxl/__init__.py").is_file()
    assert (ROOT / "frontend/dist/index.html").is_file()
    assert len(list((ROOT / "frontend/dist/assets").glob("Manrope-*.ttf"))) == 5


def test_release_zip_excludes_sensitive_and_build_data(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "tools/package_release.py")], check=True)
    output = ROOT.parent / "RekapGajiArtPro_Portable_v1.zip"
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
    forbidden = ["/database/", "/auth/", "/backup/", "/export/", "/node_modules/", "/tests/", "/.git/"]
    assert not any(token in name for token in forbidden for name in names)
    assert "RekapGajiArtPro/jalankan.bat" in names
    assert "RekapGajiArtPro/frontend/dist/index.html" in names
    assert "RekapGajiArtPro/runtime/python.exe" in names
