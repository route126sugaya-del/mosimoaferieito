"""main.pyのオーケストレーションロジックのテスト。"""
from __future__ import annotations

from types import SimpleNamespace

from moshimo_articles import main as main_module
from moshimo_articles.history import PublishedHistory
from moshimo_articles.models import GeneratedArticle, Product

_DUMMY_CONFIG = SimpleNamespace(anthropic_api_key="sk-test", claude_model="claude-sonnet-5")


def test_pick_unpublished_product_skips_published(tmp_path):
    history = PublishedHistory(path=tmp_path / "history.json")
    published = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")
    history.record(published.key, "A")

    fresh = Product(source="rakuten", product_id="2", name="B", item_url="https://example.com/2")

    picked = main_module.pick_unpublished_product([published, fresh], history)

    assert picked is fresh


def test_pick_unpublished_product_returns_none_when_all_published(tmp_path):
    history = PublishedHistory(path=tmp_path / "history.json")
    published = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")
    history.record(published.key, "A")

    picked = main_module.pick_unpublished_product([published], history)

    assert picked is None


def test_pick_unpublished_product_skips_products_without_url(tmp_path):
    history = PublishedHistory(path=tmp_path / "history.json")
    no_url = Product(source="rakuten", product_id="1", name="A", item_url="")

    picked = main_module.pick_unpublished_product([no_url], history)

    assert picked is None


def test_process_one_article_records_history_on_success(tmp_path, monkeypatch):
    history = PublishedHistory(path=tmp_path / "history.json")
    product = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")

    monkeypatch.setattr(main_module, "build_link_for_product", lambda product, config: "https://af.moshimo.com/x")
    monkeypatch.setattr(
        main_module,
        "generate_article",
        lambda **kwargs: GeneratedArticle(
            title="タイトル", body_html="<p>本文</p>", excerpt="要約", meta_description="meta", tags=[]
        ),
    )

    class DummyWpClient:
        def create_post(self, article, product):
            return {"link": "https://example.com/post/1"}

    result = main_module.process_one_article(
        config=_DUMMY_CONFIG, product=product, history=history, wp_client=DummyWpClient()
    )

    assert result is True
    assert history.has_published(product.key)


def test_process_one_article_returns_false_when_link_not_configured(tmp_path, monkeypatch):
    history = PublishedHistory(path=tmp_path / "history.json")
    product = Product(source="rakuten", product_id="1", name="A", item_url="https://example.com/1")

    def raise_not_configured(product, config):
        raise main_module.MoshimoLinkNotConfiguredError("not configured")

    monkeypatch.setattr(main_module, "build_link_for_product", raise_not_configured)

    result = main_module.process_one_article(config=object(), product=product, history=history, wp_client=None)

    assert result is False
    assert not history.has_published(product.key)
