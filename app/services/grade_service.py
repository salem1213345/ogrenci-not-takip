"""Not işlemleri, ders ortalamaları ve karne hesaplamaları."""

import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.config import DEFAULT_WEIGHTS, EXAM_TYPES
from app.database import Database
from app.errors import NotFoundError, ValidationError
from app.grading import compute_gpa, grade_point, is_passed, letter_grade, weighted_average
from app.models import ClassSummary, CourseAverage, Grade, Student, StudentReport
from app.validators import clean, parse_date, parse_decimal

EARLIEST_EXAM_DATE = date(2000, 1, 1)
ENROLL_SQL = "INSERT OR IGNORE INTO enrollments (student_id, course_id) VALUES (?, ?)"


class SheetValidationError(ValidationError):
    """Toplu not girişinde bir veya daha fazla hücre geçersiz.

    ``errors``: {(öğrenci_id, sınav_türü): hata metni}
    """

    def __init__(self, errors: dict):
        first = next(iter(errors.values()))
        count = len(errors)
        message = first if count == 1 else f"{count} hücre hatalı. İlk hata: {first}"
        super().__init__(message, field="Puan")
        self.errors = errors


@dataclass
class SheetRow:
    """Bir dersin not çizelgesinde tek öğrencinin satırı."""

    student: Student
    grades: dict = field(default_factory=dict)  # sınav türü -> Grade
    average: float | None = None
    letter: str = "-"
    status: str = "Not yok"


BASE_SELECT = """
    SELECT g.*, c.code AS course_code, c.name AS course_name, c.credit AS course_credit
    FROM grades g
    JOIN courses c ON c.id = g.course_id
"""


class GradeService:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------- doğrulama
    @staticmethod
    def default_weight(exam_type: str) -> float:
        return DEFAULT_WEIGHTS.get(clean(exam_type), 40.0)

    @staticmethod
    def _exam_date(value) -> str:
        """Sınav tarihi geçerli olmalı ve makul bir aralıkta bulunmalı."""
        iso = parse_date(value, "Sınav tarihi")
        parsed = date.fromisoformat(iso)
        if parsed < EARLIEST_EXAM_DATE or parsed > date.today() + timedelta(days=366):
            raise ValidationError(
                "Sınav tarihi 01.01.2000 ile önümüzdeki bir yıl arasında olmalıdır.",
                field="Sınav tarihi",
            )
        return iso

    def _validate(self, exam_type, score, weight):
        exam = clean(exam_type)
        if exam not in EXAM_TYPES:
            raise ValidationError("Sınav türü şunlardan biri olmalı: " + ", ".join(EXAM_TYPES),
                                  field="Sınav türü")
        score_value = parse_decimal(score, "Puan", 0, 100)
        weight_text = clean(weight)
        if weight_text:
            weight_value = parse_decimal(weight_text, "Ağırlık", 1, 100)
        else:
            weight_value = self.default_weight(exam)
        return exam, score_value, weight_value

    def _ensure_student(self, student_id) -> None:
        row = self.db.query_one("SELECT id FROM students WHERE id = ?", (student_id,))
        if row is None:
            raise NotFoundError("Seçilen öğrenci bulunamadı.")

    def _ensure_course(self, course_id) -> None:
        row = self.db.query_one("SELECT id FROM courses WHERE id = ?", (course_id,))
        if row is None:
            raise NotFoundError("Seçilen ders bulunamadı.")

    # ------------------------------------------------------------------- CRUD
    def add(self, student_id, course_id, exam_type, score, weight=None,
            exam_date=None) -> Grade:
        self._ensure_student(student_id)
        self._ensure_course(course_id)
        exam, score_value, weight_value = self._validate(exam_type, score, weight)
        date_value = self._exam_date(exam_date)
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """INSERT INTO grades
                       (student_id, course_id, exam_type, score, weight, exam_date)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (student_id, course_id, exam, score_value, weight_value, date_value),
                )
                new_id = int(cur.lastrowid)
                # Not girilen öğrenci o derse kayıtlı sayılır.
                cur.execute(ENROLL_SQL, (student_id, course_id))
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                f"Bu ders için '{exam}' notu zaten girilmiş. Güncellemeyi kullanın.",
                field="Sınav türü",
            ) from exc
        return self.get(new_id)

    def update(self, grade_id, student_id, course_id, exam_type, score, weight=None,
               exam_date=None) -> Grade:
        self.get(grade_id)
        self._ensure_student(student_id)
        self._ensure_course(course_id)
        exam, score_value, weight_value = self._validate(exam_type, score, weight)
        date_value = self._exam_date(exam_date)
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """UPDATE grades
                       SET student_id = ?, course_id = ?, exam_type = ?, score = ?,
                           weight = ?, exam_date = ?
                       WHERE id = ?""",
                    (student_id, course_id, exam, score_value, weight_value, date_value,
                     grade_id),
                )
                cur.execute(ENROLL_SQL, (student_id, course_id))
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                f"Bu ders için '{exam}' notu zaten girilmiş. Güncellemeyi kullanın.",
                field="Sınav türü",
            ) from exc
        return self.get(grade_id)

    def delete(self, grade_id) -> None:
        affected = self.db.run("DELETE FROM grades WHERE id = ?", (grade_id,))
        if not affected:
            raise NotFoundError("Silinecek not bulunamadı.")

    # ------------------------------------------------------------------ sorgu
    def get(self, grade_id) -> Grade:
        row = self.db.query_one(f"{BASE_SELECT} WHERE g.id = ?", (grade_id,))
        if row is None:
            raise NotFoundError("Not kaydı bulunamadı.")
        return Grade.from_row(row)

    def list_by_student(self, student_id) -> list[Grade]:
        rows = self.db.query(
            f"{BASE_SELECT} WHERE g.student_id = ? ORDER BY c.code, g.exam_type",
            (student_id,),
        )
        return [Grade.from_row(row) for row in rows]

    def list_by_course(self, course_id) -> list[Grade]:
        rows = self.db.query(
            f"{BASE_SELECT} WHERE g.course_id = ? ORDER BY g.score DESC",
            (course_id,),
        )
        return [Grade.from_row(row) for row in rows]

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS total FROM grades")
        return int(row["total"]) if row else 0

    # ------------------------------------------------------------- hesaplama
    def student_report(self, student_id) -> StudentReport:
        row = self.db.query_one("SELECT * FROM students WHERE id = ?", (student_id,))
        if row is None:
            raise NotFoundError("Öğrenci bulunamadı.")
        student = Student.from_row(row)

        grades = self.db.query(
            """SELECT g.course_id, g.exam_type, g.score, g.weight,
                      c.code AS course_code, c.name AS course_name, c.credit AS credit
               FROM grades g
               JOIN courses c ON c.id = g.course_id
               WHERE g.student_id = ?
               ORDER BY c.code, g.exam_type""",
            (student_id,),
        )

        grouped: dict[int, dict] = {}
        for grade in grades:
            entry = grouped.setdefault(
                grade["course_id"],
                {
                    "code": grade["course_code"],
                    "name": grade["course_name"],
                    "credit": int(grade["credit"]),
                    "items": [],
                },
            )
            entry["items"].append((float(grade["score"]), float(grade["weight"])))

        courses: list[CourseAverage] = []
        for course_id, entry in grouped.items():
            average = weighted_average(entry["items"])
            if average is None:
                continue
            courses.append(
                CourseAverage(
                    course_id=course_id,
                    course_code=entry["code"],
                    course_name=entry["name"],
                    credit=entry["credit"],
                    average=average,
                    letter=letter_grade(average),
                    point=grade_point(average),
                    passed=is_passed(average),
                    grade_count=len(entry["items"]),
                )
            )

        gpa = compute_gpa([(course.point, course.credit) for course in courses])
        return StudentReport(
            student=student,
            courses=courses,
            gpa=gpa,
            total_credit=sum(course.credit for course in courses),
        )

    def class_summary(self) -> list[ClassSummary]:
        students = self.db.query("SELECT id, student_no FROM students ORDER BY student_no")
        summaries: list[ClassSummary] = []
        for row in students:
            report = self.student_report(row["id"])
            summaries.append(
                ClassSummary(
                    student_id=int(row["id"]),
                    student_no=row["student_no"],
                    full_name=report.student.full_name,
                    department=report.student.department,
                    course_count=len(report.courses),
                    gpa=report.gpa,
                    failed_count=report.failed_count,
                    status=report.status,
                )
            )
        return summaries

    # ------------------------------------------------------- ders çizelgesi
    def course_sheet(self, course_id, class_year=None) -> list[SheetRow]:
        """Derse kayıtlı her öğrenci için sınav notları ve ağırlıklı ortalama."""
        self._ensure_course(course_id)
        sql = ("SELECT s.* FROM enrollments e JOIN students s ON s.id = e.student_id "
               "WHERE e.course_id = ?")
        params: list = [course_id]
        if class_year:
            sql += " AND s.class_year = ?"
            params.append(int(class_year))
        rows = self.db.query(sql + " ORDER BY s.student_no", tuple(params))
        students = [Student.from_row(r) for r in rows]
        grades: dict[int, dict] = {}
        for row in self.db.query(f"{BASE_SELECT} WHERE g.course_id = ?", (course_id,)):
            grade = Grade.from_row(row)
            grades.setdefault(grade.student_id, {})[grade.exam_type] = grade
        sheet = []
        for student in students:
            own = grades.get(student.id, {})
            average = weighted_average((g.score, g.weight) for g in own.values())
            sheet.append(SheetRow(
                student=student,
                grades=own,
                average=average,
                letter=letter_grade(average) if average is not None else "-",
                status=("Geçti" if is_passed(average) else "Kaldı") if average is not None
                else "Not yok",
            ))
        return sheet

    def save_sheet(self, course_id, entries: dict, exam_date=None) -> tuple[int, int]:
        """Toplu not girişi: {öğrenci_id: {sınav_türü: puan_metni}}.

        Boş hücreler atlanır (mevcut not değişmez). Önce tüm hücreler doğrulanır;
        tek bir hata varsa hiçbir şey kaydedilmez. (eklenen, güncellenen) döner.
        """
        self._ensure_course(course_id)
        date_value = self._exam_date(exam_date)
        enrolled = {s.id for s in (row.student for row in self.course_sheet(course_id))}
        existing = {
            (int(r["student_id"]), r["exam_type"]): r
            for r in self.db.query("SELECT * FROM grades WHERE course_id = ?", (course_id,))
        }
        errors: dict = {}
        inserts, updates = [], []
        for student_id, cells in entries.items():
            if int(student_id) not in enrolled:
                errors[(student_id, "")] = "Öğrenci bu derse kayıtlı değil."
                continue
            for exam, text in cells.items():
                if not clean(text):
                    continue
                if exam not in EXAM_TYPES:
                    errors[(student_id, exam)] = f"Geçersiz sınav türü: {exam}"
                    continue
                try:
                    score = parse_decimal(text, "Puan", 0, 100)
                except ValidationError as exc:
                    errors[(student_id, exam)] = str(exc)
                    continue
                current = existing.get((int(student_id), exam))
                if current is None:
                    inserts.append((student_id, course_id, exam, score,
                                    self.default_weight(exam), date_value))
                elif float(current["score"]) != score:
                    updates.append((score, current["id"]))
        if errors:
            raise SheetValidationError(errors)
        with self.db.cursor() as cur:
            cur.executemany(
                "INSERT INTO grades (student_id, course_id, exam_type, score, weight, exam_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                inserts,
            )
            cur.executemany("UPDATE grades SET score = ? WHERE id = ?", updates)
        return len(inserts), len(updates)

    # ---------------------------------------------------- öğretmen özeti
    def recent_for_teacher(self, teacher_id, limit: int = 8) -> list[dict]:
        """Öğretmenin derslerinde en son girilen notlar (yeniden eskiye)."""
        return self.db.query(
            """SELECT g.exam_type, g.score, g.exam_date, c.code AS course_code,
                      s.first_name || ' ' || s.last_name AS student_name
               FROM grades g
               JOIN courses c ON c.id = g.course_id
               JOIN students s ON s.id = g.student_id
               WHERE c.teacher_id = ? OR c.teacher_id IS NULL
               ORDER BY g.exam_date DESC, g.id DESC
               LIMIT ?""",
            (teacher_id, int(limit)),
        )

    def teacher_stats(self, teacher_id) -> dict:
        """Öğretmenin derslerine göre hesaplanan sayılar (ana sayfa kartları)."""
        scope = "(c.teacher_id = ? OR c.teacher_id IS NULL)"
        courses = self.db.query_one(
            f"SELECT COUNT(*) AS total FROM courses c WHERE {scope}", (teacher_id,)
        )["total"]
        students = self.db.query(
            f"SELECT DISTINCT e.student_id FROM enrollments e JOIN courses c "
            f"ON c.id = e.course_id WHERE {scope}",
            (teacher_id,),
        )
        grades = self.db.query_one(
            f"SELECT COUNT(*) AS total FROM grades g JOIN courses c ON c.id = g.course_id "
            f"WHERE {scope}",
            (teacher_id,),
        )["total"]
        gpas = [self.student_report(r["student_id"]).gpa for r in students]
        gpas = [value for value in gpas if value is not None]
        return {
            "students": len(students),
            "courses": int(courses),
            "grades": int(grades),
            "average_gpa": round(sum(gpas) / len(gpas), 2) if gpas else None,
        }
