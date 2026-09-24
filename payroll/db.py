"""Modul database: koneksi SQLite, skema, seed aturan, dan CRUD karyawan."""
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS tb_karyawan (
    id_karyawan     TEXT PRIMARY KEY,
    nama            TEXT NOT NULL,
    ptkp            TEXT DEFAULT '',
    kode_bagian     TEXT DEFAULT '',
    jabatan         TEXT DEFAULT '',
    tgl_awal_kerja  TEXT DEFAULT '',
    tgl_akhir_kerja TEXT DEFAULT '',
    tipe_gaji       TEXT NOT NULL DEFAULT 'harian',
    gaji_bulanan    INTEGER DEFAULT 0,
    upah_harian     INTEGER DEFAULT 0,
    uang_makan_hari INTEGER DEFAULT 0,
    status_aktif    INTEGER DEFAULT 1,
    catatan         TEXT DEFAULT '',
    policy_code     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_bagian (
    kode_bagian TEXT PRIMARY KEY,
    nama_bagian TEXT NOT NULL,
    kategori    TEXT DEFAULT 'produksi'
);

CREATE TABLE IF NOT EXISTS tb_aturan (
    id_aturan  INTEGER PRIMARY KEY AUTOINCREMENT,
    nama       TEXT NOT NULL UNIQUE,
    nilai      REAL DEFAULT 0,
    deskripsi  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_periode (
    id_periode  INTEGER PRIMARY KEY AUTOINCREMENT,
    bulan       TEXT NOT NULL,
    tgl_mulai   TEXT DEFAULT '',
    tgl_selesai TEXT DEFAULT '',
    status      TEXT DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS tb_minggu (
    id_minggu   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_periode  INTEGER NOT NULL,
    minggu_ke   INTEGER DEFAULT 1,
    tgl_mulai   TEXT DEFAULT '',
    tgl_selesai TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_kehadiran (
    id_kehadiran        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_minggu           INTEGER NOT NULL,
    id_karyawan         TEXT NOT NULL,
    tanggal             TEXT DEFAULT '',
    upah_hari           INTEGER DEFAULT 0,
    tambahan_tgl_merah  INTEGER DEFAULT 0,
    uang_makan_lembur   INTEGER DEFAULT 0,
    lembur_malam        INTEGER DEFAULT 0,
    lembur_jam          REAL DEFAULT 0,
    keterangan          TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_lembur_detail (
    id_detail   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_kehadiran INTEGER NOT NULL,
    keterangan  TEXT DEFAULT '',
    lokasi      TEXT DEFAULT '',
    project     TEXT DEFAULT '',
    jam_lembur  REAL DEFAULT 0,
    jumlah      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tb_potongan (
    id_potongan INTEGER PRIMARY KEY AUTOINCREMENT,
    id_periode  INTEGER NOT NULL,
    id_karyawan TEXT NOT NULL,
    jenis       TEXT DEFAULT 'lainnya',
    jumlah      INTEGER DEFAULT 0,
    keterangan  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_kasbon (
    id_kasbon   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_karyawan TEXT NOT NULL,
    tanggal     TEXT DEFAULT '',
    jenis       TEXT DEFAULT 'pabrik',
    jumlah      INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'belum_lunas',
    keterangan  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_kasbon_alokasi (
    id_alokasi  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_kasbon   INTEGER NOT NULL,
    id_periode  INTEGER NOT NULL,
    id_karyawan TEXT NOT NULL,
    jumlah      INTEGER NOT NULL CHECK (jumlah >= 0),
    keterangan  TEXT DEFAULT '',
    UNIQUE (id_kasbon, id_periode)
);

CREATE TABLE IF NOT EXISTS tb_periode_karyawan (
    id_snapshot     INTEGER PRIMARY KEY AUTOINCREMENT,
    id_periode      INTEGER NOT NULL,
    id_karyawan     TEXT NOT NULL,
    nama            TEXT NOT NULL,
    kode_bagian     TEXT DEFAULT '',
    jabatan         TEXT DEFAULT '',
    tipe_gaji       TEXT NOT NULL,
    gaji_bulanan    INTEGER DEFAULT 0,
    upah_harian     INTEGER DEFAULT 0,
    uang_makan_hari INTEGER DEFAULT 0,
    policy_code     TEXT DEFAULT '',
    UNIQUE (id_periode, id_karyawan)
);

CREATE TABLE IF NOT EXISTS tb_transfer (
    id_transfer  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_periode   INTEGER NOT NULL,
    bank         TEXT DEFAULT '',
    tanggal      TEXT DEFAULT '',
    no_referensi TEXT DEFAULT '',
    jumlah       INTEGER DEFAULT 0,
    keterangan   TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_thr (
    id_thr      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_periode  INTEGER NOT NULL,
    id_karyawan TEXT NOT NULL,
    hari_masuk  INTEGER DEFAULT 0,
    jumlah      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tb_kenaikan (
    id_kenaikan   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_karyawan   TEXT NOT NULL,
    berlaku_sejak TEXT DEFAULT '',
    jenis         TEXT DEFAULT 'gaji_pokok',
    nilai_lama    INTEGER DEFAULT 0,
    nilai_baru    INTEGER DEFAULT 0,
    keterangan    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tb_log (
    id_log  INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu   TEXT DEFAULT '',
    aksi    TEXT DEFAULT '',
    tabel   TEXT DEFAULT '',
    id_data TEXT DEFAULT '',
    detail  TEXT DEFAULT ''
);
"""

# Aturan default (diambil dari sheet ATURAN file Excel MAY 2026)
ATURAN_DEFAULT = [
    ("jam_kerja_normal", 8.5, "Jam kerja normal per hari (08.00-16.30)"),
    ("uang_makan_lembur", 10000, "Uang makan lembur kerja di atas pukul 18.00"),
    ("tarif_lembur_jam", 20000, "Lembur per jam di atas pukul 22.00"),
    ("lembur_malam_harian", 1, "Lembur malam 18.30-22.00: 1x upah harian"),
    ("lembur_malam_bulanan", 1, "Lembur malam 18.30-22.00: 1x uang makan/hari"),
    ("tgl_merah_harian", 0.5, "Tambahan tgl merah: 1/2 x upah harian"),
    ("tgl_merah_bulanan", 0.5, "Tambahan tgl merah: 1/2 x uang makan/hari"),
    ("thr_harian_pembagi", 312, "THR harian: (hari masuk/312) x (26 x upah harian)"),
    ("thr_harian_pengali", 26, "THR harian: pengali hari upah"),
    ("batas_jam_makan_lembur", 18.0, "Batas jam untuk uang makan lembur"),
    ("batas_jam_lembur_malam", 22.0, "Batas jam lembur malam"),
]

BAGIAN_DEFAULT = [
    ("PRO", "Produksi", "produksi"),
    ("FIN", "Finishing", "finishing"),
    ("LAS", "Besi/Las", "las"),
    ("KTR", "Kantor", "kantor"),
    ("KUS", "Produksi Kusen", "produksi"),
    ("OPR", "Operator", "produksi"),
]


def get_conn(db_path=None):
    """Buka koneksi SQLite (row_factory=sqlite3.Row)."""
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "database", "gaji.db")
    # Pastikan folder database ada (dibuat otomatis jika belum)
    folder = os.path.dirname(os.path.abspath(db_path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path=None):
    """Buat tabel + seed aturan & bagian (idempotent)."""
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    # Migrasi privasi: hapus kolom nik & alamat dari tabel lama bila masih ada
    _migrasi_hapus_kolom_privat(conn)
    _migrasi_tambah_kolom_policy(conn)
    _migrasi_thr_unik(conn)
    for nama, nilai, deskripsi in ATURAN_DEFAULT:
        conn.execute(
            "INSERT OR IGNORE INTO tb_aturan (nama, nilai, deskripsi) VALUES (?, ?, ?)",
            (nama, nilai, deskripsi))
    for kode, nama, kategori in BAGIAN_DEFAULT:
        conn.execute(
            "INSERT OR IGNORE INTO tb_bagian (kode_bagian, nama_bagian, kategori) VALUES (?, ?, ?)",
            (kode, nama, kategori))
    conn.commit()
    conn.close()


def _migrasi_tambah_kolom_policy(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tb_karyawan)").fetchall()}
    if "policy_code" not in cols:
        conn.execute("ALTER TABLE tb_karyawan ADD COLUMN policy_code TEXT DEFAULT ''")


def _migrasi_thr_unik(conn):
    """Satu baris THR per (periode, karyawan): buang duplikat lalu pasang unique index.

    Tanpa ini, INSERT OR REPLACE di thr.simpan_otomatis selalu menambah baris baru
    sehingga tombol "Hitung THR" berulang kali menumpuk data.
    """
    conn.execute(
        "DELETE FROM tb_thr WHERE id_thr NOT IN ("
        "SELECT MAX(id_thr) FROM tb_thr GROUP BY id_periode, id_karyawan)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_thr_periode_karyawan "
        "ON tb_thr (id_periode, id_karyawan)")


def _migrasi_hapus_kolom_privat(conn):
    """Buang kolom 'nik' & 'alamat' dari tabel yang sudah ada (privasi pengguna)."""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tb_karyawan)").fetchall()}
    except Exception:
        return
    for kolom in ("nik", "alamat"):
        if kolom in cols:
            try:
                conn.execute(f"ALTER TABLE tb_karyawan DROP COLUMN {kolom}")
            except Exception:
                pass  # SQLite terlalu lama → recreate (fallback di bawah)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tb_karyawan)").fetchall()}
    if "nik" in cols or "alamat" in cols:
        _recreate_tabel_tanpa_kolom_privat(conn, cols)


def _recreate_tabel_tanpa_kolom_privat(conn, cols_sekarang):
    """Fallback untuk SQLite tua: rebuild tabel tanpa kolom nik/alamat (12-step)."""
    keep = [c for c in cols_sekarang if c not in ("nik", "alamat")]
    conn.execute("ALTER TABLE tb_karyawan RENAME TO tb_karyawan_lama")
    conn.execute("DROP TABLE IF EXISTS tb_karyawan")
    conn.executescript(SCHEMA)  # tabel baru dengan skema bersih (tanpa nik/alamat)
    col_list = ", ".join(keep)
    conn.execute(
        f"INSERT INTO tb_karyawan ({col_list}) SELECT {col_list} FROM tb_karyawan_lama")
    conn.execute("DROP TABLE tb_karyawan_lama")


# ---------- CRUD KARYAWAN ----------

def _normalize(data):
    """Pastikan semua kolom ada dengan nilai default."""
    cols = ["id_karyawan", "nama", "ptkp", "kode_bagian", "jabatan",
            "tgl_awal_kerja", "tgl_akhir_kerja", "tipe_gaji", "gaji_bulanan",
            "upah_harian", "uang_makan_hari", "status_aktif", "catatan", "policy_code"]
    out = {c: data.get(c, "") for c in cols}
    out["tipe_gaji"] = out["tipe_gaji"] or "harian"
    out["status_aktif"] = 1 if data.get("status_aktif", 1) in (1, "1", True) else 0
    out["gaji_bulanan"] = int(out["gaji_bulanan"] or 0)
    out["upah_harian"] = int(out["upah_harian"] or 0)
    out["uang_makan_hari"] = int(out["uang_makan_hari"] or 0)
    return out


def tambah_karyawan(db_path=None, data=None):
    data = _normalize(data or {})
    conn = get_conn(db_path)
    try:
        conn.execute("""
            INSERT INTO tb_karyawan (id_karyawan, nama, ptkp, kode_bagian,
                jabatan, tgl_awal_kerja, tgl_akhir_kerja, tipe_gaji, gaji_bulanan,
                upah_harian, uang_makan_hari, status_aktif, catatan, policy_code)
            VALUES (:id_karyawan, :nama, :ptkp, :kode_bagian,
                :jabatan, :tgl_awal_kerja, :tgl_akhir_kerja, :tipe_gaji, :gaji_bulanan,
                :upah_harian, :uang_makan_hari, :status_aktif, :catatan, :policy_code)
        """, data)
        conn.commit()
    finally:
        conn.close()


def ubah_karyawan(db_path=None, id_karyawan=None, data=None):
    data = _normalize(data or {})
    data["id_karyawan"] = id_karyawan
    conn = get_conn(db_path)
    try:
        conn.execute("""
            UPDATE tb_karyawan SET nama=:nama, ptkp=:ptkp,
                kode_bagian=:kode_bagian, jabatan=:jabatan, tgl_awal_kerja=:tgl_awal_kerja,
                tgl_akhir_kerja=:tgl_akhir_kerja, tipe_gaji=:tipe_gaji,
                gaji_bulanan=:gaji_bulanan, upah_harian=:upah_harian,
                uang_makan_hari=:uang_makan_hari, status_aktif=:status_aktif,
                catatan=:catatan, policy_code=:policy_code
            WHERE id_karyawan=:id_karyawan
        """, data)
        conn.commit()
    finally:
        conn.close()


def daftar_karyawan(db_path=None, hanya_aktif=True):
    conn = get_conn(db_path)
    try:
        if hanya_aktif:
            rows = conn.execute(
                "SELECT * FROM tb_karyawan WHERE status_aktif=1 ORDER BY id_karyawan"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tb_karyawan ORDER BY id_karyawan").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def ambil_karyawan(db_path=None, id_karyawan=None):
    conn = get_conn(db_path)
    try:
        row = conn.execute("SELECT * FROM tb_karyawan WHERE id_karyawan=?",
                           (id_karyawan,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

