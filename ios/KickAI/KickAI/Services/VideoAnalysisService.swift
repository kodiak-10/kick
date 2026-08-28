import Foundation
import UniformTypeIdentifiers

struct VideoAnalysisServiceConfiguration {
    let baseURL: URL?
    let endpointPath: String
    let videoFieldName: String
    let timeout: TimeInterval

    let simulatorBaseURL: URL
    let deviceBaseURL: URL?
    let debugOverrideBaseURL: URL?
    let baseURLSourceDescription: String
    let requestMethod: String

    static let defaultEndpointPath = "analyze_video"
    static let defaultVideoFieldName = "video_file"
    static let defaultTimeout: TimeInterval = 60
    static let simulatorDefaultBaseURL = URL(string: "http://127.0.0.1:8000")!
    static let deviceDevelopmentFallbackBaseURL = URL(string: "http://10.66.144.25:8000")

    static var live: VideoAnalysisServiceConfiguration {
        let simulatorConfiguredBaseURL = resolvedConfiguredURL(
            fullURLKeys: ["KICKAI_ANALYZE_SIMULATOR_BASE_URL", "kickai.analyze.simulatorBaseURL"],
            hostKeys: ["KICKAI_ANALYZE_SIMULATOR_HOST", "kickai.analyze.simulatorHost"],
            portKeys: ["KICKAI_ANALYZE_SIMULATOR_PORT", "kickai.analyze.simulatorPort"],
            fallback: nil
        )
        let simulatorBaseURL = simulatorConfiguredBaseURL ?? simulatorDefaultBaseURL

        let deviceBaseURL = resolvedConfiguredURL(
            fullURLKeys: ["KICKAI_ANALYZE_DEVICE_BASE_URL", "kickai.analyze.deviceBaseURL"],
            hostKeys: ["KICKAI_ANALYZE_DEVICE_HOST", "kickai.analyze.deviceHost"],
            portKeys: ["KICKAI_ANALYZE_DEVICE_PORT", "kickai.analyze.devicePort"],
            fallback: nil
        )

        let debugOverrideBaseURL = resolvedConfiguredURL(
            fullURLKeys: ["KICKAI_ANALYZE_BASE_URL", "kickai.analyze.baseURL"],
            hostKeys: ["KICKAI_ANALYZE_HOST", "kickai.analyze.host"],
            portKeys: ["KICKAI_ANALYZE_PORT", "kickai.analyze.port"],
            fallback: nil
        )

        let resolvedBaseURL: URL?
        let baseURLSourceDescription: String

        #if targetEnvironment(simulator)
        if let debugOverrideBaseURL {
            resolvedBaseURL = debugOverrideBaseURL
            baseURLSourceDescription = "debug override"
        } else if simulatorConfiguredBaseURL != nil {
            resolvedBaseURL = simulatorBaseURL
            baseURLSourceDescription = "simulator override"
        } else {
            resolvedBaseURL = simulatorBaseURL
            baseURLSourceDescription = "simulator default"
        }
        #else
        if let debugOverrideBaseURL {
            resolvedBaseURL = debugOverrideBaseURL
            baseURLSourceDescription = "debug override"
        } else if let deviceBaseURL {
            resolvedBaseURL = deviceBaseURL
            baseURLSourceDescription = "device override"
        } else {
            resolvedBaseURL = deviceDevelopmentFallbackBaseURL
            baseURLSourceDescription = deviceDevelopmentFallbackBaseURL == nil
                ? "device unconfigured"
                : "device development fallback"
        }
        #endif

        return VideoAnalysisServiceConfiguration(
            baseURL: resolvedBaseURL,
            endpointPath: defaultEndpointPath,
            videoFieldName: defaultVideoFieldName,
            timeout: defaultTimeout,
            simulatorBaseURL: simulatorBaseURL,
            deviceBaseURL: deviceBaseURL,
            debugOverrideBaseURL: debugOverrideBaseURL,
            baseURLSourceDescription: baseURLSourceDescription,
            requestMethod: "POST"
        )
    }

    init(
        baseURL: URL?,
        endpointPath: String = Self.defaultEndpointPath,
        videoFieldName: String = Self.defaultVideoFieldName,
        timeout: TimeInterval = Self.defaultTimeout,
        simulatorBaseURL: URL = Self.simulatorDefaultBaseURL,
        deviceBaseURL: URL? = nil,
        debugOverrideBaseURL: URL? = nil,
        baseURLSourceDescription: String = "custom",
        requestMethod: String = "POST"
    ) {
        self.baseURL = baseURL
        self.endpointPath = endpointPath
        self.videoFieldName = videoFieldName
        self.timeout = timeout
        self.simulatorBaseURL = simulatorBaseURL
        self.deviceBaseURL = deviceBaseURL
        self.debugOverrideBaseURL = debugOverrideBaseURL
        self.baseURLSourceDescription = baseURLSourceDescription
        self.requestMethod = requestMethod
    }

    init(
        baseURL: URL,
        endpointPath: String = Self.defaultEndpointPath,
        videoFieldName: String = Self.defaultVideoFieldName,
        timeout: TimeInterval = Self.defaultTimeout
    ) {
        self.init(
            baseURL: baseURL,
            endpointPath: endpointPath,
            videoFieldName: videoFieldName,
            timeout: timeout,
            baseURLSourceDescription: "custom"
        )
    }

    var requestURL: URL? {
        guard let baseURL else { return nil }
        return baseURL.appendingPathComponent(endpointPath)
    }

    var resolvedHost: String? {
        baseURL?.host
    }

    var resolvedPort: Int? {
        baseURL?.port
    }

    var baseURLText: String {
        baseURL?.absoluteString ?? "未配置"
    }

    var requestURLText: String {
        requestURL?.absoluteString ?? "未配置"
    }

    var isConfigured: Bool {
        baseURL != nil
    }
}

private func resolvedConfiguredURL(
    fullURLKeys: [String],
    hostKeys: [String],
    portKeys: [String],
    fallback: URL?
) -> URL? {
    if let urlString = firstEnvironmentValue(for: fullURLKeys),
       let url = URL(string: urlString) {
        return url
    }

    if let host = firstEnvironmentValue(for: hostKeys) {
        let portValue = firstEnvironmentValue(for: portKeys).flatMap { Int($0) }
        var components = URLComponents()
        components.scheme = "http"
        components.host = host
        components.port = portValue ?? 8000
        return components.url
    }

    return fallback
}

private func firstEnvironmentValue(for keys: [String]) -> String? {
    for key in keys {
        if let value = ProcessInfo.processInfo.environment[key]?.trimmingCharacters(in: .whitespacesAndNewlines),
           !value.isEmpty {
            return value
        }
        if let value = UserDefaults.standard.string(forKey: key)?.trimmingCharacters(in: .whitespacesAndNewlines),
           !value.isEmpty {
            return value
        }
    }

    for key in keys {
        if let value = legacyMalformedEnvironmentValue(for: key) {
            return value
        }
    }

    return nil
}

private func legacyMalformedEnvironmentValue(for expectedKey: String) -> String? {
    for environmentKey in ProcessInfo.processInfo.environment.keys {
        let trimmedKey = environmentKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmedKey.hasPrefix(expectedKey) else { continue }

        let parts = trimmedKey.split(separator: "=", maxSplits: 1).map {
            String($0).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        if parts.count == 2, !parts[1].isEmpty {
            return parts[1]
        }
    }

    return nil
}

enum VideoAnalysisServiceEvent {
    case requestURL(String)
    case requestTimeout(TimeInterval)
    case multipartFieldNames([String])
    case filename(String)
    case mimeType(String)
    case requestBodySize(Int64)
    case uploadStarted
    case uploadFinished
    case responseReceived
    case responseStatusCode(Int)
    case responseTextPreview(String)
    case errorMessage(String)
}

struct MultipartFormField: Hashable {
    let name: String
    let value: String
}

enum VideoAnalysisServiceError: LocalizedError {
    case invalidBaseURL
    case missingVideoFile
    case transport(URLError)
    case nonHTTPResponse
    case server(statusCode: Int, body: String?, failureMessage: String?, failureReason: String?)
    case analysisFailed(response: VideoAnalysisResponse, statusCode: Int?)
    case emptyResponse
    case decodingFailed
    case bodyEncodingFailed

    var errorDescription: String? {
        switch self {
        case .invalidBaseURL:
            return "分析服务地址未配置。模拟器默认使用 127.0.0.1:8000，真机默认尝试当前开发机 10.66.144.25:8000；如网络变化，请通过 KICKAI_ANALYZE_DEVICE_BASE_URL 指定宿主机局域网 IP。"
        case .missingVideoFile:
            return "请先选择一个视频。"
        case .transport(let error):
            return Self.transportMessage(for: error)
        case .nonHTTPResponse:
            return "服务器返回了无法识别的响应。"
        case .server(let statusCode, let body, let failureMessage, _):
            if let failureMessage, !failureMessage.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return failureMessage
            }
            if statusCode == 400,
               let body,
               body.localizedCaseInsensitiveContains("missing_video_file") {
                return "上传字段名错误或视频文件未成功附加到请求体"
            }
            if statusCode == 404 {
                return "分析接口不存在（404）。请确认后端提供 POST /analyze_video。"
            }
            if statusCode >= 500 {
                return "分析服务返回错误，请稍后重试。"
            }
            return "分析服务返回错误，请稍后重试。"
        case .analysisFailed(let response, _):
            return response.failureReasonText ?? response.failureMessageText ?? "分析服务返回错误，请稍后重试。"
        case .emptyResponse:
            return "服务器没有返回可解析的数据。"
        case .decodingFailed:
            return "JSON 解析失败，后端返回结构与当前页面不匹配。"
        case .bodyEncodingFailed:
            return "视频上传请求构建失败，请重新选择视频。"
        }
    }

    var statusCode: Int? {
        switch self {
        case .server(let statusCode, _, _, _):
            return statusCode
        case .analysisFailed(_, let statusCode):
            return statusCode
        default:
            return nil
        }
    }

    var failureMessage: String? {
        switch self {
        case .server(_, _, let failureMessage, _):
            return failureMessage
        case .analysisFailed(let response, _):
            return response.failureMessageText
        default:
            return nil
        }
    }

    var failureReason: String? {
        switch self {
        case .server(_, _, _, let failureReason):
            return failureReason
        case .analysisFailed(let response, _):
            return response.failureReasonText
        default:
            return nil
        }
    }

    var analysisStatus: String? {
        switch self {
        case .analysisFailed(let response, _):
            return response.analysisStatusText
        default:
            return nil
        }
    }

    var responseBodyPreview: String? {
        switch self {
        case .server(_, let body, _, _):
            return body?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
        case .analysisFailed(let response, _):
            return response.routeDebugText
        default:
            return nil
        }
    }

    var logTag: String {
        switch self {
        case .transport:
            return "[KICK_UPLOAD_NETWORK_ERROR]"
        case .server:
            return "[KICK_UPLOAD_SERVER_ERROR]"
        case .analysisFailed:
            return "[KICK_UPLOAD_FAILURE_STATE]"
        default:
            return "[KICK_UPLOAD_FAILURE_STATE]"
        }
    }

    func logLine(requestURL: String) -> String {
        switch self {
        case .transport(let error):
            return "[KICK_UPLOAD_NETWORK_ERROR] request_url=\(requestURL) error_code=\(error.code.rawValue) error_domain=\(NSURLErrorDomain) localized_description=\(error.localizedDescription)"
        case .server(let statusCode, let body, let failureMessage, let failureReason):
            return "[KICK_UPLOAD_SERVER_ERROR] request_url=\(requestURL) status_code=\(statusCode) failure_message=\(failureMessage ?? "nil") failure_reason=\(failureReason ?? "nil") response_body_preview=\(body?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? "nil")"
        case .analysisFailed(let response, let statusCode):
            return "[KICK_UPLOAD_FAILURE_STATE] request_url=\(requestURL) status_code=\(statusCode.map(String.init) ?? "nil") analysis_status=\(response.analysisStatusText) failure_message=\(response.failureMessageText ?? "nil") failure_reason=\(response.failureReasonText ?? "nil") route_debug_text=\(response.routeDebugText.replacingOccurrences(of: "\n", with: " | "))"
        case .invalidBaseURL:
            return "[KICK_UPLOAD_FAILURE_STATE] request_url=\(requestURL) localized_description=\(localizedDescription)"
        case .missingVideoFile:
            return "[KICK_UPLOAD_FAILURE_STATE] request_url=\(requestURL) localized_description=\(localizedDescription)"
        case .nonHTTPResponse:
            return "[KICK_UPLOAD_SERVER_ERROR] request_url=\(requestURL) localized_description=\(localizedDescription)"
        case .emptyResponse:
            return "[KICK_UPLOAD_SERVER_ERROR] request_url=\(requestURL) localized_description=\(localizedDescription)"
        case .decodingFailed:
            return "[KICK_UPLOAD_SERVER_ERROR] request_url=\(requestURL) localized_description=\(localizedDescription)"
        case .bodyEncodingFailed:
            return "[KICK_UPLOAD_FAILURE_STATE] request_url=\(requestURL) localized_description=\(localizedDescription)"
        }
    }

    private static func transportMessage(for error: URLError) -> String {
        switch error.code {
        case .notConnectedToInternet,
             .networkConnectionLost,
             .cannotConnectToHost,
             .timedOut:
            if error.code == .notConnectedToInternet {
                return "当前没有可用网络，无法连接分析服务。"
            }
            return "后端未启动，无法连接分析服务。"
        case .cannotFindHost,
             .dnsLookupFailed:
            return "分析服务地址不可用，请检查 host / port。"
        default:
            return "网络请求失败：\(error.localizedDescription)"
        }
    }
}

final class VideoAnalysisService {
    private let configuration: VideoAnalysisServiceConfiguration
    private let session: URLSession

    var requestTimeoutSeconds: TimeInterval {
        configuration.timeout
    }

    var requestMethod: String {
        configuration.requestMethod
    }

    var endpointPath: String {
        configuration.endpointPath
    }

    var requestURL: URL? {
        configuration.requestURL
    }

    var requestURLString: String {
        configuration.requestURLText
    }

    var baseURLString: String {
        configuration.baseURLText
    }

    var baseURLSourceDescription: String {
        configuration.baseURLSourceDescription
    }

    var hostDescription: String {
        configuration.resolvedHost ?? "未配置"
    }

    var portDescription: String {
        configuration.resolvedPort.map(String.init) ?? "未配置"
    }

    init(configuration: VideoAnalysisServiceConfiguration = .live) {
        self.configuration = configuration

        let urlSessionConfiguration = URLSessionConfiguration.default
        urlSessionConfiguration.waitsForConnectivity = false
        urlSessionConfiguration.timeoutIntervalForRequest = configuration.timeout
        urlSessionConfiguration.timeoutIntervalForResource = configuration.timeout
        urlSessionConfiguration.requestCachePolicy = .reloadIgnoringLocalCacheData

        session = URLSession(configuration: urlSessionConfiguration)
    }

    func analyzeVideo(
        fileURL: URL,
        selectedAction: AnalysisActionChoice,
        onEvent: (@Sendable (VideoAnalysisServiceEvent) -> Void)? = nil
    ) async throws -> VideoAnalysisResponse {
        guard let baseURL = configuration.baseURL,
              baseURL.scheme != nil,
              baseURL.host != nil else {
            let message = VideoAnalysisServiceError.invalidBaseURL.localizedDescription
            onEvent?(.errorMessage(message))
            print("[KICK_UPLOAD_FAILURE_STATE] kind=configuration_missing message=\(message) base_url_source=\(configuration.baseURLSourceDescription) base_url=\(configuration.baseURLText) simulator_base_url=\(configuration.simulatorBaseURL.absoluteString) device_base_url=\(configuration.deviceBaseURL?.absoluteString ?? "nil") debug_override_base_url=\(configuration.debugOverrideBaseURL?.absoluteString ?? "nil")")
            throw VideoAnalysisServiceError.invalidBaseURL
        }

        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            let message = VideoAnalysisServiceError.missingVideoFile.localizedDescription
            onEvent?(.errorMessage(message))
            print("[KICK_UPLOAD_FAILURE_STATE] kind=validation message=\(message) file_url=\(fileURL.absoluteString)")
            throw VideoAnalysisServiceError.missingVideoFile
        }

        let endpointURL = baseURL.appendingPathComponent(configuration.endpointPath)
        onEvent?(.requestURL(endpointURL.absoluteString))
        onEvent?(.requestTimeout(configuration.timeout))
        print("[KICK_UPLOAD_REQUEST] request_url=\(endpointURL.absoluteString) method=\(configuration.requestMethod) base_url=\(configuration.baseURLText) host=\(configuration.resolvedHost ?? "nil") port=\(configuration.resolvedPort.map(String.init) ?? "nil") endpoint_path=\(configuration.endpointPath) timeout_seconds=\(configuration.timeout) base_url_source=\(configuration.baseURLSourceDescription)")

        var request = URLRequest(url: endpointURL)
        request.httpMethod = configuration.requestMethod
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.timeoutInterval = configuration.timeout

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        // Keep the user's explicit action choice visible in the multipart payload.
        let selectedActionField = MultipartFormField(
            name: "selected_action",
            value: selectedAction.selectedActionValue
        )
        let analysisTemplateField = MultipartFormField(
            name: "analysis_template",
            value: selectedAction.analysisTemplateValue
        )
        let extraFields = [selectedActionField, analysisTemplateField]
        print("[KICK_UPLOAD_REQUEST] selected_action=\(selectedAction.selectedActionValue) analysis_template=\(selectedAction.analysisTemplateValue) video_field_name=\(configuration.videoFieldName)")

        let bodyInfo = try buildMultipartBody(
            boundary: boundary,
            textFields: extraFields,
            fileURL: fileURL,
            fieldName: configuration.videoFieldName,
            fileName: fileURL.lastPathComponent.isEmpty ? "video.mov" : fileURL.lastPathComponent,
            mimeType: mimeType(for: fileURL)
        )

        defer {
            try? FileManager.default.removeItem(at: bodyInfo.bodyURL)
        }

        onEvent?(.multipartFieldNames(bodyInfo.fieldNames))
        onEvent?(.filename(bodyInfo.fileName))
        onEvent?(.mimeType(bodyInfo.mimeType))
        onEvent?(.requestBodySize(bodyInfo.bodySizeBytes))
        print("[KICK_UPLOAD_REQUEST] multipart_field_names=\(bodyInfo.fieldNames.joined(separator: ",")) filename=\(bodyInfo.fileName) mime_type=\(bodyInfo.mimeType) request_body_size=\(bodyInfo.bodySizeBytes)")

        do {
            onEvent?(.uploadStarted)
            print("[KICK_UPLOAD_REQUEST] upload_started=true request_url=\(endpointURL.absoluteString)")

            let (data, response) = try await session.upload(for: request, fromFile: bodyInfo.bodyURL)

            onEvent?(.uploadFinished)
            print("[KICK_UPLOAD_REQUEST] upload_finished=true request_url=\(endpointURL.absoluteString)")

            guard let httpResponse = response as? HTTPURLResponse else {
                throw VideoAnalysisServiceError.nonHTTPResponse
            }

            onEvent?(.responseReceived)
            onEvent?(.responseStatusCode(httpResponse.statusCode))
            let responsePreview = responseTextPreview(from: data)
            onEvent?(.responseTextPreview(responsePreview))
            print("[KICK_UPLOAD_RESPONSE] connected=true request_url=\(endpointURL.absoluteString) status_code=\(httpResponse.statusCode) response_body_preview=\(responsePreview)")

            guard 200..<300 ~= httpResponse.statusCode else {
                let bodyText = String(data: data, encoding: .utf8)
                let failureDetails = backendFailureDetails(from: data)
                throw VideoAnalysisServiceError.server(
                    statusCode: httpResponse.statusCode,
                    body: bodyText,
                    failureMessage: failureDetails?.failureMessage,
                    failureReason: failureDetails?.failureReason
                )
            }

            guard !data.isEmpty else {
                throw VideoAnalysisServiceError.emptyResponse
            }

            do {
                let response = try JSONDecoder().decode(VideoAnalysisResponse.self, from: data)
                if response.isAnalysisFailure {
                    throw VideoAnalysisServiceError.analysisFailed(
                        response: response,
                        statusCode: httpResponse.statusCode
                    )
                }

                return response
            } catch {
                if let serviceError = error as? VideoAnalysisServiceError {
                    throw serviceError
                }

                throw VideoAnalysisServiceError.decodingFailed
            }
        } catch is CancellationError {
            throw CancellationError()
        } catch let error as VideoAnalysisServiceError {
            onEvent?(.errorMessage(error.localizedDescription))
            print(error.logLine(requestURL: endpointURL.absoluteString))
            throw error
        } catch let error as URLError {
            if error.code == .cancelled {
                throw CancellationError()
            }

            let mappedError = VideoAnalysisServiceError.transport(error)
            onEvent?(.errorMessage(mappedError.localizedDescription))
            print("[KICK_UPLOAD_NETWORK_ERROR] request_url=\(endpointURL.absoluteString) error_code=\(error.code.rawValue) error_domain=\(NSURLErrorDomain) localized_description=\(error.localizedDescription)")
            throw mappedError
        } catch {
            onEvent?(.errorMessage(VideoAnalysisServiceError.decodingFailed.localizedDescription))
            print("[KICK_UPLOAD_SERVER_ERROR] request_url=\(endpointURL.absoluteString) status_code=unknown response_body_preview=unavailable failure_message=unavailable failure_reason=unavailable localized_description=\(error.localizedDescription)")
            throw VideoAnalysisServiceError.decodingFailed
        }
    }

    private struct BackendFailureDetails {
        let failureMessage: String?
        let failureReason: String?
        let analysisStatus: String?
    }

    private func backendFailureDetails(from data: Data) -> BackendFailureDetails? {
        guard !data.isEmpty,
              let payload = try? JSONDecoder().decode(JSONValue.self, from: data) else {
            return nil
        }

        let failureMessage = backendStringValue(
            for: ["failure_message", "failureMessage", "message", "detail", "error_message", "errorMessage"],
            in: payload
        )
        let failureReason = backendStringValue(
            for: ["failure_reason", "failureReason", "reason", "failure_detail", "failureDetail"],
            in: payload
        )
        let analysisStatus = backendStringValue(
            for: ["analysis_status", "analysisStatus", "status", "state"],
            in: payload
        )

        guard failureMessage != nil || failureReason != nil || analysisStatus != nil else {
            return nil
        }

        return BackendFailureDetails(
            failureMessage: failureMessage,
            failureReason: failureReason,
            analysisStatus: analysisStatus
        )
    }

    private func backendStringValue(for keys: [String], in payload: JSONValue) -> String? {
        for key in keys {
            if let value = payload.searchValue(for: key),
               let string = value.stringValue(preferredKeys: ["message", "text", "detail", "content", "summary", "value"]) {
                return string
            }
        }

        return nil
    }

    func buildMultipartBody(
        boundary: String,
        textFields: [MultipartFormField] = [],
        fileURL: URL,
        fieldName: String,
        fileName: String,
        mimeType: String
    ) throws -> MultipartBodyInfo {
        let bodyURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("kickai-upload-\(UUID().uuidString).tmp")

        FileManager.default.createFile(atPath: bodyURL.path, contents: nil)

        var shouldKeepBodyFile = false
        defer {
            if !shouldKeepBodyFile {
                try? FileManager.default.removeItem(at: bodyURL)
            }
        }

        guard let writer = FileHandle(forWritingAtPath: bodyURL.path) else {
            throw VideoAnalysisServiceError.bodyEncodingFailed
        }

        defer {
            try? writer.close()
        }

        let sanitizedFileName = sanitize(fileName)

        func write(_ string: String) throws {
            guard let data = string.data(using: .utf8) else {
                throw VideoAnalysisServiceError.bodyEncodingFailed
            }
            try writer.write(contentsOf: data)
        }

        for field in textFields {
            try write("--\(boundary)\r\n")
            try write("Content-Disposition: form-data; name=\"\(field.name)\"\r\n\r\n")
            try write("\(field.value)\r\n")
        }

        try write("--\(boundary)\r\n")
        try write("Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(sanitizedFileName)\"\r\n")
        try write("Content-Type: \(mimeType)\r\n\r\n")

        guard let reader = FileHandle(forReadingAtPath: fileURL.path) else {
            throw VideoAnalysisServiceError.missingVideoFile
        }

        defer {
            try? reader.close()
        }

        while true {
            let chunk = try reader.read(upToCount: 64 * 1024)
            guard let chunk, !chunk.isEmpty else {
                break
            }
            try writer.write(contentsOf: chunk)
        }

        try write("\r\n--\(boundary)--\r\n")

        let attributes = try FileManager.default.attributesOfItem(atPath: bodyURL.path)
        let bodySizeBytes = (attributes[.size] as? NSNumber)?.int64Value ?? 0

        let bodyInfo = MultipartBodyInfo(
            bodyURL: bodyURL,
            fieldNames: textFields.map(\.name) + [fieldName],
            fileName: sanitizedFileName,
            mimeType: mimeType,
            bodySizeBytes: bodySizeBytes
        )

        shouldKeepBodyFile = true
        return bodyInfo
    }

    func mimeType(for fileURL: URL) -> String {
        if let type = UTType(filenameExtension: fileURL.pathExtension),
           let mimeType = type.preferredMIMEType {
            return mimeType
        }
        return "video/mp4"
    }

    private func responseTextPreview(from data: Data, limit: Int = 180) -> String {
        guard !data.isEmpty else {
            return "空响应"
        }

        guard let rawText = String(data: data, encoding: .utf8) else {
            return "非 UTF-8 响应（\(data.count) bytes）"
        }

        let normalized = rawText
            .replacingOccurrences(of: "\r\n", with: " ")
            .replacingOccurrences(of: "\n", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        guard normalized.count > limit else {
            return normalized
        }

        let index = normalized.index(normalized.startIndex, offsetBy: limit)
        return String(normalized[..<index]) + "…"
    }

    private func sanitize(_ fileName: String) -> String {
        fileName
            .replacingOccurrences(of: "\"", with: "_")
            .replacingOccurrences(of: "\r", with: "_")
            .replacingOccurrences(of: "\n", with: "_")
    }
}

struct MultipartBodyInfo {
    let bodyURL: URL
    let fieldNames: [String]
    let fileName: String
    let mimeType: String
    let bodySizeBytes: Int64
}
