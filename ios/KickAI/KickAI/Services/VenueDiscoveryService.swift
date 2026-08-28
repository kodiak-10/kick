import Foundation

struct FootballVenue: Identifiable, Codable, Hashable {
    let id: String
    let name: String
    let address: String
    let latitude: Double?
    let longitude: Double?
    let phone: String?
    let source: VenueDataSource
    let lastVerifiedAt: Date?
}

struct VenueSearchQuery: Codable, Hashable {
    var cityOrAdcode: String
    var keyword: String
    var latitude: Double?
    var longitude: Double?
    var radiusMeters: Int
}

enum VenueDataSource: String, Codable, CaseIterable {
    case amap
    case baidu
    case tencent
    case userCorrection
    case venueOwner

    var displayName: String {
        switch self {
        case .amap:
            return "高德地图"
        case .baidu:
            return "百度地图"
        case .tencent:
            return "腾讯地图"
        case .userCorrection:
            return "用户纠错"
        case .venueOwner:
            return "球场认证"
        }
    }
}

enum VenueDiscoveryPlan {
    static let footballKeywords = [
        "足球场",
        "五人制足球场",
        "七人制足球场",
        "体育场馆 足球",
        "校园足球场"
    ]

    static func queries(for cityOrAdcode: String, latitude: Double? = nil, longitude: Double? = nil) -> [VenueSearchQuery] {
        footballKeywords.map { keyword in
            VenueSearchQuery(
                cityOrAdcode: cityOrAdcode,
                keyword: keyword,
                latitude: latitude,
                longitude: longitude,
                radiusMeters: 10_000
            )
        }
    }
}

protocol VenueDiscoveryProviding {
    var source: VenueDataSource { get }
    func searchVenues(query: VenueSearchQuery) async throws -> [FootballVenue]
}

enum VenueDiscoveryPolicy {
    static func mergeAndRank(_ venues: [FootballVenue]) -> [FootballVenue] {
        Dictionary(grouping: venues) { venue in
            "\(venue.name)-\(venue.address)"
        }
        .compactMap { _, candidates in
            candidates.sorted { lhs, rhs in
                reliabilityWeight(lhs.source) > reliabilityWeight(rhs.source)
            }
            .first
        }
        .sorted { lhs, rhs in
            reliabilityWeight(lhs.source) == reliabilityWeight(rhs.source)
                ? lhs.name < rhs.name
                : reliabilityWeight(lhs.source) > reliabilityWeight(rhs.source)
        }
    }

    static func reliabilityLabel(for source: VenueDataSource) -> String {
        switch source {
        case .venueOwner:
            return "商家认证"
        case .userCorrection:
            return "用户校验"
        case .amap, .baidu, .tencent:
            return "地图来源"
        }
    }

    private static func reliabilityWeight(_ source: VenueDataSource) -> Int {
        switch source {
        case .venueOwner:
            return 3
        case .userCorrection:
            return 2
        case .amap, .baidu, .tencent:
            return 1
        }
    }
}
