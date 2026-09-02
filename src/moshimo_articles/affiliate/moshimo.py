"""もしもアフィリエイトの成果測定URL(af.moshimo.com/af/c/click)を組み立てる。

もしもアフィリエイトの管理画面で各広告主(楽天市場・Amazon等)と提携すると、
「広告リンクタグ」からその提携固有の a_id / p_id / pc_id / pl_id が発行される。
これらに任意の遷移先URL(商品ページのURL)を `url` パラメータとして付与すると、
その商品ページへ直接アフィリエイトリンクを張れる(WordPressテーマ等が内部で
使っているのと同じ仕組み)。

参考: もしもアフィリエイトの広告リンクタグは
`https://af.moshimo.com/af/c/click?a_id=...&p_id=...&pc_id=...&pl_id=...` の形式で発行される。
"""
from __future__ import annotations

from urllib.parse import quote

from moshimo_articles.config import Config, MoshimoLinkConfig
from moshimo_articles.models import Product

_CLICK_ENDPOINT = "https://af.moshimo.com/af/c/click"


class MoshimoLinkNotConfiguredError(RuntimeError):
    """該当ソースのもしもアフィリエイトIDが未設定の場合に送出する。"""


def build_link(destination_url: str, link_config: MoshimoLinkConfig) -> str:
    """通常の商品URLをもしもアフィリエイト経由のリンクに変換する。"""
    if not link_config.is_configured:
        raise MoshimoLinkNotConfiguredError(
            "もしもアフィリエイトの a_id/p_id/pc_id/pl_id が設定されていません。"
            ".env.example を参照し、管理画面の広告リンクタグから値を取得してください。"
        )

    encoded_url = quote(destination_url, safe="")
    return (
        f"{_CLICK_ENDPOINT}?a_id={link_config.a_id}&p_id={link_config.p_id}"
        f"&pc_id={link_config.pc_id}&pl_id={link_config.pl_id}&url={encoded_url}"
    )


def build_link_for_product(product: Product, config: Config) -> str:
    """商品の取得元(楽天/Amazon)に応じたもしもリンクを組み立てる。"""
    if product.source == "rakuten":
        link_config = config.rakuten.moshimo_link
    elif product.source == "amazon":
        link_config = config.amazon.moshimo_link
    else:
        raise ValueError(f"未対応の商品ソースです: {product.source}")

    return build_link(product.item_url, link_config)
