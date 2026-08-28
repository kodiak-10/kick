import Combine
import CoreLocation
import MapKit
import SwiftUI

struct DiscoverView: View {
    @StateObject private var viewModel = DiscoverViewModel()
    @StateObject private var locationProvider = DiscoverLocationProvider()
    @State private var selectedSegment: DiscoverSegment = .community
    @State private var selectedRegion = "实时定位"
    @State private var regionMode: DiscoverRegionMode = .currentLocation
    @State private var activeSheet: DiscoverActiveSheet?

    private var activeCoordinate: DiscoverCoordinate? {
        regionMode == .currentLocation ? locationProvider.coordinate : nil
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: AppSpacing.sectionGap) {
                header
                heroCard
                regionSelector
                segmentControl

                if let message = viewModel.statusMessage {
                    DiscoverInlineStatusCard(message: message)
                }

                switch selectedSegment {
                case .community:
                    communityContent
                case .venues:
                    venuesContent
                case .coaches:
                    coachesContent
                }
            }
            .padding(.horizontal, AppSpacing.screenPadding)
            .padding(.top, 12)
            .padding(.bottom, 36)
        }
        .kickScreenBackground()
        .toolbar(.hidden, for: .navigationBar)
        .task {
            locationProvider.requestCurrentLocation()
            let region = resolvedRegionTitle
            await viewModel.load(region: region, coordinate: activeCoordinate)
        }
        .refreshable {
            await viewModel.refresh(region: resolvedRegionTitle, coordinate: activeCoordinate)
        }
        .onReceive(locationProvider.$regionTitle.removeDuplicates()) { region in
            guard regionMode == .currentLocation else { return }
            guard selectedRegion != region else { return }
            selectedRegion = region
            Task {
                await viewModel.refresh(region: region, coordinate: locationProvider.coordinate)
            }
        }
        .onReceive(locationProvider.$coordinate.compactMap { $0 }) { coordinate in
            guard regionMode == .currentLocation else { return }
            Task {
                await viewModel.refresh(region: resolvedRegionTitle, coordinate: coordinate)
            }
        }
        .sheet(item: $activeSheet) { sheet in
            switch sheet {
            case .regionPicker:
                DiscoverRegionPickerView(
                    selectedRegion: selectedRegion,
                    mode: regionMode,
                    currentLocationTitle: locationProvider.regionTitle,
                    currentLocationStatus: locationProvider.statusTitle
                ) { mode, region in
                    regionMode = mode
                    selectedRegion = region
                    activeSheet = nil
                    if mode == .currentLocation {
                        locationProvider.requestCurrentLocation()
                    }
                    Task {
                        await viewModel.refresh(region: resolvedRegionTitle, coordinate: activeCoordinate)
                    }
                }
            case let .postComposer(post):
                DiscoverPostComposerView(post: post, region: resolvedRegionTitle) { title, body, badge, visibility in
                    Task {
                        if let post {
                            await viewModel.updatePost(
                                post,
                                title: title,
                                body: body,
                                badge: badge,
                                visibility: visibility
                            )
                        } else {
                            await viewModel.createPost(
                                title: title,
                                body: body,
                                badge: badge,
                                visibility: visibility,
                                region: resolvedRegionTitle
                            )
                        }
                        activeSheet = nil
                    }
                }
            case let .postDetail(post):
                DiscoverPostDetailView(
                    post: post,
                    onLike: { Task { await viewModel.like(post: post) } },
                    onEdit: { activeSheet = .postComposer(post) },
                    onUserTap: { activeSheet = .userProfile(post) }
                )
            case let .userProfile(post):
                DiscoverUserProfileView(authorPost: post)
            case let .venueDetail(venue):
                DiscoverVenueDetailView(venue: venue)
            case let .coachChat(coach):
                DiscoverCoachChatView(coach: coach, region: resolvedRegionTitle)
            }
        }
    }

    private var resolvedRegionTitle: String {
        if regionMode == .currentLocation {
            return locationProvider.regionTitle
        }
        return selectedRegion
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("发现")
                .font(AppTypography.pageTitle)
                .foregroundStyle(AppColors.textPrimary)

            Text("按你的位置或手动城市发现球友、球场和私教。")
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)
        }
    }

    private var heroCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top, spacing: 14) {
                ZStack {
                    Circle()
                        .fill(AppColors.pitchGreen.opacity(0.16))
                        .frame(width: 58, height: 58)

                    Image(systemName: "sparkles")
                        .font(.system(size: 24, weight: .bold))
                        .foregroundStyle(AppColors.pitchGreen)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("发现已接入后端")
                        .font(AppTypography.sectionTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("发帖、球场 POI、私教预约走 `/discovery`；你可以用实时定位，也可以手动切换全国城市。")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            HStack(spacing: 10) {
                DiscoverHeroPill(title: "后端 \(viewModel.backendStateTitle)", icon: viewModel.backendStateIcon)
                DiscoverHeroPill(title: viewModel.venueProviderTitle, icon: "mappin.and.ellipse")
                DiscoverHeroPill(title: regionMode.title, icon: regionMode.iconName)
            }
        }
        .padding(20)
        .background(
            LinearGradient(
                colors: [
                    AppColors.pitchGreen.opacity(0.18),
                    AppColors.matchBlue.opacity(0.10),
                    AppColors.card
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                .stroke(AppColors.pitchGreen.opacity(0.24), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
        .shadow(color: AppShadows.card, radius: 20, x: 0, y: 10)
    }

    private var regionSelector: some View {
        Button {
            activeSheet = .regionPicker
        } label: {
            HStack(spacing: 12) {
                Image(systemName: regionMode.iconName)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(AppColors.pitchGreen)
                    .frame(width: 38, height: 38)
                    .background(AppColors.pitchGreen.opacity(0.14))
                    .clipShape(Circle())

                VStack(alignment: .leading, spacing: 3) {
                    Text(regionMode == .currentLocation ? "当前位置" : "手动城市")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)
                    Text(resolvedRegionTitle)
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textPrimary)
                }

                Spacer()

                Text("切换")
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.accent)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(AppColors.backgroundSoft)
                    .clipShape(Capsule())
            }
            .padding(14)
            .background(AppColors.card)
            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private var segmentControl: some View {
        HStack(spacing: 10) {
            ForEach(DiscoverSegment.allCases, id: \.self) { segment in
                Button {
                    withAnimation(.spring(response: 0.28, dampingFraction: 0.88)) {
                        selectedSegment = segment
                    }
                } label: {
                    Text(segment.title)
                        .font(AppTypography.headline)
                        .foregroundStyle(selectedSegment == segment ? AppColors.onAccent : AppColors.textSecondary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(selectedSegment == segment ? AppColors.accent : AppColors.backgroundSoft)
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var communityContent: some View {
        VStack(alignment: .leading, spacing: AppSpacing.itemGap) {
            HStack(alignment: .top) {
                DiscoverSectionHeader(
                    title: "球友圈",
                    subtitle: "发帖、点赞已接入后端本地存储。"
                )

                Spacer()

                DiscoverSmallButton(title: "发帖", icon: "square.and.pencil") {
                    activeSheet = .postComposer(nil)
                }
            }

            if viewModel.isLoading && viewModel.posts.isEmpty {
                DiscoverLoadingCard(title: "正在加载球友圈")
            } else if viewModel.posts.isEmpty {
                DiscoverEmptyCard(title: "暂无帖子", subtitle: "先发一条同城训练讨论，后端会保存到本地 JSON。")
            } else {
                ForEach(viewModel.posts) { post in
                    DiscoverPostCard(
                        post: post,
                        onOpen: { activeSheet = .postDetail(post) },
                        onUserTap: { activeSheet = .userProfile(post) },
                        onLike: { Task { await viewModel.like(post: post) } }
                    )
                }
            }

            DiscoverActionCard(
                title: "帖子现在可编辑和控制可见范围",
                subtitle: "公开、互相关注可见、仅自己看已经写入后端字段；后续接账号体系后就能做真正关注关系校验。",
                icon: "calendar.badge.plus",
                actionTitle: "已接入"
            )
        }
    }

    private var venuesContent: some View {
        VStack(alignment: .leading, spacing: AppSpacing.itemGap) {
            HStack(alignment: .top) {
                DiscoverSectionHeader(
                    title: "发现球场",
                    subtitle: "从地图 POI 动态拉取，用户纠错负责补全草皮、灯光、价格。"
                )

                Spacer()

                DiscoverSmallButton(title: "刷新", icon: "arrow.clockwise") {
                    Task { await viewModel.refreshVenues(region: resolvedRegionTitle, coordinate: activeCoordinate) }
                }
            }

            if viewModel.venueSearchReady == false {
                DiscoverActionCard(
                    title: "地图 Key 待配置",
                    subtitle: viewModel.venueSetupHint,
                    icon: "key.horizontal",
                    actionTitle: "后端可用"
                )
            }

            if viewModel.isLoading && viewModel.venues.isEmpty {
                DiscoverLoadingCard(title: "正在搜索附近球场")
            } else if viewModel.venues.isEmpty {
                DiscoverEmptyCard(
                    title: "暂未拉到真实球场",
                    subtitle: "当前区域：\(resolvedRegionTitle)。你可以切换城市，或打开定位后搜附近球场。"
                )
            } else {
                ForEach(viewModel.venues) { venue in
                    DiscoverVenueCard(venue: venue) {
                        activeSheet = .venueDetail(venue)
                    }
                }
            }

            DiscoverReliabilityCard(providerSummary: viewModel.providerSummary)
        }
    }

    private var coachesContent: some View {
        VStack(alignment: .leading, spacing: AppSpacing.itemGap) {
            DiscoverSectionHeader(
                title: "私教一对一",
                subtitle: "教练列表和预约已接入后端，后续可接支付与教练后台。"
            )

            if viewModel.isLoading && viewModel.coaches.isEmpty {
                DiscoverLoadingCard(title: "正在加载私教")
            } else if viewModel.coaches.isEmpty {
                DiscoverEmptyCard(title: "暂无教练", subtitle: "后端 coaches 为空，可在数据文件或后台补充教练。")
            } else {
                ForEach(viewModel.coaches) { coach in
                    DiscoverCoachCard(coach: coach) {
                        activeSheet = .coachChat(coach)
                    }
                }
            }

            DiscoverActionCard(
                title: "商业化建议先做撮合",
                subtitle: "用户带分析报告预约，教练按问题点报价；平台负责沟通、评价和退款规则，先降低重服务成本。",
                icon: "creditcard.and.123",
                actionTitle: "预约已接"
            )
        }
    }
}

private enum DiscoverSegment: String, CaseIterable {
    case community
    case venues
    case coaches

    var title: String {
        switch self {
        case .community:
            return "球友圈"
        case .venues:
            return "球场"
        case .coaches:
            return "私教"
        }
    }
}

private enum DiscoverRegionMode {
    case currentLocation
    case manual

    var title: String {
        switch self {
        case .currentLocation:
            return "实时定位"
        case .manual:
            return "手动城市"
        }
    }

    var iconName: String {
        switch self {
        case .currentLocation:
            return "location.fill"
        case .manual:
            return "map"
        }
    }
}

private enum DiscoverActiveSheet: Identifiable {
    case regionPicker
    case postComposer(DiscoverCommunityPost?)
    case postDetail(DiscoverCommunityPost)
    case userProfile(DiscoverCommunityPost)
    case venueDetail(DiscoverVenue)
    case coachChat(DiscoverCoachListing)

    var id: String {
        switch self {
        case .regionPicker:
            return "region-picker"
        case let .postComposer(post):
            return post.map { "post-edit-\($0.id)" } ?? "post-compose"
        case let .postDetail(post):
            return "post-detail-\(post.id)"
        case let .userProfile(post):
            return "user-profile-\(post.userID)"
        case let .venueDetail(venue):
            return "venue-detail-\(venue.id)"
        case let .coachChat(coach):
            return "coach-chat-\(coach.id)"
        }
    }
}

private struct DiscoverCoordinate: Equatable {
    let latitude: Double
    let longitude: Double
}

private struct DiscoverRegionPickerView: View {
    let selectedRegion: String
    let mode: DiscoverRegionMode
    let currentLocationTitle: String
    let currentLocationStatus: String
    let onSelect: (DiscoverRegionMode, String) -> Void

    @State private var manualCity = ""
    @State private var manualDistrict = ""

    private let quickRegions = [
        "重庆 · 沙坪坝",
        "重庆 · 渝北",
        "成都 · 武侯",
        "北京 · 朝阳",
        "上海 · 浦东新区",
        "广州 · 天河",
        "深圳 · 南山",
        "杭州 · 西湖",
        "武汉 · 洪山",
        "西安 · 雁塔",
        "南京 · 建邺",
        "长沙 · 岳麓"
    ]

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 18) {
                    Button {
                        onSelect(.currentLocation, currentLocationTitle)
                    } label: {
                        HStack(spacing: 14) {
                            Image(systemName: "location.fill")
                                .font(.system(size: 20, weight: .bold))
                                .foregroundStyle(AppColors.pitchGreen)
                                .frame(width: 44, height: 44)
                                .background(AppColors.pitchGreen.opacity(0.14))
                                .clipShape(Circle())

                            VStack(alignment: .leading, spacing: 4) {
                                Text("使用实时位置")
                                    .font(AppTypography.cardTitle)
                                    .foregroundStyle(AppColors.textPrimary)
                                Text("\(currentLocationTitle) · \(currentLocationStatus)")
                                    .font(AppTypography.body)
                                    .foregroundStyle(AppColors.textSecondary)
                            }

                            Spacer()

                            if mode == .currentLocation {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(AppColors.pitchGreen)
                            }
                        }
                        .padding(16)
                        .background(AppColors.card)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
                    }
                    .buttonStyle(.plain)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("手动选择城市")
                            .font(AppTypography.sectionTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        HStack(spacing: 10) {
                            TextField("城市，例如 北京 / 成都 / 广州", text: $manualCity)
                                .textInputAutocapitalization(.never)
                                .padding(12)
                                .background(AppColors.card)
                                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))

                            TextField("区县，可选", text: $manualDistrict)
                                .textInputAutocapitalization(.never)
                                .padding(12)
                                .background(AppColors.card)
                                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
                        }

                        Button {
                            let city = manualCity.trimmingCharacters(in: .whitespacesAndNewlines)
                            let district = manualDistrict.trimmingCharacters(in: .whitespacesAndNewlines)
                            guard !city.isEmpty else { return }
                            let region = district.isEmpty ? city : "\(city) · \(district)"
                            onSelect(.manual, region)
                        } label: {
                            Label("搜索这个城市的球场", systemImage: "magnifyingglass")
                                .font(AppTypography.headline)
                                .foregroundStyle(AppColors.onAccent)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(manualCity.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? AppColors.textTertiary : AppColors.accent)
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("热门城市")
                            .font(AppTypography.sectionTitle)
                            .foregroundStyle(AppColors.textPrimary)

                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            ForEach(quickRegions, id: \.self) { region in
                                Button {
                                    onSelect(.manual, region)
                                } label: {
                                    HStack {
                                        Text(region)
                                            .font(AppTypography.bodyMedium)
                                            .foregroundStyle(AppColors.textPrimary)
                                        Spacer()
                                        if selectedRegion == region && mode == .manual {
                                            Image(systemName: "checkmark")
                                                .foregroundStyle(AppColors.pitchGreen)
                                        }
                                    }
                                    .padding(13)
                                    .background(AppColors.card)
                                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
                .padding(20)
            }
            .kickScreenBackground()
            .navigationTitle("选择位置")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }
}

private struct DiscoverPostComposerView: View {
    let post: DiscoverCommunityPost?
    let region: String
    let onSubmit: (String, String, String, DiscoverPostVisibility) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var title: String
    @State private var bodyText: String
    @State private var badge: String
    @State private var visibility: DiscoverPostVisibility

    init(
        post: DiscoverCommunityPost?,
        region: String,
        onSubmit: @escaping (String, String, String, DiscoverPostVisibility) -> Void
    ) {
        self.post = post
        self.region = region
        self.onSubmit = onSubmit
        _title = State(initialValue: post?.title ?? "")
        _bodyText = State(initialValue: post?.body ?? "")
        _badge = State(initialValue: post?.badge ?? "同城约练")
        _visibility = State(initialValue: post?.visibility ?? .public)
    }

    private var canSubmit: Bool {
        !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !bodyText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("发布到 \(region)")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)

                    TextField("标题，例如 今晚约练传球", text: $title)
                        .font(AppTypography.cardTitle)
                        .padding(14)
                        .background(AppColors.card)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))

                    TextField("标签，例如 同城约练 / 射门纠错", text: $badge)
                        .font(AppTypography.body)
                        .padding(14)
                        .background(AppColors.card)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("内容")
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textPrimary)

                    TextEditor(text: $bodyText)
                        .font(AppTypography.body)
                        .frame(minHeight: 150)
                        .padding(10)
                        .scrollContentBackground(.hidden)
                        .background(AppColors.card)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("谁可以看")
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textPrimary)

                    Picker("可见范围", selection: $visibility) {
                        ForEach(DiscoverPostVisibility.allCases, id: \.rawValue) { option in
                            Label(option.title, systemImage: option.iconName)
                                .tag(option)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                Spacer()

                Button {
                    guard canSubmit else { return }
                    onSubmit(
                        title.trimmingCharacters(in: .whitespacesAndNewlines),
                        bodyText.trimmingCharacters(in: .whitespacesAndNewlines),
                        badge.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "训练讨论" : badge.trimmingCharacters(in: .whitespacesAndNewlines),
                        visibility
                    )
                    dismiss()
                } label: {
                    Text(post == nil ? "发布" : "保存修改")
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.onAccent)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 15)
                        .background(canSubmit ? AppColors.accent : AppColors.textTertiary)
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
            .padding(20)
            .kickScreenBackground()
            .navigationTitle(post == nil ? "发帖" : "编辑帖子")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("关闭") { dismiss() }
                }
            }
        }
        .presentationDetents([.large])
    }
}

private struct DiscoverPostDetailView: View {
    let post: DiscoverCommunityPost
    let onLike: () -> Void
    let onEdit: () -> Void
    let onUserTap: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 18) {
                    Button(action: onUserTap) {
                        HStack(spacing: 12) {
                            Circle()
                                .fill(AppColors.accent.opacity(0.14))
                                .frame(width: 50, height: 50)
                                .overlay(
                                    Image(systemName: "figure.soccer")
                                        .foregroundStyle(AppColors.accent)
                                )

                            VStack(alignment: .leading, spacing: 4) {
                                Text(post.userName)
                                    .font(AppTypography.cardTitle)
                                    .foregroundStyle(AppColors.textPrimary)
                                Text("\(post.region) · \(post.badge)")
                                    .font(AppTypography.body)
                                    .foregroundStyle(AppColors.textSecondary)
                            }

                            Spacer()
                            Image(systemName: "chevron.right")
                                .foregroundStyle(AppColors.textTertiary)
                        }
                    }
                    .buttonStyle(.plain)

                    HStack(spacing: 8) {
                        DiscoverSourceBadge(post.visibility.title)
                        if post.isOwnedByCurrentUser {
                            DiscoverSourceBadge("我发布的")
                        }
                    }

                    Text(post.title)
                        .font(AppTypography.pageTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(post.body)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)

                    if let aiReply = post.aiReply {
                        Text(aiReply)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                            .padding(16)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(AppColors.card)
                            .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                    }

                    HStack(spacing: 12) {
                        Button(action: onLike) {
                            Label("\(post.likes)", systemImage: "heart")
                                .font(AppTypography.headline)
                                .foregroundStyle(AppColors.textPrimary)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 13)
                                .background(AppColors.card)
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)

                        if post.isOwnedByCurrentUser {
                            Button(action: onEdit) {
                                Label("编辑", systemImage: "square.and.pencil")
                                    .font(AppTypography.headline)
                                    .foregroundStyle(AppColors.onAccent)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 13)
                                    .background(AppColors.accent)
                                    .clipShape(Capsule())
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(20)
            }
            .kickScreenBackground()
            .navigationTitle("帖子详情")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }
}

private struct DiscoverUserProfileView: View {
    let authorPost: DiscoverCommunityPost

    @State private var posts: [DiscoverCommunityPost] = []
    @State private var isLoading = true
    @State private var errorText: String?
    private let service = DiscoverService()

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 18) {
                    HStack(spacing: 14) {
                        Circle()
                            .fill(AppColors.accent.opacity(0.14))
                            .frame(width: 64, height: 64)
                            .overlay(
                                Image(systemName: "figure.soccer")
                                    .font(.system(size: 27, weight: .semibold))
                                    .foregroundStyle(AppColors.accent)
                            )

                        VStack(alignment: .leading, spacing: 5) {
                            Text(authorPost.userName)
                                .font(AppTypography.sectionTitle)
                                .foregroundStyle(AppColors.textPrimary)
                            Text(authorPost.region)
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                    }

                    Text("发布内容")
                        .font(AppTypography.sectionTitle)
                        .foregroundStyle(AppColors.textPrimary)

                    if isLoading {
                        DiscoverLoadingCard(title: "正在加载发布内容")
                    } else if let errorText {
                        DiscoverInlineStatusCard(message: errorText)
                    } else if posts.isEmpty {
                        DiscoverEmptyCard(title: "暂无可查看内容", subtitle: "对方可能设置了仅自己或互相关注可见。")
                    } else {
                        ForEach(posts) { post in
                            DarkCard {
                                VStack(alignment: .leading, spacing: 10) {
                                    HStack {
                                        Text(post.badge)
                                            .font(AppTypography.captionMedium)
                                            .foregroundStyle(AppColors.energyGold)
                                        Spacer()
                                        DiscoverSourceBadge(post.visibility.shortTitle)
                                    }
                                    Text(post.title)
                                        .font(AppTypography.cardTitle)
                                        .foregroundStyle(AppColors.textPrimary)
                                    Text(post.body)
                                        .font(AppTypography.body)
                                        .foregroundStyle(AppColors.textSecondary)
                                        .lineLimit(3)
                                }
                            }
                        }
                    }
                }
                .padding(20)
            }
            .kickScreenBackground()
            .navigationTitle("个人主页")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                await loadPosts()
            }
        }
        .presentationDetents([.medium, .large])
    }

    private func loadPosts() async {
        isLoading = true
        defer { isLoading = false }
        do {
            posts = try await service.fetchUserPosts(userID: authorPost.userID)
        } catch {
            errorText = "用户内容加载失败：\(error.localizedDescription)"
        }
    }
}

private enum DiscoverVenueMapMode: String, CaseIterable {
    case twoD
    case threeD

    var title: String {
        switch self {
        case .twoD:
            return "2D"
        case .threeD:
            return "3D"
        }
    }
}

private struct DiscoverVenueDetailView: View {
    let venue: DiscoverVenue
    @State private var mapMode: DiscoverVenueMapMode = .twoD

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(venue.name)
                            .font(AppTypography.pageTitle)
                            .foregroundStyle(AppColors.textPrimary)
                        Text(venue.address)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Picker("地图模式", selection: $mapMode) {
                        ForEach(DiscoverVenueMapMode.allCases, id: \.rawValue) { mode in
                            Text(mode.title).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)

                    if let coordinate = venue.coordinate {
                        DiscoverVenueMapView(
                            coordinate: coordinate,
                            title: venue.name,
                            mode: mapMode
                        )
                        .frame(height: 300)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                                .stroke(AppColors.textPrimary.opacity(0.08), lineWidth: 1)
                        )

                        Button {
                            openInMaps(coordinate: coordinate)
                        } label: {
                            Label("打开地图导航", systemImage: "arrow.triangle.turn.up.right.diamond.fill")
                                .font(AppTypography.headline)
                                .foregroundStyle(AppColors.onAccent)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 15)
                                .background(AppColors.accent)
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    } else {
                        DiscoverEmptyCard(title: "暂无坐标", subtitle: "这个球场只有文字地址，暂时不能直接打开导航。")
                    }

                    DarkCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("球场信息")
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)
                            HStack(spacing: 8) {
                                DiscoverSourceBadge(venue.sourceLabel ?? "未知来源")
                                DiscoverSourceBadge(venue.reliabilityLabel ?? "待校验")
                            }
                            if let phone = venue.phone, !phone.isEmpty {
                                Text("电话：\(phone)")
                                    .font(AppTypography.body)
                                    .foregroundStyle(AppColors.textSecondary)
                            }
                            Text("2D/3D 展示来自系统地图。草皮、灯光、价格和预约需要后续接球场认证或用户纠错。")
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                    }
                }
                .padding(20)
            }
            .kickScreenBackground()
            .navigationTitle("球场位置")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.large])
    }

    private func openInMaps(coordinate: CLLocationCoordinate2D) {
        let placemark = MKPlacemark(coordinate: coordinate)
        let item = MKMapItem(placemark: placemark)
        item.name = venue.name
        item.openInMaps(launchOptions: [
            MKLaunchOptionsDirectionsModeKey: MKLaunchOptionsDirectionsModeDriving
        ])
    }
}

private struct DiscoverVenueMapView: UIViewRepresentable {
    let coordinate: CLLocationCoordinate2D
    let title: String
    let mode: DiscoverVenueMapMode

    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView(frame: .zero)
        mapView.isRotateEnabled = true
        mapView.isPitchEnabled = true
        mapView.showsCompass = true
        mapView.showsScale = true
        return mapView
    }

    func updateUIView(_ mapView: MKMapView, context: Context) {
        mapView.removeAnnotations(mapView.annotations)
        let annotation = MKPointAnnotation()
        annotation.coordinate = coordinate
        annotation.title = title
        mapView.addAnnotation(annotation)

        switch mode {
        case .twoD:
            mapView.mapType = .standard
            let region = MKCoordinateRegion(
                center: coordinate,
                latitudinalMeters: 1200,
                longitudinalMeters: 1200
            )
            mapView.setRegion(region, animated: true)
        case .threeD:
            mapView.mapType = .hybridFlyover
            let camera = MKMapCamera(
                lookingAtCenter: coordinate,
                fromDistance: 900,
                pitch: 58,
                heading: 20
            )
            mapView.setCamera(camera, animated: true)
        }
    }
}

private extension DiscoverVenue {
    var coordinate: CLLocationCoordinate2D? {
        guard let latitude, let longitude else { return nil }
        return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

private final class DiscoverLocationProvider: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var coordinate: DiscoverCoordinate?
    @Published var regionTitle = "实时定位"
    @Published var statusTitle = "定位待授权"

    private let manager = CLLocationManager()
    private let geocoder = CLGeocoder()

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        manager.distanceFilter = 300
    }

    func requestCurrentLocation() {
        switch manager.authorizationStatus {
        case .notDetermined:
            updateStatus("定位待授权")
            manager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            updateStatus("定位中")
            manager.requestLocation()
        case .denied, .restricted:
            updateStatus("定位未授权")
        @unknown default:
            updateStatus("定位不可用")
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        requestCurrentLocation()
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        let nextCoordinate = DiscoverCoordinate(
            latitude: location.coordinate.latitude,
            longitude: location.coordinate.longitude
        )
        DispatchQueue.main.async {
            self.coordinate = nextCoordinate
            self.statusTitle = "定位已开启"
        }
        reverseGeocode(location)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        updateStatus("定位失败")
    }

    private func reverseGeocode(_ location: CLLocation) {
        geocoder.reverseGeocodeLocation(location, preferredLocale: Locale(identifier: "zh_CN")) { [weak self] placemarks, _ in
            guard let self, let placemark = placemarks?.first else { return }
            let city = placemark.locality ?? placemark.administrativeArea
            let district = placemark.subLocality
            let region = [city, district]
                .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
                .joined(separator: " · ")
            guard !region.isEmpty else { return }
            DispatchQueue.main.async {
                self.regionTitle = region
            }
        }
    }

    private func updateStatus(_ title: String) {
        DispatchQueue.main.async {
            self.statusTitle = title
        }
    }
}

@MainActor
private final class DiscoverViewModel: ObservableObject {
    @Published var posts: [DiscoverCommunityPost] = []
    @Published var venues: [DiscoverVenue] = []
    @Published var coaches: [DiscoverCoachListing] = []
    @Published var config: DiscoverConfig?
    @Published var venueSearchResponse: DiscoverVenueSearchResponse?
    @Published var statusMessage: String?
    @Published var isLoading = false

    private let service = DiscoverService()
    private var didLoad = false

    var backendStateTitle: String {
        config == nil ? "待连接" : "已连接"
    }

    var backendStateIcon: String {
        config == nil ? "wifi.slash" : "checkmark.seal"
    }

    var venueSearchReady: Bool {
        config?.venueSearchReady ?? venueSearchResponse?.venueSearchReady ?? false
    }

    var venueProviderTitle: String {
        venueSearchReady ? "POI 已配置" : "POI 待配置"
    }

    var venueSetupHint: String {
        venueSearchResponse?.setupHint
            ?? "请在后端环境变量配置 KICK_AMAP_KEY、KICK_BAIDU_MAP_AK 或 KICK_TENCENT_MAP_KEY，才能搜索真实球场。"
    }

    var providerSummary: String {
        guard let response = venueSearchResponse else {
            return "暂未搜索球场。"
        }
        if !response.providerErrors.isEmpty {
            return "地图 Provider 有错误：\(response.providerErrors.map { "\($0.key): \($0.value)" }.joined(separator: "；"))"
        }
        if response.providerResultCount.isEmpty {
            return response.setupHint ?? "当前没有 Provider 返回结果。"
        }
        return response.providerResultCount
            .map { "\($0.key) \($0.value) 条" }
            .sorted()
            .joined(separator: "，")
    }

    func load(region: String, coordinate: DiscoverCoordinate?) async {
        guard !didLoad else { return }
        didLoad = true
        await refresh(region: region, coordinate: coordinate)
    }

    func refresh(region: String, coordinate: DiscoverCoordinate?) async {
        isLoading = true
        statusMessage = nil
        defer { isLoading = false }

        await loadConfig()
        await loadPosts(region: region)
        await loadVenues(region: region, coordinate: coordinate)
        await loadCoaches(region: region)
    }

    func refreshVenues(region: String, coordinate: DiscoverCoordinate?) async {
        isLoading = true
        statusMessage = nil
        defer { isLoading = false }
        await loadVenues(region: region, coordinate: coordinate)
    }

    func createPost(
        title: String,
        body: String,
        badge: String,
        visibility: DiscoverPostVisibility,
        region: String
    ) async {
        do {
            let post = try await service.createPost(
                title: title,
                body: body,
                region: region,
                badge: badge,
                visibility: visibility
            )
            posts.insert(post, at: 0)
            statusMessage = "帖子已保存到后端。"
        } catch {
            statusMessage = "发帖失败：\(error.localizedDescription)"
        }
    }

    func updatePost(
        _ post: DiscoverCommunityPost,
        title: String,
        body: String,
        badge: String,
        visibility: DiscoverPostVisibility
    ) async {
        do {
            let updatedPost = try await service.updatePost(
                id: post.id,
                title: title,
                body: body,
                badge: badge,
                visibility: visibility
            )
            if let index = posts.firstIndex(where: { $0.id == post.id }) {
                posts[index] = updatedPost
            }
            statusMessage = "帖子已更新。"
        } catch {
            statusMessage = "编辑失败：\(error.localizedDescription)"
        }
    }

    func like(post: DiscoverCommunityPost) async {
        do {
            let updatedPost = try await service.likePost(id: post.id)
            if let index = posts.firstIndex(where: { $0.id == post.id }) {
                posts[index] = updatedPost
            }
        } catch {
            statusMessage = "点赞失败：\(error.localizedDescription)"
        }
    }

    func book(coach: DiscoverCoachListing, region: String) async {
        do {
            let booking = try await service.bookCoach(
                coachID: coach.id,
                region: region,
                goal: "希望教练基于我的传球/射门分析报告，做一次一对一动作纠错。"
            )
            statusMessage = "已提交预约：\(booking.coachName ?? coach.name)，状态 \(booking.status)。"
        } catch {
            statusMessage = "预约失败：\(error.localizedDescription)"
        }
    }

    private func loadConfig() async {
        do {
            config = try await service.fetchConfig()
        } catch {
            statusMessage = "发现后端未连接：\(error.localizedDescription)"
        }
    }

    private func loadPosts(region: String) async {
        do {
            // 球友圈首页先展示全部可见帖子，避免用户手动/实时定位切换后把自己刚发的内容过滤掉。
            posts = try await service.fetchPosts(region: nil)
        } catch {
            statusMessage = "球友圈加载失败：\(error.localizedDescription)"
        }
    }

    private func loadVenues(region: String, coordinate: DiscoverCoordinate?) async {
        do {
            if coordinate == nil && isRealtimeLocationPlaceholder(region) {
                venueSearchResponse = nil
                venues = []
                statusMessage = "正在获取实时位置；也可以点“切换”手动选择全国任意城市。"
                return
            }

            let target = splitRegion(region)
            let useCoordinateSearch = coordinate != nil
            let response = try await service.searchVenues(
                city: useCoordinateSearch ? nil : target.city,
                district: useCoordinateSearch ? nil : target.district,
                latitude: coordinate?.latitude,
                longitude: coordinate?.longitude
            )
            venueSearchResponse = response
            venues = response.items
        } catch {
            statusMessage = "球场搜索失败：\(error.localizedDescription)"
        }
    }

    private func isRealtimeLocationPlaceholder(_ region: String) -> Bool {
        let value = region.trimmingCharacters(in: .whitespacesAndNewlines)
        return value.isEmpty || value == "实时定位" || value == "当前位置" || value == "定位中"
    }

    private func loadCoaches(region: String) async {
        do {
            coaches = try await service.fetchCoaches(region: region)
        } catch {
            statusMessage = "私教加载失败：\(error.localizedDescription)"
        }
    }

    private func splitRegion(_ region: String) -> (city: String, district: String?) {
        let parts = region
            .components(separatedBy: "·")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        if parts.count >= 2 {
            return (parts[0], parts[1])
        }
        return (region.trimmingCharacters(in: .whitespacesAndNewlines), nil)
    }
}

private struct DiscoverHeroPill: View {
    let title: String
    let icon: String

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 12, weight: .bold))
            Text(title)
                .font(AppTypography.captionMedium)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
        }
        .foregroundStyle(AppColors.textPrimary)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .frame(maxWidth: .infinity)
        .background(AppColors.background.opacity(0.74))
        .clipShape(Capsule())
    }
}

private struct DiscoverSectionHeader: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(AppTypography.sectionTitle)
                .foregroundStyle(AppColors.textPrimary)

            Text(subtitle)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct DiscoverPostCard: View {
    let post: DiscoverCommunityPost
    let onOpen: () -> Void
    let onUserTap: () -> Void
    let onLike: () -> Void

    var body: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 12) {
                    Button(action: onUserTap) {
                        Circle()
                            .fill(AppColors.accent.opacity(0.14))
                            .frame(width: 44, height: 44)
                            .overlay(
                                Image(systemName: "figure.soccer")
                                    .foregroundStyle(AppColors.accent)
                            )
                    }
                    .buttonStyle(.plain)

                    VStack(alignment: .leading, spacing: 4) {
                        Text(post.userName)
                            .font(AppTypography.headline)
                            .foregroundStyle(AppColors.textPrimary)
                        Text("\(post.region) · \(post.badge)")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.energyGold)
                    }

                    Spacer()

                    Label(post.visibility.shortTitle, systemImage: post.visibility.iconName)
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 6)
                        .background(AppColors.backgroundSoft)
                        .clipShape(Capsule())
                }

                Text(post.title)
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                Text(post.body)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)

                if let aiReply = post.aiReply {
                    Text(aiReply)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(AppColors.backgroundSoft)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))
                }

                HStack(spacing: 12) {
                    Button(action: onLike) {
                        Label("\(post.likes)", systemImage: "heart")
                            .font(AppTypography.captionMedium)
                            .foregroundStyle(AppColors.textPrimary)
                    }
                    .buttonStyle(.plain)

                    Label("\(post.commentCount)", systemImage: "bubble.left")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.textSecondary)

                    Spacer()

                    Text("点开查看")
                        .font(AppTypography.captionMedium)
                        .foregroundStyle(AppColors.accent)
                }
            }
        }
        .contentShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
        .onTapGesture(perform: onOpen)
    }
}

private struct DiscoverVenueCard: View {
    let venue: DiscoverVenue
    let onOpen: () -> Void

    var body: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "mappin.and.ellipse")
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundStyle(AppColors.pitchGreen)
                        .frame(width: 44, height: 44)
                        .background(AppColors.pitchGreen.opacity(0.14))
                        .clipShape(Circle())

                    VStack(alignment: .leading, spacing: 6) {
                        Text(venue.name)
                            .font(AppTypography.cardTitle)
                            .foregroundStyle(AppColors.textPrimary)
                        Text(venue.address)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    Image(systemName: "chevron.right")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(AppColors.textTertiary)
                }

                HStack(spacing: 8) {
                    DiscoverSourceBadge(venue.sourceLabel ?? "未知来源")
                    DiscoverSourceBadge(venue.reliabilityLabel ?? "待校验")
                    if venue.latitude != nil, venue.longitude != nil {
                        DiscoverSourceBadge("有坐标")
                    }
                }

                if let phone = venue.phone, !phone.isEmpty {
                    Text("电话：\(phone)")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }

                HStack(spacing: 10) {
                    Label("查看地图", systemImage: "map")
                    Label("导航", systemImage: "arrow.triangle.turn.up.right.diamond")
                }
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.accent)
            }
        }
        .contentShape(RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous))
        .onTapGesture(perform: onOpen)
    }
}

private struct DiscoverCoachChatView: View {
    let coach: DiscoverCoachListing
    let region: String

    @Environment(\.dismiss) private var dismiss
    @State private var conversation: DiscoverCoachConversation?
    @State private var draft = ""
    @State private var isLoading = false
    @State private var errorText: String?

    private let service = DiscoverService()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView(showsIndicators: false) {
                    VStack(alignment: .leading, spacing: 16) {
                        DarkCard {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack(spacing: 10) {
                                    Image(systemName: coach.verified == true ? "checkmark.seal.fill" : "person.crop.circle")
                                        .foregroundStyle(coach.verified == true ? AppColors.pitchGreen : AppColors.accent)

                                    Text(coach.name)
                                        .font(AppTypography.cardTitle)
                                        .foregroundStyle(AppColors.textPrimary)

                                    Spacer()

                                    Text(conversation?.status == "open" ? "会话中" : "待连接")
                                        .font(AppTypography.captionMedium)
                                        .foregroundStyle(AppColors.textSecondary)
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 7)
                                        .background(AppColors.backgroundSoft)
                                        .clipShape(Capsule())
                                }

                                Text("\(coach.specialty) · \(coach.priceText)")
                                    .font(AppTypography.body)
                                    .foregroundStyle(AppColors.textSecondary)
                            }
                        }

                        if let errorText {
                            DiscoverInlineStatusCard(message: errorText)
                        }

                        if isLoading && conversation == nil {
                            DiscoverLoadingCard(title: "正在连接私教聊天")
                        }

                        ForEach(conversation?.messages ?? []) { message in
                            DiscoverCoachMessageBubble(message: message)
                        }
                    }
                    .padding(20)
                }

                Divider()
                    .overlay(AppColors.textPrimary.opacity(0.08))

                HStack(spacing: 10) {
                    TextField("输入你想咨询的问题", text: $draft, axis: .vertical)
                        .lineLimit(1...4)
                        .font(AppTypography.body)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 11)
                        .background(AppColors.backgroundSoft)
                        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))

                    Button {
                        Task { await sendMessage() }
                    } label: {
                        Image(systemName: "paperplane.fill")
                            .font(.system(size: 17, weight: .bold))
                            .foregroundStyle(AppColors.onAccent)
                            .frame(width: 44, height: 44)
                            .background(canSend ? AppColors.accent : AppColors.textTertiary)
                            .clipShape(Circle())
                    }
                    .disabled(!canSend || isLoading)
                    .buttonStyle(.plain)
                }
                .padding(14)
                .background(AppColors.background)
            }
            .kickScreenBackground()
            .navigationTitle("私教聊天")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("关闭") { dismiss() }
                }
            }
            .task {
                await startConversationIfNeeded()
            }
        }
        .presentationDetents([.large])
    }

    private var canSend: Bool {
        !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private func startConversationIfNeeded() async {
        guard conversation == nil else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            conversation = try await service.startCoachConversation(
                coachID: coach.id,
                region: region,
                initialMessage: "我想基于 KickAI 的动作分析报告做一次一对一纠错，请先帮我看最适合怎么练。"
            )
            errorText = nil
        } catch {
            errorText = "私教聊天连接失败：\(error.localizedDescription)"
        }
    }

    private func sendMessage() async {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        if conversation == nil {
            await startConversationIfNeeded()
        }
        guard let conversation else { return }

        draft = ""
        isLoading = true
        defer { isLoading = false }
        do {
            self.conversation = try await service.sendCoachMessage(
                conversationID: conversation.id,
                body: text
            )
            errorText = nil
        } catch {
            draft = text
            errorText = "消息发送失败：\(error.localizedDescription)"
        }
    }
}

private struct DiscoverCoachMessageBubble: View {
    let message: DiscoverCoachMessage

    var body: some View {
        HStack {
            if message.isCurrentUser {
                Spacer(minLength: 48)
            }

            VStack(alignment: message.isCurrentUser ? .trailing : .leading, spacing: 5) {
                Text(message.senderName)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)

                Text(message.body)
                    .font(AppTypography.body)
                    .foregroundStyle(message.isCurrentUser ? AppColors.onAccent : AppColors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(13)
                    .background(message.isCurrentUser ? AppColors.accent : AppColors.card)
                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
            }

            if !message.isCurrentUser {
                Spacer(minLength: 48)
            }
        }
    }
}

private struct DiscoverCoachCard: View {
    let coach: DiscoverCoachListing
    let onBook: () -> Void

    var body: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 7) {
                        HStack(spacing: 8) {
                            Text(coach.name)
                                .font(AppTypography.cardTitle)
                                .foregroundStyle(AppColors.textPrimary)

                            if coach.verified == true {
                                Image(systemName: "checkmark.seal.fill")
                                    .foregroundStyle(AppColors.pitchGreen)
                            }
                        }

                        Text("\(coach.region) · \(coach.specialty)")
                            .font(AppTypography.bodyMedium)
                            .foregroundStyle(AppColors.pitchGreen)
                    }

                    Spacer()

                    Text(coach.priceText)
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.onAccent)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(AppColors.accent)
                        .clipShape(Capsule())
                }

                Text(coach.description)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)

                Button(action: onBook) {
                    Label("预约试聊", systemImage: "person.crop.circle.badge.checkmark")
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.onAccent)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 13)
                        .background(AppColors.accent)
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
    }
}

private struct DiscoverActionCard: View {
    let title: String
    let subtitle: String
    let icon: String
    let actionTitle: String

    var body: some View {
        DarkCard {
            HStack(alignment: .center, spacing: 14) {
                Image(systemName: icon)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(AppColors.onAccent)
                    .frame(width: 48, height: 48)
                    .background(AppColors.accent)
                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))

                VStack(alignment: .leading, spacing: 6) {
                    Text(title)
                        .font(AppTypography.cardTitle)
                        .foregroundStyle(AppColors.textPrimary)
                    Text(subtitle)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)

                Text(actionTitle)
                    .font(AppTypography.captionMedium)
                    .foregroundStyle(AppColors.textSecondary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 7)
                    .background(AppColors.backgroundSoft)
                    .clipShape(Capsule())
            }
        }
    }
}

private struct DiscoverReliabilityCard: View {
    let providerSummary: String

    var body: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("球场数据可信度")
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)

                Text("覆盖靠地图 POI，真实体验靠用户纠错，预约能力靠商家认证；不要承诺全国绝不漏掉，而是标清来源和更新时间。")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)

                Text(providerSummary)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(AppColors.backgroundSoft)
                    .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.small, style: .continuous))

                HStack(spacing: 8) {
                    DiscoverSourceBadge("地图来源")
                    DiscoverSourceBadge("用户校验")
                    DiscoverSourceBadge("商家认证")
                }
            }
        }
    }
}

private struct DiscoverInlineStatusCard: View {
    let message: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill")
                .foregroundStyle(AppColors.matchBlue)
            Text(message)
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(14)
        .background(AppColors.backgroundSoft)
        .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
    }
}

private struct DiscoverLoadingCard: View {
    let title: String

    var body: some View {
        DarkCard {
            HStack(spacing: 12) {
                ProgressView()
                Text(title)
                    .font(AppTypography.bodyMedium)
                    .foregroundStyle(AppColors.textSecondary)
                Spacer()
            }
        }
    }
}

private struct DiscoverEmptyCard: View {
    let title: String
    let subtitle: String

    var body: some View {
        DarkCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(AppTypography.cardTitle)
                    .foregroundStyle(AppColors.textPrimary)
                Text(subtitle)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct DiscoverSmallButton: View {
    let title: String
    let icon: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: icon)
                .font(AppTypography.captionMedium)
                .foregroundStyle(AppColors.accent)
                .padding(.horizontal, 12)
                .padding(.vertical, 9)
                .background(AppColors.backgroundSoft)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }
}

private struct DiscoverSourceBadge: View {
    let title: String

    init(_ title: String) {
        self.title = title
    }

    var body: some View {
        Text(title)
            .font(AppTypography.captionMedium)
            .foregroundStyle(AppColors.textSecondary)
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(AppColors.backgroundSoft)
            .clipShape(Capsule())
    }
}
