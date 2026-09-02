"""Amazon PA-API連携のテスト(ライブラリ内部構造への依存部分)。"""
from __future__ import annotations

from types import SimpleNamespace

from moshimo_articles.product_sources.amazon import _safe_get, _to_product


def test_safe_get_returns_none_for_missing_attribute():
    obj = SimpleNamespace(a=SimpleNamespace(b=None))
    assert _safe_get(obj, "a", "b", "c") is None


def test_safe_get_traverses_nested_attributes_and_index():
    obj = SimpleNamespace(listings=[SimpleNamespace(price=SimpleNamespace(amount=1980))])
    assert _safe_get(obj, "listings", 0, "price", "amount") == 1980


def test_to_product_maps_fields():
    item = SimpleNamespace(
        asin="B000000000",
        detail_page_url="https://www.amazon.co.jp/dp/B000000000",
        item_info=SimpleNamespace(
            title=SimpleNamespace(display_value="テスト商品"),
            features=SimpleNamespace(display_values=["特徴1", "特徴2"]),
        ),
        images=SimpleNamespace(primary=SimpleNamespace(large=SimpleNamespace(url="https://example.com/img.jpg"))),
        offers=SimpleNamespace(listings=[SimpleNamespace(price=SimpleNamespace(amount=1980))]),
    )

    product = _to_product(item)

    assert product.source == "amazon"
    assert product.product_id == "B000000000"
    assert product.name == "テスト商品"
    assert product.price == 1980
    assert product.image_url == "https://example.com/img.jpg"
    assert product.description == "特徴1 / 特徴2"
