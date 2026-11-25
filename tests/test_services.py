import csv
import os
import tempfile
import unittest

from src.database.db import get_connection
from src.models.entities import Course, Student
from src.repositories.repos import DuplicateError
from src.services.app_services import (CourseService, EnrollmentService,
                                       GradeService, StudentService)
from src.services.auth_service import AuthService, hash_password, verify_password
from src.services.exporter import ReportExporter


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.students = StudentService(self.conn)
        self.courses = CourseService(self.conn)
        self.enroll = EnrollmentService(self.conn)
        self.grades = GradeService(self.conn)
        self.exporter = ReportExporter(self.students, self.courses,
                                       self.enroll, self.grades)

    def tearDown(self):
        self.conn.close()

    def make_student(self, no="1001", first="Ayşe", last="Yılmaz"):
        return self.students.add(Student(no, first, last))

    def make_course(self, code="BIL101", credit=3):
        return self.courses.add(Course(code, "Programlama", credit))


class TestStudentService(BaseCase):
    def test_add_and_list(self):  # TC-16
        self.make_student()
        self.assertEqual(len(self.students.list_all()), 1)

    def test_duplicate_number_rejected(self):  # TC-17
        self.make_student("1001")
        with self.assertRaises(DuplicateError):
            self.make_student("1001", "Ali", "Veli")

    def test_required_fields(self):  # TC-18
        with self.assertRaises(ValueError):
            self.students.add(Student("", "A", "B"))

    def test_invalid_email(self):  # TC-19
        with self.assertRaises(ValueError):
            self.students.add(Student("1", "A", "B", "yanlis"))

    def test_update(self):  # TC-20
        s = self.make_student()
        s.last_name = "Demir"
        self.students.update(s)
        self.assertEqual(self.students.search("Demir")[0].id, s.id)

    def test_search(self):  # TC-21
        self.make_student("1001", "Ayşe", "Yılmaz")
        self.make_student("1002", "Mehmet", "Demir")
        self.assertEqual(len(self.students.search("Meh")), 1)
        self.assertEqual(len(self.students.search("")), 2)

    def test_delete_cascades_enrollment(self):  # TC-22
        s, c = self.make_student(), self.make_course()
        self.enroll.enroll(s.id, c.id, "2026-Güz")
        self.students.delete(s.id)
        self.assertEqual(self.enroll.list_by_course(c.id), [])

    def test_sql_injection_is_inert(self):  # TC-23
        self.make_student()
        self.students.search("x'; DROP TABLE students; --")
        self.assertEqual(len(self.students.list_all()), 1)


class TestCourseAndEnrollment(BaseCase):
    def test_course_invalid_credit(self):  # TC-24
        with self.assertRaises(ValueError):
            self.courses.add(Course("X1", "Y", 0))

    def test_course_invalid_weights(self):  # TC-25
        with self.assertRaises(ValueError):
            self.courses.add(Course("X1", "Y", 3, 50, 60))

    def test_duplicate_course_code(self):  # TC-26
        self.make_course("BIL101")
        with self.assertRaises(DuplicateError):
            self.make_course("BIL101")

    def test_duplicate_enrollment(self):  # TC-27
        s, c = self.make_student(), self.make_course()
        self.enroll.enroll(s.id, c.id, "2026-Güz")
        with self.assertRaises(DuplicateError):
            self.enroll.enroll(s.id, c.id, "2026-Güz")

    def test_same_course_other_term_allowed(self):  # TC-28
        s, c = self.make_student(), self.make_course()
        self.enroll.enroll(s.id, c.id, "2026-Güz")
        self.enroll.enroll(s.id, c.id, "2027-Bahar")
        self.assertEqual(len(self.enroll.list_by_student(s.id)), 2)

    def test_drop(self):  # TC-29
        s, c = self.make_student(), self.make_course()
        eid = self.enroll.enroll(s.id, c.id, "2026-Güz")
        self.enroll.drop(eid)
        self.assertEqual(self.enroll.list_by_student(s.id), [])


class TestGradeService(BaseCase):
    def setUp(self):
        super().setUp()
        self.s, self.c = self.make_student(), self.make_course()
        self.eid = self.enroll.enroll(self.s.id, self.c.id, "2026-Güz")

    def test_evaluate_without_grade(self):  # TC-30
        r = self.grades.evaluate(self.eid, self.c)
        self.assertEqual(r["status"], "Tamamlanmadı")
        self.assertIsNone(r["average"])

    def test_pass(self):  # TC-31
        self.grades.enter_grade(self.eid, 70, 80)
        r = self.grades.evaluate(self.eid, self.c)
        self.assertEqual((r["average"], r["letter"], r["status"]),
                         (76.0, "CB", "Geçti"))

    def test_fail_by_average(self):  # TC-32
        self.grades.enter_grade(self.eid, 20, 55)
        self.assertEqual(self.grades.evaluate(self.eid, self.c)["status"], "Kaldı")

    def test_fail_by_final_floor(self):  # TC-33
        self.grades.enter_grade(self.eid, 100, 45)
        r = self.grades.evaluate(self.eid, self.c)
        self.assertEqual(r["average"], 67.0)
        self.assertEqual(r["status"], "Kaldı")

    def test_invalid_grade_not_saved(self):  # TC-34
        with self.assertRaises(ValueError):
            self.grades.enter_grade(self.eid, 120, 50)
        self.assertIsNone(self.grades.repo.get(self.eid))

    def test_update_overwrites(self):  # TC-35
        self.grades.enter_grade(self.eid, 10, 10)
        self.grades.enter_grade(self.eid, 90, 90)
        self.assertEqual(self.grades.evaluate(self.eid, self.c)["average"], 90.0)

    def test_course_weights_used(self):  # TC-36
        c2 = self.courses.add(Course("MAT1", "Mat", 4, 50, 50))
        eid = self.enroll.enroll(self.s.id, c2.id, "2026-Güz")
        self.grades.enter_grade(eid, 60, 80)
        self.assertEqual(self.grades.evaluate(eid, c2)["average"], 70.0)

    def test_assignment_used(self):  # TC-37
        self.grades.enter_grade(self.eid, 70, 85, 90)
        self.assertEqual(self.grades.evaluate(self.eid, self.c)["average"], 81.5)


class TestExporter(BaseCase):
    def setUp(self):
        super().setUp()
        self.s, self.c = self.make_student(), self.make_course()
        self.eid = self.enroll.enroll(self.s.id, self.c.id, "2026-Güz")
        self.grades.enter_grade(self.eid, 90, 90)
        self.tmp = tempfile.mkdtemp()

    def test_csv_content(self):  # TC-38
        path = self.exporter.export_course_csv(self.c.id,
                                               os.path.join(self.tmp, "a.csv"))
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        self.assertEqual(rows[0][0], "ogrenci_no")
        self.assertEqual(rows[1][0], "1001")
        self.assertEqual(rows[1][6:], ["90.00", "AA", "Geçti"])

    def test_csv_missing_grade_is_blank(self):  # TC-39
        s2 = self.make_student("1002", "Ali", "Veli")
        self.enroll.enroll(s2.id, self.c.id, "2026-Güz")
        path = self.exporter.export_course_csv(self.c.id,
                                               os.path.join(self.tmp, "b.csv"))
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        self.assertEqual(rows[2][3:], ["", "", "", "", "", "Tamamlanmadı"])

    def test_pdf_created(self):  # TC-40
        path = self.exporter.export_transcript_pdf(
            self.s.id, os.path.join(self.tmp, "t.pdf"))
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(5), b"%PDF-")

    def test_transcript_gpa(self):  # TC-41
        rows, gpa = self.exporter.transcript_rows(self.s.id)
        self.assertEqual(gpa, 4.0)
        self.assertEqual(len(rows), 1)

    def test_unknown_ids(self):  # TC-42
        with self.assertRaises(ValueError):
            self.exporter.export_course_csv(999, os.path.join(self.tmp, "x.csv"))
        with self.assertRaises(ValueError):
            self.exporter.export_transcript_pdf(999, os.path.join(self.tmp, "x.pdf"))


class TestAuth(BaseCase):
    def test_hash_not_plaintext_and_verifies(self):  # TC-43
        h = hash_password("gizli123")
        self.assertNotIn("gizli123", h)
        self.assertTrue(verify_password("gizli123", h))
        self.assertFalse(verify_password("yanlis", h))

    def test_salt_differs(self):  # TC-44
        self.assertNotEqual(hash_password("aynisifre"), hash_password("aynisifre"))

    def test_login_and_roles(self):  # TC-45
        auth = AuthService(self.conn)
        auth.create_user("admin", "admin123", "admin")
        auth.create_user("ogr", "ogretmen1", "teacher")
        admin = auth.login("admin", "admin123")
        teacher = auth.login("ogr", "ogretmen1")
        self.assertIsNone(auth.login("admin", "yanlis"))
        self.assertTrue(auth.has_permission(admin, "delete_student"))
        self.assertFalse(auth.has_permission(teacher, "delete_student"))
        self.assertTrue(auth.has_permission(teacher, "enter_grade"))

    def test_short_password_rejected(self):  # TC-46
        with self.assertRaises(ValueError):
            AuthService(self.conn).create_user("x", "123")


if __name__ == "__main__":
    unittest.main()
