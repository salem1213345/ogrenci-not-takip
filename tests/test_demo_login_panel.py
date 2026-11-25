"""Giriş ekranındaki "Demo Hesapları" paneli: hesaplar gerçek mi, yalnızca demoda mı?"""

import shutil

import pytest

import main
from app.config import DEMO_DB_PATH
from app.database import Database
from app.demo_data import demo_accounts, load_demo_data
from app.services.auth_service import AuthService


def open_demo(path) -> Database:
    args = main.build_parser().parse_args(["--demo", "--db", str(path)])
    return main.prepare_database(args)


@pytest.fixture(scope="module")
def demo_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("panel") / "demo.db"
    open_demo(path).close()
    return path


@pytest.fixture()
def demo_db(tmp_path, demo_path):
    """Her test için demo veritabanının taze bir kopyası."""
    copy = tmp_path / "demo.db"
    shutil.copy(demo_path, copy)
    database = Database(copy)
    yield database
    database.close()


def _assert_all_log_in(db, accounts):
    auth = AuthService(db)
    for account in accounts:
        user = auth.authenticate(account.username, account.password)
        assert user.username == account.username
        assert user.role == account.role
        assert user.full_name == account.full_name
        if account.role == "student":
            assert user.student_id


# ------------------------------------------------------------------ veri
def test_every_shown_account_logs_in_with_shown_password(demo_db):
    accounts = demo_accounts(demo_db)
    assert [a.username for a in accounts] == [
        "ogretmen1", "ogretmen2", "ogretmen3", "ogretmen4",
        "ogrenci1", "ogrenci2", "ogrenci3", "ogrenci4", "ogrenci5"]
    _assert_all_log_in(demo_db, accounts)


@pytest.mark.skipif(not DEMO_DB_PATH.is_file(), reason="data/demo.db yok")
def test_accounts_in_project_demo_db_log_in(tmp_path):
    """Projedeki gerçek data/demo.db dosyasında (kopyası üzerinde) panelde
    gösterilen her hesap, gösterilen şifreyle giriş yapabilmelidir."""
    copy = tmp_path / "demo.db"
    shutil.copy(DEMO_DB_PATH, copy)
    database = Database(copy)
    try:
        accounts = demo_accounts(database)
        assert {a.role for a in accounts} == {"teacher", "student"}
        assert 1 <= sum(a.role == "teacher" for a in accounts) <= 4
        assert 1 <= sum(a.role == "student" for a in accounts) <= 5
        _assert_all_log_in(database, accounts)
    finally:
        database.close()


def test_accounts_come_from_database_not_hardcoded(demo_db):
    """Veritabanında değişen hesaplar panele yansır: şifresi değiştirilen hesap
    gösterilmez, yerine sıradaki geçerli hesap gelir."""
    auth = AuthService(demo_db)
    teacher = auth.authenticate("ogretmen2", "1234")
    auth.change_password(teacher.id, "1234", "YeniSifre123")
    demo_db.run("DELETE FROM users WHERE username = 'ogrenci1'")
    names = [a.username for a in demo_accounts(demo_db)]
    assert "ogretmen2" not in names and "ogrenci1" not in names
    assert names == ["ogretmen1", "ogretmen3", "ogretmen4",
                     "ogrenci2", "ogrenci3", "ogrenci4", "ogrenci5", "ogrenci6"]
    _assert_all_log_in(demo_db, demo_accounts(demo_db))


def test_listing_does_not_touch_last_login(demo_db):
    demo_accounts(demo_db)
    row = demo_db.query_one("SELECT COUNT(*) AS n FROM users WHERE last_login IS NOT NULL")
    assert row["n"] == 0


def test_no_accounts_for_non_demo_database(db):
    """Gerçek (demo olmayan) veritabanında, şifresi 1234 olan hesap olsa bile boş."""
    AuthService(db).create_teacher("ogretmen1", "Gerçek Öğretmen", "1234",
                                   enforce_policy=False)
    assert not demo_accounts(db)


# --------------------------------------------------------------- arayüz
def _tk_available() -> bool:
    try:
        import tkinter  # pylint: disable=import-outside-toplevel

        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # pylint: disable=broad-except  # noqa: BLE001
        return False


needs_tk = pytest.mark.skipif(not _tk_available(), reason="Ekran (Tk) yok")


def _window(db, path):
    from app.ui.app_window import AppWindow  # pylint: disable=import-outside-toplevel

    window = AppWindow(db, db_path=str(path))
    window.withdraw()
    window.update_idletasks()
    return window


@needs_tk
def test_panel_click_fills_fields_and_enter_logs_in(tmp_path, demo_path):
    path = tmp_path / "demo.db"
    shutil.copy(demo_path, path)
    window = _window(open_demo(path), path)
    window.deiconify()  # klavye olayları (Enter) odaklı, görünür pencereye gider
    try:
        view = window.login_view
        panel = view.demo_panel
        assert panel is not None
        assert list(panel.rows) == [a.username for a in demo_accounts(window.db)]
        for username, role in (("ogretmen1", "teacher"), ("ogrenci3", "student")):
            panel.pick(panel.rows[username].account)
            assert view.username.get() == username
            assert view.password.get() == "1234"
            window.focus_force()
            window.update()
            view.pass_entry.focus_force()
            window.update()
            assert window.focus_get() is view.pass_entry  # tıklamadan sonra odak şifrede
            view.pass_entry.event_generate("<Return>")
            window.update()
            assert window.current_user is not None
            assert window.current_user.username == username
            assert window.current_user.role == role
            window.logout()
            assert window.current_user is None
        panel.copy(panel.rows["ogrenci2"].account)
        assert window.clipboard_get() == "ogrenci2\t1234"
    finally:
        window._on_close()  # pylint: disable=protected-access


@needs_tk
def test_panel_hidden_on_real_database(tmp_path):
    path = tmp_path / "notlar.db"
    db = Database(path)
    AuthService(db).create_teacher("ogretmen1", "Gerçek Öğretmen", "Guclu.Sifre123")
    window = _window(db, path)
    try:
        assert window.login_view.demo_panel is None
    finally:
        window._on_close()  # pylint: disable=protected-access


def test_load_demo_data_is_needed_for_panel(db):
    """Boş veritabanı panel göstermez; demo verisi yüklenince gösterir."""
    assert not demo_accounts(db)
    load_demo_data(db)
    assert len(demo_accounts(db)) == 9
