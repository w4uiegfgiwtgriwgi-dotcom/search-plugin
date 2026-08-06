# 阶段1验收报告

> 日期：2026-08-06  
> 项目根目录：`E:\搜索插件`  
> 阶段：阶段1 本地素材搜索 MVP  
> 边界：未创建远程仓库，未推送 GitHub，未进入阶段2，未接入真实平台登录或真实平台自动搜索。

## 验收结论

阶段1本地 MVP 验收通过。

当前已经形成可运行的本地应用闭环：FastAPI 本地服务、SQLite 数据库、两类安全样本适配器、搜索任务、结果列表、项目、收藏、CSV/JSON/Markdown 导出、桌面端 Electron 壳、API 自动检测/拉起逻辑，以及 Chrome MV3 扩展骨架。

## 已完成

- 本地 API：FastAPI 入口可用，标准库 HTTP 服务保留为备用。
- 数据库：SQLite 已支持搜索任务、搜索结果、项目和收藏素材。
- 搜索 MVP：`web-search` 录制样本适配器和 `bilibili` Mock 适配器可返回归一化结果。
- 桌面端：Electron 可启动，界面可搜索、创建项目、收藏结果、导出结果。
- API 生命周期：Electron 启动时检查 `127.0.0.1:17860`，API 不存在时尝试拉起 FastAPI，API 已存在时复用。
- 浏览器扩展：MV3 骨架已提供，当前只做用户主动读取当前页面标题和 URL。
- 依赖：Python 与桌面端依赖均已锁定。
- 文档：阶段1报告和运行说明已更新。

## 未完成

- 真实 B站搜索、普通网页联网搜索尚未启用。
- 未接入用户登录态、扫码登录、验证码暂停恢复等浏览器辅助流程。
- 浏览器扩展尚未把当前页面写入本地素材库。
- Electron 尚未做 Windows 安装包和生产打包验证。
- 真实 OCR、ASR、视觉向量 Provider 尚未接入。

## 验收测试结果

| 项目 | 命令/方式 | 结果 |
|---|---|---|
| API 单元测试 | `npm run test:api` | 通过，3 个测试 OK |
| Node 单元测试 | `node --test tests/unit/*.test.mjs` | 通过，6 个测试 OK |
| 阶段0回归 | `node scripts/stage0/run-stage0-checks.mjs` | 通过，8 项 passed，0 failed |
| FastAPI 接口链路 | POST 搜索、GET 结果、创建项目、收藏、导出 | 通过，任务 completed，返回 3 条结果 |
| Electron smoke | `npm run smoke` | 通过，输出 `electron smoke api status: ready` |
| 当前服务状态 | `127.0.0.1:17860` | FastAPI 正在运行，PID 18708 |

## 验收样本结果

- 搜索词：`极端高温废墟旧空调`
- 平台：`web-search`、`bilibili`
- 搜索任务状态：`completed`
- 返回结果数：3
- 导出验证：JSON 返回 3 条；CSV 包含 `source_url`
- 收藏验证：创建项目成功，收藏结果成功

## 已知风险

- 当前搜索结果来自录制样本和 Mock，不能代表真实平台搜索能力。
- 真实平台适配会遇到页面变化、风控、登录态、验证码和访问频率限制。
- 当前 FFmpeg 为 gyan.dev 构建，后续若随产品分发，需要继续处理 GPL/LGPL 合规策略。
- Electron 已能 smoke 启动，但打包、安装、自动更新和 Windows 权限场景未验证。
- `.local-data` 是本地运行数据，已被 `.gitignore` 忽略，不进入仓库。

## 下一阶段建议

阶段1可以关门。建议进入阶段2前先明确真实截图反查路线：

- 选择 OCR Provider：PaddleOCR、本地轻量 OCR 或继续 Mock。
- 选择视觉向量 Provider：本地 CLIP、轻量 embedding 或 Mock。
- 准备合法测试素材：自制视频、公共领域内容、明确允许测试的图片/视频。
- 保持阶段2只做截图上传、pHash、OCR、视觉向量和候选视频抽帧匹配，不提前扩展真实平台登录能力。
