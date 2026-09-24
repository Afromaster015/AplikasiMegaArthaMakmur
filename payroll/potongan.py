"""Modul potongan: izin/kasbon (pengganti kolom AK-AP + HITUNG POTONGAN)."""
import payroll.db as db


def tambah(db_path=None, data=None):
    conn = db.get_conn(db_path)
    try:
        cur = conn.execute("""
            INSERT INTO tb_potongan (id_periode, id_karyawan, jenis, jumlah, keterangan)
            VALUES (:id_periode, :id_karyawan, :jenis, :jumlah, :keterangan)
        """, {
            "id_periode": int(data.get("id_periode") or 0),
            "id_karyawan": data.get("id_karyawan") or "",
            "jenis": data.get("jenis") or "lainnya",
            "jumlah": int(data.get("jumlah") or 0),
            "keterangan": data.get("keterangan") or "",
        })
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hapus(db_path=None, id_potongan=None):
    conn = db.get_conn(db_path)
    try:
        conn.execute("DELETE FROM tb_potongan WHERE id_potongan=?", (id_potongan,))
        conn.commit()
    finally:
        conn.close()


def daftar(db_path=None, id_periode=None):
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tb_potongan WHERE id_periode=? ORDER BY id_potongan",
            (id_periode,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def kasbon_tambah(db_path=None, data=None):
    conn = db.get_conn(db_path)
    try:
        cur = conn.execute("""
            INSERT INTO tb_kasbon (id_karyawan, tanggal, jenis, jumlah, status, keterangan)
            VALUES (:id_karyawan, :tanggal, :jenis, :jumlah, :status, :keterangan)
        """, {
            "id_karyawan": data.get("id_karyawan") or "",
            "tanggal": data.get("tanggal") or "",
            "jenis": data.get("jenis") or "pabrik",
            "jumlah": int(data.get("jumlah") or 0),
            "status": data.get("status") or "belum_lunas",
            "keterangan": data.get("keterangan") or "",
        })
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def kasbon_daftar(db_path=None, id_karyawan=None):
    conn = db.get_conn(db_path)
    try:
        if id_karyawan:
            rows = conn.execute(
                "SELECT * FROM tb_kasbon WHERE id_karyawan=? ORDER BY tanggal DESC",
                (id_karyawan,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tb_kasbon ORDER BY tanggal DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def kasbon_lunasi(db_path=None, id_kasbon=None):
    conn = db.get_conn(db_path)
    try:
        conn.execute("UPDATE tb_kasbon SET status='lunas' WHERE id_kasbon=?",
                     (id_kasbon,))
        conn.commit()
    finally:
        conn.close()


def kasbon_alokasi(db_path=None, data=None):
    """Alokasikan sebagian saldo kasbon ke satu periode payroll."""
    data = data or {}
    conn = db.get_conn(db_path)
    try:
        kasbon = conn.execute(
            "SELECT * FROM tb_kasbon WHERE id_kasbon=?", (data.get("id_kasbon"),)
        ).fetchone()
        if not kasbon:
            raise ValueError("Kasbon tidak ditemukan")
        jumlah = int(data.get("jumlah") or 0)
        if jumlah <= 0:
            raise ValueError("Jumlah alokasi harus lebih besar dari nol")
        row = conn.execute(
            "SELECT COALESCE(SUM(jumlah),0) AS total FROM tb_kasbon_alokasi WHERE id_kasbon=?",
            (kasbon["id_kasbon"],),
        ).fetchone()
        saldo = int(kasbon["jumlah"] or 0) - int(row["total"] or 0)
        if jumlah > saldo:
            raise ValueError(f"Alokasi melebihi saldo kasbon ({saldo:,})")
        conn.execute("""
            INSERT INTO tb_kasbon_alokasi
                (id_kasbon, id_periode, id_karyawan, jumlah, keterangan)
            VALUES (?, ?, ?, ?, ?)
        """, (kasbon["id_kasbon"], int(data["id_periode"]), kasbon["id_karyawan"],
              jumlah, data.get("keterangan") or ""))
        if jumlah == saldo:
            conn.execute("UPDATE tb_kasbon SET status='lunas' WHERE id_kasbon=?",
                         (kasbon["id_kasbon"],))
        conn.commit()
    finally:
        conn.close()

