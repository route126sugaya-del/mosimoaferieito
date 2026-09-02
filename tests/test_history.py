"""履歴管理(重複投稿防止)のテスト。"""
from __future__ import annotations

from pathlib import Path

from moshimo_articles.history import PublishedHistory


def test_history_round_trip(tmp_path: Path):
    history_path = tmp_path / "history.json"
    history = PublishedHistory(path=history_path)

    assert not history.has_published("rakuten:1001")

    history.record("rakuten:1001", "テスト記事", "https://example.com/1")
    history.save()

    assert history_path.exists()

    reloaded = PublishedHistory(path=history_path)
    assert reloaded.has_published("rakuten:1001")


def test_history_missing_file_returns_empty(tmp_path: Path):
    history_path = tmp_path / "does_not_exist.json"
    history = PublishedHistory(path=history_path)

    assert history.has_published("rakuten:1001") is False
