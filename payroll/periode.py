"""Modul periode: buat periode bulanan + minggu kalender otomatis (Senin-Minggu).

Minggu mengikuti kalender asli: Senin -> Minggu. Minggu pertama dimulai dari
Senin terdekat (sebelum/sama dengan tanggal mulai periode), sehingga beberapa
hari dari bulan sebelumnya bisa ikut dalam minggu 1. Hari di luar rentang
periode TIDAK bisa diinput (opsi b).
"""
from datetime import date, timedelta

import payroll.db as db

HARI_INDONESIA = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def buat_periode(db_path=None, nama=None, tgl_mulai=None):
    """Buat periode baru + minggu-minggu kalender (Senin-Minggu) yang menutup bulan.

    - nama: label periode (mis. "Mei 2026")
    - tgl_mulai: string YYYY-MM-DD (awal periode, biasanya tgl 1)
    - Minggu 1 dimulai dari Senin pada/minggu yang memuat tgl_mulai;
      minggu terakhir adalah minggu yang memuat tgl_selesai (boleh melewati
      akhir bulan, tapi hari di luar periode tidak bisa diinput).
    """
    if tgl_mulai is None:
        raise ValueError("tgl_mulai wajib diisi")
    tgl = date.fromisoformat(tgl_mulai)

    # akhir bulan: hari pertama bulan berikutnya - 1
    if tgl.month == 12:
        akhir = date(tgl.year + 1, 1, 1) - timedelta(days=1)
    else:
        akhir = date(tgl.year, tgl.month + 1, 1) - timedelta(days=1)

    conn = db.get_conn(db_path)
    try:
        # cek duplikat nama (tanpa membedakan huruf besar/kecil)
        ada = conn.execute("SELECT id_periode FROM tb_periode WHERE UPPER(bulan)=UPPER(?)",
                           (nama,)).fetchone()
        if ada:
            raise ValueError(f"Periode '{nama}' sudah ada.")
        cur = conn.execute(
            "INSERT INTO tb_periode (bulan, tgl_mulai, tgl_selesai, status) VALUES (?,?,?,?)",
            (nama, tgl.isoformat(), akhir.isoformat(), "draft"))
        pid = cur.lastrowid
        # Snapshot roster dan tarif agar histori tidak berubah saat master diedit.
        conn.execute("""
            INSERT INTO tb_periode_karyawan
                (id_periode, id_karyawan, nama, kode_bagian, jabatan, tipe_gaji,
                 gaji_bulanan, upah_harian, uang_makan_hari, policy_code)
            SELECT ?, id_karyawan, nama, kode_bagian, jabatan, tipe_gaji,
                   gaji_bulanan, upah_harian, uang_makan_hari,
                   COALESCE(policy_code, '')
            FROM tb_karyawan WHERE status_aktif=1
        """, (pid,))

        # Senin pada minggu yang memuat tgl_mulai (Senin = weekday 0)
        senin_awal = tgl - timedelta(days=tgl.weekday())

        # bangun minggu Senin-Minggu sampai minggu yang memuat akhir bulan
        mulai = senin_awal
        minggu_ke = 1
        while mulai <= akhir:
            selesai = mulai + timedelta(days=6)  # Minggu
            conn.execute(
                "INSERT INTO tb_minggu (id_periode, minggu_ke, tgl_mulai, tgl_selesai) VALUES (?,?,?,?)",
                (pid, minggu_ke, mulai.isoformat(), selesai.isoformat()))
            minggu_ke += 1
            mulai = selesai + timedelta(days=1)
        conn.commit()
        return pid
    finally:
        conn.close()


def daftar_periode(db_path=None):
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tb_periode ORDER BY tgl_mulai DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def daftar_minggu(db_path=None, id_periode=None):
    conn = db.get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tb_minggu WHERE id_periode=? ORDER BY minggu_ke",
            (id_periode,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def daftar_hari_input(db_path=None, id_minggu=None):
    """Hari yang BOLEH diinput = hari minggu yang masih dalam rentang periode.

    Hari di luar periode (mis. 27-30 April pada minggu 1 periode Mei)
    disembunyikan/tidak bisa diisi.
    """
    conn = db.get_conn(db_path)
    try:
        minggu = conn.execute(
            "SELECT * FROM tb_minggu WHERE id_minggu=?", (id_minggu,)).fetchone()
        if not minggu:
            return []
        per = conn.execute(
            "SELECT * FROM tb_periode WHERE id_periode=?",
            (minggu["id_periode"],)).fetchone()
        if not per:
            return []
        batas_awal = date.fromisoformat(per["tgl_mulai"])
        batas_akhir = date.fromisoformat(per["tgl_selesai"])
        tgl = date.fromisoformat(minggu["tgl_mulai"])
        hari = []
        for i in range(7):
            t = tgl + timedelta(days=i)
            if batas_awal <= t <= batas_akhir:
                hari.append(t.isoformat())
        return hari
    finally:
        conn.close()


def nama_hari(tanggal):
    """Nama hari Indonesia untuk tanggal (str YYYY-MM-DD atau date)."""
    if isinstance(tanggal, str):
        tanggal = date.fromisoformat(tanggal)
    return HARI_INDONESIA[tanggal.weekday()]


def ambil_periode(db_path=None, id_periode=None):
    conn = db.get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM tb_periode WHERE id_periode=?", (id_periode,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

