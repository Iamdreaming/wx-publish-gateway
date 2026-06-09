"""Tests for API key authentication."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from wx_publish_gateway.auth import verify_api_key


class TestVerifyApiKey:
    def test_valid_key_allowed(self):
        app = FastAPI()
        valid_keys = ["key1", "key2"]

        @app.get("/v1/test")
        def endpoint(_auth=verify_api_key(valid_keys)):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/v1/test", headers={"X-API-Key": "key1"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_invalid_key_rejected(self):
        app = FastAPI()
        valid_keys = ["key1", "key2"]

        @app.get("/v1/test")
        def endpoint(_auth=verify_api_key(valid_keys)):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/v1/test", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 403
        assert "Invalid" in resp.json()["detail"]

    def test_missing_header_rejected(self):
        app = FastAPI()
        valid_keys = ["key1"]

        @app.get("/v1/test")
        def endpoint(_auth=verify_api_key(valid_keys)):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/v1/test")
        assert resp.status_code == 403

    def test_empty_keys_allows_none(self):
        """When no API keys configured, auth should allow all (or reject all)."""
        app = FastAPI()
        valid_keys = []

        @app.get("/v1/test")
        def endpoint(_auth=verify_api_key(valid_keys)):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/v1/test", headers={"X-API-Key": "anything"})
        # With empty keys, no key can match, so should be 403
        assert resp.status_code == 403
