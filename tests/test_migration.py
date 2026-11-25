"""Şema sürüm 1 -> 2 geçişi: mevcut veriler korunmalı."""

import sqlite3

from app.database import SCHEMA, SCHEMA_VERSION, Database


def _make_v1_database(path):
    """Eski (sürüm 1) uygulamanın oluşturduğu biçimde dolu bir veritabanı."""
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO students (student_no, first_name, last_name, department, email) "
                 "VALUES ('2026001', 'Elif', 'Yılmaz', 'Bilgisayar', 'elif@okul.edu.tr')")
    conn.execute("INSERT INTO students (student_no, first_name, last_name) "
                 "VALUES ('2026002', 'Ahmet', 'Demir')")
    conn.execute("INSERT INTO courses (code, name, credit, instructor, semester) "
                 "VALUES ('BIL101', 'Programlama', 4, 'Dr. Kaya', '2026-Güz')")
    conn.execute("INSERT INTO grades (student_id, course_id, exam_type, score, weight, exam_date) "
                 "VALUES (1, 1, 'Vize', 80, 40, '2026-10-01')")
    conn.execute("INSERT INTO grades (student_id, course_id, exam_type, score, weight, exam_date) "
                 "VALUES (1, 1, 'Final', 60, 60, '2026-11-01')")
    conn.commit()
    conn.close()


def test_v1_data_survives_migration(tmp_path):
    path = tmp_path / "notlar.db"
    _make_v1_database(path)

    db = Database(path)
    try:
        assert db.schema_version == SCHEMA_VERSION
        students = db.query("SELECT * FROM students ORDER BY id")
        assert [s["student_no"] for s in students] == ["2026001", "2026002"]
        assert students[0]["email"] == "elif@okul.edu.tr"
        assert students[0]["class_year"] is None
        assert db.query_one("SELECT COUNT(*) AS n FROM grades")["n"] == 2
        course = db.query_one("SELECT * FROM courses")
        assert course["instructor"] == "Dr. Kaya" and course["teacher_id"] is None
        # Notu olan öğrenci derse kayıtlı sayılır; notu olmayan sayılmaz.
        enrollments = db.query("SELECT student_id, course_id FROM enrollments")
        assert [(e["student_id"], e["course_id"]) for e in enrollments] == [(1, 1)]
        tables = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"users", "enrollments", "messages", "message_recipients", "meta"} <= tables
    finally:
        db.close()


def test_migration_makes_backup_of_existing_file(tmp_path):
    path = tmp_path / "notlar.db"
    _make_v1_database(path)
    db = Database(path)
    db.close()
    backup = tmp_path / "notlar.v1-yedek.db"
    assert backup.is_file()
    conn = sqlite3.connect(backup)
    try:
        assert conn.execute("SELECT COUNT(*) FROM grades").fetchone()[0] == 2
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
    finally:
        conn.close()


def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "notlar.db"
    _make_v1_database(path)
    Database(path).close()
    db = Database(path)  # ikinci açılış: tekrar göç etmemeli
    try:
        assert db.schema_version == SCHEMA_VERSION
        assert db.query_one("SELECT COUNT(*) AS n FROM enrollments")["n"] == 1
    finally:
        db.close()


def test_new_database_has_no_backup(tmp_path):
    path = tmp_path / "yeni.db"
    Database(path).close()
    assert not list(tmp_path.glob("*yedek*"))


def test_meta_roundtrip(db):
    assert db.get_meta("demo") is None
    db.set_meta("demo", "1")
    db.set_meta("demo", "2")
    assert db.get_meta("demo") == "2"
