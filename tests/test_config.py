"""Tests for configuration parsing."""

import json
import os
from unittest.mock import patch

import pytest

from wx_publish_gateway.config import Settings, get_settings


class TestSettingsFromEnv:
    """Test that Settings correctly parses environment variables."""

    def test_minimal_config(self, monkeypatch):
        monkeypatch.delenv("WXPG_API_KEYS", raising=False)
        monkeypatch.delenv("WXPG_DEFAULT_ACCOUNT", raising=False)
        monkeypatch.delenv("WXPG_ACCOUNTS_JSON", raising=False)
        monkeypatch.delenv("WXPG_WECHAT_BASE_URL", raising=False)
        s = Settings()
        assert s.api_keys == []
        assert s.default_account is None
        assert s.accounts == {}
        assert s.wechat_base_url == "https://api.weixin.qq.com"
        assert s.service_name == "wx-publish-gateway"

    def test_api_keys_parsed(self, monkeypatch):
        monkeypatch.setenv("WXPG_API_KEYS", "key1,key2,key3")
        monkeypatch.delenv("WXPG_DEFAULT_ACCOUNT", raising=False)
        monkeypatch.delenv("WXPG_ACCOUNTS_JSON", raising=False)
        monkeypatch.delenv("WXPG_WECHAT_BASE_URL", raising=False)
        s = Settings()
        assert s.api_keys == ["key1", "key2", "key3"]

    def test_single_api_key(self, monkeypatch):
        monkeypatch.setenv("WXPG_API_KEYS", "only-key")
        monkeypatch.delenv("WXPG_DEFAULT_ACCOUNT", raising=False)
        monkeypatch.delenv("WXPG_ACCOUNTS_JSON", raising=False)
        monkeypatch.delenv("WXPG_WECHAT_BASE_URL", raising=False)
        s = Settings()
        assert s.api_keys == ["only-key"]

    def test_accounts_json_parsed(self, monkeypatch):
        accounts = {
            "main": {"appid": "wx123", "secret": "sec123", "author": "张三"},
            "backup": {"appid": "wx456", "secret": "sec456"},
        }
        monkeypatch.setenv("WXPG_ACCOUNTS_JSON", json.dumps(accounts))
        monkeypatch.delenv("WXPG_API_KEYS", raising=False)
        monkeypatch.delenv("WXPG_DEFAULT_ACCOUNT", raising=False)
        monkeypatch.delenv("WXPG_WECHAT_BASE_URL", raising=False)
        s = Settings()
        assert s.accounts["main"].appid == "wx123"
        assert s.accounts["main"].secret == "sec123"
        assert s.accounts["main"].author == "张三"
        assert s.accounts["backup"].appid == "wx456"
        assert s.accounts["backup"].author is None

    def test_default_account(self, monkeypatch):
        monkeypatch.setenv("WXPG_DEFAULT_ACCOUNT", "main")
        monkeypatch.delenv("WXPG_API_KEYS", raising=False)
        monkeypatch.delenv("WXPG_ACCOUNTS_JSON", raising=False)
        monkeypatch.delenv("WXPG_WECHAT_BASE_URL", raising=False)
        s = Settings()
        assert s.default_account == "main"

    def test_custom_wechat_base_url(self, monkeypatch):
        monkeypatch.setenv("WXPG_WECHAT_BASE_URL", "https://mock.weixin.com")
        monkeypatch.delenv("WXPG_API_KEYS", raising=False)
        monkeypatch.delenv("WXPG_DEFAULT_ACCOUNT", raising=False)
        monkeypatch.delenv("WXPG_ACCOUNTS_JSON", raising=False)
        s = Settings()
        assert s.wechat_base_url == "https://mock.weixin.com"

    def test_get_settings_caches(self, monkeypatch):
        monkeypatch.setenv("WXPG_API_KEYS", "k1")
        monkeypatch.delenv("WXPG_DEFAULT_ACCOUNT", raising=False)
        monkeypatch.delenv("WXPG_ACCOUNTS_JSON", raising=False)
        monkeypatch.delenv("WXPG_WECHAT_BASE_URL", raising=False)
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestConfigEdgeCases:
    def test_invalid_accounts_json(self, monkeypatch):
        monkeypatch.setenv("WXPG_ACCOUNTS_JSON", "not valid json}{")
        monkeypatch.delenv("WXPG_API_KEYS", raising=False)
        monkeypatch.delenv("WXPG_DEFAULT_ACCOUNT", raising=False)
        monkeypatch.delenv("WXPG_WECHAT_BASE_URL", raising=False)
        with pytest.raises(ValueError, match="accounts"):
            Settings()

    def test_unknown_account_selection(self):
        settings = Settings(default_account="nonexistent")
        with pytest.raises(ValueError, match="nonexistent"):
            settings.get_account("nonexistent")
