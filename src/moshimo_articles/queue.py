"""記事化候補の商品をキューとして管理する。

記事の執筆自体はこのリポジトリでは行わない(2026-10-12 方針変更)。
note-blog-auto側のClaude実行が、このキュー(data/product_queue.json)を読み、
既存ブログの文体・カテゴリ運用ルールに沿って商品紹介記事を書く。
status が "pending" のエントリが未着手、"used" が記事化済み。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_PATH = Path("data/product_queue.json")


class ProductQueue:
    def __init__(self, path: Path = DEFAULT_QUEUE_PATH):
        self._path = path
        self._entries: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def has_entry(self, key: str) -> bool:
        """既にキューに追加済み(pending/used問わず)かどうか。重複追加を避けるために使う。"""
        return key in self._entries

    def add(self, key: str, data: dict) -> None:
        self._entries[key] = {
            **data,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2, sort_keys=True)
        logger.info("商品キューを保存しました: %s (%d件)", self._path, len(self._entries))
