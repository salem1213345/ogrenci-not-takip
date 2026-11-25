"""Öğrenci portalı: sol kenar çubuğu ve öğrenciye yönelik ekranlar."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.errors import AppError
from app.grading import format_score
from app.ui.common import clear_tree, make_tree, show_error
from app.ui.messages import MessagesView
from app.ui.theme import (
    badge,
    grid_card,
    section_header,
    stat_card,
    status_tone,
)

MENU = (
    ("home", "Ana Sayfa"),
    ("courses", "Derslerim"),
    ("grades", "Notlarım"),
    ("gpa", "Not Ortalamam"),
    ("office", "Ofis Saatleri"),
    ("messages", "Mesajlar"),
)


class _StudentScreen(ttk.Frame):
    def __init__(self, parent, portal):
        super().__init__(parent, style="TFrame", padding=(24, 16))
        self.portal = portal
        self.app = portal.app
        self.columnconfigure(0, weight=1)

    def refresh(self) -> None:
        pass


class StudentHome(_StudentScreen):
    """Karne özeti, ders ilerlemesi ve yaklaşan sınavlar."""

    def __init__(self, parent, portal):
        super().__init__(parent, portal)
        self.rowconfigure(2, weight=1)
        self._build()

    def _build(self) -> None:
        self.hero = grid_card(self, 0, 0, sticky="ew", pady=(0, 16))
        self.hero.columnconfigure(0, weight=1)
        self.welcome = ttk.Label(self.hero, text="Merhaba", style="HeroCard.TLabel")
        self.welcome.pack(anchor="w")
        self.hero_note = ttk.Label(self.hero, text="Ders ve not durumunuz aşağıda.",
                                   style="CardMuted.TLabel")
        self.hero_note.pack(anchor="w", pady=(2, 0))

        self.stats = ttk.Frame(self)
        self.stats.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for index in range(4):
            self.stats.columnconfigure(index, weight=1, uniform="student-stat")
        self.stat_widgets = [
            stat_card(self.stats, "Genel Not Ortalaması", "-", "4'lük sistem", "primary"),
            stat_card(self.stats, "Toplam Kredi", "-", "Not girilen dersler", "primary"),
            stat_card(self.stats, "Geçilen Ders", "-", "Başarıyla tamamlandı", "primary"),
            stat_card(self.stats, "Kalan Ders", "-", "Tekrar gerekiyor", "primary"),
        ]
        for index, widget in enumerate(self.stat_widgets):
            widget.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 10, 0))

        lower = ttk.Frame(self)
        lower.grid(row=2, column=0, sticky="nsew")
        lower.columnconfigure(0, weight=3, uniform="student-lower")
        lower.columnconfigure(1, weight=2, uniform="student-lower")
        lower.rowconfigure(0, weight=1)

        courses = grid_card(lower, 0, 0, sticky="nsew", padx=(0, 10))
        courses.columnconfigure(0, weight=1)
        courses.rowconfigure(1, weight=1)
        section_header(courses, "Derslerim", "Ders bazlı ağırlıklı ortalama").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        container, self.course_tree = make_tree(
            courses,
            (("course", "Ders", 170, "w"), ("avg", "Ortalama", 80, "center"),
             ("letter", "Harf", 60, "center"), ("state", "Durum", 80, "center")),
            height=7,
        )
        container.grid(row=1, column=0, sticky="nsew")

        upcoming = grid_card(lower, 0, 1, sticky="nsew")
        upcoming.columnconfigure(0, weight=1)
        section_header(upcoming, "Son Notlar", "Girilen sınav notları").pack(anchor="w")
        self.recent_box = ttk.Frame(upcoming, style="Card.TFrame")
        self.recent_box.pack(fill="both", expand=True, pady=(10, 0))
        self.recent_box.columnconfigure(0, weight=1)

    def refresh(self) -> None:
        report = self.portal.report()
        student = report.student if report else None
        self.welcome.configure(text=f"Merhaba, {student.first_name}" if student else "Merhaba")
        self.hero_note.configure(
            text=f"{student.student_no} · {student.department}" if student else "Öğrenci seçilmedi"
        )
        values = (
            format_score(report.gpa) if report else "-",
            str(report.total_credit) if report else "-",
            str(sum(1 for course in report.courses if course.passed)) if report else "-",
            str(report.failed_count) if report else "-",
        )
        for widget, value in zip(self.stat_widgets, values):
            widget.value_label.configure(text=value)

        clear_tree(self.course_tree)
        for child in self.recent_box.winfo_children():
            child.destroy()
        if report is None:
            return
        for course in report.courses:
            self.course_tree.insert(
                "", "end",
                values=(f"{course.course_code} - {course.course_name}",
                        format_score(course.average), course.letter, course.status),
                tags=(status_tone(course.status),),
            )
        self.course_tree.tag_configure("success", foreground="#14532D")
        self.course_tree.tag_configure("danger", foreground="#93000A")

        # list_by_student ders koduna göre sıralı döner; "Son Notlar" için tarihe göre sırala.
        grades = sorted(
            self.portal.grades(), key=lambda grade: (grade.exam_date, grade.id), reverse=True
        )[:5]
        for grade in reversed(grades):
            row = ttk.Frame(self.recent_box, style="Card.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=f"{grade.course_code} · {grade.exam_type}",
                      style="Card.TLabel").pack(side="left")
            tone = status_tone("Geçti" if grade.score >= 60 else "Kaldı")
            badge(row, format_score(grade.score), tone).pack(side="right")


class StudentCourses(_StudentScreen):
    """Ders listesi ve ders bilgileri."""

    COLUMNS = (
        ("code", "Ders Kodu", 100, "w"),
        ("name", "Ders Adı", 250, "w"),
        ("credit", "Kredi", 70, "center"),
        ("teacher", "Öğretim Görevlisi", 220, "w"),
        ("term", "Dönem", 120, "w"),
    )

    def __init__(self, parent, portal):
        super().__init__(parent, portal)
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.rowconfigure(2, weight=1)
        self._build()
        self.search_var.trace_add("write", lambda *_: self.refresh())

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Derslerim", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.count_var, style="Muted.TLabel").pack(side="right")

        toolbar = grid_card(self, 1, 0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Ara", style="CardMuted.TLabel").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(toolbar, textvariable=self.search_var).grid(row=0, column=1, sticky="ew")

        holder = grid_card(self, 2, 0, sticky="nsew")
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(1, weight=1)
        section_header(holder, "Kayıtlı Dersler", "Dönem ve öğretim görevlisi bilgileri").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        container, self.tree = make_tree(holder, self.COLUMNS, height=14)
        container.grid(row=1, column=0, sticky="nsew")

    def refresh(self) -> None:
        courses = self.portal.courses()
        needle = self.search_var.get().strip().casefold()
        if needle:
            courses = [c for c in courses if needle in f"{c.code} {c.name}".casefold()]
        clear_tree(self.tree)
        for course in courses:
            self.tree.insert(
                "", "end",
                values=(course.code, course.name, course.credit,
                        course.instructor, course.semester),
            )
        self.count_var.set(f"{len(courses)} ders")


class StudentGrades(_StudentScreen):
    """Öğrencinin tüm sınav notları."""

    COLUMNS = (
        ("course", "Ders", 250, "w"),
        ("exam", "Sınav Türü", 100, "center"),
        ("score", "Puan", 80, "center"),
        ("weight", "Ağırlık", 80, "center"),
        ("date", "Tarih", 110, "center"),
    )

    def __init__(self, parent, portal):
        super().__init__(parent, portal)
        self.exam_var = tk.StringVar(value="Tümü")
        self.count_var = tk.StringVar()
        self.rowconfigure(2, weight=1)
        self._build()
        self.exam_var.trace_add("write", lambda *_: self.refresh())

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Notlarım", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.count_var, style="Muted.TLabel").pack(side="right")

        toolbar = grid_card(self, 1, 0, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="Sınav Türü",
                  style="CardMuted.TLabel").pack(side="left", padx=(0, 8))
        ttk.Combobox(toolbar, textvariable=self.exam_var,
                     values=("Tümü", "Vize", "Final", "Ödev", "Proje"),
                     state="readonly", width=16).pack(side="left")

        holder = grid_card(self, 2, 0, sticky="nsew")
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(1, weight=1)
        section_header(holder, "Sınav Sonuçları", "Ders ve sınav bazında notlar").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        container, self.tree = make_tree(holder, self.COLUMNS, height=14)
        container.grid(row=1, column=0, sticky="nsew")

    def refresh(self) -> None:
        grades = self.portal.grades()
        if self.exam_var.get() != "Tümü":
            grades = [grade for grade in grades if grade.exam_type == self.exam_var.get()]
        clear_tree(self.tree)
        for grade in grades:
            self.tree.insert(
                "", "end",
                values=(f"{grade.course_code} - {grade.course_name}", grade.exam_type,
                        format_score(grade.score), format_score(grade.weight, 0), grade.exam_date),
                tags=(status_tone("Geçti" if grade.score >= 60 else "Kaldı"),),
            )
        self.tree.tag_configure("success", foreground="#14532D")
        self.tree.tag_configure("danger", foreground="#93000A")
        self.count_var.set(f"{len(grades)} not")


class StudentGPA(_StudentScreen):
    """Not ortalaması ve ders bazında harf notları."""

    def __init__(self, parent, portal):
        super().__init__(parent, portal)
        self.rowconfigure(2, weight=1)
        self._build()

    def _build(self) -> None:
        self.hero = grid_card(self, 0, 0, sticky="ew", pady=(0, 16))
        self.hero.columnconfigure(0, weight=1)
        self.gpa_label = ttk.Label(self.hero, text="Genel Not Ortalamam", style="CardMuted.TLabel")
        self.gpa_label.pack(anchor="w")
        self.gpa_value = ttk.Label(self.hero, text="-", style="HeroCard.TLabel")
        self.gpa_value.pack(anchor="w", pady=(2, 6))
        self.gpa_note = ttk.Label(self.hero, text="", style="CardMuted.TLabel")
        self.gpa_note.pack(anchor="w")

        holder = grid_card(self, 2, 0, sticky="nsew")
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(2, weight=1)
        section_header(holder, "Ders Bazında Durum", "Ağırlıklı ortalama ve harf notu").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        columns = (("course", "Ders", 230, "w"), ("avg", "Ortalama", 80, "center"),
                   ("point", "Katsayı", 70, "center"), ("letter", "Harf", 60, "center"),
                   ("state", "Durum", 80, "center"))
        container, self.tree = make_tree(holder, columns, height=12)
        container.grid(row=2, column=0, sticky="nsew")

    def refresh(self) -> None:
        report = self.portal.report()
        if report is None:
            self.gpa_value.configure(text="-")
            self.gpa_note.configure(text="Öğrenci seçilmedi")
            clear_tree(self.tree)
            return
        self.gpa_value.configure(text=format_score(report.gpa))
        self.gpa_note.configure(
            text=f"Toplam kredi: {report.total_credit}  ·  Durum: {report.status}"
        )
        clear_tree(self.tree)
        for course in report.courses:
            self.tree.insert(
                "", "end",
                values=(f"{course.course_code} - {course.course_name}",
                        format_score(course.average), format_score(course.point, 2),
                        course.letter, course.status),
                tags=(status_tone(course.status),),
            )
        self.tree.tag_configure("success", foreground="#14532D")
        self.tree.tag_configure("danger", foreground="#93000A")


class StudentOfficeHours(_StudentScreen):
    """Kayıtlı olunan derslerin öğretim görevlileri ve iletişim yolu."""

    def __init__(self, parent, portal):
        super().__init__(parent, portal)
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Ofis Saatleri", style="Title.TLabel").pack(side="left")
        ttk.Label(self, text="Görüşme saati ayarlamak için dersin öğretmenine Mesajlar "
                             "ekranından yazabilirsiniz.", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(0, 10))
        self.holder = ttk.Frame(self)
        self.holder.grid(row=2, column=0, sticky="nsew")
        self.holder.columnconfigure(0, weight=1, uniform="office")
        self.holder.columnconfigure(1, weight=1, uniform="office")
        self.rowconfigure(2, weight=1)

    def refresh(self) -> None:
        for child in self.holder.winfo_children():
            child.destroy()
        teachers = {t.id: t.full_name for t in self.app.auth_service.teachers()}
        courses = self.portal.courses()
        if not courses:
            ttk.Label(self.holder, text="Kayıtlı olduğunuz ders bulunmuyor.",
                      style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        for index, course in enumerate(courses):
            column = index % 2
            card = grid_card(self.holder, index // 2, column, sticky="nsew",
                             padx=(0, 6) if column == 0 else (6, 0), pady=(0, 12))
            card.columnconfigure(0, weight=1)
            ttk.Label(card, text=course.code, style="SectionCard.TLabel").grid(
                row=0, column=0, sticky="w")
            ttk.Label(card, text=course.semester or "", style="CardMuted.TLabel").grid(
                row=0, column=1, sticky="e")
            ttk.Label(card, text=course.name, style="Card.TLabel").grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
            ttk.Label(card, text=course.instructor or "Öğretim görevlisi belirtilmemiş",
                      style="CardMuted.TLabel").grid(row=2, column=0, columnspan=2,
                                                     sticky="w", pady=(6, 0))
            contact = teachers.get(course.teacher_id)
            ttk.Label(card, text=f"Mesaj: {contact}" if contact else "Mesaj gönderilemez "
                                                                     "(sorumlu hesap yok)",
                      style="CardMuted.TLabel").grid(row=3, column=0, columnspan=2,
                                                     sticky="w", pady=(2, 0))


class StudentPortal(ttk.Frame):
    """Sol kenar çubuğu + öğrenci ekranları."""

    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app
        self.student_var = tk.StringVar()
        self.current_student_id: int | None = None

        self.sidebar = ttk.Frame(self, style="Soft.TFrame", width=256)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.main = ttk.Frame(self, style="TFrame")
        self.main.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_header()
        self._build_screens()

    # ------------------------------------------------------------- yerleşim
    def _build_sidebar(self) -> None:
        brand = ttk.Frame(self.sidebar, style="Soft.TFrame")
        brand.pack(fill="x", padx=20, pady=(24, 28))
        ttk.Label(brand, text="AKADEMİPUSULA", style="SoftSection.TLabel").pack(anchor="w")
        ttk.Label(brand, text="Öğrenci Portalı", style="SoftMuted.TLabel").pack(
            anchor="w", pady=(2, 0)
        )

        self.nav_buttons: dict[str, ttk.Button] = {}
        for key, label in MENU:
            button = ttk.Button(
                self.sidebar, text=f"  {label}", style="SideNav.TButton",
                command=lambda item=key: self.show(item),
            )
            button.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = button

        footer = ttk.Frame(self.sidebar, style="Soft.TFrame")
        footer.pack(side="bottom", fill="x", padx=14, pady=18)
        ttk.Button(footer, text="Şifremi Değiştir",
                   command=self.app._change_password).pack(  # pylint: disable=protected-access
            fill="x", pady=(0, 6))
        ttk.Button(footer, text="Çıkış Yap", command=self.app.logout).pack(fill="x")

    def _build_header(self) -> None:
        header = ttk.Frame(self.main, style="Card.TFrame", padding=(20, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Öğrenci", style="CardMuted.TLabel").pack(side="left", padx=(0, 8))
        ttk.Label(header, textvariable=self.student_var, style="Header.TLabel").pack(side="left")
        ttk.Button(header, text="Yenile (F5)", command=self.refresh_all).pack(side="right")

    def _build_screens(self) -> None:
        area = ttk.Frame(self.main, style="TFrame")
        area.pack(fill="both", expand=True)
        self.screens: dict[str, ttk.Frame] = {
            "home": StudentHome(area, self),
            "courses": StudentCourses(area, self),
            "grades": StudentGrades(area, self),
            "gpa": StudentGPA(area, self),
            "office": StudentOfficeHours(area, self),
            "messages": MessagesView(area, self.app),
        }
        for screen in self.screens.values():
            screen.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.show("home")

    # ------------------------------------------------------------- gezinme
    def show(self, key: str) -> None:
        screen = self.screens.get(key)
        if screen is None:
            return
        screen.tkraise()
        for item, button in self.nav_buttons.items():
            button.state(["selected" if item == key else "!selected"])
        screen.refresh()
        self.app.set_status(f"Öğrenci portalı · {dict(MENU)[key]}")

    def open_for(self, user) -> None:
        """Öğrenci girişinde: yalnızca bu öğrencinin verileri gösterilir."""
        self.current_student_id = user.student_id
        try:
            student = self.app.student_service.get(user.student_id)
            self.student_var.set(student.label)
        except AppError:
            self.student_var.set(user.full_name)
        self.show("home")
        self.refresh_all()

    def reset(self) -> None:
        """Çıkışta önceki öğrencinin verileri ekranda kalmaz."""
        self.current_student_id = None
        self.student_var.set("")
        self.screens["messages"].reset()
        for key, screen in self.screens.items():
            if key != "messages":
                screen.refresh()
        self.set_unread(0)

    def set_unread(self, count: int) -> None:
        label = f"  Mesajlar ({count})" if count else "  Mesajlar"
        self.nav_buttons["messages"].configure(text=label)

    def refresh_all(self) -> None:
        if self.current_student_id is None:
            return
        for screen in self.screens.values():
            screen.refresh()

    def report(self):
        if self.current_student_id is None:
            return None
        try:
            return self.app.grade_service.student_report(self.current_student_id)
        except AppError as exc:
            show_error(self, exc)
            return None

    def grades(self) -> list:
        if self.current_student_id is None:
            return []
        try:
            return self.app.grade_service.list_by_student(self.current_student_id)
        except AppError as exc:
            show_error(self, exc)
            return []

    def courses(self) -> list:
        if self.current_student_id is None:
            return []
        try:
            return self.app.enrollment_service.courses_of(self.current_student_id)
        except AppError as exc:
            show_error(self, exc)
            return []
