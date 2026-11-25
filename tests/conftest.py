"""Ortak pytest fixture'ları."""

from types import SimpleNamespace

import pytest

from app.database import Database
from app.services.course_service import CourseService
from app.services.grade_service import GradeService
from app.services.report_service import ReportService
from app.services.student_service import StudentService


@pytest.fixture()
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture()
def student_service(db):
    return StudentService(db)


@pytest.fixture()
def course_service(db):
    return CourseService(db)


@pytest.fixture()
def grade_service(db):
    return GradeService(db)


@pytest.fixture()
def report_service(student_service, grade_service):
    return ReportService(student_service, grade_service)


@pytest.fixture()
def sample(student_service, course_service, grade_service):
    """Bir öğrenci, iki ders ve üç not içeren küçük veri seti."""
    student = student_service.add(
        "2026001", "Elif", "Yılmaz", "Bilgisayar Mühendisliği", "elif@okul.edu.tr"
    )
    course = course_service.add("BIL101", "Programlamaya Giriş", 4, "Dr. Kaya", "2026-Güz")
    other = course_service.add("MAT101", "Matematik I", 4, "Prof. Dr. Öztürk", "2026-Güz")
    grade_service.add(student.id, course.id, "Vize", 80, 40, "2026-10-01")
    grade_service.add(student.id, course.id, "Final", 60, 60, "2026-01-10")
    grade_service.add(student.id, other.id, "Vize", 90, 40, "2026-10-02")
    return SimpleNamespace(student=student, course=course, other_course=other)
