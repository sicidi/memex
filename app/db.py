"""
Lokale SQLite-Datenbank mit FTS5-Volltextsuche.

Enthält drei Kern-Tabellen:
  pages  – besuchte/gecrawlte HTML-Seiten (Plaintext + vollständiges HTML)
  links  – alle auf einer Seite gefundenen Links (mit Crawling-Status)
  files  – lokal gespeicherte Binärdateien (PDF, PPTX, DOCX …) mit Metadaten

Volltextsuche über zwei FTS5-Indexe: pages_fts (Titel/Plaintext) und files_fts
(Dateiname/extrahierter Text).
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DEFAULT_BASE_DIR = Path.home() / "Library" / "Application Support" / "Memex"
LEGACY_BASE_DIR = Path.home() / "Library" / "Application Support" / "SharePointLocalScraper"
DEFAULT_DB_PATH = DEFAULT_BASE_DIR / "memex.db"
DEFAULT_FILES_DIR = DEFAULT_BASE_DIR / "files"


def resolve_paths() -> tuple[Path, Path]:
    """
    Ermittelt DB- und Files-Pfad. Wenn der neue Memex-Pfad leer ist, aber unter
    dem alten SharePointLocalScraper-Pfad schon eine DB liegt, nutzen wir den
    alten Pfad weiter (keine Datenmigration nötig).
    """
    new_db = DEFAULT_BASE_DIR / "memex.db"
    new_files = DEFAULT_BASE_DIR / "files"
    legacy_db = LEGACY_BASE_DIR / "scraper.db"
    legacy_files = LEGACY_BASE_DIR / "files"
    if not new_db.exists() and legacy_db.exists():
        return legacy_db, legacy_files
    return new_db, new_files


class Database:
    """Thread-safer SQLite-Wrapper mit FTS5-Indexen und Datei-Metadaten."""

    def __init__(self, db_path: Path | str | None = None, files_dir: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.files_dir = Path(files_dir) if files_dir else DEFAULT_FILES_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    # ------------------------------------------------------------------ schema

    def _init_schema(self):
        with self._lock, self._conn() as con:
            con.executescript(
                """
                -- Seiten ----------------------------------------------------
                CREATE TABLE IF NOT EXISTS pages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    url         TEXT NOT NULL UNIQUE,
                    title       TEXT NOT NULL DEFAULT '',
                    content     TEXT NOT NULL DEFAULT '',   -- sichtbarer Plaintext
                    html        TEXT NOT NULL DEFAULT '',   -- vollständiges HTML
                    hostname    TEXT NOT NULL DEFAULT '',
                    source      TEXT NOT NULL DEFAULT 'visit',  -- 'visit' | 'crawl'
                    first_seen  TEXT NOT NULL,
                    last_seen   TEXT NOT NULL,
                    visit_count INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_pages_last_seen ON pages(last_seen DESC);
                CREATE INDEX IF NOT EXISTS idx_pages_hostname  ON pages(hostname);

                -- FTS5 für Pages -------------------------------------------
                CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                    title, content, url, hostname,
                    content='pages',
                    content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2'
                );
                CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN
                    INSERT INTO pages_fts(rowid, title, content, url, hostname)
                    VALUES (new.id, new.title, new.content, new.url, new.hostname);
                END;
                CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN
                    INSERT INTO pages_fts(pages_fts, rowid, title, content, url, hostname)
                    VALUES ('delete', old.id, old.title, old.content, old.url, old.hostname);
                END;
                CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN
                    INSERT INTO pages_fts(pages_fts, rowid, title, content, url, hostname)
                    VALUES ('delete', old.id, old.title, old.content, old.url, old.hostname);
                    INSERT INTO pages_fts(rowid, title, content, url, hostname)
                    VALUES (new.id, new.title, new.content, new.url, new.hostname);
                END;

                -- Dateien ---------------------------------------------------
                CREATE TABLE IF NOT EXISTS files (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    url             TEXT NOT NULL UNIQUE,
                    sha256          TEXT NOT NULL,
                    filename        TEXT NOT NULL DEFAULT '',
                    mime_type       TEXT NOT NULL DEFAULT '',
                    size            INTEGER NOT NULL DEFAULT 0,
                    local_path      TEXT NOT NULL DEFAULT '',
                    extracted_text  TEXT NOT NULL DEFAULT '',
                    first_seen      TEXT NOT NULL,
                    last_seen       TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256);

                CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                    filename, extracted_text, url,
                    content='files',
                    content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2'
                );
                CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                    INSERT INTO files_fts(rowid, filename, extracted_text, url)
                    VALUES (new.id, new.filename, new.extracted_text, new.url);
                END;
                CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                    INSERT INTO files_fts(files_fts, rowid, filename, extracted_text, url)
                    VALUES ('delete', old.id, old.filename, old.extracted_text, old.url);
                END;
                CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
                    INSERT INTO files_fts(files_fts, rowid, filename, extracted_text, url)
                    VALUES ('delete', old.id, old.filename, old.extracted_text, old.url);
                    INSERT INTO files_fts(rowid, filename, extracted_text, url)
                    VALUES (new.id, new.filename, new.extracted_text, new.url);
                END;

                -- Links -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS links (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_page_id  INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
                    url             TEXT NOT NULL,
                    link_text       TEXT NOT NULL DEFAULT '',
                    discovered_at   TEXT NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'pending',
                    -- pending | fetched_page | fetched_file | error | skipped
                    error           TEXT NOT NULL DEFAULT '',
                    target_page_id  INTEGER REFERENCES pages(id) ON DELETE SET NULL,
                    target_file_id  INTEGER REFERENCES files(id) ON DELETE SET NULL,
                    UNIQUE(source_page_id, url)
                );
                CREATE INDEX IF NOT EXISTS idx_links_status ON links(status);
                CREATE INDEX IF NOT EXISTS idx_links_url    ON links(url);
                """
            )
            # Inkrementelle Migrationen (für ältere DBs ohne diese Spalten)
            self._migrate(con)

    def _migrate(self, con):
        existing_cols = {r[1] for r in con.execute("PRAGMA table_info(pages)")}
        if "html" not in existing_cols:
            con.execute("ALTER TABLE pages ADD COLUMN html TEXT NOT NULL DEFAULT ''")
        if "source" not in existing_cols:
            con.execute("ALTER TABLE pages ADD COLUMN source TEXT NOT NULL DEFAULT 'visit'")

    # ------------------------------------------------------------------ pages

    def upsert_page(
        self,
        url: str,
        title: str,
        content: str,
        html: str = "",
        hostname: str = "",
        source: str = "visit",
    ) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with self._lock, self._conn() as con:
            row = con.execute("SELECT id FROM pages WHERE url = ?", (url,)).fetchone()
            if row is None:
                cur = con.execute(
                    """
                    INSERT INTO pages (url, title, content, html, hostname, source,
                                       first_seen, last_seen, visit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (url, title, content, html, hostname, source, now, now),
                )
                return cur.lastrowid
            con.execute(
                """
                UPDATE pages
                   SET title       = ?,
                       content     = ?,
                       html        = CASE WHEN length(?) > 0 THEN ? ELSE html END,
                       hostname    = ?,
                       last_seen   = ?,
                       visit_count = visit_count + 1
                 WHERE id = ?
                """,
                (title, content, html, html, hostname, now, row["id"]),
            )
            return row["id"]

    def get_page(self, page_id: int) -> dict | None:
        with self._lock, self._conn() as con:
            row = con.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
            return dict(row) if row else None

    def page_id_by_url(self, url: str) -> int | None:
        with self._lock, self._conn() as con:
            row = con.execute("SELECT id FROM pages WHERE url = ?", (url,)).fetchone()
            return row["id"] if row else None

    def delete_page(self, page_id: int) -> None:
        with self._lock, self._conn() as con:
            con.execute("DELETE FROM pages WHERE id = ?", (page_id,))

    # ------------------------------------------------------------------ links

    def record_links(self, source_page_id: int, links: list[dict]) -> list[str]:
        """
        Schreibt Links in die DB (UNIQUE über source_page_id+url).
        Gibt die Liste der URLs zurück, die neu als 'pending' angelegt wurden
        (also tatsächlich gecrawlt werden sollten).
        """
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        to_crawl: list[str] = []
        with self._lock, self._conn() as con:
            for link in links:
                url = (link.get("href") or "").strip()
                if not url:
                    continue
                text = (link.get("text") or "").strip()[:500]
                try:
                    cur = con.execute(
                        """
                        INSERT INTO links (source_page_id, url, link_text, discovered_at, status)
                        VALUES (?, ?, ?, ?, 'pending')
                        """,
                        (source_page_id, url, text, now),
                    )
                    if cur.rowcount > 0:
                        to_crawl.append(url)
                except sqlite3.IntegrityError:
                    # Schon bekannt → nichts tun
                    pass
            # Zusätzlicher Deduplizierungsschritt: URLs, die bereits als file/page
            # erfolgreich erfasst wurden, brauchen wir nicht erneut zu crawlen.
            if to_crawl:
                placeholders = ",".join("?" * len(to_crawl))
                seen_pages = {r[0] for r in con.execute(
                    f"SELECT url FROM pages WHERE url IN ({placeholders})", to_crawl
                )}
                seen_files = {r[0] for r in con.execute(
                    f"SELECT url FROM files WHERE url IN ({placeholders})", to_crawl
                )}
                to_crawl = [u for u in to_crawl if u not in seen_pages and u not in seen_files]
        return to_crawl

    def mark_link(
        self,
        source_page_id: int,
        url: str,
        status: str,
        *,
        error: str = "",
        target_page_id: int | None = None,
        target_file_id: int | None = None,
    ) -> None:
        with self._lock, self._conn() as con:
            con.execute(
                """
                UPDATE links
                   SET status = ?, error = ?, target_page_id = ?, target_file_id = ?
                 WHERE source_page_id = ? AND url = ?
                """,
                (status, error, target_page_id, target_file_id, source_page_id, url),
            )

    def links_for_page(self, page_id: int) -> list[dict]:
        with self._lock, self._conn() as con:
            rows = con.execute(
                """
                SELECT id, url, link_text, discovered_at, status, error,
                       target_page_id, target_file_id
                  FROM links
                 WHERE source_page_id = ?
                 ORDER BY id
                """,
                (page_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ files

    def upsert_file(
        self,
        url: str,
        sha256: str,
        filename: str,
        mime_type: str,
        size: int,
        local_path: str,
        extracted_text: str = "",
    ) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with self._lock, self._conn() as con:
            row = con.execute("SELECT id FROM files WHERE url = ?", (url,)).fetchone()
            if row is None:
                cur = con.execute(
                    """
                    INSERT INTO files (url, sha256, filename, mime_type, size, local_path,
                                       extracted_text, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (url, sha256, filename, mime_type, size, local_path, extracted_text, now, now),
                )
                return cur.lastrowid
            con.execute(
                """
                UPDATE files
                   SET sha256 = ?, filename = ?, mime_type = ?, size = ?,
                       local_path = ?, extracted_text = ?, last_seen = ?
                 WHERE id = ?
                """,
                (sha256, filename, mime_type, size, local_path, extracted_text, now, row["id"]),
            )
            return row["id"]

    def get_file(self, file_id: int) -> dict | None:
        with self._lock, self._conn() as con:
            row = con.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
            return dict(row) if row else None

    def delete_file(self, file_id: int) -> None:
        with self._lock, self._conn() as con:
            row = con.execute("SELECT local_path FROM files WHERE id = ?", (file_id,)).fetchone()
            con.execute("DELETE FROM files WHERE id = ?", (file_id,))
        if row:
            try:
                Path(row["local_path"]).unlink(missing_ok=True)
            except Exception:
                pass

    # ------------------------------------------------------------------ search

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Kombinierte Suche über pages + files."""
        with self._lock, self._conn() as con:
            results: list[dict] = []

            if not query.strip():
                # Neueste Pages und Files gemischt
                rows = con.execute(
                    """
                    SELECT 'page' AS kind, id, url, title AS name, hostname,
                           last_seen, visit_count,
                           substr(content, 1, 240) AS snippet,
                           NULL AS mime_type, NULL AS local_path, NULL AS size
                      FROM pages
                    UNION ALL
                    SELECT 'file' AS kind, id, url, filename AS name, '' AS hostname,
                           last_seen, 1 AS visit_count,
                           substr(extracted_text, 1, 240) AS snippet,
                           mime_type, local_path, size
                      FROM files
                     ORDER BY last_seen DESC
                     LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [dict(r) for r in rows]

            fts_query = _sanitize_fts_query(query)

            # Pages
            for r in con.execute(
                """
                SELECT 'page' AS kind, p.id, p.url, p.title AS name, p.hostname,
                       p.last_seen, p.visit_count,
                       snippet(pages_fts, 1, '[', ']', ' … ', 12) AS snippet,
                       NULL AS mime_type, NULL AS local_path, NULL AS size,
                       bm25(pages_fts) AS rank
                  FROM pages_fts
                  JOIN pages p ON p.id = pages_fts.rowid
                 WHERE pages_fts MATCH ?
                 ORDER BY rank
                 LIMIT ?
                """,
                (fts_query, limit),
            ):
                results.append(dict(r))

            # Files
            for r in con.execute(
                """
                SELECT 'file' AS kind, f.id, f.url, f.filename AS name,
                       '' AS hostname, f.last_seen, 1 AS visit_count,
                       snippet(files_fts, 1, '[', ']', ' … ', 12) AS snippet,
                       f.mime_type, f.local_path, f.size,
                       bm25(files_fts) AS rank
                  FROM files_fts
                  JOIN files f ON f.id = files_fts.rowid
                 WHERE files_fts MATCH ?
                 ORDER BY rank
                 LIMIT ?
                """,
                (fts_query, limit),
            ):
                results.append(dict(r))

            # Gemischt sortieren nach rank
            results.sort(key=lambda r: r.get("rank", 0.0))
            return results[:limit]

    # ------------------------------------------------------------------ stats

    def stats(self) -> dict:
        with self._lock, self._conn() as con:
            n_pages = con.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
            n_files = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            n_links_pending = con.execute(
                "SELECT COUNT(*) FROM links WHERE status = 'pending'"
            ).fetchone()[0]
            n_links_done = con.execute(
                "SELECT COUNT(*) FROM links WHERE status IN ('fetched_page', 'fetched_file')"
            ).fetchone()[0]
            last_page = con.execute("SELECT MAX(last_seen) FROM pages").fetchone()[0]
            hosts = con.execute(
                "SELECT hostname, COUNT(*) AS c FROM pages GROUP BY hostname ORDER BY c DESC LIMIT 10"
            ).fetchall()
            total_bytes = con.execute("SELECT COALESCE(SUM(size),0) FROM files").fetchone()[0]
            return {
                "count": n_pages,                 # Kompat
                "pages": n_pages,
                "files": n_files,
                "links_pending": n_links_pending,
                "links_fetched": n_links_done,
                "files_bytes": total_bytes,
                "last_seen": last_page,
                "top_hosts": [dict(h) for h in hosts],
                "db_path": str(self.db_path),
                "files_dir": str(self.files_dir),
            }

    # ------------------------------------------------------------------ Kompat

    def delete(self, page_id: int) -> None:
        # alte UI nutzt delete() - Kompat-Shim
        self.delete_page(page_id)

    def get(self, page_id: int) -> dict | None:
        return self.get_page(page_id)


# --------------------------------------------------------------------- helpers


_FTS_SPECIALS = set('"()*:^')


def _sanitize_fts_query(q: str) -> str:
    """
    FTS5-Query aus freier User-Eingabe bauen. Positive Tokens mit AND verknüpfen,
    negative per "A NOT (B OR C)"-Form anhängen. Prefix-Suche ab 3 Zeichen.
    """
    tokens: list[str] = []
    buf: list[str] = []
    in_quotes = False
    for ch in q:
        if ch == '"':
            if in_quotes:
                tokens.append('"' + "".join(buf).replace('"', "") + '"')
                buf = []
                in_quotes = False
            else:
                if buf:
                    tokens.append("".join(buf))
                    buf = []
                in_quotes = True
            continue
        if in_quotes:
            buf.append(ch)
            continue
        if ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf))

    positives: list[str] = []
    negatives: list[str] = []
    for t in tokens:
        if not t:
            continue
        neg = t.startswith("-")
        if neg:
            t = t[1:]
        t = t.lstrip("+")
        if not t:
            continue
        if t.startswith('"') and t.endswith('"'):
            quoted = t
        else:
            safe = "".join(c for c in t if c not in _FTS_SPECIALS)
            if not safe:
                continue
            if len(safe) >= 3 and not safe.endswith("*"):
                quoted = f'"{safe}"*'
            else:
                quoted = f'"{safe}"'
        (negatives if neg else positives).append(quoted)

    if not positives and not negatives:
        return '""'
    pos_part = " AND ".join(positives) if positives else '""'
    if not negatives:
        return pos_part
    neg_part = " OR ".join(negatives)
    return f"({pos_part}) NOT ({neg_part})"
