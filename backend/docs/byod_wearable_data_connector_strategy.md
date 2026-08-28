# KickAI 方案 C：纯背心 + 用户自带设备数据接入方案

更新时间：2026-06-07

## 结论

方案 C 可以做，而且是成本最低、商业风险最低的早期路线。

但要纠正一个关键点：

```text
不要让用户把手表放进背心里测心率。
```

Apple Watch、Garmin、华为、小米等腕式设备的心率通常依赖手腕贴合。放进背心口袋后，心率基本不可用。纯背心应该承担：

- 固定手机或小型 GPS Pod。
- 固定胸带式心率带。
- 提供球员编号 / QR / NFC 身份识别。
- 辅助视频识别目标球员。
- 让用户穿戴体验统一。

用户已有手表应继续戴在手腕上；KickAI 通过 HealthKit、文件导入、厂商 API 或 BLE 读取数据。

## 方案 C 的产品定义

KickAI 销售：

- 纯背心
- App
- 数据报告订阅
- 可选胸带固定结构
- 可选手机后背口袋
- 可选球员 ID / QR / NFC 标识

用户自带：

- Apple Watch
- Garmin
- Polar
- COROS
- 华为 / 小米 / 佳明等运动表
- Strava / Apple 健康 / 运动 App
- 手机 GPS

KickAI 的核心价值：

- 把不同品牌的数据统一成比赛报告。
- 把穿戴数据和视频事件同步。
- 输出足球专项解释，而不是只展示通用运动数据。

## 不同品牌数据怎么获取

建议做一个 `Wearable Data Connector Hub`，不要为每个品牌写死业务逻辑。

### 路线 1：Apple HealthKit

适合：

- Apple Watch
- 写入 Apple 健康的第三方 App
- 部分 Garmin / Polar / Strava 同步到 Apple 健康后的数据

可读取：

- HKWorkout
- 心率样本
- 活动能量
- 步数
- 距离
- workout route 路线
- 运动开始和结束时间

优点：

- iOS 生态最稳。
- 用户授权后直接读取。
- 对 Apple Watch 用户体验最好。

限制：

- 数据是否完整取决于来源 App 是否写入 HealthKit。
- 某些第三方 App 不一定把详细秒级数据写入健康。
- 路线数据需要单独查询。

### 路线 2：文件导入

适合：

- Garmin
- COROS
- Wahoo
- Suunto
- Polar
- 第三方 GPS App
- 用户从运动平台导出的活动文件

支持格式优先级：

```text
FIT > TCX > GPX > CSV
```

可读取：

- 时间戳
- 经纬度
- 海拔
- 心率
- 速度
- 距离
- 步频
- 功率或负荷字段
- 设备来源

优点：

- 不依赖厂商 API。
- 数据主权更清晰，用户主动导入。
- 适合商业化早期。

限制：

- 用户多一步导入操作。
- 不同厂商字段差异大。
- FIT 解析需要稳定库。

### 路线 3：厂商 API / OAuth

适合成熟后提升体验。

优先级：

- Polar AccessLink：相对开放，适合心率和训练数据。
- Garmin Health API：商业价值高，但需要申请和审批。
- Strava API：适合作为跨品牌中转，但原始心率和 stream 权限不一定稳定。

不建议早期过度依赖：

- 华为 / 小米 / OPPO / vivo 私有运动数据接口
- 没有稳定公开 API 的厂商
- 只支持网页查看、不支持导出的平台

### 路线 4：BLE 直连

适合：

- Polar H10
- Garmin HRM
- 支持标准 BLE Heart Rate Service 的心率带

可读取：

- 实时心率
- 部分设备支持 RR interval

优点：

- 实时。
- 不依赖厂商云。
- 非常适合训练和比赛心率同步。

限制：

- 大多数手表不会稳定开放 BLE 心率广播。
- BLE 只解决心率，不解决 GPS 热力图。

## 推荐的数据接入优先级

App 内优先按以下顺序引导：

```text
Apple Watch 用户：Apple HealthKit
Garmin / COROS / Suunto 用户：导入 FIT / TCX
Polar 用户：Polar AccessLink 或 BLE 心率
Strava 用户：Strava API / GPX 导入
没有设备：手机 GPS + 视频分析
```

## 统一数据模型

不管数据来自 Apple、Garmin、Polar 还是 CSV，都先转换成 KickAI 内部格式。

```json
{
  "source": "healthkit|fit|tcx|gpx|csv|polar|garmin|strava|ble_hr",
  "device_brand": "apple|garmin|polar|coros|huawei|xiaomi|unknown",
  "device_model": "Apple Watch|Forerunner|H10|unknown",
  "activity_id": "string",
  "athlete_id": "string",
  "match_id": "string",
  "timestamp_ms": 0,
  "elapsed_s": 0.0,
  "heart_rate_bpm": null,
  "lat": null,
  "lon": null,
  "x_m": null,
  "y_m": null,
  "speed_mps": null,
  "distance_m": null,
  "cadence_spm": null,
  "altitude_m": null,
  "quality_flags": []
}
```

## 数据质量分级

不同品牌、不同导入方式质量不同，必须在报告里标注可信度。

### A 级

- 秒级或更高频率时间戳。
- 有 GPS 轨迹。
- 有心率。
- 有明确开始/结束时间。
- 能和视频时间同步。

### B 级

- 有心率和总距离。
- 轨迹不完整或采样较低。
- 可以做负荷趋势，但热力图仅参考。

### C 级

- 只有总距离、平均心率等汇总。
- 只能做比赛概要，不能做精确时间线。

### D 级

- 用户手动输入或缺少时间戳。
- 只能作为备注，不进入专业分析。

## 纯背心该怎么设计

纯背心不要承诺自己采集心率或 GPS，除非里面有电子硬件。

建议结构：

- 背部上方：手机 / 小型 GPS Pod 口袋。
- 胸前：心率胸带固定通道。
- 前后：大面积号码和颜色识别区域。
- 肩背：可贴 QR / NFC / 球员 ID。
- 材料：透气、弹力、防滑、可机洗。
- 尺码：儿童、青少年、成人。

商业卖点：

- 让视频更容易锁定目标球员。
- 让手机/GPS 记录更稳定。
- 让胸带不会滑。
- 让比赛数据和视频能绑定到同一个球员。

## App 用户流程

### 比赛前

1. 选择“整场比赛”。
2. 选择数据来源：
   - Apple 健康
   - 导入 FIT / GPX / TCX
   - 连接心率带
   - 暂无设备，只用视频
3. 选择目标球员或扫描背心 QR。
4. 设置比赛开始时间、半场、换人时间。

### 比赛后

1. 导入视频。
2. 导入或同步手表数据。
3. App 自动匹配时间线。
4. 用户确认：
   - 上半场开始
   - 下半场开始
   - 换人时间
   - 目标球员
5. 生成报告。

## 品牌兼容策略

### 第一批必须支持

- Apple Watch：HealthKit
- Polar H10：BLE 心率
- Garmin：FIT 文件导入
- 通用 GPX / TCX：文件导入

### 第二批支持

- Strava：OAuth + Activity Streams
- Polar Flow：AccessLink
- COROS：优先文件导入
- Suunto / Wahoo：优先文件导入

### 暂不承诺深度支持

- 华为
- 小米
- OPPO
- vivo

原因：

- 商业 API 不稳定或不公开。
- 数据权限和平台策略不确定。
- 可以先通过 HealthKit 同步或文件导入解决一部分。

## 方案 C 的商业模式

可以卖：

- 纯背心硬件
- App Pro 订阅
- 比赛报告次数包
- 球队版账号
- 视频 + 穿戴数据融合分析

不要把收入押在：

- 第三方 API 永久在线
- 第三方设备完整开放原始数据
- 用户愿意手动操作复杂导入

所以 App 必须提供：

- 自动同步路径
- 文件导入路径
- 无设备视频路径
- 数据质量提示

## 最低成本 MVP

第一版建议只做：

- Apple HealthKit 导入
- FIT / GPX / TCX 文件导入
- BLE 心率带直连
- 比赛视频同步
- 手动换人时间
- 手动目标球员确认

暂不做：

- 厂商深度 API
- 自研硬件
- 多球员全自动识别
- 实时球队大屏

## 权威参考

- Apple HealthKit Route Data: https://developer.apple.com/documentation/healthkit/reading-route-data
- Apple Watch Heart Rate: https://support.apple.com/en-us/HT204511
- Garmin Health API: https://developer.garmin.com/gc-developer-program/health-api/
- Polar AccessLink API: https://www.polar.com/accesslink-api/
- Strava API: https://strava.github.io/api/
- Bluetooth Heart Rate Service: https://www.bluetooth.com/specifications/specs/heart-rate-service-1-0/
