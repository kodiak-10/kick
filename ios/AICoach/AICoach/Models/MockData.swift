import Foundation

enum MockData {
    static let onboardingSteps: [OnboardingStep] = [
        OnboardingStep(
            title: "上传你的足球射门视频",
            subtitle: "3 步内开始第一次动作评估",
            detail: "第一版以演示流程为主，你可以先使用应用内示例视频，后续再接真实上传与 AI 分析。",
            symbol: "video.badge.plus"
        ),
        OnboardingStep(
            title: "获得清晰的动作评分",
            subtitle: "总分 + 技术执行 + 控制稳定 + 安全性",
            detail: "我们会把复杂动作指标翻译成训练语言，直接告诉你这次动作哪里好、哪里还能提升。",
            symbol: "figure.soccer"
        ),
        OnboardingStep(
            title: "用 Pro 解锁完整建议",
            subtitle: "高级问题点、训练计划与历史记录",
            detail: "基础版可体验核心评分，Pro 会进一步解锁详细建议、更多历史和更完整的分析内容。",
            symbol: "crown.fill"
        )
    ]

    static let demoClips: [DemoClip] = [
        DemoClip(
            title: "右脚正脚背射门",
            subtitle: "中距离完成射门，适合演示标准分析",
            fileName: "right_foot_finish.mov",
            durationSeconds: 4.8,
            athleteLabel: "Demo Athlete A",
            style: .stadiumBlue
        ),
        DemoClip(
            title: "左脚搓射",
            subtitle: "更强调身体打开与收尾控制",
            fileName: "left_curve_finish.mov",
            durationSeconds: 5.4,
            athleteLabel: "Demo Athlete B",
            style: .sunsetOrange
        ),
        DemoClip(
            title: "受压情况下抢点射门",
            subtitle: "更强调支撑稳定和触球效率",
            fileName: "pressure_finish.mov",
            durationSeconds: 3.9,
            athleteLabel: "Demo Athlete C",
            style: .trainingGreen
        )
    ]

    static let paywallFeatures: [PaywallFeature] = [
        PaywallFeature(
            icon: "chart.bar.doc.horizontal",
            title: "完整动作评分结构",
            detail: "查看总分、技术执行分、控制稳定分与动作安全性分的完整解释。"
        ),
        PaywallFeature(
            icon: "exclamationmark.bubble",
            title: "最多 3 个关键问题点",
            detail: "不止告诉你哪里不够好，还会说明它对出球质量的影响。"
        ),
        PaywallFeature(
            icon: "figure.strengthtraining.traditional",
            title: "专项训练建议",
            detail: "解锁针对射门的练习组合、组次建议与动作提示。"
        ),
        PaywallFeature(
            icon: "clock.arrow.trianglehead.counterclockwise.rotate.90",
            title: "完整历史记录",
            detail: "长期记录你的训练结果，支持回看趋势与对比。"
        )
    ]

    static let sampleHistory: [AnalysisRecord] = [
        makeRecord(
            createdAt: Date().addingTimeInterval(-900),
            athleteLabel: "Demo Athlete Pass",
            clipName: "pass_receive_sequence.mp4",
            duration: 5.9,
            goal: .passing,
            overall: 95,
            technique: 95,
            control: 95,
            safety: 95,
            summary: "传接球序列 动作得分 95/100，主要问题是Pass Execution Time / 传球完成时间。",
            positive: "传球后接球的节奏连贯，整体控制非常稳定。",
            targetZone: "传接衔接",
            contactDescription: "传球和接球之间的节奏清晰，衔接稳定。",
            releaseDescription: "下一动作准备度高，连续性很好。",
            style: .trainingGreen,
            issues: [],
            reportState: .readyToScore,
            qualityStatus: .good,
            observations: [],
            errorTimestamps: [],
            analysisMetrics: [],
            triggeredRules: [],
            failReasons: [],
            feedbackMessages: ["传球完成时间还没有形成稳定评分，建议继续补充样本。"],
            suggestions: [],
            insights: [],
            sequenceResult: passReceiveSequenceResult()
        ),
        makeRecord(
            createdAt: Date().addingTimeInterval(-3_600),
            athleteLabel: "Demo Athlete A",
            clipName: "right_foot_finish.mov",
            duration: 4.8,
            goal: .shooting,
            overall: 86,
            technique: 88,
            control: 80,
            safety: 90,
            summary: "这次射门整体节奏流畅，击球方向稳定，主要损失来自支撑脚位置略偏近。",
            positive: "摆腿时序不错，触球前重心控制较稳。",
            targetZone: "远角低平球",
            contactDescription: "脚背触球位置整体准确",
            releaseDescription: "出球方向稳定，旋转控制中等",
            style: .stadiumBlue,
            issues: [
                issue(.support, "支撑脚落点偏近", "支撑脚距离球心略近，限制了摆腿空间。", "容易让出球角度偏窄，影响远角打门。", time: "0.8s"),
                issue(.strike, "触球瞬间躯干打开稍早", "上半身提早打开，导致发力传导略分散。", "会降低远端角度控制与击球穿透感。", time: "1.7s"),
                issue(.followThrough, "收尾不够完整", "触球后摆腿结束稍急，动作没有完全送出去。", "会让球速上限和随挥稳定性略受影响。", time: "2.9s")
            ],
            reportState: .readyToScore,
            qualityStatus: .good,
            observations: [],
            errorTimestamps: [
                timestamp(0.7, 1.1, "支撑脚落点偏近", "支撑脚与球体距离偏小，影响摆腿通道。"),
                timestamp(1.6, 2.0, "上体提前打开", "触球瞬间上半身先离开目标线。"),
                timestamp(2.8, 3.2, "随摆收尾不足", "触球后动作结束偏快。")
            ],
            analysisMetrics: [
                metric("support_foot_lateral_offset_cm", "支撑脚横向落点", "18 cm", "支撑脚略偏近球侧后方，仍在可接受范围。", tone: .watch),
                metric("support_foot_ap_offset_cm", "支撑脚前后落点", "6 cm", "前后落点基本稳定。", tone: .good),
                metric("trunk_lean_deg_at_impact_proxy", "触球时上体后仰", "11°", "上体保持稳定，没有明显后仰。", tone: .good),
                metric("quality_status", "视频质量状态", "good", "可支持正式评分。", tone: .good)
            ],
            triggeredRules: [
                ruleTrigger("support_foot_too_far", "支撑脚落点偏近", .support, "支撑脚距离球心略近，限制了摆腿空间。"),
                ruleTrigger("upper_body_back_lean", "上体后仰明显", .strike, "触球瞬间上半身提早打开。"),
                ruleTrigger("follow_through_incomplete", "随摆不完整", .followThrough, "收尾动作结束稍急。")
            ],
            failReasons: [],
            feedbackMessages: [
                "支撑脚再靠近球侧后方一点，落点不要离球太远。",
                "触球前把胸口稳住，不要向后倒。",
                "触球后把摆腿继续送出去，不要在碰球瞬间急停。"
            ],
            suggestions: [
                suggestion("下一步重点", "先把支撑脚落在球侧后方半步位置，再保持摆腿通道更顺畅。", "支撑脚定位练习", "3 组 x 10 次", "支撑脚先到位，再完成摆腿。"),
                suggestion("射门稳定训练", "用两点门框目标做 8 组低平球练习，优先保持动作一致性。", "双门角低平球", "8 组 x 5 球", "动作一致比绝对力量更重要。"),
                suggestion("收尾强化", "触球后继续向目标方向送胯，练完整随挥。", "随挥延长练习", "3 组 x 8 次", "击球后保持前送，别急着收腿。")
            ],
            insights: [
                insight("支撑稳定观察", "支撑脚与球的相对距离略近，建议增加约半个脚掌宽的留量。"),
                insight("动作节奏观察", "摆腿起速顺畅，但触球后的收尾断得稍快。"),
                insight("训练建议", "先巩固命中方向，再逐步提高射门力量。")
            ]
        ),
        makeRecord(
            createdAt: Date().addingTimeInterval(-86_400),
            athleteLabel: "Demo Athlete B",
            clipName: "left_curve_finish.mov",
            duration: 5.4,
            goal: .shooting,
            overall: 0,
            technique: 0,
            control: 0,
            safety: 0,
            summary: "当前只记录到部分准备和支撑线索，先看观察结果和重拍建议。",
            positive: "助跑节奏已经进入动作，但关键触球帧还没有完整锁定。",
            targetZone: "近角弧线球",
            contactDescription: "触球点偏上，球的旋转偏多",
            releaseDescription: "出球弧线有潜力，但落点波动较大",
            style: .sunsetOrange,
            issues: [
                issue(.support, "支撑阶段左右平衡不足", "支撑腿稳定时间偏短，身体在触球前有轻微漂移。", "会让出球点与脚型控制不稳定。", time: "1.2s"),
                issue(.strike, "摆腿路线略绕", "摆腿从后向前的路径不够直接。", "影响触球效率与球速输出。", time: "1.8s"),
                issue(.followThrough, "身体朝向没有完全跟随目标", "收尾时髋部和肩线没有完整朝向目标。", "容易造成弧线过多或落点偏差。", time: "2.6s")
            ],
            reportState: .insufficientEvidence,
            qualityStatus: .limited,
            observations: [
                observation(.setup, "0.6s", "动作只记录到准备阶段", "助跑进入节奏，但后续触球瞬间没有完整锁定。"),
                observation(.support, "1.3s", "支撑脚和球体只短暂同框", "画面里能看到落脚，但关键接触帧不够清楚。"),
                observation(.strike, "1.9s", "球轨迹未完整出现", "触球后的球路只出现了部分片段，无法确认最终落点。")
            ],
            errorTimestamps: [
                timestamp(0.5, 0.9, "准备阶段可见", "动作进入前置节奏，但还未完成正式触球。"),
                timestamp(1.2, 1.8, "关键帧不完整", "触球前后画面被部分遮挡，阶段未锁定。")
            ],
            analysisMetrics: [
                metric("support_foot_lateral_offset_cm", "支撑脚横向落点", "—", "支撑脚与球体关系未能稳定锁定。", tone: .neutral),
                metric("support_foot_ap_offset_cm", "支撑脚前后落点", "—", "关键接触帧不完整，无法稳定读取。", tone: .neutral),
                metric("trunk_lean_deg_at_impact_proxy", "触球时上体后仰", "—", "动作阶段未锁定，暂不输出技术分。", tone: .neutral),
                metric("quality_status", "视频质量状态", "limited", "可用于观察结果，但不足以支持正式评分。", tone: .warn)
            ],
            triggeredRules: [
                ruleTrigger("ball_track_missing_ratio_high", "球轨迹缺失比例偏高", .setup, "球轨迹只出现了部分片段，无法确认最终落点。"),
                ruleTrigger("visible_frame_ratio_low", "可见帧比例偏低", .setup, "动作证据不足，阶段未锁定。")
            ],
            failReasons: [
                "当前只检测到部分准备和支撑线索，动作证据不足。",
                "球轨迹不清晰，阶段未锁定。"
            ],
            feedbackMessages: [
                "请补拍全身更清晰的视频，让关键触球帧完整入镜。",
                "动作未完成前先不要看正式评分，先看观察结果。"
            ],
            suggestions: [
                suggestion("优先纠正", "先建立支撑阶段的稳定性，再提升弧线球精度。", "支撑停稳 + 射门", "4 组 x 6 次", "先稳住，再发力。"),
                suggestion("摆腿路径训练", "缩短摆腿绕行，建立更直接的发力路径。", "小步助跑射门", "3 组 x 8 次", "摆腿直达球心，不要绕。"),
                suggestion("目标对齐练习", "收尾时让胸口和髋部更多地跟向目标。", "目标对齐收尾", "3 组 x 10 次", "击球后保持身体朝向目标。")
            ],
            insights: [
                insight("风险提示", "当前不是受伤风险问题，更多是技术完成质量不稳定。"),
                insight("球路观察", "弧线感存在，但每次出球的方向一致性不足。"),
                insight("训练建议", "先稳定球路，再提高球速和旋转。")
            ]
        ),
        makeRecord(
            createdAt: Date().addingTimeInterval(-172_800),
            athleteLabel: "Demo Athlete C",
            clipName: "pressure_finish.mov",
            duration: 3.9,
            goal: .shooting,
            overall: 0,
            technique: 0,
            control: 0,
            safety: 0,
            summary: "本次视频质量不足，先看质量问题和重拍建议。",
            positive: "能看出有完成动作的意图，但清晰度不足以支撑正式判断。",
            targetZone: "门将反方向中高球",
            contactDescription: "触球点与发力方向一致",
            releaseDescription: "球路干净，完成质量接近比赛状态",
            style: .trainingGreen,
            issues: [
                issue(.followThrough, "收尾还可更充分", "已经完成得不错，但随挥还可以更完整一些。", "能进一步提高球速与稳定性上限。", time: "2.8s"),
                issue(.support, "助跑最后一步可再放松", "最后一步略紧，影响动作舒展度。", "在高对抗下可能限制自然发力。", time: "1.4s")
            ],
            reportState: .qualityFail,
            qualityStatus: .poor,
            observations: [
                observation(.setup, "0.4s", "画面抖动明显", "助跑阶段的关键帧不稳定，球体轮廓多次丢失。"),
                observation(.support, "1.1s", "球体被身体遮挡", "支撑脚和球的位置没有持续完整入镜。"),
                observation(.strike, "2.0s", "无法确认最终出球方向", "触球后的球路没有稳定追踪到。")
            ],
            errorTimestamps: [
                timestamp(0.3, 1.0, "画面稳定性不足", "关键动作阶段存在明显抖动。"),
                timestamp(1.0, 2.2, "球体跟踪缺失", "触球前后无法持续识别球体。")
            ],
            analysisMetrics: [
                metric("support_foot_lateral_offset_cm", "支撑脚横向落点", "—", "画面抖动过大，无法稳定读取。", tone: .fail),
                metric("support_foot_ap_offset_cm", "支撑脚前后落点", "—", "球体跟踪缺失，无法确认落点。", tone: .fail),
                metric("trunk_lean_deg_at_impact_proxy", "触球时上体后仰", "—", "关键帧缺失，暂不输出微观技术分。", tone: .fail),
                metric("quality_status", "视频质量状态", "poor", "建议重拍后再分析。", tone: .fail)
            ],
            triggeredRules: [
                ruleTrigger("video_quality_fail", "视频质量不足", .setup, "关键动作阶段存在明显抖动。"),
                ruleTrigger("ball_track_missing_ratio_high", "球轨迹缺失比例偏高", .setup, "触球前后无法持续识别球体。")
            ],
            failReasons: [
                "关键动作阶段存在明显抖动。",
                "球体跟踪缺失，无法稳定输出技术评分。"
            ],
            feedbackMessages: [
                "请重拍更清晰的全身视频，确保球、支撑脚和关键触球瞬间都入镜。",
                "视频质量不足时只看结果，不看微观技术分。"
            ],
            suggestions: [
                suggestion("保持优势", "继续巩固支撑稳定和自然前送，这是你当前最强的部分。", "高质量重复", "6 组 x 4 球", "优先保持动作一致性。"),
                suggestion("进阶提高", "在保证稳定性的前提下，再逐步拉高射门速度。", "速度递增射门", "4 组 x 5 球", "先稳再快。")
            ],
            insights: [
                insight("高分解释", "当前属于良好到优秀之间，可把重点转向更高比赛强度下的稳定性。"),
                insight("技术亮点", "支撑脚落位和重心前送对动作完成质量贡献明显。"),
                insight("下一步", "适合进入更高节奏和更复杂场景的训练。")
            ]
        ),
        makeRecord(
            createdAt: Date().addingTimeInterval(-259_200),
            athleteLabel: "Demo Athlete A",
            clipName: "team_finish_02.mov",
            duration: 4.3,
            goal: .shooting,
            overall: 79,
            technique: 81,
            control: 75,
            safety: 82,
            summary: "整体动作结构已经具备，但触球瞬间的身体对齐还不稳定，所以落点不够整齐。",
            positive: "助跑节奏稳定，进入击球前的准备做得不错。",
            targetZone: "门将近角地滚球",
            contactDescription: "触球质量中等，偶尔偏离理想甜区",
            releaseDescription: "落点偏差主要来自上半身控制",
            style: .stadiumBlue,
            issues: [
                issue(.strike, "触球时肩线略歪", "上半身对目标的控制稍差。", "容易让球路出现轻微飘移。", time: "1.8s"),
                issue(.followThrough, "摆腿结束太快", "触球后急于回收腿部。", "会让发力不完全。", time: "2.7s")
            ],
            reportState: .readyToScore,
            qualityStatus: .good,
            observations: [],
            errorTimestamps: [],
            analysisMetrics: [
                metric("support_foot_lateral_offset_cm", "支撑脚横向落点", "21 cm", "落点接近临界区，仍需再收紧一点。", tone: .watch),
                metric("support_foot_ap_offset_cm", "支撑脚前后落点", "8 cm", "前后位置基本到位。", tone: .good),
                metric("trunk_lean_deg_at_impact_proxy", "触球时上体后仰", "14°", "有轻微后仰，但仍在可控区间。", tone: .watch),
                metric("quality_status", "视频质量状态", "good", "可支持正式评分。", tone: .good)
            ],
            triggeredRules: [
                ruleTrigger("support_foot_too_far", "支撑脚落点偏远", .support, "支撑脚落点仍偏远，影响力量传导。"),
                ruleTrigger("upper_body_back_lean", "上体后仰明显", .strike, "触球时肩线略歪，导致方向控制波动。"),
                ruleTrigger("follow_through_incomplete", "随摆不完整", .followThrough, "摆腿结束太快。")
            ],
            failReasons: [
                "支撑脚落点仍偏远，影响力量传导。",
                "触球时肩线略歪，导致方向控制波动。"
            ],
            feedbackMessages: [
                "支撑脚落位再收近一点，脚尖保持朝向目标。",
                "触球时让胸口更稳，避免提前打开。",
                "击球后把随摆完整送出去，不要急停。"
            ],
            suggestions: [
                suggestion("短期重点", "先让上半身方向和目标对齐，再追求更高球速。", "肩线对齐射门", "3 组 x 8 次", "胸口朝向目标。"),
                suggestion("动作延长", "把随挥送完整，减少急停。", "送髋收尾练习", "3 组 x 10 次", "击球后继续向前。")
            ],
            insights: [
                insight("完成度观察", "动作模式基本对，但缺少稳定的最后一击控制。"),
                insight("训练策略", "优先做低强度高重复的精度练习。")
            ]
        ),
        makeRecord(
            createdAt: Date().addingTimeInterval(-345_600),
            athleteLabel: "Demo Athlete B",
            clipName: "training_finish_07.mov",
            duration: 5.1,
            goal: .shooting,
            overall: 68,
            technique: 70,
            control: 63,
            safety: 73,
            summary: "这次动作更像是匆忙完成的射门，支撑和摆腿节奏都还不够稳定，导致动作质量偏低。",
            positive: "有明显的向前发力意图，敢于完成动作。",
            targetZone: "中路抽射",
            contactDescription: "触球点偏散，击球质量起伏较大",
            releaseDescription: "球路稳定性不足，方向和力量波动明显",
            style: .sunsetOrange,
            issues: [
                issue(.setup, "准备阶段节奏太急", "进入动作前身体还没有完全整理好。", "会让后续环节全部变得仓促。", time: "0.9s"),
                issue(.support, "支撑脚稳定时间不足", "支撑脚刚落地就急于完成触球。", "直接影响动作控制和出球质量。", time: "1.5s"),
                issue(.strike, "触球点不稳定", "脚型和触球区域没有保持一致。", "会导致方向和力量都难以控制。", time: "2.0s")
            ],
            reportState: .readyToScore,
            qualityStatus: .good,
            observations: [],
            errorTimestamps: [],
            analysisMetrics: [
                metric("support_foot_lateral_offset_cm", "支撑脚横向落点", "26 cm", "已经进入偏远区间。", tone: .warn),
                metric("support_foot_ap_offset_cm", "支撑脚前后落点", "12 cm", "前后距离略大，发力链条偏长。", tone: .warn),
                metric("trunk_lean_deg_at_impact_proxy", "触球时上体后仰", "18°", "上体后仰较明显，需要优先纠正。", tone: .warn),
                metric("quality_status", "视频质量状态", "good", "可支持正式评分。", tone: .good)
            ],
            triggeredRules: [
                ruleTrigger("support_foot_too_far", "支撑脚落点偏远", .support, "支撑脚稳定时间不足。"),
                ruleTrigger("upper_body_back_lean", "上体后仰明显", .strike, "触球时肩线略歪。"),
                ruleTrigger("follow_through_incomplete", "随摆不完整", .followThrough, "摆腿结束太快。")
            ],
            failReasons: [
                "支撑脚稳定时间不足。",
                "触球点不稳定。"
            ],
            feedbackMessages: [
                "把节奏放慢，先把准备和支撑阶段做稳。",
                "固定球位反复练触球甜区。",
                "先把动作一致性做出来，再提升力量。"
            ],
            suggestions: [
                suggestion("先做基础", "先把节奏放慢，建立稳定的准备和支撑阶段。", "慢节奏分解射门", "4 组 x 5 次", "动作慢下来，质量先上去。"),
                suggestion("触球专项", "用固定球位反复练触球甜区。", "固定球位击球", "5 组 x 6 球", "追求每次触球都一样。"),
                suggestion("稳定性训练", "加入单脚稳定与支撑训练。", "单脚停稳射门", "3 组 x 8 次", "先停稳再击球。")
            ],
            insights: [
                insight("训练重点", "当前最需要提升的是动作的一致性，而不是力量。"),
                insight("改进顺序", "准备阶段 -> 支撑阶段 -> 触球点，这个顺序更有效。")
            ]
        )
    ]

    static func generateRecord(from draft: UploadDraft, existingCount: Int) -> AnalysisRecord {
        let template: AnalysisRecord
        switch draft.goal {
        case .passing:
            template = sampleHistory.first(where: { $0.sequenceResult != nil }) ?? sampleHistory[0]
        case .firstTouch:
            template = sampleHistory.first(where: { $0.goal == .firstTouch }) ?? sampleHistory.first(where: { $0.goal == .shooting }) ?? sampleHistory[0]
        case .shooting:
            template = sampleHistory.first(where: { $0.goal == .shooting }) ?? sampleHistory[0]
        }

        return AnalysisRecord(
            id: UUID(),
            createdAt: Date(),
            athleteLabel: draft.demoClip.athleteLabel,
            clipName: draft.clipName,
            durationSeconds: draft.durationSeconds,
            goal: draft.goal,
            score: template.score,
            reportState: template.reportState,
            qualityStatus: template.qualityStatus,
            summary: template.summary,
            positiveNote: template.positiveNote,
            targetZone: template.targetZone,
            contactDescription: template.contactDescription,
            releaseDescription: template.releaseDescription,
            thumbnailStyle: draft.demoClip.style,
            analysisMetrics: template.analysisMetrics,
            triggeredRules: template.triggeredRules,
            failReasons: template.failReasons,
            feedbackMessages: template.feedbackMessages,
            issues: template.issues,
            observations: template.observations,
            errorTimestamps: template.errorTimestamps,
            suggestions: template.suggestions,
            premiumInsights: template.premiumInsights,
            sequenceResult: template.sequenceResult
        )
    }

    private static func passReceiveSequenceResult() -> PassReceiveSequenceResult {
        PassReceiveSequenceResult(
            actionDisplayName: "传接球序列",
            overallScore: 95.0,
            levelLabel: ResultLevel.level(for: 95.0).title,
            summary: "传接球序列 动作得分 95/100，主要问题是Pass Execution Time / 传球完成时间。",
            passMetrics: [
                sequenceMetric(
                    "pass_endpoint_error_m",
                    title: "传球终点误差",
                    valueText: "0.185 m",
                    detail: "终点偏差很小，传球落点控制到位。",
                    tone: .good
                ),
                sequenceMetric(
                    "pass_execution_time_s",
                    title: "传球完成时间",
                    valueText: "0.20 s",
                    detail: "当前是低置信度结果，先作为待确认项，不要当作错误。",
                    tone: .watch,
                    lowConfidence: true
                )
            ],
            receiveMetrics: [
                sequenceMetric(
                    "receive_control_zone_success_rate",
                    title: "接球控制区成功率",
                    valueText: "97%",
                    detail: "接球后的控制区命中率很高，第一下处理很稳。",
                    tone: .good
                ),
                sequenceMetric(
                    "receive_stabilization_time_s",
                    title: "接球稳定时间",
                    valueText: "0.13 s",
                    detail: "接球后很快回到稳定控制状态。",
                    tone: .good
                ),
                sequenceMetric(
                    "receive_corrective_touch_count",
                    title: "接球补救触球数",
                    valueText: "0 次",
                    detail: "没有额外补救触球，动作完成干净。",
                    tone: .good
                )
            ],
            sequenceMetrics: [
                sequenceMetric(
                    "pass_receive_gap_s",
                    title: "传接间隔",
                    valueText: "0.18 s",
                    detail: "传接之间几乎没有多余停顿，衔接很流畅。",
                    tone: .good
                ),
                sequenceMetric(
                    "sequence_continuity_score",
                    title: "序列衔接分",
                    valueText: "93%",
                    detail: "序列整体连贯性高，动作链条完整。",
                    tone: .good
                ),
                sequenceMetric(
                    "next_action_readiness",
                    title: "下一动作准备度",
                    valueText: "96.6%",
                    detail: "接球后可以很快进入下一步动作。",
                    tone: .good
                )
            ],
            feedbackMessages: ["传球完成时间还没有形成稳定评分，建议继续补充样本。"],
            rawActionCandidates: [
                candidate("first_touch_like", score: 0.958, sources: ["temporal_features.first_touch_like", "temporal_best_prediction", "temporal_action_votes"]),
                candidate("pass_like", score: 0.92, sources: ["temporal_features.pass_like", "temporal_action_votes", "sequence_snapshot.action_label"]),
                candidate("shoot_like", score: 0.378, sources: ["temporal_action_votes"]),
                candidate("shot_like", score: 0.375, sources: ["temporal_features.shot_like"])
            ],
            candidateScores: [
                "first_touch_like": 0.958,
                "pass_like": 0.92,
                "shoot_like": 0.378,
                "shot_like": 0.375
            ],
            metricDebug: [
                "pass_execution_time": SequenceMetricDebugField(
                    value: 0.2,
                    resolved: true,
                    lowConfidence: true,
                    confidence: 0.78,
                    startTime: 0.166,
                    endTime: 0.366,
                    startEvent: "pre_contact_proxy",
                    endEvent: "pass_contact",
                    eventSource: "frame_proxy",
                    fallbackToVideoEnd: false,
                    rawValue: nil,
                    score: nil,
                    band: nil,
                    direction: nil,
                    thresholds: nil,
                    logic: nil,
                    contactDetected: nil,
                    receiveContactDetected: nil,
                    stabilizationDetected: nil,
                    usedProxyLocalWindow: nil,
                    usedVideoEndTime: nil,
                    passExecutionLowConfidence: nil,
                    passReceiveGapLowConfidence: nil,
                    receiveStabilizationLowConfidence: nil
                ),
                "pass_receive_gap": SequenceMetricDebugField(
                    value: 0.183,
                    resolved: true,
                    lowConfidence: false,
                    confidence: 1.0,
                    startTime: 0.366,
                    endTime: 0.549,
                    startEvent: "pass_contact",
                    endEvent: "receive_contact",
                    eventSource: "contact_pair",
                    fallbackToVideoEnd: false,
                    rawValue: nil,
                    score: nil,
                    band: nil,
                    direction: nil,
                    thresholds: nil,
                    logic: nil,
                    contactDetected: nil,
                    receiveContactDetected: nil,
                    stabilizationDetected: nil,
                    usedProxyLocalWindow: nil,
                    usedVideoEndTime: nil,
                    passExecutionLowConfidence: nil,
                    passReceiveGapLowConfidence: nil,
                    receiveStabilizationLowConfidence: nil
                ),
                "receive_stabilization_time": SequenceMetricDebugField(
                    value: 0.133,
                    resolved: true,
                    lowConfidence: false,
                    confidence: 1.0,
                    startTime: 0.549,
                    endTime: 0.682,
                    startEvent: "receive_contact",
                    endEvent: "receive_stable_state",
                    eventSource: "stable_control_window",
                    fallbackToVideoEnd: false,
                    rawValue: nil,
                    score: nil,
                    band: nil,
                    direction: nil,
                    thresholds: nil,
                    logic: nil,
                    contactDetected: nil,
                    receiveContactDetected: nil,
                    stabilizationDetected: nil,
                    usedProxyLocalWindow: nil,
                    usedVideoEndTime: nil,
                    passExecutionLowConfidence: nil,
                    passReceiveGapLowConfidence: nil,
                    receiveStabilizationLowConfidence: nil
                ),
                "fallback_flags": SequenceMetricDebugField(
                    value: nil,
                    resolved: nil,
                    lowConfidence: nil,
                    confidence: nil,
                    startTime: nil,
                    endTime: nil,
                    startEvent: nil,
                    endEvent: nil,
                    eventSource: nil,
                    fallbackToVideoEnd: nil,
                    rawValue: nil,
                    score: nil,
                    band: nil,
                    direction: nil,
                    thresholds: nil,
                    logic: nil,
                    contactDetected: true,
                    receiveContactDetected: true,
                    stabilizationDetected: true,
                    usedProxyLocalWindow: true,
                    usedVideoEndTime: false,
                    passExecutionLowConfidence: true,
                    passReceiveGapLowConfidence: false,
                    receiveStabilizationLowConfidence: false
                ),
                "receive_control_zone_success_rate_band_logic": SequenceMetricDebugField(
                    value: nil,
                    resolved: nil,
                    lowConfidence: nil,
                    confidence: nil,
                    startTime: nil,
                    endTime: nil,
                    startEvent: nil,
                    endEvent: nil,
                    eventSource: nil,
                    fallbackToVideoEnd: nil,
                    rawValue: 0.97,
                    score: 100.0,
                    band: "excellent",
                    direction: "higher_is_better",
                    thresholds: [
                        "excellent": 0.82,
                        "good": 0.65,
                        "needs_work": 0.45
                    ],
                    logic: [
                        SequenceBandLogicStep(condition: "raw_value >= excellent", band: "excellent", otherwise: nil),
                        SequenceBandLogicStep(condition: "raw_value >= good", band: "good", otherwise: nil),
                        SequenceBandLogicStep(condition: "raw_value >= needs_work", band: "needs_work", otherwise: nil),
                        SequenceBandLogicStep(condition: nil, band: nil, otherwise: "poor")
                    ],
                    contactDetected: nil,
                    receiveContactDetected: nil,
                    stabilizationDetected: nil,
                    usedProxyLocalWindow: nil,
                    usedVideoEndTime: nil,
                    passExecutionLowConfidence: nil,
                    passReceiveGapLowConfidence: nil,
                    receiveStabilizationLowConfidence: nil
                )
            ],
            qualityGate: SequenceQualityGate(
                actionName: "pass_receive_sequence",
                qualityStatus: "pass",
                passed: true,
                allowMicroTechniqueScore: true,
                hideMicroTechniqueScore: false,
                shouldReshoot: false,
                reshootHint: "请重拍更清晰的全身视频，确保球、支撑脚和关键触球瞬间都入镜。",
                thresholds: [
                    "min_video_fps_outcome": 30.0,
                    "min_video_fps_technique": 60.0,
                    "min_pose_visibility": 0.75,
                    "min_pose_presence": 0.75,
                    "min_visible_frame_ratio": 0.85,
                    "max_ball_track_missing_ratio": 0.1
                ],
                observed: [
                    "fps": 60.109086071571106,
                    "pose_presence": 1.0,
                    "visible_frame_ratio": 1.0,
                    "pose_visibility": 0.987274891777536,
                    "ball_track_missing_ratio": 0.0028328611898017497,
                    "frame_count": 353.0,
                    "valid_pose_frames": 353.0,
                    "ball_frames": 352.0
                ],
                triggeredRules: [],
                failReasons: []
            )
        )
    }

    private static func makeRecord(
        createdAt: Date,
        athleteLabel: String,
        clipName: String,
        duration: Double,
        goal: TrainingGoal,
        overall: Int,
        technique: Int,
        control: Int,
        safety: Int,
        summary: String,
        positive: String,
        targetZone: String,
        contactDescription: String,
        releaseDescription: String,
        style: ThumbnailStyle,
        issues: [AnalysisIssue],
        reportState: ResultReportState = .readyToScore,
        qualityStatus: VideoQualityStatus = .good,
        observations: [ResultObservation] = [],
        errorTimestamps: [ResultTimestamp] = [],
        analysisMetrics: [AnalysisMetric] = [],
        triggeredRules: [RuleTriggerSummary] = [],
        failReasons: [String] = [],
        feedbackMessages: [String] = [],
        suggestions: [TrainingSuggestion],
        insights: [PremiumInsight],
        sequenceResult: PassReceiveSequenceResult? = nil
    ) -> AnalysisRecord {
        AnalysisRecord(
            id: UUID(),
            createdAt: createdAt,
            athleteLabel: athleteLabel,
            clipName: clipName,
            durationSeconds: duration,
            goal: goal,
            score: ScoreBreakdown(
                overall: overall,
                technique: technique,
                control: control,
                safety: safety
            ),
            reportState: reportState,
            qualityStatus: qualityStatus,
            summary: summary,
            positiveNote: positive,
            targetZone: targetZone,
            contactDescription: contactDescription,
            releaseDescription: releaseDescription,
            thumbnailStyle: style,
            analysisMetrics: analysisMetrics,
            triggeredRules: triggeredRules,
            failReasons: failReasons,
            feedbackMessages: feedbackMessages,
            issues: issues,
            observations: observations,
            errorTimestamps: errorTimestamps,
            suggestions: suggestions,
            premiumInsights: insights,
            sequenceResult: sequenceResult
        )
    }

    private static func issue(
        _ stage: MotionStage,
        _ title: String,
        _ detail: String,
        _ impact: String,
        time: String? = nil
    ) -> AnalysisIssue {
        AnalysisIssue(id: UUID(), stage: stage, title: title, detail: detail, impact: impact, time: time)
    }

    private static func observation(
        _ stage: MotionStage,
        _ time: String,
        _ title: String,
        _ detail: String
    ) -> ResultObservation {
        ResultObservation(id: UUID(), phase: stage, time: time, title: title, detail: detail)
    }

    private static func timestamp(
        _ start: Double,
        _ end: Double,
        _ label: String,
        _ detail: String
    ) -> ResultTimestamp {
        ResultTimestamp(id: UUID(), start: start, end: end, label: label, detail: detail)
    }

    private static func metric(
        _ key: String,
        _ title: String,
        _ valueText: String,
        _ detail: String,
        tone: AnalysisSignalTone
    ) -> AnalysisMetric {
        AnalysisMetric(
            key: key,
            title: title,
            valueText: valueText,
            detail: detail,
            tone: tone
        )
    }

    private static func ruleTrigger(
        _ key: String,
        _ title: String,
        _ phase: MotionStage,
        _ detail: String
    ) -> RuleTriggerSummary {
        RuleTriggerSummary(
            key: key,
            title: title,
            phase: phase,
            detail: detail
        )
    }

    private static func suggestion(
        _ title: String,
        _ summary: String,
        _ drillName: String,
        _ dosage: String,
        _ cue: String,
        proOnly: Bool = false
    ) -> TrainingSuggestion {
        TrainingSuggestion(
            id: UUID(),
            title: title,
            summary: summary,
            drill: DrillRecommendation(
                id: UUID(),
                name: drillName,
                dosage: dosage,
                cue: cue
            ),
            proOnly: proOnly
        )
    }

    private static func insight(_ title: String, _ detail: String) -> PremiumInsight {
        PremiumInsight(id: UUID(), title: title, detail: detail)
    }

    private static func sequenceMetric(
        _ id: String,
        title: String,
        valueText: String,
        detail: String,
        tone: AnalysisSignalTone,
        lowConfidence: Bool = false
    ) -> SequenceMetricSummary {
        SequenceMetricSummary(
            id: id,
            title: title,
            valueText: valueText,
            detail: detail,
            tone: tone,
            lowConfidence: lowConfidence
        )
    }

    private static func candidate(
        _ action: String,
        score: Double,
        sources: [String]
    ) -> SequenceActionCandidate {
        SequenceActionCandidate(action: action, score: score, sources: sources)
    }
}
