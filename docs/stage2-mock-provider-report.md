# 阶段2 Mock Provider 截图反查报告

> 日期：2026-08-06  
> 范围：阶段2 截图反查最小闭环  
> 边界：使用 Mock OCR 与 Mock 视觉向量；未接入真实 OCR/CLIP；未做真实平台登录、真实平台搜索或第三方视频采集。

## 已完成

- 新增 `media_assets` 数据表，保存截图分析结果。
- 新增 `frame_matches` 数据表，保存候选视频匹配结果。
- 新增截图分析核心：格式/大小校验、FFmpeg 读取图片尺寸、生成缩略图、计算 64 位感知哈希、Mock OCR、Mock 视觉向量。
- 新增候选视频匹配核心：FFmpeg 抽帧、逐帧 pHash/Mock embedding 打分、输出最佳时间点、相似度、匹配帧路径和证据。
- 新增 FastAPI 接口：
  - `POST /api/assets/analyze-image`
  - `GET /api/assets/{assetId}`
  - `POST /api/matches/find`
  - `GET /api/matches/{matchId}`
- 标准库备用 HTTP 服务同步补齐上述接口。
- 桌面端新增“截图反查”面板，可填写本地截图路径和候选视频路径，触发分析和匹配。
- 自动化测试使用 FFmpeg 生成自制 testsrc 视频和查询帧，不引入第三方版权素材。

## 未完成

- OCR 仍为 Mock Provider，未接入 PaddleOCR 或其他真实 OCR。
- 视觉向量仍为 Mock Provider，未接入 CLIP 或其他真实 embedding 模型。
- 当前接口接收本地文件路径，尚未实现 multipart 文件上传。
- 当前只验证单候选视频匹配，尚未做批量候选、密集抽帧二次精排和阈值 UI。

## 测试结果

- API 单元测试：4 个通过。
- Node 单元测试：6 个通过。
- 阶段2接口烟测：通过。
- 烟测样本：自制 `testsrc` 视频，查询帧来自该视频 1 秒处。
- 烟测结果：`match_type=same_frame`，`combined_score=1.0`，`timestamp_ms=1000`，匹配帧文件存在。

## 已知风险

- Mock OCR 和 Mock embedding 只能验证接口与流程，不能代表真实识别准确率。
- 当前 pHash 使用 FFmpeg 缩放为 8x8 灰度的平均哈希，对裁剪、遮挡、字幕变化的鲁棒性有限。
- 当前匹配分数权重是阶段2临时实现，进入真实 Provider 前需要配置化。
- Windows 中文路径通过 PowerShell JSON 传输时可能出现编码问题；Python UTF-8 客户端烟测正常。

## 下一步建议

- 阶段2继续补 multipart 上传，让桌面端不必手填绝对路径。
- 接入一个真实 OCR Provider 前，先确认依赖体积、许可证和本机性能。
- 引入更接近真实截图的自制测试素材：压缩、裁剪、轻度调色、加字幕、局部遮挡。
- 再做批量候选视频匹配和更密集的局部时间段精排。
