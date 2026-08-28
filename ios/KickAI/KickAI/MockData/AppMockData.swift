import Foundation

enum AppMockData {
    static let onboardingPages: [OnboardingPage] = [
        OnboardingPage(
            iconName: "figure.soccer",
            title: "上传足球训练视频",
            subtitle: "适用于传球、接球、停球、射门等基础动作"
        ),
        OnboardingPage(
            iconName: "scope",
            title: "不只给分，更给反馈",
            subtitle: "定位最值得优先改的动作点，标记关键时刻，告诉你怎么改、怎么练"
        ),
        OnboardingPage(
            iconName: "crown.fill",
            title: "会员解锁更细诊断",
            subtitle: "查看错误时刻标记、关键帧分析、更细训练建议和历史对比"
        )
    ]

    static let permissionItems: [PermissionItem] = [
        PermissionItem(
            iconName: "camera.fill",
            title: "相机权限",
            detail: "用于拍摄动作视频"
        ),
        PermissionItem(
            iconName: "photo.on.rectangle.angled",
            title: "相册权限",
            detail: "用于上传已有训练视频"
        )
    ]

    static let premiumFeatures: [AppFeature] = [
        AppFeature(
            iconName: "exclamationmark.triangle.fill",
            title: "错误时刻标记",
            detail: "把最关键的错误点单独标出来，直接定位到视频时刻"
        ),
        AppFeature(
            iconName: "photo.on.rectangle.angled",
            title: "关键帧分析",
            detail: "查看接球前、出脚瞬间和稳定瞬间的画面证据"
        ),
        AppFeature(
            iconName: "slider.horizontal.3",
            title: "更细的关键反馈",
            detail: "把优先改什么、为什么先改它讲清楚"
        ),
        AppFeature(
            iconName: "list.bullet.clipboard",
            title: "更具体的训练建议",
            detail: "直接给出可执行的练习方式和训练节奏"
        ),
        AppFeature(
            iconName: "chart.xyaxis.line",
            title: "历史对比与进步追踪",
            detail: "持续看见你的变化，而不是只看单次分数"
        ),
        AppFeature(
            iconName: "square.and.arrow.up",
            title: "训练复盘导出",
            detail: "把训练反馈整理成方便回看的复盘摘要"
        )
    ]

    static let subscriptionPlans: [SubscriptionPlan] = [
        SubscriptionPlan(
            id: "monthly",
            title: "月付专业版",
            price: "¥38 / 月",
            note: "按月续订，可随时取消",
            description: "适合短期专项训练",
            badge: nil
        ),
        SubscriptionPlan(
            id: "yearly",
            title: "年付专业版",
            price: "¥268 / 年",
            note: "约合 ¥22 / 月，长期更划算",
            description: "适合持续追踪进步",
            badge: "最受欢迎"
        )
    ]

    static let processingSteps: [ProcessingStep] = [
        ProcessingStep(title: "视频上传成功", subtitle: "训练片段已准备进入分析流程"),
        ProcessingStep(title: "正在确认动作类型", subtitle: "系统会辅助判断动作趋势，但不会替代你的选择"),
        ProcessingStep(title: "正在提取关键动作节点", subtitle: "定位支撑、触球与随摆阶段的重点帧"),
        ProcessingStep(title: "正在生成分析结果", subtitle: "整理问题诊断、评分与建议")
    ]

    static let userProfile = UserProfile(
        id: UUID(),
        name: "Kodiak",
        email: "kodiak@kick.app",
        avatarSymbolName: "person.crop.circle.fill",
        tier: .free
    )

    static let latestAnalysis = makeAnalysisResult(index: 0)

    static let historyItems: [HistoryItem] = [
        historyItem(dayOffset: -1, score: 78, issue: "支撑脚位置偏远"),
        historyItem(dayOffset: -3, score: 82, issue: "摆腿节奏偏慢"),
        historyItem(dayOffset: -5, score: 75, issue: "上体后仰明显"),
        historyItem(dayOffset: -8, score: 72, issue: "触球时机略晚")
    ]

    static func makeAnalysisResult(index: Int) -> AnalysisResult {
        let issueSets: [[AnalysisIssue]] = [
            [
                AnalysisIssue(title: "支撑脚落点偏远", detail: "支撑脚距离球体稍远，力量传导不够集中。", severityLabel: "优先修正"),
                AnalysisIssue(title: "上体后仰明显", detail: "触球瞬间上体控制不足，影响压球质量。", severityLabel: "重点关注")
            ],
            [
                AnalysisIssue(title: "摆腿节奏偏慢", detail: "摆腿加速阶段偏保守，导致出球速度不稳定。", severityLabel: "重点关注"),
                AnalysisIssue(title: "髋部打开不足", detail: "触球前身体旋转幅度有限，影响发力方向。", severityLabel: "建议优化")
            ],
            [
                AnalysisIssue(title: "触球时机略晚", detail: "触球点偏后，导致球路抬升较多。", severityLabel: "优先修正"),
                AnalysisIssue(title: "落地衔接不够稳", detail: "随摆后的重心回收较慢，影响动作连贯性。", severityLabel: "建议优化")
            ]
        ]

        let summaries = [
            "动作基础较好，但支撑脚与上体控制还有提升空间。",
            "发力链路比较清晰，细节稳定性仍有继续打磨的空间。",
            "整体动作完成度不错，节奏控制和触球精度还可以更稳定。"
        ]

        let scores = [78, 82, 76, 84]
        let trends = [
            "近 3 次分析中，稳定性评分持续改善，支撑脚问题出现频率下降。",
            "相比上周，动作节奏更连贯，但触球一致性仍需加强。",
            "近期训练中，下肢发力改善明显，建议继续关注上体控制。"
        ]

        let suggestions = [
            "加入单脚支撑稳定训练，缩短支撑脚与球的距离。",
            "进行低平球击球练习，强化触球瞬间的躯干前压。",
            "用节奏分解练习优化摆腿启动与随摆连贯性。"
        ]
        let videoReviewData = makeVideoReviewData(index: index)

        let resultIndex = abs(index) % scores.count
        let issueIndex = abs(index) % issueSets.count
        let date = Calendar.current.date(byAdding: .day, value: -abs(index), to: Date()) ?? Date()

        return AnalysisResult(
            date: date,
            motionType: "足球动作训练",
            score: scores[resultIndex],
            summary: summaries[resultIndex % summaries.count],
            freeIssues: issueSets[issueIndex],
            videoReviewData: videoReviewData,
            premiumInsights: premiumFeatures,
            trainingSuggestions: suggestions,
            trendSummary: trends[resultIndex % trends.count]
        )
    }

    private static func historyItem(dayOffset: Int, score: Int, issue: String) -> HistoryItem {
        let date = Calendar.current.date(byAdding: .day, value: dayOffset, to: Date()) ?? Date()
        let result = AnalysisResult(
            date: date,
            motionType: "足球动作训练",
            score: score,
            summary: "本次动作完成度稳定，但关键发力节点仍有修正空间。",
            freeIssues: [
                AnalysisIssue(title: issue, detail: "这是当前训练中最值得优先修正的问题。", severityLabel: "重点关注"),
                AnalysisIssue(title: "躯干控制略松", detail: "上体与下肢发力衔接还有提升空间。", severityLabel: "建议优化")
            ],
            videoReviewData: makeVideoReviewData(index: dayOffset),
            premiumInsights: premiumFeatures,
            trainingSuggestions: [
                "进行 10 分钟支撑脚定位训练。",
                "加入慢动作触球练习，提升动作可控性。",
                "复盘拍摄角度，保持侧面完整入镜。"
            ],
            trendSummary: "最近两周整体得分趋于稳定，动作一致性正在提升。"
        )

        return HistoryItem(result: result)
    }

    private static func makeVideoReviewData(index: Int) -> VideoReviewData {
        let timeShift = Double(abs(index) % 3) * 0.05

        let issues: [PlaybackIssue] = [
            PlaybackIssue(
                time: 0.8 + timeShift,
                title: "支撑脚落点偏远",
                phase: .support,
                shortHint: "支撑脚落点偏远会削弱力量传导。",
                explanation: "支撑脚距离球体偏远，身体重心容易后撤，击球时力量链路被拉长，出球方向也更容易出现漂移。",
                fixAdvice: "支撑脚应落在球侧一脚距离内，并提前稳定身体重心。",
                trainingAdvice: "原地支撑脚定位练习，3组 × 10次。",
                isProOnly: false
            ),
            PlaybackIssue(
                time: 1.1 + timeShift,
                title: "上体后仰明显",
                phase: .strike,
                shortHint: "上体后仰会影响压球和出球稳定性。",
                explanation: "触球瞬间上体后仰，导致核心控制被拉松，球的飞行轨迹更容易上飘，击球稳定性下降。",
                fixAdvice: "触球前收紧核心，让胸口略向球前压，保持上体更稳定。",
                trainingAdvice: "靠墙击球控制练习，3组 × 8次。",
                isProOnly: true
            ),
            PlaybackIssue(
                time: 1.3 + timeShift,
                title: "随摆不完整",
                phase: .followThrough,
                shortHint: "随摆不足会影响力量释放和动作连贯性。",
                explanation: "击球后摆腿回收过快，力量没有顺畅释放到球上，动作连贯性也会受到影响。",
                fixAdvice: "击球后让摆腿自然延伸到目标方向，再顺势回收。",
                trainingAdvice: "慢动作随摆控制练习，4组 × 6次。",
                isProOnly: true
            ),
            PlaybackIssue(
                time: 1.6 + timeShift,
                title: "摆腿路径偏外",
                phase: .approach,
                shortHint: "摆腿路径偏外会影响击球面的稳定。",
                explanation: "摆腿轨迹外摆过大，脚背接触角度变化更明显，球的方向和力度都更容易失控。",
                fixAdvice: "从髋部带动摆腿，尽量沿直线加速进入触球点。",
                trainingAdvice: "定点摆腿轨迹练习，3组 × 10次。",
                isProOnly: true
            )
        ]

        return VideoReviewData(
            duration: 2.2 + Double(abs(index) % 2) * 0.1,
            freeIssueLimit: 1,
            issues: issues
        )
    }
}
