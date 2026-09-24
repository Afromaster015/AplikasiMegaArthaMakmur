"""Autentikasi lokal untuk aplikasi payroll.

Kredensial disimpan sebagai hash PBKDF2-HMAC-SHA256 dalam file lokal
terpisah dari source code. Tidak ada password plaintext yang disimpan.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets


ITERATIONS = 310_000


def hash_password(password, salt=None):
    if not password:
        raise ValueError("Password tidak boleh kosong")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS
    )
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "digest": base64.b64encode(digest).decode("ascii"),
    }


def verify_password(password, record):
    if not password or not record:
        return False
    try:
        salt = base64.b64decode(record["salt"])
        expected = base64.b64decode(record["digest"])
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt,
            int(record.get("iterations", ITERATIONS)),
        )
        return hmac.compare_digest(actual, expected)
    except (KeyError, TypeError, ValueError):
        return False


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save(path, username, password):
    record = {"username": username, "password": hash_password(password)}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return record

