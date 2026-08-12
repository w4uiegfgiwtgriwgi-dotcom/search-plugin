# 阶段5 Windows 打包方案

> 日期：2026-08-12  
> 范围：Windows 安装包方案、打包依赖、FFmpeg 分发策略和下一步执行条件。  
> 结论：当前先完成打包方案和准备检查，尚未联网安装打包依赖，也尚未生成安装包。

## 推荐打包工具

推荐使用 `electron-builder` 作为 Windows 打包工具。

原因：

- 支持 Windows `nsis` 安装包和免安装目录包。
- Electron 项目常用，文档和社区案例较多。
- 可以先做本地安装包，再逐步补自动更新。

当前状态：

- `electron-builder` 尚未安装。
- `apps/desktop/package.json` 尚未加入正式 `dist` 脚本。
- 需要用户确认后，才能联网安装打包依赖并更新 lock 文件。

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

## 下一步需要授权

如果要真正进入安装包打包，需要先获得明确确认，然后执行：

```powershell
cd E:\搜索插件\apps\desktop
npm install --save-dev electron-builder
```

安装完成后再补：

- `apps/desktop/package.json` 的 `build` 配置。
- `apps/desktop/package.json` 的 `dist` 脚本。
- 打包输出目录说明。
- Windows 安装包冒烟检查。

## 当前不做

- 不签名安装包。
- 不配置自动更新。
- 不把 FFmpeg 二进制随包分发。
- 不上传 release。
- 不改变 GitHub 发布设置。
