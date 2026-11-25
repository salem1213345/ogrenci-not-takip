"""Giriş ekranı ve ilk kurulum (ilk öğretmen hesabı) ekranı."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app import config
from app.demo_data import DemoAccount, demo_accounts
from app.ui.dialogs import PASSWORD_HINT
from app.ui.forms import Form, FormField, handle_errors
from app.ui.theme import (FONT_LABEL, FONT_SMALL, MONO_FAMILY, MUTED, NAVY, NAVY_CONTAINER,
                          OUTLINE, SURFACE_HIGH, SURFACE_LOW, TEXT)

HERO_WIDTH = 460
ROW_FONT = (MONO_FAMILY, 9)  # kullanıcı adı / şifre: karakterler net ayırt edilsin


def _hero(parent: tk.Misc) -> tk.Frame:
    """Sol bilgi paneli: kurum adı ve kısa açıklama (süsleme yok)."""
    hero = tk.Frame(parent, background=NAVY, width=HERO_WIDTH)
    hero.pack(side="left", fill="y")
    hero.pack_propagate(False)
    tk.Label(hero, text="AkademiPusula", background=NAVY, foreground="#ffffff",
             font=("Segoe UI", 15, "bold"), anchor="w").pack(anchor="w", padx=40, pady=(44, 0))
    tk.Label(hero, text=config.APP_NAME, background=NAVY, foreground="#B6C4FF",
             font=("Segoe UI", 10), anchor="w").pack(anchor="w", padx=40, pady=(2, 0))
    tk.Frame(hero, background=NAVY_CONTAINER, height=1).pack(fill="x", padx=40, pady=(28, 0))
    tk.Label(hero, text="Dersler, notlar ve iletişim\ntek merkezde.", background=NAVY,
             foreground="#ffffff", font=("Segoe UI", 21, "bold"), justify="left",
             anchor="w").pack(anchor="w", padx=40, pady=(28, 0))
    tk.Label(hero, text="Öğretmenler ders, not ve döküm işlemlerini yürütür;\n"
                        "öğrenciler notlarını, ortalamalarını ve mesajlarını izler.",
             background=NAVY, foreground="#D6DDFF", font=("Segoe UI", 10),
             justify="left", anchor="w").pack(anchor="w", padx=40, pady=(14, 0))
    tk.Label(hero, text=f"Sürüm {config.APP_VERSION}", background=NAVY, foreground="#B6C4FF",
             font=("Segoe UI", 9)).pack(side="bottom", anchor="w", padx=40, pady=28)
    return hero


def _card(parent: tk.Misc, height: int | None) -> ttk.Frame:
    """Ortalanmış kart. height=None: kart içeriği kadar yer kaplar."""
    area = ttk.Frame(parent)
    area.pack(side="left", fill="both", expand=True)
    border = ttk.Frame(area, style="Border.TFrame")
    size = {"width": 440} if height is None else {"width": 440, "height": height}
    border.place(relx=0.5, rely=0.5, anchor="center", **size)
    card = ttk.Frame(border, style="Card.TFrame", padding=(32, 26))
    card.pack(fill="both", expand=True, padx=1, pady=1)
    card.columnconfigure(1, weight=1)
    return card


class LoginView(ttk.Frame):
    """Kullanıcı adı + şifre ile giriş. Rol, hesaptan belirlenir."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.show_password = tk.BooleanVar(value=False)
        _hero(self)
        accounts = _panel_accounts(app)
        card = _card(self, None if accounts else 430)
        ttk.Label(card, text="Sisteme Giriş", style="SectionCard.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(card, text="Size verilen kullanıcı adı ve şifreyle giriş yapın. Hesabı "
                             "olmayan öğrenciler ders öğretmenine başvurmalıdır.",
                  style="CardMuted.TLabel", wraplength=370, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 10))
        body = ttk.Frame(card, style="Card.TFrame")
        body.grid(row=2, column=0, columnspan=2, sticky="ew")
        body.columnconfigure(1, weight=1)
        self.form = Form(body)
        self.user_entry = ttk.Entry(body, textvariable=self.username)
        self.form.add("username", FormField(body, "Kullanıcı adı", self.user_entry, 0))
        self.pass_entry = ttk.Entry(body, textvariable=self.password, show="•")
        self.form.add("password", FormField(body, "Şifre", self.pass_entry, 1))
        ttk.Checkbutton(body, text="Şifreyi göster", variable=self.show_password,
                        command=self._toggle_password).grid(row=4, column=1, sticky="w")
        self.form.place_message(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Button(actions, text="Giriş Yap", style="Accent.TButton",
                   command=self.submit).pack(fill="x")
        forgot = ttk.Label(actions, text="Şifremi unuttum", style="CardMuted.TLabel",
                           cursor="hand2")
        forgot.pack(anchor="w", pady=(10, 0))
        forgot.bind("<Button-1>", lambda _e: self._forgot())
        self.demo_panel = None
        if accounts:
            self.demo_panel = DemoPanel(card, accounts, self)
            self.demo_panel.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        for entry in (self.user_entry, self.pass_entry):
            entry.bind("<Return>", lambda _e: self.submit())
            entry.bind("<KP_Enter>", lambda _e: self.submit())

    def fill(self, account: DemoAccount) -> None:
        """Demo panelinden seçilen hesabı alanlara yazar; Enter ile giriş yapılır."""
        self.username.set(account.username)
        self.password.set(account.password)
        self.form.clear_errors()
        self.pass_entry.focus_set()
        self.pass_entry.icursor("end")
        self.app.set_status(f"{account.username} seçildi. Giriş için Enter'a basın.")

    def _toggle_password(self) -> None:
        self.pass_entry.configure(show="" if self.show_password.get() else "•")

    def _forgot(self) -> None:
        messagebox.showinfo(
            "Şifremi unuttum",
            "Öğrenciler şifre sıfırlama için ders öğretmenine başvurmalıdır.\n"
            "Öğretmen şifreleri sistemdeki başka bir öğretmen hesabından yenilenebilir.",
            parent=self,
        )

    def reset(self) -> None:
        self.password.set("")
        self.show_password.set(False)
        self._toggle_password()
        self.form.clear_errors()
        (self.user_entry if not self.username.get() else self.pass_entry).focus_set()

    def submit(self) -> None:
        def action():
            return self.app.auth_service.authenticate(self.username.get(), self.password.get())

        user = handle_errors(self.form, action)
        if user is not None:
            self.password.set("")
            self.app.login(user)


def _panel_accounts(app) -> list[DemoAccount]:
    """Demo paneli yalnızca demo veritabanında gösterilir; gerçek veritabanı
    (data/notlar.db) açıkken, içeriği ne olursa olsun asla gösterilmez."""
    if Path(app.db_path).resolve() == Path(config.DEFAULT_DB_PATH).resolve():
        return []
    return demo_accounts(app.db)


class _DemoRow(tk.Frame):
    """Tek hesap satırı: kullanıcı adı, şifre ve "Kopyala". Satıra tıklamak alanları doldurur."""

    def __init__(self, parent, account: DemoAccount, panel: "DemoPanel", name_width: int):
        super().__init__(parent, background=SURFACE_LOW, cursor="hand2")
        self.account = account
        self.columnconfigure(2, weight=1)
        self._labels = [
            tk.Label(self, text=account.username, font=ROW_FONT, foreground=TEXT,
                     background=SURFACE_LOW, anchor="w", cursor="hand2", width=name_width),
            tk.Label(self, text=account.password, font=ROW_FONT, foreground=MUTED,
                     background=SURFACE_LOW, anchor="w", cursor="hand2"),
        ]
        self._labels[0].grid(row=0, column=0, sticky="w", padx=(4, 6), pady=2)
        self._labels[1].grid(row=0, column=1, sticky="w", pady=2)
        copy = tk.Label(self, text="Kopyala", font=FONT_SMALL, foreground=NAVY,
                        background=SURFACE_LOW, cursor="hand2")
        copy.grid(row=0, column=2, sticky="e", padx=(6, 4), pady=2)
        self._labels.append(copy)
        for widget in (self, *self._labels[:2]):  # satırın tamamı tıklanabilir
            widget.bind("<Button-1>", lambda _e: panel.pick(account))
        copy.bind("<Button-1>", lambda _e: panel.copy(account))
        for widget in (self, *self._labels):
            widget.bind("<Enter>", lambda _e: self._shade(SURFACE_HIGH))
            widget.bind("<Leave>", lambda _e: self._shade(SURFACE_LOW))

    def _shade(self, color: str) -> None:
        self.configure(background=color)
        for label in self._labels:
            label.configure(background=color)


class DemoPanel(tk.Frame):
    """Giriş kartının altındaki "Demo Hesapları" kutusu (yalnızca demo modunda).

    Hesaplar demo veritabanından okunur (app.demo_data.demo_accounts); burada
    sabit hesap yazılmaz. Öğretmenler ve öğrenciler iki sütunda listelenir.
    """

    def __init__(self, parent, accounts: list[DemoAccount], view: LoginView):
        super().__init__(parent, background=OUTLINE)  # 1 px çerçeve
        self.view = view
        self.rows: dict[str, _DemoRow] = {}
        inner = tk.Frame(self, background=SURFACE_LOW, padx=10, pady=8)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        inner.columnconfigure((0, 1), weight=1)
        name_width = max(len(a.username) for a in accounts)
        tk.Label(inner, text="Demo Hesapları", font=FONT_LABEL, foreground=TEXT,
                 background=SURFACE_LOW, anchor="w").grid(row=0, column=0, columnspan=2,
                                                          sticky="w")
        tk.Label(inner, text="Bir hesaba tıklayın, alanlar dolar; ardından Enter'a basın.",
                 font=FONT_SMALL, foreground=MUTED, background=SURFACE_LOW, anchor="w",
                 wraplength=340, justify="left").grid(row=1, column=0, columnspan=2,
                                                      sticky="w", pady=(0, 6))
        for column, (role, title) in enumerate((("teacher", "Öğretmenler"),
                                                ("student", "Öğrenciler"))):
            group = tk.Frame(inner, background=SURFACE_LOW)
            group.grid(row=2, column=column, sticky="new", padx=(0, 8) if column == 0 else 0)
            group.columnconfigure(0, weight=1)
            tk.Label(group, text=title, font=FONT_SMALL, foreground=MUTED,
                     background=SURFACE_LOW, anchor="w").grid(row=0, column=0, sticky="w",
                                                              padx=4)
            for index, account in enumerate(a for a in accounts if a.role == role):
                row = _DemoRow(group, account, self, name_width)
                row.grid(row=index + 1, column=0, sticky="ew")
                self.rows[account.username] = row

    def pick(self, account: DemoAccount) -> None:
        self.view.fill(account)

    def copy(self, account: DemoAccount) -> None:
        self.clipboard_clear()
        self.clipboard_append(f"{account.username}	{account.password}")
        self.view.app.set_status(f"{account.username} kullanıcı adı ve şifresi kopyalandı.")


class SetupView(ttk.Frame):
    """Hiç öğretmen hesabı yokken gösterilir: ilk öğretmen hesabı oluşturulur."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.vars = {key: tk.StringVar() for key in ("full_name", "username", "password",
                                                     "again")}
        _hero(self)
        card = _card(self, 520)
        ttk.Label(card, text="İlk Kurulum", style="SectionCard.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(card, text="Sistemde henüz öğretmen hesabı yok. Devam etmek için ilk "
                             "öğretmen hesabını oluşturun; sorumlusu atanmamış mevcut "
                             f"dersler bu hesaba atanır. {PASSWORD_HINT}",
                  style="CardMuted.TLabel", wraplength=370, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 10))
        body = ttk.Frame(card, style="Card.TFrame")
        body.grid(row=2, column=0, columnspan=2, sticky="ew")
        body.columnconfigure(1, weight=1)
        self.form = Form(body)
        specs = (("full_name", "Ad Soyad", "", "Ad Soyad"),
                 ("username", "Kullanıcı adı", "", "Kullanıcı adı"),
                 ("password", "Şifre", "•", "Şifre"),
                 ("again", "Şifre (tekrar)", "•", "Şifre (tekrar)"))
        for row, (key, label, show, alias) in enumerate(specs):
            entry = ttk.Entry(body, textvariable=self.vars[key], show=show)
            self.form.add(key, FormField(body, label, entry, row, required=True), alias)
            entry.bind("<Return>", lambda _e: self.submit())
        self.form.place_message(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(card, text="Hesabı Oluştur ve Giriş Yap", style="Accent.TButton",
                   command=self.submit).grid(row=3, column=0, columnspan=2, sticky="ew",
                                             pady=(16, 0))
        ttk.Label(card, text="* zorunlu alan", style="CardMuted.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def submit(self) -> None:
        values = {key: var.get() for key, var in self.vars.items()}

        def action():
            return self.app.auth_service.create_teacher(
                values["username"], values["full_name"], values["password"], values["again"])

        user = handle_errors(self.form, action)
        if user is not None:
            for var in self.vars.values():
                var.set("")
            self.app.login(user)
