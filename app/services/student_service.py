"""Öğrenci işlemleri (CRUD + arama)."""

from __future__ import annotations

import re
import sqlite3

from app.database import Database
from app.errors import NotFoundError, ValidationError
from app.models import Student
from app.validators import (
    clean,
    optional_text,
    parse_class_year,
    require_text,
    validate_email,
)

STUDENT_NO_RE = r"^[0-9A-Za-z_-]{3,20}$"
DUPLICATE_NO = "Bu öğrenci numarası zaten kayıtlı."


class StudentService:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------ ortak
    def _validate(self, student_no, first_name, last_name, department, email,
                  class_year=None):
        number = require_text(student_no, "Öğrenci numarası", max_length=20)
        if not re.match(STUDENT_NO_RE, number):
            raise ValidationError(
                "Öğrenci numarası 3-20 karakter olmalı; harf, rakam, - ve _ içerebilir.",
                field="Öğrenci numarası",
            )
        return (
            number,
            require_text(first_name, "Ad", max_length=50),
            require_text(last_name, "Soyad", max_length=50),
            optional_text(department, "Bölüm", max_length=80),
            validate_email(email),
            parse_class_year(class_year),
        )

    # ------------------------------------------------------------------- CRUD
    def add(self, student_no, first_name, last_name, department="", email="",
            class_year=None) -> Student:
        values = self._validate(student_no, first_name, last_name, department, email,
                                class_year)
        try:
            new_id = self.db.execute(
                """INSERT INTO students
                   (student_no, first_name, last_name, department, email, class_year)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                values,
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationError(DUPLICATE_NO, field="Öğrenci numarası") from exc
        return self.get(new_id)

    def update(self, student_id, student_no, first_name, last_name, department="",
               email="", class_year=None) -> Student:
        old_number = self.get(student_id).student_no
        values = self._validate(student_no, first_name, last_name, department, email,
                                class_year)
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """UPDATE students
                       SET student_no = ?, first_name = ?, last_name = ?, department = ?,
                           email = ?, class_year = ?
                       WHERE id = ?""",
                    values + (student_id,),
                )
                # Görünen ad öğrenci kaydını izler. Kullanıcı adı yalnızca öğrenci
                # numarasıyla aynıysa değişir (özel kullanıcı adları korunur).
                cur.execute("UPDATE users SET full_name = ? WHERE student_id = ?",
                            (f"{values[1]} {values[2]}", student_id))
                cur.execute(
                    "UPDATE users SET username = ? WHERE student_id = ? AND username = ?",
                    (values[0], student_id, old_number),
                )
        except sqlite3.IntegrityError as exc:
            raise ValidationError(DUPLICATE_NO, field="Öğrenci numarası") from exc
        return self.get(student_id)

    def delete(self, student_id) -> None:
        affected = self.db.run("DELETE FROM students WHERE id = ?", (student_id,))
        if not affected:
            raise NotFoundError("Silinecek öğrenci bulunamadı.")

    # ------------------------------------------------------------------ sorgu
    def get(self, student_id) -> Student:
        row = self.db.query_one("SELECT * FROM students WHERE id = ?", (student_id,))
        if row is None:
            raise NotFoundError("Öğrenci bulunamadı.")
        return Student.from_row(row)

    def list(self, search: str = "") -> list[Student]:
        text = clean(search)
        if not text:
            rows = self.db.query("SELECT * FROM students ORDER BY student_no")
        else:
            pattern = f"%{text}%"
            rows = self.db.query(
                """SELECT * FROM students
                   WHERE student_no LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                      OR department LIKE ? OR email LIKE ?
                   ORDER BY student_no""",
                (pattern, pattern, pattern, pattern, pattern),
            )
        return [Student.from_row(row) for row in rows]

    def departments(self) -> list[str]:
        rows = self.db.query(
            "SELECT DISTINCT department FROM students WHERE department <> '' ORDER BY department"
        )
        return [row["department"] for row in rows]

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS total FROM students")
        return int(row["total"]) if row else 0
