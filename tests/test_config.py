"""環境変数からの設定読み込みのテスト。"""
from __future__ import annotations

import pytest

from moshimo_articles import config as config_module

_ALL_VARS = [
    "RAKUTEN_APP_ID",
    "RAKUTEN_ACCESS_KEY",
    "RAKUTEN_REFERER",
    "RAKUTEN_AFFILIATE_ID",
    "AMAZON_CREDENTIAL_ID",
    "AMAZON_CREDENTIAL_SECRET",
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
    "PRODUCTS_PER_RUN",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in _ALL_VARS:
        monkeypatch.delenv(name, raising=False)


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "access-key")
    monkeypatch.setenv("RAKUTEN_REFERER", "https://example.com")

    cfg = config_module.load_config()

    assert cfg.rakuten.is_configured is True
    assert cfg.amazon.is_configured is False
    assert cfg.products_per_run == 1


def test_load_config_with_no_env_does_not_raise():
    # 商品ソース(楽天/Amazon)はmain側でチェックするため、config自体は必須項目を持たない。
    cfg = config_module.load_config()

    assert cfg.rakuten.is_configured is False
    assert cfg.amazon.is_configured is False


def test_get_treats_empty_string_as_unset(monkeypatch):
    monkeypatch.setenv("PRODUCTS_PER_RUN", "")
    assert config_module._get("PRODUCTS_PER_RUN", default="fallback") == "fallback"
