"""Modul transfer: input pembayaran aktual + hitung selisih (pengganti REKAP TRANSFER UPAH)."""
import payroll.db as db


def tambah(db_path=None, data=None):
    conn = db.get_conn(db_path)
    try:
        cur = conn.execute("""
            INSERT INTO tb_transfer (id_periode, bank, tanggal, no_referensi, jumlah, keterangan)
            VALUES (:id_periode, :bank, :tanggal, :no_referensi, :jumlah, :keterangan)
        """, {
            "id_periode": int(data.get("id_periode") or 0),
            "bank": data.get("bank") or "",
            "tanggal": data.get("tanggal") or "",
            "no_referensi": data.get("no_referensi") or "",
            "jumlah": int(data.get("jumlah") or 0),
            "keterangan": data.get("keterangan") or "",
        })
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hapus(db_path=None, id_transfer=None):
    conn = db.get_conn(db_path)
    try:
        conn.execute("DELETE FROM tb_transfer WHERE id_transfer=?", (id_transfer,))
        conn.commit()
    finally:
        conn.close()


def daftar(db_path=None, id_periode=None):
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tb_transfer WHERE id_periode=? ORDER BY tanggal",
            (id_periode,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def total(db_path=None, id_periode=None):
    conn = db.get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(jumlah),0) AS t FROM tb_transfer WHERE id_periode=?",
            (id_periode,)).fetchone()
        return int(row["t"] or 0)
    finally:
        conn.close()


def daftar_bank(db_path=None):
    """Nama bank unik dari riwayat semua periode (untuk dropdown form)."""
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT bank FROM tb_transfer "
            "WHERE bank IS NOT NULL AND bank != '' ORDER BY bank"
        ).fetchall()
        return [r["bank"] for r in rows]
    finally:
        conn.close()

