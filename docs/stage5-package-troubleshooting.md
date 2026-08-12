# 阶段5打包诊断与重试说明

> 日期：2026-08-12  
> 范围：Windows 打包失败诊断、重试步骤和通过标准。  
> 当前状态：打包配置已接入，但目录包尚未成功生成。

## 当前已完成

- 已安装 `electron-builder`。
- 桌面端已加入 `pack` 和 `dist` 脚本。
- 已关闭证书自动探测和自动发布。
- 已关闭 Windows 可执行文件资源编辑。
- `npm run smoke` 通过。
- `npm run stage5:package-plan` 通过。
- `npm run stage5:preflight` 通过。

## 当前失败现象

运行：

```powershell
cd E:\搜索插件\apps\desktop
npm run pack
```

已观察到以下失败：

- `read ECONNRESET`
- `connect ETIMEDOUT 20.205.243.166:443`
- 命令长时间无响应直到超时

这些错误发生在 electron-builder 的 packaging 阶段，通常和访问 GitHub 资源或下载构建辅助文件有关。

## 重试前检查

先确认网络：

```powershell
curl.exe -I https://github.com
```

如果该命令超时或失败，不建议立刻重试打包。

再确认项目检查：

```powershell
cd E:\搜索插件
npm run stage5:package-plan
npm run stage5:preflight
```

## 重试打包

网络稳定后运行：

```powershell
cd E:\搜索插件\apps\desktop
npm run pack
```

通过标准：

- 出现 `dist\win-unpacked` 目录。
- 目录内存在桌面端可执行文件。
- 运行可执行文件后能打开桌面界面。
- API 状态能显示已连接或已自动启动。

## 生成安装包

目录包通过后，再运行：

```powershell
cd E:\搜索插件\apps\desktop
npm run dist
```

通过标准：

- `dist` 下出现 NSIS 安装包。
- 安装后能启动桌面端。
- 卸载不会删除用户主动备份的数据。

## 当前不处理

- 不签名安装包。
- 不配置自动更新。
- 不上传 GitHub Release。
- 不把 FFmpeg 二进制打进安装包。

## 后续建议

如果网络长期不稳定，可以考虑：

- 预先缓存 electron-builder 需要的构建资源。
- 使用公司或家庭网络重新打包。
- 在 CI 或另一台能稳定访问 GitHub 的 Windows 机器上打包。
