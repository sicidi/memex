import SwiftUI
import AppKit

// Impressum / „Info"-Fenster nach CGI-Schema: CGI-Logo, App-Name, Urheber,
// E-Mail und die Freizeitprojekt-/Marken-Hinweise.
struct AboutView: View {
    private static let disclaimer1 =
        "Diese App gehört CGI (www.cgi.com/de). Sie ist als reines Freizeitprojekt " +
        "entstanden und darf nicht an Kunden weitergegeben oder dort eingesetzt " +
        "werden. Sie ist keine offizielle CGI-IP und wurde nicht durch eine formale " +
        "Qualitätskontrolle geprüft."
    private static let disclaimer2 =
        "CGI und das CGI-Logo sind Marken/Assets der CGI Inc. bzw. verbundener " +
        "Unternehmen."

    var body: some View {
        ZStack {
            Color(nsColor: .windowBackgroundColor).ignoresSafeArea()
            VStack(alignment: .leading, spacing: 18) {
                logo
                    .frame(height: 88, alignment: .leading)
                    .padding(.bottom, 2)

                Text("Memex")
                    .font(.system(size: 34, weight: .bold))
                    .foregroundStyle(.primary)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Katrin Schwabel").font(.title3.bold())
                    Text(verbatim: "katrin.schwabel@cgi.com")
                        .foregroundStyle(.secondary)
                    Text(Self.disclaimer1)
                        .foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                    Text(Self.disclaimer2)
                        .foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
            }
            .padding(40)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color(nsColor: .textBackgroundColor))
                    .strokeBorder(Color.primary.opacity(0.08))
            )
            .padding(20)
        }
        .frame(width: 640, height: 600)
    }

    @ViewBuilder private var logo: some View {
        if let img = Self.cgiLogo() {
            Image(nsImage: img).resizable().scaledToFit()
        } else {
            // Fallback, falls die Bild-Ressource fehlt.
            Text("CGI").font(.system(size: 64, weight: .heavy))
                .foregroundStyle(Color(hex: 0xE31937))
        }
    }

    private static func cgiLogo() -> NSImage? {
        if let url = Bundle.main.url(forResource: "cgi_logo", withExtension: "png"),
           let img = NSImage(contentsOf: url) {
            return img
        }
        return nil
    }
}
