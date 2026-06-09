"""WeChat HTTP client with token caching and explicit JSON serialization."""

from __future__ import annotations

import json
import time
from typing import Dict, Optional, Tuple

import httpx

from wx_publish_gateway.config import AccountConfig

TOKEN_REFRESH_BUFFER = 300


class WeChatError(httpx.HTTPStatusError):
    """Raised when WeChat API returns a non-zero errcode."""

    def __init__(self, errcode: int, errmsg: str, request: httpx.Request):
        self.errcode = errcode
        self.errmsg = errmsg
        message = f"WeChat API error {errcode}: {errmsg}"
        if errcode == 40164:
            message += " (IP whitelist mismatch: add this VPS public egress IP in WeChat Official Account settings)"
        super().__init__(
            message,
            request=request,
            response=httpx.Response(status_code=200, request=request),
        )


class WeChatClient:
    """Small synchronous client for WeChat Official Account APIs."""

    def __init__(self, base_url: str = "https://api.weixin.qq.com"):
        self.base_url = base_url.rstrip("/")
        self._token_cache: Dict[str, Tuple[str, float]] = {}

    def _check_response(self, response: httpx.Response) -> dict:
        try:
            body = response.json()
        except ValueError:
            response.raise_for_status()
            return {}

        if "errcode" in body and body["errcode"] != 0:
            raise WeChatError(
                errcode=int(body["errcode"]),
                errmsg=str(body.get("errmsg", "unknown error")),
                request=response.request,
            )
        response.raise_for_status()
        return body

    def get_access_token(self, account: AccountConfig) -> str:
        now = time.time()
        cached = self._token_cache.get(account.appid)
        if cached:
            token, expiry = cached
            if expiry - now > TOKEN_REFRESH_BUFFER:
                return token

        with httpx.Client(base_url=self.base_url) as client:
            response = client.get(
                "/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": account.appid,
                    "secret": account.secret,
                },
            )
        body = self._check_response(response)
        token = body["access_token"]
        expires_in = int(body.get("expires_in", 7200))
        self._token_cache[account.appid] = (token, now + expires_in)
        return token

    def upload_cover(
        self,
        account: AccountConfig,
        image_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        token = self.get_access_token(account)
        with httpx.Client(base_url=self.base_url) as client:
            response = client.post(
                "/cgi-bin/material/add_material",
                params={"access_token": token, "type": "image"},
                files={"media": (filename, image_bytes, content_type)},
            )
        return self._check_response(response)["media_id"]

    def upload_inline_image(
        self,
        account: AccountConfig,
        image_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        token = self.get_access_token(account)
        with httpx.Client(base_url=self.base_url) as client:
            response = client.post(
                "/cgi-bin/media/uploadimg",
                params={"access_token": token},
                files={"media": (filename, image_bytes, content_type)},
            )
        return self._check_response(response)["url"]

    def create_draft(self, account: AccountConfig, payload: dict) -> str:
        token = self.get_access_token(account)
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        with httpx.Client(base_url=self.base_url) as client:
            response = client.post(
                "/cgi-bin/draft/add",
                params={"access_token": token},
                content=content,
                headers=headers,
            )
        return self._check_response(response)["media_id"]

    def submit_draft(self, account: AccountConfig, media_id: str) -> str:
        token = self.get_access_token(account)
        payload = {"media_id": media_id}
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        with httpx.Client(base_url=self.base_url) as client:
            response = client.post(
                "/cgi-bin/freepublish/submit",
                params={"access_token": token},
                content=content,
                headers=headers,
            )
        return self._check_response(response)["publish_id"]
