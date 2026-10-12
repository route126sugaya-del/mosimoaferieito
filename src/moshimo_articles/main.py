"""商品検索〜もしもアフィリエイトリンク生成〜キュー保存までを実行するエントリポイント。

記事の執筆・WordPress投稿はこのリポジトリでは行わない(2026-10-12方針変更)。
note-blog-auto側のClaude実行が、ここで積んだキュー(data/product_queue.json)を
読み、既存ブログ(kamidera.com)の文体・カテゴリ運用ルールに沿って記事を書く。

使い方:
    python -m moshimo_articles.main
"""
from __future__ import annotations

import dataclasses
import logging
import random
import sys

from moshimo_articles.affiliate.moshimo import MoshimoLinkNotConfiguredError, build_link_for_product
from moshimo_articles.config import Config, ConfigError, load_config
from moshimo_articles.keywords import load_keywords
from moshimo_articles.models import Product
from moshimo_articles.product_sources import amazon as amazon_source
from moshimo_articles.product_sources import rakuten as rakuten_source
from moshimo_articles.queue import ProductQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def collect_candidates(config: Config, keyword: str) -> list[Product]:
    """設定済みの商品ソース(楽天/Amazon)からキーワードに合う商品を集める。"""
    candidates: list[Product] = []

    if config.rakuten.is_configured:
        try:
            candidates.extend(rakuten_source.search_products(config.rakuten, keyword))
        except Exception:
            logger.exception("楽天市場APIでの商品検索に失敗しました(keyword=%s)", keyword)

    if config.amazon.is_configured:
        try:
            candidates.extend(amazon_source.search_products(config.amazon, keyword))
        except Exception:
            logger.exception("Amazon Creators APIでの商品検索に失敗しました(keyword=%s)", keyword)

    return candidates


def pick_new_product(candidates: list[Product], queue: ProductQueue) -> Product | None:
    """まだキューに入れていない商品を、レビュー数順(=検索結果の順序)で先頭から選ぶ。"""
    for product in candidates:
        if product.item_url and not queue.has_entry(product.key):
            return product
    return None


def enqueue_one_product(config: Config, product: Product, queue: ProductQueue) -> bool:
    """1商品についてもしもリンクを生成し、キューに積む。成功したらTrue。"""
    try:
        affiliate_link = build_link_for_product(product, config)
    except MoshimoLinkNotConfiguredError:
        logger.exception("もしもアフィリエイトリンクの生成に失敗しました(product=%s)", product.name)
        return False

    entry = dataclasses.asdict(product)
    entry["affiliate_url"] = affiliate_link
    queue.add(product.key, entry)
    return True


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("設定エラー: %s", exc)
        return 1

    if not config.rakuten.is_configured and not config.amazon.is_configured:
        logger.error("楽天市場・Amazonのどちらの商品ソースも未設定です。.env.example を参照してください。")
        return 1

    keywords = load_keywords()
    queue = ProductQueue()

    added = 0
    attempts = 0
    max_attempts = max(config.products_per_run * 5, 10)
    shuffled_keywords = random.sample(keywords, k=len(keywords))

    while added < config.products_per_run and attempts < max_attempts:
        keyword = shuffled_keywords[attempts % len(shuffled_keywords)]
        attempts += 1

        candidates = collect_candidates(config, keyword)
        product = pick_new_product(candidates, queue)
        if product is None:
            logger.info("キーワード「%s」では未登録の商品が見つかりませんでした", keyword)
            continue

        if enqueue_one_product(config, product, queue):
            added += 1

    queue.save()

    logger.info("完了: %d/%d 件の商品をキューに追加しました", added, config.products_per_run)
    return 0 if added > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
