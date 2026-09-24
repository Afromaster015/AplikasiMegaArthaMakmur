import json
from pathlib import Path

import payroll.db as db
from backend.app import ApiApp


def call(app, method, path, body=None, headers=None):
    payload = json.dumps(body).encode() if body is not None else b""
    status, out_headers, raw = app.handle(method, path, headers or {}, payload)
    return status, out_headers, json.loads(raw.decode()) if raw else None


def authenticated_app(tmp_path):
    app = ApiApp(tmp_path)
    status, _, setup = call(app, "POST", "/api/auth/setup", {"username": "admin", "password": "password-kuat"})
    assert status == 201
    cookie = setup["data"]["session"]
    csrf = setup["data"]["csrf"]
    return app, {"Cookie": f"session={cookie}", "X-CSRF-Token": csrf}


def test_health_and_setup_status(tmp_path):
    app = ApiApp(tmp_path)
    status, _, body = call(app, "GET", "/api/health")
    assert status == 200
    assert body["data"]["status"] == "ok"
    status, _, body = call(app, "GET", "/api/auth/status")
    assert body["data"] == {"configured": False, "authenticated": False, "user": None}


def test_setup_login_and_csrf(tmp_path):
    app, headers = authenticated_app(tmp_path)
    status, _, body = call(app, "GET", "/api/auth/status", headers=headers)
    assert status == 200 and body["data"]["authenticated"] is True
    status, _, body = call(app, "POST", "/api/karyawan", {"id_karyawan": "TK999", "nama": "PEGAWAI UJI", "tipe_gaji": "harian"}, {"Cookie": headers["Cookie"]})
    assert status == 403 and body["error"]["code"] == "CSRF_INVALID"
    status, _, _ = call(app, "POST", "/api/karyawan", {"id_karyawan": "TK998", "nama": "CASE HEADER", "tipe_gaji": "harian"}, {"cookie": headers["Cookie"], "X-Csrf-Token": headers["X-CSRF-Token"]})
    assert status == 201


def test_employee_and_period_crud(tmp_path):
    app, headers = authenticated_app(tmp_path)
    employee = {"id_karyawan": "TK999", "nama": "PEGAWAI UJI", "tipe_gaji": "harian", "upah_harian": 100000, "uang_makan_hari": 15000, "status_aktif": 1}
    status, _, _ = call(app, "POST", "/api/karyawan", employee, headers)
    assert status == 201
    status, _, body = call(app, "GET", "/api/karyawan", headers=headers)
    assert body["data"][0]["id_karyawan"] == "TK999"
    status, _, body = call(app, "POST", "/api/periode", {"nama": "JANUARI 2026", "tgl_mulai": "2026-01-01"}, headers)
    assert status == 201
    status, _, body = call(app, "GET", "/api/periode", headers=headers)
    assert len(body["data"]) == 1


def test_unknown_api_is_json_404(tmp_path):
    app, headers = authenticated_app(tmp_path)
    status, _, body = call(app, "GET", "/api/tidak-ada", headers=headers)
    assert status == 404
    assert body["error"]["code"] == "NOT_FOUND"


def test_backup_list_and_restore_use_safe_filename(tmp_path):
    app, headers = authenticated_app(tmp_path)
    status, _, created = call(app, "POST", "/api/backup", {}, headers)
    assert status == 201
    name = created["data"]["file"]
    status, _, listing = call(app, "GET", "/api/backup", headers=headers)
    assert listing["data"] == [{"nama": name}]
    status, _, restored = call(app, "POST", "/api/backup/restore", {"nama": name}, headers)
    assert status == 200 and restored["data"]["restored"] == name
    status, _, rejected = call(app, "POST", "/api/backup/restore", {"nama": "../gaji.db"}, headers)
    assert status == 422 and rejected["error"]["code"] == "VALIDATION_ERROR"


def test_setup_password_minimum_is_ten(tmp_path):
    app = ApiApp(tmp_path)
    assert call(app, "POST", "/api/auth/setup", {"username": "admin", "password": "123456789"})[0] == 422
    assert call(app, "POST", "/api/auth/setup", {"username": "admin", "password": "1234567890"})[0] == 201


def test_thr_calculation_is_idempotent(tmp_path):
    app, headers = authenticated_app(tmp_path)
    call(app, "POST", "/api/karyawan", {"id_karyawan": "TK001", "nama": "PEGAWAI UJI", "tipe_gaji": "harian", "upah_harian": 100000}, headers)
    pid = call(app, "POST", "/api/periode", {"nama": "JANUARI 2026", "tgl_mulai": "2026-01-01"}, headers)[2]["data"]["id_periode"]
    call(app, "POST", f"/api/thr/{pid}", {}, headers)
    call(app, "POST", f"/api/thr/{pid}", {}, headers)
    conn = db.get_conn(app.db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM tb_thr").fetchone()[0]
    finally:
        conn.close()
    assert total == 1


def test_write_actions_are_audited(tmp_path):
    app, headers = authenticated_app(tmp_path)
    call(app, "POST", "/api/karyawan", {"id_karyawan": "TK001", "nama": "PEGAWAI UJI", "tipe_gaji": "harian"}, headers)
    pid = call(app, "POST", "/api/periode", {"nama": "JANUARI 2026", "tgl_mulai": "2026-01-01"}, headers)[2]["data"]["id_periode"]
    call(app, "POST", f"/api/transfer/{pid}", {"tanggal": "2026-01-01", "bank": "BCA", "nominal": 1000}, headers)
    call(app, "PUT", "/api/karyawan/TK001", {"nama": "PEGAWAI UBAH", "tipe_gaji": "harian"}, headers)
    logs = call(app, "GET", "/api/log", headers=headers)[2]["data"]
    tabel_aksi = {(row["tabel"], row["aksi"]) for row in logs}
    assert ("tb_karyawan", "tambah") in tabel_aksi
    assert ("tb_karyawan", "ubah") in tabel_aksi
    assert ("tb_periode", "buat") in tabel_aksi
    assert ("tb_transfer", "tambah") in tabel_aksi
