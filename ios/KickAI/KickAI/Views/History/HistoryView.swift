import Foundation
import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @State private var displayedMonth = Calendar.current.startOfMonth(for: Date())
    @State private var focusedDate = Date()
    @State private var reviewScope: HistoryReviewScope = .month
    @State private var selectedDaySelection: HistoryDaySelection?
    @State private var didSeedInitialDate = false

    private var calendar: Calendar { .current }

    private var historyItems: [HistoryItem] {
        sessionManager.historyItems.sorted { $0.date > $1.date }
    }

    private var groupedHistory: [Date: [HistoryItem]] {
        let grouped = Dictionary(grouping: historyItems) { calendar.startOfDay(for: $0.date) }
        return grouped.mapValues { $0.sorted { $0.date > $1.date } }
    }

    private var focusedDayItems: [HistoryItem] {
        groupedHistory[calendar.startOfDay(for: focusedDate)] ?? []
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                monthCalendarCard
                scopeSummaryCard

                if historyItems.isEmpty {
                    EmptyStateView(
                        title: "还没有分析记录",
                        subtitle: "分析成功后会自动保存到这里，按月和按周都能继续复盘。",
                        systemImage: "calendar.badge.clock"
                    )
                }
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .kickScreenBackground()
        .navigationTitle("历史记录")
        .navigationBarTitleDisplayMode(.large)
        .kickNavigationBar()
        .onAppear {
            seedInitialDateIfNeeded()
        }
        .onChange(of: sessionManager.historyItems) { _, _ in
            seedInitialDateIfNeeded(force: false)
        }
        .sheet(item: $selectedDaySelection) { selection in
            HistoryDayRecordsSheet(selection: selection)
                .environmentObject(sessionManager)
        }
    }

    private var monthCalendarCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                monthHeader
                weekdayHeader
                calendarGrid
                calendarLegend
                focusedDayCard
            }
        }
    }

    private var monthHeader: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                Text(Self.monthFormatter.string(from: displayedMonth))
                    .font(AppTypography.sectionTitle)
                    .foregroundStyle(AppColors.textPrimary)

                Text("点日期先预览当天记录，状态条只显示概况，详情在下方打开。")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)

            HStack(spacing: 8) {
                calendarButton(systemImage: "chevron.left") {
                    shiftMonth(by: -1)
                }

                calendarButton(systemImage: "chevron.right") {
                    shiftMonth(by: 1)
                }
            }
        }
    }

    private var weekdayHeader: some View {
        HStack(spacing: 8) {
            ForEach(Self.weekdaySymbols, id: \.self) { symbol in
                Text(symbol)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)
                    .frame(maxWidth: .infinity)
            }
        }
    }

    private var calendarGrid: some View {
        LazyVGrid(
            columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 7),
            spacing: 8
        ) {
            ForEach(calendarCells) { cell in
                HistoryCalendarDayCell(
                    cell: cell,
                    onTap: {
                        selectCell(cell)
                    }
                )
            }
        }
    }

    private var calendarLegend: some View {
        HStack(spacing: 10) {
            legendPill(color: AppColors.positive, text: "稳定")
            legendPill(color: AppColors.warning, text: "需注意")
            legendPill(color: AppColors.critical, text: "明显问题")
            legendPill(color: AppColors.reference, text: "低置信")
        }
        .font(AppTypography.captionMedium)
        .foregroundStyle(AppColors.textSecondary)
    }

    private var focusedDayCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(Self.dayFormatter.string(from: focusedDate))
                        .font(AppTypography.bodyMedium)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(focusedDayItems.isEmpty ? "这一天还没有分析记录。" : "这一天有 \(focusedDayItems.count) 次分析，点按钮查看完整列表。")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }

                Spacer(minLength: 0)

                if !focusedDayItems.isEmpty {
                    TrainingFeedbackTag(text: "\(focusedDayItems.count)次")
                }
            }

            if !focusedDayItems.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(focusedDayItems.prefix(4), id: \.id) { item in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(item.motionType)
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(AppColors.textPrimary)

                                Text("\(item.score) 分 · \(item.reviewTone.displayLabel)")
                                    .font(AppTypography.caption)
                                    .foregroundStyle(AppColors.textSecondary)
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 10)
                            .background(AppColors.backgroundSoft)
                            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
                        }
                    }
                }

                SecondaryButton(title: "查看当天 \(focusedDayItems.count) 条记录", systemImage: "list.bullet.rectangle") {
                    Haptics.selection()
                    selectedDaySelection = HistoryDaySelection(date: focusedDate)
                }
            }
        }
        .padding(12)
        .background(AppColors.cardSecondary)
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                .stroke(AppColors.stroke, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }

    private var scopeSummaryCard: some View {
        let summary = makeScopeSummary()

        return DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(summary.title)
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text(summary.subtitle)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    scopeToggle
                }

                HStack(alignment: .top, spacing: 14) {
                    StatItem(value: "\(summary.averageScore)", label: "平均分")
                    StatItem(value: "\(summary.analysisCount)", label: "分析次数")
                    StatItem(value: "\(summary.stableDays)", label: "稳定日")
                    StatItem(value: "\(summary.attentionDays + summary.problemDays)", label: "待改日")
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text(summary.insight)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)

                    HStack(spacing: 8) {
                        if let changeText = summary.changeText {
                            TrainingFeedbackTag(text: changeText)
                        }

                        if let focusTitle = summary.focusTitle {
                            TrainingFeedbackTag(text: "当前重点 · \(focusTitle)")
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private var scopeToggle: some View {
        HStack(spacing: 8) {
            ForEach(HistoryReviewScope.allCases, id: \.self) { scope in
                Button {
                    guard reviewScope != scope else { return }
                    Haptics.selection()
                    withAnimation(.easeInOut(duration: 0.2)) {
                        reviewScope = scope
                    }
                } label: {
                    Text(scope.title)
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(reviewScope == scope ? AppColors.textPrimary : AppColors.textSecondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 7)
                        .background(reviewScope == scope ? AppColors.backgroundElevated : AppColors.backgroundSoft)
                        .overlay(
                            Capsule()
                                .stroke(reviewScope == scope ? AppColors.strongStroke : AppColors.stroke, lineWidth: 1)
                        )
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var calendarCells: [HistoryCalendarCell] {
        let monthStart = calendar.startOfMonth(for: displayedMonth)
        let daysInMonth = calendar.range(of: .day, in: .month, for: monthStart)?.count ?? 0
        guard daysInMonth > 0 else { return [] }

        let leadingCount = leadingBlankCount(for: monthStart)
        let totalSlots = leadingCount + daysInMonth
        let totalCells = Int(ceil(Double(totalSlots) / 7.0)) * 7

        return (0..<totalCells).compactMap { index in
            let dayOffset = index - leadingCount

            guard dayOffset >= 0, dayOffset < daysInMonth,
                  let date = calendar.date(byAdding: .day, value: dayOffset, to: monthStart) else {
                return HistoryCalendarCell(
                    id: "empty-\(index)",
                    date: nil,
                    dayNumber: nil,
                    items: [],
                    isSelected: false,
                    isInCurrentMonth: false
                )
            }

            let dayStart = calendar.startOfDay(for: date)
            let items = groupedHistory[dayStart] ?? []

            return HistoryCalendarCell(
                id: Self.dayKey(for: date),
                date: date,
                dayNumber: calendar.component(.day, from: date),
                items: items,
                isSelected: calendar.isDate(date, inSameDayAs: focusedDate),
                isInCurrentMonth: calendar.isDate(date, equalTo: monthStart, toGranularity: .month)
            )
        }
    }

    private func selectCell(_ cell: HistoryCalendarCell) {
        guard let date = cell.date else { return }

        focusedDate = date

        Haptics.light()
    }

    private func shiftMonth(by offset: Int) {
        guard let nextMonth = calendar.date(byAdding: .month, value: offset, to: displayedMonth) else {
            return
        }

        Haptics.light()
        withAnimation(.easeInOut(duration: 0.2)) {
            displayedMonth = calendar.startOfMonth(for: nextMonth)
            focusedDate = displayedMonth
        }
    }

    private func seedInitialDateIfNeeded(force: Bool = false) {
        guard !didSeedInitialDate || force else { return }

        let anchor = historyItems.first?.date ?? Date()
        displayedMonth = calendar.startOfMonth(for: anchor)
        focusedDate = anchor
        didSeedInitialDate = true
    }

    private func makeScopeSummary() -> HistoryScopeSummary {
        let records = recordsForCurrentScope()
        let currentAverageScore = averageScore(for: records)
        let previousRecords = recordsForPreviousScope()
        let previousAverage = averageScore(for: previousRecords)
        let change = currentAverageScore - previousAverage

        let stableDays = records.filter { $0.reviewTone == .stable }.count
        let attentionDays = records.filter { $0.reviewTone == .attention }.count
        let problemDays = records.filter { $0.reviewTone == .problem }.count
        let referenceDays = records.filter { $0.reviewTone == .reference }.count
        let focusTitle = mostFrequentPriorityFocus(in: records)

        let subtitle = records.isEmpty
            ? "当前区间还没有记录，先去分析页上传视频后，这里会自动沉淀复盘。"
            : "\(periodLabel()) 内共 \(records.count) 次分析，自动保存后会继续累积在这里。"

        let insight: String
        if records.isEmpty {
            insight = "这一段还没有训练记录，先开始一次分析，后面就能按周和按月继续对比。"
        } else if problemDays > attentionDays {
            insight = "最近更适合先把「\(focusTitle ?? "当前重点")」这类动作点压下去，再去追求更高分。"
        } else if stableDays >= attentionDays + problemDays {
            insight = "整体状态比较稳，可以继续保持当前节奏，围绕「\(focusTitle ?? "当前重点")」继续打磨。"
        } else {
            insight = "目前有稳定项，也有待改点，建议先抓「\(focusTitle ?? "当前重点")」这一类问题。"
        }

        let changeText: String?
        if previousAverage == 0 && previousRecords.isEmpty {
            changeText = "已沉淀到历史记录"
        } else if change > 0 {
            changeText = "比上期提升 \(change) 分"
        } else if change < 0 {
            changeText = "比上期下降 \(abs(change)) 分"
        } else {
            changeText = "与上期基本持平"
        }

        return HistoryScopeSummary(
            title: reviewScope.title,
            subtitle: subtitle,
            averageScore: currentAverageScore,
            analysisCount: records.count,
            stableDays: stableDays,
            attentionDays: attentionDays,
            problemDays: problemDays,
            referenceDays: referenceDays,
            changeText: changeText,
            insight: insight,
            focusTitle: focusTitle
        )
    }

    private func recordsForCurrentScope() -> [HistoryItem] {
        let interval = scopeInterval(for: reviewScope, around: focusedDate)
        return historyItems.filter { interval.contains($0.date) }
    }

    private func recordsForPreviousScope() -> [HistoryItem] {
        let previousDate: Date?
        switch reviewScope {
        case .week:
            previousDate = calendar.date(byAdding: .day, value: -7, to: focusedDate)
        case .month:
            previousDate = calendar.date(byAdding: .month, value: -1, to: focusedDate)
        }

        guard let previousDate else { return [] }
        let interval = scopeInterval(for: reviewScope, around: previousDate)
        return historyItems.filter { interval.contains($0.date) }
    }

    private func scopeInterval(for scope: HistoryReviewScope, around date: Date) -> DateInterval {
        switch scope {
        case .week:
            return calendar.dateInterval(of: .weekOfYear, for: date)
                ?? DateInterval(start: calendar.startOfDay(for: date), duration: 60 * 60 * 24 * 7)
        case .month:
            return calendar.dateInterval(of: .month, for: date)
                ?? DateInterval(start: calendar.startOfMonth(for: date), duration: 60 * 60 * 24 * 30)
        }
    }

    private func periodLabel() -> String {
        switch reviewScope {
        case .week:
            return "本周"
        case .month:
            return "本月"
        }
    }

    private func averageScore(for records: [HistoryItem]) -> Int {
        guard !records.isEmpty else { return 0 }
        return records.map(\.score).reduce(0, +) / records.count
    }

    private func mostFrequentPriorityFocus(in records: [HistoryItem]) -> String? {
        guard !records.isEmpty else { return nil }

        let grouped = Dictionary(grouping: records, by: { $0.priorityFocusTitle })
        return grouped.max(by: {
            if $0.value.count == $1.value.count {
                return $0.value.first?.date ?? .distantPast < $1.value.first?.date ?? .distantPast
            }
            return $0.value.count < $1.value.count
        })?.key
    }

    private func leadingBlankCount(for monthStart: Date) -> Int {
        let weekday = calendar.component(.weekday, from: monthStart)
        return (weekday - calendar.firstWeekday + 7) % 7
    }

    private func calendarButton(systemImage: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(AppColors.textPrimary)
                .frame(width: 32, height: 32)
                .background(AppColors.backgroundSoft)
                .overlay(
                    Circle()
                        .stroke(AppColors.stroke, lineWidth: 1)
                )
                .clipShape(Circle())
        }
        .buttonStyle(.plain)
    }

    private func legendPill(color: Color, text: String) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)

            Text(text)
        }
    }

    fileprivate static func dayKey(for date: Date) -> String {
        let day = Calendar.current.startOfDay(for: date)
        return String(day.timeIntervalSinceReferenceDate)
    }

    private static let monthFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "yyyy 年 M 月"
        return formatter
    }()

    private static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "M 月 d 日 EEEE"
        return formatter
    }()

    private static let weekdaySymbols: [String] = {
        let calendar = Calendar.current
        let symbols = calendar.shortStandaloneWeekdaySymbols
        let startIndex = max(calendar.firstWeekday - 1, 0)
        return Array(symbols[startIndex...] + symbols[..<startIndex])
    }()
}

private enum HistoryReviewScope: String, CaseIterable, Hashable {
    case week
    case month

    var title: String {
        switch self {
        case .week:
            return "周复盘"
        case .month:
            return "月复盘"
        }
    }
}

private enum HistoryReviewTone: Int, CaseIterable, Hashable {
    case stable = 0
    case reference = 1
    case attention = 2
    case problem = 3

    var displayLabel: String {
        switch self {
        case .stable:
            return "整体稳定"
        case .attention:
            return "有待改点"
        case .problem:
            return "明显问题"
        case .reference:
            return "低置信"
        }
    }

    var color: Color {
        switch self {
        case .stable:
            return AppColors.positive
        case .attention:
            return AppColors.warning
        case .problem:
            return AppColors.critical
        case .reference:
            return AppColors.reference
        }
    }

    var summaryOrder: Int {
        rawValue
    }
}

private struct HistoryScopeSummary {
    let title: String
    let subtitle: String
    let averageScore: Int
    let analysisCount: Int
    let stableDays: Int
    let attentionDays: Int
    let problemDays: Int
    let referenceDays: Int
    let changeText: String?
    let insight: String
    let focusTitle: String?
}

private struct HistoryDaySelection: Identifiable, Hashable {
    let date: Date

    var id: String {
        HistoryView.dayKey(for: date)
    }
}

private struct HistoryCalendarCell: Identifiable {
    let id: String
    let date: Date?
    let dayNumber: Int?
    let items: [HistoryItem]
    let isSelected: Bool
    let isInCurrentMonth: Bool

    var toneSegments: [HistoryReviewTone] {
        Array(items.prefix(4).map(\.reviewTone))
    }
}

private struct HistoryCalendarDayCell: View {
    let cell: HistoryCalendarCell
    let onTap: () -> Void

    var body: some View {
        Button {
            onTap()
        } label: {
            VStack(spacing: 6) {
                Text(cell.dayNumber.map(String.init) ?? "")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(textColor)
                    .frame(height: 16)

                dotRow
            }
            .frame(maxWidth: .infinity)
            .frame(minHeight: 62)
            .padding(.vertical, 8)
            .background(backgroundColor)
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous)
                    .stroke(borderColor, lineWidth: cell.isSelected ? 1.4 : 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(cell.date == nil)
        .opacity(cell.date == nil ? 0.08 : 1)
    }

    private var dotRow: some View {
        VStack(spacing: 4) {
            if cell.items.isEmpty {
                Capsule()
                    .fill(Color.clear)
                    .frame(width: 28, height: 4)
            } else {
                HStack(spacing: 2) {
                    ForEach(Array(cell.toneSegments.enumerated()), id: \.offset) { _, tone in
                        Capsule()
                            .fill(tone.color)
                            .frame(width: cell.items.count == 1 ? 22 : 10, height: 4)
                    }
                }

                if cell.items.count > 1 {
                    Text("\(cell.items.count)次")
                        .font(.system(size: 9, weight: .semibold))
                        .foregroundStyle(AppColors.textPrimary)
                        .padding(.horizontal, 5)
                        .padding(.vertical, 2)
                        .background(AppColors.backgroundSoft)
                        .clipShape(Capsule())
                }
            }
        }
        .frame(height: 22)
    }

    private var textColor: Color {
        guard cell.date != nil else { return AppColors.textTertiary }
        return cell.items.isEmpty ? AppColors.textSecondary : AppColors.textPrimary
    }

    private var backgroundColor: Color {
        if cell.isSelected {
            return AppColors.backgroundElevated
        }

        if cell.items.isEmpty {
            return AppColors.backgroundSoft.opacity(0.55)
        }

        return AppColors.cardSecondary
    }

    private var borderColor: Color {
        if cell.isSelected {
            return AppColors.strongStroke
        }

        if cell.items.isEmpty {
            return AppColors.stroke.opacity(0.7)
        }

        return AppColors.stroke
    }
}

private struct HistoryDayBucket {
    let date: Date
    let items: [HistoryItem]

    var dayTitle: String {
        Self.dayFormatter.string(from: date)
    }

    var summaryText: String {
        if items.isEmpty {
            return "当天没有分析记录。"
        }

        if items.count == 1 {
            return "这条记录已经自动保存在历史里，之后可以直接对比。"
        }

        return "当天有 \(items.count) 条记录，方便你比较不同尝试。"
    }

    var averageScore: Int {
        guard !items.isEmpty else { return 0 }
        return items.map(\.score).reduce(0, +) / items.count
    }

    var reviewTone: HistoryReviewTone {
        items.map(\.reviewTone).max { $0.summaryOrder < $1.summaryOrder } ?? .reference
    }

    var focusTitle: String {
        items.first?.priorityFocusTitle ?? "继续观察动作节奏"
    }

    private static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "M 月 d 日"
        return formatter
    }()
}

private struct HistoryDayRecordsSheet: View {
    @EnvironmentObject private var sessionManager: SessionManager
    @Environment(\.dismiss) private var dismiss
    let selection: HistoryDaySelection

    @State private var selectedHistoryItem: HistoryItem?
    @State private var editingNoteItem: HistoryItem?

    private var calendar: Calendar { .current }

    private var bucket: HistoryDayBucket {
        let dayItems = sessionManager.historyItems
            .filter { calendar.isDate($0.date, inSameDayAs: selection.date) }
            .sorted { $0.date > $1.date }

        return HistoryDayBucket(date: selection.date, items: dayItems)
    }

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                    bucketSummaryCard

                    if bucket.items.isEmpty {
                        EmptyStateView(
                            title: "这一天还没有记录",
                            subtitle: "你可以继续切回日历，选择有记录的日期查看完整复盘。",
                            systemImage: "calendar.badge.exclamationmark"
                        )
                    } else {
                        VStack(spacing: 12) {
                            ForEach(bucket.items) { item in
                                HistoryDayRecordRow(
                                    item: item,
                                    onOpen: {
                                        selectedHistoryItem = item
                                    },
                                    onToggleFavorite: {
                                        sessionManager.toggleFavorite(for: item.id)
                                    },
                                    onEditNote: {
                                        editingNoteItem = item
                                    },
                                    onDelete: {
                                        sessionManager.deleteHistoryItem(id: item.id)
                                        if selectedHistoryItem?.id == item.id {
                                            selectedHistoryItem = nil
                                        }
                                    }
                                )
                            }
                        }
                    }
                }
                .padding(.horizontal, AppSpacing.screenPadding)
                .padding(.top, 12)
                .padding(.bottom, 28)
            }
            .background(AppColors.background)
            .navigationTitle(bucket.dayTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("关闭") {
                        dismiss()
                    }
                    .foregroundStyle(AppColors.textPrimary)
                }
            }
            .navigationDestination(item: $selectedHistoryItem) { item in
                ResultView(
                    result: item.result,
                    source: .history,
                    videoURL: item.videoURL,
                    videoLabel: item.videoFileName,
                    professionalAccessOverride: sessionManager.hasProAccess || item.professionalAccessGranted == true
                )
            }
            .sheet(item: $editingNoteItem) { item in
                HistoryNoteEditor(item: item) { note in
                    sessionManager.updateNote(for: item.id, note: note)
                }
            }
            .onChange(of: sessionManager.historyItems) { _, _ in
                if bucket.items.isEmpty {
                    dismiss()
                }
            }
        }
    }

    private var bucketSummaryCard: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(bucket.dayTitle)
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        Text(bucket.summaryText)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    TrainingFeedbackTag(text: bucket.reviewTone.displayLabel)
                }

                HStack(alignment: .top, spacing: 14) {
                    StatItem(value: "\(bucket.averageScore)", label: "平均分")
                    StatItem(value: "\(bucket.items.count)", label: "记录数")
                    StatItem(value: bucket.focusTitle, label: "当天重点")
                }
            }
        }
    }
}

private struct HistoryDayRecordRow: View {
    let item: HistoryItem
    let onOpen: () -> Void
    let onToggleFavorite: () -> Void
    let onEditNote: () -> Void
    let onDelete: () -> Void

    var body: some View {
        DarkCard {
            ZStack(alignment: .topTrailing) {
                Button(action: onOpen) {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack(alignment: .top, spacing: 10) {
                            Circle()
                                .fill(item.reviewTone.color)
                                .frame(width: 10, height: 10)
                                .padding(.top, 5)

                            VStack(alignment: .leading, spacing: 6) {
                                HStack(alignment: .top, spacing: 8) {
                                    Text(item.formattedTimeText)
                                        .font(AppTypography.captionMedium)
                                        .foregroundStyle(AppColors.textSecondary)

                                    Spacer(minLength: 0)

                                    Text("总分 \(item.score)")
                                        .font(AppTypography.captionMedium)
                                        .foregroundStyle(AppColors.textPrimary)
                                }

                                Text(item.motionType)
                                    .font(AppTypography.cardTitle)
                                    .foregroundStyle(AppColors.textPrimary)
                                    .fixedSize(horizontal: false, vertical: true)

                                Text("优先改 1 点：\(item.priorityFocusTitle)")
                                    .font(AppTypography.body)
                                    .foregroundStyle(AppColors.textSecondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }

                            VStack(alignment: .trailing, spacing: 6) {
                                Text("详情")
                                    .font(AppTypography.captionMedium)
                                    .foregroundStyle(AppColors.textSecondary)

                                Image(systemName: "chevron.right")
                                    .font(.system(size: 11, weight: .semibold))
                                    .foregroundStyle(AppColors.textTertiary)
                            }
                        }
                    }
                    .padding(.trailing, 52)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)

                Menu {
                    Button(item.isFavorite ? "取消收藏" : "收藏") {
                        onToggleFavorite()
                    }

                    Button("添加备注") {
                        onEditNote()
                    }

                    Button(role: .destructive) {
                        onDelete()
                    } label: {
                        Text("删除记录")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(item.isFavorite ? AppColors.accent : AppColors.textSecondary)
                        .frame(width: 28, height: 28)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

private struct HistoryNoteEditor: View {
    let item: HistoryItem
    let onSave: (String?) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var noteText: String

    init(item: HistoryItem, onSave: @escaping (String?) -> Void) {
        self.item = item
        self.onSave = onSave
        _noteText = State(initialValue: item.note ?? "")
    }

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                    DarkCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("为这次分析写一句备注")
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)

                            Text(item.motionType)
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)

                            Text(item.summary)
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    DarkCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("备注内容")
                                .font(AppTypography.captionMedium)
                                .foregroundStyle(AppColors.textSecondary)

                            TextEditor(text: $noteText)
                                .frame(minHeight: 180)
                                .scrollContentBackground(.hidden)
                                .padding(10)
                                .background(AppColors.backgroundSoft)
                                .overlay(
                                    RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                                        .stroke(AppColors.stroke, lineWidth: 1)
                                )
                                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))

                            Text("可以记录拍摄角度、当天重点、下次训练想验证的点。")
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                    }
                }
                .padding(.horizontal, AppSpacing.screenPadding)
                .padding(.top, 12)
                .padding(.bottom, 28)
            }
            .kickScreenBackground()
            .navigationTitle("添加备注")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") {
                        dismiss()
                    }
                    .foregroundStyle(AppColors.textPrimary)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("保存") {
                        let trimmed = noteText.trimmingCharacters(in: .whitespacesAndNewlines)
                        onSave(trimmed.isEmpty ? nil : trimmed)
                        dismiss()
                    }
                    .foregroundStyle(AppColors.textPrimary)
                }
            }
        }
    }
}

private extension HistoryItem {
    var reviewTone: HistoryReviewTone {
        let statuses = metricSnapshots.map(\.status)
        let hasNeedsWork = statuses.contains(.needsWork)
        let referenceCount = statuses.filter { $0 == .reference }.count
        let goodCount = statuses.filter { $0 == .good || $0 == .excellent }.count

        if hasNeedsWork {
            return score < 70 || statuses.filter { $0 == .needsWork }.count >= 2 ? .problem : .attention
        }

        if referenceCount >= max(2, (statuses.count / 2) + 1) {
            return .reference
        }

        if score >= 85 || goodCount >= max(1, statuses.count - 1) {
            return .stable
        }

        return .attention
    }

    var formattedTimeText: String {
        Self.timeFormatter.string(from: date)
    }

    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "HH:mm"
        return formatter
    }()
}

private extension Calendar {
    func startOfMonth(for date: Date) -> Date {
        let components = dateComponents([.year, .month], from: date)
        return self.date(from: components) ?? startOfDay(for: date)
    }
}
