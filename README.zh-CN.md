<div align="center">

<img src="ios/KickAI/KickAI/Assets.xcassets/AppIcon.appiconset/KickIcon-120.png" alt="Kick 图标" width="88" />

# Kick

[English](README.md) · **简体中文**

### 把每一次训练，变成看得见的进步。

面向足球训练的视频分析项目，连接动作评估、视频复盘与训练反馈。

**SwiftUI · FastAPI · Computer Vision**

[快速开始](#快速开始) · [iOS 客户端](ios/KickAI/README.zh-CN.md) · [后端与 API](backend/README.zh-CN.md)

</div>

---

## 项目介绍

Kick 将 iOS 端的视频上传与回放体验，与 Python 后端的姿态检测、足球动作规则和评分流程连接起来，帮助使用者回看动作、理解反馈并记录训练。

当前仓库包含主应用、分析服务和探索性实现。以下能力依据代码整理；不代表所有流程已达到正式发布标准，也不代表分析准确率已经过独立验证。

## 核心体验

| 方向 | 当前实现 |
| --- | --- |
| 动作分析 | 提供传球、射门、接球及传接球序列的选择入口和后端分析路由 |
| 训练反馈 | 输出动作评分、问题提示和分析状态，在客户端展示训练反馈 |
| 视频复盘 | 结合视频回放查看动作与反馈，保留训练历史入口 |
| 长视频探索 | 包含单一球员长视频入口、目标跟踪和动作片段定位实现 |
| 足球发现 | 包含球友圈、球场查询、教练列表和预约等接口与界面 |

分析结果受拍摄角度、遮挡、画面质量和动作类型影响。评分基于当前规则与视觉流程，应结合原视频理解。长视频及发现功能仍需按具体场景验证。

## 工作方式

```text
选择动作与视频
      ↓
SwiftUI 客户端上传
      ↓
FastAPI 接收请求并选择分析流程
      ↓
姿态与球轨迹处理 → 动作规则与评分 → 质量状态与反馈
      ↓
客户端报告与视频复盘
```

分析服务会返回状态和告警信息。接入时应同时检查结果内容与分析状态，不能仅凭 HTTP 请求成功判断分析有效。

## 快速开始

### 1. 启动分析服务

需要 Python 3.10 或更高版本；依赖未锁定，具体环境兼容性需在本机验证。

```bash
git clone https://github.com/kodiak-10/kick.git
cd kick/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

启动后查看 [健康状态](http://127.0.0.1:8000/health) 与 [交互式 API 文档](http://127.0.0.1:8000/docs)。确认健康响应中的视频分析服务可用，并检查启动告警。

球场查询的地图配置、上传示例和状态说明见 [后端文档](backend/README.zh-CN.md)。

### 2. 运行 iOS 应用

1. 在 macOS 上用支持 iOS 17 SDK 的 Xcode 打开 `ios/KickAI/Kick.xcodeproj`。
2. 选择 `KickAI` scheme，以及 iOS 17 或更高版本的模拟器或设备。
3. 模拟器默认连接 `http://127.0.0.1:8000`。真机需在 Xcode 的 **Edit Scheme → Run → Arguments → Environment Variables** 设置：

```text
KICKAI_ANALYZE_DEVICE_BASE_URL=http://<Mac 的局域网 IP>:8000
```

真机与 Mac 需要网络互通。完整配置见 [iOS 文档](ios/KickAI/README.zh-CN.md)。

## 仓库导航

```text
kick/
├── ios/KickAI/          主 SwiftUI 应用、Xcode 工程与测试
├── ios/AICoach/         早期 iOS 实现，保留供参考
├── backend/
│   ├── main.py         FastAPI 服务入口
│   ├── analysis/       动作路由、视频分析、跟踪与评分
│   ├── vision/         姿态检测与关键点处理
│   ├── tests/          后端测试与样例
│   ├── docs/           研究资料、使用说明与规划
│   └── schemas/        数据结构定义
└── docs/               网页演示文件
```

以代码与当前接口为准；`backend/docs/` 中的规划文档包含尚待实施的设想。

## 开发与验证

后端测试：

```bash
cd backend
python -m pytest
```

iOS 测试：在 Xcode 中选择 `KickAI` scheme 后执行 **Product → Test**。

测试目录覆盖动作路由、评分、视频结果一致性及客户端模型等方向。测试通过情况应以实际运行结果为准。

## 反馈与协作

欢迎通过 [Issues](https://github.com/kodiak-10/kick/issues) 提交问题。请附上复现步骤、运行环境、所选动作和实际结果；分享视频与日志前，请移除个人信息和凭据。

提交改动前，请说明变更目的与验证结果。地图密钥、用户视频、本地数据库及生成报告应保留在本地。
