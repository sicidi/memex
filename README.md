# Memex

*„Consider a future device for individual use, which is a sort of mechanized
private file and library."* — Vannevar Bush, *As We May Think*, 1945.

**Memex** ist ein Mini-„Second Brain"-Datenwiederfinder für alles, was du in SharePoint
anschaust: Die Chrome-Extension archiviert im Hintergrund jede besuchte Seite
und die dort verlinkten Dateien (PDF, Powerpoint, Word, Excel …) in einer
**lokalen** SQLite-Datenbank. Du kannst später per Stichwort alles
wiederfinden, direkt im Fenster **lesen** und für Dateien eine **Quick-Look-
Vorschau** öffnen.

Und wichtig: Nichts davon verlässt deinen Mac.

---

## Was Memex macht

* **Chrome-Extension** – erkennt SharePoint-Seiten und schickt an die lokale
  App auf `http://127.0.0.1:8765`:
  * Titel, sichtbarer Plaintext, vollständiges HTML
  * Alle auf der Seite enthaltenen Links
  Anschließend lädt sie im Hintergrund die verlinkten Ziele mit deinen
  Browser-Cookies nach. HTML-Seiten werden als Seiten gespeichert;
  PDF/Office/Bilder/Textdateien werden als Dateien abgelegt.
* **Native macOS-App (SwiftUI)** – `Memex.app` zeigt ein schlichtes „M" in der
  Menüleiste und startet im Hintergrund das Python-Backend (lokaler HTTP-Server
  + SQLite/FTS5 + Datei-Textextraktion). Beim Beenden wird das Backend sauber
  mitgestoppt.
* **Such-Fenster** – natives SwiftUI-Fenster mit Live-Suche, Filter
  (Alle/Seiten/Dateien), Vorschau-Pane und einem Detail-Viewer mit Tabs für
  Text, HTML-Quelltext, Links und Metadaten. Für Dateien native Quick-Look-Vorschau.

---

## Projektstruktur

```
sharepoint-scraper/
├── chrome-extension/       # Chrome-Extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js       # Service Worker + Link-Crawler
│   ├── content.js          # Scraper für besuchte Seiten
│   ├── popup.html / popup.js
│   └── icon16.png / icon48.png / icon128.png
├── app/                    # Python-Backend (kein GUI mehr)
│   ├── serve.py            # Headless-Einstiegspunkt (startet den HTTP-Server)
│   ├── server.py           # Lokaler HTTP-Server (127.0.0.1:8765) + REST-API
│   ├── db.py               # SQLite + FTS5 + Pfad-Logik
│   ├── app_icon.png        # App-Icon (für Memex.app)
│   └── requirements.txt
├── macos/                  # Native SwiftUI-App (Memex.app)
│   ├── Package.swift       # Swift Package (macOS 15+)
│   ├── Sources/Memex/      # MemexApp, SearchView, DetailView, APIClient, …
│   ├── Resources/          # CGI-Logo fürs Impressum
│   ├── Info.plist          # LSUIElement (reine Menüleisten-App)
│   ├── build_app.sh        # baut das .app-Bundle (inkl. eingebettetem Backend)
│   └── make_dmg.sh         # verpackt die App in ein teilbares DMG
├── install.sh              # Dev-Installer (venv mit Extraktions-Libs, optional launchd)
└── README.md
```

> **Self-contained:** In `Memex.app` ist das Python-Backend eingebettet
> (`Contents/Resources/backend/`). Die App nutzt einen auf dem System
> vorhandenen `python3`; für das reine Speichern/Suchen genügt die
> Python-Standardbibliothek. Deshalb lässt sich die App als DMG weitergeben,
> ohne dass Empfänger etwas bauen müssen.

### Daten-Ablageort

* DB: `~/Library/Application Support/Memex/memex.db`
* Dateien: `~/Library/Application Support/Memex/files/<sha256[:2]>/<sha256>.<ext>`

*Hinweis zur Migration:* Falls du eine frühere Version unter
`~/Library/Application Support/SharePointLocalScraper/` installiert hattest,
nutzt Memex diese DB automatisch weiter – deine Daten bleiben erhalten.

In der DB landen:

* **pages** – besuchte oder gecrawlte HTML-Seiten (URL, Titel, Plaintext und
  vollständiges HTML).
* **links** – jeder auf einer Seite gefundene Link, mit Status
  `pending / fetched_page / fetched_file / error / skipped` und Verweis
  auf das Ziel (Seite oder Datei).
* **files** – heruntergeladene Binärdateien (PDF, PPTX, DOCX, XLSX, CSV, …)
  mit Metadaten und – wenn möglich – extrahiertem Text für die FTS-Suche.

---

## Installation

### 1. App installieren (DMG)

1. **`Memex-<version>.dmg`** öffnen (Doppelklick).
2. **Memex** in den **Programme**-Ordner ziehen (das Symbol ist im DMG-Fenster
   neben der Verknüpfung sichtbar).
3. Memex aus dem Programme-Ordner starten.

**Beim ersten Start** (die App ist nicht über den App Store signiert):
Rechtsklick auf *Memex* → **Öffnen** → im Dialog nochmals **Öffnen**.
Alternativ einmalig im Terminal:

    xattr -dr com.apple.quarantine "/Applications/Memex.app"

In der Menüleiste erscheint dann ein schlichtes „M". Das Suchfenster öffnet
sich beim Start automatisch bzw. über **„Suche öffnen …"** im Menü.

**Voraussetzung:** Auf dem Mac muss ein **Python 3** vorhanden sein (Memex
bringt das Backend selbst mit und braucht dafür nur die Standardbibliothek).
Falls keines installiert ist, meldet das Menü „Kein Python 3 gefunden"; dann
einmalig `xcode-select --install` ausführen oder Python von
[python.org](https://www.python.org) installieren.

> *Optional – bessere Volltextsuche in Dateien:* Mit `pip3 install pypdf
> python-docx python-pptx openpyxl` wird zusätzlich Text aus PDF/Office-Dateien
> extrahiert. Ohne diese Pakete werden Dateien trotzdem gespeichert, nur ihr
> Inhalt ist nicht durchsuchbar.

### 2. Chrome-Extension laden (nötig fürs Archivieren!)

Ohne die Extension empfängt Memex keine Inhalte. Sie liegt **dem DMG bei**
(Ordner `Memex Chrome-Extension`) bzw. im Repo unter `chrome-extension/`.

1. Den Ordner `Memex Chrome-Extension` aus dem DMG an einen **festen Ort**
   kopieren (z. B. nach *Dokumente*). **Nicht direkt vom DMG laden** – nach dem
   Auswerfen wäre die Extension sonst weg.
2. In Chrome `chrome://extensions` öffnen.
3. Oben rechts den **Entwicklermodus** aktivieren.
4. **Entpackte Erweiterung laden** klicken und den kopierten Ordner wählen.
5. In der Adressleiste erscheint das violette „M" → die Extension anpinnen.

### 3. On-Premise-SharePoint konfigurieren (optional)

Klicke auf das Extension-Icon. Trage die Hostnamen deines internen
SharePoints ein (einen pro Zeile, z. B. `sharepoint.meinefirma.de`). Nach dem
Speichern registriert die Extension sich automatisch auch für diese Domains.
Empfohlene Domains für den Anfang:
groupecgi.sharepoint.com
intranet.ent.cgi.com

---

## Für Entwickler – Build & Weitergabe

Endnutzer brauchen das **nicht** – sie installieren nur das DMG (siehe oben).
Zum Bauen werden Xcode bzw. die Command Line Tools benötigt (macOS 15+).

```
# App-Bundle bauen (inkl. eingebettetem Python-Backend)
macos/build_app.sh            # -> macos/build/Memex.app
macos/build_app.sh --install  # zusätzlich nach ~/Applications kopieren

# Teilbares DMG erzeugen
macos/make_dmg.sh             # -> macos/build/Memex-<version>.dmg
```

`build_app.sh` kopiert `app/db.py`, `app/server.py` und `app/serve.py` nach
`Memex.app/Contents/Resources/backend/`; die App ist damit eigenständig.

**Optionaler Dev-Installer** `./install.sh`: legt ein venv mit den
Extraktions-Libs an, schreibt `~/Library/Application Support/Memex/backend.conf`
(überschreibt für die Entwicklungsmaschine Python-Interpreter und serve.py-Pfad)
und richtet optional einen launchd-Autostart ein.

> **Signatur/Notarisierung:** Die App ist nur ad-hoc signiert (keine Apple
> Developer ID). Beim ersten Start auf fremden Macs greift Gatekeeper – siehe
> den Rechtsklick-→-Öffnen-Hinweis unter „App installieren".

---

## Bedienung

### Menüleiste

* **Suche öffnen …** – öffnet das Suchfenster.
* **Statistik anzeigen** – Seiten, Dateien, Links, Top-Hosts, Pfade.
* **Aufzeichnung pausieren** – stoppt Ingest und Crawler bis zum Wiedereinschalten.
* **Datenbank im Finder zeigen / Dateien-Ordner öffnen**

### Suchfenster

* **Suchfeld** mit Live-Suche ab 3 Zeichen; `Return` sucht sofort, `✕` leert.
* **Filter-Chips**: Alle · Seiten · Dateien
* **Aktualisieren** (oder `⌘R`) – Ergebnisliste und Statistik neu laden.
* **Doppelklick** auf eine Zeile öffnet den Detail-Viewer.
* Die rechte Seite zeigt eine Vorschau mit Titel, URL und Ausschnitt sowie
  Buttons für Lesen · Quick Look · Öffnen · Löschen.

### Detail-Viewer

Für **Seiten**:
* **Text** – der gescrapte Plaintext, gut lesbar wie ein Reader-View.
* **HTML-Quelltext** – das vollständige HTML.
* **Links** – alle auf der Seite gefundenen Links mit Status; Doppelklick öffnet
  gespeicherte Ziele direkt im Viewer.
* **Info** – URL, Hostname, Zeitstempel, Besuchszähler, Textlängen.

Für **Dateien**:
* **Vorschau** – macOS Quick Look (`qlmanage -p`) für PDFs, Office-Dokumente,
  Bilder, Text, ZIP usw.
* **Extrahierter Text** – was aus der Datei für die FTS-Suche gewonnen wurde.
* **Info** – MIME, Größe, SHA-256, Pfad.

### Suchsyntax

Stichworte werden AND-verknüpft; ab 3 Zeichen wird Prefix-Suche aktiviert.
Anführungszeichen bilden Phrasen, `-` negiert.

```
urlaubsantrag
"project phoenix" kickoff
budget -entwurf
```

### Was wird gespeichert?

Für jede besuchte SharePoint-Seite:
1. Plaintext **und** vollständiges HTML der Seite selbst.
2. Alle Links in die DB (Status `pending` → bis gecrawlt).
3. Die Extension ruft jeden neuen Link einmalig ab (mit deinen Cookies):
   * `text/html`, `application/xhtml+xml` → als Seite gespeichert.
   * PDF, DOCX, PPTX, XLSX, DOC, PPT, XLS, ODT/ODP/ODS, TXT, CSV, MD, RTF,
     ZIP, Bilder → als Datei lokal gespeichert (dedupliziert per SHA-256).
   * Andere MIME-Typen (Video, Audio, unbekannt) werden übersprungen.

Crawling-Tiefe ist **1** (nur direkte Links der besuchten Seite). Limits:
max. 200 Links/Seite, 100 MB/Datei, 15 MB HTML/Unterseite, 3 parallele Fetches.

---

## Datenschutz & Sicherheit

* Der Server bindet ausschließlich an `127.0.0.1`, also nicht aus dem Netz
  erreichbar.
* Datenbank und Dateien liegen plain im Benutzer-Account.
* Du kannst jederzeit alles löschen:
  rm -rf "$HOME/Library/Application Support/Memex"

---

## Impressum / Urheber

Memex wurde entwickelt von:
**Katrin Schwabel**
<katrin.schwabel@cgi.com>


## Deinstallation

# 1) Autostart entfernen (falls gesetzt)
launchctl unload ~/Library/LaunchAgents/com.local.memex.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.local.memex.plist

# 2) App entfernen
rm -rf "/Applications/Memex.app" "$HOME/Applications/Memex.app"

# 3) Datenbank + Dateien (und ggf. Dev-venv/backend.conf) löschen
rm -rf "$HOME/Library/Application Support/Memex"

# 4) (Optional) Alten Installationspfad löschen:
rm -rf "$HOME/Library/Application Support/SharePointLocalScraper"

# 5) Extension in chrome://extensions entfernen.

---

## Troubleshooting

* **„Memex lässt sich nicht öffnen" / „nicht verifizierter Entwickler"** →
  Beim ersten Start Rechtsklick auf *Memex* → **Öffnen**, oder einmalig
  `xattr -dr com.apple.quarantine "/Applications/Memex.app"`.
* **„Memex-App nicht erreichbar"** im Extension-Popup → App läuft nicht.
  Starte sie aus dem Programme-Ordner.
* **Menüleisten-Eintrag zeigt „Kein Python 3 gefunden"** → Es ist kein `python3`
  installiert. `xcode-select --install` ausführen oder Python von python.org
  installieren, dann Memex neu starten.
* **Menüleisten-Eintrag zeigt dauerhaft „Backend startet …"** → Das eingebettete
  Backend antwortet nicht. Prüfe in der Konsole (Logs) bzw. starte die App neu.
* **Port 8765 belegt** → Ändere `HTTP_PORT` in `app/serve.py`/`app/server.py`
  und `APIClient.port` in `macos/Sources/Memex/APIClient.swift`; passe zudem
  `LOCAL_BASE` in `chrome-extension/background.js` sowie die URLs in
  `content.js`/`popup.js` an.
* **SharePoint-Seiten werden nicht erfasst** → Extension im Entwicklermodus
  neu laden und die Konsole (DevTools → Service Worker) prüfen.
* **Quick-Look öffnet sich nicht** → `qlmanage` ist Teil von macOS und immer
  verfügbar; ggf. hat die Datei einen exotischen MIME-Typ, der von keinem
  Quick-Look-Generator unterstützt wird.
