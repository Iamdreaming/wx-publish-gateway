# Scripts Location

The `scripts.sh` file is located at:

```text
./scripts.sh
```

## Preferred Gateway Configuration

`scripts.sh` now prefers `wx-publish-gateway` over direct WeChat API calls.

Required environment variables:

```bash
WXPG_GATEWAY_URL="http://<fixed-ip-or-internal-address>:<port>"
WXPG_API_KEY="<gateway api key>"
WXPG_ACCOUNT="main"   # optional
```

When these are set:

- `get_wechat_token` returns the sentinel `__WXPG_GATEWAY__` instead of a real WeChat token.
- `upload_wechat_image` calls `POST /v1/media/cover`.
- `upload_inline_image` calls `POST /v1/media/inline`.
- `create_draft` calls `POST /v1/draft`.
- The script does **not** call `/v1/token` and does **not** expose WeChat `access_token` locally.

## Usage

If the current Hermes/social-media process already loaded profile env vars, just source the helper:

```bash
source ./scripts.sh
```

If running manually from a raw shell, load only the needed WXPG variables from the profile `.env` with your preferred safe env loader; avoid blindly `source your .env file` if that file contains keys with hyphens.

## Fallback Mode

If `WXPG_GATEWAY_URL + WXPG_API_KEY` are not set, the script falls back to the old direct WeChat API mode using:

```bash
WECHAT_APPID="..."
WECHAT_SECRET="..."
PROXY_URL="http://127.0.0.1:10808"   # optional
```

Fallback mode is kept for compatibility only. Prefer the gateway because it provides a fixed egress IP and avoids repeated WeChat `40164` whitelist failures.
