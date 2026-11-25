"""Veritabanı katmanı testleri."""

from app.database import Database


def test_schema_tables_created(db):
    rows = db.query("SELECT name FROM sqlite_master WHERE type = 'table'")
    names = {row["name"] for row in rows}
    assert {"students", "courses", "grades"} <= names


def test_memory_database_works():
    with Database(":memory:") as database:
        row = database.query_one("SELECT 1 AS value")
        assert row["value"] == 1


def test_foreign_keys_enabled(db):
    assert db.query_one("PRAGMA foreign_keys")["foreign_keys"] == 1


def test_student_delete_cascades_grades(db, sample):
    db.run("DELETE FROM students WHERE id = ?", (sample.student.id,))
    assert db.query_one("SELECT COUNT(*) AS total FROM grades")["total"] == 0


def test_course_delete_cascades_grades(db, sample):
    db.run("DELETE FROM courses WHERE id = ?", (sample.course.id,))
    remaining = db.query_one("SELECT COUNT(*) AS total FROM grades")["total"]
    assert remaining == 1


def test_transaction_rolls_back_on_error(db):
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO students (student_no, first_name, last_name) VALUES (?, ?, ?)",
                ("9001", "Test", "Kişi"),
            )
            raise RuntimeError("beklenmeyen hata")
    except RuntimeError:
        pass
    assert db.query_one("SELECT COUNT(*) AS total FROM students")["total"] == 0
