"""Form altyapısı: zorunlu alanlar, alan altında hata, tarih seçici, sayısal alanlar.

Servis katmanı ``ValidationError(message, field=...)`` fırlatır; ``Form`` bu alan
adını ilgili widget'a eşler, alanı kırmızı çerçeveyle işaretler, hatayı altında
gösterir ve odağı oraya taşır.
"""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

from app.errors import AppError, ValidationError
from app.ui.theme import MUTED, NAVY, NAVY_TINT, SURFACE, SURFACE_LOW, TEXT

MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
          "Eylül", "Ekim", "Kasım", "Aralık")
WEEKDAYS = ("Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pz")
DATE_FORMAT = "%d.%m.%Y"


# --------------------------------------------------------------- doğrulayıcılar
def _numeric_ok(proposed: str, allow_decimal: bool, max_length: int) -> bool:
    if proposed == "":
        return True
    if len(proposed) > max_length:
        return False
    allowed = "0123456789" + (".," if allow_decimal else "")
    if any(ch not in allowed for ch in proposed):
        return False
    return sum(proposed.count(sep) for sep in ".,") <= 1


def numeric_validator(widget: tk.Misc, allow_decimal: bool = True, max_length: int = 6):
    """Tuş vuruşu sırasında yalnızca sayı (ve tek ondalık ayırıcı) kabul eder."""
    command = widget.register(lambda proposed: _numeric_ok(proposed, allow_decimal, max_length))
    return {"validate": "key", "validatecommand": (command, "%P")}


# ---------------------------------------------------------------- form alanı
class FormField:
    """Etiket + widget + altında hata satırı."""

    def __init__(self, parent, label: str, widget: tk.Widget, row: int, column: int = 0,
                 required: bool = False, span: int = 1):
        self.widget = widget
        self.required = required
        text = f"{label} *" if required else label
        self.label = ttk.Label(parent, text=text, style="CardField.TLabel")
        self.label.grid(row=row * 2, column=column, sticky="w",
                        padx=(0 if column == 0 else 18, 10), pady=(6, 0))
        widget.grid(row=row * 2, column=column + 1, columnspan=span, sticky="ew", pady=(6, 0))
        self.error = ttk.Label(parent, text="", style="FieldError.TLabel")
        self.error.grid(row=row * 2 + 1, column=column + 1, columnspan=span, sticky="w")
        self._base_style = str(widget.cget("style")) if _is_ttk(widget) else ""

    def set_error(self, message: str) -> None:
        self.error.configure(text=message)
        if _is_ttk(self.widget):
            kind = self.widget.winfo_class()  # TEntry, TCombobox, TSpinbox
            self.widget.configure(style=f"Invalid.{kind}")
        elif isinstance(self.widget, DateField):
            self.widget.set_invalid(True)

    def clear(self) -> None:
        self.error.configure(text="")
        if _is_ttk(self.widget):
            self.widget.configure(style=self._base_style)
        elif isinstance(self.widget, DateField):
            self.widget.set_invalid(False)

    def focus(self) -> None:
        target = self.widget.entry if isinstance(self.widget, DateField) else self.widget
        target.focus_set()


def _is_ttk(widget) -> bool:
    return widget.winfo_class() in ("TEntry", "TCombobox", "TSpinbox")


class Form:
    """Alanları ve hata gösterimini yönetir."""

    def __init__(self, parent):
        self.parent = parent
        self.fields: dict[str, FormField] = {}
        self.aliases: dict[str, str] = {}
        self.message = ttk.Label(parent, text="", style="FormError.TLabel", wraplength=640)

    def add(self, key: str, field: FormField, *service_names: str) -> FormField:
        self.fields[key] = field
        for name in service_names:
            self.aliases[name] = key
        return field

    def place_message(self, **grid) -> None:
        self.message.grid(**grid)
        self.message.grid_remove()

    def clear_errors(self) -> None:
        for field in self.fields.values():
            field.clear()
        if self.message.winfo_manager():
            self.message.grid_remove()

    def show_error(self, exc: AppError) -> None:
        """Hatayı ilgili alanın altında; alan yoksa form mesajı olarak gösterir."""
        self.clear_errors()
        key = getattr(exc, "field", None)
        key = self.aliases.get(key, key)
        field = self.fields.get(key) if key else None
        if field is not None:
            field.set_error(str(exc))
            field.focus()
        else:
            self.message.configure(text=str(exc))
            self.message.grid()

    def widgets(self) -> list:
        result = []
        for field in self.fields.values():
            result.append(field.widget.entry if isinstance(field.widget, DateField)
                          else field.widget)
        return result


# ----------------------------------------------------------------- tarih alanı
class DateField(ttk.Frame):
    """GG.AA.YYYY biçiminde tarih girişi + takvimden seçim."""

    def __init__(self, parent, variable: tk.StringVar, width: int = 12):
        super().__init__(parent, style="Card.TFrame")
        self.variable = variable
        self.entry = ttk.Entry(self, textvariable=variable, width=width)
        self.entry.pack(side="left", fill="x", expand=True)
        self.button = ttk.Button(self, text="Takvim", width=0, command=self.open_calendar)
        self.button.pack(side="left", padx=(6, 0))
        self._popup: CalendarPopup | None = None

    def set_invalid(self, invalid: bool) -> None:
        self.entry.configure(style="Invalid.TEntry" if invalid else "TEntry")

    def current(self) -> date:
        try:
            return datetime.strptime(self.variable.get().strip(), DATE_FORMAT).date()
        except ValueError:
            try:
                return date.fromisoformat(self.variable.get().strip())
            except ValueError:
                return date.today()

    def open_calendar(self) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.lift()
            return
        self._popup = CalendarPopup(self, self.current(), self._picked)

    def _picked(self, value: date) -> None:
        self.variable.set(value.strftime(DATE_FORMAT))
        self.entry.focus_set()
        self.entry.icursor("end")


class CalendarPopup(tk.Toplevel):
    """Ay görünümlü takvim. Klavye: oklar gün değiştirir, Enter seçer, Esc kapatır."""

    def __init__(self, anchor: tk.Widget, selected: date, on_pick):
        super().__init__(anchor)
        self.withdraw()
        self.overrideredirect(True)
        self.configure(background=MUTED)
        self.on_pick = on_pick
        self.selected = selected
        self.shown = selected.replace(day=1)
        body = tk.Frame(self, background=SURFACE, padx=10, pady=10)
        body.pack(padx=1, pady=1)
        head = tk.Frame(body, background=SURFACE)
        head.pack(fill="x")
        ttk.Button(head, text="Önceki", width=0, command=lambda: self._move_month(-1)).pack(
            side="left")
        self.title_label = tk.Label(head, background=SURFACE, foreground=TEXT,
                                    font=("Segoe UI", 10, "bold"))
        self.title_label.pack(side="left", expand=True)
        ttk.Button(head, text="Sonraki", width=0, command=lambda: self._move_month(1)).pack(
            side="right")
        self.grid_frame = tk.Frame(body, background=SURFACE)
        self.grid_frame.pack(pady=(8, 6))
        foot = tk.Frame(body, background=SURFACE)
        foot.pack(fill="x")
        ttk.Button(foot, text="Bugün", width=0, command=lambda: self._pick(date.today())).pack(
            side="left")
        ttk.Button(foot, text="Kapat", width=0, command=self.destroy).pack(side="right")
        self._render()
        self._place(anchor)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._pick(self.selected))
        for key, delta in (("<Left>", -1), ("<Right>", 1), ("<Up>", -7), ("<Down>", 7)):
            self.bind(key, lambda _e, d=delta: self._move_day(d))
        self.bind("<FocusOut>", self._focus_out)
        self.deiconify()
        self.focus_force()

    def _place(self, anchor: tk.Widget) -> None:
        self.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 2
        screen_h = self.winfo_screenheight()
        if y + self.winfo_reqheight() > screen_h:
            y = anchor.winfo_rooty() - self.winfo_reqheight() - 2
        self.geometry(f"+{x}+{y}")

    def _focus_out(self, _event) -> None:
        focus = self.focus_get()
        if focus is None or not str(focus).startswith(str(self)):
            self.after(150, self._close_if_unfocused)

    def _close_if_unfocused(self) -> None:
        if not self.winfo_exists():
            return
        focus = self.focus_get()
        if focus is None or not str(focus).startswith(str(self)):
            self.destroy()

    def _move_month(self, delta: int) -> None:
        month = self.shown.month - 1 + delta
        self.shown = self.shown.replace(year=self.shown.year + month // 12, month=month % 12 + 1)
        self._render()

    def _move_day(self, delta: int) -> None:
        self.selected = date.fromordinal(self.selected.toordinal() + delta)
        self.shown = self.selected.replace(day=1)
        self._render()

    def _pick(self, value: date) -> None:
        self.on_pick(value)
        self.destroy()

    def _render(self) -> None:
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.title_label.configure(text=f"{MONTHS[self.shown.month - 1]} {self.shown.year}")
        for column, name in enumerate(WEEKDAYS):
            tk.Label(self.grid_frame, text=name, width=4, background=SURFACE,
                     foreground=MUTED, font=("Segoe UI", 9, "bold")).grid(row=0, column=column)
        today = date.today()
        month_calendar = calendar.Calendar(firstweekday=0)
        weeks = month_calendar.monthdatescalendar(self.shown.year, self.shown.month)
        for row, week in enumerate(weeks, start=1):
            for column, day in enumerate(week):
                in_month = day.month == self.shown.month
                selected = day == self.selected
                button = tk.Button(
                    self.grid_frame, text=str(day.day), width=3, relief="flat",
                    takefocus=0, cursor="hand2",
                    background=NAVY if selected else (NAVY_TINT if day == today else SURFACE),
                    foreground="#ffffff" if selected else (TEXT if in_month else "#9A9CA8"),
                    activebackground=SURFACE_LOW, font=("Segoe UI", 9),
                    command=lambda d=day: self._pick(d),
                )
                button.grid(row=row, column=column, padx=1, pady=1)


# ---------------------------------------------------------- yardımcı işlevler
def handle_errors(form: Form | None, action, on_success=None, parent=None):
    """``action()`` çalıştırır; ValidationError/AppError forma (yoksa kutuya) yazılır."""
    from tkinter import messagebox  # pylint: disable=import-outside-toplevel

    try:
        result = action()
    except ValidationError as exc:
        if form is not None:
            form.show_error(exc)
        else:
            messagebox.showerror("Geçersiz bilgi", str(exc), parent=parent)
        return None
    except AppError as exc:
        if form is not None:
            form.show_error(exc)
        else:
            messagebox.showerror("İşlem başarısız", str(exc), parent=parent)
        return None
    if form is not None:
        form.clear_errors()
    if on_success is not None:
        on_success(result)
    return result
