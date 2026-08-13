# 全网视频素材智能搜索助手

当前阶段：阶段5（Windows 打包与生产化验收）。

这是一个 Windows 本地素材搜索与截图反查 MVP，包含桌面端、本地 API、Chrome MV3 扩展骨架和本地素材库。当前仍使用 Mock OCR 与 Mock 视觉向量，不宣称真实平台全网搜索能力。

## 当前能力

- 本地 API：FastAPI + SQLite，支持搜索样本、项目、素材收藏、素材库筛选和导出。
- 桌面端：Electron 启动后会检查并自动拉起本地 API，支持搜索、项目素材、截图反查、导出和浏览器采集提示。
- 截图反查：支持截图上传、拖拽/粘贴、批量截图、候选视频抽帧、粗扫加精排、时间点定位和匹配帧收藏。
- 素材库：支持搜索收藏和截图反查收藏统一管理，包含复核状态、版权状态、标签备注、可信度、待处理清单、可用状态和时间线。
- 浏览器扩展：用户主动点击后读取当前公开页面标题、URL、作者、描述、封面、发布时间和站点名，并保存到本地素材库。
- 视频号半自动：生成视频号人工搜索词、复制块、人工搜索步骤和安全边界，不自动登录、不自动搜索、不读取登录态。
- 小红书/抖音真实候选：可桥接本机已安装的搜索 CLI，返回公开视频候选链接，并显示匹配度和匹配理由。

## 快速启动

安装依赖后启动桌面端：

```powershell
cd E:\搜索插件\apps\desktop
npm start
```

桌面端会连接或自动拉起 `http://127.0.0.1:17860` 本地 API。

也可以单独启动本地 API：

```powershell
cd E:\搜索插件
.\.venv\Scripts\python.exe scripts\run-fastapi-api.py
```

## Windows 安装包

已生成本机 Windows 安装包：

```text
E:\搜索插件\apps\desktop\dist\全网视频素材智能搜索助手 Setup 0.1.0-stage1.exe
```

目录包位置：

```text
E:\搜索插件\apps\desktop\dist\win-unpacked
```

打包后目录包冒烟已通过，输出 `electron smoke api status: ready`。
安装包静默安装、安装版冒烟和静默卸载均已通过。

## 小红书和抖音真实候选源

桌面端搜索区可以勾选“小红书真实候选”和“抖音真实候选”。
本项目会优先识别仓库 `.venv\Scripts` 里的 `xhs` / `dy` 命令，也支持系统 PATH 中的同名命令。

默认会寻找以下本机命令：

```powershell
xhs search "{query}" --type video --json
dy search "{query}" --type video --count {limit} --json-output
```

如果你安装的开源工具命令不同，可以设置：

```powershell
$env:VMF_XHS_SEARCH_COMMAND = "你的xhs搜索命令 {query} {limit}"
$env:VMF_DOUYIN_SEARCH_COMMAND = "你的dy搜索命令 {query} {limit}"
$env:VMF_SEARCH_CLI_HOME = "候选源登录和缓存目录"
```

小红书、抖音真实搜索通常需要平台登录态、正常网络和平台页面可访问。若未登录或被网络/风控拦截，界面会显示“需要先登录授权”或“网络访问受限”，不会把底层报错直接甩给你。
桌面端候选源状态区会显示登录引导，也可以直接复制以下命令：

```powershell
npm run stage6:login-xhs
npm run stage6:login-xhs:qrcode
npm run stage6:login-douyin
```

详细说明见 `docs/stage6-real-search-candidates.md`。

## 浏览器扩展验收

Chrome 手动加载扩展目录：

```text
E:\搜索插件\apps\browser-extension
```

详细步骤见：

- `docs/stage3-manual-acceptance.md`

扩展只在用户主动点击后读取当前可见页面公开信息，不读取密码、Cookie、Token 或登录态。

## 常用测试

```powershell
cd E:\搜索插件
npm test
npm run test:api
npm run stage3:check
npm run stage4:check
npm run stage5:preflight
npm run stage5:package-plan
npm run stage5:runtime-check
npm run stage6:check-sources
npm run stage5:backup-data
```

`npm run stage3:check` 会依次运行 Node 单元测试、API 测试、扩展脚本语法检查和 Electron 冒烟。
`npm run stage4:check` 会在阶段3检查基础上，额外检查桌面端脚本和阶段4验收文档。
`npm run stage5:preflight` 会在阶段4检查基础上，额外检查打包前关键文件、FFmpeg、Python 和 Electron 依赖。
`npm run stage5:package-plan` 会检查 Windows 打包方案文件和桌面端打包前置条件，不会生成安装包。
`npm run stage5:runtime-check` 会检查 Node、npm、Python、FFmpeg、本地 API 端口、运行目录和 `.gitignore` 安全项。
`npm run stage6:check-sources` 会检查小红书/抖音真实候选源 CLI 是否已经配置。
`npm run stage5:backup-data` 会把本地素材库 `.local-data` 备份为 zip；恢复方式见阶段5数据备份说明。

阶段2/3 常用检查：

```powershell
cd E:\搜索插件\apps\local-api
& '..\..\.venv\Scripts\python.exe' -m unittest tests.test_service tests.test_stage2_media_matching
& '..\..\.venv\Scripts\python.exe' scripts\stage2_robustness_check.py
& '..\..\.venv\Scripts\python.exe' scripts\stage3_browser_collect_smoke.py
```

桌面端冒烟：

```powershell
cd E:\搜索插件\apps\desktop
npm run smoke
```

扩展脚本语法检查：

```powershell
cd E:\搜索插件\apps\browser-extension
node --check src\popup.js
```

## 阶段报告

- `docs/user-guide.md`
- `docs/stage0-report.md`
- `docs/stage1-acceptance-report.md`
- `docs/stage2-acceptance-report.md`
- `docs/stage3-browser-extension-report.md`
- `docs/stage3-acceptance-report.md`
- `docs/stage3-manual-acceptance.md`
- `docs/stage4-wechat-channel-semi-auto-report.md`
- `docs/stage4-manual-acceptance.md`
- `docs/stage4-acceptance-report.md`
- `docs/stage5-production-readiness.md`
- `docs/stage5-windows-package-plan.md`
- `docs/stage5-package-troubleshooting.md`
- `docs/stage5-data-backup.md`
- `docs/stage5-security-license-review.md`
- `docs/stage5-acceptance-report.md`
- `docs/stage6-real-search-candidates.md`

## 重要边界

- 不保存密码、完整 Cookie、Token 或登录态。
- 不实现验证码绕过、DRM 破解、代理证书拦截或加密视频解密。
- 不使用真实账号进行无人值守高频测试。
- 不自动发布、评论、点赞、关注或私信。
- 不承诺搜索互联网中的所有内容。
- 当前 OCR、视觉向量和部分平台能力仍是 Mock 或样本适配器。
- 未经许可证审查，不复制第三方仓库代码。
