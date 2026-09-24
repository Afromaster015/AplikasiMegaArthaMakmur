"""Framework-free JSON API untuk aplikasi payroll lokal."""
import json
import mimetypes
import os
import re
import secrets
import time
from http import cookies
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from payroll import auth, backup, db, kehadiran, laporan, log, periode, perhitungan, potongan, rekap, thr, transfer

MAX_BODY = 2 * 1024 * 1024


def serial(value):
    if hasattr(value, "keys"):
        return {key: serial(value[key]) for key in value.keys()}
    if isinstance(value, (list, tuple)):
        return [serial(item) for item in value]
    if isinstance(value, dict):
        return {key: serial(item) for key, item in value.items()}
    return value


class ApiError(Exception):
    def __init__(self, status, code, message, fields=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or {}


class ApiApp:
    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parent.parent)
        self.data_dir = self.root / "database"
        self.auth_dir = self.root / "auth"
        self.backup_dir = self.root / "backup"
        self.export_dir = self.root / "export"
        for folder in (self.data_dir, self.auth_dir, self.backup_dir, self.export_dir):
            folder.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.data_dir / "gaji.db")
        self.auth_path = str(self.auth_dir / "admin.json")
        self.frontend = self.root / "frontend" / "dist"
        self.sessions = {}
        db.init_db(self.db_path)

    def ok(self, data=None, status=200, meta=None, headers=None):
        payload = {"ok": True, "data": serial(data)}
        if meta is not None:
            payload["meta"] = meta
        return self._json(status, payload, headers)

    def fail(self, status, code, message, fields=None):
        return self._json(status, {"ok": False, "error": {"code": code, "message": message, "fields": fields or {}}})

    def _json(self, status, payload, headers=None):
        out = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        result = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}
        result.update(headers or {})
        return status, result, out

    def _body(self, raw):
        if len(raw) > MAX_BODY:
            raise ApiError(413, "BODY_TOO_LARGE", "Ukuran data melebihi batas.")
        if not raw:
            return {}
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, "INVALID_JSON", "Format JSON tidak valid.")
        if not isinstance(value, dict):
            raise ApiError(400, "INVALID_JSON", "Request body harus berupa object JSON.")
        return value

    @staticmethod
    def _header(headers, name, default=""):
        expected = name.lower()
        return next((value for key, value in headers.items() if key.lower() == expected), default)

    def _cookies(self, headers):
        jar = cookies.SimpleCookie()
        jar.load(self._header(headers, "Cookie"))
        return {key: morsel.value for key, morsel in jar.items()}

    def _session(self, headers):
        token = self._cookies(headers).get("session", "")
        record = self.sessions.get(token)
        if not record or record["expires"] < time.time():
            self.sessions.pop(token, None)
            return None, None
        return token, record

    def _require_auth(self, headers, write=False):
        token, session = self._session(headers)
        if not session:
            raise ApiError(401, "AUTH_REQUIRED", "Silakan masuk terlebih dahulu.")
        if write and not secrets.compare_digest(self._header(headers, "X-CSRF-Token"), session["csrf"]):
            raise ApiError(403, "CSRF_INVALID", "Token keamanan tidak valid.")
        return token, session

    def _new_session(self, username):
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        self.sessions[token] = {"username": username, "csrf": csrf, "expires": time.time() + 8 * 3600}
        return token, csrf

    def _required(self, data, names):
        fields = {name: "Wajib diisi." for name in names if data.get(name) in (None, "")}
        if fields:
            raise ApiError(422, "VALIDATION_ERROR", "Periksa kembali data yang diisi.", fields)

    @staticmethod
    def _period_row(row):
        value = serial(row)
        if value and "bulan" in value:
            value["nama"] = value["bulan"]
        return value

    def _ensure_period_open(self, period_id):
        conn = db.get_conn(self.db_path)
        try:
            row = conn.execute("SELECT status FROM tb_periode WHERE id_periode=?", (period_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            raise ApiError(404, "PERIOD_NOT_FOUND", "Periode tidak ditemukan.")
        if row["status"] != "draft":
            raise ApiError(409, "PERIOD_LOCKED", "Periode sudah ditutup dan tidak dapat diubah.")

    def handle(self, method, raw_path, headers=None, raw_body=b""):
        headers = headers or {}
        parsed = urlsplit(raw_path)
        path = parsed.path.rstrip("/") or "/"
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        try:
            if path == "/api/health" and method == "GET":
                return self.ok({"status": "ok", "server": "python-stdlib", "flask": False})
            if path == "/api/auth/status" and method == "GET":
                _, session = self._session(headers)
                return self.ok({"configured": auth.load(self.auth_path) is not None, "authenticated": bool(session), "user": session["username"] if session else None})
            if path == "/api/auth/setup" and method == "POST":
                if auth.load(self.auth_path):
                    raise ApiError(409, "ALREADY_CONFIGURED", "Administrator sudah dibuat.")
                data = self._body(raw_body); self._required(data, ("username", "password"))
                if len(data["password"]) < 10:
                    raise ApiError(422, "VALIDATION_ERROR", "Password minimal 10 karakter.", {"password": "Minimal 10 karakter."})
                auth.save(self.auth_path, data["username"], data["password"])
                token, csrf = self._new_session(data["username"])
                return self.ok({"session": token, "csrf": csrf, "user": data["username"]}, 201, headers={"Set-Cookie": f"session={token}; HttpOnly; SameSite=Strict; Path=/"})
            if path == "/api/auth/login" and method == "POST":
                data = self._body(raw_body); record = auth.load(self.auth_path)
                if not record or data.get("username") != record.get("username") or not auth.verify_password(data.get("password", ""), record.get("password")):
                    raise ApiError(401, "LOGIN_FAILED", "Nama pengguna atau password salah.")
                token, csrf = self._new_session(record["username"])
                return self.ok({"session": token, "csrf": csrf, "user": record["username"]}, headers={"Set-Cookie": f"session={token}; HttpOnly; SameSite=Strict; Path=/"})
            if path == "/api/auth/logout" and method == "POST":
                token, _ = self._require_auth(headers, True); self.sessions.pop(token, None)
                return self.ok({"logged_out": True}, headers={"Set-Cookie": "session=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/"})

            if path.startswith("/api/"):
                self._require_auth(headers, method in ("POST", "PUT", "PATCH", "DELETE"))
                return self._api(method, path, query, headers, raw_body)
            if method != "GET":
                raise ApiError(405, "METHOD_NOT_ALLOWED", "Metode tidak diizinkan.")
            return self._static(parsed.path)
        except ApiError as exc:
            return self.fail(exc.status, exc.code, exc.message, exc.fields)
        except (ValueError, TypeError) as exc:
            return self.fail(422, "VALIDATION_ERROR", str(exc) or "Data tidak valid.")
        except Exception:
            return self.fail(500, "INTERNAL_ERROR", "Terjadi kesalahan lokal. Periksa log aplikasi.")

    def _api(self, method, path, query, headers, raw_body):
        data = self._body(raw_body) if method in ("POST", "PUT", "PATCH") else {}
        if path == "/api/dashboard" and method == "GET":
            employees = db.daftar_karyawan(self.db_path, True)
            periods = periode.daftar_periode(self.db_path)
            return self.ok({"karyawan_aktif": len(employees), "harian": sum(1 for x in employees if x["tipe_gaji"] == "harian"), "bulanan": sum(1 for x in employees if x["tipe_gaji"] == "bulanan"), "periode": len(periods), "periode_terakhir": self._period_row(periods[0]) if periods else None})
        if path == "/api/karyawan":
            if method == "GET": return self.ok(db.daftar_karyawan(self.db_path, query.get("aktif", "1") != "0"))
            if method == "POST":
                self._required(data, ("id_karyawan", "nama", "tipe_gaji")); db.tambah_karyawan(self.db_path, data)
                log.catat(self.db_path, "tambah", "tb_karyawan", data["id_karyawan"], "Tambah karyawan")
                return self.ok(db.ambil_karyawan(self.db_path, data["id_karyawan"]), 201)
        if path in ("/api/bagian", "/api/aturan") and method == "GET":
            table = "tb_bagian" if path.endswith("bagian") else "tb_aturan"
            order = "kode_bagian" if table == "tb_bagian" else "id_aturan"
            conn = db.get_conn(self.db_path)
            try:
                return self.ok(conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall())
            finally:
                conn.close()
        match = re.fullmatch(r"/api/karyawan/([^/]+)", path)
        if match:
            code = match.group(1)
            if method == "GET": return self.ok(db.ambil_karyawan(self.db_path, code))
            if method == "PUT":
                db.ubah_karyawan(self.db_path, code, data)
                log.catat(self.db_path, "ubah", "tb_karyawan", code, "Ubah karyawan")
                return self.ok(db.ambil_karyawan(self.db_path, code))
            if method == "DELETE":
                conn = db.get_conn(self.db_path)
                try:
                    conn.execute("UPDATE tb_karyawan SET status_aktif=0 WHERE id_karyawan=?", (code,)); conn.commit()
                finally:
                    conn.close()
                log.catat(self.db_path, "nonaktifkan", "tb_karyawan", code, "Nonaktifkan karyawan")
                return self.ok({"deactivated": True})
        if path == "/api/periode":
            if method == "GET": return self.ok([self._period_row(row) for row in periode.daftar_periode(self.db_path)])
            if method == "POST":
                self._required(data, ("nama", "tgl_mulai")); pid = periode.buat_periode(self.db_path, data["nama"], data["tgl_mulai"])
                log.catat(self.db_path, "buat", "tb_periode", pid, "Buat periode " + str(data["nama"]))
                return self.ok(self._period_row(periode.ambil_periode(self.db_path, pid)), 201)
        match = re.fullmatch(r"/api/periode/(\d+)", path)
        if match and method == "GET":
            pid = int(match.group(1)); return self.ok({"periode": self._period_row(periode.ambil_periode(self.db_path, pid)), "minggu": periode.daftar_minggu(self.db_path, pid)})
        match = re.fullmatch(r"/api/periode/(\d+)/status", path)
        if match and method == "POST":
            pid = int(match.group(1)); status = data.get("status")
            if status not in ("draft", "tutup"):
                raise ApiError(422, "VALIDATION_ERROR", "Status periode tidak valid.")
            conn = db.get_conn(self.db_path)
            try:
                cur = conn.execute("UPDATE tb_periode SET status=? WHERE id_periode=?", (status, pid)); conn.commit()
            finally:
                conn.close()
            if not cur.rowcount: raise ApiError(404, "PERIOD_NOT_FOUND", "Periode tidak ditemukan.")
            log.catat(self.db_path, "tutup" if status == "tutup" else "buka", "tb_periode", pid,
                      "Tutup periode" if status == "tutup" else "Buka kembali periode")
            return self.ok({"id_periode": pid, "status": status})
        match = re.fullmatch(r"/api/minggu/(\d+)/hari", path)
        if match and method == "GET": return self.ok(periode.daftar_hari_input(self.db_path, int(match.group(1))))
        if path == "/api/kehadiran" and method == "GET":
            mid = int(query.get("id_minggu", 0)); tanggal = query.get("tanggal", "")
            conn = db.get_conn(self.db_path)
            try:
                week = conn.execute("""SELECT m.*,p.tgl_mulai period_start,p.tgl_selesai period_end
                    FROM tb_minggu m JOIN tb_periode p ON p.id_periode=m.id_periode
                    WHERE m.id_minggu=?""", (mid,)).fetchone()
                if not week or not (week["tgl_mulai"] <= tanggal <= week["tgl_selesai"]) or not (week["period_start"] <= tanggal <= week["period_end"]):
                    raise ApiError(422, "VALIDATION_ERROR", "Tanggal tidak berada dalam rentang periode dan minggu terpilih.")
                rows = conn.execute("""SELECT s.id_karyawan,s.nama,
                    COALESCE(k.upah_hari,0) upah_hari,COALESCE(k.tambahan_tgl_merah,0) tambahan_tgl_merah,
                    COALESCE(k.uang_makan_lembur,0) uang_makan_lembur,COALESCE(k.lembur_malam,0) lembur_malam,
                    COALESCE(k.lembur_jam,0) lembur_jam,COALESCE(k.keterangan,'') keterangan
                    FROM tb_periode_karyawan s LEFT JOIN tb_kehadiran k
                    ON k.id_karyawan=s.id_karyawan AND k.id_minggu=? AND k.tanggal=?
                    WHERE s.id_periode=? ORDER BY s.nama""", (mid, tanggal, week["id_periode"])).fetchall()
                return self.ok(rows)
            finally:
                conn.close()
        if path == "/api/kehadiran/batch" and method == "POST":
            self._required(data, ("id_minggu", "tanggal", "baris"))
            conn = db.get_conn(self.db_path)
            try:
                week = conn.execute("""SELECT m.id_periode,m.tgl_mulai week_start,m.tgl_selesai week_end,
                    p.tgl_mulai period_start,p.tgl_selesai period_end FROM tb_minggu m
                    JOIN tb_periode p ON p.id_periode=m.id_periode WHERE m.id_minggu=?""", (int(data["id_minggu"]),)).fetchone()
            finally:
                conn.close()
            if not week: raise ApiError(422, "VALIDATION_ERROR", "Minggu tidak valid.")
            if not (week["week_start"] <= data["tanggal"] <= week["week_end"]) or not (week["period_start"] <= data["tanggal"] <= week["period_end"]):
                raise ApiError(422, "VALIDATION_ERROR", "Tanggal tidak berada dalam rentang periode dan minggu terpilih.")
            self._ensure_period_open(week["id_periode"])
            for row in data["baris"]:
                kehadiran.simpan(self.db_path, int(data["id_minggu"]), row["id_karyawan"], data["tanggal"], row)
            log.catat(self.db_path, "simpan", "tb_kehadiran", f"minggu {data['id_minggu']}",
                      "Simpan kehadiran " + str(data["tanggal"]) + " (" + str(len(data["baris"])) + " baris)")
            return self.ok({"saved": len(data["baris"])})
        match = re.fullmatch(r"/api/rekap/(\d+)", path)
        if match and method == "GET": return self.ok(rekap.rekap_periode(self.db_path, int(match.group(1))))
        match = re.fullmatch(r"/api/transfer/(\d+)", path)
        if match:
            pid = int(match.group(1))
            if method == "GET":
                paid = transfer.total(self.db_path, pid)
                netto = rekap.rekap_periode(self.db_path, pid)["total"]["total_bersih"]
                return self.ok({"daftar": transfer.daftar(self.db_path, pid), "total": paid, "target_netto": netto, "selisih": netto - paid, "bank": transfer.daftar_bank(self.db_path)})
            if method == "POST":
                self._ensure_period_open(pid)
                data["id_periode"] = pid; data["jumlah"] = data.get("jumlah", data.get("nominal", 0))
                tid = transfer.tambah(self.db_path, data)
                log.catat(self.db_path, "tambah", "tb_transfer", tid, "Tambah transfer " + str(data["jumlah"]))
                return self.ok({"saved": True}, 201)
        match = re.fullmatch(r"/api/transfer/item/(\d+)", path)
        if match and method == "DELETE":
            tid = int(match.group(1)); conn = db.get_conn(self.db_path)
            try:
                row = conn.execute("SELECT id_periode FROM tb_transfer WHERE id_transfer=?", (tid,)).fetchone()
            finally:
                conn.close()
            if not row: raise ApiError(404, "TRANSFER_NOT_FOUND", "Transfer tidak ditemukan.")
            self._ensure_period_open(row["id_periode"]); transfer.hapus(self.db_path, tid)
            log.catat(self.db_path, "hapus", "tb_transfer", tid, "Hapus transfer")
            return self.ok({"deleted": True})
        match = re.fullmatch(r"/api/potongan/(\d+)", path)
        if match:
            pid = int(match.group(1))
            if method == "GET": return self.ok(potongan.daftar(self.db_path, pid))
            if method == "POST":
                self._ensure_period_open(pid)
                data["id_periode"] = pid; data["jenis"] = data.get("jenis", data.get("nama", "lainnya")); data["jumlah"] = data.get("jumlah", data.get("nominal", 0))
                oid = potongan.tambah(self.db_path, data)
                log.catat(self.db_path, "tambah", "tb_potongan", oid, "Tambah potongan " + str(data["jumlah"]))
                return self.ok({"saved": True}, 201)
        match = re.fullmatch(r"/api/potongan/item/(\d+)", path)
        if match and method == "DELETE":
            item = int(match.group(1)); conn = db.get_conn(self.db_path)
            try:
                row = conn.execute("SELECT id_periode FROM tb_potongan WHERE id_potongan=?", (item,)).fetchone()
            finally:
                conn.close()
            if not row: raise ApiError(404, "DEDUCTION_NOT_FOUND", "Potongan tidak ditemukan.")
            self._ensure_period_open(row["id_periode"]); potongan.hapus(self.db_path, item)
            log.catat(self.db_path, "hapus", "tb_potongan", item, "Hapus potongan")
            return self.ok({"deleted": True})
        if path == "/api/kasbon":
            if method == "GET": return self.ok(potongan.kasbon_daftar(self.db_path, query.get("id_karyawan") or None))
            if method == "POST":
                data["jenis"] = data.get("jenis", data.get("nama", "pabrik")); data["jumlah"] = data.get("jumlah", data.get("nominal", 0))
                kid = potongan.kasbon_tambah(self.db_path, data)
                log.catat(self.db_path, "tambah", "tb_kasbon", kid, "Tambah kasbon " + str(data["jumlah"]))
                return self.ok({"saved": True}, 201)
        if path == "/api/kasbon/alokasi" and method == "POST":
            self._required(data, ("id_kasbon", "id_periode", "jumlah"))
            self._ensure_period_open(int(data["id_periode"]))
            potongan.kasbon_alokasi(self.db_path, data)
            log.catat(self.db_path, "alokasi", "tb_kasbon_alokasi", data["id_kasbon"],
                      "Alokasi kasbon " + str(data["jumlah"]) + " ke periode " + str(data["id_periode"]))
            return self.ok({"saved": True}, 201)
        match = re.fullmatch(r"/api/kasbon/(\d+)/lunasi", path)
        if match and method == "POST":
            potongan.kasbon_lunasi(self.db_path, int(match.group(1)))
            log.catat(self.db_path, "lunasi", "tb_kasbon", match.group(1), "Tandai kasbon lunas")
            return self.ok({"paid": True})
        match = re.fullmatch(r"/api/thr/(\d+)", path)
        if match:
            pid = int(match.group(1))
            if method == "GET": return self.ok(thr.ambil_map(self.db_path, pid))
            if method == "POST":
                self._ensure_period_open(pid); thr.simpan_otomatis(self.db_path, pid)
                log.catat(self.db_path, "hitung", "tb_thr", pid, "Hitung THR periode")
                return self.ok(thr.ambil_map(self.db_path, pid))
        match = re.fullmatch(r"/api/laporan/(\d+)", path)
        if match and method == "GET":
            pid = int(match.group(1)); kind = query.get("jenis", "internal")
            if kind not in ("internal", "konsultan"): raise ApiError(400, "INVALID_REPORT", "Jenis laporan tidak valid.")
            return self.ok(laporan.laporan_internal(self.db_path, pid) if kind == "internal" else laporan.laporan_konsultan(self.db_path, pid))
        match = re.fullmatch(r"/api/laporan/(\d+)/export", path)
        if match and method == "GET":
            pid = int(match.group(1)); kind = query.get("jenis", "konsultan")
            if kind not in ("internal", "konsultan"): raise ApiError(400, "INVALID_REPORT", "Jenis laporan tidak valid.")
            target = self.export_dir / f"laporan_{kind}_{pid}.xlsx"
            laporan.export_excel(self.db_path, pid, str(target), jenis=kind)
            log.catat(self.db_path, "export", "tb_laporan", pid, "Export laporan " + str(kind))
            return self._download(target, f"Laporan_{kind}_{pid}.xlsx")
        match = re.fullmatch(r"/api/slip/(\d+)", path)
        if match and method == "GET":
            pid = int(match.group(1)); return self.ok({"periode": periode.ambil_periode(self.db_path, pid), "karyawan": db.daftar_karyawan(self.db_path)})
        match = re.fullmatch(r"/api/slip/(\d+)/([^/]+)", path)
        if match and method == "GET":
            pid, code = int(match.group(1)), match.group(2)
            peg = db.ambil_karyawan(self.db_path, code)
            if not peg: raise ApiError(404, "EMPLOYEE_NOT_FOUND", "Karyawan tidak ditemukan.")
            hasil = perhitungan.hitung_pegawai(self.db_path, code, pid)
            for row in rekap.rekap_periode(self.db_path, pid)["baris"]:
                if row["id_karyawan"] == code: hasil["potongan"] = row["potongan"]
            hasil["thr"] = thr.ambil_pegawai(self.db_path, pid, code)
            return self.ok({"periode": periode.ambil_periode(self.db_path, pid), "pegawai": peg, "hasil": hasil})
        if path == "/api/backup" and method == "GET": return self.ok([{"nama": name} for name in backup.daftar(self.db_path, str(self.backup_dir))])
        if path == "/api/backup" and method == "POST":
            nama_backup = backup.buat(self.db_path, str(self.backup_dir))
            log.catat(self.db_path, "backup", "tb_backup", nama_backup, "Buat backup database")
            return self.ok({"file": nama_backup}, 201)
        if path == "/api/backup/restore" and method == "POST":
            self._required(data, ("nama",))
            backup.restore(self.db_path, str(self.backup_dir), data["nama"])
            db.init_db(self.db_path)
            log.catat(self.db_path, "restore", "tb_backup", data["nama"], "Restore database dari backup")
            return self.ok({"restored": data["nama"]})
        if path == "/api/log" and method == "GET": return self.ok(log.daftar(self.db_path, min(int(query.get("limit", 200)), 500)))
        raise ApiError(404, "NOT_FOUND", "Endpoint tidak ditemukan.")

    def _download(self, path, filename):
        candidate = Path(path).resolve()
        root = self.export_dir.resolve()
        if root not in candidate.parents or not candidate.is_file():
            raise ApiError(404, "FILE_NOT_FOUND", "File export tidak ditemukan.")
        return 200, {"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     "Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"}, candidate.read_bytes()

    def _static(self, request_path):
        relative = request_path.lstrip("/") or "index.html"
        candidate = (self.frontend / relative).resolve()
        root = self.frontend.resolve()
        if root not in candidate.parents and candidate != root:
            raise ApiError(404, "NOT_FOUND", "File tidak ditemukan.")
        if not candidate.is_file(): candidate = self.frontend / "index.html"
        if not candidate.is_file():
            return 503, {"Content-Type": "text/plain; charset=utf-8"}, b"Frontend belum dibangun."
        mime = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        cache = "no-cache" if candidate.name == "index.html" else "public, max-age=31536000, immutable"
        return 200, {"Content-Type": mime, "Cache-Control": cache}, candidate.read_bytes()
