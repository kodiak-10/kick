# Kick

Kick 是一款 iOS 足球视频分析应用，当前包含传球、射门、传接球训练分析，以及球友圈、球场发现和私教服务入口。

## 本地运行

1. 用 Xcode 打开 `Kick.xcodeproj`。
2. 选择 `KickAI` scheme 和目标设备。
3. 如需连接本地分析服务，在运行配置中设置分析服务地址；真机必须使用局域网可访问的地址，不能使用 `127.0.0.1`。

## 配置

地图 POI 由后端环境变量提供，密钥不提交到本仓库：

```text
KICK_AMAP_KEY=your_amap_key
```

## 说明

`xcuserdata`、构建缓存、设备个人配置和本地密钥均已通过 `.gitignore` 排除。
