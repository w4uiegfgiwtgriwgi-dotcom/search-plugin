# 阶段5生产化准备报告

> 日期：2026-08-12  
> 范围：Windows 打包前预检、环境依赖、数据目录、许可证风险和阶段5执行顺序。  
> 结论：阶段5生产化准备已完成；Windows 目录包、NSIS 安装包、安装版冒烟和卸载验收均已通过。

## 当前生产化状态

- 桌面端：Electron 已可启动，并能自动连接或拉起本地 API。
- 本地 API：FastAPI + SQLite 已通过阶段4检查。
- 浏览器扩展：Chrome MV3 扩展已完成阶段3验收。
- 视频号半自动：桌面端入口、搜索计划、手动链接保存和阶段4验收已完成。
- 数据目录：本地数据位于 `.local-data`，已被 `.gitignore` 忽略。
- 依赖目录：`.venv`、`node_modules`、构建产物和本地测试素材已被 `.gitignore` 忽略。

## 新增预检命令

```powershell
cd E:\搜索插件
npm run stage5:preflight
```

该命令会检查：

- 阶段4基线检查是否通过。
- 桌面端主进程、API 拉起脚本和依赖配置是否存在。
- 本地 API 依赖锁定文件是否存在。
- 许可证审查文档是否存在。
- FFmpeg 是否可在当前系统 PATH 中调用。
- Python 虚拟环境是否可用。
- Electron 依赖是否已安装。
- Node、npm、本地 API 端口、运行目录和 `.gitignore` 安全项是否正常。

## 新增运行环境检查

```powershell
cd E:\搜索插件
npm run stage5:runtime-check
```

该命令会检查：

- Node 和 npm 是否可用。
- Python 虚拟环境是否可用。
- FFmpeg 是否可用。
- 本地 API 端口 `17860` 当前是空闲还是已有服务。
- `.local-data`、桌面端依赖和本地 API 目录是否存在。
- `.gitignore` 是否继续忽略本地数据、虚拟环境、依赖目录和 SQLite 数据库。

## 打包前必须处理

- 已新增 Windows 打包方案：`docs/stage5-windows-package-plan.md`。
- 已新增打包方案检查：`npm run stage5:package-plan`。
- 已新增数据备份与恢复说明：`docs/stage5-data-backup.md`。
- 已新增本地数据备份命令：`npm run stage5:backup-data`。
- 已新增本地数据恢复命令：`npm run stage5:restore-data -- "备份zip路径"`。
- 已新增安全审查与许可证复核：`docs/stage5-security-license-review.md`。
- 已新增最终用户使用说明：`docs/user-guide.md`。
- 已安装 `electron-builder` 并新增桌面端 `pack` / `dist` 脚本。
- 当前打包配置不包含 `.local-data`、`backups` 或 FFmpeg 二进制。
- 已把本地 API 源码、启动脚本和 Python 虚拟环境随桌面端安装包提供。
- 当前 `npm run pack` 已成功生成目录包。
- 当前 `npm run dist` 已成功生成 Windows NSIS 安装包。
- 打包后目录包冒烟已通过，输出 `electron smoke api status: ready`。
- 安装包静默安装、安装版冒烟和静默卸载均已通过。
- 已新增打包诊断与重试说明：`docs/stage5-package-troubleshooting.md`。
- 已新增阶段5最终验收报告：`docs/stage5-acceptance-report.md`。
- 尚未决定 FFmpeg 是否随安装包分发；当前本机 FFmpeg 为外部依赖。
- 如果未来随包分发 FFmpeg，必须重新确认 GPL/LGPL 构建和分发义务。
- 尚未设计自动更新策略。

## 安全边界

- 不保存密码、Cookie、Token 或登录态。
- 不实现验证码绕过、代理证书拦截、DRM 破解或加密视频解密。
- 不自动发布、评论、点赞、关注或私信。
- 不使用真实账号进行无人值守高频测试。
- 当前 OCR 和视觉向量仍是 Mock Provider，不宣称真实模型识别准确率。

## 阶段5建议顺序

1. 根据需要补安装包签名、图标和第三方依赖许可证清单。
2. 根据需要配置自动更新和发布渠道。
3. 根据需要接入真实 OCR / 真实视觉向量 / 真实平台 API。
