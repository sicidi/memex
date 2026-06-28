import SwiftUI

// Memex-Farbpalette (entspricht der bisherigen Tkinter-UI).
enum Theme {
    static let accent     = Color(hex: 0x7c3aed)
    static let accentDark = Color(hex: 0x4c1d95)
    static let ink        = Color(hex: 0x1e1b4b)
    static let muted      = Color(hex: 0x6b7280)
    static let pageBadge  = Color(hex: 0x047857)
    static let fileBadge  = Color(hex: 0xa21caf)
}

extension Color {
    init(hex: UInt32) {
        let r = Double((hex >> 16) & 0xff) / 255
        let g = Double((hex >> 8) & 0xff) / 255
        let b = Double(hex & 0xff) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: 1)
    }
}

// Gemeinsame Formatierungs-Helfer.
enum Fmt {
    static func size(_ n: Int?) -> String {
        guard let n, n > 0 else { return "" }
        var s = Double(n)
        for unit in ["B", "KB", "MB", "GB"] {
            if s < 1024 || unit == "GB" {
                return unit == "B" ? "\(Int(s)) B" : String(format: "%.1f %@", s, unit)
            }
            s /= 1024
        }
        return ""
    }

    /// ISO-Zeitstempel ("2026-06-27T12:08:01Z") relativ formatieren.
    static func relTime(_ ts: String?) -> String {
        guard let ts, !ts.isEmpty else { return "" }
        let clean = ts.hasSuffix("Z") ? String(ts.dropLast()) : ts
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        let date = f.date(from: ts) ?? altParse(clean)
        guard let date else { return ts }
        let delta = Date().timeIntervalSince(date)
        if delta < 60 { return "vor wenigen Sekunden" }
        if delta < 3600 { return "vor \(Int(delta / 60)) Min." }
        if delta < 86400 { return "vor \(Int(delta / 3600)) Std." }
        if delta < 7 * 86400 { return "vor \(Int(delta / 86400)) Tg." }
        let out = DateFormatter(); out.dateFormat = "yyyy-MM-dd"
        return out.string(from: date)
    }

    static func absTime(_ ts: String?) -> String {
        guard let ts, !ts.isEmpty else { return "–" }
        let clean = ts.hasSuffix("Z") ? String(ts.dropLast()) : ts
        guard let date = altParse(clean) else { return ts }
        let out = DateFormatter(); out.dateFormat = "yyyy-MM-dd HH:mm"
        return out.string(from: date)
    }

    private static func altParse(_ s: String) -> Date? {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return f.date(from: s)
    }
}
