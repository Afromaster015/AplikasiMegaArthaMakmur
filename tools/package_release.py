"""Buat ZIP distribusi portable tanpa data pengguna dan build tooling."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
import os

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT.parent / "RekapGajiArtPro_Portable_v1.zip"
PREFIX = "RekapGajiArtPro"
INCLUDE_FILES = ["server.py", "jalankan.bat", "CARA PAKAI.txt", "README.md", "RELEASE_NOTES.md"]
INCLUDE_DIRS = ["backend", "payroll", "frontend/dist", "runtime"]
BLOCKED_PARTS = {"__pycache__", ".pytest_cache", "node_modules", "test-results", "playwright-report", "database", "auth", "sessions", "backup", "export", "logs", ".git"}
BLOCKED_SUFFIXES = {".pyc", ".pyo", ".map", ".db", ".sqlite", ".log"}


def allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    return not any(part in BLOCKED_PARTS for part in rel.parts) and path.suffix.lower() not in BLOCKED_SUFFIXES


def files():
    for name in INCLUDE_FILES:
        path = ROOT / name
        if path.is_file(): yield path
    for name in INCLUDE_DIRS:
        base = ROOT / name
        if base.exists():
            for path in sorted(base.rglob("*")):
                if path.is_file() and allowed(path): yield path


def main():
    if OUTPUT.exists(): OUTPUT.unlink()
    selected = list(files())
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path in selected:
            archive.write(path, f"{PREFIX}/{path.relative_to(ROOT).as_posix()}")
    with ZipFile(OUTPUT) as archive:
        bad = archive.testzip()
        if bad: raise RuntimeError(f"ZIP rusak: {bad}")
        names = archive.namelist()
        forbidden = [name for name in names if any(f"/{part}/" in f"/{name}/" for part in BLOCKED_PARTS) or Path(name).suffix.lower() in BLOCKED_SUFFIXES]
        if forbidden: raise RuntimeError(f"File terlarang: {forbidden}")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"output={OUTPUT}")
    print(f"files={len(selected)}")
    print(f"bytes={OUTPUT.stat().st_size}")
    print(f"sha256={digest}")

if __name__ == "__main__": main()
