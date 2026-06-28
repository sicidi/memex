import SwiftUI

enum ResultFilter: String, CaseIterable, Identifiable {
    case all, pages, files
    var id: String { rawValue }
    var label: String {
        switch self {
        case .all: return "Alle"
        case .pages: return "Seiten"
        case .files: return "Dateien"
        }
    }
}

@MainActor
final class AppStore: ObservableObject {
    @Published var query = ""
    @Published var filter: ResultFilter = .all
    @Published var allResults: [SearchResult] = []
    @Published var selection: SearchResult.ID?
    @Published var stats: Stats?
    @Published var status = "Bereit."
    @Published var paused = false

    private let api = APIClient()
    private var searchTask: Task<Void, Never>?

    var results: [SearchResult] {
        switch filter {
        case .all: return allResults
        case .pages: return allResults.filter { $0.isPage }
        case .files: return allResults.filter { !$0.isPage }
        }
    }

    var selected: SearchResult? {
        results.first { $0.id == selection }
    }

    // Live-Suche ab 3 Zeichen; leere Eingabe zeigt „Neueste".
    func queryChanged() {
        let q = query.trimmingCharacters(in: .whitespaces)
        searchTask?.cancel()
        if q.isEmpty {
            searchTask = Task { await self.load(query: "") }
        } else if q.count >= 3 {
            searchTask = Task {
                try? await Task.sleep(nanoseconds: 180_000_000)   // Debounce
                if Task.isCancelled { return }
                await self.load(query: q)
            }
        }
    }

    func refresh() {
        Task { await load(query: query.trimmingCharacters(in: .whitespaces)) }
    }

    func load(query q: String) async {
        do {
            let res = try await api.search(q, limit: 300)
            allResults = res
            status = q.isEmpty ? "\(res.count) Einträge (zuletzt gesehen)"
                               : "\(res.count) Treffer für „\(q)“"
            await loadStats()
        } catch {
            status = "Fehler: \(error.localizedDescription)"
        }
    }

    func loadStats() async {
        stats = try? await api.ping()
        if let p = stats?.paused { paused = p }
    }

    func togglePause() {
        Task {
            if let p = try? await api.setPaused(!paused) { paused = p }
        }
    }

    func deleteSelected() {
        guard let r = selected else { return }
        Task {
            do {
                try await api.delete(kind: r.kind, id: r.rowID)
                refresh()
            } catch {
                status = "Löschen fehlgeschlagen: \(error.localizedDescription)"
            }
        }
    }
}
