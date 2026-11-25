"""Not girişi: yönlendirmeli akış.

1. Dönem / sınıf ve ders seçimi
2. Dersin öğrenci listesi (notlar, ortalama, ders kaydı)
3. Seçilen öğrencinin notunu ekleme / düzenleme
4. Toplu not girişi: dersin tüm öğrencileri tek tabloda

Her adımda "Geri" düğmesi ve tıklanabilir konum çubuğu (breadcrumb) bulunur.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from app.config import DEFAULT_WEIGHTS, EXAM_TYPES
from app.errors import AppError
from app.grading import format_score
from app.services.grade_service import SheetValidationError
from app.ui.common import clear_tree, make_tree, page_header, show_error
from app.ui.forms import DATE_FORMAT, DateField, Form, FormField, handle_errors, numeric_validator
from app.ui.messages import confirm_discard
from app.ui.theme import SURFACE, grid_card, status_tone

ALL_SEMESTERS = "Tüm dönemler"
ALL_CLASSES = "Tüm sınıflar"
STEPS = ("courses", "students", "student", "sheet")


def _class_label(value) -> str:
    return f"{value}. Sınıf" if value else "-"


def _iso_to_tr(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime(DATE_FORMAT)
    except (TypeError, ValueError):
        return value or ""


class GradesTab(ttk.Frame):
    """Öğretmenin not ekranı (adım adım)."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=(24, 16))
        self.app = app
        self.service = app.grade_service
        self.step = "courses"
        self.semester = ""
        self.class_year: int | None = None
        self.course = None
        self.student = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        page_header(self, "Notlar")
        nav = ttk.Frame(self)
        nav.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.back_button = ttk.Button(nav, text="Geri", command=self.back)
        self.back_button.pack(side="left")
        self.crumbs = ttk.Frame(nav)
        self.crumbs.pack(side="left", padx=(14, 0))

        stack = ttk.Frame(self)
        stack.grid(row=2, column=0, sticky="nsew")
        stack.columnconfigure(0, weight=1)
        stack.rowconfigure(0, weight=1)
        self.pages = {
            "courses": CoursePicker(stack, self),
            "students": CourseStudents(stack, self),
            "student": StudentGradeEditor(stack, self),
            "sheet": QuickSheet(stack, self),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.go("courses")

    # ------------------------------------------------------------- gezinme
    @property
    def teacher_id(self):
        user = self.app.current_user
        return user.id if user else None

    def go(self, step: str) -> None:
        if self.step == "sheet" and step != "sheet" and self.pages["sheet"].is_dirty():
            if not confirm_discard(self):
                return
        self.step = step
        page = self.pages[step]
        page.tkraise()
        page.refresh()
        self.back_button.state(["disabled" if step == "courses" else "!disabled"])
        self._render_crumbs()
        page.focus_first()

    def back(self) -> None:
        previous = {"students": "courses", "student": "students", "sheet": "students"}
        if self.step in previous:
            self.go(previous[self.step])

    def open_course(self, course) -> None:
        self.course = course
        self.go("students")

    def open_student(self, student) -> None:
        self.student = student
        self.go("student")

    def _render_crumbs(self) -> None:
        for child in self.crumbs.winfo_children():
            child.destroy()
        trail = [("Notlar", "courses")]
        if self.semester:
            trail[0] = ("Notlar", "courses")
            trail.append((self.semester, "courses"))
        if self.step != "courses" and self.course:
            trail.append((self.course.label, "students"))
        if self.step == "student" and self.student:
            trail.append((self.student.label, "student"))
        if self.step == "sheet":
            trail.append(("Toplu Not Girişi", "sheet"))
        for index, (text, step) in enumerate(trail):
            last = index == len(trail) - 1
            if index:
                ttk.Label(self.crumbs, text="›", style="Crumb.TLabel").pack(side="left", padx=6)
            label = ttk.Label(self.crumbs, text=text,
                              style="CrumbCurrent.TLabel" if last else "Link.TLabel",
                              cursor="" if last else "hand2")
            label.pack(side="left")
            if not last:
                label.bind("<Button-1>", lambda _e, s=step: self.go(s))

    def refresh(self) -> None:
        self.pages[self.step].refresh()

    def reset(self) -> None:
        """Oturum kapanırken: ilk adıma dön, seçimleri temizle (değişiklik sorulmaz)."""
        self.pages["sheet"].discard()
        self.semester, self.class_year, self.course, self.student = "", None, None, None
        self.pages["courses"].reset_filters()
        self.step = "courses"
        self.pages["courses"].tkraise()
        self._render_crumbs()
        self.back_button.state(["disabled"])

    def changed(self, message: str) -> None:
        self.app.set_status(message)
        self.app.update_unread()


# ===================================================================== 1. adım
class CoursePicker(ttk.Frame):
    COLUMNS = (
        ("code", "Kod", 90, "w"),
        ("name", "Ders Adı", 260, "w"),
        ("semester", "Dönem", 110, "w"),
        ("credit", "Kredi", 60, "center"),
        ("count", "Kayıtlı Öğrenci", 120, "center"),
    )

    def __init__(self, parent, flow: GradesTab):
        super().__init__(parent)
        self.flow = flow
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.semester_var = tk.StringVar(value=ALL_SEMESTERS)
        self.class_var = tk.StringVar(value=ALL_CLASSES)
        self.courses: dict[str, object] = {}

        filters = grid_card(self, 0, 0, sticky="ew", pady=(0, 12))
        ttk.Label(filters, text="1. Dönem ve ders seçin", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))
        ttk.Label(filters, text="Dönem", style="CardField.TLabel").grid(
            row=1, column=0, padx=(0, 10))
        self.semester_combo = ttk.Combobox(filters, textvariable=self.semester_var,
                                           state="readonly", width=18)
        self.semester_combo.grid(row=1, column=1)
        self.semester_combo.bind("<<ComboboxSelected>>", lambda _e: self._filter_changed())
        ttk.Label(filters, text="Sınıf", style="CardField.TLabel").grid(
            row=1, column=2, padx=(18, 10))
        self.class_combo = ttk.Combobox(
            filters, textvariable=self.class_var, state="readonly", width=14,
            values=[ALL_CLASSES] + [f"{year}. Sınıf" for year in range(1, 7)])
        self.class_combo.grid(row=1, column=3)
        self.class_combo.bind("<<ComboboxSelected>>", lambda _e: self._filter_changed())
        ttk.Label(filters, text="Yalnızca sorumlu olduğunuz dersler listelenir.",
                  style="CardMuted.TLabel").grid(row=1, column=4, sticky="e", padx=(18, 0))
        filters.columnconfigure(4, weight=1)

        listing = grid_card(self, 1, 0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        holder, self.tree = make_tree(listing, self.COLUMNS, height=10)
        holder.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _e: self.open())
        self.tree.bind("<Return>", lambda _e: self.open())
        actions = ttk.Frame(listing, style="Card.TFrame")
        actions.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(actions, text="Çift tıklayın veya Enter'a basın.",
                  style="CardMuted.TLabel").pack(side="left")
        ttk.Button(actions, text="Dersi Aç", style="Accent.TButton",
                   command=self.open).pack(side="right")

    def reset_filters(self) -> None:
        self.semester_var.set(ALL_SEMESTERS)
        self.class_var.set(ALL_CLASSES)
        clear_tree(self.tree)

    def _filter_changed(self) -> None:
        semester = self.semester_var.get()
        self.flow.semester = "" if semester == ALL_SEMESTERS else semester
        label = self.class_var.get()
        self.flow.class_year = int(label.split(".")[0]) if label != ALL_CLASSES else None
        self.refresh()
        self.flow._render_crumbs()  # pylint: disable=protected-access

    def refresh(self) -> None:
        app = self.flow.app
        try:
            semesters = app.course_service.semesters()
            courses = app.course_service.for_teacher(self.flow.teacher_id, self.flow.semester)
            counts = app.enrollment_service.counts_by_course()
        except AppError as exc:
            show_error(self, exc)
            return
        self.semester_combo["values"] = [ALL_SEMESTERS] + semesters
        selected = self.tree.selection()
        clear_tree(self.tree)
        self.courses = {}
        for course in courses:
            iid = str(course.id)
            self.tree.insert("", "end", iid=iid, values=(
                course.code, course.name, course.semester or "-", course.credit,
                counts.get(course.id, 0)))
            self.courses[iid] = course
        keep = selected[0] if selected and selected[0] in self.courses else None
        keep = keep or (str(self.flow.course.id) if self.flow.course
                        and str(self.flow.course.id) in self.courses else None)
        if keep:
            self.tree.selection_set(keep)
            self.tree.focus(keep)
        elif self.courses:
            first = next(iter(self.courses))
            self.tree.selection_set(first)
            self.tree.focus(first)

    def open(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Ders seçin", "Devam etmek için listeden bir ders seçin.",
                                parent=self)
            return
        self.flow.open_course(self.courses[selection[0]])

    def focus_first(self) -> None:
        self.tree.focus_set()


# ===================================================================== 2. adım
class CourseStudents(ttk.Frame):
    COLUMNS = (
        ("no", "Öğrenci No", 100, "w"),
        ("name", "Ad Soyad", 170, "w"),
        ("class", "Sınıf", 70, "center"),
        ("Vize", "Vize", 60, "center"),
        ("Final", "Final", 60, "center"),
        ("Ödev", "Ödev", 60, "center"),
        ("Proje", "Proje", 60, "center"),
        ("avg", "Ortalama", 80, "center"),
        ("letter", "Harf", 60, "center"),
        ("status", "Durum", 80, "center"),
    )

    def __init__(self, parent, flow: GradesTab):
        super().__init__(parent)
        self.flow = flow
        self.rows: dict[str, object] = {}
        self.outsiders: dict[str, object] = {}
        self.add_var = tk.StringVar()
        self.info_var = tk.StringVar()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = grid_card(self, 0, 0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)
        ttk.Label(card, text="2. Öğrenci seçin", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(card, textvariable=self.info_var, style="CardMuted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 10))
        holder, self.tree = make_tree(card, self.COLUMNS, height=10)
        holder.grid(row=2, column=0, sticky="nsew")
        for tone, color in (("success", "#14532D"), ("danger", "#93000A")):
            self.tree.tag_configure(tone, foreground=color)
        self.tree.bind("<Double-1>", lambda _e: self.edit())
        self.tree.bind("<Return>", lambda _e: self.edit())

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(actions, text="Not Gir / Düzenle", style="Accent.TButton",
                   command=self.edit).pack(side="left")
        ttk.Button(actions, text="Toplu Not Girişi",
                   command=lambda: self.flow.go("sheet")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Kaydı Sil", style="Danger.TButton",
                   command=self.unenroll).pack(side="right")
        ttk.Button(actions, text="Derse Ekle", command=self.enroll).pack(
            side="right", padx=(0, 18))
        self.add_combo = ttk.Combobox(actions, textvariable=self.add_var, state="readonly",
                                      width=30)
        self.add_combo.pack(side="right", padx=(0, 8))
        ttk.Label(actions, text="Öğrenci ekle", style="CardField.TLabel").pack(side="right",
                                                                               padx=(0, 8))

    def refresh(self) -> None:
        flow, app = self.flow, self.flow.app
        if flow.course is None:
            return
        try:
            flow.course = app.course_service.get(flow.course.id)
            sheet = app.grade_service.course_sheet(flow.course.id, flow.class_year)
            enrolled = {s.id for s in app.enrollment_service.students_of(flow.course.id)}
            everyone = app.student_service.list()
        except AppError as exc:
            show_error(self, exc)
            return
        course = flow.course
        scope = f" · {flow.class_year}. sınıf öğrencileri" if flow.class_year else ""
        self.info_var.set(f"{course.label} · {course.semester or 'Dönem yok'} · "
                          f"{len(sheet)} öğrenci{scope}")
        selected = self.tree.selection()
        clear_tree(self.tree)
        self.rows = {}
        for row in sheet:
            student = row.student
            iid = str(student.id)
            scores = [format_score(row.grades[e].score) if e in row.grades else ""
                      for e in EXAM_TYPES]
            self.tree.insert("", "end", iid=iid, tags=(status_tone(row.status),), values=(
                student.student_no, student.full_name, _class_label(student.class_year),
                *scores, format_score(row.average), row.letter, row.status))
            self.rows[iid] = student
        self.outsiders = {s.label: s for s in everyone if s.id not in enrolled}
        self.add_combo["values"] = list(self.outsiders)
        self.add_var.set("")
        keep = selected[0] if selected and selected[0] in self.rows else None
        keep = keep or (str(flow.student.id) if flow.student and
                        str(flow.student.id) in self.rows else None)
        target = keep or next(iter(self.rows), None)
        if target:
            self.tree.selection_set(target)
            self.tree.focus(target)

    def _selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Öğrenci seçin", "Önce listeden bir öğrenci seçin.", parent=self)
            return None
        return self.rows[selection[0]]

    def edit(self) -> None:
        student = self._selected()
        if student is not None:
            self.flow.open_student(student)

    def enroll(self) -> None:
        student = self.outsiders.get(self.add_var.get())
        if student is None:
            messagebox.showinfo("Öğrenci seçin", "Derse eklenecek öğrenciyi seçin.", parent=self)
            return
        done = handle_errors(None, lambda: self.flow.app.enrollment_service.enroll(
            student.id, self.flow.course.id) or True, parent=self)
        if done:
            self.flow.student = student
            self.refresh()
            self.flow.changed(f"Derse eklendi: {student.label}")

    def unenroll(self) -> None:
        student = self._selected()
        if student is None:
            return
        if not messagebox.askyesno(
                "Ders kaydını sil",
                f"{student.label} bu dersten çıkarılacak. Devam edilsin mi?", parent=self):
            return
        done = handle_errors(None, lambda: self.flow.app.enrollment_service.unenroll(
            student.id, self.flow.course.id) or True, parent=self)
        if done:
            self.refresh()
            self.flow.changed(f"Ders kaydı silindi: {student.label}")

    def focus_first(self) -> None:
        self.tree.focus_set()


# ===================================================================== 3. adım
class StudentGradeEditor(ttk.Frame):
    COLUMNS = (
        ("exam", "Sınav Türü", 120, "w"),
        ("score", "Puan", 80, "center"),
        ("weight", "Ağırlık", 80, "center"),
        ("date", "Tarih", 110, "center"),
    )

    def __init__(self, parent, flow: GradesTab):
        super().__init__(parent)
        self.flow = flow
        self.grades: dict[str, object] = {}
        self.exam_var = tk.StringVar(value=EXAM_TYPES[0])
        self.score_var = tk.StringVar()
        self.weight_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.info_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self.mode_var = tk.StringVar()
        self.columnconfigure(0, weight=3, uniform="editor")
        self.columnconfigure(1, weight=2, uniform="editor")
        self.rowconfigure(0, weight=1)
        self._build_list()
        self._build_form()

    def _build_list(self) -> None:
        card = grid_card(self, 0, 0, sticky="nsew", padx=(0, 12))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)
        ttk.Label(card, text="3. Notu ekleyin veya düzenleyin", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(card, textvariable=self.info_var, style="CardMuted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 4))
        ttk.Label(card, textvariable=self.summary_var, style="SummaryValue.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 10))
        holder, self.tree = make_tree(card, self.COLUMNS, height=6)
        holder.grid(row=3, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_form(self) -> None:
        card = grid_card(self, 0, 1, sticky="nsew")
        card.columnconfigure(1, weight=1)
        ttk.Label(card, textvariable=self.mode_var, style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        body = ttk.Frame(card, style="Card.TFrame")
        body.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        body.columnconfigure(1, weight=1)
        self.form = Form(body)
        self.exam_combo = ttk.Combobox(body, textvariable=self.exam_var, values=EXAM_TYPES,
                                       state="readonly", width=16)
        self.exam_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_exam())
        self.form.add("exam", FormField(body, "Sınav türü", self.exam_combo, 0, required=True),
                      "Sınav türü")
        score = ttk.Spinbox(body, from_=0, to=100, increment=1, textvariable=self.score_var,
                            width=10, **numeric_validator(body, allow_decimal=True))
        self.form.add("score", FormField(body, "Puan (0-100)", score, 1, required=True), "Puan")
        weight = ttk.Spinbox(body, from_=1, to=100, increment=5, textvariable=self.weight_var,
                             width=10, **numeric_validator(body, allow_decimal=True))
        self.form.add("weight", FormField(body, "Ağırlık", weight, 2, required=True), "Ağırlık")
        self.date_field = DateField(body, self.date_var)
        self.form.add("date", FormField(body, "Tarih", self.date_field, 3, required=True),
                      "Sınav tarihi")
        self.form.place_message(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        for widget in (self.exam_combo, score, weight, self.date_field.entry):
            widget.bind("<Return>", lambda _e: self.save())
            widget.bind("<KP_Enter>", lambda _e: self.save())
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="Kaydet", style="Accent.TButton", command=self.save).pack(
            side="left")
        ttk.Button(actions, text="Yeni Not", command=self.new).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Notu Sil", style="Danger.TButton", command=self.delete).pack(
            side="right")
        ttk.Label(card, text="* zorunlu alan · Enter kaydeder", style="CardMuted.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # --------------------------------------------------------------- veri
    def refresh(self) -> None:
        flow, app = self.flow, self.flow.app
        if flow.course is None or flow.student is None:
            return
        try:
            grades = [g for g in app.grade_service.list_by_student(flow.student.id)
                      if g.course_id == flow.course.id]
        except AppError as exc:
            show_error(self, exc)
            return
        self.info_var.set(f"{flow.student.label} · {flow.course.label}")
        clear_tree(self.tree)
        self.grades = {}
        for grade in sorted(grades, key=lambda g: EXAM_TYPES.index(g.exam_type)):
            self.tree.insert("", "end", iid=grade.exam_type, values=(
                grade.exam_type, format_score(grade.score), format_score(grade.weight, 0),
                _iso_to_tr(grade.exam_date)))
            self.grades[grade.exam_type] = grade
        sheet_row = next((row for row in app.grade_service.course_sheet(flow.course.id)
                          if row.student.id == flow.student.id), None)
        if sheet_row and sheet_row.average is not None:
            self.summary_var.set(f"Ortalama {format_score(sheet_row.average)} · "
                                 f"{sheet_row.letter} · {sheet_row.status}")
        else:
            self.summary_var.set("Bu derste henüz not yok")
        missing = next((e for e in EXAM_TYPES if e not in self.grades), EXAM_TYPES[0])
        self.exam_var.set(missing)
        self._load_exam()

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if selection:
            self.exam_var.set(selection[0])
            self._load_exam(select=False)

    def _load_exam(self, select: bool = True) -> None:
        """Seçilen sınav türünün notu varsa düzenleme, yoksa yeni kayıt kipine geçer."""
        self.form.clear_errors()
        grade = self.grades.get(self.exam_var.get())
        if grade:
            self.mode_var.set(f"{grade.exam_type} notunu düzenle")
            self.score_var.set(format_score(grade.score))
            self.weight_var.set(format_score(grade.weight, 0))
            self.date_var.set(_iso_to_tr(grade.exam_date))
            if select and self.tree.exists(grade.exam_type):
                self.tree.selection_set(grade.exam_type)
        else:
            self.mode_var.set(f"Yeni {self.exam_var.get()} notu")
            self.score_var.set("")
            self.weight_var.set(f"{DEFAULT_WEIGHTS.get(self.exam_var.get(), 40.0):.0f}")
            self.date_var.set(date.today().strftime(DATE_FORMAT))
            if self.tree.selection():
                self.tree.selection_remove(*self.tree.selection())

    def new(self) -> None:
        missing = next((e for e in EXAM_TYPES if e not in self.grades), self.exam_var.get())
        self.exam_var.set(missing)
        self._load_exam()
        self.focus_first()

    def save(self) -> None:
        flow, service = self.flow, self.flow.app.grade_service
        grade = self.grades.get(self.exam_var.get())
        values = (self.exam_var.get(), self.score_var.get(), self.weight_var.get(),
                  self.date_var.get())
        if grade:
            def action():
                return service.update(grade.id, flow.student.id, flow.course.id, *values)
        else:
            def action():
                return service.add(flow.student.id, flow.course.id, *values)
        saved = handle_errors(self.form, action)
        if saved is not None:
            self.refresh()
            self.exam_var.set(saved.exam_type)
            self._load_exam()
            verb = "güncellendi" if grade else "eklendi"
            flow.changed(f"Not {verb}: {flow.student.label} / {saved.course_code} / "
                         f"{saved.exam_type} = {format_score(saved.score)}")

    def delete(self) -> None:
        grade = self.grades.get(self.exam_var.get())
        if grade is None:
            messagebox.showinfo("Silinecek not yok",
                                "Bu sınav türü için kayıtlı not bulunmuyor.", parent=self)
            return
        if not messagebox.askyesno("Notu sil", f"{grade.exam_type} notu silinecek. "
                                               "Devam edilsin mi?", parent=self):
            return
        if handle_errors(None, lambda: self.flow.app.grade_service.delete(grade.id) or True,
                         parent=self):
            self.refresh()
            self.flow.changed(f"Not silindi: {self.flow.student.label} / {grade.exam_type}")

    def focus_first(self) -> None:
        widgets = self.form.widgets()
        (widgets[1] if len(widgets) > 1 else widgets[0]).focus_set()


# ===================================================================== 4. adım
class QuickSheet(ttk.Frame):
    """Dersin tüm öğrencileri için tablo halinde not girişi."""

    def __init__(self, parent, flow: GradesTab):
        super().__init__(parent)
        self.flow = flow
        self.cells: dict[tuple, ttk.Entry] = {}
        self.vars: dict[tuple, tk.StringVar] = {}
        self.initial: dict[tuple, str] = {}
        self.order: list[int] = []
        self.date_var = tk.StringVar(value=date.today().strftime(DATE_FORMAT))
        self.info_var = tk.StringVar()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = grid_card(self, 0, 0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)
        ttk.Label(card, text="Toplu not girişi", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w")
        top = ttk.Frame(card, style="Card.TFrame")
        top.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        ttk.Label(top, textvariable=self.info_var, style="CardMuted.TLabel").pack(side="left")
        date_box = ttk.Frame(top, style="Card.TFrame")
        date_box.pack(side="right")
        ttk.Label(date_box, text="Yeni notların tarihi", style="CardField.TLabel").pack(
            side="left", padx=(0, 8))
        self.date_field = DateField(date_box, self.date_var)
        self.date_field.pack(side="left")

        frame = ttk.Frame(card, style="Border.TFrame")
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(frame, background=SURFACE, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.table = ttk.Frame(self.canvas, style="Card.TFrame", padding=(8, 6))
        self.window = self.canvas.create_window((0, 0), window=self.table, anchor="nw")
        self.table.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self.window, width=e.width))
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(card, textvariable=self.error_var, style="FormError.TLabel",
                                     wraplength=700)
        self.error_label.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.error_label.grid_remove()
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(actions, text="Boş hücre mevcut notu değiştirmez. Enter bir alt satıra "
                                "geçer · Ctrl+S kaydeder.", style="CardMuted.TLabel").pack(
            side="left")
        ttk.Button(actions, text="Vazgeç", command=self.flow.back).pack(side="right")
        ttk.Button(actions, text="Tümünü Kaydet", style="Accent.TButton",
                   command=self.save).pack(side="right", padx=(0, 8))

    def _wheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    # --------------------------------------------------------------- veri
    def refresh(self) -> None:
        flow = self.flow
        if flow.course is None:
            return
        try:
            sheet = flow.app.grade_service.course_sheet(flow.course.id, flow.class_year)
        except AppError as exc:
            show_error(self, exc)
            return
        self.discard()
        for child in self.table.winfo_children():
            child.destroy()
        headers = ("Öğrenci No", "Ad Soyad") + EXAM_TYPES + ("Ortalama",)
        for column, text in enumerate(headers):
            ttk.Label(self.table, text=text, style="Header.TLabel").grid(
                row=0, column=column, sticky="w", padx=6, pady=(0, 6))
        validator = numeric_validator(self.table, allow_decimal=True)
        for row_index, row in enumerate(sheet, start=1):
            student = row.student
            self.order.append(student.id)
            ttk.Label(self.table, text=student.student_no, style="Card.TLabel").grid(
                row=row_index, column=0, sticky="w", padx=6, pady=2)
            ttk.Label(self.table, text=student.full_name, style="Card.TLabel").grid(
                row=row_index, column=1, sticky="w", padx=6, pady=2)
            for column, exam in enumerate(EXAM_TYPES, start=2):
                key = (student.id, exam)
                value = format_score(row.grades[exam].score) if exam in row.grades else ""
                var = tk.StringVar(value=value)
                entry = ttk.Entry(self.table, textvariable=var, width=8, justify="center",
                                  **validator)
                entry.grid(row=row_index, column=column, padx=4, pady=2)
                entry.bind("<Return>", lambda _e, k=key: self._move_down(k))
                entry.bind("<KP_Enter>", lambda _e, k=key: self._move_down(k))
                entry.bind("<Control-s>", lambda _e: (self.save(), "break")[1])
                self.cells[key], self.vars[key], self.initial[key] = entry, var, value
            ttk.Label(self.table, text=format_score(row.average), style="CardMuted.TLabel").grid(
                row=row_index, column=len(headers) - 1, padx=6)
        scope = f" · {flow.class_year}. sınıf" if flow.class_year else ""
        self.info_var.set(f"{flow.course.label} · {len(sheet)} öğrenci{scope}")
        self.canvas.yview_moveto(0)

    def _move_down(self, key) -> str:
        student_id, exam = key
        index = self.order.index(student_id)
        if index + 1 < len(self.order):
            target = self.cells[(self.order[index + 1], exam)]
            target.focus_set()
            target.select_range(0, "end")
            self._scroll_into_view(target)
        return "break"

    def _scroll_into_view(self, widget) -> None:
        self.canvas.update_idletasks()
        total = max(self.table.winfo_height(), 1)
        top = widget.winfo_y() / total
        first, last = self.canvas.yview()
        if top < first or top > last - 0.05:
            self.canvas.yview_moveto(max(top - 0.3, 0))

    def is_dirty(self) -> bool:
        """Kaydedilecek (boş olmayan ve değişmiş) hücre var mı?"""
        return any(var.get().strip() and var.get().strip() != self.initial[key]
                   for key, var in self.vars.items())

    def discard(self) -> None:
        self.cells, self.vars, self.initial, self.order = {}, {}, {}, []
        self.error_var.set("")
        self.error_label.grid_remove()

    def save(self) -> None:
        for entry in self.cells.values():
            entry.configure(style="TEntry")
        changed: dict[int, dict] = {}
        for key, var in self.vars.items():
            value = var.get().strip()
            if value != self.initial[key] and value:
                changed.setdefault(key[0], {})[key[1]] = value
        if not changed:
            self.flow.app.set_status("Kaydedilecek değişiklik yok.")
            return
        try:
            added, updated = self.flow.app.grade_service.save_sheet(
                self.flow.course.id, changed, self.date_var.get())
        except SheetValidationError as exc:
            for key in exc.errors:
                if key in self.cells:
                    self.cells[key].configure(style="Invalid.TEntry")
            first = next((k for k in exc.errors if k in self.cells), None)
            if first:
                self.cells[first].focus_set()
            self.error_var.set(str(exc))
            self.error_label.grid()
            return
        except AppError as exc:
            self.error_var.set(str(exc))
            self.error_label.grid()
            return
        self.error_var.set("")
        self.error_label.grid_remove()
        self.refresh()
        self.flow.changed(f"Toplu not girişi kaydedildi: {added} yeni, {updated} güncellendi.")

    def focus_first(self) -> None:
        if self.order:
            self.cells[(self.order[0], EXAM_TYPES[0])].focus_set()
