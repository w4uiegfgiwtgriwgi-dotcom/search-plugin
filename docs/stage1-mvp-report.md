# 阶段1 MVP 执行报告

> 日期：2026-08-05  
> 范围：阶段1 本地素材搜索 MVP 早期闭环。  
> 边界：未创建远程仓库，未推送 GitHub，未接入真实平台登录，未实现完整生产 UI。

## 已完成

- 本地 API 核心服务：搜索任务、结果入库、项目、收藏、CSV/JSON/Markdown 导出。
- SQLite 持久化结构：`search_tasks`、`search_results`、`projects`、`project_materials`。
- 两个平台适配器：`web-search` 录制样本、`bilibili` Mock 样本。
- 桌面端阶段1壳：可打开的静态搜索界面，预留 Electron 入口。
- Chrome MV3 扩展骨架：用户主动点击后读取当前页面标题和 URL。
- 自动化测试：Python `unittest` 覆盖搜索、收藏、导出、查询扩展；Node 测试沿用阶段0验证。

## 未完成

- 当前环境未安装 FastAPI，已提供 `fastapi_app.py` 兼容入口，但未启动真实 FastAPI 服务。
- 当前环境未安装 Electron/React 依赖，桌面端以静态页面和 Electron 配置骨架交付。
- 真实 B站或普通网页联网搜索未启用，阶段1继续使用低风险样本适配器。
- 还没有实现登录态、浏览器辅助搜索、真实收藏当前页面到本地 API。

## 测试结果

- Python API 单元测试：3 个测试通过。
- Node 阶段0/共享测试：6 个测试通过。
- 阶段0技术检查回归：8 项通过。
- HTTP API 烟测：通过。POST `/api/search/tasks` 返回 `completed`，GET `/api/search/tasks/{id}/results` 返回 3 条结果，平台包括 `bilibili` 和 `web-search`。`scripts/run-local-api.py` 已启动后台服务，当前地址为 `http://127.0.0.1:17860`。

## 已知风险

- 当前平台结果来自录制样本和 Mock，不代表真实平台搜索能力已经完成。
- FastAPI、Electron、React 依赖尚未安装和锁定，后续需要联网安装或提供离线包。
- 当前桌面端静态页面依赖本地 API 已启动；还没有应用内自动拉起本地服务。
- 浏览器扩展只读当前页面标题和 URL，尚未写入本地素材库。

## 下一步建议

- 安装并锁定 FastAPI/Uvicorn 与 Electron/React 依赖版本。
- 将标准库 HTTP 服务迁移到真实 FastAPI 运行，并保留核心 service 的测试。
- 在获得允许后做一次低频公开网页搜索联网验证。
- 继续保持适配器和 Provider 接口隔离，避免把平台逻辑写死在 UI 中。

