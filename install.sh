#!/bin/bash
# Installations-Skript für Memex (macOS).
# Erstellt ein Python-venv, installiert rumps und legt einen launchd-Autostart an (optional).

set -euo pipefail

# Niemals als root / mit sudo ausführen: sonst gehören venv und Datenbank
# root und die App (die als normaler User läuft) kann nicht schreiben.
if [ "$(id -u)" -eq 0 ]; then
  echo "FEHLER: Bitte install.sh NICHT mit sudo / als root ausführen." >&2
  echo "        Sonst gehört das Memex-Verzeichnis root und die App kann" >&2
  echo "        keine Daten schreiben. Starte es einfach als normaler User:" >&2
  echo "          ./install.sh" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HERE/app"
BASE_DIR="$HOME/Library/Application Support/Memex"
VENV_DIR="$BASE_DIR/venv"
PLIST_PATH="$HOME/Library/LaunchAgents/com.local.memex.plist"

echo "== Memex – Installer =="
echo "App-Verzeichnis: $APP_DIR"
echo "Basis:           $BASE_DIR"
echo "venv:            $VENV_DIR"

mkdir -p "$BASE_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 wurde nicht gefunden. Bitte installieren (z. B. von https://www.python.org oder 'brew install python')." >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
echo "Python-Version: $PY_VER"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

# ---- Apple Silicon Check -------------------------------------------------
MAC_ARCH="$(uname -m)"
if [ "$MAC_ARCH" = "arm64" ]; then
  PY_ARCH="$("$VENV_DIR/bin/python" -c 'import platform; print(platform.machine())')"
  if [ "$PY_ARCH" != "arm64" ]; then
    echo
    echo "WARNUNG: Python läuft als ${PY_ARCH} (Rosetta 2) auf deinem Apple Silicon Mac."
    echo "Empfehlung: Installiere natives arm64-Python:"
    echo "  brew install python@3  ODER  https://www.python.org (macOS arm64 Installer)"
    echo "Danach install.sh erneut ausführen."
  fi
fi

# ---- Tkinter Check -------------------------------------------------------
echo
echo "Prüfe tkinter..."
if "$VENV_DIR/bin/python" -c "import tkinter" 2>/dev/null; then
  echo "tkinter: OK"
else
  PY_MIN="$("$VENV_DIR/bin/python" -c 'import sys; print(sys.version_info.minor)')"
  echo
  echo "FEHLER: tkinter fehlt – das Suchfenster wird nicht funktionieren!"
  if command -v brew >/dev/null 2>&1; then
    echo "Lösung (Homebrew):"
    echo "  brew install python-tk@3.${PY_MIN}"
    echo "Danach install.sh erneut ausführen."
  else
    echo "Lösung: Python von https://www.python.org installieren (enthält tkinter)."
  fi
fi

echo
read -r -p "Launchd-Autostart beim Login einrichten? [y/N] " AUTOSTART
if [[ "${AUTOSTART:-}" =~ ^[Yy]$ ]]; then
  # Alten Launchd-Eintrag (falls vorhanden) aufräumen
  OLD_PLIST="$HOME/Library/LaunchAgents/com.local.sharepoint-scraper.plist"
  if [ -f "$OLD_PLIST" ]; then
    launchctl unload "$OLD_PLIST" 2>/dev/null || true
    rm -f "$OLD_PLIST"
  fi
  mkdir -p "$(dirname "$PLIST_PATH")"
  cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.local.memex</string>
  <key>ProgramArguments</key>
  <array>
    <string>$VENV_DIR/bin/python</string>
    <string>$APP_DIR/main.py</string>
  </array>
  <key>WorkingDirectory</key><string>$APP_DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/memex.out.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/memex.err.log</string>
</dict>
</plist>
PLIST
  echo "Launchd-Datei angelegt: $PLIST_PATH"
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
  launchctl load  "$PLIST_PATH"
  echo "Autostart aktiv. Zum Deaktivieren:  launchctl unload '$PLIST_PATH'"
else
  echo "Autostart übersprungen. Du kannst Memex jederzeit starten mit:"
  echo "  '$VENV_DIR/bin/python' '$APP_DIR/main.py'"
fi

echo
echo "== Fertig =="
echo "Nächste Schritte:"
echo "  1) Memex starten (falls nicht per launchd):"
echo "     '$VENV_DIR/bin/python' '$APP_DIR/main.py'"
echo "  2) Chrome öffnen -> chrome://extensions -> Entwicklermodus aktivieren"
echo "  3) 'Entpackte Erweiterung laden' und den Ordner 'chrome-extension' wählen."
echo "  4) Das M-Icon in der Menüleiste -> 'Suche öffnen…'"
