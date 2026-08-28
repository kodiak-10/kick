//
//  KickApp.swift
//  Kick
//
//  Created by Xxnew. on 2026/3/18.
//

import SwiftUI
import UIKit

@main
struct KickApp: App {
    @StateObject private var sessionManager = SessionManager()
    @StateObject private var subscriptionManager = SubscriptionManager()
    @StateObject private var purchaseManager = PurchaseManager()

    init() {
        AppearanceConfigurator.configure()
    }

    var body: some Scene {
        WindowGroup {
            AppRootView()
                .environmentObject(sessionManager)
                .environmentObject(subscriptionManager)
                .environmentObject(purchaseManager)
        }
    }
}

private enum AppearanceConfigurator {
    static func configure() {
        let navigationAppearance = UINavigationBarAppearance()
        navigationAppearance.configureWithTransparentBackground()
        navigationAppearance.backgroundEffect = UIBlurEffect(style: .systemThickMaterial)
        navigationAppearance.backgroundColor = UIColor.secondarySystemBackground.withAlphaComponent(0.86)
        navigationAppearance.shadowColor = UIColor.separator.withAlphaComponent(0.08)
        navigationAppearance.titleTextAttributes = [.foregroundColor: UIColor.label]
        navigationAppearance.largeTitleTextAttributes = [.foregroundColor: UIColor.label]

        UINavigationBar.appearance().standardAppearance = navigationAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navigationAppearance

        let tabAppearance = UITabBarAppearance()
        tabAppearance.configureWithTransparentBackground()
        tabAppearance.backgroundEffect = UIBlurEffect(style: .systemUltraThinMaterial)
        tabAppearance.backgroundColor = UIColor.secondarySystemBackground.withAlphaComponent(0.62)
        tabAppearance.shadowColor = UIColor.separator.withAlphaComponent(0.05)
        tabAppearance.stackedLayoutAppearance.selected.iconColor = UIColor.label
        tabAppearance.stackedLayoutAppearance.selected.titleTextAttributes = [.foregroundColor: UIColor.label]
        tabAppearance.stackedLayoutAppearance.normal.iconColor = UIColor.secondaryLabel
        tabAppearance.stackedLayoutAppearance.normal.titleTextAttributes = [.foregroundColor: UIColor.secondaryLabel]

        UITabBar.appearance().standardAppearance = tabAppearance
        UITabBar.appearance().scrollEdgeAppearance = tabAppearance
    }
}
