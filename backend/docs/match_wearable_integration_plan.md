# KickAI 比赛分析与穿戴设备接入方案

更新时间：2026-06-07

## 目标效果

比赛分析最终要接近用户参考图中的信息密度，但数据来源要可解释、可校验，不能用视频估算伪造精确体能指标。

核心模块：

- 比赛概览：上场时长、位置角色、首发/替补、换人时间、比赛时段。
- 体能负荷：总距离、每 90 分钟折算距离、高速跑、冲刺跑、最高速度、平均速度、加减速次数、步数。
- 心率负荷：平均心率、最高心率、心率区间停留时间、训练负荷、热量估算。
- 空间表现：全场热力图、冲刺轨迹、三分区占比、进攻/防守半场占比、边路/中路占比。
- 技战术事件：传球次数、成功率、射门次数、射正、触球、带球、抢断、压迫、失误、关键时间线。
- 换人后分析：换人前/后或上场前/后分段，对距离、速度、冲刺、心率、事件效率做 per-90 或 per-minute 标准化比较。
- 视频证据：关键事件回放、轨迹叠加、事件时间线、可点击切换图表。

## 推荐数据来源分工

### 穿戴设备负责

- 心率与心率区间
- GPS / LPS 位置轨迹
- 速度、距离、冲刺、高速跑、加速度、减速度
- Player Load / 训练负荷
- 部分设备可输出步频、冲击、IMU 姿态变化

### 视频负责

- 传球、射门、触球、带球、抢断等足球事件
- 球员身份锁定与换人确认
- 球门、球、队友、对手、空间关系
- 射门目标区、进球/射偏/被扑等结果
- 关键动作的生物力学窗口：支撑脚、触球脚、髋膝踝发力链、躯干稳定、随摆

### 双源融合负责

- 把 GPS 轨迹投影到球场图，生成热力图和轨迹图。
- 用视频事件时间戳对齐穿戴数据，得到“第 63 分钟冲刺后完成射门”“换人后 10 分钟内高强度跑下降”等解释。
- 用心率和速度共同判断体能状态，避免只看跑动距离。

## 设备选型建议

### MVP 阶段：低成本验证

适合目的：先把 App 的数据接入、图表、历史记录、视频同步跑通。

推荐组合：

- Polar H10 心率带：通过蓝牙 BLE 实时读取心率，稳定、成本低。
- 手机 / Apple Watch / Garmin 运动记录：导出 GPX/FIT/TCX 或通过健康平台同步。
- 视频端继续做传球、射门、触球、换人时间线。

优点：

- 采购简单，成本低。
- 蓝牙心率接入难度较低。
- 可以快速做出心率区间、负荷趋势、视频同步。

限制：

- 手机/手表 GPS 不是专业 EPTS，球场热力图和冲刺速度会有噪声。
- 无法稳定得到职业级 Player Load。
- 事件统计仍依赖视频或手动标注。

### 半专业阶段：足球 GPS 背心

适合目的：做接近参考图的足球专项距离、速度、冲刺、热力图。

可调研设备：

- STATSports APEX / Apex Athlete Series
- Catapult Vector / Catapult One
- Polar Team Pro
- Playermaker
- SoccerBee
- POSSIBALL / 神仙球 X-Vest

采购前必须确认：

- 是否支持导出 CSV / FIT / JSON。
- 是否提供 API 或云端数据下载。
- 采样率是多少，GPS 是否至少 10Hz。
- 是否有心率数据，是否需要额外心率带。
- 是否支持单人购买，还是只卖球队套装。
- 是否支持中国大陆使用、账号注册、售后、固件更新。
- 数据是否可以归用户所有，是否允许接入第三方 App。

### 专业阶段：球队级 EPTS / LPS

适合目的：商业化专业版、俱乐部/校园/青训团队。

建议优先选择有 FIFA EPTS Quality Programme 背书或明确足球场景验证的方案。

限制：

- 成本明显更高。
- 往往需要联系销售，不一定开放个人购买。
- API 可能需要企业合同。
- 室内或遮挡环境要考虑 LPS，而不是普通 GPS。

## 采购渠道建议

### 国际官方渠道

- STATSports：优先查官方商店或联系销售，确认 Apex Athlete / Team 系列是否开放数据导出。
- Catapult：联系官方销售，重点问 Vector / Catapult One 的数据导出和 API。
- Polar：Polar Team Pro 适合团队，Polar H10 适合低成本心率 MVP。
- Playermaker：适合脚部触球和技术动作方向，但要确认数据接口开放程度。
- SoccerBee：足球 GPS 方向，可作为中低成本 GPS 方案调研。

### 国内渠道

- 神仙球 / POSSIBALL：从你截图看有 X-Vest 产品，建议通过小红书官方号、微信客服或社群购买前索要数据样例。
- 淘宝 / 京东 / 闲鱼：可以找 Polar H10、Garmin、二手 Catapult / STATSports，但不要只买“背心”，必须确认是否包含传感器 Pod、账号权限和数据导出能力。

### 采购前要向商家索要

- 一场比赛的 CSV / JSON / FIT 样例。
- 字段说明文档。
- 是否有 API 文档。
- 数据导出频率：实时、赛后、手动导出。
- 是否能拿到原始时间戳。
- 心率区间规则是否可配置。
- 是否能区分上半场、下半场、换人后片段。
- 售后是否支持开发接入。

## 推荐接入路线

### 第 1 阶段：文件导入

先支持用户导入设备导出的 CSV / FIT / GPX / TCX 文件。

优点：

- 不依赖厂商开放 API。
- 适配设备范围广。
- 更适合快速验证比赛分析页面。

后端新增接口建议：

```text
POST /match_sessions
POST /match_sessions/{id}/wearable_import
POST /match_sessions/{id}/video_import
POST /match_sessions/{id}/sync
GET  /match_sessions/{id}/report
```

核心字段：

```json
{
  "athlete_id": "player_001",
  "match_id": "match_001",
  "device_vendor": "polar|garmin|statsports|catapult|possiball|manual",
  "timestamp_ms": 0,
  "elapsed_s": 0.0,
  "heart_rate_bpm": 0,
  "lat": null,
  "lon": null,
  "x_m": null,
  "y_m": null,
  "speed_mps": null,
  "accel_mps2": null,
  "distance_m": null,
  "player_load": null,
  "quality_flags": []
}
```

### 第 2 阶段：蓝牙心率实时接入

优先接 Polar H10 / Garmin HRM 等标准 BLE Heart Rate Service。

App 侧：

- CoreBluetooth 扫描 Heart Rate Service。
- 读取心率 Measurement Characteristic。
- 本地记录 timestamp + bpm。
- 与视频开始时间对齐。

适合做：

- 心率实时曲线。
- 心率区间。
- 训练负荷趋势。
- 比赛后报告。

### 第 3 阶段：厂商 API / 云端同步

当确定设备厂商后，再做 OAuth / API 接入。

优先级：

- Polar AccessLink / Polar Team Pro 数据导出。
- Garmin Health API。
- Catapult / STATSports 企业 API 或 CSV 导出。
- POSSIBALL 如果能提供开发文档，再接入其格式。

## 比赛指标计算口径

### 距离与速度

- 总距离：相邻位置点距离累加，先滤波再累计。
- 每 90 分钟距离：`total_distance / played_minutes * 90`。
- 平均速度：有效运动时长内速度均值。
- 最高速度：用短窗口平滑后的速度最大值，避免 GPS 抖动虚高。
- 高速跑：速度进入高强度阈值后持续超过最短时间才计入。
- 冲刺跑：速度进入冲刺阈值后持续超过最短时间才计入。

### 心率区间

需要用户最大心率或实测阈值。

默认区间可以先用：

- 热身 / 恢复：50%-60% HRmax
- 有氧耐力：60%-75% HRmax
- 有氧动力区：75%-85% HRmax
- 乳酸堆积区：85%-95% HRmax
- 无氧极限区：95%-100% HRmax

注意：年龄公式只能粗略估计，专业版应允许用户输入实测最大心率或阈值心率。

### 换人后分析

换人场景不能直接比总量，要做标准化：

- 上场分钟数
- 每分钟距离
- 每 90 分钟折算距离
- 每分钟高强度跑
- 每分钟冲刺次数
- 每分钟触球 / 传球 / 射门
- 心率恢复速度
- 上场后 5/10/15 分钟强度变化

## App 界面建议

比赛分析不要照搬单次动作反馈页，应独立成“比赛报告”。

推荐 Tab：

- 总览：比分/时长/上场时间/核心结论。
- 体能：心率、速度、距离、负荷。
- 空间：热力图、冲刺轨迹、三分区。
- 事件：传球、射门、触球、压迫、时间线。
- 换人：上场前后、半场前后、疲劳趋势。
- 证据：视频关键片段。

交互原则：

- 用点击切换，不用上滑解锁。
- 图表卡片可横向切换，但一屏内要有清楚的当前层级。
- 热力图、轨迹、三分区要支持点击解释“这个图说明什么”。
- 对“待标定 / 待锁定球员 / 数据不足”给出明确下一步，而不是只显示灰色点。

## 当前最推荐的落地方案

如果现在就要推进，建议：

1. 先买 1 条 Polar H10，做心率实时接入和心率区间。
2. 同时找 POSSIBALL / 神仙球客服要 X-Vest 的 CSV/API 样例，不要先批量采购。
3. 再买 1 套足球 GPS 背心做对比，优先选择能导出 CSV 的设备。
4. App 先做“文件导入 + 视频同步 + 比赛报告”。
5. 确认数据质量后，再做厂商 API 和商业化专业版。

## 权威参考

- FIFA EPTS Quality Programme: https://football-technology.fifa.com/innovation/standards/epts
- FIFA EPTS Standard Data Format: https://football-technology.fifa.com/innovation/standards/epts/research-development-epts-standard-data-format
- StatsBomb Open Data: https://github.com/statsbomb/open-data
- Bluetooth Heart Rate Service: https://www.bluetooth.com/specifications/specs/heart-rate-service-1-0/
- Polar AccessLink: https://www.polar.com/accesslink-api/
- Garmin Health API: https://developer.garmin.com/health-api/overview/
