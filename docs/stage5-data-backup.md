# 阶段5数据备份与恢复说明

> 日期：2026-08-12  
> 范围：本地素材库 `.local-data` 的备份、恢复和迁移说明。  
> 边界：只处理本地数据目录，不上传云端，不读取密码、Cookie、Token 或登录态。

## 数据位置

当前本地素材库位于：

```text
E:\搜索插件\.local-data
```

主要包含：

- `video-material-finder.sqlite`：本地 SQLite 数据库。
- `stage2/`：截图反查、缩略图、抽帧等本地生成素材。

该目录已被 `.gitignore` 忽略，不会提交到 GitHub。

## 创建备份

```powershell
cd E:\搜索插件
npm run stage5:backup-data
```

备份会输出到：

```text
E:\搜索插件\backups
```

文件名格式：

```text
video-material-finder-data-YYYYMMDD-HHMMSS.zip
```

如果桌面端或本地 API 正在运行，脚本会用 SQLite 在线备份方式复制数据库，避免直接压缩正在使用的数据库文件失败。
本地素材较多时，压缩可能需要一两分钟。

## 恢复备份

```powershell
cd E:\搜索插件
npm run stage5:restore-data -- "E:\搜索插件\backups\video-material-finder-data-YYYYMMDD-HHMMSS.zip"
```

恢复前，脚本会先把当前 `.local-data` 再备份一次，文件名格式：

```text
before-restore-YYYYMMDD-HHMMSS.zip
```

这样即使恢复错了，也还有一次回退机会。
恢复前的安全备份同样使用 SQLite 在线备份方式复制数据库。

## 迁移到新电脑

1. 在旧电脑运行 `npm run stage5:backup-data`。
2. 把生成的 zip 复制到新电脑。
3. 在新电脑安装项目依赖和 FFmpeg。
4. 在新电脑运行 `npm run stage5:restore-data -- "备份zip路径"`。
5. 启动桌面端，确认项目和素材能正常显示。

## 注意事项

- 恢复前建议先关闭桌面端和本地 API，避免覆盖正在使用的 SQLite 文件。
- 备份 zip 可能包含用户本地素材路径、截图和项目备注，不建议公开分享。
- 备份目录 `backups/` 已被 `.gitignore` 忽略，避免误提交。
- 如果未来安装包使用用户目录存储数据，需要同步更新本说明。
