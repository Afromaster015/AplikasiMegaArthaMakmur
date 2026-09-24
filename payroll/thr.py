"""Modul THR: perhitungan THR sesuai aturan (pengganti sheet THR)."""
import payroll.db as db
import payroll.kehadiran as kehadiran


def hitung_pegawai(db_path=None, id_karyawan=None, id_periode=None):
    """THR per pegawai:
    - Harian : (hari masuk / 312) x (26 x upah harian)
    - Bulanan: 1 x gaji bulanan
    """
    conn = db.get_conn(db_path)
    try:
        peg = conn.execute(
            "SELECT * FROM tb_karyawan WHERE id_karyawan=?", (id_karyawan,)).fetchone()
        if not peg:
            return 0
        ringkas = kehadiran.ringkasan_pegawai(db_path, id_periode, id_karyawan)
        pembagi = _aturan_int(conn, "thr_harian_pembagi", 312)
        pengali = _aturan_int(conn, "thr_harian_pengali", 26)
        if peg["tipe_gaji"] == "bulanan":
            return int(peg["gaji_bulanan"] or 0)
        if pembagi <= 0:
            return 0
        return int((ringkas["hari_masuk"] / pembagi) * (pengali * int(peg["upah_harian"] or 0)))
    finally:
        conn.close()


def _aturan_int(conn, nama, default):
    row = conn.execute("SELECT nilai FROM tb_aturan WHERE nama=?", (nama,)).fetchone()
    return int(row["nilai"]) if row else default


def ambil_pegawai(db_path=None, id_periode=None, id_karyawan=None):
    conn = db.get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM tb_thr WHERE id_periode=? AND id_karyawan=?",
            (id_periode, id_karyawan)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def ambil_map(db_path=None, id_periode=None):
    """Map id_karyawan -> jumlah THR untuk periode."""
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id_karyawan, jumlah FROM tb_thr WHERE id_periode=?",
            (id_periode,)).fetchall()
        return {r["id_karyawan"]: int(r["jumlah"] or 0) for r in rows}
    finally:
        conn.close()


def simpan_otomatis(db_path=None, id_periode=None):
    """Hitung & simpan THR semua pegawai aktif untuk periode."""
    conn = db.get_conn(db_path)
    try:
        pegawai = conn.execute(
            "SELECT id_karyawan FROM tb_karyawan WHERE status_aktif=1").fetchall()
    finally:
        conn.close()
    for peg in pegawai:
        jumlah = hitung_pegawai(db_path, peg["id_karyawan"], id_periode)
        conn = db.get_conn(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO tb_thr (id_periode, id_karyawan, hari_masuk, jumlah) "
                "SELECT ?, id_karyawan, "
                "(SELECT COALESCE(SUM(k.upah_hari),0) FROM tb_kehadiran k "
                " JOIN tb_minggu m ON k.id_minggu=m.id_minggu "
                " WHERE m.id_periode=? AND k.id_karyawan=tb_karyawan.id_karyawan), ? "
                "FROM tb_karyawan WHERE id_karyawan=?",
                (id_periode, id_periode, jumlah, peg["id_karyawan"]))
            conn.commit()
        finally:
            conn.close()

