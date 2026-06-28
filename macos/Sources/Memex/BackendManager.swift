import Foundation

// Startet und überwacht das Python-Backend (serve.py) als Kindprozess.
//
// Self-contained: Das Backend (db.py/server.py/serve.py) ist ins App-Bundle
// eingebettet (Contents/Resources/backend/). Als Python-Interpreter wird ein
// auf dem System vorhandener python3 genutzt – das Backend braucht nur die
// Standardbibliothek (die Text-Extraktions-Libs sind optional).
//
// Auf der Entwicklungsmaschine kann ~/Library/Application Support/Memex/
// backend.conf (PYTHON=…, SERVE=…) beides überschreiben – z. B. um das venv
// mit den Extraktions-Libs zu verwenden.
@MainActor
final class BackendManager: ObservableObject {
    static let shared = BackendManager()

    @Published var running = false
    @Published var lastError: String?

    private var process: Process?
    private var starting = false
    private let api = APIClient()

    private static var supportDir: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Memex")
    }

    // MARK: Backend-Skript & Python finden

    /// serve.py: bevorzugt das eingebettete Backend, sonst backend.conf (Dev).
    private func resolveServeScript() -> String? {
        if let res = Bundle.main.resourceURL {
            let bundled = res.appendingPathComponent("backend/serve.py")
            if FileManager.default.isReadableFile(atPath: bundled.path) { return bundled.path }
        }
        if let serve = readConf()["SERVE"], FileManager.default.isReadableFile(atPath: serve) {
            return serve
        }
        return nil
    }

    /// Python: bevorzugt backend.conf (venv inkl. Extraktions-Libs), sonst ein
    /// auf dem System vorhandener python3.
    private func resolvePython() -> String? {
        if let py = readConf()["PYTHON"], FileManager.default.isExecutableFile(atPath: py) {
            return py
        }
        let candidates = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
            "/usr/bin/python3",
        ]
        return candidates.first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    private func readConf() -> [String: String] {
        let conf = Self.supportDir.appendingPathComponent("backend.conf")
        guard let text = try? String(contentsOf: conf, encoding: .utf8) else { return [:] }
        var out: [String: String] = [:]
        for line in text.split(whereSeparator: \.isNewline) {
            let parts = line.split(separator: "=", maxSplits: 1).map(String.init)
            if parts.count == 2 {
                out[parts[0].trimmingCharacters(in: .whitespaces)] =
                    parts[1].trimmingCharacters(in: .whitespaces)
            }
        }
        return out
    }

    // MARK: Lebenszyklus

    /// Stellt sicher, dass das Backend läuft. Idempotent + re-entrancy-fest:
    /// gleichzeitige Aufrufe (AppDelegate + Fenster-Task) starten nicht doppelt.
    func ensureRunning() async {
        if running || starting { return }
        starting = true
        defer { starting = false }

        if await isReachable() { running = true; return }

        guard let serve = resolveServeScript() else {
            lastError = "Backend-Skript nicht gefunden (weder im App-Bundle noch via backend.conf)."
            running = false; return
        }
        guard let python = resolvePython() else {
            lastError = "Kein Python 3 gefunden. Bitte Python 3 installieren " +
                        "(z. B. ‚xcode-select --install‘ oder python.org)."
            running = false; return
        }

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: python)
        proc.arguments = [serve]
        proc.currentDirectoryURL = URL(fileURLWithPath: serve).deletingLastPathComponent()
        do {
            try proc.run()
            process = proc
        } catch {
            lastError = "Backend-Start fehlgeschlagen: \(error.localizedDescription)"
            running = false; return
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
