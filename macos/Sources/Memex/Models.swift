import Foundation

// Datenmodelle, die 1:1 die JSON-Antworten des Python-Backends abbilden.
// Der JSONDecoder nutzt .convertFromSnakeCase, daher camelCase-Properties.

struct SearchResult: Identifiable, Decodable, Hashable {
    let kind: String          // "page" | "file"
    let rowID: Int
    let url: String?
    let name: String?
    let hostname: String?
    let lastSeen: String?
    let visitCount: Int?
    let snippet: String?
    let mimeType: String?
    let localPath: String?
    let size: Int?

    enum CodingKeys: String, CodingKey {
        case kind, id, url, name, hostname, lastSeen, visitCount, snippet, mimeType, localPath, size
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = try c.decodeIfPresent(String.self, forKey: .kind) ?? "page"
        rowID = try c.decodeIfPresent(Int.self, forKey: .id) ?? 0
        url = try c.decodeIfPresent(String.self, forKey: .url)
        name = try c.decodeIfPresent(String.self, forKey: .name)
        hostname = try c.decodeIfPresent(String.self, forKey: .hostname)
        lastSeen = try c.decodeIfPresent(String.self, forKey: .lastSeen)
        visitCount = try c.decodeIfPresent(Int.self, forKey: .visitCount)
        snippet = try c.decodeIfPresent(String.self, forKey: .snippet)
        mimeType = try c.decodeIfPresent(String.self, forKey: .mimeType)
        localPath = try c.decodeIfPresent(String.self, forKey: .localPath)
        size = try c.decodeIfPresent(Int.self, forKey: .size)
    }

    // Stabile, eindeutige Identität (Typ + DB-Id).
    var id: String { "\(kind):\(rowID)" }
    var isPage: Bool { kind == "page" }
}

struct PageDetail: Decodable {
    let id: Int
    let url: String?
    let title: String?
    let content: String?
    let html: String?
    let hostname: String?
    let source: String?
    let firstSeen: String?
    let lastSeen: String?
    let visitCount: Int?
}

struct FileDetail: Decodable {
    let id: Int
    let url: String?
    let sha256: String?
    let filename: String?
    let mimeType: String?
    let size: Int?
    let localPath: String?
    let extractedText: String?
    let firstSeen: String?
    let lastSeen: String?
}

struct LinkRow: Decodable, Identifiable, Hashable {
    let id: Int
    let url: String
    let linkText: String?
    let discoveredAt: String?
    let status: String
    let error: String?
    let targetPageId: Int?
    let targetFileId: Int?
}

struct TopHost: Decodable, Hashable {
    let hostname: String?
    let c: Int?
}

struct Stats: Decodable {
    let pages: Int?
    let files: Int?
    let linksPending: Int?
    let linksFetched: Int?
    let filesBytes: Int?
    let lastSeen: String?
    let topHosts: [TopHost]?
    let dbPath: String?
    let filesDir: String?
    let paused: Bool?
}

// Referenz für ein Detail-Fenster (Typ + Id), Hashable für WindowGroup(for:).
struct ItemRef: Codable, Hashable, Identifiable {
    let kind: String
    let rowID: Int
    var id: String { "\(kind):\(rowID)" }
}

// Wrapper für /links und /search.
struct LinksResponse: Decodable { let links: [LinkRow] }
struct SearchResponse: Decodable { let results: [SearchResult] }
