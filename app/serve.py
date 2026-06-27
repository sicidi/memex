"""
Memex – Headless-Backend.

Startet ausschließlich den lokalen HTTP-Server (SQLite/FTS5 + Datei-Extraktion)
ohne jegliche GUI. Wird von der nativen SwiftUI-App (Memex.app) als Kindprozess
gestartet und beim Beenden der App wieder gestoppt.

Die Menüleiste und die Such-/Detail-Oberfläche übernimmt die SwiftUI-App; dieses
Skript ersetzt damit den GUI-Teil der früheren rumps-App (app/main.py).
"""

from __future__ import annotations

import logging
import sys

from db import Database, resolve_paths
import server as srv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("memex.serve")

HTTP_PORT = 8765


def main() -> int:
    db_path, files_dir = resolve_paths()
    db = Database(db_path=db_path, files_dir=files_dir)
    log.info("DB: %s  Files: %s", db_path, files_dir)
    try:
        # Blockierend, bis der Prozess beendet wird (z. B. SIGTERM von der App).
        srv.run_server(db, host="127.0.0.1", port=HTTP_PORT)
    except KeyboardInterrupt:
        log.info("Beendet (KeyboardInterrupt).")
    except OSError as exc:
        log.error("Server konnte nicht starten (Port %s belegt?): %s", HTTP_PORT, exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
