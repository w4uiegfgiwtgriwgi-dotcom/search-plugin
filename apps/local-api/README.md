# 本地 API（阶段1 MVP）

阶段1优先实现一个不依赖外网安装的本地 API 核心：

- `vmf_api.service.LocalApiService`：SQLite、搜索任务、结果、项目、收藏和导出。
- `vmf_api.server`：只用 Python 标准库的本地 HTTP 服务。
- `vmf_api.fastapi_app`：FastAPI 兼容入口；当前环境未安装 FastAPI，所以作为后续真实服务入口保留。

## 启动标准库 HTTP 服务

```powershell
$env:PYTHONPATH='apps/local-api'
& 'C:\Users\Administrator.DESKTOP-P33KF9U\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m vmf_api.server
```
