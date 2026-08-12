# 阶段5 Windows 打包方案

> 日期：2026-08-12  
> 范围：Windows 安装包方案、打包依赖、FFmpeg 分发策略和下一步执行条件。  
> 结论：已安装 `electron-builder` 并加入保守的 Windows 打包配置；当前先验证目录包，再生成安装包。

## 推荐打包工具

推荐使用 `electron-builder` 作为 Windows 打包工具。

原因：

- 支持 Windows `nsis` 安装包和免安装目录包。
- Electron 项目常用，文档和社区案例较多。
- 可以先做本地安装包，再逐步补自动更新。

当前状态：

- `electron-builder` 已安装到桌面端开发依赖。
- `apps/desktop/package.json` 已加入 `pack` 和 `dist` 脚本，并关闭证书自动探测、自动发布和 Windows 可执行文件资源编辑。
- 打包配置只包含桌面端入口、预加载脚本、API 拉起脚本、静态 UI 和桌面端 `package.json`。
- 当前不会把 `.venv`、`.local-data`、`backups`、FFmpeg 二进制或根目录测试素材打进安装包。

## 推荐打包产物

第一版建议先生成：

- Windows x64 目录包，便于本机冒烟。
- Windows NSIS 安装包，便于普通用户安装。

暂不建议第一步就做自动更新。自动更新会牵涉签名、发布渠道、版本策略和回滚策略，建议安装包稳定后再补。

## FFmpeg 分发策略

当前建议先采用“外部依赖提示”：

- 不把 FFmpeg 二进制文件直接打进安装包。
- 启动前检查系统 PATH 是否能调用 `ffmpeg`。
- 如果找不到 FFmpeg，提示用户安装并加入 PATH。

原因：

- 当前本机 FFmpeg 为 gyan.dev `essentials_build`，配置包含 GPL/version3 选项。
- 如果随安装包分发，需要重新确认 GPL/LGPL 构建、源码提供和许可证义务。
- 外部依赖提示更适合当前 MVP 阶段。

## 打包前检查

```powershell
cd E:\搜索插件
npm run stage5:package-plan
```

该命令只检查打包方案前置文件，不会生成安装包。

## 打包命令

生成 Windows 目录包：

```powershell
cd E:\搜索插件\apps\desktop
npm run pack
```

生成 Windows NSIS 安装包：

```powershell
cd E:\搜索插件\apps\desktop
npm run dist
```

打包输出目录：

```text
E:\搜索插件\apps\desktop\dist
```

## 当前打包验证结果

已完成：

- `electron-builder` 安装成功。
- `npm run smoke` 通过，桌面端仍能启动并连接本地 API。
- `npm run stage5:package-plan` 通过，打包方案检查能识别 `electron-builder` 已安装。

尚未完成：

- `npm run pack` 尚未成功生成 `dist\win-unpacked`。

已观察到的问题：

- 第一次打包失败：`electron` 依赖需要移到 `devDependencies`，已修复。
- 后续打包进入 `packaging` 阶段后，访问 GitHub 资源时出现 `ECONNRESET` / `ETIMEDOUT`。
- 关闭证书自动探测、自动发布和 Windows 可执行文件资源编辑后，打包仍可能超时。

当前判断：

- 打包配置已接入。
- 安装包产物尚未验证通过。
- 需要网络稳定后重新运行 `npm run pack`，再进入 `npm run dist`。

## 当前不做

- 不签名安装包。
- 不配置自动更新。
- 不把 FFmpeg 二进制随包分发。
- 不上传 release。
- 不改变 GitHub 发布设置。
