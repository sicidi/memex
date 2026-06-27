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
* **Menüleisten-App (Python + rumps)** – nimmt alles entgegen und speichert es
  lokal. In der Menüleiste erscheint ein schlichtes „M"-Symbol.
* **Such-Fenster** – hübsche Tkinter-UI mit Live-Suche, Filter-Chips, Vorschau
  und einem Detail-Viewer mit Tabs für Text, HTML-Quelltext, Links und
  Metadaten. Für Dateien wahlweise Quick Look.

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
├── app/                    # Python-Menüleisten-App
│   ├── main.py             # rumps-App
│   ├── server.py           # Lokaler HTTP-Server (127.0.0.1:8765)
│   ├── db.py               # SQLite + FTS5 + Pfad-Logik
│   ├── search_ui.py        # Haupt-Suchfenster
│   ├── viewer.py           # Detail-Viewer (Text / HTML / Links / Info)
│   ├── search_ui_launcher.py
│   ├── menubar.png         # Template-Icon für die Menüleiste
│   ├── app_icon.png        # App-Icon (512×512)
│   └── requirements.txt
├── install.sh              # Installer (venv + optional launchd)
└── README.md
```

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

### 1. Python-App installieren

cd sharepoint-scraper
./install.sh

Der Installer
* legt ein venv in `~/Library/Application Support/Memex/venv` an,
* installiert `rumps` plus optionale Text-Extraktoren
  (`pypdf`, `python-docx`, `python-pptx`, `openpyxl`) und
* fragt optional nach einem launchd-Autostart beim Login.

Starten (falls du keinen Autostart eingerichtet hast):
"$HOME/Library/Application Support/Memex/venv/bin/python" app/main.py

In der Menüleiste erscheint ein schlichtes, monochromes „M".

### 2. Chrome-Extension laden

1. Öffne `chrome://extensions`.
2. Aktiviere oben rechts den **Entwicklermodus**.
3. Klicke auf **Entpackte Erweiterung laden** und wähle den Ordner
   `chrome-extension`.
4. In der Adressleiste erscheint das neue violette „M" → pinne die
   Extension an.

### 3. On-Premise-SharePoint konfigurieren (optional)

Klicke auf das Extension-Icon. Trage die Hostnamen deines internen
SharePoints ein (einen pro Zeile, z. B. `sharepoint.meinefirma.de`). Nach dem
Speichern registriert die Extension sich automatisch auch für diese Domains.
Empfohlene Domains für den Anfang:
groupecgi.sharepoint.com
intranet.ent.cgi.com

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

# 2) venv + Datenbank + Dateien löschen
rm -rf "$HOME/Library/Application Support/Memex"

# 3) (Optional) Alten Installationspfad löschen:
rm -rf "$HOME/Library/Application Support/SharePointLocalScraper"

# 4) Extension in chrome://extensions entfernen.

---

## Troubleshooting

* **„Memex-App nicht erreichbar"** im Extension-Popup → App läuft nicht.
  Starte sie manuell (`app/main.py`).
* **Port 8765 belegt** → Ändere `HTTP_PORT` in `app/main.py` und
  passe `LOCAL_BASE` in `chrome-extension/background.js` sowie die URLs
  in `content.js`/`popup.js` an.
* **Tkinter-Fenster öffnet nicht** → Unter macOS muss Python mit
  Tk-Unterstützung installiert sein (Standard-`python3` von python.org oder
  `brew install python-tk@3.12`).
* **SharePoint-Seiten werden nicht erfasst** → Extension im Entwicklermodus
  neu laden und die Konsole (DevTools → Service Worker) prüfen.
* **Quick-Look öffnet sich nicht** → `qlmanage` ist Teil von macOS und immer
  verfügbar; ggf. hat die Datei einen exotischen MIME-Typ, der von keinem
  Quick-Look-Generator unterstützt wird.
