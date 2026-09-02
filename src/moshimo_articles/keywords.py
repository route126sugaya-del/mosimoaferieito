"""記事化する商品を検索するためのキーワード管理。"""
from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_KEYWORDS_PATH = Path("config/keywords.yaml")


def load_keywords(path: Path = DEFAULT_KEYWORDS_PATH) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    keywords = data.get("keywords", [])
    if not keywords:
        raise ValueError(f"{path} に keywords が1件も定義されていません。")
    return list(keywords)
