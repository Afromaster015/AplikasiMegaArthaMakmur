import json
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

BASE = "http://127.0.0.1:8765"
jar = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def request(path, method="GET", body=None, csrf=""):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if csrf: headers["X-CSRF-Token"] = csrf
    response = opener.open(urllib.request.Request(BASE + path, data=data, headers=headers, method=method), timeout=10)
    return response.status, response.headers, json.loads(response.read())


status, _, health = request("/api/health")
assert status == 200 and health["data"]["flask"] is False
status, headers, setup = request("/api/auth/setup", "POST", {"username": "admin-smoke", "password": "password-smoke"})
assert status == 201 and "HttpOnly" in headers.get("Set-Cookie", "")
csrf = setup["data"]["csrf"]
status, _, employee = request("/api/karyawan", "POST", {"id_karyawan":"TK999","nama":"DUMMY SMOKE","tipe_gaji":"harian","upah_harian":100000,"uang_makan_hari":15000,"status_aktif":1}, csrf)
assert status == 201
status, _, period = request("/api/periode", "POST", {"nama":"SMOKE 2026","tgl_mulai":"2026-01-01"}, csrf)
assert status == 201
status, _, dashboard = request("/api/dashboard")
assert dashboard["data"]["karyawan_aktif"] == 1
index = opener.open(BASE + "/", timeout=10).read().decode()
assert '<div id="app"></div>' in index
print("http_smoke_ok")
