"""
Memex – Menüleisten-App (macOS).

Startet den lokalen HTTP-Server in einem Hintergrund-Thread und zeigt ein
Menü mit Aktionen: Suche öffnen, Pausieren, Statistik, Beenden.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import webbrowser
from pathlib import Path

import rumps

from db import Database, resolve_paths
import server as srv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("memex.app")

APP_NAME = "Memex"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Katrin Schwabel"
APP_AUTHOR_EMAIL = "katrin.schwabel@cgi.com"
HTTP_PORT = 8765

APP_DIR = Path(__file__).resolve().parent
MENUBAR_ICON = APP_DIR / "menubar.png"


class MemexApp(rumps.App):
    def __init__(self):
        db_path, files_dir = resolve_paths()
        icon = str(MENUBAR_ICON) if MENUBAR_ICON.exists() else None
        super().__init__(
            APP_NAME,
            title=None if icon else "M",
            icon=icon,
            template=True,
            quit_button=None,
        )
        try:
            self.db = Database(db_path=db_path, files_dir=files_dir)
        except PermissionError as exc:
            base = Path(db_path).parent
            rumps.alert(
                title="Keine Schreibrechte",
                message=(
                    f"Memex kann nicht auf sein Datenverzeichnis zugreifen:\n"
                    f"  {base}\n\n"
                    f"Vermutlich wurde install.sh mit sudo ausgeführt, sodass\n"
                    f"das Verzeichnis root gehört. So gibst du es dir zurück:\n\n"
                    f"  sudo chown -R \"$USER\":staff \\\n"
                    f"    \"{base}\"\n\n"
                    f"Details: {exc}"
                ),
            )
            raise SystemExit(1)

        try:
            self._server, self._server_thread = srv.start_server_thread(
                self.db, host="127.0.0.1", port=HTTP_PORT
            )
        except OSError as exc:
            # Port belegt → zweite Instanz oder Überrest eines alten Prozesses.
            log.warning("Port %s nicht verfügbar: %s – Server-loser Modus.", HTTP_PORT, exc)
            self._server = None
            self._server_thread = None

        self.menu = [
            rumps.MenuItem("Suche öffnen …", callback=self.open_search),
            rumps.MenuItem("Statistik anzeigen", callback=self.show_stats),
            None,
            rumps.MenuItem("Aufzeichnung pausieren", callback=self.toggle_pause),
            rumps.MenuItem("Datenbank im Finder zeigen", callback=self.reveal_db),
            rumps.MenuItem("Dateien-Ordner öffnen", callback=self.reveal_files),
            None,
            rumps.MenuItem(
                f"Server · http://127.0.0.1:{HTTP_PORT}" if self._server else f"Server · Port {HTTP_PORT} belegt",
                callback=self.open_server_url,
            ),
            None,
            rumps.MenuItem(f"Über {APP_NAME} / Impressum", callback=self.show_about),
            None,
            rumps.MenuItem(f"{APP_NAME} beenden", callback=self.quit_app),
        ]

    # -------------------------------------------------------------- callbacks

    def open_search(self, _sender=None):
        # Tkinter fehlt häufig bei Homebrew-Python auf Apple Silicon.
        try:
            import tkinter  # noqa: F401
        except ImportError:
            import platform
            minor = sys.version_info.minor
            major = sys.version_info.major
            arch = platform.machine()
            brew_hint = (
                f"\n\nLösung (Homebrew):\n  brew install python-tk@{major}.{minor}"
                if arch == "arm64" else ""
            )
            rumps.alert(
                title="Tkinter nicht gefunden",
                message=(
                    "Das Suchfenster benötigt tkinter, das in dieser\n"
                    "Python-Installation fehlt."
                    f"{brew_hint}\n\n"
                    "Alternativ: Python von https://www.python.org\n"
                    "installieren (enthält tkinter automatisch).\n\n"
                    "Danach install.sh erneut ausführen."
                ),
            )
            return
        # rumps läuft auf dem Main-Thread (AppKit); Tk in einem neuen Prozess
        # zu öffnen ist am stabilsten, sonst gibt es RunLoop-Konflikte.
        script = Path(__file__).with_name("search_ui_launcher.py")
        subprocess.Popen([sys.executable, str(script)], close_fds=True)

    def show_stats(self, _sender=None):
        s = self.db.stats()
        top = "\n".join(f"  {h['hostname']}: {h['c']}" for h in s["top_hosts"]) or "  (keine)"
        mb = (s.get("files_bytes", 0) or 0) / (1024 * 1024)
        rumps.alert(
            title=APP_NAME,
            message=(
                f"Seiten:       {s['pages']}\n"
                f"Dateien:      {s['files']}  ({mb:.1f} MB)\n"
                f"Links offen:  {s['links_pending']}  (gecrawlt: {s['links_fetched']})\n"
                f"Zuletzt:      {s['last_seen'] or '–'}\n\n"
                f"Top-Hosts:\n{top}\n\n"
                f"DB:    {s['db_path']}\n"
                f"Files: {s['files_dir']}"
            ),
        )

    def toggle_pause(self, sender):
        new = not srv.is_paused()
        srv.set_paused(new)
        sender.title = "Aufzeichnung fortsetzen" if new else "Aufzeichnung pausieren"

    def reveal_db(self, _sender=None):
        path = self.db.db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", "-R", str(path)], check=False)

    def reveal_files(self, _sender=None):
        path = self.db.files_dir
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(path)], check=False)

    def open_server_url(self, _sender=None):
        webbrowser.open(f"http://127.0.0.1:{HTTP_PORT}/ping")

    def show_about(self, _sender=None):
        rumps.alert(
            title=f"{APP_NAME} {APP_VERSION}",
            message=(
                f"Memex – dein lokales SharePoint-Archiv.\n"
                f"Inspiriert von Vannevar Bushs „As We May Think\u201c (1945).\n\n"
                f"Impressum / Urheber:\n"
                f"  {APP_AUTHOR}\n"
                f"  {APP_AUTHOR_EMAIL}\n\n"
                f"Alle Daten werden ausschließlich lokal auf diesem Mac\n"
                f"verarbeitet und gespeichert."
            ),
        )

    def quit_app(self, _sender=None):
        try:
            self._server.shutdown()
        except Exception:
            pass
        rumps.quit_application()


def main():
    MemexApp().run()


if __name__ == "__main__":
    main()
