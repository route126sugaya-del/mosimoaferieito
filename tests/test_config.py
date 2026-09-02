"""環境変数からの設定読み込みのテスト。"""
from __future__ import annotations

import pytest

from moshimo_articles import config as config_module

_REQUIRED_VARS = [
    "ANTHROPIC_API_KEY",
    "CLAUDE_MODEL",
    "RAKUTEN_APP_ID",
    "RAKUTEN_AFFILIATE_ID",
    "AMAZON_ACCESS_KEY",
    "AMAZON_SECRET_KEY",
    "AMAZON_PARTNER_TAG",
    "AMAZON_COUNTRY",
    "MOSHIMO_RAKUTEN_A_ID",
    "MOSHIMO_RAKUTEN_P_ID",
    "MOSHIMO_RAKUTEN_PC_ID",
    "MOSHIMO_RAKUTEN_PL_ID",
    "MOSHIMO_AMAZON_A_ID",
    "MOSHIMO_AMAZON_P_ID",
    "MOSHIMO_AMAZON_PC_ID",
    "MOSHIMO_AMAZON_PL_ID",
    "WP_BASE_URL",
    "WP_USERNAME",
    "WP_APP_PASSWORD",
    "WP_POST_STATUS",
    "ARTICLES_PER_RUN",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in _REQUIRED_VARS:
        monkeypatch.delenv(name, raising=False)


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("WP_BASE_URL", "https://example.com/")
    monkeypatch.setenv("WP_USERNAME", "admin")
    monkeypatch.setenv("WP_APP_PASSWORD", "app-pass")

    cfg = config_module.load_config()

    assert cfg.anthropic_api_key == "sk-test"
    assert cfg.claude_model == "claude-sonnet-5"
    assert cfg.wordpress.base_url == "https://example.com"
    assert cfg.articles_per_run == 1
    assert cfg.rakuten.is_configured is False
    assert cfg.amazon.is_configured is False


def test_load_config_missing_required_raises():
    with pytest.raises(config_module.ConfigError):
        config_module.load_config()


def test_get_treats_empty_string_as_unset(monkeypatch):
    monkeypatch.setenv("CLAUDE_MODEL", "")
    assert config_module._get("CLAUDE_MODEL", default="fallback") == "fallback"
