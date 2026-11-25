"""Tkinter ortak görünüm ayarları ve küçük yardımcılar."""

from tkinter import messagebox, ttk

from app.ui.theme import (  # noqa: F401  # pylint: disable=unused-import
    CARD,
    TEXT,
    configure_styles,
)


def make_tree(parent, columns, height: int = 12):
    """Kaydırma çubuklu bir Treeview döndürür: (container, tree).

    ``columns``: (anahtar, başlık, genişlik, hizalama) demetleri.
    """
    container = ttk.Frame(parent, style="Card.TFrame")
    keys = [column[0] for column in columns]
    tree = ttk.Treeview(
        container,
        columns=keys,
        show="headings",
        height=height,
        selectmode="browse",
    )
    for key, title, width, anchor in columns:
        # Başlık, sütun verisiyle aynı hizada durur (sola dayalı veriye sola dayalı başlık).
        tree.heading(key, text=title, anchor=anchor)
        tree.column(key, width=width, minwidth=60, anchor=anchor, stretch=True)

    yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    container.rowconfigure(0, weight=1)
    container.columnconfigure(0, weight=1)
    return container, tree


def page_header(parent, title: str, info_var=None, row: int = 0) -> ttk.Frame:
    """Sayfa başlığı (solda) ve isteğe bağlı kısa bilgi metni (sağda)."""
    header = ttk.Frame(parent)
    header.grid(row=row, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(header, text=title, style="Title.TLabel").pack(side="left")
    if info_var is not None:
        ttk.Label(header, textvariable=info_var, style="Muted.TLabel").pack(
            side="right", anchor="s"
        )
    return header


def card_label(parent, text: str, row: int, column: int) -> ttk.Label:
    """Kart içindeki form alanı etiketi (kartla aynı zemin rengi)."""
    label = ttk.Label(parent, text=text, style="Card.TLabel")
    label.grid(row=row, column=column, sticky="w", pady=4,
               padx=(0 if column == 0 else 18, 10))
    return label


def form_actions(parent, on_add, on_update, on_delete, on_clear) -> ttk.Frame:
    """Ortak form düğmeleri.

    Sık kullanılan işlemler solda (birincil "Ekle" ilk sırada); geri alınamayan
    "Sil" kazara tıklanmaması için ayrı tutulur ve en sağda durur.
    """
    actions = ttk.Frame(parent, style="Card.TFrame")
    ttk.Button(actions, text="Ekle", style="Accent.TButton", command=on_add).pack(side="left")
    ttk.Button(actions, text="Güncelle", command=on_update).pack(side="left", padx=(6, 0))
    ttk.Button(actions, text="Formu Temizle", command=on_clear).pack(side="left", padx=(6, 0))
    ttk.Button(actions, text="Sil", style="Danger.TButton", command=on_delete).pack(
        side="left", padx=(24, 0)
    )
    return actions


def bind_enter(widgets, callback) -> None:
    """Enter (ve sayısal tuş takımı Enter) tuşunu verilen işleme bağlar."""
    for widget in widgets:
        widget.bind("<Return>", lambda _event: callback())
        widget.bind("<KP_Enter>", lambda _event: callback())


def show_error(parent, exc: Exception, title: str = "İşlem başarısız") -> None:
    messagebox.showerror(title, str(exc), parent=parent)


def clear_tree(tree: ttk.Treeview) -> None:
    children = tree.get_children()
    if children:
        tree.delete(*children)
