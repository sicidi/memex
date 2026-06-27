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
import os
import sys
import threading
import time

from db import Database, resolve_paths
import server as srv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("memex.serve")

HTTP_PORT = 8765


def _watch_parent() -> None:
    """
    Beendet diesen Prozess, sobald der Eltern-Prozess (die SwiftUI-App, die uns
    gestartet hat) verschwindet. Robust auch bei Force-Quit/Absturz der App, wo
    kein sauberes SIGTERM mehr kommt. Wird nur aktiv, wenn wir tatsächlich ein
    Kind sind (ppid != 1 beim Start); bei manuellem Start aus der Shell bleibt
    der Prozess laufen, bis er regulär beendet wird.
    """
    start_ppid = os.getppid()
    if start_ppid == 1:
        return  # ohne erkennbaren Eltern-Prozess kein Watchdog
    while True:
        time.sleep(1.0)
        if os.getppid() != start_ppid:
            log.info("Eltern-Prozess (%s) beendet – Backend wird gestoppt.", start_ppid)
            os._exit(0)


def main() -> int:
    db_path, files_dir = resolve_paths()
    db = Database(db_path=db_path, files_dir=files_dir)
    log.info("DB: %s  Files: %s", db_path, files_dir)
    threading.Thread(target=_watch_parent, name="parent-watchdog", daemon=True).start()
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
