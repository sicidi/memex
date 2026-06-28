import SwiftUI
import AppKit

@main
struct MemexApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var store = AppStore()
    @StateObject private var backend = BackendManager.shared
    @Environment(\.openWindow) private var openWindow

    var body: some Scene {
        // Menüleisten-Symbol „M".
        MenuBarExtra("Memex", systemImage: "m.square.fill") {
            Button("Suche öffnen …") { openSearch() }
                .keyboardShortcut("f")
            Button(backend.running ? "Statistik anzeigen" : "Backend startet …") { openSearch() }
                .disabled(!backend.running)
            Divider()
            Button(store.paused ? "Aufzeichnung fortsetzen" : "Aufzeichnung pausieren") {
                store.togglePause()
            }
            Button("Datenbank im Finder zeigen") { FileActions.revealDatabase() }
            Divider()
            if let e = backend.lastError {
                Text(e).font(.caption)
            } else {
                Text(backend.running ? "Server · 127.0.0.1:\(APIClient.port)" : "Server startet …")
                    .font(.caption)
            }
            Divider()
            Button("Über Memex / Impressum") { openAbout() }
            Button("Memex beenden") { NSApp.terminate(nil) }
                .keyboardShortcut("q")
        }

        // Hauptsuchfenster.
        Window("Memex", id: "search") {
            SearchView()
                .environmentObject(store)
                .task {
                    await backend.ensureRunning()
                    if backend.running { await store.loadStats() }
                }
        }
        .windowResizability(.contentSize)
        .defaultLaunchBehavior(.presented)

        // Detail-Fenster (pro Eintrag eines).
        WindowGroup("Detail", id: "detail", for: ItemRef.self) { $ref in
            if let ref { DetailView(ref: ref) }
        }

        // Impressum / Info-Fenster.
        Window("Info", id: "about") {
            AboutView()
        }
        .windowResizability(.contentSize)
        .defaultLaunchBehavior(.suppressed)
    }

    private func openSearch() {
        NSApp.activate(ignoringOtherApps: true)
        openWindow(id: "search")
    }

    private func openAbout() {
        NSApp.activate(ignoringOtherApps: true)
        openWindow(id: "about")
    }
}

// Startet das Backend beim Launch (unabhängig vom Fenster) und stoppt es beim Beenden.
// Das Dock-Icon wird über LSUIElement=true in der Info.plist ausgeblendet.
final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        Task { @MainActor in await BackendManager.shared.ensureRunning() }
    }

    func applicationWillTerminate(_ notification: Notification) {
        MainActor.assumeIsolated { BackendManager.shared.stop() }
    }
}
