import Foundation

// Schlanker HTTP-Client gegen das lokale Python-Backend (127.0.0.1:8765).
struct APIClient {
    static let port = 8765
    let base = URL(string: "http://127.0.0.1:\(APIClient.port)")!

    private func decoder() -> JSONDecoder {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }

    private func get<T: Decodable>(_ path: String, query: [URLQueryItem] = [], as type: T.Type) async throws -> T {
        var comp = URLComponents(url: base.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        if !query.isEmpty { comp.queryItems = query }
        let (data, resp) = try await URLSession.shared.data(from: comp.url!)
        try Self.check(resp, data)
        return try decoder().decode(T.self, from: data)
    }

    @discardableResult
    private func post<T: Decodable>(_ path: String, body: [String: Any], as type: T.Type) async throws -> T {
        var req = URLRequest(url: base.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, resp) = try await URLSession.shared.data(for: req)
        try Self.check(resp, data)
        return try decoder().decode(T.self, from: data)
    }

    private static func check(_ resp: URLResponse, _ data: Data) throws {
        guard let http = resp as? HTTPURLResponse else { return }
        guard (200..<300).contains(http.statusCode) else {
            let msg = String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"
            throw NSError(domain: "Memex", code: http.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: msg])
        }
    }

    // ---- Endpunkte ----------------------------------------------------

    func ping() async throws -> Stats {
        try await get("ping", as: Stats.self)
    }

    func search(_ q: String, limit: Int = 300) async throws -> [SearchResult] {
        let items = [URLQueryItem(name: "q", value: q),
                     URLQueryItem(name: "limit", value: String(limit))]
        return try await get("search", query: items, as: SearchResponse.self).results
    }

    func page(id: Int) async throws -> PageDetail {
        try await get("page", query: [URLQueryItem(name: "id", value: String(id))], as: PageDetail.self)
    }

    func file(id: Int) async throws -> FileDetail {
        try await get("file", query: [URLQueryItem(name: "id", value: String(id))], as: FileDetail.self)
    }

    func links(pageID: Int) async throws -> [LinkRow] {
        try await get("links", query: [URLQueryItem(name: "page_id", value: String(pageID))],
                      as: LinksResponse.self).links
    }

    func delete(kind: String, id: Int) async throws {
        struct OK: Decodable { let ok: Bool }
        _ = try await post("delete", body: ["kind": kind, "id": id], as: OK.self)
    }

    @discardableResult
    func setPaused(_ value: Bool) async throws -> Bool {
        struct PauseResp: Decodable { let paused: Bool }
        return try await post("pause", body: ["value": value], as: PauseResp.self).paused
    }
}
