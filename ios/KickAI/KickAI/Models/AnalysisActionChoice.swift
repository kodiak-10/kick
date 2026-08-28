import Foundation

enum AnalysisActionChoice: String, CaseIterable, Identifiable, Codable, Hashable, CustomStringConvertible {
    case pass
    case shot
    case receive
    case passReceive = "pass_receive"
    case fullMatch = "full_match"
    case other

    var id: String { rawValue }

    var description: String {
        selectedActionValue
    }

    var displayTitle: String {
        switch self {
        case .pass:
            return "传球"
        case .shot:
            return "射门"
        case .receive:
            return "接球"
        case .passReceive:
            return "传接球"
        case .fullMatch:
            return "单一球员长视频"
        case .other:
            return "其他/暂不确定"
        }
    }

    var subtitle: String {
        switch self {
        case .pass:
            return "适合短传、推进传、传接配合和连续处理"
        case .shot:
            return "适合起脚、发力和射门节奏训练"
        case .receive:
            return "适合第一脚触球、接球和控球"
        case .passReceive:
            return "适合传球后接球再处理的连续动作"
        case .fullMatch:
            return "上传长视频，先锁定一名球员，再做技术事件和关键动作分析"
        case .other:
            return "动作还不确定时，也可以先继续上传视频"
        }
    }

    var iconName: String {
        switch self {
        case .pass:
            return "paperplane.fill"
        case .shot:
            return "figure.soccer"
        case .receive:
            return "hand.raised.fill"
        case .passReceive:
            return "link"
        case .fullMatch:
            return "sportscourt.fill"
        case .other:
            return "questionmark.circle.fill"
        }
    }

    /// Sent as the user's explicit choice.
    var selectedActionValue: String {
        switch self {
        case .pass:
            return "pass"
        case .shot:
            return "shot"
        case .receive:
            return "receive"
        case .passReceive:
            return "pass_receive_sequence"
        case .fullMatch:
            return "full_match"
        case .other:
            return "other"
        }
    }

    /// Sent as an analysis template hint for the backend.
    var analysisTemplateValue: String {
        switch self {
        case .pass:
            return "short_pass"
        case .shot:
            return "shot_instep"
        case .receive:
            return "receive_control"
        case .passReceive:
            return "pass_receive_sequence"
        case .fullMatch:
            return "full_match_player"
        case .other:
            return "uncertain"
        }
    }

    static func backendMatch(for rawValue: String?) -> AnalysisActionChoice? {
        guard let rawValue else {
            return nil
        }

        let normalized = rawValue
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()

        guard !normalized.isEmpty else {
            return nil
        }

        if normalized.contains("full_match") || normalized.contains("match_player") || normalized.contains("整场比赛") || normalized.contains("全场") || normalized.contains("比赛分析") {
            return .fullMatch
        }

        if normalized.contains("pass_receive") || normalized.contains("passreceive") || normalized.contains("传接") || normalized.contains("sequence") {
            return .passReceive
        }

        if normalized.contains("receive_control") || normalized.contains("first_touch") || normalized.contains("receive") || normalized.contains("接球") {
            return .receive
        }

        if normalized.contains("shot_instep") || normalized.contains("shoot") || normalized.contains("shot") || normalized.contains("射门") {
            return .shot
        }

        if normalized.contains("short_pass") || normalized.contains("pass_like") || normalized == "pass" || normalized.contains("传球") || normalized.contains("pass") {
            return .pass
        }

        if normalized.contains("uncertain") || normalized.contains("pending_confirmation") || normalized.contains("needs_confirmation") || normalized.contains("other") || normalized.contains("暂不确定") || normalized.contains("其他") {
            return .other
        }

        return nil
    }
}
