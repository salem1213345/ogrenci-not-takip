"""Veri erisim katmani: tum SQL burada, parametreli sorgularla."""
import sqlite3
from datetime import datetime

from src.models.entities import Course, Grade, Student


class DuplicateError(Exception):
    """Benzersiz alan cakismasi (ornegin ayni ogrenci numarasi)."""


def _student(r):
    return Student(r["student_no"], r["first_name"], r["last_name"],
                   r["email"], r["id"])


def _course(r):
    return Course(r["code"], r["name"], r["credit"], r["midterm_weight"],
                  r["final_weight"], r["id"])


class StudentRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, s):
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO students (student_no, first_name, last_name, email)"
                    " VALUES (?, ?, ?, ?)",
                    (s.student_no, s.first_name, s.last_name, s.email))
        except sqlite3.IntegrityError as exc:
            raise DuplicateError("Bu öğrenci numarası zaten kayıtlı.") from exc
        s.id = cur.lastrowid
        return s

    def update(self, s):
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE students SET student_no=?, first_name=?, last_name=?,"
                    " email=? WHERE id=?",
                    (s.student_no, s.first_name, s.last_name, s.email, s.id))
        except sqlite3.IntegrityError as exc:
            raise DuplicateError("Bu öğrenci numarası zaten kayıtlı.") from exc

    def delete(self, student_id):
        with self.conn:
            self.conn.execute("DELETE FROM students WHERE id=?", (student_id,))

    def get(self, student_id):
        r = self.conn.execute("SELECT * FROM students WHERE id=?",
                              (student_id,)).fetchone()
        return _student(r) if r else None

    def list_all(self):
        rows = self.conn.execute(
            "SELECT * FROM students ORDER BY student_no").fetchall()
        return [_student(r) for r in rows]

    def search(self, query):
        like = f"%{query}%"
        rows = self.conn.execute(
            "SELECT * FROM students WHERE student_no LIKE ? OR first_name LIKE ?"
            " OR last_name LIKE ? ORDER BY student_no", (like, like, like)
        ).fetchall()
        return [_student(r) for r in rows]


class CourseRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, c):
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO courses (code, name, credit, midterm_weight,"
                    " final_weight) VALUES (?, ?, ?, ?, ?)",
                    (c.code, c.name, c.credit, c.midterm_weight, c.final_weight))
        except sqlite3.IntegrityError as exc:
            raise DuplicateError("Bu ders kodu zaten kayıtlı.") from exc
        c.id = cur.lastrowid
        return c

    def delete(self, course_id):
        with self.conn:
            self.conn.execute("DELETE FROM courses WHERE id=?", (course_id,))

    def get(self, course_id):
        r = self.conn.execute("SELECT * FROM courses WHERE id=?",
                              (course_id,)).fetchone()
        return _course(r) if r else None

    def list_all(self):
        rows = self.conn.execute("SELECT * FROM courses ORDER BY code").fetchall()
        return [_course(r) for r in rows]


class EnrollmentRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, student_id, course_id, term):
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO enrollments (student_id, course_id, term)"
                    " VALUES (?, ?, ?)", (student_id, course_id, term))
        except sqlite3.IntegrityError as exc:
            raise DuplicateError(
                "Öğrenci bu derse bu dönem zaten kayıtlı.") from exc
        return cur.lastrowid

    def delete(self, enrollment_id):
        with self.conn:
            self.conn.execute("DELETE FROM enrollments WHERE id=?",
                              (enrollment_id,))

    def list_by_course(self, course_id, term=None):
        sql = ("SELECT e.id AS enrollment_id, e.term, s.* FROM enrollments e"
               " JOIN students s ON s.id = e.student_id WHERE e.course_id=?")
        params = [course_id]
        if term:
            sql += " AND e.term=?"
            params.append(term)
        rows = self.conn.execute(sql + " ORDER BY s.student_no", params).fetchall()
        return [(r["enrollment_id"], r["term"], _student(r)) for r in rows]

    def list_by_student(self, student_id):
        rows = self.conn.execute(
            "SELECT e.id AS enrollment_id, e.term, c.* FROM enrollments e"
            " JOIN courses c ON c.id = e.course_id WHERE e.student_id=?"
            " ORDER BY e.term, c.code", (student_id,)).fetchall()
        return [(r["enrollment_id"], r["term"], _course(r)) for r in rows]


class GradeRepository:
    def __init__(self, conn):
        self.conn = conn

    def save(self, g):
        now = datetime.now().isoformat(timespec="seconds")
        with self.conn:
            self.conn.execute(
                "INSERT INTO grades (enrollment_id, midterm, final, assignment,"
                " updated_at) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(enrollment_id) DO UPDATE SET midterm=excluded.midterm,"
                " final=excluded.final, assignment=excluded.assignment,"
                " updated_at=excluded.updated_at",
                (g.enrollment_id, g.midterm, g.final, g.assignment, now))

    def get(self, enrollment_id):
        r = self.conn.execute("SELECT * FROM grades WHERE enrollment_id=?",
                              (enrollment_id,)).fetchone()
        if not r:
            return None
        return Grade(r["enrollment_id"], r["midterm"], r["final"],
                     r["assignment"], r["id"])
