# 阶段0依赖许可证审查清单

> 日期：2026-08-05  
> 结论只针对阶段0候选依赖，不代表已经安装或进入产品。

| 依赖 | 用途 | 许可证 | 维护状态观察 | 阶段0结论 | 来源 |
|---|---|---|---|---|---|
| Electron | Windows 桌面应用壳 | MIT | GitHub 组织活跃，electron/electron 近期仍更新 | 可作为阶段1候选，阶段0不安装 | https://github.com/electron |
| React | 桌面端 UI | MIT | 生态成熟，仓库活跃 | 可作为阶段1候选 | https://github.com/facebook/react |
| Ant Design | UI 组件 | MIT | 生态成熟，需后续确认每个子包许可证 | 可作为 UI 候选之一 | https://github.com/ant-design/ant-design |
| Zustand | 前端状态管理 | MIT | 近期仍更新 | 可作为轻量状态管理候选 | https://github.com/pmndrs/zustand |
| FastAPI | 本地 API | MIT | 2026 年仍有发布和维护 | 可作为本地 API 候选 | https://github.com/fastapi/fastapi |
| SQLAlchemy | ORM/数据库工具 | MIT | 2026 年仍有发布 | 可作为 SQLite 数据层候选 | https://github.com/sqlalchemy/sqlalchemy |
| Alembic | 数据库迁移 | MIT | SQLAlchemy 项目下维护 | 可作为迁移工具候选 | https://github.com/sqlalchemy/alembic |
| Playwright | 可见浏览器流程与 E2E | Apache-2.0 | 2026 年仍频繁发布 | 可作为测试和用户授权浏览器流程候选 | https://github.com/microsoft/playwright |
| FFmpeg | 视频探测与抽帧 | LGPL/GPL 取决于构建参数 | 当前本机验证使用 gyan.dev `9.0-essentials_build`，其配置包含 `--enable-gpl` 与 `--enable-version3` | 阶段0本地验证可用；未来随产品分发前必须决定 GPL 合规方案或选用合适 LGPL 构建 | https://ffmpeg.org/legal.html |
| Pillow | 图片处理 | MIT-CMU | 维护活跃；注意安全公告和版本固定 | 可作为图片处理候选，需跟进 CVE | https://github.com/python-pillow/Pillow |
| OpenCV / opencv-python | 视觉处理 | OpenCV 4.5+ Apache-2.0；opencv-python 打包脚本 MIT；wheel 可能含 FFmpeg LGPLv2.1 | 维护活跃；二进制 wheel 带第三方组件 | 可作为候选，但打包前必须审查 wheel 第三方许可证 | https://github.com/opencv/opencv-python |
| imagehash | 感知哈希 | BSD-2-Clause | 最近 release 较旧，但功能稳定 | 可作为候选；也可保留独立实现作为备用 | https://github.com/JohannesBuchner/imagehash |
| PaddleOCR | OCR | Apache-2.0 | 活跃，支持多语言；安装较重 | 可作为真实 OCR 候选，阶段0先用 Mock Provider | https://github.com/PaddlePaddle/PaddleOCR |
| openai-whisper | 本地 ASR | MIT | 需要 FFmpeg 和模型文件；模型体积较大 | 可作为 ASR 候选，阶段0只预留 Mock | https://github.com/openai/whisper |
| FAISS | 向量索引 | MIT | 2026 年仍有发布 | 可作为本地向量索引候选，阶段0不安装 | https://github.com/facebookresearch/faiss |

## 禁止项

- 禁止复制非商业许可证代码进入项目。
- 禁止复制无明确许可证仓库代码进入项目。
- FFmpeg、OpenCV wheel、模型权重和素材数据需要逐项保留许可证说明。

## 阶段0审查结论

当前没有安装第三方 npm/pip 依赖，也没有复制第三方仓库代码。阶段0代码只使用 Node.js 内置模块和本地自写 Mock/验证逻辑。FFmpeg 仅作为本机外部程序进行技术验证，未提交二进制文件到仓库。
