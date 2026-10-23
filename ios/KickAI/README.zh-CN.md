# Kick · iOS 客户端

[English](README.md) · **简体中文**

基于 SwiftUI 的足球视频分析应用，包含动作选择、视频上传、训练反馈、回放与历史记录，以及球友圈、球场和教练服务入口。

[返回项目首页](../../README.zh-CN.md) · [分析后端](../../backend/README.zh-CN.md)

## 运行条件

- macOS 与支持 iOS 17 SDK 的 Xcode。
- iOS 17 或更高版本的模拟器或设备。
- 可访问的 Kick 分析后端。

## 本地运行

1. 打开本目录下的 `Kick.xcodeproj`。
2. 选择 `KickAI` scheme 和目标设备。
3. 启动分析后端，并确认 `/health` 中视频分析模块可用。
4. 按下方说明配置地址，再运行应用。真机运行还需在 Xcode 中配置自己的签名团队。

## 分析服务地址

在 **Product → Scheme → Edit Scheme → Run → Arguments → Environment Variables** 中配置：

| 场景 | 变量 | 值 |
| --- | --- | --- |
| 模拟器连接本机 | 无需设置 | 默认 `http://127.0.0.1:8000` |
| 模拟器连接其他服务 | `KICKAI_ANALYZE_SIMULATOR_BASE_URL` | 可访问的服务根地址 |
| 真机连接 Mac | `KICKAI_ANALYZE_DEVICE_BASE_URL` | `http://<Mac 的局域网 IP>:8000` |
| 统一覆盖地址 | `KICKAI_ANALYZE_BASE_URL` | 优先于设备与模拟器配置 |

填写服务根地址，不要附加 `/analyze_video`；客户端会自动拼接。

真机与 Mac 需要网络互通，后端监听 `0.0.0.0:8000`。真机中的 `127.0.0.1` 指向手机自身。当前代码保留了原开发机的默认真机地址，应明确设置自己的地址。

配置逻辑见 [VideoAnalysisService.swift](KickAI/Services/VideoAnalysisService.swift)。

## 功能与分析状态

应用提供传球、射门、接球、传接球和单一球员长视频入口。具体动作与模板映射见 [AnalysisActionChoice.swift](KickAI/Models/AnalysisActionChoice.swift)。

后端同时返回分析状态、告警和反馈内容；请求成功不代表动作分析有效。接球入口与后端路由的兼容性应在联调时检查。

地图服务密钥通过后端环境变量配置；不要写入客户端或提交到仓库。教练、订阅及发现界面的存在不代表相关商业服务已正式上线。

## 验证

在 Xcode 中选择 `KickAI` scheme，执行 **Product → Test**。单元测试与界面测试分别位于 `KickAITests/` 和 `KickAIUITests/`。

`xcuserdata`、构建缓存、设备个人配置与本地凭据不应提交到 Git。
