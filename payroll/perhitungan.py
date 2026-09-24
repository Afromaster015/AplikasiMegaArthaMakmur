"""Modul perhitungan: upah, uang makan, lembur, tgl merah, THR (sesuai sheet ATURAN)."""
import payroll.db as db
import payroll.kehadiran as kehadiran


def _aturan(conn, nama, default=0):
    row = conn.execute("SELECT nilai FROM tb_aturan WHERE nama=?", (nama,)).fetchone()
    return float(row["nilai"]) if row else default


def _tarif_aturan(conn, nama):
    return _aturan(conn, nama)


def hitung_pegawai(db_path=None, id_karyawan=None, id_periode=None):
    """Hitung seluruh komponen penghasilan satu pegawai dalam satu periode."""
    conn = db.get_conn(db_path)
    try:
        peg = conn.execute(
            "SELECT * FROM tb_periode_karyawan WHERE id_periode=? AND id_karyawan=?",
            (id_periode, id_karyawan)).fetchone()
        if not peg:
            peg = conn.execute(
                "SELECT * FROM tb_karyawan WHERE id_karyawan=?", (id_karyawan,)).fetchone()
        if not peg:
            return None
        ringkas = kehadiran.ringkasan_pegawai(db_path, id_periode, id_karyawan)
        bagian = (peg["kode_bagian"] or "").upper()
        tipe = peg["tipe_gaji"]
        upah_harian = int(peg["upah_harian"] or 0)
        uang_makan_hari = int(peg["uang_makan_hari"] or 0)
        gaji_bulanan = int(peg["gaji_bulanan"] or 0)

        tarif_lembur_jam = _tarif_aturan(conn, "tarif_lembur_jam")
        tarif_makan_lembur = _tarif_aturan(conn, "uang_makan_lembur")
        prop_tgl_merah = _tarif_aturan(conn, "tgl_merah_harian")
        prop_tgl_merah_bulanan = _tarif_aturan(conn, "tgl_merah_bulanan")
        pengali_malam_harian = _tarif_aturan(conn, "lembur_malam_harian")
        pengali_malam_bulanan = _tarif_aturan(conn, "lembur_malam_bulanan")

        # --- GAJI / UPAH ---
        if tipe == "bulanan":
            gaji = gaji_bulanan
            upah = 0
        else:
            gaji = 0
            upah = upah_harian * ringkas["hari_masuk"]

        # --- UANG MAKAN ---
        uang_makan = uang_makan_hari * ringkas["hari_masuk"]

        # --- TAMBAHAN TANGGAL MERAH ---
        # Finishing & Las tidak mendapat tambahan (sheet ATURAN)
        if bagian in ("FIN", "LAS"):
            tambahan_tgl_merah = 0
        elif tipe == "bulanan":
            tambahan_tgl_merah = int(prop_tgl_merah_bulanan * uang_makan_hari
                                     * ringkas["tgl_merah"])
        else:
            tambahan_tgl_merah = int(prop_tgl_merah * upah_harian
                                     * ringkas["tgl_merah"])

        # --- LEMBUR berdasarkan policy, bukan nama pegawai ---
        # Kompatibilitas data lama: sebelum policy_code tersedia, nama MUHIDIN
        # diperlakukan sebagai legacy exception. Data baru memakai policy_code.
        lembur_dikecualikan = ((peg["policy_code"] or "") == "NO_LEMBUR" or
                               ((peg["policy_code"] or "") == "" and
                                (peg["nama"] or "").upper() == "MUHIDIN"))
        if lembur_dikecualikan:
            uang_makan_lembur = 0
            lembur_malam = 0
            lembur_jam = 0
        else:
            uang_makan_lembur = int(tarif_makan_lembur * ringkas["uang_makan_lembur"])
            # lembur malam: harian = pengali aturan x upah/hari; bulanan = pengali aturan x uang makan/hari
            if tipe == "bulanan":
                lembur_malam = int(pengali_malam_bulanan * uang_makan_hari * ringkas["lembur_malam"])
            else:
                lembur_malam = int(pengali_malam_harian * upah_harian * ringkas["lembur_malam"])
            lembur_jam = int(tarif_lembur_jam * ringkas["lembur_jam"])

        # --- THR ---
        # THR TIDAK dihitung otomatis di penghasilan bulanan (dibayar berkala,
        # diisi manual lewat menu THR). Selalu 0 di perhitungan bulan ini.
        thr = 0

        # --- TOTAL ---
        total_penghasilan = (gaji + upah + uang_makan + tambahan_tgl_merah
                             + uang_makan_lembur + lembur_malam + lembur_jam + thr)

        return {
            "id_karyawan": peg["id_karyawan"],
            "nama": peg["nama"],
            "kode_bagian": peg["kode_bagian"],
            "jabatan": peg["jabatan"],
            "tipe_gaji": tipe,
            "gaji_bulanan": gaji,
            "upah_harian": upah,
            "uang_makan": uang_makan,
            "tambahan_tgl_merah": tambahan_tgl_merah,
            "uang_makan_lembur": uang_makan_lembur,
            "lembur_malam": lembur_malam,
            "lembur_jam": lembur_jam,
            "thr": thr,
            "hari_masuk": ringkas["hari_masuk"],
            "total_penghasilan": total_penghasilan,
        }
    finally:
        conn.close()

