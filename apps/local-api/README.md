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
