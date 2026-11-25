"""AkademiPusula görsel dili için Tkinter tema belirteçleri ve bileşenler.

Renk, tipografi ve boşluk değerleri yeni arayüz tasarım sisteminden alınmıştır.
Mevcut ekranlar da bu belirteçleri kullanarak aynı görsel dili paylaşır.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ------------------------------------------------------------------ renkler
NAVY = "#00236F"
NAVY_DARK = "#001A54"
NAVY_CONTAINER = "#1E3A8A"
NAVY_TINT = "#EFF0FF"
NAVY_TEXT = "#05297A"

TEAL = "#006A63"
TEAL_DARK = "#00534D"
TEAL_CONTAINER = "#99EFE5"
TEAL_TINT = "#E6F7F4"
TEAL_TEXT = "#003733"

AMBER = "#763300"
AMBER_CONTAINER = "#FFDBCA"
AMBER_TEXT = "#331200"

ERROR = "#BA1A1A"
ERROR_CONTAINER = "#FFDAD6"
SUCCESS = "#15803D"
SUCCESS_CONTAINER = "#DCFCE7"
WARNING = "#B45309"
WARNING_CONTAINER = "#FEF3C7"

BACKGROUND = "#FAF8FF"
SURFACE = "#FFFFFF"
SURFACE_LOW = "#F4F3FA"
SURFACE_HIGH = "#E9E7EF"
OUTLINE = "#C5C5D3"
# Giriş alanı kenarlığı: beyaz zemine karşı >= 3:1 kontrast (WCAG 1.4.11).
INPUT_BORDER = "#868898"
TEXT = "#1A1B21"
MUTED = "#444651"

# Eski modüllerin kullandığı adlar (geriye dönük uyumluluk).
BG = BACKGROUND
CARD = SURFACE
ACCENT = NAVY
ACCENT_DARK = NAVY_DARK
DANGER = ERROR

# ---------------------------------------------------------------- tipografi
FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"
FONT_BODY = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_LABEL = (FONT_FAMILY, 9, "bold")
FONT_TITLE = (FONT_FAMILY, 14, "bold")
FONT_HEADLINE = (FONT_FAMILY, 19, "bold")
FONT_DISPLAY = (FONT_FAMILY, 24, "bold")
FONT_MONO = (MONO_FAMILY, 10)

PAD_XS = 4
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24

RADIUS = 12


def register_fonts(root: tk.Misc) -> None:
    """Tasarımda kullanılan yazı tipleri yoksa yerel alternatifleri kullanır.

    Tkinter kurulumu Wix Madefor Display / Instrument Sans / Spline Sans Mono
    içermediğinden, aynı hiyerarşiyi Segoe UI ve Consolas ile kurarız.
    """
    try:
        root.tk.call("font", "exists", "TkDefaultFont")
    except tk.TclError:
        pass


def _palette(role: str) -> tuple[str, str, str, str]:  # pylint: disable=unused-argument
    """Resmi kurum görünümü için iki rol de aynı lacivert paleti kullanır."""
    return NAVY, NAVY_DARK, NAVY_TINT, NAVY_TEXT


def _configure_label_styles(style: ttk.Style, primary: str) -> None:
    style.configure(".", font=FONT_BODY, background=BACKGROUND, foreground=TEXT)
    style.configure("TFrame", background=BACKGROUND)
    style.configure("Card.TFrame", background=SURFACE, relief="flat")
    style.configure("Border.TFrame", background=OUTLINE)
    style.configure("Soft.TFrame", background=SURFACE_LOW)
    style.configure("TLabel", background=BACKGROUND, foreground=TEXT)
    style.configure("Card.TLabel", background=SURFACE, foreground=TEXT)
    style.configure("Soft.TLabel", background=SURFACE_LOW, foreground=TEXT)
    style.configure("SoftSection.TLabel", font=FONT_TITLE, foreground=primary,
                    background=SURFACE_LOW)
    style.configure("SoftMuted.TLabel", font=FONT_SMALL, foreground=MUTED,
                    background=SURFACE_LOW)
    style.configure("CardField.TLabel", font=FONT_LABEL, foreground=TEXT,
                    background=SURFACE)
    style.configure("CardTitle.TLabel", font=(FONT_FAMILY, 11, "bold"), foreground=primary,
                    background=SURFACE)
    style.configure("Muted.TLabel", font=FONT_SMALL, foreground=MUTED,
                    background=BACKGROUND)
    style.configure("CardMuted.TLabel", font=FONT_SMALL, foreground=MUTED,
                    background=SURFACE)
    style.configure("Title.TLabel", font=FONT_HEADLINE, foreground=primary,
                    background=BACKGROUND)
    style.configure("Subtitle.TLabel", font=FONT_SMALL, foreground=MUTED,
                    background=BACKGROUND)
    style.configure("Section.TLabel", font=FONT_TITLE, foreground=TEXT,
                    background=BACKGROUND)
    style.configure("SectionCard.TLabel", font=FONT_TITLE, foreground=TEXT,
                    background=SURFACE)
    style.configure("Hero.TLabel", font=FONT_DISPLAY, foreground=primary,
                    background=BACKGROUND)
    style.configure("HeroCard.TLabel", font=FONT_DISPLAY, foreground=primary,
                    background=SURFACE)
    style.configure("Metric.TLabel", font=(FONT_FAMILY, 20, "bold"), foreground=primary,
                    background=SURFACE)
    style.configure("MetricText.TLabel", font=FONT_LABEL, foreground=MUTED,
                    background=SURFACE)
    style.configure("Summary.TLabel", font=(FONT_FAMILY, 11, "bold"), background=SURFACE)
    style.configure("SummaryValue.TLabel", font=(FONT_FAMILY, 14, "bold"),
                    foreground=primary, background=SURFACE)
    style.configure("Status.TLabel", background=SURFACE_LOW, foreground=MUTED,
                    padding=(12, 6))
    style.configure("Mono.TLabel", font=FONT_MONO, foreground=TEXT, background=SURFACE)


def _configure_badge_styles(style: ttk.Style) -> None:
    for name, foreground, background in (
        ("Neutral", NAVY_TEXT, NAVY_TINT),
        ("Success", SUCCESS, SUCCESS_CONTAINER),
        ("Warning", WARNING, WARNING_CONTAINER),
        ("Danger", ERROR, ERROR_CONTAINER),
    ):
        style.configure(
            f"Badge{name}.TLabel", font=FONT_SMALL, foreground=foreground,
            background=background, padding=(8, 2),
        )


def _configure_button_styles(style: ttk.Style, primary: str, primary_dark: str,
                             tint: str, primary_text: str) -> None:
    style.configure("TButton", padding=(12, 7), font=FONT_BODY, background=SURFACE,
                    foreground=TEXT, borderwidth=1)
    style.map("TButton", background=[("active", SURFACE_LOW)])
    style.configure("Accent.TButton", background=primary, foreground="#ffffff",
                    borderwidth=0, padding=(14, 8), font=FONT_LABEL)
    # Pasif düğmeler açıkça gri görünür (etkin gibi algılanmaz).
    style.map("Accent.TButton",
              background=[("disabled", SURFACE_HIGH), ("active", primary_dark),
                          ("pressed", primary_dark)],
              foreground=[("disabled", MUTED)])
    style.configure("Danger.TButton", background=ERROR, foreground="#ffffff",
                    borderwidth=0, padding=(14, 8), font=FONT_LABEL)
    style.map("Danger.TButton",
              background=[("disabled", SURFACE_HIGH), ("active", "#93000A"),
                          ("pressed", "#690005")],
              foreground=[("disabled", MUTED)])
    style.map("TButton", foreground=[("disabled", "#8E90A0")])
    style.configure("Nav.TButton", background=primary, foreground="#ffffff",
                    borderwidth=0, padding=(16, 14), font=FONT_LABEL)
    style.map("Nav.TButton",
              background=[("active", primary_dark), ("selected", primary_dark)])
    for name, background, foreground, padding, anchor in (
        ("SideNav.TButton", BACKGROUND, TEXT, (16, 12), "w"),
        ("TopNav.TButton", SURFACE, MUTED, (10, 16), "center"),
    ):
        style.configure(name, background=background, foreground=foreground,
                        borderwidth=0, padding=padding, font=FONT_BODY, anchor=anchor)
        style.map(name,
                  background=[("active", SURFACE_LOW), ("selected", tint)],
                  foreground=[("selected", primary_text)])
    # clam temasındaki 11 karakterlik asgari genişlik kaldırılır; üst menü
    # 1000 px pencereye sığar, kısa etiketler gereksiz yer kaplamaz.
    style.configure("TopNav.TButton", width=0)
    style.configure("Brand.TLabel", font=(FONT_FAMILY, 13, "bold"),
                    foreground=primary, background=SURFACE)
    style.configure("BrandMuted.TLabel", font=FONT_SMALL,
                    foreground=MUTED, background=SURFACE)


def _configure_input_styles(style: ttk.Style, primary: str, tint: str,
                            primary_text: str = NAVY_TEXT) -> None:
    style.configure("TLabelframe", background=SURFACE, bordercolor=OUTLINE, relief="flat")
    style.configure("TLabelframe.Label", background=SURFACE, foreground=primary,
                    font=FONT_LABEL)
    for name, padding in (("TEntry", 7), ("TCombobox", 6), ("TSpinbox", 6)):
        style.configure(name, padding=padding, fieldbackground=SURFACE,
                        bordercolor=INPUT_BORDER, lightcolor=SURFACE, darkcolor=SURFACE,
                        arrowcolor=TEXT)
        # Odaktaki alan rol rengiyle belirginleşir (görünür odak, WCAG 2.4.7).
        style.map(name,
                  bordercolor=[("focus", primary)],
                  lightcolor=[("focus", tint)],
                  fieldbackground=[("readonly", SURFACE), ("disabled", SURFACE_LOW)])
    # Salt okunur açılır listeler gri değil, diğer alanlar gibi beyaz görünür.
    # clam teması odaktaki salt okunur listenin yazısını beyaz (seçim rengi) çizer;
    # zemin de beyaz olunca yazı kaybolur. Odakta açık lacivert zemin + koyu yazı.
    style.map("TCombobox",
              fieldbackground=[("readonly", "focus", tint), ("readonly", SURFACE),
                               ("disabled", SURFACE_LOW)],
              foreground=[("readonly", "focus", TEXT), ("disabled", MUTED)],
              selectbackground=[("readonly", "focus", tint), ("readonly", SURFACE)],
              selectforeground=[("readonly", TEXT)],
              background=[("readonly", SURFACE), ("active", SURFACE_LOW)])
    style.configure("TCheckbutton", background=SURFACE)
    style.configure("Treeview", rowheight=30, background=SURFACE,
                    fieldbackground=SURFACE, borderwidth=0, font=FONT_BODY)
    style.configure("Treeview.Heading", font=FONT_LABEL, background=SURFACE_LOW,
                    foreground=TEXT, relief="flat", padding=(8, 8))
    style.map("Treeview", background=[("selected", tint)],
              foreground=[("selected", TEXT)])
    style.map("Treeview.Heading", background=[("active", SURFACE_HIGH)])
    style.layout("Hidden.TNotebook", [("Hidden.TNotebook.client", {"sticky": "nswe"})])
    # Sekme başlıkları üst menüden yönetilir; boş düzen sekme şeridini gizler.
    style.layout("Hidden.TNotebook.Tab", [])
    style.configure("Hidden.TNotebook", background=BACKGROUND, borderwidth=0,
                    bordercolor=BACKGROUND, lightcolor=BACKGROUND, darkcolor=BACKGROUND)
    # Hatalı alan: kırmızı kenarlık (odakta da kırmızı kalır).
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(f"Invalid.{name}", bordercolor=ERROR, lightcolor=ERROR_CONTAINER)
        style.map(f"Invalid.{name}", bordercolor=[("focus", ERROR)],
                  lightcolor=[("focus", ERROR_CONTAINER)],
                  fieldbackground=[("readonly", SURFACE)])
    style.configure("FieldError.TLabel", font=FONT_SMALL, foreground=ERROR, background=SURFACE)
    style.configure("FormError.TLabel", font=FONT_SMALL, foreground=ERROR,
                    background=ERROR_CONTAINER, padding=(10, 6))
    style.configure("Link.TLabel", font=FONT_BODY, foreground=NAVY_TEXT, background=BACKGROUND)
    style.configure("Crumb.TLabel", font=FONT_BODY, foreground=MUTED, background=BACKGROUND)
    style.configure("CrumbCurrent.TLabel", font=FONT_LABEL, foreground=TEXT,
                    background=BACKGROUND)
    style.configure("Folder.TButton", background=SURFACE, foreground=MUTED, borderwidth=0,
                    padding=(12, 8), font=FONT_BODY, width=0)
    style.map("Folder.TButton", background=[("selected", tint), ("active", SURFACE_LOW)],
              foreground=[("selected", primary_text)])
    style.configure("Header.TLabel", font=FONT_LABEL, foreground=TEXT, background=SURFACE)
    style.configure("HeaderMuted.TLabel", font=FONT_SMALL, foreground=MUTED, background=SURFACE)


def configure_styles(root: tk.Misc, role: str = "teacher") -> None:
    """Tüm uygulama stillerini rol renk paletine göre yapılandırır."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    primary, primary_dark, tint, primary_text = _palette(role)
    root.configure(background=BACKGROUND)
    _configure_label_styles(style, primary)
    _configure_badge_styles(style)
    _configure_button_styles(style, primary, primary_dark, tint, primary_text)
    _configure_input_styles(style, primary, tint, primary_text)


# ---------------------------------------------------------------- yardımcılar
def bordered(parent, style: str = "Card.TFrame", **kwargs) -> ttk.Frame:
    """İnce çizgili bir kart çerçevesi döndürür."""
    outer = ttk.Frame(parent, style="Border.TFrame", **kwargs)
    inner = ttk.Frame(outer, style=style, padding=1)
    inner.pack(fill="both", expand=True)
    return inner


def grid_card(parent, row: int, column: int, **grid_kwargs) -> ttk.Frame:
    """Grid içine yerleştirilmeye hazır kart döndürür."""
    outer = ttk.Frame(parent, style="Border.TFrame")
    outer.grid(row=row, column=column, **grid_kwargs)
    inner = ttk.Frame(outer, style="Card.TFrame", padding=16)
    inner.pack(fill="both", expand=True)
    return inner


def pack_card(parent, **pack_kwargs) -> ttk.Frame:
    """Pack içine yerleştirilmeye hazır kart döndürür."""
    outer = ttk.Frame(parent, style="Border.TFrame")
    outer.pack(**pack_kwargs)
    inner = ttk.Frame(outer, style="Card.TFrame", padding=16)
    inner.pack(fill="both", expand=True)
    return inner


def stat_card(parent, caption: str, value: str, detail: str = "",
              tone: str = "primary") -> ttk.Frame:
    """Tek satırlık metrik kartı (Ana Sayfa / karne özetleri)."""
    palette = {
        "primary": (NAVY, NAVY_TINT),
        "secondary": (TEAL, TEAL_TINT),
        "tertiary": (AMBER, AMBER_CONTAINER),
        "success": (SUCCESS, SUCCESS_CONTAINER),
    }
    color = palette[tone][0]
    outer = ttk.Frame(parent, style="Border.TFrame")
    inner = ttk.Frame(outer, style="Card.TFrame", padding=(16, 14))
    inner.pack(fill="both", expand=True)
    tk.Frame(inner, background=color, height=3).pack(fill="x", pady=(0, 10))
    ttk.Label(inner, text=caption, style="MetricText.TLabel").pack(anchor="w")
    value_label = ttk.Label(inner, text=value, style="Metric.TLabel")
    value_label.pack(anchor="w", pady=(2, 0))
    if detail:
        ttk.Label(inner, text=detail, style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))
    # Değer etiketine doğrudan erişim: çağıranlar widget ağacında gezinmek zorunda kalmaz.
    outer.value_label = value_label
    return outer


def section_header(parent, title: str, subtitle: str = "", card: bool = True) -> ttk.Frame:
    """Bölüm başlığı + açıklama satırı."""
    holder = ttk.Frame(parent, style="Card.TFrame" if card else "TFrame")
    ttk.Label(holder, text=title,
              style="SectionCard.TLabel" if card else "Section.TLabel").pack(anchor="w")
    if subtitle:
        style = "CardMuted.TLabel" if card else "Muted.TLabel"
        ttk.Label(holder, text=subtitle, style=style).pack(anchor="w", pady=(2, 0))
    return holder


def badge(parent, text: str, tone: str = "neutral") -> ttk.Label:
    """Durum rozeti."""
    styles = {
        "neutral": "BadgeNeutral.TLabel",
        "success": "BadgeSuccess.TLabel",
        "warning": "BadgeWarning.TLabel",
        "danger": "BadgeDanger.TLabel",
    }
    return ttk.Label(parent, text=text, style=styles[tone])


def status_tone(status: str) -> str:
    """'Geçti' / 'Kaldı' metnini rozet Tonuna çevirir."""
    value = status.strip().lower()
    if "geç" in value:
        return "success"
    if "kal" in value or "başarısız" in value:
        return "danger"
    return "warning"
