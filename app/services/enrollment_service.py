"""Ders kayıtları: hangi öğrenci hangi derse kayıtlı."""

from app.database import Database
from app.errors import NotFoundError, ValidationError
from app.models import Course, Student


class EnrollmentService:
    def __init__(self, db: Database):
        self.db = db

    def enroll(self, student_id, course_id) -> bool:
        """Öğrenciyi derse kaydeder; zaten kayıtlıysa False döner."""
        if self.db.query_one("SELECT id FROM students WHERE id = ?", (student_id,)) is None:
            raise NotFoundError("Öğrenci bulunamadı.")
        if self.db.query_one("SELECT id FROM courses WHERE id = ?", (course_id,)) is None:
            raise NotFoundError("Ders bulunamadı.")
        return bool(self.db.run(
            "INSERT OR IGNORE INTO enrollments (student_id, course_id) VALUES (?, ?)",
            (student_id, course_id),
        ))

    def unenroll(self, student_id, course_id) -> None:
        graded = self.db.query_one(
            "SELECT COUNT(*) AS total FROM grades WHERE student_id = ? AND course_id = ?",
            (student_id, course_id),
        )["total"]
        if graded:
            raise ValidationError(
                "Bu öğrencinin bu derste notları var. Kaydı silmeden önce notları silin."
            )
        if not self.db.run(
            "DELETE FROM enrollments WHERE student_id = ? AND course_id = ?",
            (student_id, course_id),
        ):
            raise NotFoundError("Ders kaydı bulunamadı.")

    def is_enrolled(self, student_id, course_id) -> bool:
        return self.db.query_one(
            "SELECT 1 AS x FROM enrollments WHERE student_id = ? AND course_id = ?",
            (student_id, course_id),
        ) is not None

    def students_of(self, course_id, class_year=None) -> list[Student]:
        sql = ("SELECT s.* FROM enrollments e JOIN students s ON s.id = e.student_id "
               "WHERE e.course_id = ?")
        params: list = [course_id]
        if class_year:
            sql += " AND s.class_year = ?"
            params.append(int(class_year))
        rows = self.db.query(sql + " ORDER BY s.student_no", tuple(params))
        return [Student.from_row(row) for row in rows]

    def courses_of(self, student_id) -> list[Course]:
        rows = self.db.query(
            "SELECT c.* FROM enrollments e JOIN courses c ON c.id = e.course_id "
            "WHERE e.student_id = ? ORDER BY c.code",
            (student_id,),
        )
        return [Course.from_row(row) for row in rows]

    def counts_by_course(self) -> dict[int, int]:
        rows = self.db.query(
            "SELECT course_id, COUNT(*) AS total FROM enrollments GROUP BY course_id"
        )
        return {int(row["course_id"]): int(row["total"]) for row in rows}
