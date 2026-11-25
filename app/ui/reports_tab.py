"""Rapor önizleme ve PDF/CSV dışa aktarma sekmesi."""

import os
import subprocess
import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app import config
from app.errors import AppError
from app.ui.common import CARD, TEXT, page_header, show_error
from app.ui.theme import OUTLINE, grid_card

ALL_LABEL = "Tüm sınıf (özet)"


class ReportsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(24, 16))
        self.app = app
        self.service = app.report_service
        self.student_service = app.student_service
        self.grade_service = app.grade_service
        self.course_service = app.course_service

        self.current_student_id: int | None = None
        self._student_map: dict[str, object] = {}
        self.student_var = tk.StringVar(value=ALL_LABEL)
        self.stats_var = tk.StringVar()

        self._build()
        self._update_preview()

    # -------------------------------------------------------------- görünüm
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        page_header(self, "Raporlar", self.stats_var)

        # Önizleme kartı: üstte öğrenci seçimi, altında rapor metni.
        card = grid_card(self, 1, 0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="Öğrenci:", style="Card.TLabel").pack(side="left")
        self.student_combo = ttk.Combobox(
            toolbar, textvariable=self.student_var, state="readonly", width=42
        )
        self.student_combo.pack(side="left", padx=(8, 8))
        self.student_combo.bind("<<ComboboxSelected>>", self._on_student_change)
        ttk.Button(toolbar, text="Önizlemeyi Yenile",
                   command=self._update_preview).pack(side="left")

        preview_box = ttk.Frame(card, style="Card.TFrame")
        preview_box.grid(row=1, column=0, sticky="nsew")
        preview_box.rowconfigure(0, weight=1)
        preview_box.columnconfigure(0, weight=1)

        self.preview = tk.Text(
            preview_box,
            wrap="none",
            font=("Consolas", 10),
            background=CARD,
            foreground=TEXT,
            relief="flat",
            padx=14,
            pady=12,
            state="disabled",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=OUTLINE,
            highlightcolor=OUTLINE,
        )
        self.preview.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(preview_box, orient="vertical", command=self.preview.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(preview_box, orient="horizontal", command=self.preview.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.preview.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # Dışa aktarma kartı: öğrenci karnesi ve sınıf raporu ayrı gruplar halinde.
        export = grid_card(self, 2, 0, sticky="ew", pady=(12, 0))
        export.columnconfigure(0, weight=1)
        ttk.Label(export, text="Dışa Aktar", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            export,
            text="Raporlar varsayılan olarak 'cikti' klasörüne kaydedilir; "
                 "Excel ile açmak için CSV dosyalarını kullanın.",
            style="CardMuted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 10))
        actions = ttk.Frame(export, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="ew")
        ttk.Button(actions, text="Öğrenci Karnesi (PDF)", style="Accent.TButton",
                   command=lambda: self._export_student("pdf")).pack(side="left")
        ttk.Button(actions, text="Öğrenci Karnesi (CSV)",
                   command=lambda: self._export_student("csv")).pack(side="left", padx=(6, 0))
        ttk.Separator(actions, orient="vertical").pack(side="left", fill="y", padx=16)
        ttk.Button(actions, text="Sınıf Raporu (PDF)",
                   command=lambda: self._export_class("pdf")).pack(side="left")
        ttk.Button(actions, text="Sınıf Raporu (CSV)",
                   command=lambda: self._export_class("csv")).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Çıktı Klasörünü Aç",
                   command=self._open_export_dir).pack(side="right")

    # --------------------------------------------------------------- yardımcı
    def _selected_student(self):
        if self.current_student_id is None:
            return None
        return self._student_map.get(self.student_var.get())

    def _set_preview(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _on_student_change(self, _event=None) -> None:
        student = self._student_map.get(self.student_var.get())
        self.current_student_id = student.id if student else None
        self._update_preview()

    def _update_preview(self) -> None:
        try:
            if self.current_student_id is None:
                text = self.service.class_preview()
            else:
                text = self.service.student_preview(self.current_student_id)
        except AppError as exc:
            show_error(self, exc)
            return
        self._set_preview(text)

    # --------------------------------------------------------------- dışa aktar
    def _export_student(self, extension: str) -> None:
        student = self._selected_student()
        if student is None:
            messagebox.showinfo(
                "Seçim gerekli",
                "Öğrenci karnesi için listeden bir öğrenci seçin.",
                parent=self,
            )
            return
        kind = extension.upper()
        config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Öğrenci karnesini {kind} olarak kaydet",
            initialdir=str(config.EXPORT_DIR),
            initialfile=f"karne_{student.student_no}_{date.today():%Y%m%d}.{extension}",
            defaultextension=f".{extension}",
            filetypes=[(f"{kind} dosyası", f"*.{extension}"), ("Tüm dosyalar", "*.*")],
        )
        if not path:
            return
        try:
            if extension == "pdf":
                target = self.service.student_pdf(student.id, path)
            else:
                target = self.service.student_csv(student.id, path)
        except (AppError, OSError) as exc:
            show_error(self, exc, "Rapor kaydedilemedi")
            return
        self._report_saved(target)

    def _export_class(self, extension: str) -> None:
        kind = extension.upper()
        config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Sınıf raporunu {kind} olarak kaydet",
            initialdir=str(config.EXPORT_DIR),
            initialfile=f"sinif_raporu_{date.today():%Y%m%d}.{extension}",
            defaultextension=f".{extension}",
            filetypes=[(f"{kind} dosyası", f"*.{extension}"), ("Tüm dosyalar", "*.*")],
        )
        if not path:
            return
        try:
            if extension == "pdf":
                target = self.service.class_pdf(path)
            else:
                target = self.service.class_csv(path)
        except (AppError, OSError) as exc:
            show_error(self, exc, "Rapor kaydedilemedi")
            return
        self._report_saved(target)

    def _report_saved(self, target: Path) -> None:
        self.app.set_status(f"Rapor kaydedildi: {target}")
        messagebox.showinfo(
            "Rapor hazır",
            f"Rapor kaydedildi:\n{target}",
            parent=self,
        )

    def _open_export_dir(self) -> None:
        folder = config.EXPORT_DIR
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(folder))  # pylint: disable=no-member  # yalnızca Windows
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])  # pylint: disable=consider-using-with
            else:
                subprocess.Popen(["xdg-open", str(folder)])  # pylint: disable=consider-using-with
        except OSError as exc:
            show_error(self, exc, "Klasör açılamadı")

    # ----------------------------------------------------------------- yenile
    def refresh(self) -> None:
        try:
            students = self.student_service.list()
            courses = self.course_service.count()
            grades = self.grade_service.count()
        except AppError as exc:
            show_error(self, exc)
            return

        self._student_map = {student.label: student for student in students}
        self.student_combo["values"] = [ALL_LABEL] + list(self._student_map)

        match = next(
            (student.label for student in students if student.id == self.current_student_id),
            None,
        )
        if match is None:
            self.current_student_id = None
            self.student_var.set(ALL_LABEL)
        else:
            self.student_var.set(match)

        self.stats_var.set(f"Öğrenci: {len(students)}   Ders: {courses}   Not: {grades}")
        self._update_preview()
