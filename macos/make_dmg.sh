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

# 2) Staging-Verzeichnis: App + Symlink auf /Applications
STAGE="$(mktemp -d)/Memex"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/$APP_NAME.app"
ln -s /Applications "$STAGE/Applications"

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
