# 阶段6真实搜索候选源接入说明

> 日期：2026-08-13  
> 范围：小红书和抖音真实搜索候选源桥接、语义匹配度评分、桌面端结果展示。  
> 结论：已接入小红书/抖音 CLI 桥接层；本项目不内置第三方爬虫代码，不接下载、点赞、评论、发布或绕登录能力。

## 当前能力

- 桌面端搜索区新增“小红书真实候选”和“抖音真实候选”勾选项。
- 后端新增 `xiaohongshu` 和 `douyin` 平台适配器。
- 适配器通过本机 CLI 命令读取公开视频搜索 JSON 输出。
- 默认会优先识别仓库 `.venv\Scripts` 里的 CLI，也支持系统 PATH 中的同名命令。
- 搜索结果会统一保存为标题、链接、作者、描述、封面、标签和发布时间。
- 每条结果会给出 `semantic_match_percent` 匹配度和 `semantic_match_reasons` 匹配理由。
- CSV / Markdown 导出会带上匹配度和匹配理由。

## 使用前提

小红书默认命令：

```powershell
xhs search "{query}" --type video --json
```

抖音默认命令：

```powershell
dy search "{query}" --type video --count {limit} --json-output
```

如果你安装的开源工具命令不一样，可以设置环境变量覆盖：

```powershell
$env:VMF_XHS_SEARCH_COMMAND = 'xhs search "{query}" --type video --json'
$env:VMF_DOUYIN_SEARCH_COMMAND = 'dy search "{query}" --type video --count {limit} --json-output'
$env:VMF_SEARCH_CLI_HOME = '候选源登录和缓存目录'
```

其中：

- `{query}` 会替换为当前搜索词。
- `{limit}` 会替换为每个平台最大返回数量。
- `VMF_SEARCH_CLI_HOME` 用来指定小红书/抖音 CLI 保存登录态和缓存的位置；不设置时会使用本机应用数据目录。

注意：`stage6:check-sources` 只能确认命令是否存在。真实搜索还需要平台登录态、正常网络和平台页面可访问；如果未登录或被网络/风控拦截，桌面端会显示明确状态提示。

## 登录授权引导

桌面端候选源状态区会显示小红书和抖音的登录引导，并提供一键复制命令。

小红书常用方式：

```powershell
xhs login --cookie-source chrome --json
```

如果浏览器不是 Chrome，可以把 `chrome` 换成 `edge`，或使用扫码方式：

```powershell
xhs login --qrcode
```

抖音常用方式：

```powershell
dy login --browser
```

建议步骤：

- 先用浏览器打开对应平台官网，并确认账号已经登录。
- 回到项目终端运行复制出来的登录命令。
- 登录命令成功后，回到桌面端重新搜索。
- 如果仍然失败，优先检查网络、防火墙、代理和平台风控提示。

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
- 登录态由外部 CLI 按自己的方式管理，本项目只给 CLI 一个可写运行目录，不读取密码。

## 验收方式

```powershell
cd E:\搜索插件
npm run stage6:check-sources
npm run test:api
```

`stage6:check-sources` 会检查当前机器是否能找到 `xhs` 和 `dy` 命令。
`test:api` 会模拟小红书/抖音 CLI JSON 输出，验证：

- JSON 可解析。
- 链接、标题、作者可归一化。
- 抖音 `aweme_id` 可生成视频链接。
- 匹配度和匹配理由会写入 `raw_metadata_json`。
