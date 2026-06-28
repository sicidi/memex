import SwiftUI

struct DetailView: View {
    let ref: ItemRef
    @Environment(\.openWindow) private var openWindow

    @State private var page: PageDetail?
    @State private var file: FileDetail?
    @State private var links: [LinkRow] = []
    @State private var loadError: String?

    private let api = APIClient()

    var body: some View {
        Group {
            if let err = loadError {
                ContentUnavailableView("Konnte nicht laden", systemImage: "exclamationmark.triangle", description: Text(err))
            } else if ref.kind == "page" {
                pageBody
            } else {
                fileBody
            }
        }
        .frame(minWidth: 760, minHeight: 560)
        .task { await load() }
    }

    // MARK: Laden

    private func load() async {
        do {
            if ref.kind == "page" {
                page = try await api.page(id: ref.rowID)
                links = (try? await api.links(pageID: ref.rowID)) ?? []
            } else {
                file = try await api.file(id: ref.rowID)
            }
        } catch {
            loadError = error.localizedDescription
        }
    }

    // MARK: Seite

    @ViewBuilder private var pageBody: some View {
        if let p = page {
            VStack(alignment: .leading, spacing: 0) {
                headerBar(badge: "Seite", badgeColor: Theme.pageBadge,
                          title: p.title?.isEmpty == false ? p.title! : (p.url ?? "(ohne Titel)"),
                          meta: [p.hostname, Fmt.absTime(p.lastSeen)].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: "  ·  "),
                          url: p.url) {
                    Button { FileActions.open(urlString: p.url) } label: { Label("Im Browser öffnen", systemImage: "safari") }
                }
                TabView {
                    textTab(p.content, heading: "Text")
                        .tabItem { Text("Text") }
                    monoTab(p.html ?? "— kein HTML gespeichert —")
                        .tabItem { Text("HTML-Quelltext") }
                    linksTab.tabItem { Text("Links (\(links.count))") }
                    infoTab(pageInfo(p)).tabItem { Text("Info") }
                }
                .padding(.horizontal, 14).padding(.bottom, 14)
            }
        } else { ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity) }
    }

    // MARK: Datei

    @ViewBuilder private var fileBody: some View {
        if let f = file {
            VStack(alignment: .leading, spacing: 0) {
                headerBar(badge: "Datei", badgeColor: Theme.fileBadge,
                          title: f.filename?.isEmpty == false ? f.filename! : (f.url ?? "(ohne Titel)"),
                          meta: [f.mimeType, Fmt.size(f.size), Fmt.absTime(f.lastSeen)].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: "  ·  "),
                          url: f.url) {
                    Button { FileActions.quickLook(f.localPath ?? "") } label: { Label("Quick Look", systemImage: "eye") }
                    Button { FileActions.open(path: f.localPath ?? "") } label: { Label("Öffnen", systemImage: "arrow.up.forward.app") }
                    Button { FileActions.revealInFinder(path: f.localPath ?? "") } label: { Label("Im Finder", systemImage: "folder") }
                }
                TabView {
                    filePreviewTab(f).tabItem { Text("Vorschau") }
                    textTab(f.extractedText, heading: "Extrahierter Text")
                        .tabItem { Text("Extrahierter Text") }
                    infoTab(fileInfo(f)).tabItem { Text("Info") }
                }
                .padding(.horizontal, 14).padding(.bottom, 14)
            }
        } else { ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity) }
    }

    // MARK: Bausteine

    private func headerBar(badge: String, badgeColor: Color, title: String, meta: String,
                           url: String?, @ViewBuilder actions: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Text(badge).font(.caption.bold()).foregroundStyle(.white)
                    .padding(.horizontal, 8).padding(.vertical, 2)
                    .background(badgeColor, in: Capsule())
                Text(title).font(.title3.bold()).foregroundStyle(Theme.ink).lineLimit(2)
                Spacer()
            }
            Text(meta).font(.caption).foregroundStyle(Theme.muted)
            HStack { actions() }
            if let url, !url.isEmpty {
                Text(url).font(.system(.caption, design: .monospaced))
                    .foregroundStyle(Theme.muted).textSelection(.enabled).lineLimit(1)
            }
        }
        .padding(14)
    }

    private func textTab(_ content: String?, heading: String) -> some View {
        ScrollView {
            Text(content?.isEmpty == false ? content! : "— kein \(heading) —")
                .font(.body).textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading).padding(12)
        }
    }

    private func monoTab(_ content: String) -> some View {
        ScrollView([.vertical, .horizontal]) {
            Text(content).font(.system(.caption, design: .monospaced))
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading).padding(12)
        }
    }

    private var linksTab: some View {
        Table(links) {
            TableColumn("Status") { l in Text(statusLabel(l.status)) }.width(130)
            TableColumn("Ziel") { l in Text(targetLabel(l)) }.width(70)
            TableColumn("Link-Text") { l in Text(l.linkText ?? "").lineLimit(1) }
            TableColumn("URL") { l in Text(l.url).lineLimit(1).textSelection(.enabled) }
        }
        .contextMenu(forSelectionType: LinkRow.ID.self) { sel in
            if let id = sel.first, let l = links.first(where: { $0.id == id }) {
                Button("Öffnen") { openLink(l) }
            }
        } primaryAction: { sel in
            if let id = sel.first, let l = links.first(where: { $0.id == id }) { openLink(l) }
        }
    }

    private func filePreviewTab(_ f: FileDetail) -> some View {
        VStack(spacing: 14) {
            Image(systemName: "doc.viewfinder").font(.system(size: 48)).foregroundStyle(Theme.muted)
            Text("Native macOS-Vorschau (PDF, Office, Bilder, Text, ZIP …)")
                .multilineTextAlignment(.center).foregroundStyle(Theme.muted)
            Button { FileActions.quickLook(f.localPath ?? "") } label: {
                Label("Quick Look öffnen", systemImage: "eye")
            }.buttonStyle(.borderedProminent).tint(Theme.accent)
            if let p = f.localPath { Text(p).font(.system(.caption, design: .monospaced)).foregroundStyle(Theme.muted) }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func infoTab(_ rows: [(String, String)]) -> some View {
        ScrollView {
            Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 8) {
                ForEach(rows, id: \.0) { k, v in
                    GridRow {
                        Text(k).font(.caption.bold()).foregroundStyle(Theme.muted)
                            .gridColumnAlignment(.trailing)
                        Text(v).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading).padding(14)
        }
    }

    // MARK: Daten → Zeilen

    private func pageInfo(_ p: PageDetail) -> [(String, String)] {
        [("URL", p.url ?? ""), ("Titel", p.title ?? ""), ("Hostname", p.hostname ?? ""),
         ("Quelle", p.source == "crawl" ? "Per Link gefunden" : "Direkt besucht"),
         ("Erstmals gesehen", Fmt.absTime(p.firstSeen)), ("Zuletzt gesehen", Fmt.absTime(p.lastSeen)),
         ("Besuche", String(p.visitCount ?? 1)),
         ("Zeichen Text", String((p.content ?? "").count)),
         ("Zeichen HTML", String((p.html ?? "").count))]
    }

    private func fileInfo(_ f: FileDetail) -> [(String, String)] {
        [("URL", f.url ?? ""), ("Dateiname", f.filename ?? ""), ("MIME-Typ", f.mimeType ?? ""),
         ("Größe", Fmt.size(f.size)), ("SHA-256", f.sha256 ?? ""), ("Pfad", f.localPath ?? ""),
         ("Erstmals gesehen", Fmt.absTime(f.firstSeen)), ("Zuletzt gesehen", Fmt.absTime(f.lastSeen)),
         ("Extrahierter Text", "\((f.extractedText ?? "").count) Zeichen")]
    }

    private func statusLabel(_ s: String) -> String {
        switch s {
        case "pending": return "🕓 wartet"
        case "fetched_page", "fetched_file": return "✅ gespeichert"
        case "error": return "⚠︎ Fehler"
        case "skipped": return "— übersprungen"
        default: return s
        }
    }

    private func targetLabel(_ l: LinkRow) -> String {
        if l.targetPageId != nil { return "Seite" }
        if l.targetFileId != nil { return "Datei" }
        return "–"
    }

    private func openLink(_ l: LinkRow) {
        if let pid = l.targetPageId { openWindow(id: "detail", value: ItemRef(kind: "page", rowID: pid)); return }
        if let fid = l.targetFileId { openWindow(id: "detail", value: ItemRef(kind: "file", rowID: fid)); return }
        FileActions.open(urlString: l.url)
    }
}
