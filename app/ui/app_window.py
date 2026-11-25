"""Ana pencere: oturum (giriş / çıkış), öğretmen paneli ve öğrenci portalı."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app import config
from app.database import Database
from app.services import (
    AuthService,
    CourseService,
    EnrollmentService,
    GradeService,
    MessageService,
    ReportService,
    StudentService,
)
from app.ui.common import configure_styles
from app.ui.courses_tab import CoursesTab
from app.ui.dashboard import GradeReportTab, TeacherHomeTab
from app.ui.dialogs import ChangePasswordDialog, TeacherAccountDialog
from app.ui.grades_tab import GradesTab
from app.ui.login import LoginView, SetupView
from app.ui.messages import MessagesView, confirm_discard
from app.ui.reports_tab import ReportsTab
from app.ui.student_portal import StudentPortal
from app.ui.students_tab import StudentsTab
from app.ui.theme import NAVY

TEACHER_PAGES = (
    ("home", "Ana Sayfa"),
    ("courses", "Dersler"),
    ("students", "Öğrenciler"),
    ("grades", "Notlar"),
    ("report", "Not Dökümü"),
    ("reports", "Raporlar"),
    ("messages", "Mesajlar"),
)


class AppWindow(tk.Tk):
    """AkademiPusula ana penceresi."""

    def __init__(self, db: Database, db_path=None, show_login: bool = True):
        super().__init__()
        self.db = db
        self.db_path = str(db_path or db.path)

        self.student_service = StudentService(db)
        self.course_service = CourseService(db)
        self.grade_service = GradeService(db)
        self.report_service = ReportService(self.student_service, self.grade_service)
        self.auth_service = AuthService(db)
        self.enrollment_service = EnrollmentService(db)
        self.message_service = MessageService(db)

        self.current_user = None
        self.title(f"AkademiPusula  ·  {config.APP_NAME}")
        self.geometry("1200x760")
        self.minsize(1000, 660)
        self._set_icon()
        configure_styles(self)

        self.status_var = tk.StringVar(value="Hazır")
        self.user_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", anchor="w").pack(
            side="bottom", fill="x")
        self.workspace = ttk.Frame(self)
        self.workspace.pack(fill="both", expand=True)
        self._build_teacher_view()
        self.student_view = StudentPortal(self.workspace, self)
        self.login_view = LoginView(self.workspace, self)
        self.setup_view = SetupView(self.workspace, self)
        self.bind("<F5>", lambda _e: self.refresh_all())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if show_login or not self.auth_service.has_teacher():
            self.show_entry()
        else:
            # Araçlar (ekran görüntüsü vb.) için: ilk öğretmenle doğrudan oturum aç.
            self.login(self.auth_service.teachers()[0])

    # -------------------------------------------------------------- görünüm
    def _set_icon(self) -> None:
        assets = config.BASE_DIR / "assets"
        self._icon_image = None
        if (assets / "app_icon.ico").is_file():
            try:
                self.iconbitmap(default=str(assets / "app_icon.ico"))
            except tk.TclError:
                pass
        if (assets / "app_icon.png").is_file():
            try:
                self._icon_image = tk.PhotoImage(file=str(assets / "app_icon.png"))
                self.iconphoto(True, self._icon_image)
            except tk.TclError:
                self._icon_image = None

    def _build_teacher_view(self) -> None:
        self.teacher_view = ttk.Frame(self.workspace)
        header = ttk.Frame(self.teacher_view, style="Card.TFrame", padding=(14, 8))
        header.pack(side="top", fill="x")
        brand = ttk.Frame(header, style="Card.TFrame")
        brand.pack(side="left")
        tk.Frame(brand, background=NAVY, width=6, height=28).pack(side="left")
        ttk.Label(brand, text="AkademiPusula", style="Brand.TLabel").pack(side="left",
                                                                          padx=(9, 0))
        # Sağ grup menüden önce yerleşir; dar pencerede "Çıkış Yap" görünür kalır.
        right = ttk.Frame(header, style="Card.TFrame")
        right.pack(side="right")
        ttk.Label(right, textvariable=self.user_var, style="BrandMuted.TLabel").pack(
            side="left", padx=(0, 12))
        ttk.Button(right, text="Çıkış Yap", command=self.logout).pack(side="left")
        navigation = ttk.Frame(header, style="Card.TFrame")
        navigation.pack(side="left", padx=(14, 0))
        self.teacher_nav_buttons: dict[str, ttk.Button] = {}
        for key, label in TEACHER_PAGES:
            button = ttk.Button(navigation, text=label, style="TopNav.TButton",
                                command=lambda page=key: self.show_page(page))
            button.pack(side="left")
            self.teacher_nav_buttons[key] = button

        self.notebook = ttk.Notebook(self.teacher_view, style="Hidden.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(4, 10))
        self.home_tab = TeacherHomeTab(self.notebook, self)
        self.students_tab = StudentsTab(self.notebook, self)
        self.courses_tab = CoursesTab(self.notebook, self)
        self.grades_tab = GradesTab(self.notebook, self)
        self.report_tab = GradeReportTab(self.notebook, self)
        self.reports_tab = ReportsTab(self.notebook, self)
        self.messages_tab = MessagesView(self.notebook, self)
        self.teacher_pages = {
            "home": self.home_tab,
            "students": self.students_tab,
            "courses": self.courses_tab,
            "grades": self.grades_tab,
            "report": self.report_tab,
            "reports": self.reports_tab,
            "messages": self.messages_tab,
        }
        for page in self.teacher_pages.values():
            self.notebook.add(page)

    def _show_view(self, view: ttk.Frame) -> None:
        for item in (self.login_view, self.setup_view, self.teacher_view, self.student_view):
            item.pack_forget()
        view.pack(fill="both", expand=True)

    # --------------------------------------------------------------- oturum
    def show_entry(self) -> None:
        """Öğretmen hesabı yoksa ilk kurulum, varsa giriş ekranı."""
        self.current_user = None
        configure_styles(self)
        self._build_menu()
        if self.auth_service.has_teacher():
            self._show_view(self.login_view)
            self.login_view.reset()
            self.title(f"AkademiPusula  ·  {config.APP_NAME}  ·  Giriş")
            self.set_status("Kullanıcı adınız ve şifrenizle giriş yapın.")
        else:
            self._show_view(self.setup_view)
            self.title(f"AkademiPusula  ·  {config.APP_NAME}  ·  İlk Kurulum")
            self.set_status("İlk öğretmen hesabını oluşturun.")

    def login(self, user) -> None:
        self.current_user = user
        role = "Öğretmen" if user.is_teacher else "Öğrenci"
        self.user_var.set(f"{user.full_name}  ·  {role}")
        configure_styles(self, user.role)
        self._build_menu()
        if user.is_teacher:
            self._show_view(self.teacher_view)
            self.title(f"AkademiPusula  ·  Öğretmen Paneli  ·  {user.full_name}")
            self.show_page("home")
        else:
            self._show_view(self.student_view)
            self.title(f"AkademiPusula  ·  Öğrenci Portalı  ·  {user.full_name}")
            self.student_view.open_for(user)
        self.update_unread()
        self.set_status(f"Hoş geldiniz, {user.full_name}.")

    def logout(self) -> None:
        """Oturumu kapatır: kullanıcı bilgisi ve ekran durumları temizlenir."""
        if self.current_user is None:
            return
        sheet = self.grades_tab.pages["sheet"]
        if self.grades_tab.step == "sheet" and sheet.is_dirty() and not confirm_discard(self):
            return
        name = self.current_user.full_name
        self.current_user = None
        self.user_var.set("")
        self.grades_tab.reset()
        self.messages_tab.reset()
        self.student_view.reset()
        self.students_tab.reset()
        self.courses_tab.reset()
        self.show_entry()
        self.set_status(f"{name} oturumu kapatıldı.")

    # -------------------------------------------------------------- gezinme
    def _mark_nav(self, key: str) -> None:
        for item, button in self.teacher_nav_buttons.items():
            button.state(["selected" if item == key else "!selected"])

    def _current_teacher_page(self) -> ttk.Frame:
        current = self.notebook.select()
        return next((page for page in self.teacher_pages.values()
                     if str(page) == str(current)), self.home_tab)

    def show_page(self, key: str) -> None:
        page = self.teacher_pages.get(key)
        if page is None or self.current_user is None or not self.current_user.is_teacher:
            return
        if self.grades_tab.step == "sheet" and page is not self.grades_tab \
                and self.grades_tab.pages["sheet"].is_dirty() and not confirm_discard(self):
            return
        if page is not self.grades_tab and self.grades_tab.step == "sheet":
            self.grades_tab.pages["sheet"].discard()
        self.notebook.select(page)
        self._mark_nav(key)
        page.refresh()
        self.set_status(f"Öğretmen Paneli · {dict(TEACHER_PAGES)[key]}")

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def refresh_all(self) -> None:
        """Görünen ekranı yeniler; gizli ekranlar açıldıklarında kendilerini yeniler."""
        user = self.current_user
        if user is None:
            return
        if user.is_student:
            self.student_view.refresh_all()
        else:
            self._current_teacher_page().refresh()
        self.update_unread()

    def notify_change(self, message: str) -> None:
        self.refresh_all()
        self.set_status(message)

    def update_unread(self) -> None:
        user = self.current_user
        if user is None:
            return
        count = self.message_service.unread_count(user)
        label = f"Mesajlar ({count})" if count else "Mesajlar"
        if user.is_teacher:
            self.teacher_nav_buttons["messages"].configure(text=label)
        else:
            self.student_view.set_unread(count)

    # ---------------------------------------------------------------- menü
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        user = self.current_user
        file_menu = tk.Menu(menubar, tearoff=0)
        if user is not None and user.is_teacher:
            file_menu.add_command(label="Veritabanını Yedekle...", command=self._backup_database)
            file_menu.add_separator()
        file_menu.add_command(label="Uygulamayı Kapat", command=self._on_close)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        if user is not None:
            account = tk.Menu(menubar, tearoff=0)
            if user.is_teacher:
                account.add_command(label="Öğretmen Hesabı Ekle...",
                                    command=self._add_teacher_account)
            account.add_command(label="Şifremi Değiştir...", command=self._change_password)
            account.add_separator()
            account.add_command(label="Çıkış Yap", command=self.logout)
            menubar.add_cascade(label="Hesap", menu=account)
            view_menu = tk.Menu(menubar, tearoff=0)
            view_menu.add_command(label="Yenile (F5)", command=self.refresh_all)
            menubar.add_cascade(label="Görünüm", menu=view_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Hakkında", command=self._show_about)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        self.configure(menu=menubar)

    def _change_password(self) -> None:
        dialog = ChangePasswordDialog(self, self.auth_service, self.current_user)
        self.wait_window(dialog)
        if dialog.result:
            self.set_status("Şifreniz değiştirildi.")

    def _add_teacher_account(self) -> None:
        dialog = TeacherAccountDialog(self, self.auth_service)
        self.wait_window(dialog)
        if dialog.result:
            self.set_status(f"Öğretmen hesabı oluşturuldu: {dialog.result.username}")
            self.courses_tab.refresh()

    def _backup_database(self) -> None:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Veritabanını yedekle",
            initialdir=str(config.DATA_DIR),
            initialfile=f"notlar_yedek_{date.today():%Y%m%d}.db",
            defaultextension=".db",
            filetypes=[("SQLite veritabanı", "*.db"), ("Tüm dosyalar", "*.*")],
        )
        if not path:
            return
        try:
            target = sqlite3.connect(str(Path(path)))
            with target:
                self.db.connection.backup(target)
            target.close()
        except (sqlite3.Error, OSError) as exc:
            messagebox.showerror("Yedekleme başarısız", str(exc), parent=self)
            return
        self.set_status(f"Yedek kaydedildi: {path}")
        messagebox.showinfo("Yedek hazır", f"Veritabanı yedeklendi:\n{path}", parent=self)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Hakkında",
            f"AkademiPusula  ·  {config.APP_NAME}\n\n"
            f"Sürüm {config.APP_VERSION}\n"
            "Python + Tkinter + SQLite\n"
            "PDF: fpdf2   |   CSV: csv modülü   |   Test: pytest\n\n"
            "Not kuralı: ağırlıklı ortalama, 60 puan ve üzeri geçer (DD).",
            parent=self,
        )

    def _on_close(self) -> None:
        if self.grades_tab.step == "sheet" and self.grades_tab.pages["sheet"].is_dirty() \
                and not confirm_discard(self):
            return
        self.db.close()
        self.destroy()
