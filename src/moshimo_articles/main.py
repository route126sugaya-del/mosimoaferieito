"""記事生成〜WordPress投稿までの一連の処理を実行するエントリポイント。

使い方:
    python -m moshimo_articles.main
"""
from __future__ import annotations

import logging
import random
import sys

from moshimo_articles.affiliate.moshimo import MoshimoLinkNotConfiguredError, build_link_for_product
from moshimo_articles.config import Config, ConfigError, load_config
from moshimo_articles.content.generator import generate_article
from moshimo_articles.history import PublishedHistory
from moshimo_articles.keywords import load_keywords
from moshimo_articles.models import Product
from moshimo_articles.product_sources import amazon as amazon_source
from moshimo_articles.product_sources import rakuten as rakuten_source
from moshimo_articles.publish.wordpress import WordPressClient

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


def pick_unpublished_product(candidates: list[Product], history: PublishedHistory) -> Product | None:
    """まだ記事化していない商品を、レビュー数順(=検索結果の順序)で先頭から選ぶ。"""
    for product in candidates:
        if product.item_url and not history.has_published(product.key):
            return product
    return None


def process_one_article(
    config: Config,
    product: Product,
    history: PublishedHistory,
    wp_client: WordPressClient,
) -> bool:
    """1商品について記事生成〜投稿〜履歴記録までを行う。成功したらTrue。"""
    try:
        affiliate_link = build_link_for_product(product, config)
    except MoshimoLinkNotConfiguredError:
        logger.exception("もしもアフィリエイトリンクの生成に失敗しました(product=%s)", product.name)
        return False

    try:
        article = generate_article(
            product=product,
            affiliate_link=affiliate_link,
            api_key=config.anthropic_api_key,
            model=config.claude_model,
        )
    except Exception:
        logger.exception("記事生成に失敗しました(product=%s)", product.name)
        return False

    try:
        result = wp_client.create_post(article, product)
    except Exception:
        logger.exception("WordPressへの投稿に失敗しました(product=%s)", product.name)
        return False

    history.record(product.key, article.title, result.get("link"))
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
    history = PublishedHistory()
    wp_client = WordPressClient(config.wordpress)

    generated = 0
    attempts = 0
    max_attempts = max(config.articles_per_run * 5, 10)
    shuffled_keywords = random.sample(keywords, k=len(keywords))

    while generated < config.articles_per_run and attempts < max_attempts:
        keyword = shuffled_keywords[attempts % len(shuffled_keywords)]
        attempts += 1

        candidates = collect_candidates(config, keyword)
        product = pick_unpublished_product(candidates, history)
        if product is None:
            logger.info("キーワード「%s」では未紹介の商品が見つかりませんでした", keyword)
            continue

        if process_one_article(config, product, history, wp_client):
            generated += 1

    history.save()

    logger.info("完了: %d/%d 件の記事を生成しました", generated, config.articles_per_run)
    return 0 if generated > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
