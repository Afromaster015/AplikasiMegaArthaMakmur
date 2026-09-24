"""Modul kehadiran: simpan/baca kehadiran per karyawan per hari (pengganti input M1-M6)."""
import payroll.db as db

KOLOM = ["upah_hari", "tambahan_tgl_merah", "uang_makan_lembur",
         "lembur_malam", "lembur_jam"]


def parse_angka(nilai):
    """Parsing aman input angka: '1' → 1, '1.5'/'1,5' → 1.5, kosong/aneh → 0.

    Lembur boleh pecahan (step 0.5 di form), jadi tidak boleh dipaksa int().
    """
    teks = str(nilai if nilai is not None else "").strip().replace(",", ".")
    if not teks:
        return 0
    try:
        f = float(teks)
    except ValueError:
        return 0
    return int(f) if f == int(f) else f


def simpan(db_path=None, id_minggu=None, id_karyawan=None, tanggal=None, data=None):
    """Simpan (upsert) kehadiran satu karyawan satu hari."""
    data = data or {}
    conn = db.get_conn(db_path)
    try:
        ada = conn.execute(
            "SELECT id_kehadiran FROM tb_kehadiran WHERE id_minggu=? AND id_karyawan=? AND tanggal=?",
            (id_minggu, id_karyawan, tanggal)).fetchone()
        vals = {k: parse_angka(data.get(k)) for k in KOLOM}
        vals["keterangan"] = (data.get("keterangan") or "").strip()
        if ada:
            set_klausa = ", ".join(f"{k}=:{k}" for k in KOLOM + ["keterangan"])
            vals["id_kehadiran"] = ada["id_kehadiran"]
            conn.execute(
                f"UPDATE tb_kehadiran SET {set_klausa} WHERE id_kehadiran=:id_kehadiran",
                vals)
        else:
            vals.update(id_minggu=id_minggu, id_karyawan=id_karyawan, tanggal=tanggal)
            kolom = ["id_minggu", "id_karyawan", "tanggal"] + KOLOM + ["keterangan"]
            conn.execute(
                f"INSERT INTO tb_kehadiran ({','.join(kolom)}) VALUES "
                f"({','.join(':' + k for k in kolom)})", vals)
        conn.commit()
    finally:
        conn.close()


def ambil(db_path=None, id_minggu=None, id_karyawan=None, tanggal=None):
    conn = db.get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM tb_kehadiran WHERE id_minggu=? AND id_karyawan=? AND tanggal=?",
            (id_minggu, id_karyawan, tanggal)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def hari_kehadiran(db_path=None, id_minggu=None, tanggal=None):
    """Semua kehadiran pada satu tanggal di satu minggu (dict per id_karyawan)."""
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tb_kehadiran WHERE id_minggu=? AND tanggal=?",
            (id_minggu, tanggal)).fetchall()
        return {r["id_karyawan"]: dict(r) for r in rows}
    finally:
        conn.close()


def ringkasan_pegawai(db_path=None, id_periode=None, id_karyawan=None):
    """Agregasi kehadiran satu karyawan selama satu periode.

    Return dict: hari_masuk, tgl_merah, uang_makan_lembur, lembur_malam, lembur_jam.
    """
    conn = db.get_conn(db_path)
    try:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(k.upah_hari), 0)               AS hari_masuk,
                COALESCE(SUM(k.tambahan_tgl_merah), 0)      AS tgl_merah,
                COALESCE(SUM(k.uang_makan_lembur), 0)       AS uang_makan_lembur,
                COALESCE(SUM(k.lembur_malam), 0)            AS lembur_malam,
                COALESCE(SUM(k.lembur_jam), 0)              AS lembur_jam
            FROM tb_kehadiran k
            JOIN tb_minggu m ON k.id_minggu = m.id_minggu
            WHERE m.id_periode = ? AND k.id_karyawan = ?
        """, (id_periode, id_karyawan)).fetchone()
        hasil = {k: int(row[k] or 0) for k in
                 ["hari_masuk", "tgl_merah", "uang_makan_lembur", "lembur_malam"]}
        # Jam lembur boleh pecahan 0,5. Jangan mengubahnya menjadi int.
        hasil["lembur_jam"] = float(row["lembur_jam"] or 0)
        return hasil
    finally:
        conn.close()

