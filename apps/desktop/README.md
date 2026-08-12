# 桌面端阶段1骨架

当前目录提供一个可直接用浏览器打开的静态 MVP 界面：`src/index.html`。

已支持：

- 调用本地 API 创建搜索任务。
- Electron 启动时检查本地 API，必要时自动拉起 FastAPI。
- 展示搜索结果。
- 创建项目并把结果收藏到项目。
- 按当前任务导出 CSV、JSON、Markdown。

Electron 入口已预留在 `main.cjs`。安装依赖后可运行：

```powershell
cd apps/desktop
npm install
npm start
```

烟测启动：

```powershell
npm run smoke
```

## Windows 打包准备

阶段5当前只完成打包方案，尚未安装打包工具，也尚未生成安装包。

详见：

- `..\..\docs\stage5-windows-package-plan.md`

打包方案检查：

```powershell
cd E:\搜索插件
npm run stage5:package-plan
```
