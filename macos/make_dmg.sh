#!/bin/bash
# Baut Memex.app (release) und verpackt sie in ein teilbares DMG mit
# Drag-to-Applications-Layout.
#
#   ./make_dmg.sh        -> build/Memex-<version>.dmg
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Memex"
OUT_DIR="$HERE/build"
APP="$OUT_DIR/$APP_NAME.app"
VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$HERE/Info.plist" 2>/dev/null || echo 0.0.0)"
DMG="$OUT_DIR/${APP_NAME}-${VERSION}.dmg"

echo "== Memex DMG bauen (v$VERSION) =="

# 1) App bauen (inkl. eingebettetem Backend + Ressourcen)
"$HERE/build_app.sh"

# 2) Staging-Verzeichnis: App + Symlink auf /Applications + Chrome-Extension + Anleitung
STAGE="$(mktemp -d)/Memex"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/$APP_NAME.app"
ln -s /Applications "$STAGE/Applications"

# Chrome-Extension beilegen – ohne sie wird nichts archiviert.
cp -R "$HERE/../chrome-extension" "$STAGE/Memex Chrome-Extension"

# Kurzanleitung beilegen
cat > "$STAGE/Installation.txt" <<'TXT'
Memex – Installation
====================

1) APP INSTALLIEREN
   - "Memex" in den Ordner "Programme" (Applications) ziehen.
   - Erster Start: Rechtsklick auf Memex -> Öffnen -> im Dialog nochmals Öffnen.
     (Die App ist nicht über den App Store signiert.)
   - In der Menüleiste erscheint ein "M".

   Voraussetzung: macOS 15+ und ein vorhandenes Python 3.
   Falls keines da ist, im Terminal:  xcode-select --install

2) CHROME-EXTENSION INSTALLIEREN  (nötig fürs Archivieren!)
   - Den Ordner "Memex Chrome-Extension" aus diesem Fenster an einen festen
     Ort kopieren (z. B. nach Dokumente).
     WICHTIG: nicht direkt vom DMG laden – nach dem Auswerfen wäre sie weg.
   - In Chrome  chrome://extensions  öffnen.
   - Oben rechts "Entwicklermodus" einschalten.
   - "Entpackte Erweiterung laden" -> den kopierten Ordner auswählen.
   - Das violette "M" anpinnen.

3) LOSLEGEN
   - Eine SharePoint-/Intranet-Seite öffnen; Memex archiviert im Hintergrund.
   - Im Memex-Suchfenster ("Suche öffnen…") alles wiederfinden.

(c) Katrin Schwabel · katrin.schwabel@cgi.com · Alle Daten bleiben lokal.
TXT

# 3) Komprimiertes DMG erzeugen
rm -f "$DMG"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE" \
  -fs HFS+ \
  -format UDZO \
  -ov \
  "$DMG" >/dev/null

rm -rf "$(dirname "$STAGE")"

echo "Fertig: $DMG"
echo "Größe:  $(du -h "$DMG" | cut -f1)"
