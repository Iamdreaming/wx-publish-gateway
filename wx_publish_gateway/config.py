"""Configuration for wx-publish-gateway."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, Optional

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings


class AccountConfig(BaseModel):
    """WeChat Official Account credentials."""

    appid: str
    secret: str
    author: Optional[str] = None


class Settings(BaseSettings):
    """Application settings from init kwargs and WXPG_* environment variables."""

    model_config = {"env_prefix": "", "extra": "ignore"}

    api_keys: list[str] = Field(default_factory=list)
    default_account: Optional[str] = None
    accounts_json: Optional[str] = None
    wechat_base_url: str = "https://api.weixin.qq.com"
    service_name: str = "wx-publish-gateway"

    def __init__(self, **data):
        data.setdefault("api_keys", _parse_api_keys(os.getenv("WXPG_API_KEYS")))
        data.setdefault("default_account", os.getenv("WXPG_DEFAULT_ACCOUNT"))
        data.setdefault("accounts_json", os.getenv("WXPG_ACCOUNTS_JSON"))
        data.setdefault("wechat_base_url", os.getenv("WXPG_WECHAT_BASE_URL", "https://api.weixin.qq.com"))
        data.setdefault("service_name", os.getenv("WXPG_SERVICE_NAME", "wx-publish-gateway"))
        super().__init__(**data)

    @model_validator(mode="after")
    def _validate_accounts_json(self) -> "Settings":
        if self.accounts_json:
            self._parse_accounts()
        return self

    @property
    def accounts(self) -> Dict[str, AccountConfig]:
        return self._parse_accounts()

    def _parse_accounts(self) -> Dict[str, AccountConfig]:
        if not self.accounts_json:
            return {}
        try:
            raw = json.loads(self.accounts_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid accounts JSON in WXPG_ACCOUNTS_JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError("Invalid accounts JSON in WXPG_ACCOUNTS_JSON: expected object")
        return {name: AccountConfig(**cfg) for name, cfg in raw.items()}

    def get_account(self, name: str) -> AccountConfig:
        accounts = self.accounts
        if name not in accounts:
            raise ValueError(f"Unknown account '{name}'. Available: {list(accounts.keys())}")
        return accounts[name]

    def get_default_account(self) -> Optional[AccountConfig]:
        if not self.default_account:
            return None
        return self.get_account(self.default_account)

    def resolve_account(self, account_name: Optional[str] = None) -> AccountConfig:
        name = account_name or self.default_account
        if not name:
            raise ValueError("No account specified and no WXPG_DEFAULT_ACCOUNT configured")
        return self.get_account(name)


def _parse_api_keys(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached Settings singleton."""
    return Settings()
