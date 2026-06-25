---
name: mp-draft-push
description: 将现成的文章内容发布到微信公众号草稿箱。当用户说"发布文章"、"发布到草稿箱"、"publish to draft"、"推送到公众号"时触发。
metadata: {"emoji":"📤","requires":{"bins":["bash","curl","jq"]}}}
---

# mp-draft-push

## 功能说明

接收调用方提供的文章内容，上传封面图（可选），并将文章发布到微信公众号草稿箱。

**不负责**：内容采集、AI 写作、图片生成。

> 📖 **Proxy Configuration**: See `references/proxy-configuration.md` for WeChat API proxy setup and troubleshooting.
> 📖 **Scripts Location**: See `references/scripts-location.md` for scripts.sh file location and usage.

## wx-publish-gateway 配置（必需，优先）

家宽 IP 会变，旧的 `PROXY_URL` 方案容易再次触发微信 `40164 invalid ip ... not in whitelist`。现在默认优先使用部署在固定出口 IP 服务器上的 `wx-publish-gateway`。

**快速配置（写入 .env 文件）：**
```bash
WXPG_GATEWAY_URL="http://<你的固定IP或内网地址>:<端口>"
WXPG_API_KEY="<网关 API Key>"
WXPG_ACCOUNT="main"   # 可选；不填则使用网关默认账号
```

**执行规则：**
- 配置了 `WXPG_GATEWAY_URL + WXPG_API_KEY`：`scripts.sh` 会调用 `/v1/media/cover`、`/v1/media/inline`、`/v1/draft`。
- 不直接调用 `/v1/token`；token 只应由网关内部管理，不在本地脚本间传递。
- 未配置网关时，才 fallback 到旧的 `WECHAT_APPID/WECHAT_SECRET + PROXY_URL` 直连模式。

详见 `references/proxy-configuration.md`。

---

## 所需参数

调用方（用户或其他 Skill）需要提供：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 文章标题（不超过 64 字节，约 21 个中文字符） |
| `digest` | string | ✅ | 文章摘要（显示在分享卡片上） |
| `content_html` | string | ✅ | 文章正文 HTML（使用内联样式） |
| `cover_image_path` | string | ❌ | 封面图本地路径（如不提供则用兜底 URL 或无封面） |


---

## 执行流程

```
1. 接收参数
       ↓
2. 排版 + 初始化网关调用上下文（网关模式返回哨兵值）
       ↓
3. 上传封面图到微信素材库（获取 thumb_media_id）
       ↓
4. 上传文章内图片到微信（获取 mmbiz.qpic.cn URL，替换 content_html 中的本地路径）
       ↓
5. 构建草稿 JSON 并创建草稿
       ↓
6. 提示用户前往后台检查
```

---

## Step 1: 环境准备

- **AppID**: `WECHAT_APPID`（通过环境变量配置）
- **AppSecret**: `WECHAT_SECRET`（通过环境变量配置）
- **作者**: `WECHAT_AUTHOR`（可选，默认 `koo AI`）

**获取 AppID 和 AppSecret**：
1. 前往 [微信开发者平台](https://developers.weixin.qq.com/platform/)，微信扫码登录
2. 点击 [「我的业务 → 公众号/服务号」](https://developers.weixin.qq.com/platform/apps/subscription)，进入对应账号详情页
3. 在详情页即可查看 AppID 和 AppSecret（也可在此重置）

> ⚠️ 平台**不保存** AppSecret，需自行妥善保管。忘记只能重置生成新的。
> 若提示需要实名/认证，前往 [微信公众平台 → 设置与开发](https://mp.weixin.qq.com) 完成认证。

---

## Step 2: 接收参数

等待调用方传入上述参数。

若调用方没有提供 `cover_image_path`，按以下优先级处理封面图：
1. **优先使用 `gen_image` 工具生成封面图**：根据文章标题和主题，调用 `gen_image` 生成一张适合公众号封面的图片（建议尺寸 900×383 或 2.35:1 比例，风格简洁醒目），保存到 `/tmp/wechat_cover_generated.png`，然后作为封面上传
2. **Python Pillow 兜底**：若 `gen_image` 不可用或超时，用 Python Pillow 生成一张简单的纯色+文字封面。示例模板见 `references/cover-fallback-recipe.md`。
3. 若 Pillow 也不可用，检查环境变量 `DEFAULT_COVER_URL`：有值则下载到 `/tmp/wechat_cover_default.png` 再上传
4. 以上均不可用：`thumb_media_id` 留空（草稿不含封面）

---

## Step 3: 上传封面图并创建草稿

### 排版规范（强制）

**所有公众号文章必须应用排版规范后再发布。** 使用排版脚本自动转换：

```bash
python3 ./scripts/md_to_wechat_html.py input.md output.html
```

**排版规范：**
| 项目 | 数值 |
|:-----|:-----|
| 正文字号 | **15px** |
| 行间距 | **1.75倍** |
| 字间距 | **1.5px** |
| 页边距 | **10px** |
| 正文颜色 | **#3f3f3f** |
| 标注颜色 | **#888888** |
| 标题字号 | **22px** |
| 配图宽度 | **640px** |

**排版原则：**
- 两端对齐
- 每段3-5行
- 重点用**加粗+颜色**突出
- 分隔符每文2-3次（使用 `· · ·`）
- 结尾互动引导使用灰色背景框

### 加载脚本

```bash
source ./scripts.sh
```

### 初始化调用上下文

```bash
TOKEN=$(get_wechat_token)
```

> 在 `wx-publish-gateway` 模式下，`TOKEN` 是哨兵值 `__WXPG_GATEWAY__`，不是微信真实 access_token。后续 `upload_wechat_image` / `upload_inline_image` / `create_draft` 会忽略该参数并直接调用网关。
> 只有未配置 `WXPG_GATEWAY_URL + WXPG_API_KEY` 时，才会 fallback 到旧的 `WECHAT_APPID/WECHAT_SECRET` 直连模式。

### 上传封面图（如有）

```bash
MEDIA_RESPONSE=$(upload_wechat_image "$TOKEN" "$cover_image_path")
THUMB_MEDIA_ID=$(echo "$MEDIA_RESPONSE" | jq -r '.media_id')
```

### 上传文章内图片（如有）

如果文章有内嵌图片，在构建草稿 JSON 之前，需要先上传每张图片到微信获取 mmbiz.qpic.cn URL。

```bash
INLINE_RESP=$(upload_inline_image "$TOKEN" "$inline_image_path")
INLINE_URL=$(echo "$INLINE_RESP" | jq -r '.url')

# 替换 content_html 中的本地路径
content_html="${content_html//\/path\/to\/local\/image/$INLINE_URL}"
```

### 构建草稿 JSON 并创建草稿

**重要（2026-06-17更新）**：wx-publish-gateway 的 `/v1/draft` 端点期望**扁平字段**，不是嵌套的 `articles[0]` 结构。

**正确写法**（扁平字段，直接传给网关）：
```python
import json

draft = {
    "title": "文章标题",
    "author": "夜航",
    "digest": "文章摘要...",
    "content_html": content_html,  # 已排版的HTML字符串
    "thumb_media_id": thumb_media_id,
    "need_open_comment": 1,
    "only_fans_can_comment": 0
}

with open('/tmp/draft.json', 'w', encoding='utf-8') as f:
    json.dump(draft, f, ensure_ascii=False, indent=2)
```

**错误写法**（嵌套结构，网关会报 `missing title/content_html/thumb_media_id`）：
```python
# ❌ 不要这样写
{
    "articles": [{
        "title": "...",
        "content": "...",
        "thumb_media_id": "..."
    }]
}
```

**关键字段映射**：
| 网关字段 | 对应微信API字段 | 说明 |
|:---------|:----------------|:-----|
| `title` | `articles[0].title` | 文章标题（必填） |
| `author` | `articles[0].author` | 作者名 |
| `digest` | `articles[0].digest` | 摘要 |
| `content_html` | `articles[0].content` | 正文HTML（必填） |
| `thumb_media_id` | `articles[0].thumb_media_id` | 封面图media_id（必填） |
| `need_open_comment` | `articles[0].need_open_comment` | 是否开启评论 |
| `only_fans_can_comment` | `articles[0].only_fans_can_comment` | 仅粉丝可评论 |

`content_html` 注意事项：
- 所有样式必须内联（`style="..."`），微信会过滤 `<style>` 标签
- 图片只能使用 `mmbiz.qpic.cn` 域名（如有文章内图片，需提前上传到微信）
- JSON 序列化必须使用 `ensure_ascii=False`，否则中文乱码

> ⚠️ **thumb_media_id 是必需的**：草稿 API 必须提供有效的 `thumb_media_id`，不能留空字符串。如果没有封面图，需要先上传一张默认封面图获取 `media_id`。

**旧版 jq 构造方式（已废弃）**：
不要用 `jq` 在 bash 中构造包含复杂 HTML 的 JSON，转义问题极难处理。改用 Python 内联脚本构造 JSON（见上方正确写法）。

---

---

## Step 4: 提示用户检查

发布完成后输出：

```
✅ 草稿发布成功！

📝 文章信息
- 标题：{title}
- 摘要：{digest}
- 草稿 media_id：{DRAFT_MEDIA_ID}

📌 前往公众号后台查看并发布：
   https://mp.weixin.qq.com （登录后点击「内容管理」→「草稿箱」）

⚠️ 检查要点：
1. 图片是否正常显示
2. 排版是否正确
3. 标题和摘要是否合适
4. 确认无误后点击"发布"
```

> 注意：微信草稿 API 不返回可直接跳转的文章链接，草稿需在后台确认后才生成正式链接。上方输出中直接给出后台草稿箱的导航路径，用户点击即可到达。

---

## HTML 内联样式参考

```html
<section style="font-family: -apple-system, sans-serif; line-height: 1.8; color: #333; padding: 15px;">
  <p style="margin-bottom: 20px;">段落内容</p>

  <h2 style="border-bottom: 1px solid #eee; padding-bottom: 8px;">标题</h2>

  <p style="text-align: center; margin: 25px 0;">
    <img src="{mmbiz_img_url}" style="max-width: 100%; border-radius: 6px;">
  </p>

  <blockquote style="background: #f6f8fa; border-left: 4px solid #ddd; padding: 12px 16px;">
    引用内容
  </blockquote>
</section>
```

---

## 注意事项

1. **网关优先**：配置了 `WXPG_GATEWAY_URL + WXPG_API_KEY` 时，脚本只调用 `wx-publish-gateway` 的 `/v1/media/cover`、`/v1/media/inline`、`/v1/draft`，不直连微信 API。
2. **不要在本地获取真实 access_token**：网关模式下 `get_wechat_token` 只返回哨兵值 `__WXPG_GATEWAY__`。token 由网关内部缓存和刷新，本地脚本不要调用 `/v1/token`。
3. **中文编码**：草稿 JSON 必须用 `ensure_ascii=False` / UTF-8。当前脚本用 `jq` 构造旧 payload，再转换给网关；不要用 Python `requests.post(..., json=...)` 直接绕过脚本。
4. **图片域名**：文章内图片只能使用微信返回的 `mmbiz.qpic.cn` URL；通过 `upload_inline_image` 获取后再替换正文 HTML。
5. **thumb_media_id 必需**：草稿 API 必须提供有效的 `thumb_media_id`（错误码 40007）。即使没有封面图，也需要先上传默认封面获取 `media_id`。
6. **作者名限制**：微信 API 对 author 字段敏感。实测 `夜航` 成功，避免空格、全角标点和过长作者名。
7. **标题长度**：标题控制在 60 字节以内，避免全角括号、冒号、逗号等容易触发 45003 的字符。
8. **摘要 digest**：遇到 45004 时直接让 digest 留空字符串，微信会自动从正文开头取摘要。
9. **40164 IP 白名单错误**：如果网关返回 40164，说明 VPS 出口 IP 未加入微信公众号后台白名单；把 VPS 公网出口 IP 加进去，不要回退到家宽直连。
10. **旧 PROXY_URL 模式只作 fallback**：只有未配置网关时才使用 `WECHAT_APPID/WECHAT_SECRET + PROXY_URL` 直连。旧模式容易被家宽 IP/V2Ray 绕过大陆规则影响，非首选。
11. **.env 不能直接 source 的情况**：如果 `.env` 里存在带连字符的键名（如 `TAVILY-HIKARI_Authorization`），`source .env` 会报 `未找到命令`。发布脚本只需要 `WXPG_GATEWAY_URL` / `WXPG_API_KEY` / `WXPG_ACCOUNT`，可用专门 env 解析逻辑读取这些键，避免整文件 source。
12. **封面图必须压缩后再上传**（2026-06-09实测）：wx-publish-gateway 对大文件有超时限制。1.7MB PNG 上传超时，压缩到 ~56KB JPEG 后秒传成功。**上传前必须压缩封面图**：用 Pillow resize 到 900×603 并保存为 JPEG quality=85（约 50-60KB），不要直接传原始 PNG。命令参考：
```python
from PIL import Image
img = Image.open(原始路径)
img = img.resize((900, 603), Image.LANCZOS)
img.save(输出路径, 'JPEG', quality=85)
```
13. **Markdown 排版**：使用 `scripts/md_to_wechat_html.py` 将 Markdown 转换为微信兼容的内联样式 HTML。如果自定义排版需求，按本文「排版规范」表中的数值手动构造。
14. **bash -c 中 source 脚本必须用绝对路径**：`bash -c 'source ~/path/scripts.sh'` 会因 tilde 不展开而报 `没有那个文件或目录`。必须用完整绝对路径或先 `cd` 到 skill 目录再 `source ./scripts.sh`。
15. **WXPG 环境变量可能不在 .env 文件中**：实测发现 `WXPG_GATEWAY_URL`、`WXPG_API_KEY`、`WXPG_ACCOUNT`、`WECHAT_APPID`、`WECHAT_SECRET` 都在进程 env 中已设置，但 .env 文件里未必能找到。不要因为 .env 里找不到就认为未配置——先用 `env | grep -iE "WXPG|WECHAT"` 检查进程环境。
14. **wx-publish-gateway `/v1/draft` 期望扁平字段**（2026-06-17实测）：网关的 `/v1/draft` 端点期望**扁平字段**（`title`, `content_html`, `thumb_media_id` 等），不是微信官方API的嵌套 `articles[0]` 结构。如果传入嵌套结构会报 `{"detail":[{"type":"missing","loc":["body","title"],"msg":"Field required"}]}`。正确做法是直接传扁平字段，网关内部会转换为微信API所需的嵌套结构。详见「构建草稿 JSON 并创建草稿」章节。

15. **wx-publish-gateway `/v1/media/cover` 字段名是 `file` 不是 `media`**（2026-06-17实测）：上传封面图时，表单字段必须是 `-F "file=@cover.jpg"`，不是 `-F "media=@cover.jpg"`。后者会报 `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required"}]}`。

16. **wx-publish-gateway 403 API Key 错误**（2026-06-15实测）：调用网关接口返回 `403 {"detail":"Invalid or missing X-API-Key"}` 时，即使环境变量已设置也可能失败。排查步骤：
    - 确认网关服务正常运行：`curl -s <网关URL>/health`
    - 检查 `.env` 中的 key 与网关实际配置是否一致
    - 进程 env 中的 key 可能被脱敏为 `***`，无法判断真实值
    - 如无法快速解决，按降级策略执行（存档+标记 draft_pending_push，人工手动推送）
