import AppKit

// Native Datei-Aktionen: Quick Look, Öffnen, im Finder zeigen, URL öffnen.
enum FileActions {
    /// macOS Quick Look über `qlmanage -p` (nicht-modales Vorschaufenster) –
    /// wie in der bisherigen Tkinter-UI.
    static func quickLook(_ path: String) {
        guard !path.isEmpty else { return }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/qlmanage")
        p.arguments = ["-p", path]
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        try? p.run()
    }

    static func open(path: String) {
        guard !path.isEmpty else { return }
        NSWorkspace.shared.open(URL(fileURLWithPath: path))
    }

    static func revealInFinder(path: String) {
        guard !path.isEmpty else { return }
        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
    }

    static func open(urlString: String?) {
        guard let s = urlString, let url = URL(string: s) else { return }
        NSWorkspace.shared.open(url)
    }

    static func revealDatabase() {
        let db = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Memex/memex.db")
        NSWorkspace.shared.activateFileViewerSelecting([db])
    }
}
