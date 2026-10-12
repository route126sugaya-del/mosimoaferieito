"""商品キュー(重複排除・保存)のテスト。"""
from __future__ import annotations

from pathlib import Path

from moshimo_articles.queue import ProductQueue


def test_queue_round_trip(tmp_path: Path):
    queue_path = tmp_path / "queue.json"
    queue = ProductQueue(path=queue_path)

    assert not queue.has_entry("rakuten:1001")

    queue.add("rakuten:1001", {"name": "テスト商品", "affiliate_url": "https://example.com/1"})
    queue.save()

    assert queue_path.exists()

    reloaded = ProductQueue(path=queue_path)
    assert reloaded.has_entry("rakuten:1001")


def test_queue_add_sets_pending_status(tmp_path: Path):
    queue = ProductQueue(path=tmp_path / "queue.json")
    queue.add("rakuten:1001", {"name": "テスト商品"})
    queue.save()

    reloaded = ProductQueue(path=tmp_path / "queue.json")
    assert reloaded._entries["rakuten:1001"]["status"] == "pending"


def test_queue_missing_file_returns_empty(tmp_path: Path):
    queue_path = tmp_path / "does_not_exist.json"
    queue = ProductQueue(path=queue_path)

    assert queue.has_entry("rakuten:1001") is False
