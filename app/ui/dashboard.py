"""Öğretmen paneli ekranları: Ana Sayfa ve Not Dökümü."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app import config
from app.errors import AppError
from app.grading import format_score
from app.ui.common import clear_tree, make_tree, show_error
from app.ui.theme import grid_card, section_header, stat_card, status_tone


def _today() -> str:
    months = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    today = date.today()
    return f"{today.day} {months[today.month - 1]} {today.year}"


class TeacherHomeTab(ttk.Frame):
    """Öğretmen ana sayfası: özet kartları ve hızlı işlemler."""

    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame", padding=(24, 16))
        self.app = app
        self.columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        # Karşılama kartı: metinler solda, hızlı işlemler sağda (dikey alan tablolara kalır).
        hero = grid_card(self, 0, 0, sticky="ew", pady=(0, 14))
        hero.columnconfigure(0, weight=1)
        texts = ttk.Frame(hero, style="Card.TFrame")
        texts.grid(row=0, column=0, sticky="w")
        ttk.Label(texts, text="Öğretmen Paneli", style="CardMuted.TLabel").pack(anchor="w")
        ttk.Label(texts, text="Akademik duruma genel bakış", style="HeroCard.TLabel").pack(
            anchor="w", pady=(2, 4)
        )
        ttk.Label(
            texts,
            text=f"{_today()}  ·  Not kayıtlarınız güncel.",
            style="CardMuted.TLabel",
        ).pack(anchor="w")
        actions = ttk.Frame(hero, style="Card.TFrame")
        actions.grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="Not Dökümü Oluştur", style="Accent.TButton",
                   command=lambda: self.app.show_page("report")).pack(side="left")
        ttk.Button(actions, text="Yeni Not Gir", command=lambda: self.app.show_page("grades")).pack(
            side="left", padx=(8, 0)
        )

        stats = ttk.Frame(self)
        stats.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for index in range(4):
            stats.columnconfigure(index, weight=1, uniform="stat")
        # Tüm değerler oturumdaki öğretmenin derslerinden hesaplanır.
        self.stat_widgets = [
            stat_card(stats, "Öğrenci", "-", "Derslerinize kayıtlı", "primary"),
            stat_card(stats, "Ders", "-", "Sorumlu olduğunuz", "primary"),
            stat_card(stats, "Not Kaydı", "-", "Derslerinizde girilen", "primary"),
            stat_card(stats, "Ortalama GNO", "-", "4'lük sistem", "primary"),
        ]
        for index, widget in enumerate(self.stat_widgets):
            widget.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 10, 0))

        lower = ttk.Frame(self)
        lower.grid(row=2, column=0, sticky="nsew")
        lower.columnconfigure(0, weight=3, uniform="lower")
        lower.columnconfigure(1, weight=2, uniform="lower")
        lower.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        courses = grid_card(lower, 0, 0, sticky="nsew", padx=(0, 10))
        courses.columnconfigure(0, weight=1)
        courses.rowconfigure(1, weight=1)
        section_header(courses, "Derslerim", "Sorumlu olduğunuz dersler").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        self.course_columns = (
            ("code", "Kod", 80, "w"),
            ("name", "Ders Adı", 220, "w"),
            ("semester", "Dönem", 100, "w"),
            ("count", "Öğrenci", 70, "center"),
        )
        holder, self.course_tree = make_tree(courses, self.course_columns, height=7)
        holder.grid(row=1, column=0, sticky="nsew")

        activity = grid_card(lower, 0, 1, sticky="nsew")
        activity.columnconfigure(0, weight=1)
        activity.rowconfigure(1, weight=1)
        section_header(activity, "Son Notlar", "Derslerinizde en son girilen notlar").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        recent_columns = (
            ("course", "Ders", 80, "w"),
            ("student", "Öğrenci", 130, "w"),
            ("exam", "Sınav", 60, "center"),
            ("score", "Puan", 60, "center"),
        )
        holder, self.recent_tree = make_tree(activity, recent_columns, height=7)
        holder.grid(row=1, column=0, sticky="nsew")

    def refresh(self) -> None:
        user = self.app.current_user
        if user is None:
            return
        try:
            stats = self.app.grade_service.teacher_stats(user.id)
            courses = self.app.course_service.for_teacher(user.id)
            counts = self.app.enrollment_service.counts_by_course()
            recent = self.app.grade_service.recent_for_teacher(user.id, limit=8)
        except AppError as exc:
            show_error(self, exc)
            return

        values = (str(stats["students"]), str(stats["courses"]), str(stats["grades"]),
                  format_score(stats["average_gpa"]))
        for widget, value in zip(self.stat_widgets, values):
            widget.value_label.configure(text=value)

        clear_tree(self.course_tree)
        for course in courses:
            self.course_tree.insert("", "end", values=(
                course.code, course.name, course.semester or "-", counts.get(course.id, 0)))

        clear_tree(self.recent_tree)
        for row in recent:
            self.recent_tree.insert("", "end", values=(
                row["course_code"], row["student_name"], row["exam_type"],
                format_score(row["score"])))


class GradeReportTab(ttk.Frame):
    """Not dökümü: sınıf geneli özet tablosu ve dışa aktarma."""

    COLUMNS = (
        ("no", "Öğrenci No", 110, "w"),
        ("name", "Ad Soyad", 190, "w"),
        ("department", "Bölüm", 210, "w"),
        ("course", "Ders", 60, "center"),
        ("gpa", "GNO", 70, "center"),
        ("failed", "Kalan", 60, "center"),
        ("status", "Durum", 90, "center"),
    )

    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame", padding=(24, 16))
        self.app = app
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build()
        self.search_var.trace_add("write", lambda *_: self._reload())

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Not Dökümü", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.count_var, style="Muted.TLabel").pack(side="right")

        toolbar = grid_card(self, 1, 0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Ara", style="CardMuted.TLabel").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(toolbar, textvariable=self.search_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(toolbar, text="PDF Dışa Aktar", style="Accent.TButton",
                   command=lambda: self._export("pdf")).grid(row=0, column=2, padx=(10, 6))
        ttk.Button(toolbar, text="CSV Dışa Aktar",
                   command=lambda: self._export("csv")).grid(row=0, column=3)

        holder = grid_card(self, 2, 0, sticky="nsew")
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(1, weight=1)
        section_header(holder, "Sınıf Özeti", "Öğrenci bazında GNO ve başarı durumu").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        container, self.tree = make_tree(holder, self.COLUMNS, height=14)
        container.grid(row=1, column=0, sticky="nsew")

    def refresh(self) -> None:
        self._reload()

    def _reload(self) -> None:
        try:
            rows = self.app.grade_service.class_summary()
        except AppError as exc:
            show_error(self, exc)
            return
        needle = self.search_var.get().strip().casefold()
        if needle:
            rows = [row for row in rows if needle in f"{row.full_name} {row.student_no}".casefold()]
        clear_tree(self.tree)
        for row in rows:
            self.tree.insert(
                "", "end",
                values=(
                    row.student_no, row.full_name, row.department, row.course_count,
                    format_score(row.gpa), row.failed_count, row.status,
                ),
                tags=(status_tone(row.status),),
            )
        for tone, foreground in (("success", "#14532D"), ("danger", "#93000A"),
                                 ("warning", "#78350F")):
            self.tree.tag_configure(tone, foreground=foreground)
        self.count_var.set(f"{len(rows)} öğrenci")

    def _export(self, extension: str) -> None:
        config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Sınıf raporunu {extension.upper()} olarak kaydet",
            initialdir=str(config.EXPORT_DIR),
            initialfile=f"sinif_raporu_{date.today():%Y%m%d}.{extension}",
            defaultextension=f".{extension}",
            filetypes=[(f"{extension.upper()} dosyası", f"*.{extension}"), ("Tüm dosyalar", "*.*")],
        )
        if not path:
            return
        try:
            if extension == "pdf":
                target = self.app.report_service.class_pdf(Path(path))
            else:
                target = self.app.report_service.class_csv(Path(path))
        except (AppError, OSError) as exc:
            show_error(self, exc, "Rapor kaydedilemedi")
            return
        self.app.set_status(f"Rapor kaydedildi: {target}")
        messagebox.showinfo("Rapor hazır", f"Rapor kaydedildi:\n{target}", parent=self)
