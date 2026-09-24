"""Modul rekap: agregasi penghasilan semua pegawai dalam satu periode."""
import payroll.db as db
import payroll.perhitungan as perhitungan


def rekap_periode(db_path=None, id_periode=None):
    """Rekap semua pegawai aktif dalam periode. Return dict {baris, total}.

    - baris: list hasil hitung_pegawai per karyawan aktif
    - total: {penghasilan, gaji, upah, uang_makan, lembur, potongan}
    """
    conn = db.get_conn(db_path)
    try:
        pegawai = conn.execute(
            "SELECT k.* FROM tb_periode_karyawan s "
            "JOIN tb_karyawan k ON k.id_karyawan=s.id_karyawan "
            "WHERE s.id_periode=? ORDER BY s.id_karyawan", (id_periode,)
        ).fetchall()
        if not pegawai:
            pegawai = conn.execute(
                "SELECT * FROM tb_karyawan WHERE status_aktif=1 ORDER BY id_karyawan"
            ).fetchall()
    finally:
        conn.close()

    baris = []
    for peg in pegawai:
        hasil = perhitungan.hitung_pegawai(db_path, peg["id_karyawan"], id_periode)
        if hasil:
            baris.append(hasil)

    # potongan (izin + kasbon) per periode
    conn = db.get_conn(db_path)
    try:
        potongan_rows = conn.execute("""
            SELECT id_karyawan, SUM(jumlah) AS total
            FROM tb_potongan WHERE id_periode=? GROUP BY id_karyawan
        """, (id_periode,)).fetchall()
        potongan_map = {r["id_karyawan"]: int(r["total"] or 0) for r in potongan_rows}

        kasbon_rows = conn.execute("""
            SELECT k.id_karyawan, SUM(k.jumlah) AS total
            FROM tb_kasbon k JOIN tb_periode p
              ON date(k.tanggal) BETWEEN date(p.tgl_mulai) AND date(p.tgl_selesai)
            LEFT JOIN tb_kasbon_alokasi a ON a.id_kasbon=k.id_kasbon
            WHERE k.status='belum_lunas' AND p.id_periode=? AND a.id_alokasi IS NULL
            GROUP BY k.id_karyawan
        """, (id_periode,)).fetchall()
        allocated_rows = conn.execute("""
            SELECT id_karyawan, SUM(jumlah) AS total
            FROM tb_kasbon_alokasi WHERE id_periode=? GROUP BY id_karyawan
        """, (id_periode,)).fetchall()
        kasbon_map = {r["id_karyawan"]: int(r["total"] or 0) for r in kasbon_rows}
        for row in allocated_rows:
            kasbon_map[row["id_karyawan"]] = kasbon_map.get(row["id_karyawan"], 0) + int(row["total"] or 0)
    finally:
        conn.close()

    total = {"penghasilan": 0, "gaji": 0, "upah": 0, "uang_makan": 0,
             "lembur": 0, "potongan": 0}
    for b in baris:
        potongan = potongan_map.get(b["id_karyawan"], 0) + kasbon_map.get(b["id_karyawan"], 0)
        b["potongan"] = potongan
        b["total_bersih"] = b["total_penghasilan"] - potongan
        total["penghasilan"] += b["total_penghasilan"]
        total["gaji"] += b["gaji_bulanan"]
        total["upah"] += b["upah_harian"]
        total["uang_makan"] += b["uang_makan"]
        total["lembur"] += (b["uang_makan_lembur"] + b["lembur_malam"] + b["lembur_jam"])
        total["potongan"] += potongan
    total["total_bersih"] = total["penghasilan"] - total["potongan"]

    return {"baris": baris, "total": total}

