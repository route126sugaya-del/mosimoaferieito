"""楽天市場 商品検索API (IchibaItem Search) 連携。

API仕様: https://webservice.rakuten.co.jp/documentation/ichiba-item-search
2026年2月の認証システム刷新により、旧来の applicationId のみのリクエストは
非推奨となった。新規にアプリ登録をやり直して発行される applicationId と
accessKey(pk_から始まる値)の両方が必須。また新APIはリクエスト元を
検証するため、事前にアプリ管理画面の「許可されたWebサイト」に登録した
ドメインを Referer ヘッダーとして送信する必要がある(RAKUTEN_REFERER)。
レート制限は1秒あたり1リクエストが上限のため、呼び出し間隔を自動で空ける。
"""
from __future__ import annotations

import logging
import time

import requests

from moshimo_articles.config import RakutenConfig
from moshimo_articles.models import Product

logger = logging.getLogger(__name__)

_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
_MIN_REQUEST_INTERVAL_SECONDS = 1.0

_last_request_at: float = 0.0


def _throttle() -> None:
    """楽天APIのレート制限(1秒1リクエスト目安)に抵触しないよう間隔を空ける。"""
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)
    _last_request_at = time.monotonic()


def search_products(
    config: RakutenConfig,
    keyword: str,
    hits: int = 10,
    sort: str = "-reviewCount",
) -> list[Product]:
    """キーワードで楽天市場の商品を検索し、レビュー件数順(既定)で返す。"""
    if not config.is_configured:
        raise ValueError(
            "RakutenConfig が未設定です(RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_REFERER が必要)。"
        )

    params = {
        "applicationId": config.app_id,
        "accessKey": config.access_key,
        "keyword": keyword,
        "hits": min(hits, 30),
        "sort": sort,
        "imageFlag": 1,
        "format": "json",
    }
    if config.affiliate_id:
        params["affiliateId"] = config.affiliate_id

    _throttle()
    response = requests.get(
        _ENDPOINT,
        params=params,
        headers={"Referer": config.referer},
        timeout=15,
    )
    if not response.ok:
        raise RuntimeError(
            f"楽天API エラー: HTTP {response.status_code} - {response.text[:500]}"
        )
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
