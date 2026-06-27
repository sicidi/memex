"""
Wird als eigener Prozess gestartet, damit Tkinter seinen eigenen RunLoop
bekommt und nicht mit der rumps/AppKit-Schleife kollidiert.
"""

from __future__ import annotations

from db import Database, resolve_paths
from search_ui import SearchWindow


def main():
    db_path, files_dir = resolve_paths()
    db = Database(db_path=db_path, files_dir=files_dir)
    win = SearchWindow(db)
    win.open()
    win.mainloop()


if __name__ == "__main__":
    main()
