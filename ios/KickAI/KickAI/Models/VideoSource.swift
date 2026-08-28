import Foundation

enum VideoSource: String, CaseIterable, Identifiable {
    case photoLibrary
    case camera

    var id: String { rawValue }

    var title: String {
        switch self {
        case .photoLibrary:
            return "从相册选择"
        case .camera:
            return "立即拍摄"
        }
    }

    var subtitle: String {
        switch self {
        case .photoLibrary:
            return "导入已拍摄的训练视频"
        case .camera:
            return "使用相机记录新的训练动作"
        }
    }

    var iconName: String {
        switch self {
        case .photoLibrary:
            return "photo.on.rectangle.angled"
        case .camera:
            return "camera.fill"
        }
    }
}
