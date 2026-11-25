"""Ayrı demo veritabanı: içerik, hesaplar ve kalıcılık testleri."""

import subprocess
import sys
from pathlib import Path

import pytest

import main
from app.config import DEFAULT_DB_PATH, DEMO_DB_PATH
from app.database import Database
from app.demo_data import DEMO_PASSWORD, demo_accounts, is_demo, load_demo_data
from app.errors import ValidationError
from app.services.auth_service import AuthService
from app.services.course_service import CourseService
from app.services.grade_service import GradeService
from app.services.message_service import MessageService
from app.services.student_service import StudentService

TABLES = ("students", "courses", "grades", "users", "enrollments", "messages",
          "message_recipients", "meta")


def dump(db: Database) -> dict:
    """Tüm tabloların sıralı içeriği (karşılaştırma için)."""
    return {table: sorted(tuple(row.values()) for row in db.query(f"SELECT * FROM {table}"))
            for table in TABLES}


def open_demo(path, *extra) -> Database:
    """`python main.py --demo --db <path>` ile aynı yoldan veritabanını hazırlar."""
    args = main.build_parser().parse_args(["--demo", "--db", str(path), *extra])
    return main.prepare_database(args)


@pytest.fixture(scope="module")
def demo_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("demo") / "demo.db"
    open_demo(path).close()
    return path


@pytest.fixture()
def demo_db(demo_path):
    database = Database(demo_path)
    yield database
    database.close()


# ------------------------------------------------------------------ içerik
def test_demo_contents(demo_db):
    assert is_demo(demo_db)
    assert StudentService(demo_db).count() == 30
    assert CourseService(demo_db).count() == 8
    teachers = AuthService(demo_db).teachers()
    assert [t.username for t in teachers] == sorted(
        ["ogretmen1", "ogretmen2", "ogretmen3", "ogretmen4"],
        key=lambda name: next(t.full_name for t in teachers if t.username == name))
    names = {c.name for c in CourseService(demo_db).list()}
    assert {"Veri Tabanı", "Yazılım Mimarisi", "Yapay Zeka", "Görüntü İşleme",
            "Ağ Sistemleri", "İşletim Sistemleri", "Algoritmalar", "Matematik"} == names


def test_each_teacher_has_courses_and_classes_split(demo_db):
    courses = CourseService(demo_db)
    for teacher in AuthService(demo_db).teachers():
        assert len(courses.for_teacher(teacher.id)) == 2
    levels = demo_db.query("SELECT class_year, COUNT(*) AS n FROM students GROUP BY class_year")
    assert {(r["class_year"], r["n"]) for r in levels} == {(2, 15), (3, 15)}
    assert set(courses.semesters()) == {"2025-Güz", "2026-Bahar"}


def test_grades_cover_every_enrollment_with_some_missing(demo_db):
    grades = GradeService(demo_db)
    enrollments = demo_db.query_one("SELECT COUNT(*) AS n FROM enrollments")["n"]
    assert enrollments == 30 * 4
    total = grades.count()
    assert 300 < total < enrollments * 3  # vize/final/ödev; birkaç not eksik
    scores = [r["score"] for r in demo_db.query("SELECT score FROM grades")]
    assert min(scores) < 45 and max(scores) > 90  # gerçekçi dağılım
    for course in CourseService(demo_db).list():
        sheet = grades.course_sheet(course.id)
        assert len(sheet) == 15
        assert all(row.average is not None and row.letter != "-" for row in sheet)
    statuses = {row.status for row in grades.class_summary()}
    assert {"Geçti", "Kaldı"} <= statuses


def test_demo_messages(demo_db):
    total = demo_db.query_one("SELECT COUNT(*) AS n FROM messages")["n"]
    assert 35 <= total <= 45
    read = demo_db.query_one(
        "SELECT SUM(read_at IS NOT NULL) AS r, SUM(read_at IS NULL) AS u "
        "FROM message_recipients")
    assert read["r"] > 0 and read["u"] > 0
    teacher = AuthService(demo_db).authenticate("ogretmen1", DEMO_PASSWORD)
    inbox = MessageService(demo_db).inbox(teacher)
    assert inbox and all(m.subject and m.created_at for m in inbox)


def test_demo_accounts_log_in_with_1234(demo_db):
    auth = AuthService(demo_db)
    for number in range(1, 5):
        assert auth.authenticate(f"ogretmen{number}", "1234").is_teacher
    for number in range(1, 31):
        user = auth.authenticate(f"ogrenci{number}", "1234")
        assert user.is_student and user.student_id
    assert [a.role_label for a in demo_accounts(demo_db)] == ["Öğretmen"] * 4 + ["Öğrenci"] * 5


def test_real_accounts_still_require_strong_password(db):
    with pytest.raises(ValidationError):
        AuthService(db).create_teacher("ogretmen9", "Gerçek Hesap", "1234")


# ---------------------------------------------------------------- kalıcılık
def test_reopen_keeps_data_identical(demo_path):
    """Doldur -> kapat -> aynı komutla yeniden aç: veriler birebir aynı kalmalı."""
    first = Database(demo_path)
    before = dump(first)
    first.close()
    reopened = open_demo(demo_path)  # python main.py --demo --db data/demo.db
    try:
        assert dump(reopened) == before
    finally:
        reopened.close()


def test_data_is_on_disk_for_a_new_process(demo_path):
    """Uygulama tamamen kapanıp yeni bir süreçte açıldığında veriler diskte olmalı."""
    code = (
        "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); "
        "print(*[c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] "
        "for t in ('students','courses','users','messages')])"
    )
    out = subprocess.run([sys.executable, "-c", code, str(demo_path)], check=True,
                         capture_output=True, text=True).stdout.split()
    students, courses, users, messages = map(int, out)
    assert (students, courses, users) == (30, 8, 34) and messages >= 35


def test_added_grade_and_message_survive_reopen(tmp_path):
    path = tmp_path / "demo.db"
    db = open_demo(path)
    auth, grades = AuthService(db), GradeService(db)
    teacher = auth.authenticate("ogretmen1", "1234")
    course = next(c for c in CourseService(db).for_teacher(teacher.id)
                  if c.code == "BIL203")
    student = StudentService(db).add("2024999", "Test", "Öğrencisi", "Bilgisayar", "", 2)
    grade = grades.add(student.id, course.id, "Vize", "73,5", None, "10.11.2025")
    message_id = MessageService(db).send_to_course(teacher, course.id, "Kalıcılık testi",
                                                   "Bu mesaj yeniden açılışta kalmalı.")
    db.close()

    reopened = open_demo(path)  # demo bayrağı var: veriler silinmez, yeniden yüklenmez
    try:
        assert StudentService(reopened).count() == 31
        saved = GradeService(reopened).get(grade.id)
        assert saved.score == 73.5 and saved.exam_date == "2025-11-10"
        ogrenci = AuthService(reopened).authenticate("ogrenci1", "1234")
        subjects = {m.subject for m in MessageService(reopened).inbox(ogrenci)}
        assert "Kalıcılık testi" in subjects
        assert MessageService(reopened).get(teacher, message_id).body.startswith("Bu mesaj")
    finally:
        reopened.close()


def test_reset_demo_restores_original_data(tmp_path):
    path = tmp_path / "demo.db"
    db = open_demo(path)
    original = dump(db)
    original_students = db.query("SELECT student_no, first_name, last_name, department, "
                                 "email, class_year FROM students ORDER BY id")
    StudentService(db).add("2024998", "Silinecek", "Kayıt")
    db.close()

    reset = open_demo(path, "--reset-demo")
    try:
        assert StudentService(reset).count() == 30
        after = dump(reset)
        # Oluşturulma zamanı ve şifre özetleri (rastgele tuz) dışında içerik aynı olmalı.
        columns = "student_no, first_name, last_name, department, email, class_year"
        assert reset.query(f"SELECT {columns} FROM students ORDER BY id") == \
            original_students
        assert after["grades"] == original["grades"]
        assert len(after["messages"]) == len(original["messages"])
    finally:
        reset.close()


def test_reset_refuses_non_demo_database(tmp_path):
    path = tmp_path / "gercek.db"
    db = Database(path)
    StudentService(db).add("2026001", "Gerçek", "Öğrenci")
    db.close()
    with pytest.raises(ValidationError, match="demo veritabanı değil"):
        open_demo(path, "--reset-demo")
    db = Database(path)
    assert StudentService(db).count() == 1  # dokunulmadı
    db.close()


def test_demo_refuses_database_with_real_data(db, student_service):
    student_service.add("2026001", "Gerçek", "Öğrenci")
    with pytest.raises(ValidationError, match="ayrı bir veritabanına"):
        load_demo_data(db)
    assert student_service.count() == 1


def test_main_refuses_demo_on_real_database(capsys):
    assert main.main(["--demo", "--db", str(DEFAULT_DB_PATH)]) == 2
    assert main.main(["--demo", "--db", str(DEFAULT_DB_PATH), "--reset-demo"]) == 2
    assert main.main(["--reset-demo"]) == 2
    assert main.main(["--real", "--db", str(DEFAULT_DB_PATH)]) == 2
    with pytest.raises(SystemExit):
        main.build_parser().parse_args(["--demo", "--real"])
    assert "gerçek veritabanına" in capsys.readouterr().err


def test_main_demo_defaults_to_demo_db():
    args = main.build_parser().parse_args(["--demo"])
    assert main.resolve_db_path(args) == str(DEMO_DB_PATH)
    args = main.build_parser().parse_args([])  # seçeneksiz çalıştırma demo açar
    assert main.resolve_db_path(args) == str(DEMO_DB_PATH)
    args = main.build_parser().parse_args(["--real"])
    assert main.resolve_db_path(args) == str(DEFAULT_DB_PATH)


def test_relative_db_path_resolves_from_project_folder(tmp_path, monkeypatch):
    """Göreli --db yolu, çalışma klasöründen bağımsız olarak proje klasörüne göre çözülür."""
    monkeypatch.chdir(tmp_path)
    args = main.build_parser().parse_args(["--demo", "--db", "data/demo.db"])
    assert Path(main.resolve_db_path(args)) == DEMO_DB_PATH
    absolute = tmp_path / "baska.db"
    args = main.build_parser().parse_args(["--db", str(absolute)])
    assert main.resolve_db_path(args) == str(absolute)


# --------------------------------------------- arayüz üzerinden kalıcılık
def _tk_available() -> bool:
    try:
        import tkinter  # pylint: disable=import-outside-toplevel

        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # pylint: disable=broad-except  # noqa: BLE001
        return False


@pytest.mark.skipif(not _tk_available(), reason="Ekran (Tk) yok")
def test_ui_changes_survive_full_restart(tmp_path):
    """Arayüzden not ve mesaj ekle, pencereyi kapat, yeniden aç: hâlâ orada olmalı."""
    from app.ui.app_window import AppWindow  # pylint: disable=import-outside-toplevel
    from app.ui.messages import ComposeDialog  # pylint: disable=import-outside-toplevel

    path = tmp_path / "demo.db"
    window = AppWindow(open_demo(path), db_path=str(path))
    window.withdraw()
    window.login(window.auth_service.authenticate("ogretmen1", "1234"))
    flow = window.grades_tab
    window.show_page("grades")
    picker = flow.pages["courses"]
    picker.tree.selection_set(next(i for i, c in picker.courses.items() if c.code == "BIL304"))
    picker.open()
    flow.pages["students"].edit()
    editor = flow.pages["student"]
    student = flow.student
    editor.exam_var.set("Final")
    editor._load_exam()  # pylint: disable=protected-access
    editor.score_var.set("88")
    editor.date_var.set("10.06.2026")
    editor.save()
    window.show_page("messages")
    dialog = ComposeDialog(window.messages_tab, window)
    dialog.kind.set("course")
    dialog._load_targets()  # pylint: disable=protected-access
    dialog.target.set(next(v for v in dialog.target_combo["values"] if "BIL304" in v))
    dialog.subject.set("Arayüz kalıcılık testi")
    dialog.body.insert("1.0", "Kapatıp açınca kaybolmamalı.")
    dialog.submit()
    window._on_close()  # pylint: disable=protected-access  # uygulamayı tamamen kapat

    window = AppWindow(open_demo(path), db_path=str(path))
    window.withdraw()
    try:
        grades = window.grade_service.list_by_student(student.id)
        final = next(g for g in grades if g.course_code == "BIL304" and g.exam_type == "Final")
        assert final.score == 88.0
        user = window.auth_service.authenticate("ogretmen1", "1234")
        assert any(m.subject == "Arayüz kalıcılık testi"
                   for m in window.message_service.sent(user))
    finally:
        window._on_close()  # pylint: disable=protected-access
