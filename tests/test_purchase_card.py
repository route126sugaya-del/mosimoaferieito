"""Synthetic HTML/URLs only: these fixtures are never placed on WordPress."""
from html.parser import HTMLParser
import hashlib
import json

import pytest

from moshimo_articles.ad_manager import insert, load_ads, run
from moshimo_articles.purchase_card import render_purchase_card, validate_amazon
from tests.test_ad_manager import master, options
from unittest.mock import Mock


def amazon(url="https://link.amazon/test-only"):
    return {"url": url, "source": "amazon-associates-issued", "reviewed": True}


@pytest.mark.parametrize("url", [
    "https://link.amazon/test-only", "https://amzn.to/test-only", "https://amzn.asia/test-only",
    "https://www.amazon.co.jp/dp/TEST?tag=test-22&linkCode=sl2",
])
def test_issued_url_preserved(url):
    assert validate_amazon(amazon(url)) == url


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "http://link.amazon/test", "https://amazon.co.jp.evil.test/dp/test",
    "https://evil.test/amazon.co.jp", "https://user:pass@link.amazon/test",
    "https://link.amazon:8080/test", "https://link.amazon/", "https://www.amazon.co.jp/dp/TEST",
    "https://link.amazon/test\n", "https://link.amazon/test#fragment",
])
def test_bad_url_rejected(url):
    with pytest.raises(ValueError):
        validate_amazon(amazon(url))


@pytest.mark.parametrize("settings", [None, {}, {**amazon(), "reviewed": False},
                                      {**amazon(), "source": "guessed"}])
def test_missing_review_rejected(settings):
    with pytest.raises(ValueError):
        validate_amazon(settings)


class LinksInFrames(HTMLParser):
    def __init__(self):
        super().__init__()
        self.frames = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            self.frames.append(attrs.get("id"))
        if tag == "a":
            self.links.append((attrs, self.frames.copy()))

    def handle_endtag(self, tag):
        if tag == "div":
            self.frames.pop()


def test_two_distinct_products_in_their_own_frames(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "ads").mkdir()
    ads = []
    raw_by_id = {}
    for ident, keyword in [("camera-a", "カメラA"), ("recorder-b", "録音機B")]:
        raw = f'<div><a href="https://example.invalid/{ident}">TEST ONLY {keyword}</a></div>'
        raw_by_id[ident] = raw
        (tmp_path / f"ads/{ident}.html").write_bytes(raw.encode())
        ads.append(dict(id=ident, name=keyword, keywords=[keyword], enabled=True,
                        html_file=f"ads/{ident}.html", source="moshimo-issued", reviewed=True,
                        sha256=hashlib.sha256(raw.encode()).hexdigest(),
                        amazon=amazon(f"https://link.amazon/test-only-{ident}")))
    master = tmp_path / "data/ad_master.json"
    master.write_text(json.dumps(dict(version=1, ads=ads)), encoding="utf-8")
    loaded = load_ads(master)
    for ident, keyword in [("camera-a", "カメラA"), ("recorder-b", "録音機B")]:
        result, chosen = insert(f"<p>{keyword}について</p>", loaded)
        assert chosen == ident
        assert raw_by_id[ident] in result
        assert insert(result, loaded) == (result, None)
        parser = LinksInFrames()
        parser.feed(result)
        assert len(parser.links) == 2
        assert all(f"moshimo-purchase-{ident}" in frames for _, frames in parser.links)
        assert parser.links[-1][0]["href"] == f"https://link.amazon/test-only-{ident}"
        assert result.count("Amazonで見る") == 1
        assert 'rel="sponsored nofollow noopener"' in result
    assert insert("<p>無関係な記事</p>", loaded)[1] is None


def test_html_attribute_escaping_and_rakuten_only_compatibility():
    ad = dict(id="test", html="<div>TEST ONLY</div>")
    assert render_purchase_card(ad) == ad["html"]
    ad["amazon"] = amazon('https://www.amazon.co.jp/dp/TEST?tag=test-22&note="x"')
    parser = LinksInFrames()
    rendered = render_purchase_card(ad)
    parser.feed(rendered)
    assert parser.links[-1][0]["href"] == ad["amazon"]["url"]
    assert '&amp;note=&quot;x&quot;' in rendered


def test_invalid_amazon_stops_before_wordpress_read(master, tmp_path):
    path, ad = master
    ad["amazon"] = amazon("https://evil.test/not-amazon")
    path.write_text(json.dumps(dict(version=1, ads=[ad])), encoding="utf-8")
    client = Mock()
    with pytest.raises(ValueError):
        run(options(path, tmp_path), client)
    client.get.assert_not_called()
    client.request.assert_not_called()
