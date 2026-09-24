"""Modul backup: backup & restore database gaji.db."""
import os
import re
import sqlite3
import shutil
from datetime import datetime

import payroll.db as db


def buat(db_path=None, backup_dir=None):
    """Salin database ke folder backup dengan nama ber-tanggal. Return nama file."""
    os.makedirs(backup_dir, exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
    nama = f"gaji_backup_{stempel}.db"
    tujuan = os.path.join(backup_dir, nama)
    shutil.copy2(db_path, tujuan)
    return nama


def daftar(db_path=None, backup_dir=None):
    """Daftar file backup yang ada, terbaru dulu."""
    if not os.path.isdir(backup_dir):
        return []
    files = [f for f in os.listdir(backup_dir) if f.startswith("gaji_backup_")
             and f.endswith(".db")]
    files.sort(reverse=True)
    return files


def restore(db_path=None, backup_dir=None, nama=None):
    """Kembalikan database dari file backup tertentu."""
    if not nama or not re.fullmatch(r"gaji_backup_\d{8}_\d{6}\.db", nama):
        raise ValueError("Nama backup tidak valid")
    folder = os.path.realpath(backup_dir)
    sumber = os.path.realpath(os.path.join(folder, nama))
    if os.path.dirname(sumber) != folder:
        raise ValueError("Lokasi backup tidak valid")
    if not os.path.exists(sumber):
        raise FileNotFoundError(f"Backup tidak ditemukan: {nama}")
    conn = sqlite3.connect(sumber)
    try:
        sehat = conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()
    if sehat != "ok":
        raise ValueError("Backup database tidak lolos integrity check")
    # backup kondisi sekarang dulu (pengaman), lalu salin balik
    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(db_path, f"{db_path}.sebelum_{stempel}")
    shutil.copy2(sumber, db_path)

