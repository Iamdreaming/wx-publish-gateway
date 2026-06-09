# wx-publish-gateway

`wx-publish-gateway` is a small FastAPI gateway for WeChat Official Account publishing. It is intended to run on an Alibaba Cloud VPS with a fixed public egress IP, so local agents and scripts can call this gateway instead of calling `api.weixin.qq.com` directly.

## Problem

WeChat Official Account API requires the caller IP to be added to the account IP whitelist. Local machines, browser agents, or multi-agent runners often have changing outbound IPs. Deploying this gateway on a VPS gives all publishing traffic one stable egress IP.

## Architecture

```text
local social-media agent/script
  -> HTTPS + X-API-Key
  -> wx-publish-gateway on Alibaba Cloud VPS
  -> api.weixin.qq.com from fixed VPS IP
```

The gateway does not store drafts locally. It proxies authenticated requests to WeChat APIs, caches access tokens in memory per appid, and returns WeChat identifiers such as `media_id`, image `url`, and `publish_id`.

## Features

- `GET /health` without auth.
- API key guard for all `/v1/*` endpoints via `X-API-Key`.
- Multiple WeChat Official Account configs via `WXPG_ACCOUNTS_JSON`.
- Token caching with expiry buffer.
- Cover image upload, inline image upload, draft creation, and draft submit.
- Explicit UTF-8 JSON serialization with `ensure_ascii=False` for Chinese content.
- Clear error mapping for WeChat `errcode`, including `40164` IP whitelist failures.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env
uvicorn wx_publish_gateway.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Run tests:

```bash
python -m pytest -q
```

Tests use mocks and must not call the real WeChat API.

## Environment variables

| Variable | Required | Description |
|---|---:|---|
| `WXPG_API_KEYS` | yes | Comma-separated client API keys accepted by `X-API-Key`. |
| `WXPG_DEFAULT_ACCOUNT` | recommended | Default account name when request body/form omits `account`. |
| `WXPG_ACCOUNTS_JSON` | yes | JSON object mapping account name to `{appid, secret, author?}`. |
| `WXPG_WECHAT_BASE_URL` | no | WeChat API base URL. Defaults to `https://api.weixin.qq.com`; override in tests only. |

Example:

```bash
WXPG_API_KEYS=client-key-1,client-key-2
WXPG_DEFAULT_ACCOUNT=main
WXPG_ACCOUNTS_JSON={"main":{"appid":"wx123","secret":"sec123","author":"NightRain"}}
WXPG_WECHAT_BASE_URL=https://api.weixin.qq.com
```

## API examples

All `/v1/*` calls require:

```bash
-H 'X-API-Key: client-key-1'
```

### Get token info

Returns an access token and public account info. It never returns the WeChat app secret.

```bash
curl -s http://127.0.0.1:8000/v1/token \
  -H 'X-API-Key: client-key-1' \
  -H 'Content-Type: application/json' \
  -d '{"account":"main"}'
```

### Upload cover image

```bash
curl -s http://127.0.0.1:8000/v1/media/cover \
  -H 'X-API-Key: client-key-1' \
  -F account=main \
  -F file=@cover.jpg
```

Response:

```json
{"account":{"name":"main","appid":"wx123"},"media_id":"MEDIA_ID"}
```

### Upload inline image

```bash
curl -s http://127.0.0.1:8000/v1/media/inline \
  -H 'X-API-Key: client-key-1' \
  -F account=main \
  -F file=@inline.png
```

### Create draft

```bash
curl -s http://127.0.0.1:8000/v1/draft \
  -H 'X-API-Key: client-key-1' \
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

The gateway builds WeChat's draft payload as:

```json
{"articles":[{"title":"...","content":"...","thumb_media_id":"..."}]}
```

### Submit draft for publish

```bash
curl -s http://127.0.0.1:8000/v1/draft/submit \
  -H 'X-API-Key: client-key-1' \
  -H 'Content-Type: application/json' \
  -d '{"account":"main","media_id":"DRAFT_MEDIA_ID"}'
```

## Docker

Build and run:

```bash
docker build -t wx-publish-gateway .
docker run --rm -p 8000:8000 --env-file .env wx-publish-gateway
```

Docker Compose:

```bash
cp .env.example .env
# edit .env
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

## Alibaba Cloud VPS deployment

1. Buy or use a VPS with a stable public IPv4 address.
2. Open inbound port `8000` only to trusted caller IPs, or put the service behind Nginx/Caddy with HTTPS.
3. Copy this project to the VPS.
4. Create `.env` from `.env.example`; keep it private.
5. Run `docker compose up -d --build`.
6. Verify `GET /health` from the local agent.
7. Call `/v1/token` with `X-API-Key` to verify WeChat credentials and IP whitelist.

Production Nginx/Caddy with TLS is recommended. Do not expose the service without a firewall and strong API keys.

## WeChat IP whitelist

If WeChat returns `errcode=40164`, the current VPS egress IP is not in the Official Account IP whitelist. Add the VPS public IP in the WeChat Official Account admin console, then retry. The gateway surfaces this as a clear `IP whitelist` error hint.

## Security notes

- Never commit `.env`, WeChat app secrets, or real client API keys.
- Use long random `WXPG_API_KEYS` values.
- Restrict inbound network access on the VPS.
- Rotate API keys if they appear in logs or chat transcripts.
- `/v1/token` intentionally returns an access token for trusted clients, but never returns app secrets.
- Tests must keep using mocks and must not send real requests to `api.weixin.qq.com`.
