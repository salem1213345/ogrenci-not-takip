"""Mesajlar ekranı (rol tabanlı) ve yeni mesaj penceresi."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from app.errors import AppError
from app.ui.common import clear_tree, make_tree, page_header, show_error
from app.ui.dialogs import Dialog
from app.ui.forms import FormField, handle_errors
from app.ui.theme import INPUT_BORDER, NAVY, SURFACE, SURFACE_LOW, TEXT, grid_card

TARGET_LABELS = {"student": "Öğrenci", "class": "Sınıf", "course": "Ders", "teacher": "Öğretmen"}


def format_datetime(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return value or ""


def _text_box(parent, height: int, editable: bool) -> tk.Text:
    if editable:
        widget = tk.Text(parent, wrap="word", height=height, font=("Segoe UI", 10),
                         background=SURFACE, foreground=TEXT, insertbackground=TEXT,
                         relief="flat", borderwidth=0, highlightthickness=1,
                         highlightbackground=INPUT_BORDER, highlightcolor=NAVY,
                         padx=10, pady=6)
        # Tab metne sekme eklemek yerine odağı taşır.
        widget.bind("<Tab>", lambda e: (e.widget.tk_focusNext().focus_set(), "break")[1])
        widget.bind("<Shift-Tab>", lambda e: (e.widget.tk_focusPrev().focus_set(), "break")[1])
        # Çok satırlı metinde Enter yeni satırdır (pencerenin "gönder" kısayolunu tetiklemez);
        # göndermek için Ctrl+Enter kullanılır.
        widget.bind("<Return>", lambda e: (e.widget.insert("insert", "\n"), "break")[1])
        widget.bind("<KP_Enter>", lambda e: (e.widget.insert("insert", "\n"), "break")[1])
        return widget
    return tk.Text(parent, wrap="word", height=height, font=("Segoe UI", 10),
                   background=SURFACE_LOW, foreground=TEXT, takefocus=0, relief="flat",
                   borderwidth=0, highlightthickness=0, padx=12, pady=10, state="disabled")


class MessagesView(ttk.Frame):
    """Gelen/gönderilen mesajlar; yalnızca oturumdaki kullanıcının mesajları."""

    # Dar başlangıç genişlikleri: sütunlar en küçük pencerede de kesilmez, fazlası paylaşılır.
    COLUMNS = (
        ("who", "Gönderen", 95, "w"),
        ("subject", "Konu", 95, "w"),
        ("date", "Tarih", 90, "w"),
    )

    def __init__(self, parent, app):
        super().__init__(parent, padding=(24, 16))
        self.app = app
        self.folder = "inbox"
        self.messages: dict[str, object] = {}
        self.current = None
        self.count_var = tk.StringVar()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        header = page_header(self, "Mesajlar", self.count_var)
        ttk.Button(header, text="Yeni Mesaj", style="Accent.TButton",
                   command=self.compose).pack(side="right", padx=(0, 16))
        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1, uniform="msg")
        body.columnconfigure(1, weight=1, uniform="msg")
        body.rowconfigure(0, weight=1)
        self._build_list(body)
        self._build_detail(body)

    # ----------------------------------------------------------- yerleşim
    def _build_list(self, body) -> None:
        listing = grid_card(body, 0, 0, sticky="nsew", padx=(0, 12))
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(1, weight=1)
        folders = ttk.Frame(listing, style="Card.TFrame")
        folders.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.inbox_button = ttk.Button(folders, style="Folder.TButton",
                                       command=lambda: self.show_folder("inbox"))
        self.inbox_button.pack(side="left")
        self.sent_button = ttk.Button(folders, text="Gönderilenler", style="Folder.TButton",
                                      command=lambda: self.show_folder("sent"))
        self.sent_button.pack(side="left", padx=(4, 0))
        holder, self.tree = make_tree(listing, self.COLUMNS, height=12)
        holder.grid(row=1, column=0, sticky="nsew")
        self.tree.tag_configure("unread", font=("Segoe UI", 10, "bold"))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_detail(self, body) -> None:
        detail = grid_card(body, 0, 1, sticky="nsew")
        detail.columnconfigure(0, weight=1)
        detail.rowconfigure(2, weight=1)
        self.subject_var = tk.StringVar(value="Mesaj seçilmedi")
        self.meta_var = tk.StringVar(value="Okumak için listeden bir mesaj seçin.")
        ttk.Label(detail, textvariable=self.subject_var, style="SectionCard.TLabel",
                  wraplength=460).grid(row=0, column=0, sticky="w")
        ttk.Label(detail, textvariable=self.meta_var, style="CardMuted.TLabel",
                  wraplength=460, justify="left").grid(row=1, column=0, sticky="w", pady=(4, 10))
        self.body_text = _text_box(detail, 8, editable=False)
        self.body_text.grid(row=2, column=0, sticky="nsew")
        self.reply_label = ttk.Label(detail, text="Yanıt", style="CardField.TLabel")
        self.reply_label.grid(row=3, column=0, sticky="w", pady=(12, 4))
        self.reply = _text_box(detail, 3, editable=True)
        self.reply.grid(row=4, column=0, sticky="ew")
        self.reply.bind("<Control-Return>", lambda _e: (self.send_reply(), "break")[1])
        actions = ttk.Frame(detail, style="Card.TFrame")
        actions.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(actions, text="Ctrl+Enter ile gönderilir.", style="CardMuted.TLabel").pack(
            side="left")
        self.reply_button = ttk.Button(actions, text="Yanıtla", style="Accent.TButton",
                                       command=self.send_reply)
        self.reply_button.pack(side="right")
        self._set_reply_enabled(False)

    # ------------------------------------------------------------- veri
    @property
    def user(self):
        return self.app.current_user

    def refresh(self) -> None:
        if self.user is None:
            return
        service = self.app.message_service
        try:
            unread = service.unread_count(self.user)
            rows = service.inbox(self.user) if self.folder == "inbox" else service.sent(self.user)
        except AppError as exc:
            show_error(self, exc)
            return
        self.inbox_button.configure(text=f"Gelen Kutusu ({unread})" if unread
                                    else "Gelen Kutusu")
        self.inbox_button.state(["selected" if self.folder == "inbox" else "!selected"])
        self.sent_button.state(["selected" if self.folder == "sent" else "!selected"])
        self.tree.heading("who", text="Gönderen" if self.folder == "inbox" else "Alıcı")
        selected = self.current.id if self.current else None
        clear_tree(self.tree)
        self.messages = {}
        for message in rows:
            iid = str(message.id)
            who = message.sender_name if self.folder == "inbox" else self._recipient(message)
            day = format_datetime(message.created_at)[:10]  # saat, ayrıntı panelinde
            self.tree.insert("", "end", iid=iid, values=(who, message.subject, day),
                             tags=("unread",) if message.is_unread else ())
            self.messages[iid] = message
        total = len(rows)
        self.count_var.set(f"{total} mesaj" + (f" · {unread} okunmamış" if unread else ""))
        if selected and str(selected) in self.messages:
            self.tree.selection_set(str(selected))
        else:
            self._show(None)

    @staticmethod
    def _recipient(message) -> str:
        kind = TARGET_LABELS.get(message.target_type, "")
        return f"{kind}: {message.target_label}" if kind else message.target_label

    def show_folder(self, folder: str) -> None:
        self.folder = folder
        self.current = None
        self.refresh()

    def reset(self) -> None:
        self.folder = "inbox"
        self.current = None
        clear_tree(self.tree)
        self._show(None)

    # ------------------------------------------------------------ olaylar
    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        message = self.messages.get(selection[0])
        if message is None:
            return
        if self.folder == "inbox" and message.is_unread:
            self.app.message_service.mark_read(self.user, message.id)
            self.tree.item(selection[0], tags=())
            self.app.update_unread()
            unread = self.app.message_service.unread_count(self.user)
            self.inbox_button.configure(text=f"Gelen Kutusu ({unread})" if unread
                                        else "Gelen Kutusu")
        self._show(message)

    def _show(self, message) -> None:
        self.current = message
        self.body_text.configure(state="normal")
        self.body_text.delete("1.0", "end")
        if message is None:
            self.subject_var.set("Mesaj seçilmedi")
            self.meta_var.set("Okumak için listeden bir mesaj seçin.")
            self._set_reply_enabled(False)
        else:
            self.subject_var.set(message.subject)
            when = format_datetime(message.created_at)
            if self.folder == "inbox":
                self.meta_var.set(f"Gönderen: {message.sender_name}   ·   {when}")
            else:
                self.meta_var.set(f"Alıcı: {self._recipient(message)}   ·   "
                                  f"{message.recipient_count} kişi   ·   {when}")
            self.body_text.insert("1.0", message.body)
            self._set_reply_enabled(self.folder == "inbox")
        self.body_text.configure(state="disabled")

    def _set_reply_enabled(self, enabled: bool) -> None:
        self.reply.configure(state="normal" if enabled else "disabled",
                             background=SURFACE if enabled else SURFACE_LOW)
        self.reply_button.state(["!disabled" if enabled else "disabled"])
        if not enabled:
            self.reply.configure(state="normal")
            self.reply.delete("1.0", "end")
            self.reply.configure(state="disabled")

    def send_reply(self) -> None:
        if self.current is None:
            return
        text = self.reply.get("1.0", "end").strip()
        result = handle_errors(None, lambda: self.app.message_service.reply(
            self.user, self.current.id, text), parent=self)
        if result is not None:
            self.reply.delete("1.0", "end")
            self.app.set_status(f"Yanıt gönderildi: {self.current.sender_name}")

    def compose(self) -> None:
        dialog = ComposeDialog(self, self.app)
        self.wait_window(dialog)
        if dialog.result:
            self.show_folder("sent")
            self.app.set_status("Mesaj gönderildi.")


class ComposeDialog(Dialog):
    """Yeni mesaj. Öğretmen: öğrenci / sınıf / ders; öğrenci: kendi öğretmenleri."""

    submit_text = "Gönder"

    def __init__(self, parent, app):
        self.app = app
        self.user = app.current_user
        self.kind = tk.StringVar(value="student" if self.user.is_teacher else "teacher")
        self.target = tk.StringVar()
        self.subject = tk.StringVar()
        self.options: dict[str, object] = {}
        intro = ("Derslerinize kayıtlı bir öğrenciye, bir sınıfa veya bir dersin tüm "
                 "öğrencilerine yazabilirsiniz." if self.user.is_teacher else
                 "Kayıtlı olduğunuz derslerin öğretmenlerine yazabilirsiniz.")
        super().__init__(parent, "Yeni Mesaj", intro)

    def build(self, card):
        row = 0
        if self.user.is_teacher:
            kinds = ttk.Frame(card, style="Card.TFrame")
            for value in ("student", "class", "course"):
                ttk.Radiobutton(kinds, text=TARGET_LABELS[value], value=value,
                                variable=self.kind, command=self._load_targets).pack(
                    side="left", padx=(0, 14))
            ttk.Label(card, text="Alıcı türü", style="CardField.TLabel").grid(
                row=0, column=0, sticky="w", padx=(0, 10), pady=(6, 0))
            kinds.grid(row=0, column=1, sticky="w", pady=(6, 0))
            row = 1
        self.target_combo = ttk.Combobox(card, textvariable=self.target, state="readonly",
                                         width=44)
        self.form.add("target", FormField(card, "Alıcı", self.target_combo, row,
                                          required=True), "Alıcı")
        self.form.add("subject", FormField(card, "Konu", ttk.Entry(
            card, textvariable=self.subject, width=46), row + 1, required=True), "Konu")
        self.body = _text_box(card, 7, editable=True)
        self.body.configure(width=46)
        self.body.bind("<Control-Return>", lambda _e: (self.submit(), "break")[1])
        self.form.add("body", FormField(card, "Mesaj", self.body, row + 2, required=True),
                      "Mesaj")
        self._load_targets()

    def _load_targets(self) -> None:
        service = self.app.message_service
        kind = self.kind.get()
        if kind == "teacher":
            self.options = {t.full_name: t.id
                            for t in service.teachers_of_student(self.user.student_id)}
        elif kind == "student":
            self.options = {f"{r['student_no']} - {r['first_name']} {r['last_name']}":
                            r["student_id"] for r in service.students_of_teacher(self.user.id)}
        elif kind == "class":
            self.options = {f"{year}. Sınıf": year
                            for year in service.class_years_of_teacher(self.user.id)}
        else:
            self.options = {course.label: course.id
                            for course in self.app.course_service.for_teacher(self.user.id)}
        self.target_combo["values"] = list(self.options)
        self.target.set(next(iter(self.options), ""))

    def action(self):
        service, kind = self.app.message_service, self.kind.get()
        target = self.options.get(self.target.get())
        body = self.body.get("1.0", "end").strip()
        senders = {
            "teacher": service.send_to_teacher,
            "student": service.send_to_student,
            "class": service.send_to_class,
            "course": service.send_to_course,
        }
        return senders[kind](self.user, target, self.subject.get(), body)


def confirm_discard(parent) -> bool:
    return messagebox.askyesno("Kaydedilmemiş değişiklikler",
                               "Kaydedilmemiş değişiklikler var. Yine de çıkılsın mı?",
                               parent=parent)
