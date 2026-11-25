"""Hesap işlemleri için kalıcı (modal) pencereler."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.forms import Form, FormField, handle_errors
from app.ui.theme import BACKGROUND
from app.validators import MIN_PASSWORD_LENGTH

PASSWORD_HINT = (f"Şifre en az {MIN_PASSWORD_LENGTH} karakter olmalı; "
                 "en az bir harf ve bir rakam içermelidir.")


class Dialog(tk.Toplevel):
    """Ortak iletişim penceresi: başlık, kart içinde form, alt düğmeler.

    Enter onaylar, Esc kapatır; pencere ana pencerenin ortasında açılır.
    """

    submit_text = "Kaydet"

    def __init__(self, parent: tk.Misc, title: str, intro: str = ""):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(background=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.result = None
        outer = ttk.Frame(self, padding=(22, 18))
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=title, style="Section.TLabel").pack(anchor="w")
        if intro:
            ttk.Label(outer, text=intro, style="Muted.TLabel", wraplength=420,
                      justify="left").pack(anchor="w", pady=(4, 0))
        card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        card.pack(fill="both", expand=True, pady=(12, 12))
        card.columnconfigure(1, weight=1)
        self.form = Form(card)
        self.build(card)
        self.form.place_message(row=98, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Vazgeç", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text=self.submit_text, style="Accent.TButton",
                   command=self.submit).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _e: self.submit())
        self.bind("<KP_Enter>", lambda _e: self.submit())
        self.bind("<Escape>", lambda _e: self.destroy())
        self._center(parent)
        self.deiconify()
        self.grab_set()
        widgets = self.form.widgets()
        if widgets:
            widgets[0].focus_set()

    def _center(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        top = parent.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_reqwidth()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def build(self, card: ttk.Frame) -> None:  # pragma: no cover - alt sınıflarda
        raise NotImplementedError

    def action(self):  # pragma: no cover - alt sınıflarda
        raise NotImplementedError

    def submit(self) -> None:
        result = handle_errors(self.form, self.action)
        if result is not None:
            self.result = result
            self.destroy()

    def password_entry(self, card, key: str, label: str, row: int, var: tk.StringVar,
                       *aliases: str) -> None:
        entry = ttk.Entry(card, textvariable=var, show="•", width=32)
        self.form.add(key, FormField(card, label, entry, row, required=True), *aliases)


class StudentPasswordDialog(Dialog):
    """Öğretmen, öğrencinin portal hesabını oluşturur veya şifresini sıfırlar."""

    def __init__(self, parent, auth, student, has_account: bool):
        self.auth, self.student = auth, student
        self.password, self.again = tk.StringVar(), tk.StringVar()
        self.submit_text = "Şifreyi Sıfırla" if has_account else "Hesap Oluştur"
        account = auth.student_account(student.id)
        username = account.username if account else student.student_no
        intro = (f"{student.student_no} - {student.full_name}. "
                 f"Kullanıcı adı: {username}. {PASSWORD_HINT}")
        super().__init__(parent, "Öğrenci Portal Hesabı", intro)

    def build(self, card):
        self.password_entry(card, "password", "Şifre", 0, self.password, "Şifre")
        self.password_entry(card, "again", "Şifre (tekrar)", 1, self.again, "Şifre (tekrar)")

    def action(self):
        return self.auth.set_student_password(self.student.id, self.password.get(),
                                              self.again.get())


class ChangePasswordDialog(Dialog):
    """Oturumdaki kullanıcı kendi şifresini değiştirir."""

    submit_text = "Şifreyi Değiştir"

    def __init__(self, parent, auth, user):
        self.auth, self.user = auth, user
        self.current, self.new, self.again = tk.StringVar(), tk.StringVar(), tk.StringVar()
        super().__init__(parent, "Şifremi Değiştir", PASSWORD_HINT)

    def build(self, card):
        self.password_entry(card, "current", "Mevcut şifre", 0, self.current, "Mevcut şifre")
        self.password_entry(card, "new", "Yeni şifre", 1, self.new, "Yeni şifre")
        self.password_entry(card, "again", "Yeni şifre (tekrar)", 2, self.again,
                            "Yeni şifre (tekrar)")

    def action(self):
        self.auth.change_password(self.user.id, self.current.get(), self.new.get(),
                                  self.again.get())
        return True


class TeacherAccountDialog(Dialog):
    """Yeni öğretmen hesabı ekler."""

    submit_text = "Hesabı Oluştur"

    def __init__(self, parent, auth):
        self.auth = auth
        self.full_name, self.username = tk.StringVar(), tk.StringVar()
        self.password, self.again = tk.StringVar(), tk.StringVar()
        super().__init__(parent, "Öğretmen Hesabı Ekle", PASSWORD_HINT)

    def build(self, card):
        self.form.add("full_name", FormField(
            card, "Ad Soyad", ttk.Entry(card, textvariable=self.full_name, width=32), 0,
            required=True), "Ad Soyad")
        self.form.add("username", FormField(
            card, "Kullanıcı adı", ttk.Entry(card, textvariable=self.username, width=32), 1,
            required=True), "Kullanıcı adı")
        self.password_entry(card, "password", "Şifre", 2, self.password, "Şifre")
        self.password_entry(card, "again", "Şifre (tekrar)", 3, self.again, "Şifre (tekrar)")

    def action(self):
        return self.auth.create_teacher(self.username.get(), self.full_name.get(),
                                        self.password.get(), self.again.get())
