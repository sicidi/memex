"""
Memex – Suchfenster.

Hübsche Tkinter-UI mit Toolbar (Refresh, Filter-Chips), farbigen Typ-Badges
und einem Detail-Bereich. Doppelklick öffnet den DetailWindow aus viewer.py.
"""

from __future__ import annotations

import platform
import subprocess
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import ttk

from db import Database
from viewer import DetailWindow

# -------------------------------------------------------------- styling

PALETTE = {
    "bg":         "#faf8ff",
    "card":       "#ffffff",
    "ink":        "#1e1b4b",
    "muted":      "#6b7280",
    "accent":     "#7c3aed",
    "accent_dk":  "#4c1d95",
    "accent_bg":  "#f3f0ff",
    "border":     "#e7e5f1",
    "row_hover":  "#f3f0ff",
    "row_alt":    "#fbfaff",
    "badge_pg":   "#dcfce7",
    "badge_pg_fg":"#047857",
    "badge_fl":   "#fae8ff",
    "badge_fl_fg":"#a21caf",
}


def _fmt_ts(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.rstrip("Z"))
        # Relative Zeit bis heute
        now = datetime.utcnow()
        delta = now - dt
        if delta.days == 0:
            mins = int(delta.total_seconds() / 60)
            if mins < 1:
                return "vor wenigen Sekunden"
            if mins < 60:
                return f"vor {mins} Min."
            return f"vor {mins // 60} Std."
        if delta.days < 7:
            return f"vor {delta.days} Tg."
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ts


def _fmt_size(n: int | None) -> str:
    if not n:
        return ""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# -------------------------------------------------------------- window


class SearchWindow:
    FILTER_ALL = "all"
    FILTER_PAGES = "pages"
    FILTER_FILES = "files"

    def __init__(self, db: Database):
        self.db = db
        self.root: tk.Tk | None = None
        self._filter = self.FILTER_ALL
        self._last_query = ""

    # -------------------------------------------------------- window mgmt

    def open(self):
        if self.root is not None and self.root.winfo_exists():
            self.root.lift()
            self.root.focus_force()
            return
        self._build()

    def mainloop(self):
        if self.root is not None:
            self.root.mainloop()

    def _close(self):
        try:
            self.root.destroy()
        finally:
            self.root = None

    # -------------------------------------------------------- build

    def _build(self):
        self.root = tk.Tk()
        self.root.title("Memex")
        self.root.geometry("1080x720")
        self.root.configure(bg=PALETTE["bg"])
        self._apply_style()

        self._build_header()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        self._show_latest()

        self.root.bind("<Command-r>", lambda _e: self._refresh())
        self.root.bind("<Control-r>", lambda _e: self._refresh())
        self.root.bind("<Command-f>", lambda _e: self.entry.focus_set())
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _apply_style(self):
        style = ttk.Style(self.root)
        if platform.system() == "Darwin":
            try:
                style.theme_use("aqua")
            except tk.TclError:
                style.theme_use("clam")
        else:
            style.theme_use("clam")

        style.configure("TFrame", background=PALETTE["bg"])
        style.configure("Card.TFrame", background=PALETTE["card"])
        style.configure("TLabel", background=PALETTE["bg"], foreground=PALETTE["ink"])
        style.configure("Muted.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"])
        style.configure("Heading.TLabel", background=PALETTE["bg"], foreground=PALETTE["ink"],
                        font=("Helvetica", 18, "bold"))
        style.configure("Sub.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"],
                        font=("Helvetica", 12))

        style.configure("Treeview",
                        background=PALETTE["card"],
                        fieldbackground=PALETTE["card"],
                        foreground=PALETTE["ink"],
                        rowheight=30,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        font=("Helvetica", 11, "bold"),
                        background=PALETTE["bg"],
                        foreground=PALETTE["muted"])
        style.map("Treeview",
                  background=[("selected", PALETTE["accent_bg"])],
                  foreground=[("selected", PALETTE["accent_dk"])])

    # -------------------------------------------------------- header

    def _build_header(self):
        header = tk.Frame(self.root, bg=PALETTE["bg"])
        header.pack(fill=tk.X, padx=18, pady=(16, 6))

        logo = tk.Label(header, text="M", font=("Georgia", 22, "bold"),
                        bg=PALETTE["accent_dk"], fg="white",
                        width=2, padx=4, pady=2)
        logo.pack(side=tk.LEFT)

        txt = tk.Frame(header, bg=PALETTE["bg"])
        txt.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(txt, text="Memex", font=("Helvetica", 18, "bold"),
                 bg=PALETTE["bg"], fg=PALETTE["ink"]).pack(anchor="w")
        tk.Label(txt, text="Dein lokales SharePoint-Archiv",
                 font=("Helvetica", 11),
                 bg=PALETTE["bg"], fg=PALETTE["muted"]).pack(anchor="w")

    # -------------------------------------------------------- toolbar

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=PALETTE["bg"])
        bar.pack(fill=tk.X, padx=18, pady=(6, 8))

        # Suchfeld im „Pill"-Look
        search_card = tk.Frame(bar, bg=PALETTE["card"],
                               highlightthickness=1,
                               highlightbackground=PALETTE["border"],
                               highlightcolor=PALETTE["accent"])
        search_card.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(search_card, text="🔍", bg=PALETTE["card"], fg=PALETTE["muted"],
                 font=("Helvetica", 14), padx=10).pack(side=tk.LEFT)

        self.query_var = tk.StringVar()
        self.entry = tk.Entry(search_card, textvariable=self.query_var,
                              bd=0, bg=PALETTE["card"], fg=PALETTE["ink"],
                              font=("Helvetica", 14),
                              insertbackground=PALETTE["accent"])
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=8)
        self.entry.bind("<Return>", lambda _e: self._search())
        self.entry.bind("<KeyRelease>", lambda _e: self._maybe_live_search())
        self.entry.focus_set()

        clear = tk.Label(search_card, text="✕", bg=PALETTE["card"],
                         fg=PALETTE["muted"], font=("Helvetica", 11),
                         cursor="hand2", padx=8)
        clear.pack(side=tk.RIGHT)
        clear.bind("<Button-1>", lambda _e: self._clear_query())

        # Refresh + Stats
        right = tk.Frame(bar, bg=PALETTE["bg"])
        right.pack(side=tk.LEFT, padx=(10, 0))

        refresh_btn = tk.Button(right, text="⟳  Aktualisieren",
                                command=self._refresh, relief="flat", bd=0,
                                bg=PALETTE["accent"], fg="white",
                                activebackground=PALETTE["accent_dk"],
                                activeforeground="white",
                                font=("Helvetica", 12, "bold"),
                                padx=14, pady=8, cursor="hand2")
        refresh_btn.pack(side=tk.LEFT)

        # Filter-Chips
        chips = tk.Frame(self.root, bg=PALETTE["bg"])
        chips.pack(fill=tk.X, padx=18, pady=(0, 8))
        tk.Label(chips, text="Zeigen:", bg=PALETTE["bg"], fg=PALETTE["muted"],
                 font=("Helvetica", 11)).pack(side=tk.LEFT, padx=(0, 8))

        self._chips: dict[str, tk.Label] = {}
        for key, label in [(self.FILTER_ALL, "Alle"),
                           (self.FILTER_PAGES, "Seiten"),
                           (self.FILTER_FILES, "Dateien")]:
            chip = tk.Label(chips, text=label, font=("Helvetica", 11, "bold"),
                            padx=12, pady=4, cursor="hand2")
            chip.bind("<Button-1>", lambda _e, k=key: self._set_filter(k))
            chip.pack(side=tk.LEFT, padx=3)
            self._chips[key] = chip
        self._apply_filter_styles()

    def _apply_filter_styles(self):
        for key, chip in self._chips.items():
            if key == self._filter:
                chip.configure(bg=PALETTE["accent"], fg="white")
            else:
                chip.configure(bg=PALETTE["card"], fg=PALETTE["ink"])

    def _set_filter(self, key: str):
        self._filter = key
        self._apply_filter_styles()
        self._refresh()

    def _clear_query(self):
        self.query_var.set("")
        self._show_latest()

    def _maybe_live_search(self):
        # Live-Suche ab 3 Zeichen; leere Eingabe zeigt „Neueste"
        q = self.query_var.get().strip()
        if not q:
            self._show_latest()
        elif len(q) >= 3:
            self._search()

    # -------------------------------------------------------- body

    def _build_body(self):
        body = tk.Frame(self.root, bg=PALETTE["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 6))

        # Linke Spalte: Trefferliste
        left = tk.Frame(body, bg=PALETTE["card"],
                        highlightthickness=1,
                        highlightbackground=PALETTE["border"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cols = ("type", "name", "meta", "time")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("type", text="")
        self.tree.heading("name", text="Titel / Datei")
        self.tree.heading("meta", text="Herkunft")
        self.tree.heading("time", text="Zuletzt")
        self.tree.column("type", width=70, anchor=tk.W, stretch=False)
        self.tree.column("name", width=460, anchor=tk.W)
        self.tree.column("meta", width=220, anchor=tk.W)
        self.tree.column("time", width=120, anchor=tk.W)
        self.tree.tag_configure("row_even", background=PALETTE["card"])
        self.tree.tag_configure("row_odd",  background=PALETTE["row_alt"])
        self.tree.tag_configure("page_tag", foreground=PALETTE["badge_pg_fg"])
        self.tree.tag_configure("file_tag", foreground=PALETTE["badge_fl_fg"])
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _e: self._open_detail())
        self.tree.bind("<Return>",   lambda _e: self._open_detail())

        # Rechte Spalte: Vorschau-Kacheln
        right = tk.Frame(body, bg=PALETTE["bg"], width=320)
        right.pack(side=tk.LEFT, fill=tk.BOTH, padx=(12, 0))
        right.pack_propagate(False)

        self.preview_card = tk.Frame(right, bg=PALETTE["card"],
                                     highlightthickness=1,
                                     highlightbackground=PALETTE["border"])
        self.preview_card.pack(fill=tk.BOTH, expand=True)

        self.preview_title = tk.Label(self.preview_card, text="Kein Eintrag gewählt",
                                      bg=PALETTE["card"], fg=PALETTE["ink"],
                                      font=("Helvetica", 14, "bold"),
                                      anchor="w", justify="left", wraplength=290)
        self.preview_title.pack(fill=tk.X, padx=14, pady=(14, 4))

        self.preview_meta = tk.Label(self.preview_card, text="",
                                     bg=PALETTE["card"], fg=PALETTE["muted"],
                                     font=("Helvetica", 11),
                                     anchor="w", justify="left", wraplength=290)
        self.preview_meta.pack(fill=tk.X, padx=14)

        self.preview_url = tk.Label(self.preview_card, text="",
                                    bg=PALETTE["card"], fg=PALETTE["accent_dk"],
                                    font=("Menlo", 10), anchor="w", justify="left",
                                    wraplength=290, cursor="hand2")
        self.preview_url.pack(fill=tk.X, padx=14, pady=(6, 8))
        self.preview_url.bind("<Button-1>", lambda _e: self._open_selected_external())

        self.preview_snippet = tk.Label(
            self.preview_card, text="",
            bg=PALETTE["card"], fg=PALETTE["ink"],
            font=("Helvetica", 12), anchor="nw", justify="left", wraplength=290,
        )
        self.preview_snippet.pack(fill=tk.BOTH, expand=True, padx=14, pady=(8, 14))

        btns = tk.Frame(right, bg=PALETTE["bg"])
        btns.pack(fill=tk.X, pady=(10, 0))

        self.btn_detail = tk.Button(btns, text="Lesen / Details",
                                    command=self._open_detail,
                                    relief="flat", bd=0,
                                    bg=PALETTE["accent"], fg="white",
                                    activebackground=PALETTE["accent_dk"],
                                    activeforeground="white",
                                    font=("Helvetica", 12, "bold"),
                                    padx=12, pady=8, cursor="hand2")
        self.btn_detail.pack(fill=tk.X, pady=(0, 6))

        self.btn_preview = tk.Button(btns, text="Vorschau (Quick Look)",
                                     command=self._quicklook_selected,
                                     relief="flat", bd=0,
                                     bg=PALETTE["card"], fg=PALETTE["ink"],
                                     activebackground=PALETTE["accent_bg"],
                                     font=("Helvetica", 12), padx=12, pady=8,
                                     cursor="hand2")
        self.btn_preview.pack(fill=tk.X, pady=(0, 6))

        self.btn_open = tk.Button(btns, text="Im Browser / Finder öffnen",
                                  command=self._open_selected_external,
                                  relief="flat", bd=0,
                                  bg=PALETTE["card"], fg=PALETTE["ink"],
                                  activebackground=PALETTE["accent_bg"],
                                  font=("Helvetica", 12), padx=12, pady=8,
                                  cursor="hand2")
        self.btn_open.pack(fill=tk.X, pady=(0, 6))

        self.btn_delete = tk.Button(btns, text="Löschen",
                                    command=self._delete_selected,
                                    relief="flat", bd=0,
                                    bg=PALETTE["card"], fg="#b91c1c",
                                    activebackground="#fef2f2",
                                    font=("Helvetica", 12), padx=12, pady=8,
                                    cursor="hand2")
        self.btn_delete.pack(fill=tk.X)

    # -------------------------------------------------------- status

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=PALETTE["bg"])
        bar.pack(fill=tk.X, padx=18, pady=(6, 4))
        self.status_var = tk.StringVar(value="Bereit.")
        tk.Label(bar, textvariable=self.status_var,
                 bg=PALETTE["bg"], fg=PALETTE["muted"],
                 font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.total_var = tk.StringVar(value="")
        tk.Label(bar, textvariable=self.total_var,
                 bg=PALETTE["bg"], fg=PALETTE["muted"],
                 font=("Helvetica", 11)).pack(side=tk.RIGHT)

        # Impressum / Urheber-Footer
        footer = tk.Frame(self.root, bg=PALETTE["bg"])
        footer.pack(fill=tk.X, padx=18, pady=(0, 10))
        tk.Label(
            footer,
            text="Memex  ·  \u00a9 Katrin Schwabel  ·  katrin.schwabel@cgi.com  ·  Alle Daten bleiben lokal.",
            bg=PALETTE["bg"],
            fg=PALETTE["muted"],
            font=("Helvetica", 10),
        ).pack(side=tk.LEFT)

    # -------------------------------------------------------- data ops

    def _refresh(self):
        q = self.query_var.get().strip()
        if q:
            self._search()
        else:
            self._show_latest()

    def _search(self):
        q = self.query_var.get().strip()
        self._last_query = q
        try:
            results = self.db.search(q, limit=300)
        except Exception as e:
            self.status_var.set(f"Fehler: {e}")
            return
        filtered = self._apply_filter(results)
        info = f"{len(filtered)} Treffer für \u201e{q}\u201c" if q else f"{len(filtered)} Einträge"
        self._populate(filtered, info, total=len(results))

    def _show_latest(self):
        self._last_query = ""
        try:
            results = self.db.search("", limit=300)
        except Exception as e:
            self.status_var.set(f"Fehler: {e}")
            return
        filtered = self._apply_filter(results)
        self._populate(filtered, f"{len(filtered)} Einträge (zuletzt gesehen)",
                       total=len(results))

    def _apply_filter(self, results: list[dict]) -> list[dict]:
        if self._filter == self.FILTER_PAGES:
            return [r for r in results if r["kind"] == "page"]
        if self._filter == self.FILTER_FILES:
            return [r for r in results if r["kind"] == "file"]
        return results

    def _populate(self, results: list[dict], info: str, total: int | None = None):
        self.tree.delete(*self.tree.get_children())
        self._row_data: dict[str, dict] = {}
        for i, r in enumerate(results):
            iid = f"{r['kind']}:{r['id']}"
            if r["kind"] == "page":
                type_glyph = "●  Seite"
                tag_type = "page_tag"
                meta = r.get("hostname") or ""
            else:
                type_glyph = "◆  Datei"
                tag_type = "file_tag"
                size = _fmt_size(r.get("size"))
                mime = (r.get("mime_type") or "").split("/")[-1].upper() or ""
                meta = f"{mime} · {size}".strip(" ·")

            time_s = _fmt_ts(r.get("last_seen"))
            row_tag = "row_even" if i % 2 == 0 else "row_odd"

            self.tree.insert(
                "", tk.END, iid=iid,
                values=(type_glyph, r.get("name") or "(ohne Titel)", meta, time_s),
                tags=(tag_type, row_tag),
            )
            self._row_data[iid] = r

        self.status_var.set(info)
        if total is not None and total != len(results):
            self.total_var.set(f"(gefiltert aus {total} Gesamt)")
        else:
            self.total_var.set("")

        # Auswahl zurücksetzen
        self._set_preview(None)

        # Stats für Unterzeile
        s = self.db.stats()
        mb = (s.get("files_bytes", 0) or 0) / (1024 * 1024)
        self.total_var.set(
            (self.total_var.get() + "   " if self.total_var.get() else "") +
            f"DB: {s['pages']} Seiten · {s['files']} Dateien · {mb:.1f} MB"
        )

    # -------------------------------------------------------- selection

    def _selected_row(self) -> dict | None:
        sel = self.tree.selection()
        return self._row_data.get(sel[0]) if sel else None

    def _on_select(self, _event=None):
        self._set_preview(self._selected_row())

    def _set_preview(self, r: dict | None):
        if not r:
            self.preview_title.configure(text="Kein Eintrag gewählt")
            self.preview_meta.configure(text="")
            self.preview_url.configure(text="")
            self.preview_snippet.configure(text="Wähle einen Eintrag links aus,\num die Vorschau hier zu sehen.")
            return
        self.preview_title.configure(text=r.get("name") or "(ohne Titel)")
        if r["kind"] == "page":
            meta = r.get("hostname") or ""
            meta = f"Seite · {meta}" if meta else "Seite"
        else:
            meta = f"Datei · {r.get('mime_type') or '?'} · {_fmt_size(r.get('size'))}"
        self.preview_meta.configure(text=meta)
        self.preview_url.configure(text=r.get("url") or "")
        snippet = r.get("snippet") or "— kein Ausschnitt verfügbar —"
        self.preview_snippet.configure(text=snippet)

    # -------------------------------------------------------- actions

    def _open_detail(self):
        r = self._selected_row()
        if not r:
            return
        DetailWindow(self.db, r["kind"], int(r["id"]), parent=self.root).open()

    def _open_selected_external(self):
        r = self._selected_row()
        if not r:
            return
        if r["kind"] == "page":
            if r.get("url"):
                webbrowser.open(r["url"])
        else:
            path = r.get("local_path")
            if path:
                subprocess.run(["open", path], check=False)

    def _quicklook_selected(self):
        r = self._selected_row()
        if not r:
            return
        if r["kind"] == "file" and r.get("local_path"):
            subprocess.Popen(
                ["qlmanage", "-p", r["local_path"]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        else:
            # Für Seiten: im Browser öffnen (keine Quick-Look-Vorschau für URLs)
            self._open_selected_external()

    def _delete_selected(self):
        r = self._selected_row()
        if not r:
            return
        try:
            if r["kind"] == "page":
                self.db.delete_page(int(r["id"]))
            else:
                self.db.delete_file(int(r["id"]))
        except Exception as e:
            self.status_var.set(f"Löschen fehlgeschlagen: {e}")
            return
        self._refresh()
