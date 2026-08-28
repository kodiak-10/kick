import Combine
import Foundation

struct ProcessingStep: Identifiable, Hashable {
    let id: UUID
    let title: String
    let subtitle: String

    init(id: UUID = UUID(), title: String, subtitle: String) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
    }
}

@MainActor
final class ProcessingViewModel: ObservableObject {
    enum StepStatus {
        case completed
        case current
        case upcoming
    }

    @Published private(set) var currentStepIndex: Int = -1

    let steps: [ProcessingStep]

    init(steps: [ProcessingStep]? = nil) {
        self.steps = steps ?? AppMockData.processingSteps
    }

    var progress: Double {
        guard !steps.isEmpty else { return 0 }
        return Double(max(currentStepIndex + 1, 0)) / Double(steps.count)
    }

    func status(for index: Int) -> StepStatus {
        if index < currentStepIndex {
            return .completed
        }
        if index == currentStepIndex {
            return .current
        }
        return .upcoming
    }

    func start() async {
        guard currentStepIndex == -1 else { return }

        for index in steps.indices {
            currentStepIndex = index
            let delay: UInt64 = index == 0 ? 500_000_000 : 850_000_000
            try? await Task.sleep(nanoseconds: delay)
        }
    }
}
