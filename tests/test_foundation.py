from pathlib import Path
from payroll import db, kehadiran

def test_database_created_in_requested_temporary_path(tmp_path):
    target = tmp_path / "database" / "dummy.db"
    db.init_db(str(target))
    assert target.exists()
    with db.get_conn(str(target)) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

def test_fractional_overtime_parser_is_preserved():
    assert kehadiran.parse_angka("1.5") == 1.5
    assert kehadiran.parse_angka("0,5") == 0.5
