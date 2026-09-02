"""Amazon Product Advertising API (PA-API 5.0) 連携。

python-amazon-paapi (https://github.com/sergioteula/python-amazon-paapi) を利用する。
PA-APIのアクセスキーは「直近180日で3件以上の紹介実績」が無いと失効するため、
新規サイトでは楽天市場APIを主データソースにすることを推奨する。
"""
from __future__ import annotations

import logging

from moshimo_articles.config import AmazonConfig
from moshimo_articles.models import Product

logger = logging.getLogger(__name__)


def search_products(config: AmazonConfig, keyword: str, hits: int = 10) -> list[Product]:
    """キーワードでAmazonの商品を検索する。"""
    if not config.is_configured:
        raise ValueError(
            "AmazonConfig が未設定です(AMAZON_ACCESS_KEY / AMAZON_SECRET_KEY / AMAZON_PARTNER_TAG が必要)。"
        )

    try:
        from amazon_paapi import AmazonApi
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "python-amazon-paapi がインストールされていません。`pip install python-amazon-paapi` を実行してください。"
        ) from exc

    api = AmazonApi(
        config.access_key,
        config.secret_key,
        config.partner_tag,
        config.country,
        throttling=1.0,
    )

    result = api.search_items(keywords=keyword, item_count=min(hits, 10))
    items = getattr(result, "items", None) or []

    products: list[Product] = []
    for item in items:
        products.append(_to_product(item))

    logger.info("Amazon: キーワード「%s」で %d 件の商品を取得", keyword, len(products))
    return products


def _to_product(item) -> Product:
    title = _safe_get(item, "item_info", "title", "display_value") or ""
    image_url = _safe_get(item, "images", "primary", "large", "url")
    price = _safe_get(item, "offers", "listings", 0, "price", "amount")
    detail_url = getattr(item, "detail_page_url", None) or ""

    features = _safe_get(item, "item_info", "features", "display_values") or []
    description = " / ".join(features) if features else ""

    return Product(
        source="amazon",
        product_id=getattr(item, "asin", ""),
        name=title,
        item_url=detail_url,
        price=int(price) if price is not None else None,
        image_url=image_url,
        description=description,
        shop_name="Amazon.co.jp",
    )


def _safe_get(obj, *path):
    """ネストした属性/添字アクセスを None セーフに行う。"""
    current = obj
    for key in path:
        if current is None:
            return None
        if isinstance(key, int):
            try:
                current = current[key]
            except (IndexError, TypeError):
                return None
        else:
            current = getattr(current, key, None)
    return current
