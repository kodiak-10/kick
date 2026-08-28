import Foundation

enum AppTab: Hashable {
    case home
    case analysis
    case discover
    case history
    case profile

    var title: String {
        switch self {
        case .home:
            return "首页"
        case .analysis:
            return "分析"
        case .discover:
            return "发现"
        case .history:
            return "历史"
        case .profile:
            return "我的"
        }
    }

    var iconName: String {
        switch self {
        case .home:
            return "house"
        case .analysis:
            return "video.fill"
        case .discover:
            return "mappin.and.ellipse"
        case .history:
            return "chart.line.uptrend.xyaxis"
        case .profile:
            return "person.crop.circle"
        }
    }
}
