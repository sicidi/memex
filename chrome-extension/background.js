// background.js
// Service Worker. Zwei Aufgaben:
//   1) Dynamische Content-Script-Registrierung für zusätzliche (On-Premise-)Domains.
//   2) Link-Crawler: Fetcht URLs aus /ingest-Antworten mit Session-Cookies und
//      liefert sie an die lokale App zurück (HTML → /ingest_page, Binär → /ingest_file).

const LOCAL_BASE = "http://127.0.0.1:8765";

// Default-Domains (CGI). Werden beim ersten Installieren automatisch in die
// Domain-Liste eingetragen. Du kannst sie im Popup jederzeit ändern oder
// entfernen.
const DEFAULT_DOMAINS = [
  "groupecgi.sharepoint.com",
  "intranet.ent.cgi.com"
];

// ---- Dynamische Content-Scripts ----------------------------------------

chrome.runtime.onInstalled.addListener(async () => {
  const { extraDomains } = await chrome.storage.local.get("extraDomains");
  if (!Array.isArray(extraDomains) || extraDomains.length === 0) {
    await chrome.storage.local.set({ extraDomains: [...DEFAULT_DOMAINS] });
  }
  await registerDynamicContentScripts();
});

chrome.runtime.onStartup.addListener(registerDynamicContentScripts);

async function registerDynamicContentScripts() {
  const { extraDomains } = await chrome.storage.local.get("extraDomains");
  const list = Array.isArray(extraDomains) ? extraDomains : [];
  const matches = list
    .filter(d => typeof d === "string" && d.trim().length > 0)
    .map(d => `*://${d.trim()}/*`);

  try {
    const existing = await chrome.scripting.getRegisteredContentScripts({ ids: ["sp-extra"] });
    if (existing.length > 0) {
      await chrome.scripting.unregisterContentScripts({ ids: ["sp-extra"] });
    }
    if (matches.length === 0) return;
    await chrome.scripting.registerContentScripts([{
      id: "sp-extra",
      matches,
      js: ["content.js"],
      runAt: "document_idle"
    }]);
  } catch (e) {
    console.warn("[SP-Scraper] registerContentScripts fehlgeschlagen:", e);
  }
}

// ---- Message-Router (Popup + Content-Scripts) --------------------------

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || typeof msg !== "object") return;

  if (msg.type === "update-extra-domains") {
    chrome.storage.local.set({ extraDomains: msg.domains || [] })
      .then(registerDynamicContentScripts)
      .then(() => sendResponse({ ok: true }))
      .catch(err => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (msg.type === "ingest") {
    // Seiten-Ingest aus dem Content-Script: hier im Service Worker fetchen,
    // damit weder Seiten-CSP noch Mixed-Content/PNA den Aufruf blockieren.
    (async () => {
      try {
        const resp = await fetch(LOCAL_BASE + "/ingest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(msg.payload || {})
        });
        if (!resp.ok) {
          sendResponse({ ok: false, status: resp.status });
          return;
        }
        sendResponse({ ok: true, info: await resp.json() });
      } catch (e) {
        console.debug("[Memex] /ingest nicht erreichbar:", e.message);
        sendResponse({ ok: false, error: String(e) });
      }
    })();
    return true; // asynchrone Antwort
  }

  if (msg.type === "ping-local") {
    fetch(LOCAL_BASE + "/ping")
      .then(r => r.json())
      .then(j => sendResponse({ ok: true, info: j }))
      .catch(e => sendResponse({ ok: false, error: String(e) }));
    return true;
  }

  if (msg.type === "crawl-links") {
    // Feuer-und-vergiss – läuft im Service Worker weiter
    enqueueCrawl(msg.source_url, msg.urls || []);
    sendResponse({ ok: true, queued: (msg.urls || []).length });
    return true;
  }
});

// ---- Crawler ----------------------------------------------------------

const MAX_FILE_BYTES = 100 * 1024 * 1024;       // 100 MB
const MAX_HTML_BYTES =  15 * 1024 * 1024;       // 15 MB
const PARALLEL_FETCHES = 3;

// Queue: {source_url, url}
const _queue = [];
let _running = 0;

function enqueueCrawl(source_url, urls) {
  for (const u of urls) _queue.push({ source_url, url: u });
  kick();
}

function kick() {
  while (_running < PARALLEL_FETCHES && _queue.length > 0) {
    const job = _queue.shift();
    _running++;
    processOne(job).finally(() => {
      _running--;
      kick();
    });
  }
}

async function processOne(job) {
  const { source_url, url } = job;
  try {
    const resp = await fetch(url, {
      method: "GET",
      credentials: "include",
      redirect: "follow"
    });
    if (!resp.ok) {
      console.debug("[SP-Scraper] HTTP", resp.status, url);
      return;
    }
    const ctype = (resp.headers.get("content-type") || "").toLowerCase();
    const disposition = resp.headers.get("content-disposition") || "";
    const lenHdr = parseInt(resp.headers.get("content-length") || "0", 10) || 0;

    if (ctype.includes("text/html") || ctype.includes("application/xhtml")) {
      const html = await resp.text();
      if (!html || html.length > MAX_HTML_BYTES) return;
      const { text, title } = parseHtmlForText(html);
      await postJson(LOCAL_BASE + "/ingest_page", {
        url,
        source_url,
        title,
        content: text,
        html,
        hostname: new URL(url).hostname
      });
      return;
    }

    if (isFileMime(ctype)) {
      if (lenHdr > MAX_FILE_BYTES) {
        console.debug("[SP-Scraper] Zu groß:", url, lenHdr);
        return;
      }
      const blob = await resp.blob();
      if (blob.size > MAX_FILE_BYTES) return;
      const filename = filenameFromHeaders(disposition, url);
      const qs = new URLSearchParams({
        url, source_url, filename, mime_type: ctype.split(";")[0].trim()
      });
      await fetch(LOCAL_BASE + "/ingest_file?" + qs.toString(), {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: blob
      });
      return;
    }
    // Sonstige MIME-Typen: ignorieren.
  } catch (e) {
    console.debug("[SP-Scraper] Fetch-Fehler:", url, e.message);
  }
}

// ---- Utils -------------------------------------------------------------

function parseHtmlForText(html) {
  try {
    const doc = new DOMParser().parseFromString(html, "text/html");
    doc.querySelectorAll("script, style, noscript").forEach(n => n.remove());
    const text = (doc.body?.innerText || doc.body?.textContent || "")
      .replace(/\s+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
    const title = (doc.querySelector("title")?.textContent || "").trim();
    return { text, title };
  } catch {
    return { text: "", title: "" };
  }
}

function isFileMime(ctype) {
  const m = ctype.split(";")[0].trim();
  if (!m) return false;
  const prefixes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-",
    "application/msword",
    "application/vnd.oasis.opendocument",
    "text/plain", "text/csv", "text/markdown",
    "application/rtf", "application/zip",
    "image/"
  ];
  return prefixes.some(p => m.startsWith(p));
}

function filenameFromHeaders(disposition, url) {
  // RFC 5987 filename*=UTF-8''...  und filename="..."
  const m1 = /filename\*\s*=\s*[^']*'[^']*'([^;]+)/i.exec(disposition);
  if (m1) {
    try { return decodeURIComponent(m1[1].trim()); } catch {}
  }
  const m2 = /filename\s*=\s*"?([^";]+)"?/i.exec(disposition);
  if (m2) return m2[1].trim();
  try {
    const u = new URL(url);
    const seg = u.pathname.split("/").filter(Boolean).pop();
    return seg ? decodeURIComponent(seg) : "datei";
  } catch {
    return "datei";
  }
}

async function postJson(url, payload) {
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    console.debug("[SP-Scraper] postJson-Fehler:", e.message);
  }
}
