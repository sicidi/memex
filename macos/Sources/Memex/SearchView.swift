import SwiftUI

struct SearchView: View {
    @EnvironmentObject var store: AppStore
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            HSplitView {
                resultsTable
                    .frame(minWidth: 480)
                previewPane
                    .frame(minWidth: 280, maxWidth: 360)
            }
            Divider()
            statusBar
        }
        .frame(minWidth: 900, minHeight: 560)
        .task { await store.load(query: "") }
    }

    // MARK: Kopfbereich (Logo, Suche, Filter)

    private var header: some View {
        VStack(spacing: 10) {
            HStack(spacing: 10) {
                Text("M")
                    .font(.system(size: 20, weight: .bold, design: .serif))
                    .foregroundStyle(.white)
                    .frame(width: 30, height: 30)
                    .background(Theme.accentDark, in: RoundedRectangle(cornerRadius: 6))
                VStack(alignment: .leading, spacing: 0) {
                    Text("Memex").font(.title2.bold()).foregroundStyle(Theme.ink)
                    Text("Dein lokales SharePoint-Archiv")
                        .font(.caption).foregroundStyle(Theme.muted)
                }
                Spacer()
                Button {
                    store.refresh()
                } label: {
                    Label("Aktualisieren", systemImage: "arrow.clockwise")
                }
                .keyboardShortcut("r", modifiers: .command)
            }

            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass").foregroundStyle(Theme.muted)
                TextField("Suchen … (ab 3 Zeichen live)", text: $store.query)
                    .textFieldStyle(.plain)
                    .font(.title3)
                    .onChange(of: store.query) { store.queryChanged() }
                    .onSubmit { store.refresh() }
                if !store.query.isEmpty {
                    Button {
                        store.query = ""; store.queryChanged()
                    } label: { Image(systemName: "xmark.circle.fill") }
                        .buttonStyle(.plain).foregroundStyle(Theme.muted)
                }
            }
            .padding(8)
            .background(.background, in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(Theme.accent.opacity(0.25)))

            Picker("", selection: $store.filter) {
                ForEach(ResultFilter.allCases) { f in Text(f.label).tag(f) }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
        }
        .padding(16)
    }

    // MARK: Trefferliste

    private var resultsTable: some View {
        Table(store.results, selection: $store.selection) {
            TableColumn("") { r in
                Label(r.isPage ? "Seite" : "Datei",
                      systemImage: r.isPage ? "doc.richtext" : "doc.fill")
                    .foregroundStyle(r.isPage ? Theme.pageBadge : Theme.fileBadge)
                    .labelStyle(.titleAndIcon)
            }.width(74)
            TableColumn("Titel / Datei") { r in
                Text(r.name?.isEmpty == false ? r.name! : "(ohne Titel)").lineLimit(1)
            }
            TableColumn("Herkunft") { r in
                if r.isPage {
                    Text(r.hostname ?? "").foregroundStyle(Theme.muted).lineLimit(1)
                } else {
                    let mime = (r.mimeType ?? "").split(separator: "/").last.map(String.init)?.uppercased() ?? ""
                    Text([mime, Fmt.size(r.size)].filter { !$0.isEmpty }.joined(separator: " · "))
                        .foregroundStyle(Theme.muted).lineLimit(1)
                }
            }.width(180)
            TableColumn("Zuletzt") { r in
                Text(Fmt.relTime(r.lastSeen)).foregroundStyle(Theme.muted)
            }.width(120)
        }
        .contextMenu(forSelectionType: SearchResult.ID.self) { _ in
            Button("Lesen / Details") { openDetail() }
            Button("Löschen", role: .destructive) { store.deleteSelected() }
        } primaryAction: { _ in
            openDetail()
        }
    }

    // MARK: Vorschau

    @ViewBuilder private var previewPane: some View {
        if let r = store.selected {
            VStack(alignment: .leading, spacing: 10) {
                Text(r.name?.isEmpty == false ? r.name! : "(ohne Titel)")
                    .font(.headline).foregroundStyle(Theme.ink)
                Text(previewMeta(r)).font(.subheadline).foregroundStyle(Theme.muted)
                if let url = r.url, !url.isEmpty {
                    Text(url).font(.system(.caption, design: .monospaced))
                        .foregroundStyle(Theme.accentDark).textSelection(.enabled)
                }
                Divider()
                ScrollView {
                    Text(r.snippet?.isEmpty == false ? r.snippet! : "— kein Ausschnitt verfügbar —")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                Spacer()
                VStack(spacing: 6) {
                    Button { openDetail() } label: {
                        Label("Lesen / Details", systemImage: "book").frame(maxWidth: .infinity)
                    }.buttonStyle(.borderedProminent).tint(Theme.accent)
                    if !r.isPage {
                        Button { FileActions.quickLook(r.localPath ?? "") } label: {
                            Label("Vorschau (Quick Look)", systemImage: "eye").frame(maxWidth: .infinity)
                        }
                    }
                    Button { openExternal(r) } label: {
                        Label(r.isPage ? "Im Browser öffnen" : "Im Finder / Programm öffnen",
                              systemImage: r.isPage ? "safari" : "folder").frame(maxWidth: .infinity)
                    }
                    Button(role: .destructive) { store.deleteSelected() } label: {
                        Label("Löschen", systemImage: "trash").frame(maxWidth: .infinity)
                    }
                }
            }
            .padding(14)
        } else {
            VStack(spacing: 8) {
                Image(systemName: "sidebar.right").font(.largeTitle).foregroundStyle(Theme.muted)
                Text("Wähle links einen Eintrag,\num die Vorschau zu sehen.")
                    .multilineTextAlignment(.center).foregroundStyle(Theme.muted)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func previewMeta(_ r: SearchResult) -> String {
        if r.isPage { return "Seite · \(r.hostname ?? "")" }
        return "Datei · \(r.mimeType ?? "?") · \(Fmt.size(r.size))"
    }

    // MARK: Statusleiste

    private var statusBar: some View {
        HStack {
            Text(store.status).font(.caption).foregroundStyle(Theme.muted)
            Spacer()
            if let s = store.stats {
                let mb = Double(s.filesBytes ?? 0) / (1024 * 1024)
                Text("DB: \(s.pages ?? 0) Seiten · \(s.files ?? 0) Dateien · \(String(format: "%.1f", mb)) MB")
                    .font(.caption).foregroundStyle(Theme.muted)
            }
        }
        .padding(.horizontal, 16).padding(.vertical, 8)
    }

    // MARK: Aktionen

    private func openDetail() {
        guard let r = store.selected else { return }
        openWindow(id: "detail", value: ItemRef(kind: r.kind, rowID: r.rowID))
    }

    private func openExternal(_ r: SearchResult) {
        if r.isPage { FileActions.open(urlString: r.url) }
        else { FileActions.open(path: r.localPath ?? "") }
    }
}
