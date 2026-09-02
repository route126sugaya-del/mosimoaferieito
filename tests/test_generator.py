"""Claude APIによる記事生成のテスト。"""
from __future__ import annotations

from moshimo_articles.content import generator
from moshimo_articles.models import Product


class DummyToolUseBlock:
    type = "tool_use"
    name = "submit_article"

    def __init__(self, input_data):
        self.input = input_data


class DummyMessage:
    def __init__(self, content):
        self.content = content


class DummyMessages:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):
        return self._response


class DummyClient:
    def __init__(self, response):
        self.messages = DummyMessages(response)


def _product() -> Product:
    return Product(
        source="rakuten",
        product_id="1",
        name="折りたたみ傘",
        item_url="https://item.rakuten.co.jp/shop/1/",
    )


def test_generate_article_embeds_affiliate_link(monkeypatch):
    tool_input = {
        "title": "おすすめの折りたたみ傘",
        "body_html": '<p>紹介文</p><p><a href="{{AFFILIATE_LINK}}">商品ページ</a></p>',
        "excerpt": "要約",
        "meta_description": "meta",
        "tags": ["傘", "軽量"],
    }
    response = DummyMessage(content=[DummyToolUseBlock(tool_input)])
    monkeypatch.setattr(generator.anthropic, "Anthropic", lambda api_key: DummyClient(response))

    article = generator.generate_article(
        product=_product(),
        affiliate_link="https://af.moshimo.com/af/c/click?a_id=1&p_id=2&pc_id=3&pl_id=4&url=xxx",
        api_key="sk-test",
        model="claude-sonnet-5",
    )

    assert article.title == "おすすめの折りたたみ傘"
    assert "af.moshimo.com" in article.body_html
    assert "{{AFFILIATE_LINK}}" not in article.body_html
    assert 'rel="nofollow sponsored"' in article.body_html
    assert article.tags == ["傘", "軽量"]


def test_generate_article_appends_link_when_placeholder_missing(monkeypatch):
    tool_input = {
        "title": "タイトル",
        "body_html": "<p>本文のみ</p>",
        "excerpt": "要約",
        "meta_description": "meta",
        "tags": [],
    }
    response = DummyMessage(content=[DummyToolUseBlock(tool_input)])
    monkeypatch.setattr(generator.anthropic, "Anthropic", lambda api_key: DummyClient(response))

    affiliate_link = "https://af.moshimo.com/af/c/click?a_id=1"
    article = generator.generate_article(
        product=_product(),
        affiliate_link=affiliate_link,
        api_key="sk-test",
        model="claude-sonnet-5",
    )

    assert affiliate_link in article.body_html
    assert "商品ページを見る" in article.body_html
