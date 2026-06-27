"""
Detail-Viewer für gespeicherte Seiten und Dateien.

Zeigt den gescrapten Text lesbar an (wie in einem Reader-View), optional das
rohe HTML, die Liste aller Links der Seite, sowie — bei Dateien — Metadaten,
extrahierten Text und eine Quick-Look-Vorschau via `qlmanage`.
"""

from __future__ import annotations

import subprocess
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from db import Database

# ---------------------------------------------------------------- styling

PALETTE = {
    "bg":        "#faf8ff",
    "card":      "#ffffff",
    "ink":       "#1e1b4b",
    "muted":     "#6b7280",
    "accent":    "#7c3aed",
    "accent_bg": "#f3f0ff",
    "border":    "#e7e5f1",
    "badge_pg":  "#ecfdf5",
    "badge_pg_fg": "#047857",
    "badge_fl":  "#fdf4ff",
    "badge_fl_fg": "#a21caf",
    "ok":        "#047857",
    "err":       "#b91c1c",
    "warn":      "#b45309",
}


def _fmt_ts(ts: str | None) -> str:
    if not ts:
        return "–"
    try:
        s = ts.rstrip("Z")
        dt = datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


def _fmt_size(n: int | None) -> str:
    if not n:
        return "0 B"
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# ---------------------------------------------------------------- helpers


def _scroll_text(parent, *, font=None, wrap="word") -> tuple[tk.Text, ttk.Scrollbar]:
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.BOTH, expand=True)
    text = tk.Text(
        frame,
        wrap=wrap,
        font=font or ("Helvetica", 13),
        bg=PALETTE["card"],
        fg=PALETTE["ink"],
        relief="flat",
        padx=14,
        pady=12,
        spacing2=3,
        spacing3=6,
    )
    sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=sb.set)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    return text, sb


def _set_text(widget: tk.Text, content: str):
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", content or "")
    widget.configure(state=tk.DISABLED)


# ---------------------------------------------------------------- viewer


class DetailWindow:
    """Toplevel-Fenster, das eine einzelne Page oder File anzeigt."""

    def __init__(self, db: Database, kind: str, item_id: int, parent: tk.Misc | None = None):
        self.db = db
        self.kind = kind
        self.item_id = int(item_id)
        self.parent = parent
        self.win: tk.Toplevel | tk.Tk | None = None
        self.data: dict | None = None

    def open(self):
        self._load()
        if not self.data:
            return
        if self.parent is not None:
            self.win = tk.Toplevel(self.parent)
        else:
            self.win = tk.Tk()
        self.win.title(self._window_title())
        self.win.geometry("920x680")
        self.win.configure(bg=PALETTE["bg"])
        self._build()

    def _load(self):
        if self.kind == "page":
            self.data = self.db.get_page(self.item_id)
        else:
            self.data = self.db.get_file(self.item_id)

    def _window_title(self) -> str:
        if not self.data:
            return "Memex"
        name = self.data.get("title") or self.data.get("filename") or self.data.get("url") or ""
        return f"Memex – {name}"

    # ------------------------------------------------------------ layout

    def _build(self):
        header = tk.Frame(self.win, bg=PALETTE["bg"])
        header.pack(fill=tk.X, padx=14, pady=(14, 6))

        badge_bg = PALETTE["badge_pg"] if self.kind == "page" else PALETTE["badge_fl"]
        badge_fg = PALETTE["badge_pg_fg"] if self.kind == "page" else PALETTE["badge_fl_fg"]
        badge_text = "Seite" if self.kind == "page" else "Datei"
        badge = tk.Label(header, text=badge_text, bg=badge_bg, fg=badge_fg,
                         font=("Helvetica", 10, "bold"), padx=8, pady=2)
        badge.pack(side=tk.LEFT)

        title_text = (self.data.get("title") or self.data.get("filename")
                      or self.data.get("url") or "(ohne Titel)")
        title = tk.Label(header, text=title_text, bg=PALETTE["bg"], fg=PALETTE["ink"],
                         font=("Helvetica", 16, "bold"), anchor="w")
        title.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # Meta-Zeile (URL, Host, Zeitstempel)
        meta = tk.Frame(self.win, bg=PALETTE["bg"])
        meta.pack(fill=tk.X, padx=14, pady=(0, 8))
        url = self.data.get("url") or ""
        meta_parts = []
        if self.kind == "page":
            meta_parts.append(self.data.get("hostname") or "")
        else:
            meta_parts.append(self.data.get("mime_type") or "")
            meta_parts.append(_fmt_size(self.data.get("size")))
        meta_parts.append(_fmt_ts(self.data.get("last_seen")))
        meta_text = "  ·  ".join(p for p in meta_parts if p)
        tk.Label(meta, text=meta_text, bg=PALETTE["bg"], fg=PALETTE["muted"],
                 font=("Helvetica", 11)).pack(side=tk.LEFT)

        # Toolbar
        bar = tk.Frame(self.win, bg=PALETTE["bg"])
        bar.pack(fill=tk.X, padx=14, pady=(0, 8))
        if self.kind == "page":
            ttk.Button(bar, text="Im Browser öffnen", command=self._open_external).pack(side=tk.LEFT)
            ttk.Button(bar, text="URL kopieren", command=self._copy_url).pack(side=tk.LEFT, padx=6)
        else:
            ttk.Button(bar, text="Vorschau (Quick Look)", command=self._quicklook).pack(side=tk.LEFT)
            ttk.Button(bar, text="Öffnen", command=self._open_external).pack(side=tk.LEFT, padx=6)
            ttk.Button(bar, text="Im Finder zeigen", command=self._reveal).pack(side=tk.LEFT)
            ttk.Button(bar, text="URL kopieren", command=self._copy_url).pack(side=tk.LEFT, padx=6)

        # URL-Zeile separat (auswählbar)
        url_row = tk.Frame(self.win, bg=PALETTE["bg"])
        url_row.pack(fill=tk.X, padx=14, pady=(0, 10))
        url_entry = tk.Entry(url_row, font=("Menlo", 11), bg=PALETTE["card"],
                             fg=PALETTE["muted"], relief="flat", readonlybackground=PALETTE["card"])
        url_entry.insert(0, url)
        url_entry.configure(state="readonly")
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        # Tabs
        nb = ttk.Notebook(self.win)
        nb.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        if self.kind == "page":
            self._tab_text(nb, self.data.get("content") or "")
            self._tab_html(nb, self.data.get("html") or "")
            self._tab_links(nb)
            self._tab_info(nb)
        else:
            self._tab_preview(nb)
            self._tab_text(nb, self.data.get("extracted_text") or "", heading="Extrahierter Text")
            self._tab_info(nb)

        # Tastaturkürzel
        self.win.bind("<Command-w>", lambda _e: self.win.destroy())
        self.win.bind("<Escape>",     lambda _e: self.win.destroy())

    # ------------------------------------------------------------ tabs

    def _tab_text(self, nb: ttk.Notebook, content: str, heading: str = "Text"):
        frame = ttk.Frame(nb, padding=0)
        nb.add(frame, text=heading)
        text_widget, _ = _scroll_text(frame, font=("Helvetica", 13))
        if not content.strip():
            text_widget.configure(fg=PALETTE["muted"])
            content = "— kein extrahierter Text —"
        _set_text(text_widget, content)

    def _tab_html(self, nb: ttk.Notebook, html: str):
        frame = ttk.Frame(nb, padding=0)
        nb.add(frame, text="HTML-Quelltext")
        text_widget, _ = _scroll_text(frame, font=("Menlo", 11), wrap="none")
        _set_text(text_widget, html or "— kein HTML gespeichert —")

    def _tab_links(self, nb: ttk.Notebook):
        frame = ttk.Frame(nb, padding=0)
        nb.add(frame, text="Links")

        links = self.db.links_for_page(self.item_id)

        header = tk.Frame(frame, bg=PALETTE["bg"])
        header.pack(fill=tk.X, padx=10, pady=(10, 4))
        tk.Label(header, text=f"{len(links)} Links auf dieser Seite",
                 bg=PALETTE["bg"], fg=PALETTE["muted"],
                 font=("Helvetica", 11)).pack(side=tk.LEFT)

        cols = ("status", "kind", "link_text", "url")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=16)
        tree.heading("status", text="Status")
        tree.heading("kind",   text="Ziel")
        tree.heading("link_text", text="Link-Text")
        tree.heading("url",    text="URL")
        tree.column("status", width=120, anchor=tk.W)
        tree.column("kind",   width=90,  anchor=tk.W)
        tree.column("link_text", width=220, anchor=tk.W)
        tree.column("url",    width=420, anchor=tk.W)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 10))

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))

        labels = {
            "pending":       ("🕓 wartet",    None, None),
            "fetched_page":  ("✅ gespeichert","page", "target_page_id"),
            "fetched_file":  ("✅ gespeichert","file", "target_file_id"),
            "error":         ("⚠︎ Fehler",   None, None),
            "skipped":       ("— übersprungen", None, None),
        }
        self._link_rows: dict[str, dict] = {}
        for l in links:
            st_text, kind_text, _ = labels.get(l["status"], (l["status"], "", None))
            iid = str(l["id"])
            tree.insert("", tk.END, iid=iid, values=(
                st_text,
                {"page": "Seite", "file": "Datei"}.get(kind_text or "", "–"),
                (l.get("link_text") or "")[:80],
                l["url"],
            ))
            self._link_rows[iid] = l

        def open_selected(_e=None):
            sel = tree.selection()
            if not sel:
                return
            row = self._link_rows.get(sel[0])
            if not row:
                return
            # Wenn wir eine gespeicherte Kopie haben: Viewer auf Ziel öffnen
            if row["status"] == "fetched_page" and row.get("target_page_id"):
                DetailWindow(self.db, "page", row["target_page_id"], parent=self.win).open()
                return
            if row["status"] == "fetched_file" and row.get("target_file_id"):
                DetailWindow(self.db, "file", row["target_file_id"], parent=self.win).open()
                return
            # Fallback: URL im Browser öffnen
            if row.get("url"):
                webbrowser.open(row["url"])

        tree.bind("<Double-1>", open_selected)
        ttk.Button(frame, text="Öffnen", command=open_selected).pack(
            side=tk.LEFT, padx=10, pady=(0, 10))

    def _tab_info(self, nb: ttk.Notebook):
        frame = ttk.Frame(nb, padding=(16, 14, 16, 14))
        nb.add(frame, text="Info")

        rows: list[tuple[str, str]] = []
        if self.kind == "page":
            rows.append(("URL",         self.data.get("url") or ""))
            rows.append(("Titel",       self.data.get("title") or ""))
            rows.append(("Hostname",    self.data.get("hostname") or ""))
            rows.append(("Quelle",      {"visit": "Direkt besucht", "crawl": "Per Link gefunden"}
                                         .get(self.data.get("source") or "visit", self.data.get("source") or "")))
            rows.append(("Erstmals gesehen", _fmt_ts(self.data.get("first_seen"))))
            rows.append(("Zuletzt gesehen",  _fmt_ts(self.data.get("last_seen"))))
            rows.append(("Besuche",     str(self.data.get("visit_count") or 1)))
            rows.append(("Zeichen Text", str(len(self.data.get("content") or ""))))
            rows.append(("Zeichen HTML", str(len(self.data.get("html") or ""))))
        else:
            rows.append(("URL",         self.data.get("url") or ""))
            rows.append(("Dateiname",   self.data.get("filename") or ""))
            rows.append(("MIME-Typ",    self.data.get("mime_type") or ""))
            rows.append(("Größe",       _fmt_size(self.data.get("size"))))
            rows.append(("SHA-256",     self.data.get("sha256") or ""))
            rows.append(("Pfad",        self.data.get("local_path") or ""))
            rows.append(("Erstmals gesehen", _fmt_ts(self.data.get("first_seen"))))
            rows.append(("Zuletzt gesehen",  _fmt_ts(self.data.get("last_seen"))))
            rows.append(("Extrahierter Text", f"{len(self.data.get('extracted_text') or '')} Zeichen"))

        for i, (k, v) in enumerate(rows):
            tk.Label(frame, text=k, font=("Helvetica", 11, "bold"),
                     fg=PALETTE["muted"], bg="white", anchor="w").grid(
                row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            val = tk.Entry(frame, font=("Menlo", 11), relief="flat")
            val.insert(0, v)
            val.configure(state="readonly", readonlybackground="white", fg=PALETTE["ink"])
            val.grid(row=i, column=1, sticky="ew", pady=4)
        frame.grid_columnconfigure(1, weight=1)

    def _tab_preview(self, nb: ttk.Notebook):
        frame = ttk.Frame(nb, padding=(16, 14, 16, 14))
        nb.add(frame, text="Vorschau")

        path = self.data.get("local_path") or ""
        mime = (self.data.get("mime_type") or "").lower()

        # Bilder inline mit Tkinter anzeigen
        if mime.startswith("image/") and path and Path(path).exists():
            try:
                img = tk.PhotoImage(file=path)  # PNG/GIF direkt; JPEG funktioniert nur über PIL
                lbl = tk.Label(frame, image=img, bg="white")
                lbl.image = img  # keep reference
                lbl.pack(expand=True)
                return
            except Exception:
                pass  # Fallback unten

        # Hinweis + Button für Quick Look
        intro = tk.Label(
            frame,
            text="Klicke auf \u201eQuick Look\u201c, um eine native Vorschau von\n"
                 "macOS zu öffnen (PDF, Office-Dateien, Bilder, Text, ZIP …).",
            bg="white",
            fg=PALETTE["muted"],
            font=("Helvetica", 12),
            justify="center",
            pady=20,
        )
        intro.pack(pady=(20, 10))

        ttk.Button(frame, text="🔍  Quick Look",
                   command=self._quicklook).pack()

        if path:
            tk.Label(frame, text=path, bg="white", fg=PALETTE["muted"],
                     font=("Menlo", 10)).pack(pady=(20, 0))

    # ------------------------------------------------------------ actions

    def _open_external(self):
        if self.kind == "page":
            url = self.data.get("url")
            if url:
                webbrowser.open(url)
        else:
            path = self.data.get("local_path")
            if path:
                subprocess.run(["open", path], check=False)

    def _reveal(self):
        path = self.data.get("local_path")
        if path:
            subprocess.run(["open", "-R", path], check=False)

    def _quicklook(self):
        path = self.data.get("local_path")
        if not path:
            return
        # qlmanage -p öffnet ein nicht-modales Fenster mit Apples Quick Look
        subprocess.Popen(
            ["qlmanage", "-p", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    def _copy_url(self):
        url = self.data.get("url") or ""
        if not url or self.win is None:
            return
        self.win.clipboard_clear()
        self.win.clipboard_append(url)
