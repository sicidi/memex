const statusEl = document.getElementById("status");
const domainsEl = document.getElementById("domains");

function setStatus(text, ok) {
  const dot = statusEl.querySelector(".dot");
  const span = statusEl.querySelectorAll("span")[1];
  statusEl.className = "status " + (ok ? "ok" : "bad");
  span.textContent = text;
}

async function init() {
  const { extraDomains } = await chrome.storage.local.get("extraDomains");
  domainsEl.value = (extraDomains || []).join("\n");
  ping();
}

function ping() {
  chrome.runtime.sendMessage({ type: "ping-local" }, (resp) => {
    if (resp && resp.ok) {
      const info = resp.info || {};
      const pages = info.pages ?? info.count ?? "?";
      const files = info.files ?? 0;
      setStatus(`Verbunden · ${pages} Seiten · ${files} Dateien`, true);
    } else {
      setStatus("Memex-App nicht erreichbar. Bitte starten.", false);
    }
  });
}

document.getElementById("save").addEventListener("click", () => {
  const domains = domainsEl.value
    .split("\n")
    .map(s => s.trim())
    .filter(s => s.length > 0);
  chrome.runtime.sendMessage({ type: "update-extra-domains", domains }, (resp) => {
    if (resp && resp.ok) {
      setStatus("Domains gespeichert.", true);
    } else {
      setStatus("Speichern fehlgeschlagen: " + (resp && resp.error), false);
    }
  });
});

document.getElementById("ping").addEventListener("click", ping);

init();
