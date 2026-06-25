# wx-publish-gateway / WeChat API Egress Configuration

## 推荐方案：wx-publish-gateway

家宽 IP 会变，直接调用微信 API 容易返回：

```json
{"errcode":40164,"errmsg":"invalid ip ... not in whitelist"}
```

当前推荐方案是：把 `wx-publish-gateway` 部署到有固定公网出口 IP 的 VPS（例如阿里云），然后将 VPS 公网 IP 加入微信公众号后台 IP 白名单。本地 social-media agent 只调用这个网关。

```text
social-media agent
  -> WXPG_GATEWAY_URL + X-API-Key
  -> wx-publish-gateway（固定出口 IP）
  -> api.weixin.qq.com
```

## 配置

在 `your .env file` 中设置（不要写进 skill 文档或提交仓库）：

```bash
WXPG_GATEWAY_URL="http://<固定IP或内网地址>:<端口>"
WXPG_API_KEY="<网关 API Key>"
WXPG_ACCOUNT="main"   # 可选；不填则使用网关默认账号
```

`scripts.sh` 会优先使用网关模式：

| 函数 | 网关 endpoint |
|---|---|
| `upload_wechat_image` | `POST /v1/media/cover` |
| `upload_inline_image` | `POST /v1/media/inline` |
| `create_draft` | `POST /v1/draft` |

`get_wechat_token` 在网关模式下只返回哨兵值 `__WXPG_GATEWAY__`，不会请求 `/v1/token`，也不会把微信 access_token 暴露给本地脚本。token 由网关内部管理。

## 验证

### 1. 健康检查

```bash
curl -s "$WXPG_GATEWAY_URL/health"
```

期望返回：

```json
{"status":"ok","service":"wx-publish-gateway","version":"0.1.0"}
```

### 2. 鉴权检查

```bash
curl -s -X POST "$WXPG_GATEWAY_URL/v1/draft" \
  -H "X-API-Key: $WXPG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"test","content_html":"<p>test</p>","thumb_media_id":"invalid"}'
```

能进入业务错误（而不是 403）说明网关鉴权可用。

### 3. 端到端测试草稿

通过 `upload_wechat_image` 上传测试封面，再调用 `create_draft` 创建一篇草稿。注意：这会真实写入公众号素材库/草稿箱，测试标题请标记清楚，完成后可在后台删除。

## 旧方案：PROXY_URL fallback

如果没有配置 `WXPG_GATEWAY_URL + WXPG_API_KEY`，脚本会 fallback 到旧的微信直连模式：

```bash
WECHAT_APPID="..."
WECHAT_SECRET="..."
PROXY_URL="http://127.0.0.1:10808"   # 可选
```

旧方案的问题：

- 家宽 IP 变化后仍会 40164。
- V2Ray/Clash 的「绕过大陆」规则可能让 `api.weixin.qq.com` 走直连。
- access_token 会在本地脚本间传递，安全边界更差。

因此，除非网关不可用，否则不要优先使用旧方案。

## 40164 排查

如果网关返回 40164：

1. 确认实际请求是从 VPS 出口出去。
2. 在微信公众号后台把 VPS 公网出口 IP 加入白名单。
3. 重新测试 `/v1/media/cover` 或 `/v1/draft`。

如果旧 `PROXY_URL` fallback 返回 40164：

1. 查看错误里的 IP。
2. 把该 IP 加白名单，或改用固定出口 VPS 网关。
3. 不要继续反复换代理试错。
