// content.js
// Läuft auf jeder konfigurierten SharePoint-Seite. Extrahiert Titel, sichtbaren
// Plaintext, das vollständige HTML und alle Links und schickt sie an die
// lokale App. Bei SPA-Navigation wird neu erfasst.

// Guard gegen Doppelausführung: Wenn eine Domain sowohl vom statischen
// Manifest-Match (*.sharepoint.com) als auch durch eine dynamisch registrierte
// Zusatz-Domain abgedeckt wird, würde content.js sonst zweimal laufen.
if (window.__memexContentLoaded) {
  // bereits geladen -> zweite Ausführung stoppen
  // (kein throw, damit Chrome keine Fehler in die Konsole schreibt)
} else {
  window.__memexContentLoaded = true;

(function () {
  "use strict";

  const LOCAL_BASE = "http://127.0.0.1:8765";
  const MIN_INTERVAL_MS = 2500;

  let lastSentUrl = null;
  let lastSentAt = 0;

  function getMainContainer() {
    return (
      document.querySelector('[data-automation-id="pageContent"]') ||
      document.getElementById("spPageCanvasContent") ||
      document.querySelector("main") ||
      document.querySelector("[role='main']") ||
      document.body
    );
  }

  function getVisibleText() {
    const el = getMainContainer();
    if (!el) return "";
    const clone = el.cloneNode(true);
    clone.querySelectorAll("script, style, noscript").forEach(n => n.remove());
    const raw = clone.innerText || clone.textContent || "";
    return raw.replace(/\s+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function getFullHtml() {
    // Vollständiges HTML der Seite. Skripte lassen wir drin; das ist zwar etwas
    // redundant, aber entspricht der Erwartung „HTML-Text der Seite speichern".
    const doctype = document.doctype
      ? "<!DOCTYPE " + document.doctype.name +
        (document.doctype.publicId ? ' PUBLIC "' + document.doctype.publicId + '"' : "") +
        (document.doctype.systemId ? ' "' + document.doctype.systemId + '"' : "") + ">"
      : "<!DOCTYPE html>";
    return doctype + "\n" + (document.documentElement?.outerHTML || "");
  }

  function getTitle() {
    const t =
      document.querySelector('[data-automation-id="pageTitle"]')?.innerText ||
      document.querySelector("h1")?.innerText ||
      document.title ||
      "";
    return t.trim();
  }

  function collectLinks() {
    const out = [];
    const seen = new Set();
    document.querySelectorAll("a[href]").forEach(a => {
      const raw = a.getAttribute("href");
      if (!raw) return;
      let abs;
      try {
        abs = new URL(raw, location.href);
      } catch {
        return;
      }
      if (!/^https?:$/.test(abs.protocol)) return;
      abs.hash = "";
      const href = abs.toString();
      if (href === location.href) return;
      if (seen.has(href)) return;
      seen.add(href);
      const text = (a.innerText || a.textContent || "").trim().slice(0, 200);
      out.push({ href, text });
    });
    return out;
  }

  // Wichtig: Der POST an die lokale App MUSS über den Service Worker laufen.
  // Ein direkter fetch() aus dem Seitenkontext wird auf SharePoint von der
  // Content-Security-Policy (connect-src), Mixed-Content und Private Network
  // Access blockiert. Der Service Worker (chrome-extension://) unterliegt der
  // Seiten-CSP nicht und darf via host_permissions auf 127.0.0.1 zugreifen.
  function send(payload) {
    return new Promise(resolve => {
      try {
        chrome.runtime.sendMessage({ type: "ingest", payload }, resp => {
          if (chrome.runtime.lastError) {
            console.debug("[Memex] Ingest-Nachricht fehlgeschlagen:",
                          chrome.runtime.lastError.message);
            resolve(null);
            return;
          }
          resolve(resp && resp.ok ? resp.info : null);
        });
      } catch (e) {
        console.debug("[Memex] sendMessage-Fehler:", e.message);
        resolve(null);
      }
    });
  }

  async function capture(reason) {
    const url = location.href;
    const now = Date.now();
    if (url === lastSentUrl && now - lastSentAt < MIN_INTERVAL_MS) return;
    lastSentUrl = url;
    lastSentAt = now;

    const content = getVisibleText();
    if (!content || content.length < 40) return;

    const payload = {
      url,
      title: getTitle(),
      content,
      html: getFullHtml(),
      hostname: location.hostname,
      links: collectLinks(),
      reason,
      captured_at: new Date().toISOString()
    };

    const resp = await send(payload);
    if (resp && Array.isArray(resp.fetch) && resp.fetch.length > 0) {
      // An den Service Worker delegieren – er darf cross-origin mit Credentials fetchen.
      chrome.runtime.sendMessage({
        type: "crawl-links",
        source_url: url,
        urls: resp.fetch
      });
    }
  }

  // Erste Erfassung nach DOM-Ready-Pause (SPA braucht manchmal länger)
  setTimeout(() => capture("initial"), 1800);

  // SPA-Navigation via URL-Änderung abfangen
  let lastHref = location.href;
  const observer = new MutationObserver(() => {
    if (location.href !== lastHref) {
      lastHref = location.href;
      setTimeout(() => capture("spa-nav"), 1800);
    }
  });
  observer.observe(document, { subtree: true, childList: true });

  window.addEventListener("focus", () => setTimeout(() => capture("focus"), 500));
})();

}

