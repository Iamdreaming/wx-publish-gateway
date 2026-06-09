"""FastAPI entrypoint for wx-publish-gateway."""

from __future__ import annotations

from typing import Optional

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from wx_publish_gateway.auth import verify_api_key
from wx_publish_gateway.client import WeChatClient, WeChatError
from wx_publish_gateway.config import AccountConfig, Settings, get_settings

VERSION = "0.1.0"


class TokenRequest(BaseModel):
    account: Optional[str] = None


class DraftRequest(BaseModel):
    account: Optional[str] = None
    title: str
    content_html: str
    digest: Optional[str] = None
    thumb_media_id: str
    author: Optional[str] = None
    need_open_comment: Optional[int] = Field(default=1, ge=0, le=1)
    only_fans_can_comment: Optional[int] = Field(default=0, ge=0, le=1)


class SubmitDraftRequest(BaseModel):
    account: Optional[str] = None
    media_id: str


def _settings_from_args(
    api_keys: Optional[list[str]],
    wechat_base_url: Optional[str],
    accounts_json: Optional[dict],
    default_account: Optional[str],
) -> Settings:
    if any(value is not None for value in (api_keys, wechat_base_url, accounts_json, default_account)):
        import json

        return Settings(
            api_keys=api_keys or [],
            wechat_base_url=wechat_base_url or "https://api.weixin.qq.com",
            accounts_json=json.dumps(accounts_json or {}, ensure_ascii=False),
            default_account=default_account,
        )
    return get_settings()


def _public_account(name: str, account: AccountConfig) -> dict:
    data = {"name": name, "appid": account.appid}
    if account.author:
        data["author"] = account.author
    return data


def _resolve_account(settings: Settings, account_name: Optional[str]) -> tuple[str, AccountConfig]:
    name = account_name or settings.default_account
    if not name:
        raise HTTPException(status_code=400, detail="No account specified and no default account configured")
    try:
        return name, settings.get_account(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _wechat_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WeChatError):
        status_code = 502
        detail = {"error": str(exc), "errcode": exc.errcode, "errmsg": exc.errmsg}
        if exc.errcode == 40164:
            detail["hint"] = "WeChat IP whitelist mismatch; add this VPS egress IP to the Official Account whitelist."
        return HTTPException(status_code=status_code, detail=detail)
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(status_code=502, detail=f"WeChat HTTP error: {exc}")
    return HTTPException(status_code=502, detail=f"WeChat request failed: {exc}")


def build_article_payload(request: DraftRequest, account: AccountConfig) -> dict:
    author = request.author if request.author is not None else account.author
    article = {
        "title": request.title,
        "content": request.content_html,
        "thumb_media_id": request.thumb_media_id,
        "need_open_comment": request.need_open_comment,
        "only_fans_can_comment": request.only_fans_can_comment,
    }
    if request.digest is not None:
        article["digest"] = request.digest
    if author is not None:
        article["author"] = author
    return {"articles": [article]}


def create_app(
    *,
    api_keys: Optional[list[str]] = None,
    wechat_base_url: Optional[str] = None,
    accounts_json: Optional[dict] = None,
    default_account: Optional[str] = None,
    wechat_client: Optional[WeChatClient] = None,
) -> FastAPI:
    settings = _settings_from_args(api_keys, wechat_base_url, accounts_json, default_account)
    client = wechat_client or WeChatClient(settings.wechat_base_url)
    auth_dependency = verify_api_key(settings.api_keys)

    app = FastAPI(title=settings.service_name, version=VERSION)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": settings.service_name, "version": VERSION}

    @app.post("/v1/token", dependencies=[auth_dependency])
    def token(request: TokenRequest) -> dict:
        name, account = _resolve_account(settings, request.account)
        try:
            access_token = client.get_access_token(account)
        except Exception as exc:
            raise _wechat_error(exc) from exc
        return {"account": _public_account(name, account), "access_token": access_token}

    @app.post("/v1/media/cover", dependencies=[auth_dependency])
    def upload_cover(
        file: UploadFile = File(...),
        account: Optional[str] = Form(None),
    ) -> dict:
        name, account_config = _resolve_account(settings, account)
        try:
            media_id = client.upload_cover(
                account_config,
                file.file.read(),
                file.filename or "cover",
                file.content_type or "application/octet-stream",
            )
        except Exception as exc:
            raise _wechat_error(exc) from exc
        return {"account": _public_account(name, account_config), "media_id": media_id}

    @app.post("/v1/media/inline", dependencies=[auth_dependency])
    def upload_inline(
        file: UploadFile = File(...),
        account: Optional[str] = Form(None),
    ) -> dict:
        name, account_config = _resolve_account(settings, account)
        try:
            url = client.upload_inline_image(
                account_config,
                file.file.read(),
                file.filename or "image",
                file.content_type or "application/octet-stream",
            )
        except Exception as exc:
            raise _wechat_error(exc) from exc
        return {"account": _public_account(name, account_config), "url": url}

    @app.post("/v1/draft", dependencies=[auth_dependency])
    def create_draft(request: DraftRequest) -> dict:
        name, account = _resolve_account(settings, request.account)
        payload = build_article_payload(request, account)
        try:
            media_id = client.create_draft(account, payload)
        except Exception as exc:
            raise _wechat_error(exc) from exc
        return {"account": _public_account(name, account), "media_id": media_id}

    @app.post("/v1/draft/submit", dependencies=[auth_dependency])
    def submit_draft(request: SubmitDraftRequest) -> dict:
        name, account = _resolve_account(settings, request.account)
        try:
            publish_id = client.submit_draft(account, request.media_id)
        except Exception as exc:
            raise _wechat_error(exc) from exc
        return {"account": _public_account(name, account), "publish_id": publish_id}

    return app


app = create_app()
