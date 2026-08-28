import Foundation

enum MotionPhase: String, Hashable, CaseIterable, Codable {
    case approach
    case support
    case strike
    case followThrough

    var displayName: String {
        switch self {
        case .approach:
            return "助跑阶段"
        case .support:
            return "支撑阶段"
        case .strike:
            return "击球阶段"
        case .followThrough:
            return "随摆阶段"
        }
    }

    var symbolName: String {
        switch self {
        case .approach:
            return "figure.run"
        case .support:
            return "figure.stand"
        case .strike:
            return "soccerball"
        case .followThrough:
            return "arrow.right"
        }
    }
}

struct PlaybackIssue: Identifiable, Hashable, Codable {
    let id: UUID
    let time: Double
    let title: String
    let phase: MotionPhase
    let shortHint: String
    let explanation: String
    let fixAdvice: String
    let trainingAdvice: String
    let isProOnly: Bool

    init(
        id: UUID = UUID(),
        time: Double,
        title: String,
        phase: MotionPhase,
        shortHint: String,
        explanation: String,
        fixAdvice: String,
        trainingAdvice: String,
        isProOnly: Bool
    ) {
        self.id = id
        self.time = time
        self.title = title
        self.phase = phase
        self.shortHint = shortHint
        self.explanation = explanation
        self.fixAdvice = fixAdvice
        self.trainingAdvice = trainingAdvice
        self.isProOnly = isProOnly
    }

    var timeLabel: String {
        String(format: "%.1fs", time)
    }
}

struct VideoReviewData: Hashable, Codable {
    let duration: Double
    let freeIssueLimit: Int
    let issues: [PlaybackIssue]
}

extension PlaybackIssue {
    static func fallbackIssues(for result: AnalysisResult) -> [PlaybackIssue] {
        let isShot = result.motionType.localizedCaseInsensitiveContains("射门") ||
            result.motionType.localizedCaseInsensitiveContains("shot")
        let duration = max(result.videoReviewData.duration, 6)
        let firstIssue = result.freeIssues.first
        let firstSuggestion = result.trainingSuggestions.first

        if isShot {
            return [
                PlaybackIssue(
                    time: duration * 0.42,
                    title: firstIssue?.title.nonEmpty ?? "支撑脚和目标区",
                    phase: .support,
                    shortHint: firstIssue?.detail.nonEmpty ?? "先看支撑脚是否踩稳、脚尖是否指向目标区。",
                    explanation: "射门质量主要由支撑底座、摆腿发力链和触球后球门方向共同决定；当前缺少稳定回看节点时，先按这三个环节检查。",
                    fixAdvice: "支撑脚落在球侧 15-25cm，脚尖朝目标区，身体略压住球，不要后仰。",
                    trainingAdvice: firstSuggestion?.nonEmpty ?? "做 4 组定点射门，每组 6 球，记录命中目标区次数。",
                    isProOnly: false
                ),
                PlaybackIssue(
                    time: duration * 0.58,
                    title: "摆腿发力链",
                    phase: .strike,
                    shortHint: "看髋部是否先带动大腿，再带小腿和脚背击球。",
                    explanation: "如果只靠小腿甩动，球速和方向会不稳定；髋部、大腿、小腿、脚踝需要按顺序传递力量。",
                    fixAdvice: "先 70% 力量完成动作，触球后脚背继续向目标方向送出。",
                    trainingAdvice: "做 3 组无球摆腿 8 次 + 有球射门 5 次，重点练髋部、大腿前侧和脚踝锁定。",
                    isProOnly: true
                ),
                PlaybackIssue(
                    time: duration * 0.72,
                    title: "球门结果判断",
                    phase: .followThrough,
                    shortHint: "看球是否进门、进门区域和高度是否符合目标。",
                    explanation: "射门不是只看动作好不好，还要结合是否进门、球速、角度和落点稳定性判断。",
                    fixAdvice: "每组固定一个目标区，先追求命中，再逐步提高力量。",
                    trainingAdvice: "做 5 组目标区射门，每组 4 球，左右下角、左右上角轮换。",
                    isProOnly: true
                )
            ]
        }

        return [
            PlaybackIssue(
                time: duration * 0.32,
                title: firstIssue?.title.nonEmpty ?? "支撑脚和触球面",
                phase: .support,
                shortHint: firstIssue?.detail.nonEmpty ?? "先看支撑脚指向、脚踝锁定和触球面是否稳定。",
                explanation: "传球质量优先看球是否按预期线路、速度和落点到达目标；支撑脚和触球面是最稳定的检查入口。",
                fixAdvice: "支撑脚指向目标，脚内侧平面打开，触球后腿继续向目标方向送出。",
                trainingAdvice: firstSuggestion?.nonEmpty ?? "做 4 组墙传或目标门传球，每组 12 次，左右脚各练。",
                isProOnly: false
            ),
            PlaybackIssue(
                time: duration * 0.52,
                title: "出球线路",
                phase: .strike,
                shortHint: "看球的方向、速度和落点是否服务下一步处理。",
                explanation: "传球不是单纯把球踢出去，而是要让队友下一步能舒服处理。",
                fixAdvice: "先降低力量，保证出球线稳定，再逐步加入移动目标。",
                trainingAdvice: "设置 1.5 米目标门，做 5 组穿门传球，每组 10 次，记录通过率。",
                isProOnly: true
            ),
            PlaybackIssue(
                time: duration * 0.68,
                title: "接续动作准备",
                phase: .followThrough,
                shortHint: "看传球后身体是否能继续移动或准备下一脚。",
                explanation: "传完球后如果停住，比赛中会影响接应和二次处理。",
                fixAdvice: "触球后顺势迈出下一步，保持身体面向下一处理方向。",
                trainingAdvice: "做 4 组传球后启动练习，每组 8 次，练协调性、节奏感和第一步反应。",
                isProOnly: true
            )
        ]
    }
}
