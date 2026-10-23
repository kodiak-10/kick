# Kick · 分析后端

[English](README.md) · **简体中文**

为 Kick iOS 应用提供视频分析、训练计划及足球发现接口。主入口为 `main.py`，使用 FastAPI；动作分析由 `analysis/` 下的模块处理。

[返回项目首页](../README.zh-CN.md) · [iOS 接入](../ios/KickAI/README.zh-CN.md)

## 本地启动

需要 Python 3.10 或更高版本。依赖版本尚未锁定，安装与模型运行兼容性需在目标环境验证。

从仓库根目录执行：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

保持工作目录为 `backend/`，以便相对路径的数据与配置正确解析。

- 健康检查：`GET http://127.0.0.1:8000/health`
- 交互式接口文档：`http://127.0.0.1:8000/docs`

服务会在后台预加载分析模块。检查健康响应中的 `analyzer_availability.video_analysis`：`pending` 表示尚在准备，`available` 表示已导入，`degraded` 表示加载失败。模块可导入不等于真实视频分析已验证；同时检查 `startup_warnings` 与实际请求结果。

## 配置

应用通过进程环境变量读取配置，不会自动加载 `.env`。如需地图查询配置，可在当前终端加载本地文件后再启动服务：

```bash
cp .env.example .env
# 先编辑 .env，填写自己的地图密钥。
set -a
source .env
set +a
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

| 变量 | 用途 | 默认值 |
| --- | --- | --- |
| `KICK_AMAP_KEY` | 高德地图服务密钥 | 未设置 |
| `KICK_ENABLE_OSM_FALLBACK` | 地图提供方不可用时是否尝试 OpenStreetMap | 开启 |
| `KICK_DB_PATH` | 训练计划 SQLite 数据库路径 | `./data/plans.db` |
| `KICK_DISCOVERY_DB_PATH` | 发现模块数据文件路径 | `./data/discovery.json` |
| `KICK_BACKEND_VERSION` | 健康响应中的服务版本标识 | `local-dev` |

地图查询需要网络，结果取决于提供方与地区数据覆盖。`.env` 仅保留在本地。

## 视频分析 API

`POST /analyze_video` 使用 `multipart/form-data`：

| 字段 | 说明 |
| --- | --- |
| `video_file` | 上传的视频文件 |
| `selected_action` | 明确指定动作类型 |
| `analysis_template` | 可选模板提示；实际模板由动作路由决定 |

当前路由：

| 动作 | `selected_action` | 模板 |
| --- | --- | --- |
| 传球 | `pass` | `short_pass` |
| 射门 | `shot` | `shot_instep` |
| 接球控球 | `receive_control` | `receive_control` |
| 传接球序列 | `pass_receive_sequence` | `pass_receive_sequence` |
| 单一球员长视频 | `full_match` | `full_match_player` |

示例：从 `backend/` 上传仓库中的短片样例。该命令演示调用格式，不保证样例能产生有效评分。

```bash
curl --fail-with-body http://127.0.0.1:8000/analyze_video \
  -F "video_file=@tests/samples/sample_short.mp4" \
  -F "selected_action=pass" \
  -F "analysis_template=short_pass"
```

客户端应读取 `analysis_status`、`failure_reason`、`warnings` 及动作路由信息。HTTP 200 也可能包含部分结果或分析失败；不能直接当作有效评分。

## 其他接口

| 接口 | 用途 |
| --- | --- |
| `POST /generate_plan` | 生成并保存训练计划 |
| `GET /plan/{plan_id}` | 读取训练计划 |
| `DELETE /plan/{plan_id}` | 删除训练计划 |
| `/discovery/community/…` | 社区帖子、点赞与评论 |
| `GET /discovery/venues/search` | 球场查询 |
| `/discovery/coaches…` | 教练列表、预约与会话 |

参数与请求结构以运行服务的 `/docs` 为准。接口存在不代表支付、真实教练履约或生产部署流程已经完成。

## 验证与代码导航

```bash
python -m pytest
```

- `analysis/analyzer_router.py`：动作与模板路由。
- `analysis/shot_analysis.py`：视频分析入口与结果整合。
- `analysis/football_scoring.py`：足球动作评分。
- `analysis/long_video_locator.py`：长视频候选片段定位。
- `vision/`：姿态检测与关键点处理。
- `tests/`：接口、动作、评分与一致性测试。

## 研究与历史实现

仓库还保留 `pipeline.py`、`coach.py`、数据集索引及 `NeuroMiniGame.js` 等实验工具；它们有各自的数据与依赖要求，不属于上述 API 启动流程。

[生物力学参考](docs/biomechanics_reference.md) · [数据集结构](datasets/schema.md)

`scripts/run_kick_backend.sh` 包含原开发机的绝对路径；其他环境请使用本文的启动命令。
