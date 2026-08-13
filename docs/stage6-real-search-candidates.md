# 阶段6真实搜索候选源接入说明

> 日期：2026-08-13  
> 范围：小红书和抖音真实搜索候选源桥接、语义匹配度评分、桌面端结果展示。  
> 结论：已接入小红书/抖音 CLI 桥接层；本项目不内置第三方爬虫代码，不接下载、点赞、评论、发布或绕登录能力。

## 当前能力

- 桌面端搜索区新增“小红书真实候选”和“抖音真实候选”勾选项。
- 后端新增 `xiaohongshu` 和 `douyin` 平台适配器。
- 适配器通过本机 CLI 命令读取公开视频搜索 JSON 输出。
- 搜索结果会统一保存为标题、链接、作者、描述、封面、标签和发布时间。
- 每条结果会给出 `semantic_match_percent` 匹配度和 `semantic_match_reasons` 匹配理由。
- CSV / Markdown 导出会带上匹配度和匹配理由。

## 使用前提

小红书默认命令：

```powershell
xhs search {query} --json --limit {limit}
```

抖音默认命令：

```powershell
dy search {query} --json --limit {limit}
```

如果你安装的开源工具命令不一样，可以设置环境变量覆盖：

```powershell
$env:VMF_XHS_SEARCH_COMMAND = "xhs search {query} --json --limit {limit}"
$env:VMF_DOUYIN_SEARCH_COMMAND = "dy search {query} --json --limit {limit}"
```

其中：

- `{query}` 会替换为当前搜索词。
- `{limit}` 会替换为每个平台最大返回数量。

## 匹配度说明

当前匹配度基于公开元数据：

- 标题
- 描述
- 标签
- 作者
- 封面是否存在
- 视频时长是否存在

当前不等同于真实画面识别。没有字幕、关键帧或真实视觉模型时，只能说明“公开视频元数据和你的描述有多接近”。

## 安全边界

- 不保存平台密码、Cookie、Token 或登录态。
- 不实现验证码绕过、代理证书拦截、风控规避或加密视频解密。
- 不自动点赞、收藏、评论、关注、私信或发布。
- 不提供无水印下载能力。
- 不把第三方开源爬虫代码复制进仓库，只通过用户本机已安装 CLI 做桥接。

## 验收方式

```powershell
cd E:\搜索插件
npm run test:api
```

阶段6测试会模拟小红书/抖音 CLI JSON 输出，验证：

- JSON 可解析。
- 链接、标题、作者可归一化。
- 抖音 `aweme_id` 可生成视频链接。
- 匹配度和匹配理由会写入 `raw_metadata_json`。
