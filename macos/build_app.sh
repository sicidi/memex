#!/bin/bash
# Baut aus dem Swift-Package ein fertiges Memex.app-Bundle (reine Menüleisten-App).
#
#   ./build_app.sh            -> baut nach ./build/Memex.app
#   ./build_app.sh --install  -> baut und kopiert nach ~/Applications/Memex.app
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Memex"
CONFIG="release"
OUT_DIR="$HERE/build"
APP="$OUT_DIR/$APP_NAME.app"

echo "== Memex.app bauen =="
swift build -c "$CONFIG" --package-path "$HERE"
BIN="$(swift build -c "$CONFIG" --package-path "$HERE" --show-bin-path)/$APP_NAME"

# Bundle-Struktur anlegen
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/$APP_NAME"
cp "$HERE/Info.plist" "$APP/Contents/Info.plist"

# App-Icon (optional) aus app/app_icon.png erzeugen
ICON_SRC="$HERE/../app/app_icon.png"
if [ -f "$ICON_SRC" ]; then
  ICONSET="$(mktemp -d)/AppIcon.iconset"; mkdir -p "$ICONSET"
  for sz in 16 32 64 128 256 512; do
    sips -z "$sz" "$sz"   "$ICON_SRC" --out "$ICONSET/icon_${sz}x${sz}.png"      >/dev/null 2>&1 || true
    sips -z $((sz*2)) $((sz*2)) "$ICON_SRC" --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null 2>&1 || true
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns" 2>/dev/null || true
fi

# Ad-hoc-Signatur, damit macOS die App ohne Warnung startet
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true

echo "Fertig: $APP"

if [ "${1:-}" = "--install" ]; then
  DEST="$HOME/Applications/$APP_NAME.app"
  mkdir -p "$HOME/Applications"
  rm -rf "$DEST"
  cp -R "$APP" "$DEST"
  echo "Installiert: $DEST"
fi
