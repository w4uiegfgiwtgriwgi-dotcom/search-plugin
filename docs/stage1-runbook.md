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

如果只想看静态页面，可直接打开：

`apps/desktop/src/index.html`

## 测试

```powershell
npm run test:api
npm test
npm run stage0:check
```
