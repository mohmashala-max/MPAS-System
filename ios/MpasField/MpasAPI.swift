import Foundation

struct TokenResponse: Decodable {
    let accessToken: String
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

struct ImageUploadResponse: Decodable {
    let imageURI: String
    let contentType: String
    let sizeBytes: Int

    enum CodingKeys: String, CodingKey {
        case imageURI = "image_uri"
        case contentType = "content_type"
        case sizeBytes = "size_bytes"
    }
}

final class MpasAPI {
    private let baseURL: URL
    private var accessToken: String?
    private let session: URLSession

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func login(username: String, password: String) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/auth/token"))
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = "username=\(username.urlEncoded)&password=\(password.urlEncoded)".data(using: .utf8)
        let (data, response) = try await session.data(for: request)
        try validate(response)
        accessToken = try JSONDecoder().decode(TokenResponse.self, from: data).accessToken
    }

    func uploadAndInspect(inspection: Inspection) async throws {
        guard let accessToken else { throw APIError.unauthorized }
        let imageData = try Data(contentsOf: URL(fileURLWithPath: inspection.imagePath))
        let boundary = "Boundary-\(UUID().uuidString)"
        var upload = URLRequest(url: baseURL.appendingPathComponent("api/v1/images"))
        upload.httpMethod = "POST"
        upload.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        upload.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        upload.httpBody = multipart(data: imageData, boundary: boundary)
        let (imageResponse, response) = try await session.data(for: upload)
        try validate(response)
        let stored = try JSONDecoder().decode(ImageUploadResponse.self, from: imageResponse)

        var inspect = URLRequest(url: baseURL.appendingPathComponent("api/v1/ai/inspect"))
        inspect.httpMethod = "POST"
        inspect.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        inspect.setValue("application/json", forHTTPHeaderField: "Content-Type")
        inspect.httpBody = try JSONSerialization.data(withJSONObject: [
            "facility_id": inspection.facilityId,
            "trap_id": inspection.trapId,
            "image_uri": stored.imageURI,
            "detections": []
        ])
        let (_, inspectResponse) = try await session.data(for: inspect)
        try validate(inspectResponse)
    }

    private func multipart(data: Data, boundary: String) -> Data {
        var body = Data()
        body.append(Data("--\(boundary)\r\n".utf8))
        body.append(Data("Content-Disposition: form-data; name=\"image\"; filename=\"inspection.jpg\"\r\n".utf8))
        body.append(Data("Content-Type: image/jpeg\r\n\r\n".utf8))
        body.append(data)
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))
        return body
    }

    private func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.requestFailed
        }
    }

    enum APIError: Error { case unauthorized, requestFailed }
}

private extension String {
    var urlEncoded: String { addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? self }
}
