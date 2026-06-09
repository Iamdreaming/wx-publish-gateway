"""Tests for WeChat HTTP client (no real API calls)."""

import json
import time

import httpx
import pytest
import respx

from wx_publish_gateway.client import WeChatClient, WeChatError
from wx_publish_gateway.config import AccountConfig


@pytest.fixture
def account():
    return AccountConfig(appid="wx_test_appid", secret="test_secret", author="测试作者")


@pytest.fixture
def client(account):
    return WeChatClient(base_url="https://mock.weixin.qq.com")


@pytest.fixture
def mock_wechat():
    with respx.mock(base_url="https://mock.weixin.qq.com") as respx_mock:
        yield respx_mock


class TestGetAccessToken:
    def test_get_access_token_caches(self, client, account, mock_wechat):
        route = mock_wechat.get("/cgi-bin/token").respond(
            json={"access_token": "token_abc", "expires_in": 7200}
        )

        t1 = client.get_access_token(account)
        assert t1 == "token_abc"
        assert route.call_count == 1
        assert dict(route.calls.last.request.url.params) == {
            "grant_type": "client_credential",
            "appid": "wx_test_appid",
            "secret": "test_secret",
        }

        t2 = client.get_access_token(account)
        assert t2 == "token_abc"
        assert route.call_count == 1

    def test_get_access_token_expiry_buffer(self, client, account, mock_wechat):
        route = mock_wechat.get("/cgi-bin/token").mock(
            side_effect=[
                httpx.Response(200, json={"access_token": "token_first", "expires_in": 30}),
                httpx.Response(200, json={"access_token": "token_refreshed", "expires_in": 7200}),
            ]
        )

        assert client.get_access_token(account) == "token_first"
        assert client.get_access_token(account) == "token_refreshed"
        assert route.call_count == 2

    def test_wechat_errcode_raises(self, client, account, mock_wechat):
        mock_wechat.get("/cgi-bin/token").respond(
            json={"errcode": 40013, "errmsg": "invalid appid"}
        )

        with pytest.raises(httpx.HTTPStatusError, match="40013"):
            client.get_access_token(account)

    def test_ip_whitelist_error_is_obvious(self, client, account, mock_wechat):
        mock_wechat.get("/cgi-bin/token").respond(
            json={"errcode": 40164, "errmsg": "invalid ip 1.2.3.4"}
        )

        with pytest.raises(WeChatError, match="IP whitelist"):
            client.get_access_token(account)


class TestUploadCover:
    def test_upload_cover_returns_media_id(self, client, account, mock_wechat):
        route = mock_wechat.post("/cgi-bin/material/add_material").respond(
            json={"media_id": "media_cover_123"}
        )

        client._token_cache["wx_test_appid"] = ("tok", time.time() + 3600)
        result = client.upload_cover(account, b"image-data", "cover.jpg", "image/jpeg")
        assert result == "media_cover_123"
        assert dict(route.calls.last.request.url.params) == {"access_token": "tok", "type": "image"}


class TestUploadInlineImage:
    def test_upload_inline_returns_url(self, client, account, mock_wechat):
        route = mock_wechat.post("/cgi-bin/media/uploadimg").respond(
            json={"url": "https://mmbiz.qpic.cn/inline123"}
        )

        client._token_cache["wx_test_appid"] = ("tok", time.time() + 3600)
        result = client.upload_inline_image(account, b"img-data", "photo.png", "image/png")
        assert result == "https://mmbiz.qpic.cn/inline123"
        assert dict(route.calls.last.request.url.params) == {"access_token": "tok"}


class TestCreateDraft:
    def test_create_draft_returns_media_id(self, client, account, mock_wechat):
        route = mock_wechat.post("/cgi-bin/draft/add").respond(
            json={"media_id": "draft_456"}
        )

        client._token_cache["wx_test_appid"] = ("tok", time.time() + 3600)
        payload = {
            "articles": [
                {
                    "title": "测试标题",
                    "content": "<p>正文内容</p>",
                    "thumb_media_id": "thumb_001",
                    "need_open_comment": 1,
                    "only_fans_can_comment": 0,
                }
            ]
        }
        result = client.create_draft(account, payload)
        assert result == "draft_456"
        request = route.calls.last.request
        assert dict(request.url.params) == {"access_token": "tok"}
        assert request.headers["content-type"] == "application/json; charset=utf-8"
        raw = request.content.decode("utf-8")
        assert "测试标题" in raw
        assert "\\u6d4b" not in raw
        assert json.loads(raw) == payload


class TestSubmitDraft:
    def test_submit_returns_publish_id(self, client, account, mock_wechat):
        route = mock_wechat.post("/cgi-bin/freepublish/submit").respond(
            json={"publish_id": "pub_789"}
        )

        client._token_cache["wx_test_appid"] = ("tok", time.time() + 3600)
        result = client.submit_draft(account, "draft_456")
        assert result == "pub_789"
        assert dict(route.calls.last.request.url.params) == {"access_token": "tok"}
        assert json.loads(route.calls.last.request.content.decode("utf-8")) == {"media_id": "draft_456"}


class TestErrorMapping:
    def test_http_error_wraps(self, client, account, mock_wechat):
        mock_wechat.get("/cgi-bin/token").respond(status_code=500)

        with pytest.raises(httpx.HTTPStatusError):
            client.get_access_token(account)
