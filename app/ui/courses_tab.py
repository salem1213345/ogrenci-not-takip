"""Ders kayıtları ekranı (form + liste)."""

import tkinter as tk
from tkinter import messagebox, ttk

from app.config import SEMESTERS
from app.errors import AppError
from app.ui.common import clear_tree, form_actions, make_tree, page_header, show_error
from app.ui.forms import Form, FormField, handle_errors, numeric_validator
from app.ui.theme import grid_card

UNASSIGNED = "(Atanmamış)"


class CoursesTab(ttk.Frame):
    COLUMNS = (
        ("code", "Kod", 90, "w"),
        ("name", "Ders Adı", 230, "w"),
        ("credit", "Kredi", 60, "center"),
        ("semester", "Dönem", 100, "w"),
        ("instructor", "Öğretim Görevlisi", 200, "w"),
        ("teacher", "Sorumlu Hesap", 140, "w"),
    )

    def __init__(self, parent, app):
        super().__init__(parent, padding=(24, 16))
        self.app = app
        self.service = app.course_service
        self.selected_id: int | None = None
        self.teachers: dict[str, int | None] = {UNASSIGNED: None}
        self.vars = {
            "code": tk.StringVar(),
            "name": tk.StringVar(),
            "credit": tk.StringVar(value="3"),
            "semester": tk.StringVar(),
            "instructor": tk.StringVar(),
            "teacher": tk.StringVar(value=UNASSIGNED),
        }
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar(value="0 ders")
        self._build()
        self.search_var.trace_add("write", lambda *_: self._reload())

    # -------------------------------------------------------------- görünüm
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        page_header(self, "Dersler", self.count_var)

        card = grid_card(self, 1, 0, sticky="ew", pady=(0, 12))
        card.columnconfigure(0, weight=1)
        title = ttk.Frame(card, style="Card.TFrame")
        title.grid(row=0, column=0, sticky="ew")
        ttk.Label(title, text="Ders Bilgileri", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(title, text="* zorunlu alan · Enter ekler", style="CardMuted.TLabel").pack(
            side="right")
        body = ttk.Frame(card, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="ew")
        for column in (1, 3, 5):
            body.columnconfigure(column, weight=1)
        self.form = Form(body)
        add, v = self.form.add, self.vars
        code = ttk.Entry(body, textvariable=v["code"], width=12)
        add("code", FormField(body, "Ders Kodu", code, 0, 0, required=True), "Ders kodu")
        add("name", FormField(body, "Ders Adı", ttk.Entry(body, textvariable=v["name"]),
                              0, 2, required=True, span=3), "Ders adı")
        add("credit", FormField(body, "Kredi", ttk.Spinbox(
            body, from_=1, to=10, textvariable=v["credit"], width=6,
            **numeric_validator(body, allow_decimal=False, max_length=2)), 1, 0,
            required=True), "Kredi")
        self.semester_combo = ttk.Combobox(body, textvariable=v["semester"], values=SEMESTERS,
                                           width=14)
        add("semester", FormField(body, "Dönem", self.semester_combo, 1, 2), "Dönem")
        self.teacher_combo = ttk.Combobox(body, textvariable=v["teacher"], state="readonly")
        add("teacher", FormField(body, "Sorumlu Hesap", self.teacher_combo, 1, 4),
            "Sorumlu öğretmen")
        add("instructor", FormField(body, "Öğretim Görevlisi", ttk.Entry(
            body, textvariable=v["instructor"]), 2, 0, span=5), "Öğretim görevlisi")
        self.form.place_message(row=8, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        for widget in self.form.widgets():
            widget.bind("<Return>", lambda _e: self._on_add())
            widget.bind("<KP_Enter>", lambda _e: self._on_add())
        footer = ttk.Frame(card, style="Card.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        form_actions(footer, self._on_add, self._on_update, self._on_delete,
                     self._clear_form).pack(side="left")
        ttk.Label(footer, text="Sorumlu hesap, dersin notlarını girebilen ve mesaj alan "
                               "öğretmendir.", style="CardMuted.TLabel").pack(side="right")

        listing = grid_card(self, 2, 0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(listing, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="Ara:", style="Card.TLabel").pack(side="left")
        ttk.Entry(toolbar, textvariable=self.search_var, width=32).pack(side="left", padx=(8, 0))
        ttk.Label(toolbar, text="İpucu: Ders silindiğinde o derse ait tüm notlar da silinir.",
                  style="CardMuted.TLabel").pack(side="right")
        container, self.tree = make_tree(listing, self.COLUMNS, height=13)
        container.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # --------------------------------------------------------------- eylemler
    def _values(self) -> dict:
        values = {key: var.get() for key, var in self.vars.items() if key != "teacher"}
        values["teacher_id"] = self.teachers.get(self.vars["teacher"].get())
        return values

    def _on_add(self) -> None:
        course = handle_errors(self.form, lambda: self.service.add(**self._values()))
        if course is not None:
            self._clear_form()
            self.app.notify_change(f"Ders eklendi: {course.label}")

    def _on_update(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Seçim gerekli", "Önce listeden bir ders seçin.", parent=self)
            return
        course = handle_errors(self.form, lambda: self.service.update(
            self.selected_id, **self._values()))
        if course is not None:
            self.app.notify_change(f"Ders güncellendi: {course.label}")

    def _on_delete(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Seçim gerekli", "Önce listeden bir ders seçin.", parent=self)
            return
        try:
            course = self.service.get(self.selected_id)
        except AppError as exc:
            show_error(self, exc)
            return
        confirmed = messagebox.askyesno(
            "Dersi sil",
            f"{course.label} dersi, ders kayıtları ve bu derse ait tüm notlar silinecek.\n"
            "Bu işlem geri alınamaz. Devam edilsin mi?",
            parent=self,
        )
        if not confirmed:
            return
        try:
            self.service.delete(self.selected_id)
        except AppError as exc:
            show_error(self, exc)
            return
        self._clear_form()
        self.app.notify_change(f"Ders silindi: {course.label}")

    def _teacher_label(self, teacher_id) -> str:
        return next((label for label, tid in self.teachers.items() if tid == teacher_id),
                    UNASSIGNED)

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        try:
            course = self.service.get(self.selected_id)
        except AppError as exc:
            show_error(self, exc)
            return
        self.form.clear_errors()
        self.vars["code"].set(course.code)
        self.vars["name"].set(course.name)
        self.vars["credit"].set(str(course.credit))
        self.vars["semester"].set(course.semester)
        self.vars["instructor"].set(course.instructor)
        self.vars["teacher"].set(self._teacher_label(course.teacher_id))

    def _clear_form(self) -> None:
        for key, var in self.vars.items():
            var.set({"credit": "3", "teacher": UNASSIGNED}.get(key, ""))
        if self.app.current_user is not None and self.app.current_user.is_teacher:
            self.vars["teacher"].set(self._teacher_label(self.app.current_user.id))
        self.selected_id = None
        self.form.clear_errors()
        if self.tree.selection():
            self.tree.selection_remove(*self.tree.selection())

    def reset(self) -> None:
        self.search_var.set("")
        self._clear_form()

    # ----------------------------------------------------------------- yenile
    def refresh(self) -> None:
        self.teachers = {UNASSIGNED: None}
        for teacher in self.app.auth_service.teachers():
            self.teachers[f"{teacher.full_name} ({teacher.username})"] = teacher.id
        self.teacher_combo["values"] = list(self.teachers)
        semesters = list(SEMESTERS) + [s for s in self.service.semesters() if s not in SEMESTERS]
        self.semester_combo["values"] = semesters
        if self.selected_id is None:
            self._clear_form()
        self._reload()

    def _reload(self) -> None:
        try:
            courses = self.service.list(self.search_var.get())
        except AppError as exc:
            show_error(self, exc)
            return
        names = {tid: label.split(" (", maxsplit=1)[0]
                 for label, tid in self.teachers.items() if tid}
        clear_tree(self.tree)
        for course in courses:
            self.tree.insert("", "end", iid=str(course.id), values=(
                course.code, course.name, course.credit, course.semester or "-",
                course.instructor, names.get(course.teacher_id, "-")))
        self.count_var.set(f"{len(courses)} ders")
        if self.selected_id is not None:
            if self.tree.exists(str(self.selected_id)):
                self.tree.selection_set(str(self.selected_id))
            else:
                self._clear_form()
