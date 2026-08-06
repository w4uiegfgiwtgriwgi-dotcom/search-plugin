# 阶段1补强运行说明

## 本地 API

优先启动 FastAPI：

```powershell
npm run api:dev
```

地址：`http://127.0.0.1:17860`

备用标准库服务：

```powershell
npm run api:legacy
```

## 桌面端

```powershell
npm run desktop:start
```

Electron 启动时会自动检查 `http://127.0.0.1:17860`。如果本地 API 不存在，会尝试通过 `.venv` 拉起 FastAPI；如果 API 已经在运行，则复用已有服务。

烟测 Electron 启动：

```powershell
cd apps/desktop
npm run smoke
```

如果提示 Electron 安装不完整，先重试二进制安装：

```powershell
node node_modules/electron/install.js
```

如果只想看静态页面，可直接打开：

`apps/desktop/src/index.html`

## 测试

```powershell
npm run test:api
npm test
npm run stage0:check
```
