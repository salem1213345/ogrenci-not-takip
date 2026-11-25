"""Is mantigi: dogrulama ve repository koordinasyonu."""
import re

from src.models.entities import Course, Grade, Student
from src.repositories.repos import (CourseRepository, EnrollmentRepository,
                                    GradeRepository, StudentRepository)
from src.services import grade_calculator as calc

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class StudentService:
    def __init__(self, conn):
        self.repo = StudentRepository(conn)

    @staticmethod
    def _validate(s):
        s.student_no = (s.student_no or "").strip()
        s.first_name = (s.first_name or "").strip()
        s.last_name = (s.last_name or "").strip()
        if not (s.student_no and s.first_name and s.last_name):
            raise ValueError("Numara, ad ve soyad zorunludur.")
        if s.email and not EMAIL_RE.match(s.email):
            raise ValueError("E-posta adresi geçersiz.")

    def add(self, s):
        self._validate(s)
        return self.repo.add(s)

    def update(self, s):
        self._validate(s)
        self.repo.update(s)

    def delete(self, student_id):
        self.repo.delete(student_id)

    def search(self, query=""):
        return self.repo.search(query.strip()) if query.strip() else self.repo.list_all()

    def list_all(self):
        return self.repo.list_all()


class CourseService:
    def __init__(self, conn):
        self.repo = CourseRepository(conn)

    def add(self, c):
        c.code = (c.code or "").strip()
        c.name = (c.name or "").strip()
        if not (c.code and c.name):
            raise ValueError("Ders kodu ve adı zorunludur.")
        if not isinstance(c.credit, int) or c.credit <= 0:
            raise ValueError("Kredi pozitif tam sayı olmalıdır.")
        c.validate_weights()
        return self.repo.add(c)

    def delete(self, course_id):
        self.repo.delete(course_id)

    def list_all(self):
        return self.repo.list_all()


class EnrollmentService:
    def __init__(self, conn):
        self.repo = EnrollmentRepository(conn)

    def enroll(self, student_id, course_id, term):
        if not term or not term.strip():
            raise ValueError("Dönem zorunludur.")
        return self.repo.add(student_id, course_id, term.strip())

    def drop(self, enrollment_id):
        self.repo.delete(enrollment_id)

    def list_by_course(self, course_id, term=None):
        return self.repo.list_by_course(course_id, term)

    def list_by_student(self, student_id):
        return self.repo.list_by_student(student_id)


class GradeService:
    def __init__(self, conn):
        self.repo = GradeRepository(conn)

    def enter_grade(self, enrollment_id, midterm, final, assignment=None):
        """Notlari dogrular ve kaydeder (FR-07)."""
        g = Grade(enrollment_id,
                  calc.validate_score(midterm, "Vize"),
                  calc.validate_score(final, "Final"),
                  calc.validate_score(assignment, "Ödev"))
        self.repo.save(g)
        return g

    def evaluate(self, enrollment_id, course):
        """Kayit icin sonuc sozlugu; not eksikse status='Tamamlanmadı'."""
        g = self.repo.get(enrollment_id)
        if g is None or not g.is_complete():
            return {"midterm": g.midterm if g else None,
                    "final": g.final if g else None,
                    "assignment": g.assignment if g else None,
                    "average": None, "letter": None, "coef": None,
                    "status": "Tamamlanmadı"}
        weights = None
        if g.assignment is None:
            weights = (course.midterm_weight, course.final_weight, 0)
        avg = calc.calculate_average(g.midterm, g.final, g.assignment, weights)
        letter, coef = calc.to_letter(avg)
        passed = calc.is_passed(avg, g.final)
        return {"midterm": g.midterm, "final": g.final,
                "assignment": g.assignment, "average": avg, "letter": letter,
                "coef": coef, "status": "Geçti" if passed else "Kaldı"}
