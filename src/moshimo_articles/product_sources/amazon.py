"""Amazon Creators API 連携。

2026年5月にAmazon Product Advertising API (PA-API) v5が完全に終了し、
後継の Amazon Creators API への移行が必須となった。認証方式もAWS Signature V4から
OAuth 2.0(credential_id / credential_secret)に変わっている。
python-amazon-paapi (https://github.com/sergioteula/python-amazon-paapi) の
amazon_creatorsapi モジュールを利用する。認証情報はAmazonアソシエイト管理画面の
「CreatorsAPI」タブから新規に発行する(旧PA-APIのアクセスキーは使えない)。
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
            "AmazonConfig が未設定です"
            "(AMAZON_CREDENTIAL_ID / AMAZON_CREDENTIAL_SECRET / AMAZON_PARTNER_TAG が必要)。"
        )

    try:
        from amazon_creatorsapi import AmazonCreatorsApi, Country
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "python-amazon-paapi がインストールされていません。`pip install python-amazon-paapi` を実行してください。"
        ) from exc

    country = getattr(Country, config.country.upper(), None)
    if country is None:
        raise ValueError(f"Amazon Creators APIが未対応の国コードです: {config.country}")

    api = AmazonCreatorsApi(
        credential_id=config.credential_id,
        credential_secret=config.credential_secret,
        version="2.2",
        tag=config.partner_tag,
        country=country,
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
    price = _safe_get(item, "offers_v2", "listings", 0, "price", "money", "amount")
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
