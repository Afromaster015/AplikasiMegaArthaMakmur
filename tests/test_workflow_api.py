import json
from backend.app import ApiApp


def call(app, method, path, body=None, headers=None):
    raw = json.dumps(body).encode() if body is not None else b""
    status, response_headers, payload = app.handle(method, path, headers or {}, raw)
    return status, response_headers, json.loads(payload.decode())


def session(tmp_path):
    app = ApiApp(tmp_path)
    status, headers, body = call(app, "POST", "/api/auth/setup", {"username": "admin", "password": "password-kuat"})
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    return app, {"Cookie": cookie, "X-CSRF-Token": body["data"]["csrf"]}


def test_vertical_payroll_workflow(tmp_path):
    app, headers = session(tmp_path)
    employee = {"id_karyawan": "TK001", "nama": "Karyawan Uji", "tipe_gaji": "harian", "kode_bagian": "PRO", "policy_code": "", "upah_harian": 100000, "uang_makan_hari": 15000}
    assert call(app, "POST", "/api/karyawan", employee, headers)[0] == 201

    status, _, created = call(app, "POST", "/api/periode", {"nama": "JANUARI 2026", "tgl_mulai": "2026-01-01"}, headers)
    assert status == 201 and created["data"]["nama"] == "JANUARI 2026"
    pid = created["data"]["id_periode"]
    detail = call(app, "GET", f"/api/periode/{pid}", headers=headers)[2]["data"]
    week = detail["minggu"][0]
    date = max("2026-01-01", week["tgl_mulai"])

    if week["tgl_mulai"] < "2026-01-01":
        outside = call(app, "GET", f"/api/kehadiran?id_minggu={week['id_minggu']}&tanggal={week['tgl_mulai']}", headers=headers)
        assert outside[0] == 422

    status, _, attendance = call(app, "GET", f"/api/kehadiran?id_minggu={week['id_minggu']}&tanggal={date}", headers=headers)
    assert status == 200 and attendance["data"][0]["id_karyawan"] == "TK001"
    row = attendance["data"][0]
    row.update({"upah_hari": 1, "lembur_jam": 1.5})
    status, _, _ = call(app, "POST", "/api/kehadiran/batch", {"id_minggu": week["id_minggu"], "tanggal": date, "baris": [row]}, headers)
    assert status == 200

    assert call(app, "POST", f"/api/potongan/{pid}", {"id_karyawan": "TK001", "nama": "izin", "nominal": 5000}, headers)[0] == 201
    assert call(app, "POST", f"/api/transfer/{pid}", {"tanggal": date, "bank": "BCA", "nominal": 100000}, headers)[0] == 201
    assert call(app, "POST", "/api/kasbon", {"id_karyawan": "TK001", "tanggal": date, "nama": "pabrik", "nominal": 50000}, headers)[0] == 201
    kasbon = call(app, "GET", "/api/kasbon", headers=headers)[2]["data"][0]
    assert call(app, "POST", "/api/kasbon/alokasi", {"id_kasbon": kasbon["id_kasbon"], "id_periode": pid, "jumlah": 10000}, headers)[0] == 201

    rekap = call(app, "GET", f"/api/rekap/{pid}", headers=headers)[2]["data"]
    assert rekap["baris"] and rekap["baris"][0]["id_karyawan"] == "TK001"
    assert rekap["baris"][0]["lembur_jam"] == 30000
    reconciliation = call(app, "GET", f"/api/transfer/{pid}", headers=headers)[2]["data"]
    assert reconciliation["target_netto"] == rekap["total"]["total_bersih"]
    assert reconciliation["selisih"] == reconciliation["target_netto"] - 100000
    assert call(app, "POST", f"/api/periode/{pid}/status", {"status": "tutup"}, headers)[0] == 200
    locked = call(app, "POST", f"/api/transfer/{pid}", {"tanggal": date, "nominal": 1}, headers)
    assert locked[0] == 409 and locked[2]["error"]["code"] == "PERIOD_LOCKED"
    assert call(app, "POST", f"/api/periode/{pid}/status", {"status": "draft"}, headers)[0] == 200

    assert call(app, "DELETE", "/api/karyawan/TK001", headers=headers)[0] == 200
    active = call(app, "GET", "/api/karyawan", headers=headers)[2]["data"]
    assert not active
    all_employees = call(app, "GET", "/api/karyawan?aktif=0", headers=headers)[2]["data"]
    assert all_employees[0]["id_karyawan"] == "TK001"
