import Foundation

// Startet und überwacht das Python-Backend (serve.py) als Kindprozess.
//
// Pfade kommen aus  ~/Library/Application Support/Memex/backend.conf
// (vom Installer geschrieben), Format:
//     PYTHON=/…/venv/bin/python
//     SERVE=/…/app/serve.py
// Fällt sonst auf die Standard-venv und eine Suche relativ zum Repo zurück.
@MainActor
final class BackendManager: ObservableObject {
    static let shared = BackendManager()

    @Published var running = false
    @Published var lastError: String?

    private var process: Process?
    private let api = APIClient()

    private static var supportDir: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Memex")
    }

    // MARK: Konfiguration

    private struct Config { let python: String; let serve: String }

    private func loadConfig() -> Config? {
        let conf = Self.supportDir.appendingPathComponent("backend.conf")
        var python = Self.supportDir.appendingPathComponent("venv/bin/python").path
        var serve: String?
        if let text = try? String(contentsOf: conf, encoding: .utf8) {
            for line in text.split(whereSeparator: \.isNewline) {
                let parts = line.split(separator: "=", maxSplits: 1).map(String.init)
                guard parts.count == 2 else { continue }
                let key = parts[0].trimmingCharacters(in: .whitespaces)
                let val = parts[1].trimmingCharacters(in: .whitespaces)
                if key == "PYTHON" { python = val }
                if key == "SERVE" { serve = val }
            }
        }
        guard let serve, FileManager.default.isExecutableFile(atPath: python) else { return nil }
        return Config(python: python, serve: serve)
    }

    // MARK: Lebenszyklus

    /// Stellt sicher, dass das Backend läuft: antwortet /ping bereits, wird
    /// nichts gestartet (z. B. extern gestarteter serve.py). Sonst Kindprozess.
    func ensureRunning() async {
        if await isReachable() { running = true; return }
        guard let cfg = loadConfig() else {
            lastError = "backend.conf fehlt oder venv-Python nicht ausführbar – bitte install.sh ausführen."
            running = false
            return
        }
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: cfg.python)
        proc.arguments = [cfg.serve]
        proc.currentDirectoryURL = URL(fileURLWithPath: cfg.serve).deletingLastPathComponent()
        do {
            try proc.run()
            process = proc
        } catch {
            lastError = "Backend-Start fehlgeschlagen: \(error.localizedDescription)"
            running = false
            return
        }
        // Auf Erreichbarkeit warten (max. ~5 s).
        for _ in 0..<25 {
            if await isReachable() { running = true; lastError = nil; return }
            try? await Task.sleep(nanoseconds: 200_000_000)
        }
        lastError = "Backend antwortet nicht auf 127.0.0.1:\(APIClient.port)."
        running = false
    }

    private func isReachable() async -> Bool {
        (try? await api.ping()) != nil
    }

    func stop() {
        process?.terminate()
        process = nil
        running = false
    }
}
