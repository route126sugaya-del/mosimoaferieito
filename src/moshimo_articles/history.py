"""生成済み商品の履歴管理(同じ商品を何度も記事化しないための重複排除)。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_PATH = Path("data/published_history.json")


class PublishedHistory:
    def __init__(self, path: Path = DEFAULT_HISTORY_PATH):
        self._path = path
        self._entries: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def has_published(self, key: str) -> bool:
        return key in self._entries

    def record(self, key: str, title: str, wordpress_url: str | None = None) -> None:
        self._entries[key] = {
            "title": title,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "wordpress_url": wordpress_url,
        }

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2, sort_keys=True)
        logger.info("履歴を保存しました: %s (%d件)", self._path, len(self._entries))
