# 阶段0技术方案

## 技术方向

- 桌面端：Electron + React + TypeScript，阶段0只保留目录，不开发 UI。
- 本地服务：Python 3.11+ + FastAPI，阶段0先确认本机 Python 可用性与接口边界。
- 浏览器扩展：Chrome Manifest V3，阶段0只保留目录。
- 平台适配器：所有平台通过独立 Adapter 接口声明能力、会话状态、搜索、翻页、归一化和取消。
- AI 能力：OCR、ASR、视觉向量全部通过 Provider 接口接入，阶段0优先 Mock，真实模型进入前单独评估体积、速度、许可证与安装成本。
- 数据：SQLite + SQLAlchemy/Alembic 作为阶段1以后候选，阶段0只做许可证审查。

## 阶段0验证策略

1. 用本地脚本检测 FFmpeg/ffprobe 是否可执行。
2. 用本地生成的文本图片矩阵验证感知哈希流程。
3. 用 Mock OCR Provider 验证接口、返回格式和测试可控性。
4. 用 Mock Visual Embedding Provider 验证向量维度、归一化和相似度计算。
5. 用录制 HTML 样本验证公开网页搜索适配器解析和归一化，避免 CI 或本机验证频繁访问真实平台。

## 不做的事情

- 不开发完整 UI。
- 不接入真实登录态。
- 不下载或提交第三方完整视频素材。
- 不绕过验证码、DRM 或平台访问控制。
- 不创建 GitHub 远程仓库，不推送。
