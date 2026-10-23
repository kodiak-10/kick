<div align="center">

<img src="docs/assets/kick-banner.svg" alt="Kick — 足球视频分析。看清动作，理解下一步。" width="100%" />

# Kick

**以球员为中心的足球视频分析。**

将动作分析、视频复盘和训练反馈，连接在原生 iOS 体验中。

[English](README.md) · **简体中文**

[了解产品](#训练闭环) · [快速开始](#快速开始) · [iOS 文档](ios/KickAI/README.zh-CN.md) · [后端与 API](backend/README.zh-CN.md)

<sub>SwiftUI · iOS 17+ · Python · FastAPI · OpenCV · MediaPipe</sub>

</div>

---

## 从训练影像，到动作反馈

训练视频记录发生了什么。Kick 将动作评估与反馈放进同一个复盘流程，帮助球员看清动作如何完成，以及下一次训练应该关注什么。

项目连接 SwiftUI 应用与 Python 计算机视觉后端：选择动作、上传片段，再结合原视频查看分析反馈。

<table>
<tr>
<td width="33%" valign="top"><strong>01 / 分析动作</strong><br /><br />通过足球专项动作路由与规则评分，评估动作技术与控制表现。</td>
<td width="33%" valign="top"><strong>02 / 理解反馈</strong><br /><br />结合问题说明、阶段评分与质量信号，理解结果的依据与边界。</td>
<td width="33%" valign="top"><strong>03 / 回看训练</strong><br /><br />在原生 iOS 流程中查看视频回放、训练反馈与历史记录。</td>
</tr>
</table>

## 训练闭环

1. **确定训练重点。** 选择传球、射门、接球、传接球序列或单一球员长视频入口。
2. **上传训练影像。** 从 iOS 客户端将视频片段上传到分析服务。
3. **查看动作分析。** 后端将姿态与球轨迹处理，连接到动作规则、评分与质量检查。
4. **回到视频复盘。** 结合评分、问题说明和训练提示，重新查看原始动作。

| 产品方向 | 仓库中的实现 |
| --- | --- |
| **动作分析** | 明确的动作选择与对应后端分析路由 |
| **训练反馈** | 技术完成度、控制稳定性、阶段评分与下一步建议 |
| **视频复盘** | 回放反馈界面与训练历史 |
| **长视频探索** | 单一球员入口、目标跟踪与候选动作片段定位 |
| **足球发现** | 球友圈、球场查询、教练列表与预约界面和接口 |

## 产品背后的工程设计

| 设计选择 | 实现依据 |
| --- | --- |
| **明确的动作路由** | 根据所选动作确定分析模板，并返回路由信息供核对。[动作路由](backend/analysis/analyzer_router.py) |
| **足球专项评分** | 通过动作模板描述准备、支撑、触球和随挥，提供问题说明与训练提示。[评分逻辑](backend/analysis/football_scoring.py) |
| **评分伴随质量信号** | 质量检查评估帧率、姿态可见度和球轨迹覆盖情况。[质量检查](backend/quality_gate.py) |
| **目标连续性** | 目标锁定逻辑比较不同画面中的位置、身体尺度与外观。[目标跟踪](backend/analysis/target_tracking.py) |
| **客户端与接口分工** | SwiftUI 承载应用体验，FastAPI 提供分析与发现服务。[iOS](ios/KickAI/README.zh-CN.md) · [后端](backend/README.zh-CN.md) |

### 项目状态

Kick 仍在持续开发中。以上介绍对应仓库中已有的代码，不代表分析准确率已经过独立验证或产品已达到正式发布标准。长视频与发现流程需要按场景验证；教练与预约界面不代表相关服务已正式履约上线。

分析受拍摄角度、遮挡、画面质量和动作类型影响。请结合原视频理解评分，并检查分析状态与告警，即使 HTTP 请求成功也应如此。

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
