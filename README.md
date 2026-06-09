# wx-publish-gateway

> 部署在固定公网 IP 服务器上的微信公众号发布 API 网关，用来解决本地 Agent / 脚本调用微信 API 时遇到的 **IP 白名单失效** 问题。

[English README](./README.en.md)

---

## 这个项目解决什么问题？

微信公众号开发接口要求调用方出口 IP 必须在公众号后台的 **IP 白名单** 中。

如果你在本地电脑、家宽网络、NAS、动态代理、AI Agent 运行环境里直接调用：

```text
https://api.weixin.qq.com/cgi-bin/draft/add
```

很容易遇到：

```json
{
  "errcode": 40164,
  "errmsg": "invalid ip ... not in whitelist"
}
```

家宽 IP 一变，就得重新去公众号后台加白名单，自动化发布链路会经常断。

`wx-publish-gateway` 的思路很简单：

```text
本地 Agent / 脚本
        │
        │ HTTPS + X-API-Key
        ▼
阿里云 / 腾讯云 / VPS 上的 wx-publish-gateway
        │  固定公网出口 IP
        ▼
api.weixin.qq.com
```

你只需要把 **VPS 的固定公网 IP** 加进微信公众号后台白名单。之后本地 Agent 永远只调用这个网关，不再直接碰微信 API。

---

## 适用场景

- AI Agent 自动生成公众号文章后，推送到草稿箱。
- 本地脚本需要稳定调用微信公众号 API。
- 公众号自动化发布被 `40164 IP whitelist` 卡住。
- 家宽 / 动态 IP / 多机器运行导致微信 API 白名单维护困难。
- 需要统一管理多个公众号的 `appid / secret / access_token`。

---

## 当前能力

- `GET /health` 健康检查，无需鉴权。
- 所有 `/v1/*` 接口使用 `X-API-Key` 鉴权。
- 支持多个微信公众号账号配置。
- access_token 进程内缓存，带过期刷新缓冲。
- 上传封面图到微信素材库，返回 `media_id`。
- 上传正文内图片到微信 CDN，返回 `mmbiz.qpic.cn` URL。
- 创建微信公众号草稿箱草稿。
- 提交草稿发布接口。
- 微信 `errcode` 映射为清晰错误。
- 对 `40164` IP 白名单错误给出明确提示。
- 中文 JSON 使用 `ensure_ascii=False` 显式 UTF-8 序列化，避免中文转义/乱码坑。
- Docker / Docker Compose 部署。
- 测试全部 mock，不会请求真实微信 API。

---

## 快速开始

### 1. 本地运行

```bash
git clone https://github.com/Iamdreaming/wx-publish-gateway.git
cd wx-publish-gateway

python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入你的 API key 和公众号配置

uvicorn wx_publish_gateway.main:app --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

返回示例：

```json
{
  "status": "ok",
  "service": "wx-publish-gateway",
  "version": "0.1.0"
}
```

---

## 环境变量

复制模板：

```bash
cp .env.example .env
```

`.env` 示例：

```bash
WXPG_API_KEYS=change-me-client-key,another-client-key
WXPG_DEFAULT_ACCOUNT=main
WXPG_ACCOUNTS_JSON={"main":{"appid":"wx_your_appid","secret":"your_wechat_app_secret","author":"Your Name"}}
WXPG_WECHAT_BASE_URL=https://api.weixin.qq.com
```

变量说明：

| 变量 | 必填 | 说明 |
|---|---:|---|
| `WXPG_API_KEYS` | 是 | 允许调用网关的客户端 key，逗号分隔。请求时放到 `X-API-Key` header。 |
| `WXPG_DEFAULT_ACCOUNT` | 推荐 | 默认公众号账号名。请求不传 `account` 时使用它。 |
| `WXPG_ACCOUNTS_JSON` | 是 | 公众号账号配置，格式为账号名到 `{appid, secret, author?}` 的 JSON 映射。 |
| `WXPG_WECHAT_BASE_URL` | 否 | 微信 API Base URL，默认 `https://api.weixin.qq.com`。测试时可覆盖。 |

多账号配置示例：

```bash
WXPG_DEFAULT_ACCOUNT=main
WXPG_ACCOUNTS_JSON={"main":{"appid":"wx_main","secret":"sec_main","author":"夜航"},"backup":{"appid":"wx_backup","secret":"sec_backup"}}
```

---

## API 使用示例

所有 `/v1/*` 接口都需要：

```bash
-H 'X-API-Key: change-me-client-key'
```

### 获取 access_token

```bash
curl -s http://127.0.0.1:8000/v1/token \
  -H 'X-API-Key: change-me-client-key' \
  -H 'Content-Type: application/json' \
  -d '{"account":"main"}'
```

返回示例：

```json
{
  "account": {
    "name": "main",
    "appid": "wx_your_appid",
    "author": "Your Name"
  },
  "access_token": "ACCESS_TOKEN"
}
```

> 注意：`/v1/token` 会返回 access_token，但不会返回公众号 `secret`。这个接口只适合可信客户端使用。

---

### 上传封面图

对应微信接口：`/cgi-bin/material/add_material?type=image`

```bash
curl -s http://127.0.0.1:8000/v1/media/cover \
  -H 'X-API-Key: change-me-client-key' \
  -F account=main \
  -F file=@cover.jpg
```

返回示例：

```json
{
  "account": {
    "name": "main",
    "appid": "wx_your_appid"
  },
  "media_id": "MEDIA_ID"
}
```

---

### 上传正文内图片

对应微信接口：`/cgi-bin/media/uploadimg`

```bash
curl -s http://127.0.0.1:8000/v1/media/inline \
  -H 'X-API-Key: change-me-client-key' \
  -F account=main \
  -F file=@inline.png
```

返回示例：

```json
{
  "account": {
    "name": "main",
    "appid": "wx_your_appid"
  },
  "url": "https://mmbiz.qpic.cn/..."
}
```

正文 HTML 里的 `<img src="...">` 应使用这个返回的 `mmbiz.qpic.cn` URL。

---

### 创建公众号草稿

对应微信接口：`/cgi-bin/draft/add`

```bash
curl -s http://127.0.0.1:8000/v1/draft \
  -H 'X-API-Key: change-me-client-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "account":"main",
    "title":"中文标题",
    "content_html":"<p>正文内容</p>",
    "digest":"摘要",
    "thumb_media_id":"COVER_MEDIA_ID",
    "need_open_comment":1,
    "only_fans_can_comment":0
  }'
```

返回示例：

```json
{
  "account": {
    "name": "main",
    "appid": "wx_your_appid"
  },
  "media_id": "DRAFT_MEDIA_ID"
}
```

网关内部会构造成微信需要的 payload：

```json
{
  "articles": [
    {
      "title": "中文标题",
      "content": "<p>正文内容</p>",
      "thumb_media_id": "COVER_MEDIA_ID",
      "digest": "摘要",
      "author": "Your Name",
      "need_open_comment": 1,
      "only_fans_can_comment": 0
    }
  ]
}
```

---

### 提交草稿发布

对应微信接口：`/cgi-bin/freepublish/submit`

```bash
curl -s http://127.0.0.1:8000/v1/draft/submit \
  -H 'X-API-Key: change-me-client-key' \
  -H 'Content-Type: application/json' \
  -d '{"account":"main","media_id":"DRAFT_MEDIA_ID"}'
```

返回示例：

```json
{
  "account": {
    "name": "main",
    "appid": "wx_your_appid"
  },
  "publish_id": "PUBLISH_ID"
}
```

> 注意：个人未认证订阅号的发布能力可能受微信官方权限限制。本项目首先解决的是 **API 调用出口 IP 白名单** 问题，不绕过微信账号权限。

---

## Docker 部署

### 构建镜像

```bash
docker build -t wx-publish-gateway .
```

### 运行容器

```bash
docker run --rm -p 8000:8000 --env-file .env wx-publish-gateway
```

### Docker Compose

```bash
cp .env.example .env
# 编辑 .env

docker compose up -d --build
curl http://127.0.0.1:8000/health
```

---

## 阿里云 VPS 部署建议

1. 购买或使用一台有固定公网 IPv4 的阿里云 ECS / 轻量应用服务器。
2. 在服务器安全组里开放服务端口，例如 `8000`，但建议只允许你的本地出口 IP 访问。
3. 更推荐用 Nginx / Caddy 套一层 HTTPS，例如：

```text
https://your-domain.example.com -> 127.0.0.1:8000
```

4. 上传或 clone 项目：

```bash
git clone https://github.com/Iamdreaming/wx-publish-gateway.git
cd wx-publish-gateway
```

5. 配置环境变量：

```bash
cp .env.example .env
vim .env
```

6. 启动：

```bash
docker compose up -d --build
```

7. 检查：

```bash
curl http://127.0.0.1:8000/health
```

8. 在微信公众号后台把 **VPS 公网出口 IP** 加入 IP 白名单。

9. 用 `/v1/token` 做一次真实连通性验证。

---

## 微信 IP 白名单说明

如果微信返回：

```json
{
  "errcode": 40164,
  "errmsg": "invalid ip ... not in whitelist"
}
```

说明当前请求的出口 IP 不在微信公众号后台白名单里。

本项目部署在 VPS 后，请将 **VPS 的公网出口 IP** 加到：

```text
微信公众平台后台 -> 设置与开发 -> 基本配置 -> IP 白名单
```

网关会把 `40164` 映射成带有 `IP whitelist` 提示的错误，方便 Agent / 脚本识别根因。

---

## 与社媒 Agent 集成思路

原来的流程：

```text
social-media agent -> api.weixin.qq.com -> 40164 风险
```

改造后：

```text
social-media agent -> wx-publish-gateway -> api.weixin.qq.com
```

`mp-draft-push` 这类发布脚本可以改为：

1. 本地完成文章排版。
2. 调 `/v1/media/cover` 上传封面图。
3. 调 `/v1/media/inline` 上传正文内图片并替换 HTML 中的图片 URL。
4. 调 `/v1/draft` 创建草稿。
5. 如果账号权限允许，再调 `/v1/draft/submit`。

---

## 测试

```bash
python -m pytest -q
```

当前测试覆盖：

- 配置解析
- API key 鉴权
- token 缓存
- 微信错误映射
- 中文 JSON 序列化
- 草稿 payload 构造
- endpoint happy path
- secret 不泄露

测试全部 mock，不会请求真实微信 API。

---

## 安全注意事项

- 不要提交 `.env`。
- 不要把真实 `appid / secret / API key` 写进 README、issue、聊天记录或日志。
- `WXPG_API_KEYS` 请使用足够长的随机字符串。
- 生产环境建议放到 HTTPS 后面。
- 生产环境建议限制访问来源 IP，不要裸露在公网。
- `/v1/token` 会返回 access_token，只应开放给可信客户端。
- 如果怀疑 key 泄露，立即轮换 `WXPG_API_KEYS` 和公众号 secret。

---

## 当前限制

- access_token 缓存在进程内，容器重启后会丢失。
- 没有账号管理后台，账号通过环境变量配置。
- 没有内置 Markdown 排版器；当前 `/v1/draft` 接收 `content_html`。
- 不绕过微信官方账号权限限制；未认证个人号能否发布取决于微信开放的接口权限。

---

## License

MIT
