# AI Coach iOS Demo

这是一个基于 `Xcode + SwiftUI` 的第一版可演示产品骨架，目标是为未来的 App Store 上架版本提供页面结构、mock 数据和订阅分层基础。

## 当前已完成

- 欢迎页 / 新手引导
- 首页
- 视频上传页
- 分析处理中页
- 分析结果页
- 订阅页 Paywall
- 历史记录页
- 个人中心页
- mock 订阅状态逻辑
- 免费版 / Pro 版展示分层

## 工程路径

- Xcode 工程：`ios/AICoach/AICoach.xcodeproj`
- App 源码：`ios/AICoach/AICoach/`

## 运行方式

1. 用 Xcode 打开 `ios/AICoach/AICoach.xcodeproj`
2. 选择 `AICoach` scheme
3. 选择模拟器或真机后运行

## 当前说明

- 第一版不接真实视频上传，不接真实 AI 分析，不接真实 StoreKit
- Upload / Processing / Result 全部使用 mock 流程和假数据
- 订阅按钮只切换本地状态，不会产生真实扣费

## 下一步建议

1. 接入 `PhotosPicker` 或 `PHPickerViewController` 做真实视频选择
2. 用 `StoreKit 2` 替换 mock 订阅逻辑
3. 接入真实分析任务接口
4. 增加 App Icon、Launch Screen、隐私政策与订阅条款
