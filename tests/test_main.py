"""main.pyのオーケストレーションロジックのテスト。"""
from __future__ import annotations

from moshimo_articles import main as main_module
from moshimo_articles.models import Product
from moshimo_articles.queue import ProductQueue


def test_pick_new_product_skips_entries_already_in_queue(tmp_path):
    queue = ProductQueue(path=tmp_path / "queue.json")
    already_queued = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")
    queue.add(already_queued.key, {"name": "A"})

    fresh = Product(source="rakuten", product_id="2", name="B", item_url="https://example.com/2")

    picked = main_module.pick_new_product([already_queued, fresh], queue)

    assert picked is fresh


def test_pick_new_product_returns_none_when_all_queued(tmp_path):
    queue = ProductQueue(path=tmp_path / "queue.json")
    already_queued = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")
    queue.add(already_queued.key, {"name": "A"})

    picked = main_module.pick_new_product([already_queued], queue)

    assert picked is None


def test_pick_new_product_skips_products_without_url(tmp_path):
    queue = ProductQueue(path=tmp_path / "queue.json")
    no_url = Product(source="rakuten", product_id="1", name="A", item_url="")

    picked = main_module.pick_new_product([no_url], queue)

    assert picked is None


def test_enqueue_one_product_adds_entry_with_affiliate_url(tmp_path, monkeypatch):
    queue = ProductQueue(path=tmp_path / "queue.json")
    product = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")

    monkeypatch.setattr(main_module, "build_link_for_product", lambda product, config: "https://af.moshimo.com/x")

    result = main_module.enqueue_one_product(config=object(), product=product, queue=queue)

    assert result is True
    assert queue.has_entry(product.key)
    assert queue._entries[product.key]["affiliate_url"] == "https://af.moshimo.com/x"


def test_enqueue_one_product_returns_false_when_link_not_configured(tmp_path, monkeypatch):
    queue = ProductQueue(path=tmp_path / "queue.json")
    product = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")

    def raise_not_configured(product, config):
        raise main_module.MoshimoLinkNotConfiguredError("not configured")

    monkeypatch.setattr(main_module, "build_link_for_product", raise_not_configured)

    result = main_module.enqueue_one_product(config=object(), product=product, queue=queue)

    assert result is False
    assert not queue.has_entry(product.key)
