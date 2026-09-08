"""もしもアフィリエイトリンク変換のテスト。"""
from __future__ import annotations

import pytest

from moshimo_articles.affiliate.moshimo import (
    MoshimoLinkNotConfiguredError,
    build_link,
    build_link_for_product,
)
from moshimo_articles.config import (
    AmazonConfig,
    Config,
    MoshimoLinkConfig,
    RakutenConfig,
    WordPressConfig,
)
from moshimo_articles.models import Product

_EMPTY_LINK = MoshimoLinkConfig(a_id=None, p_id=None, pc_id=None, pl_id=None)


def test_build_link_encodes_destination_url():
    link_config = MoshimoLinkConfig(a_id="1", p_id="2", pc_id="3", pl_id="4")
    url = build_link("https://item.rakuten.co.jp/shop/item001/", link_config)

    assert url.startswith("https://af.moshimo.com/af/c/click?a_id=1&p_id=2&pc_id=3&pl_id=4&url=")
    assert "https%3A%2F%2Fitem.rakuten.co.jp%2Fshop%2Fitem001%2F" in url


def test_build_link_raises_when_not_configured():
    with pytest.raises(MoshimoLinkNotConfiguredError):
        build_link("https://example.com", _EMPTY_LINK)


def _make_config(rakuten_link=None, amazon_link=None) -> Config:
    return Config(
        anthropic_api_key="key",
        claude_model="claude-sonnet-5",
        rakuten=RakutenConfig(
            app_id="app", access_key="access-key", affiliate_id=None, moshimo_link=rakuten_link or _EMPTY_LINK
        ),
        amazon=AmazonConfig(
            credential_id="cid",
            credential_secret="csecret",
            partner_tag="t",
            country="JP",
            moshimo_link=amazon_link or _EMPTY_LINK,
        ),
        wordpress=WordPressConfig(
            base_url="https://example.com", username="u", app_password="p", post_status="draft"
        ),
        articles_per_run=1,
    )


def test_build_link_for_product_selects_rakuten_config():
    rakuten_link = MoshimoLinkConfig(a_id="1", p_id="2", pc_id="3", pl_id="4")
    config = _make_config(rakuten_link=rakuten_link)
    product = Product(source="rakuten", product_id="x", name="test", item_url="https://item.rakuten.co.jp/x/")

    link = build_link_for_product(product, config)

    assert "a_id=1" in link


def test_build_link_for_product_selects_amazon_config():
    amazon_link = MoshimoLinkConfig(a_id="9", p_id="8", pc_id="7", pl_id="6")
    config = _make_config(amazon_link=amazon_link)
    product = Product(source="amazon", product_id="x", name="test", item_url="https://www.amazon.co.jp/dp/x/")

    link = build_link_for_product(product, config)

    assert "a_id=9" in link


def test_build_link_for_product_unknown_source_raises():
    config = _make_config()
    product = Product(source="unknown", product_id="x", name="test", item_url="https://example.com")

    with pytest.raises(ValueError):
        build_link_for_product(product, config)
