import json
from pathlib import Path
from backend.app import ApiApp


def call(app, method, path, body=None, headers=None):
    raw = json.dumps(body).encode() if body is not None else b""
    status, response_headers, payload = app.handle(method, path, headers or {}, raw)
    parsed = json.loads(payload) if response_headers.get("Content-Type", "").startswith("application/json") else payload
    return status, response_headers, parsed


def test_flask_parity_routes(tmp_path):
    app = ApiApp(tmp_path)
    status, _, body = call(app, "POST", "/api/auth/setup", {"username": "admin", "password": "password-123"})
    headers = {"Cookie": "session=" + body["data"]["session"], "X-CSRF-Token": body["data"]["csrf"]}
    assert status == 201
    assert call(app, "GET", "/api/bagian", headers=headers)[0] == 200
    assert call(app, "GET", "/api/aturan", headers=headers)[0] == 200
    call(app, "POST", "/api/karyawan", {"id_karyawan":"TK001","nama":"Uji","tipe_gaji":"harian","upah_harian":100000}, headers)
    pid = call(app, "POST", "/api/periode", {"nama":"JANUARI 2026","tgl_mulai":"2026-01-01"}, headers)[2]["data"]["id_periode"]
    transfer = call(app, "POST", f"/api/transfer/{pid}", {"tanggal":"2026-01-01","nominal":1000}, headers)
    assert transfer[0] == 201
    tid = call(app, "GET", f"/api/transfer/{pid}", headers=headers)[2]["data"]["daftar"][0]["id_transfer"]
    assert call(app, "DELETE", f"/api/transfer/item/{tid}", headers=headers)[0] == 200
    deduction = call(app, "POST", f"/api/potongan/{pid}", {"id_karyawan":"TK001","nama":"Izin","nominal":1000}, headers)
    assert deduction[0] == 201
    did = call(app, "GET", f"/api/potongan/{pid}", headers=headers)[2]["data"][0]["id_potongan"]
    assert call(app, "DELETE", f"/api/potongan/item/{did}", headers=headers)[0] == 200
    loan = call(app, "POST", "/api/kasbon", {"id_karyawan":"TK001","tanggal":"2026-01-01","nominal":5000}, headers)
    assert loan[0] == 201
    kid = call(app, "GET", "/api/kasbon", headers=headers)[2]["data"][0]["id_kasbon"]
    assert call(app, "POST", f"/api/kasbon/{kid}/lunasi", {}, headers)[0] == 200
    report = call(app, "GET", f"/api/laporan/{pid}/export?jenis=konsultan", headers=headers)
    assert report[0] == 200 and report[1]["Content-Type"].startswith("application/vnd.openxmlformats")
    slip = call(app, "GET", f"/api/slip/{pid}/TK001", headers=headers)
    assert slip[0] == 200 and slip[2]["data"]["pegawai"]["id_karyawan"] == "TK001"
