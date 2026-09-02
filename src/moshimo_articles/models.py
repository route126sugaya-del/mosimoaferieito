"""データモデル定義。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Product:
    """商品データソース(楽天/Amazon)から取得した商品情報。"""

    source: str  # "rakuten" or "amazon"
    product_id: str
    name: str
    item_url: str
    price: int | None = None
    image_url: str | None = None
    description: str = ""
    shop_name: str | None = None
    review_average: float | None = None
    review_count: int | None = None

    @property
    def key(self) -> str:
        """履歴管理・重複排除に使う一意キー。"""
        return f"{self.source}:{self.product_id}"


@dataclass
class GeneratedArticle:
    """Claude APIが生成した記事本文。"""

    title: str
    body_html: str
    excerpt: str
    meta_description: str
    tags: list[str] = field(default_factory=list)
