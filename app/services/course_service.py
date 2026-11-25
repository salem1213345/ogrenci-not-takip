"""Ders işlemleri (CRUD + arama)."""

import sqlite3

from app.database import Database
from app.errors import NotFoundError, ValidationError
from app.models import Course
from app.validators import CODE_RE, clean, optional_text, parse_credit, require_text

DUPLICATE_CODE = "Bu ders kodu zaten kayıtlı."


class CourseService:
    def __init__(self, db: Database):
        self.db = db

    def _validate(self, code, name, credit, instructor, semester, teacher_id=None):
        course_code = require_text(code, "Ders kodu", max_length=16).upper()
        if not CODE_RE.match(course_code):
            raise ValidationError(
                "Ders kodu 2-16 karakter olmalı; boşluk yerine - kullanın.", field="Ders kodu"
            )
        return (
            course_code,
            require_text(name, "Ders adı", max_length=100),
            parse_credit(credit),
            optional_text(instructor, "Öğretim görevlisi", max_length=80),
            optional_text(semester, "Dönem", max_length=30),
            self._teacher(teacher_id),
        )

    def _teacher(self, teacher_id) -> int | None:
        if teacher_id in (None, ""):
            return None
        row = self.db.query_one(
            "SELECT id FROM users WHERE id = ? AND role = 'teacher'", (teacher_id,)
        )
        if row is None:
            raise ValidationError("Seçilen sorumlu öğretmen bulunamadı.",
                                  field="Sorumlu öğretmen")
        return int(row["id"])

    def add(self, code, name, credit=3, instructor="", semester="", teacher_id=None) -> Course:
        values = self._validate(code, name, credit, instructor, semester, teacher_id)
        try:
            new_id = self.db.execute(
                """INSERT INTO courses (code, name, credit, instructor, semester, teacher_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                values,
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationError(DUPLICATE_CODE, field="Ders kodu") from exc
        return self.get(new_id)

    def update(self, course_id, code, name, credit=3, instructor="", semester="",
               teacher_id=None) -> Course:
        self.get(course_id)
        values = self._validate(code, name, credit, instructor, semester, teacher_id)
        try:
            self.db.run(
                """UPDATE courses
                   SET code = ?, name = ?, credit = ?, instructor = ?, semester = ?,
                       teacher_id = ?
                   WHERE id = ?""",
                values + (course_id,),
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationError(DUPLICATE_CODE, field="Ders kodu") from exc
        return self.get(course_id)

    def delete(self, course_id) -> None:
        affected = self.db.run("DELETE FROM courses WHERE id = ?", (course_id,))
        if not affected:
            raise NotFoundError("Silinecek ders bulunamadı.")

    def get(self, course_id) -> Course:
        row = self.db.query_one("SELECT * FROM courses WHERE id = ?", (course_id,))
        if row is None:
            raise NotFoundError("Ders bulunamadı.")
        return Course.from_row(row)

    def list(self, search: str = "") -> list[Course]:
        text = clean(search)
        if not text:
            rows = self.db.query("SELECT * FROM courses ORDER BY code")
        else:
            pattern = f"%{text}%"
            rows = self.db.query(
                """SELECT * FROM courses
                   WHERE code LIKE ? OR name LIKE ? OR instructor LIKE ? OR semester LIKE ?
                   ORDER BY code""",
                (pattern, pattern, pattern, pattern),
            )
        return [Course.from_row(row) for row in rows]

    def semesters(self) -> list[str]:
        rows = self.db.query(
            "SELECT DISTINCT semester FROM courses WHERE semester <> '' ORDER BY semester"
        )
        return [row["semester"] for row in rows]

    def for_teacher(self, teacher_id, semester: str = "") -> list[Course]:
        """Öğretmenin dersleri: kendisine atanmış dersler ve henüz sorumlusu olmayanlar."""
        sql = "SELECT * FROM courses WHERE (teacher_id = ? OR teacher_id IS NULL)"
        params: list = [teacher_id]
        if semester:
            sql += " AND semester = ?"
            params.append(semester)
        rows = self.db.query(sql + " ORDER BY code", tuple(params))
        return [Course.from_row(row) for row in rows]

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS total FROM courses")
        return int(row["total"]) if row else 0
