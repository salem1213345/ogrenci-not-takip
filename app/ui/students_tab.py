"""Öğrenci kayıtları ekranı (form + liste + portal hesabı)."""

import tkinter as tk
from tkinter import messagebox, ttk

from app.errors import AppError
from app.ui.common import clear_tree, form_actions, make_tree, page_header, show_error
from app.ui.dialogs import StudentPasswordDialog
from app.ui.forms import Form, FormField, handle_errors
from app.ui.theme import grid_card
from app.validators import CLASS_YEARS

NO_CLASS = ""


class StudentsTab(ttk.Frame):
    COLUMNS = (
        ("no", "Öğrenci No", 100, "w"),
        ("name", "Ad Soyad", 180, "w"),
        ("class", "Sınıf", 60, "center"),
        ("department", "Bölüm", 220, "w"),
        ("email", "E-posta", 210, "w"),
        ("account", "Hesap", 70, "center"),
    )
    KEYS = ("student_no", "first_name", "last_name", "department", "class_year", "email")

    def __init__(self, parent, app):
        super().__init__(parent, padding=(24, 16))
        self.app = app
        self.service = app.student_service
        self.selected_id: int | None = None
        self.accounts: dict[int, str] = {}  # öğrenci id -> kullanıcı adı
        self.vars = {key: tk.StringVar() for key in self.KEYS}
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar(value="0 öğrenci")
        self.account_var = tk.StringVar(value="Öğrenci seçilmedi")
        self._build()
        self.search_var.trace_add("write", lambda *_: self._reload())

    # -------------------------------------------------------------- görünüm
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        page_header(self, "Öğrenciler", self.count_var)

        card = grid_card(self, 1, 0, sticky="ew", pady=(0, 12))
        card.columnconfigure(0, weight=1)
        title = ttk.Frame(card, style="Card.TFrame")
        title.grid(row=0, column=0, sticky="ew")
        ttk.Label(title, text="Öğrenci Bilgileri", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(title, text="* zorunlu alan · Enter ekler", style="CardMuted.TLabel").pack(
            side="right")
        body = ttk.Frame(card, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="ew")
        for column in (1, 3, 5):
            body.columnconfigure(column, weight=1)
        self.form = Form(body)
        add = self.form.add
        add("student_no", FormField(body, "Öğrenci No", ttk.Entry(
            body, textvariable=self.vars["student_no"], width=14), 0, 0, required=True),
            "Öğrenci numarası")
        add("first_name", FormField(body, "Ad", ttk.Entry(
            body, textvariable=self.vars["first_name"]), 0, 2, required=True), "Ad")
        add("last_name", FormField(body, "Soyad", ttk.Entry(
            body, textvariable=self.vars["last_name"]), 0, 4, required=True), "Soyad")
        self.department_combo = ttk.Combobox(body, textvariable=self.vars["department"])
        add("department", FormField(body, "Bölüm", self.department_combo, 1, 0), "Bölüm")
        add("class_year", FormField(body, "Sınıf", ttk.Combobox(
            body, textvariable=self.vars["class_year"], state="readonly", width=8,
            values=[NO_CLASS] + [str(year) for year in CLASS_YEARS]), 1, 2), "Sınıf")
        add("email", FormField(body, "E-posta", ttk.Entry(
            body, textvariable=self.vars["email"]), 1, 4), "E-posta")
        self.form.place_message(row=8, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        for widget in self.form.widgets():
            widget.bind("<Return>", lambda _e: self._on_add())
            widget.bind("<KP_Enter>", lambda _e: self._on_add())

        footer = ttk.Frame(card, style="Card.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        form_actions(footer, self._on_add, self._on_update, self._on_delete,
                     self._clear_form).pack(side="left")
        account = ttk.Frame(footer, style="Card.TFrame")
        account.pack(side="right")
        ttk.Label(account, text="Portal hesabı:", style="CardField.TLabel").pack(side="left")
        ttk.Label(account, textvariable=self.account_var, style="CardMuted.TLabel").pack(
            side="left", padx=(6, 10))
        self.account_button = ttk.Button(
            account, text="Hesap Oluştur", command=self._manage_account)
        self.account_button.pack(side="left")
        self.account_button.state(["disabled"])

        listing = grid_card(self, 2, 0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(listing, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="Ara:", style="Card.TLabel").pack(side="left")
        ttk.Entry(toolbar, textvariable=self.search_var, width=32).pack(side="left", padx=(8, 0))
        ttk.Label(
            toolbar,
            text="İpucu: Güncelleme veya silme işlemi için listeden bir öğrenci seçin.",
            style="CardMuted.TLabel",
        ).pack(side="right")
        container, self.tree = make_tree(listing, self.COLUMNS, height=13)
        container.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # --------------------------------------------------------------- eylemler
    def _values(self) -> dict:
        return {key: var.get() for key, var in self.vars.items()}

    def _on_add(self) -> None:
        student = handle_errors(self.form, lambda: self.service.add(**self._values()))
        if student is not None:
            self._clear_form()
            self.app.notify_change(f"Öğrenci eklendi: {student.full_name}")

    def _on_update(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Seçim gerekli", "Önce listeden bir öğrenci seçin.", parent=self)
            return
        student = handle_errors(self.form, lambda: self.service.update(
            self.selected_id, **self._values()))
        if student is not None:
            self.app.notify_change(f"Öğrenci güncellendi: {student.full_name}")

    def _on_delete(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Seçim gerekli", "Önce listeden bir öğrenci seçin.", parent=self)
            return
        try:
            student = self.service.get(self.selected_id)
        except AppError as exc:
            show_error(self, exc)
            return
        confirmed = messagebox.askyesno(
            "Öğrenciyi sil",
            f"{student.full_name} ({student.student_no}), tüm notları ve portal hesabı "
            "silinecek.\nBu işlem geri alınamaz. Devam edilsin mi?",
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
        self.app.notify_change(f"Öğrenci silindi: {student.full_name}")

    def _manage_account(self) -> None:
        if self.selected_id is None:
            return
        student = self.service.get(self.selected_id)
        has_account = self.selected_id in self.accounts
        dialog = StudentPasswordDialog(self, self.app.auth_service, student, has_account)
        self.wait_window(dialog)
        if dialog.result:
            verb = "şifresi sıfırlandı" if has_account else "portal hesabı oluşturuldu"
            self.app.notify_change(f"{student.full_name}: {verb} "
                                   f"(kullanıcı adı {dialog.result.username}).")

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        try:
            student = self.service.get(self.selected_id)
        except AppError as exc:
            show_error(self, exc)
            return
        self.form.clear_errors()
        self.vars["student_no"].set(student.student_no)
        self.vars["first_name"].set(student.first_name)
        self.vars["last_name"].set(student.last_name)
        self.vars["department"].set(student.department)
        self.vars["class_year"].set(str(student.class_year or NO_CLASS))
        self.vars["email"].set(student.email)
        self._show_account(student)

    def _show_account(self, student=None) -> None:
        if student is None:
            self.account_var.set("Öğrenci seçilmedi")
            self.account_button.configure(text="Hesap Oluştur")
            self.account_button.state(["disabled"])
            return
        self.account_button.state(["!disabled"])
        if student.id in self.accounts:
            self.account_var.set(f"Var (kullanıcı adı {self.accounts[student.id]})")
            self.account_button.configure(text="Şifre Sıfırla")
        else:
            self.account_var.set("Yok")
            self.account_button.configure(text="Hesap Oluştur")

    def _clear_form(self) -> None:
        for var in self.vars.values():
            var.set("")
        self.selected_id = None
        self.form.clear_errors()
        self._show_account(None)
        if self.tree.selection():
            self.tree.selection_remove(*self.tree.selection())

    def reset(self) -> None:
        self.search_var.set("")
        self._clear_form()

    # ----------------------------------------------------------------- yenile
    def refresh(self) -> None:
        self.department_combo["values"] = self.service.departments()
        self._reload()

    def _reload(self) -> None:
        try:
            students = self.service.list(self.search_var.get())
            self.accounts = {int(row["student_id"]): row["username"] for row in self.app.db.query(
                "SELECT student_id, username FROM users WHERE student_id IS NOT NULL")}
        except AppError as exc:
            show_error(self, exc)
            return
        clear_tree(self.tree)
        for student in students:
            self.tree.insert("", "end", iid=str(student.id), values=(
                student.student_no, student.full_name,
                f"{student.class_year}." if student.class_year else "-",
                student.department, student.email,
                "Var" if student.id in self.accounts else "Yok"))
        self.count_var.set(f"{len(students)} öğrenci")
        if self.selected_id is not None:
            if self.tree.exists(str(self.selected_id)):
                self.tree.selection_set(str(self.selected_id))
            else:
                self._clear_form()
