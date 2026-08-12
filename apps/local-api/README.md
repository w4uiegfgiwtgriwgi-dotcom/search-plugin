# 本地 API（阶段1 MVP）

阶段1本地 API 提供两个入口：

- `vmf_api.fastapi_app:app`：FastAPI 入口，安装依赖后优先使用。
- `vmf_api.server`：只用 Python 标准库的备用 HTTP 服务，便于离线验证核心能力。

## 启动 FastAPI 服务

```powershell
.\.venv\Scripts\python.exe -m uvicorn vmf_api.fastapi_app:app --app-dir apps/local-api --host 127.0.0.1 --port 17860
```

## 启动标准库备用服务

```powershell
$env:PYTHONPATH='apps/local-api'
& 'C:\Users\Administrator.DESKTOP-P33KF9U\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m vmf_api.server
```

## 示例请求

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:17860/api/search/tasks -ContentType 'application/json' -Body '{"query":"极端高温废墟旧空调"}'
```

## 阶段2截图反查接口

当前先使用 Mock OCR 和 Mock 视觉向量，但 pHash、缩略图、候选视频抽帧和时间点匹配会真实执行。

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:17860/api/assets/analyze-image -ContentType 'application/json' -Body '{"image_path":"E:\\搜索插件\\tests\\fixtures\\stage2\\stage2-air-query.png"}'
```

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:17860/api/matches/find -ContentType 'application/json' -Body '{"query_asset_id":1,"candidate_video_path":"E:\\搜索插件\\tests\\fixtures\\stage2\\stage2-self-made-testsrc.mp4","fps":1,"threshold":0.75}'
```

## 阶段4视频号半自动搜索计划

当前只生成搜索词和人工操作指引，不自动登录微信、不读取登录态、不自动翻页或批量采集。

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:17860/api/wechat-channel/search-plan -ContentType 'application/json' -Body '{"query":"极端高温废墟里男人翻垃圾，最后发现旧空调","keywords":["男人翻垃圾","旧空调"]}'
```
