"""Ornek veri yukler: python seed_demo.py"""
from src.database.db import get_connection
from src.models.entities import Course, Student
from src.services.app_services import (CourseService, EnrollmentService,
                                       GradeService, StudentService)
from src.services.auth_service import AuthService


def main():
    conn = get_connection()
    students, courses = StudentService(conn), CourseService(conn)
    enroll, grades = EnrollmentService(conn), GradeService(conn)
    course = courses.add(Course("BIL101", "Programlamaya Giriş", 4))
    data = [("20240001", "Ayşe", "Yılmaz", 70, 85, 90),
            ("20240002", "Mehmet", "Demir", 45, 50, None),
            ("20240003", "Zeynep", "Kaya", 95, 92, None)]
    for no, first, last, mid, fin, asg in data:
        s = students.add(Student(no, first, last))
        eid = enroll.enroll(s.id, course.id, "2026-Güz")
        grades.enter_grade(eid, mid, fin, asg)
    AuthService(conn).create_user("admin", "admin123", "admin")
    print("Örnek veri yüklendi.")


if __name__ == "__main__":
    main()
