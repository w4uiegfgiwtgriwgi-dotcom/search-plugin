# 阶段1 MVP 执行报告

> 日期：2026-08-06  
> 范围：阶段1 本地素材搜索 MVP 补强。  
> 边界：未创建远程仓库，未推送 GitHub，未接入真实平台登录，未实现真实平台自动搜索。

## 已完成

- 本地 API 核心服务：搜索任务、结果入库、项目、收藏、CSV/JSON/Markdown 导出。
- SQLite 持久化结构：`search_tasks`、`search_results`、`projects`、`project_materials`。
- FastAPI 入口补齐：平台、搜索任务、结果、项目、收藏、导出接口均可用，并加入 CORS。
- Python 依赖已安装到项目 `.venv`，并生成 `apps/local-api/requirements.lock.txt`。
- 桌面端依赖已安装并锁定，生成 `apps/desktop/package-lock.json`。
- 两个平台适配器：`web-search` 录制样本、`bilibili` Mock 样本。
- 桌面端阶段1壳补强：搜索、项目创建、收藏到项目、CSV/JSON/Markdown 导出入口。
- Electron 主进程补强：启动时检测本地 API，必要时自动拉起 FastAPI，退出时清理自己拉起的 API 进程。
- Chrome MV3 扩展骨架：用户主动点击后读取当前页面标题和 URL。
- 运行说明：`docs/stage1-runbook.md`。

## 已锁定的关键依赖

- FastAPI：0.141.1
- Uvicorn：0.52.1
- Pydantic：2.13.4
- Electron：43.3.0
- React：19.2.8
- React DOM：19.2.8
- Vite：8.2.0
- @vitejs/plugin-react：6.0.5

## 未完成

- 真实 B站或普通网页联网搜索未启用，阶段1继续使用低风险样本适配器。
- 还没有实现登录态、浏览器辅助搜索、真实收藏当前页面到本地 API。
- 桌面端已安装 Electron，并已实现基础 API 自动检测和拉起；但未做生产打包，也未覆盖 Windows 安装包场景。

## 测试结果

- Python API 单元测试：3 个测试通过。
- Node 阶段0/共享测试：6 个测试通过。
- 阶段0技术检查回归：8 项通过。
- FastAPI 临时端口烟测：通过。平台数 2，搜索任务 `completed`，结果数 3。
- FastAPI 17860 运行中烟测：通过。搜索返回 3 条结果，创建项目成功，收藏结果成功，CSV 导出包含 `source_url`。
- 桌面端和扩展 JS 语法检查：通过。
- Electron 自动拉起逻辑检查：通过。`api-process.cjs` 可检测到当前 FastAPI 服务，并在服务已运行时复用已有服务。
- Electron GUI smoke：暂未通过。原因是 `electron` npm 包已安装，但 Electron Windows 二进制未下载成功，`node_modules/electron/dist/electron.exe` 不存在；重复运行安装脚本 5 分钟超时。

## 当前运行状态

- FastAPI 服务已运行在 `http://127.0.0.1:17860`。
- 当前监听进程 PID：18708。
- 桌面静态页面路径：`apps/desktop/src/index.html`。

## 已知风险

- 当前平台结果来自录制样本和 Mock，不代表真实平台搜索能力已经完成。
- 依赖版本已锁定，但 Electron 二进制下载在当前网络环境下未完成，因此 Electron GUI 启动和 Windows 打包仍未验证。
- 当前 FFmpeg 发行包为 gyan.dev full/essentials 系列，后续若随产品分发需继续处理 GPL/LGPL 合规策略。
- 当前浏览器扩展只读当前页面标题和 URL，尚未写入本地素材库。

## 下一步建议

- 在阶段1内继续做桌面端真实交互 QA 和打包前检查。
- 先解决 Electron 二进制下载问题，可重试 `node node_modules/electron/install.js` 或配置可用镜像源后再运行 `npm run smoke`。
- 在获得明确允许后，做一次低频公开网页搜索联网验证。
- 再进入阶段2前，确认截图上传、OCR、pHash、视觉向量真实 Provider 的安装策略。
