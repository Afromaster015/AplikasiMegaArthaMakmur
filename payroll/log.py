"""Modul log: audit trail sederhana."""
from datetime import datetime

import payroll.db as db


def catat(db_path=None, aksi="", tabel="", id_data="", detail=""):
    conn = db.get_conn(db_path)
    try:
        conn.execute(
            "INSERT INTO tb_log (waktu, aksi, tabel, id_data, detail) VALUES (?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), aksi, tabel, id_data, detail))
        conn.commit()
    finally:
        conn.close()


def daftar(db_path=None, limit=50):
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tb_log ORDER BY id_log DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

