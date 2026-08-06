# 阶段2 Mock Provider 截图反查报告

> 日期：2026-08-06
> 范围：阶段2截图反查最小闭环、文件上传、基础鲁棒性测试、批量候选匹配和局部精排
> 边界：继续使用 Mock OCR 与 Mock 视觉向量；未接入真实 OCR/CLIP；未做真实平台登录、真实平台搜索或第三方视频采集。

## 已完成

- 新增 `media_assets` 数据表，保存截图分析结果。
- 新增 `frame_matches` 数据表，保存候选视频匹配结果。
- 新增截图分析核心：格式/大小校验、FFmpeg 读取图片尺寸、生成缩略图、计算 64 位感知哈希、Mock OCR、Mock 视觉向量。
- 新增候选视频匹配核心：FFmpeg 抽帧、逐帧 pHash/Mock embedding 打分、输出最佳时间点、相似度、匹配帧路径和证据。
- 新增局部精排：先用低 fps 粗扫，再围绕最佳时间点用更高 fps 二次抽帧，证据里记录粗扫帧数、精排帧数、候选 Top5。
- 新增批量候选匹配：一次传入多个本地视频路径，成功结果按综合分排序，失败路径单独返回错误，不影响其他候选继续匹配。
- 新增文件上传保存逻辑：上传截图保存到 `.local-data/stage2/uploads`，自动做文件名净化、扩展名校验、空文件校验和 20MB 限制。
- 新增 FastAPI 接口：
  - `POST /api/assets/analyze-image`
  - `POST /api/assets/upload-image`
  - `GET /api/assets/{assetId}`
  - `POST /api/matches/find`
  - `POST /api/matches/batch`
  - `GET /api/matches/{matchId}`
- 桌面端“截图反查”面板新增文件选择器，可以直接上传并分析截图，也保留本地路径分析入口；新增批量候选视频路径输入框，每行一个视频路径。
- 自动化测试使用 FFmpeg 生成自制 `testsrc` 视频和查询帧，不引入第三方版权素材。
- 新增可复跑脚本：`apps/local-api/scripts/stage2_robustness_check.py`。

## 鲁棒性测试

测试样本来自自制 `testsrc` 视频第 1 秒截图，并生成以下变体：

| 变形场景 | 综合分 | pHash 分 | 结果 |
| --- | ---: | ---: | --- |
| compressed | 0.871 | 1.0 | 通过 |
| scaled | 0.875 | 1.0 | 通过 |
| tone | 0.802 | 0.969 | 通过 |
| text | 0.824 | 1.0 | 通过 |
| occlusion | 0.756 | 0.938 | 通过 |

当前通过阈值为 `0.45`。这个阈值只用于 Mock Provider 阶段的流程验证，不能代表真实模型上线后的最终阈值。

## 测试结果

- API 阶段2单元测试：5 个通过。
- FastAPI 上传路由加载检查：通过，已注册 `/api/assets/upload-image`。
- 鲁棒性检查脚本：通过，5 个变形样本全部达到阈值。
- Electron 桌面端冒烟：通过，API 状态为 ready。

## 未完成

- OCR 仍为 Mock Provider，未接入 PaddleOCR 或其他真实 OCR。
- 视觉向量仍为 Mock Provider，未接入 CLIP 或其他真实 embedding 模型。
- 阈值 UI 尚未完成，当前仍在请求里使用默认阈值。
- 上传接口目前只处理单张截图，尚未支持批量上传、拖拽上传或剪贴板粘贴。

## 已知风险

- Mock OCR 和 Mock embedding 只能验证接口与流程，不能代表真实识别准确率。
- 当前 pHash 使用 FFmpeg 缩放为 8x8 灰度平均哈希，对裁剪、遮挡、字幕变化的鲁棒性有限。
- 当前匹配分数权重和精排窗口是阶段2临时实现，进入真实 Provider 前需要配置化。
- 真实截图通常会有播放器控件、水印、压缩噪声、平台 UI 遮挡，后续需要加入更接近真实场景的自制样本。

## 下一步建议

- 继续补阈值 UI、匹配结果收藏到项目、以及 Top 候选结果的人工确认入口。
- 在接入真实 OCR Provider 前，先确认依赖体积、许可证、本机性能和离线可用性。
- 补桌面端拖拽上传、剪贴板截图粘贴和错误提示优化。
