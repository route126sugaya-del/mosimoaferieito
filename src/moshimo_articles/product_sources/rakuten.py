"""楽天市場 商品検索API (IchibaItem Search) 連携。

API仕様: https://webservice.rakuten.co.jp/documentation/ichiba-item-search
無料・審査不要でアプリIDを発行できる。レート制限は1秒あたり1リクエストが目安。
"""
from __future__ import annotations

import logging

import requests

from moshimo_articles.config import RakutenConfig
from moshimo_articles.models import Product

logger = logging.getLogger(__name__)

_ENDPOINT = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"


def search_products(
    config: RakutenConfig,
    keyword: str,
    hits: int = 10,
    sort: str = "-reviewCount",
) -> list[Product]:
    """キーワードで楽天市場の商品を検索し、レビュー件数順(既定)で返す。"""
    if not config.is_configured:
        raise ValueError("RakutenConfig が未設定です(RAKUTEN_APP_ID が必要)。")

    params = {
        "applicationId": config.app_id,
        "keyword": keyword,
        "hits": min(hits, 30),
        "sort": sort,
        "imageFlag": 1,
        "format": "json",
    }
    if config.affiliate_id:
        params["affiliateId"] = config.affiliate_id

    response = requests.get(_ENDPOINT, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()

    if "error" in payload:
        raise RuntimeError(f"楽天API エラー: {payload.get('error_description', payload['error'])}")

    products: list[Product] = []
    for entry in payload.get("Items", []):
        item = entry.get("Item", {})
        image_urls = item.get("mediumImageUrls") or []
        image_url = image_urls[0].get("imageUrl") if image_urls else None
        # 楽天の画像URLは "?_ex=128x128" のようなサイズ指定が付くことがあるため取り除く
        if image_url and "?" in image_url:
            image_url = image_url.split("?", 1)[0]

        products.append(
            Product(
                source="rakuten",
                product_id=str(item.get("itemCode", item.get("itemUrl", ""))),
                name=item.get("itemName", ""),
                item_url=item.get("itemUrl", ""),
                price=item.get("itemPrice"),
                image_url=image_url,
                description=item.get("itemCaption", ""),
                shop_name=item.get("shopName"),
                review_average=item.get("reviewAverage"),
                review_count=item.get("reviewCount"),
            )
        )

    logger.info("楽天市場: キーワード「%s」で %d 件の商品を取得", keyword, len(products))
    return products
