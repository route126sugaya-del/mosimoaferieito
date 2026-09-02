"""WordPress REST API投稿のテスト。"""
from __future__ import annotations

from moshimo_articles.config import WordPressConfig
from moshimo_articles.models import GeneratedArticle, Product
from moshimo_articles.publish import wordpress


class DummyResponse:
    def __init__(self, json_data=None, status_code=200, content=b""):
        self._json = json_data
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def _config() -> WordPressConfig:
    return WordPressConfig(
        base_url="https://example.com", username="admin", app_password="app-pass", post_status="draft"
    )


def _product() -> Product:
    return Product(
        source="rakuten",
        product_id="1",
        name="商品A",
        item_url="https://item.rakuten.co.jp/x/",
        image_url="https://example.com/product.jpg",
    )


def test_upload_featured_image_returns_media_id(monkeypatch):
    client = wordpress.WordPressClient(_config())

    monkeypatch.setattr(wordpress.requests, "get", lambda url, timeout: DummyResponse(content=b"fake-bytes"))
    monkeypatch.setattr(
        wordpress.requests, "post", lambda url, auth, headers, data, timeout: DummyResponse({"id": 42})
    )

    media_id = client.upload_featured_image(_product())

    assert media_id == 42


def test_upload_featured_image_returns_none_without_image_url():
    client = wordpress.WordPressClient(_config())
    product = _product()
    product.image_url = None

    assert client.upload_featured_image(product) is None


def test_resolve_tag_ids_creates_missing_tags(monkeypatch):
    client = wordpress.WordPressClient(_config())

    monkeypatch.setattr(wordpress.requests, "get", lambda url, auth, params, timeout: DummyResponse([]))
    monkeypatch.setattr(
        wordpress.requests,
        "post",
        lambda url, auth, json, timeout: DummyResponse({"id": 99, "name": json["name"]}),
    )

    tag_ids = client.resolve_tag_ids(["新しいタグ"])

    assert tag_ids == [99]


def test_resolve_tag_ids_reuses_existing_tag(monkeypatch):
    client = wordpress.WordPressClient(_config())

    monkeypatch.setattr(
        wordpress.requests,
        "get",
        lambda url, auth, params, timeout: DummyResponse([{"id": 5, "name": params["search"]}]),
    )

    tag_ids = client.resolve_tag_ids(["既存タグ"])

    assert tag_ids == [5]


def test_create_post_sends_expected_payload(monkeypatch):
    client = wordpress.WordPressClient(_config())

    monkeypatch.setattr(client, "upload_featured_image", lambda product: 42)
    monkeypatch.setattr(client, "resolve_tag_ids", lambda tags: [1, 2])

    captured = {}

    def fake_post(url, auth, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse({"id": 1, "status": "draft", "link": "https://example.com/?p=1"})

    monkeypatch.setattr(wordpress.requests, "post", fake_post)

    article = GeneratedArticle(
        title="タイトル", body_html="<p>本文</p>", excerpt="要約", meta_description="meta", tags=["タグ1"]
    )
    result = client.create_post(article, _product())

    assert result["link"] == "https://example.com/?p=1"
    assert captured["url"] == "https://example.com/wp-json/wp/v2/posts"
    assert captured["json"]["status"] == "draft"
    assert captured["json"]["featured_media"] == 42
    assert captured["json"]["tags"] == [1, 2]
