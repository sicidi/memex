// swift-tools-version:6.0
import PackageDescription

let package = Package(
    name: "Memex",
    platforms: [
        .macOS(.v15)
    ],
    targets: [
        .executableTarget(
            name: "Memex",
            path: "Sources/Memex"
        )
    ],
    // Swift-5-Sprachmodus: vermeidet die strikte Swift-6-Concurrency-Prüfung.
    swiftLanguageModes: [.v5]
)
