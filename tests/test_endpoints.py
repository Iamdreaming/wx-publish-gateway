"""Integration tests for API endpoints using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from wx_publish_gateway.main import create_app


class FakeWeChatClient:
    def __init__(self):
        self.last_draft_payload = None

    def get_access_token(self, account):
        return f"token_for_{account.appid}"

    def upload_cover(self, account, image_bytes, filename, content_type):
        assert image_bytes
        assert filename
        assert content_type
        return "media_cover_123"

    def upload_inline_image(self, account, image_bytes, filename, content_type):
        assert image_bytes
        return "https://mmbiz.qpic.cn/inline123"

    def create_draft(self, account, payload):
        self.last_draft_payload = payload
        return "draft_456"

    def submit_draft(self, account, media_id):
        assert media_id == "draft_123"
        return "publish_789"


@pytest.fixture
def fake_wechat():
    return FakeWeChatClient()


@pytest.fixture
def app(fake_wechat):
    return create_app(
        api_keys=["test-key-1", "test-key-2"],
        wechat_base_url="https://mock.weixin.qq.com",
        accounts_json={
            "main": {"appid": "wx_main", "secret": "sec_main", "author": "主账号"},
            "backup": {"appid": "wx_backup", "secret": "sec_backup"},
        },
        default_account="main",
        wechat_client=fake_wechat,
    )


@pytest.fixture
def client(app):
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_no_auth_required(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "wx-publish-gateway"
        assert "version" in data

    def test_health_with_auth_header_still_works(self, client):
        resp = client.get("/health", headers={"X-API-Key": "test-key-1"})
        assert resp.status_code == 200


class TestAuthGuard:
    def test_v1_endpoint_rejects_missing_key(self, client):
        resp = client.post("/v1/token", json={})
        assert resp.status_code == 403

    def test_v1_endpoint_rejects_wrong_key(self, client):
        resp = client.post("/v1/token", json={}, headers={"X-API-Key": "wrong"})
        assert resp.status_code == 403

    def test_v1_endpoint_accepts_valid_key(self, client):
        resp = client.post("/v1/token", json={}, headers={"X-API-Key": "test-key-1"})
        assert resp.status_code == 200


class TestTokenEndpoint:
    def test_token_returns_info_without_secret(self, client):
        resp = client.post("/v1/token", json={}, headers={"X-API-Key": "test-key-1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["account"]["name"] == "main"
        assert data["account"]["appid"] == "wx_main"
        assert data["access_token"] == "token_for_wx_main"
        assert "secret" not in str(data)

    def test_token_specific_account(self, client):
        resp = client.post(
            "/v1/token",
            json={"account": "backup"},
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account"]["name"] == "backup"
        assert data["account"]["appid"] == "wx_backup"
        assert "secret" not in str(data)

    def test_token_unknown_account(self, client):
        resp = client.post(
            "/v1/token",
            json={"account": "ghost"},
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 400


class TestMediaEndpoints:
    def test_upload_cover(self, client):
        resp = client.post(
            "/v1/media/cover",
            files={"file": ("cover.jpg", b"image-data", "image/jpeg")},
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["media_id"] == "media_cover_123"

    def test_upload_inline(self, client):
        resp = client.post(
            "/v1/media/inline",
            files={"file": ("inline.png", b"image-data", "image/png")},
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://mmbiz.qpic.cn/inline123"


class TestDraftEndpoint:
    def test_create_draft_missing_thumb(self, client):
        resp = client.post(
            "/v1/draft",
            json={"title": "Test", "content_html": "<p>Hello</p>"},
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 422

    def test_create_draft_minimal_payload(self, client, fake_wechat):
        resp = client.post(
            "/v1/draft",
            json={
                "title": "中文标题",
                "content_html": "<p>正文内容</p>",
                "thumb_media_id": "thumb_001",
            },
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["media_id"] == "draft_456"
        assert fake_wechat.last_draft_payload == {
            "articles": [
                {
                    "title": "中文标题",
                    "content": "<p>正文内容</p>",
                    "thumb_media_id": "thumb_001",
                    "need_open_comment": 1,
                    "only_fans_can_comment": 0,
                    "author": "主账号",
                }
            ]
        }


class TestDraftSubmitEndpoint:
    def test_submit_draft(self, client):
        resp = client.post(
            "/v1/draft/submit",
            json={"media_id": "draft_123"},
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["publish_id"] == "publish_789"
