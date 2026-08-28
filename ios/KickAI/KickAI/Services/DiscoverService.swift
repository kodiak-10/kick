import Foundation

struct DiscoverServiceConfiguration {
    let baseURL: URL?
    let timeout: TimeInterval

    static var live: DiscoverServiceConfiguration {
        DiscoverServiceConfiguration(
            baseURL: VideoAnalysisServiceConfiguration.live.baseURL,
            timeout: 20
        )
    }

    var baseURLText: String {
        baseURL?.absoluteString ?? "未配置"
    }
}

enum DiscoverServiceError: LocalizedError {
    case missingBaseURL
    case invalidURL
    case invalidResponse
    case httpStatus(Int)

    var errorDescription: String? {
        switch self {
        case .missingBaseURL:
            return "后端地址未配置"
        case .invalidURL:
            return "接口地址无效"
        case .invalidResponse:
            return "后端响应无效"
        case let .httpStatus(code):
            return "后端返回错误状态 \(code)"
        }
    }
}

struct DiscoverConfig: Decodable {
    let status: String
    let venueProviderKeys: [String: Bool]
    let venueSearchReady: Bool
    let poiProviderEnvKeys: [String: String]
    let storagePath: String
    let features: [String: Bool]
}

enum DiscoverPostVisibility: String, Codable, CaseIterable {
    case `public`
    case mutualFollow = "mutual_follow"
    case `private`

    var title: String {
        switch self {
        case .public:
            return "公开"
        case .mutualFollow:
            return "互相关注可见"
        case .private:
            return "仅自己"
        }
    }

    var shortTitle: String {
        switch self {
        case .public:
            return "公开"
        case .mutualFollow:
            return "互关"
        case .private:
            return "私密"
        }
    }

    var iconName: String {
        switch self {
        case .public:
            return "globe.asia.australia"
        case .mutualFollow:
            return "person.2"
        case .private:
            return "lock"
        }
    }
}

struct DiscoverCommunityPost: Identifiable, Decodable {
    let id: String
    let userID: String
    let userName: String
    let region: String
    let badge: String
    let title: String
    let body: String
    let visibility: DiscoverPostVisibility
    let aiReply: String?
    let likes: Int
    let commentCount: Int
    let createdAt: String?
    let updatedAt: String?

    var isOwnedByCurrentUser: Bool {
        userID == DiscoverService.currentUserID
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case userID = "userId"
        case userName
        case region
        case badge
        case title
        case body
        case visibility
        case aiReply
        case likes
        case commentCount
        case createdAt
        case updatedAt
    }
}

struct DiscoverVenue: Identifiable, Decodable {
    let id: String
    let name: String
    let address: String
    let longitude: Double?
    let latitude: Double?
    let phone: String?
    let source: String?
    let sourceLabel: String?
    let reliabilityLabel: String?
    let lastVerifiedAt: String?
}

struct DiscoverCoachListing: Identifiable, Decodable {
    let id: String
    let name: String
    let region: String
    let specialty: String
    let priceText: String
    let description: String
    let rating: Double?
    let verified: Bool?
}

struct DiscoverCoachBooking: Identifiable, Decodable {
    let id: String
    let coachID: String
    let coachName: String?
    let userName: String
    let contact: String
    let region: String
    let goal: String
    let preferredTime: String?
    let status: String
    let createdAt: String?

    private enum CodingKeys: String, CodingKey {
        case id
        case coachID = "coachId"
        case coachName
        case userName
        case contact
        case region
        case goal
        case preferredTime
        case status
        case createdAt
    }
}

struct DiscoverCoachMessage: Identifiable, Decodable {
    let id: String
    let conversationID: String
    let senderID: String
    let senderName: String
    let role: String
    let body: String
    let createdAt: String?

    var isCurrentUser: Bool {
        senderID == DiscoverService.currentUserID || role == "user"
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case conversationID = "conversationId"
        case senderID = "senderId"
        case senderName
        case role
        case body
        case createdAt
    }
}

struct DiscoverCoachConversation: Identifiable, Decodable {
    let id: String
    let coachID: String
    let coachName: String?
    let userID: String
    let userName: String
    let region: String
    let status: String
    let createdAt: String?
    let updatedAt: String?
    let messages: [DiscoverCoachMessage]

    private enum CodingKeys: String, CodingKey {
        case id
        case coachID = "coachId"
        case coachName
        case userID = "userId"
        case userName
        case region
        case status
        case createdAt
        case updatedAt
        case messages
    }
}

struct DiscoverVenueSearchResponse: Decodable {
    let status: String
    let providerKeys: [String: Bool]
    let venueSearchReady: Bool
    let providerResultCount: [String: Int]
    let providerErrors: [String: String]
    let items: [DiscoverVenue]
    let setupHint: String?
}

private struct DiscoverListResponse<T: Decodable>: Decodable {
    let status: String
    let items: [T]
}

private struct DiscoverItemResponse<T: Decodable>: Decodable {
    let status: String
    let item: T?
    let errorCode: String?
    let message: String?
}

private struct DiscoverPostCreateRequest: Encodable {
    let userID: String
    let userName: String
    let region: String
    let badge: String
    let title: String
    let body: String
    let visibility: DiscoverPostVisibility

    private enum CodingKeys: String, CodingKey {
        case userID = "userId"
        case userName
        case region
        case badge
        case title
        case body
        case visibility
    }
}

private struct DiscoverPostUpdateRequest: Encodable {
    let userID: String
    let title: String
    let body: String
    let badge: String
    let visibility: DiscoverPostVisibility

    private enum CodingKeys: String, CodingKey {
        case userID = "userId"
        case title
        case body
        case badge
        case visibility
    }
}

private struct DiscoverCoachBookingCreateRequest: Encodable {
    let coachID: String
    let userName: String
    let contact: String
    let region: String
    let goal: String
    let preferredTime: String?

    private enum CodingKeys: String, CodingKey {
        case coachID = "coachId"
        case userName
        case contact
        case region
        case goal
        case preferredTime
    }
}

private struct DiscoverCoachConversationCreateRequest: Encodable {
    let coachID: String
    let userID: String
    let userName: String
    let region: String
    let initialMessage: String?

    private enum CodingKeys: String, CodingKey {
        case coachID = "coachId"
        case userID = "userId"
        case userName
        case region
        case initialMessage
    }
}

private struct DiscoverCoachMessageCreateRequest: Encodable {
    let senderID: String
    let senderName: String
    let body: String

    private enum CodingKeys: String, CodingKey {
        case senderID = "senderId"
        case senderName
        case body
    }
}

final class DiscoverService {
    static let currentUserID = "kickai-demo-user"
    static let currentUserName = "KickAI 用户"

    private let configuration: DiscoverServiceConfiguration
    private let session: URLSession

    init(
        configuration: DiscoverServiceConfiguration = .live,
        session: URLSession = .shared
    ) {
        self.configuration = configuration
        self.session = session
    }

    var baseURLText: String {
        configuration.baseURLText
    }

    func fetchConfig() async throws -> DiscoverConfig {
        try await get("discovery/config")
    }

    func fetchPosts(region: String? = nil) async throws -> [DiscoverCommunityPost] {
        let response: DiscoverListResponse<DiscoverCommunityPost> = try await get(
            "discovery/community/posts",
            queryItems: [
                URLQueryItem(name: "region", value: region),
                URLQueryItem(name: "viewer_user_id", value: Self.currentUserID)
            ]
        )
        return response.items
    }

    func fetchPost(id: String) async throws -> DiscoverCommunityPost {
        let response: DiscoverItemResponse<DiscoverCommunityPost> = try await get(
            "discovery/community/posts/\(id)",
            queryItems: [
                URLQueryItem(name: "viewer_user_id", value: Self.currentUserID)
            ]
        )
        return try unwrapItem(response)
    }

    func fetchUserPosts(userID: String) async throws -> [DiscoverCommunityPost] {
        let response: DiscoverListResponse<DiscoverCommunityPost> = try await get(
            "discovery/community/users/\(userID)/posts",
            queryItems: [
                URLQueryItem(name: "viewer_user_id", value: Self.currentUserID)
            ]
        )
        return response.items
    }

    func createPost(
        title: String,
        body: String,
        region: String,
        badge: String = "同城讨论",
        visibility: DiscoverPostVisibility = .public
    ) async throws -> DiscoverCommunityPost {
        let request = DiscoverPostCreateRequest(
            userID: Self.currentUserID,
            userName: Self.currentUserName,
            region: region,
            badge: badge,
            title: title,
            body: body,
            visibility: visibility
        )
        let response: DiscoverItemResponse<DiscoverCommunityPost> = try await post(
            "discovery/community/posts",
            body: request
        )
        return try unwrapItem(response)
    }

    func updatePost(
        id: String,
        title: String,
        body: String,
        badge: String,
        visibility: DiscoverPostVisibility
    ) async throws -> DiscoverCommunityPost {
        let request = DiscoverPostUpdateRequest(
            userID: Self.currentUserID,
            title: title,
            body: body,
            badge: badge,
            visibility: visibility
        )
        let response: DiscoverItemResponse<DiscoverCommunityPost> = try await put(
            "discovery/community/posts/\(id)",
            body: request
        )
        return try unwrapItem(response)
    }

    func likePost(id: String) async throws -> DiscoverCommunityPost {
        let response: DiscoverItemResponse<DiscoverCommunityPost> = try await post(
            "discovery/community/posts/\(id)/like",
            body: EmptyBody()
        )
        return try unwrapItem(response)
    }

    func searchVenues(
        city: String? = nil,
        district: String?,
        keyword: String = "足球场",
        latitude: Double? = nil,
        longitude: Double? = nil,
        radius: Int = 20000
    ) async throws -> DiscoverVenueSearchResponse {
        try await get(
            "discovery/venues/search",
            queryItems: [
                URLQueryItem(name: "city", value: city),
                URLQueryItem(name: "district", value: district),
                URLQueryItem(name: "keyword", value: keyword),
                URLQueryItem(name: "latitude", value: latitude.map { String($0) }),
                URLQueryItem(name: "longitude", value: longitude.map { String($0) }),
                URLQueryItem(name: "radius", value: String(radius))
            ]
        )
    }

    func fetchCoaches(region: String? = nil) async throws -> [DiscoverCoachListing] {
        let response: DiscoverListResponse<DiscoverCoachListing> = try await get(
            "discovery/coaches",
            queryItems: [
                URLQueryItem(name: "region", value: region)
            ]
        )
        return response.items
    }

    func bookCoach(
        coachID: String,
        region: String,
        goal: String,
        contact: String = "demo@kick.local",
        preferredTime: String? = "本周内"
    ) async throws -> DiscoverCoachBooking {
        let request = DiscoverCoachBookingCreateRequest(
            coachID: coachID,
            userName: "KickAI 用户",
            contact: contact,
            region: region,
            goal: goal,
            preferredTime: preferredTime
        )
        let response: DiscoverItemResponse<DiscoverCoachBooking> = try await post(
            "discovery/coaches/bookings",
            body: request
        )
        return try unwrapItem(response)
    }

    func startCoachConversation(
        coachID: String,
        region: String,
        initialMessage: String? = nil
    ) async throws -> DiscoverCoachConversation {
        let request = DiscoverCoachConversationCreateRequest(
            coachID: coachID,
            userID: Self.currentUserID,
            userName: Self.currentUserName,
            region: region,
            initialMessage: initialMessage
        )
        let response: DiscoverItemResponse<DiscoverCoachConversation> = try await post(
            "discovery/coaches/conversations",
            body: request
        )
        return try unwrapItem(response)
    }

    func fetchCoachConversation(id: String) async throws -> DiscoverCoachConversation {
        let response: DiscoverItemResponse<DiscoverCoachConversation> = try await get(
            "discovery/coaches/conversations/\(id)"
        )
        return try unwrapItem(response)
    }

    func sendCoachMessage(
        conversationID: String,
        body: String
    ) async throws -> DiscoverCoachConversation {
        let request = DiscoverCoachMessageCreateRequest(
            senderID: Self.currentUserID,
            senderName: Self.currentUserName,
            body: body
        )
        let response: DiscoverItemResponse<DiscoverCoachConversation> = try await post(
            "discovery/coaches/conversations/\(conversationID)/messages",
            body: request
        )
        return try unwrapItem(response)
    }

    private func get<T: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem] = []
    ) async throws -> T {
        let url = try makeURL(path: path, queryItems: queryItems)
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = configuration.timeout
        return try await perform(request)
    }

    private func post<RequestBody: Encodable, ResponseBody: Decodable>(
        _ path: String,
        body: RequestBody
    ) async throws -> ResponseBody {
        let url = try makeURL(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = configuration.timeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(body)

        return try await perform(request)
    }

    private func put<RequestBody: Encodable, ResponseBody: Decodable>(
        _ path: String,
        body: RequestBody
    ) async throws -> ResponseBody {
        let url = try makeURL(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.timeoutInterval = configuration.timeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(body)

        return try await perform(request)
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw DiscoverServiceError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw DiscoverServiceError.httpStatus(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(T.self, from: data)
    }

    private func makeURL(
        path: String,
        queryItems: [URLQueryItem] = []
    ) throws -> URL {
        guard var url = configuration.baseURL else {
            throw DiscoverServiceError.missingBaseURL
        }

        for component in path.split(separator: "/") {
            url.appendPathComponent(String(component))
        }

        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            throw DiscoverServiceError.invalidURL
        }

        let filteredItems = queryItems.filter { item in
            guard let value = item.value else { return false }
            return !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        if !filteredItems.isEmpty {
            components.queryItems = filteredItems
        }

        guard let finalURL = components.url else {
            throw DiscoverServiceError.invalidURL
        }
        return finalURL
    }

    private func unwrapItem<T>(_ response: DiscoverItemResponse<T>) throws -> T {
        if let item = response.item {
            return item
        }
        throw DiscoverServiceError.invalidResponse
    }
}

private struct EmptyBody: Encodable {}
