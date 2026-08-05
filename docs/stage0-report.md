# 阶段0执行报告

> 日期：2026-08-05  
> 项目根目录：`E:\搜索插件`  
> 阶段边界：只执行“阶段0：仓库与技术验证”，未开发完整 UI，未创建远程仓库，未推送 GitHub，未进入阶段1。

## 已完成

- 已初始化本地 Git 仓库。
- 已保留项目根目录 PRD：`全网视频素材智能搜索插件_PRD.md`。
- 已建立最小 Monorepo 骨架：`apps/`、`packages/`、`services/`、`tests/`、`docs/`、`scripts/`、`LICENSES/`。
- 已编写阶段0技术方案：`docs/architecture-stage0.md`。
- 已编写依赖许可证审查清单：`docs/license-review.md`。
- 已编写风险清单：`docs/risk-register.md`。
- 已实现最小验证代码：
  - FFmpeg/ffprobe 可用性检测
  - FFmpeg 生成测试视频并抽取单帧
  - 感知哈希最小验证
  - OCR Mock Provider
  - 视觉向量 Mock Provider
  - 公开网页搜索录制样本适配器
- 已编写自动化测试。

## 未完成

- 真实 OCR 未安装，阶段0只验证了 Provider 接口和 Mock 返回格式。
- 真实视觉向量模型未下载，阶段0只验证了 Provider 接口和 Mock 向量流程。
- 真实联网平台搜索未执行，阶段0使用录制 HTML 样本验证适配器归一化，避免高频访问真实平台。

## 测试结果

### 自动化测试

命令：`node --test tests/unit/*.test.mjs`

结果：6 个测试全部通过。

- OCR Mock Provider：通过
- 感知哈希相似图：通过
- 感知哈希差异图：通过
- URL 标准化：通过
- 视觉向量 Mock Provider：通过
- 公开网页搜索录制样本适配器：通过

### 阶段0检查

命令：临时加入 FFmpeg 路径后执行：

```powershell
$env:Path = 'E:\tools\ffmpeg\ffmpeg-9.0-essentials_build\ffmpeg-9.0-essentials_build\bin;' + $env:Path
node scripts/stage0/run-stage0-checks.mjs
```

结果：全部通过。

| 检查项 | 结果 | 说明 |
|---|---|---|
| ffmpeg | 通过 | ffmpeg version 9.0-essentials_build-www.gyan.dev |
| ffprobe | 通过 | ffprobe version 9.0-essentials_build-www.gyan.dev |
| ffmpeg_frame_extraction | 通过 | 已生成测试视频并抽取 `stage0-artifacts/ffmpeg-smoke/frame-001.png` |
| perceptual_hash_similar_image | 通过 | similarity=1.000 |
| perceptual_hash_different_image | 通过 | similarity=0.750 |
| ocr_provider_mock | 通过 | 返回文本包含“旧空调” |
| visual_embedding_mock | 通过 | 16维向量，自相似度 1.000 |
| recorded_web_search_adapter | 通过 | 从录制样本归一化 2 条结果 |

## 阻塞项

- 当前 Codex 旧会话可能仍未刷新系统 PATH；但用户已在新开的 Windows 命令行中验证 `ffmpeg -version` 可直接运行。阶段0脚本使用同一 FFmpeg 发行包路径完成真实抽帧验证。

## 已知风险

- 当前下载的 gyan.dev essentials build 配置里包含 `--enable-gpl` 和 `--enable-version3`。本地技术验证可以使用，但未来如果要随产品分发 FFmpeg，需要认真处理 GPL 义务，或选择/自建符合产品分发策略的 LGPL 构建。
- OCR 和视觉向量真实模型会引入较重依赖、模型体积、首次下载时间和许可证链条，需要单独审批。
- OpenCV wheel 可能包含 FFmpeg 等第三方二进制组件，后续进入产品前必须审查 `LICENSE-3RD-PARTY.txt`。
- 平台页面搜索适配器长期存在页面结构变化风险，需要录制样本测试和清晰错误提示。

## 下一阶段建议

阶段0的本地技术验证已通过。用户已在新开的 Windows 命令行中执行 `ffmpeg -version`，确认系统 PATH 可直接识别 FFmpeg。未经明确同意，不进入阶段1。

