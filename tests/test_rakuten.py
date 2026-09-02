"""楽天市場API連携のテスト。"""
from __future__ import annotations

import pytest

from moshimo_articles.config import MoshimoLinkConfig, RakutenConfig
from moshimo_articles.product_sources import rakuten

_EMPTY_LINK = MoshimoLinkConfig(a_id=None, p_id=None, pc_id=None, pl_id=None)


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def json(self):
        return self._payload


def _config() -> RakutenConfig:
    return RakutenConfig(app_id="dummy-app-id", affiliate_id=None, moshimo_link=_EMPTY_LINK)


def test_search_products_parses_items(monkeypatch):
    payload = {
        "Items": [
            {
                "Item": {
                    "itemCode": "shop:1001",
                    "itemName": "テスト商品",
                    "itemPrice": 1980,
                    "itemUrl": "https://item.rakuten.co.jp/shop/1001/",
                    "itemCaption": "説明文",
                    "shopName": "テストショップ",
                    "mediumImageUrls": [
                        {"imageUrl": "https://image.rakuten.co.jp/shop/cabinet/1001.jpg?_ex=128x128"}
                    ],
                    "reviewAverage": 4.5,
                    "reviewCount": 12,
                }
            }
        ]
    }

    def fake_get(url, params, timeout):
        assert params["applicationId"] == "dummy-app-id"
        assert params["keyword"] == "傘"
        return DummyResponse(payload)

    monkeypatch.setattr(rakuten.requests, "get", fake_get)

    products = rakuten.search_products(_config(), "傘")

    assert len(products) == 1
    product = products[0]
    assert product.source == "rakuten"
    assert product.product_id == "shop:1001"
    assert product.name == "テスト商品"
    assert product.price == 1980
    assert product.image_url == "https://image.rakuten.co.jp/shop/cabinet/1001.jpg"
    assert product.review_count == 12


def test_search_products_raises_on_api_error(monkeypatch):
    def fake_get(url, params, timeout):
        return DummyResponse({"error": "wrong_parameter", "error_description": "bad"})

    monkeypatch.setattr(rakuten.requests, "get", fake_get)

    with pytest.raises(RuntimeError):
        rakuten.search_products(_config(), "傘")


def test_search_products_requires_app_id():
    config = RakutenConfig(app_id=None, affiliate_id=None, moshimo_link=_EMPTY_LINK)
    with pytest.raises(ValueError):
        rakuten.search_products(config, "傘")
