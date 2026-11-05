import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from moshimo_articles.ad_manager import insert, load_ads, run


@pytest.fixture
def master(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "ads").mkdir()
    html = b'<a href="https://example.invalid/">TEST ONLY</a>'
    (tmp_path / "ads/test.html").write_bytes(html)
    ad = dict(id="test", name="test", keywords=["SDカード"], enabled=True,
              source="moshimo-issued", reviewed=True, html_file="ads/test.html",
              sha256=hashlib.sha256(html).hexdigest())
    path = tmp_path / "data/ad_master.json"
    path.write_text(json.dumps(dict(version=1, ads=[ad])), encoding="utf-8")
    return path, ad


def test_exact_html_and_idempotency(master):
    ads = load_ads(master[0])
    result, chosen = insert("<p>SDカード</p>", ads)
    assert chosen == "test"
    assert ads[0]["html"] in result
    assert insert(result, ads) == (result, None)
    assert insert("無関係な本文", ads) == ("無関係な本文", None)


@pytest.mark.parametrize("change", [dict(sha256="bad"), dict(reviewed=False),
                                    dict(html_file="../outside.html"), dict(enabled="true")])
def test_invalid_master(master, change):
    path, ad = master
    path.write_text(json.dumps(dict(version=1, ads=[dict(ad, **change)])), encoding="utf-8")
    with pytest.raises(ValueError):
        load_ads(path)


def options(master, tmp_path, **kw):
    return argparse.Namespace(master=master, input=None, post_id=123, output=tmp_path / "run",
                              dry_run=False, apply=False, approve_sha256=None, **kw)


def post(status="draft"):
    return dict(id=123, status=status, modified_gmt="today", content={"raw": "<p>SDカード</p>"})


def test_dry_run_never_writes_wordpress(master, tmp_path):
    client = Mock()
    client.get.return_value = post()
    report = run(options(master[0], tmp_path), client)
    assert report["changed"]
    client.request.assert_not_called()
    assert (tmp_path / "run/before.json").is_file()


@pytest.mark.parametrize("status", ["publish", "future", "private", "pending"])
def test_public_update_blocked(master, tmp_path, status):
    client = Mock()
    client.get.return_value = post(status)
    args = options(master[0], tmp_path)
    args.apply = True
    content, _ = insert(post()["content"]["raw"], load_ads(master[0]))
    args.approve_sha256 = hashlib.sha256(content.encode()).hexdigest()
    with pytest.raises(ValueError, match="Only draft"):
        run(args, client)
    client.request.assert_not_called()


def test_approved_draft_update(master, tmp_path):
    client = Mock()
    client.get.return_value = post()
    content, _ = insert(post()["content"]["raw"], load_ads(master[0]))
    client.request.return_value = dict(post(), content={"raw": content})
    args = options(master[0], tmp_path)
    args.apply = True
    args.approve_sha256 = hashlib.sha256(content.encode()).hexdigest()
    assert run(args, client)["mode"] == "apply"
    client.request.assert_called_once_with("POST", 123, json={"content": content, "status": "draft"})


def test_stale_content_blocked(master, tmp_path):
    client = Mock()
    client.get.side_effect = [post(), dict(post(), modified_gmt="later")]
    args = options(master[0], tmp_path)
    args.apply = True
    content, _ = insert(post()["content"]["raw"], load_ads(master[0]))
    args.approve_sha256 = hashlib.sha256(content.encode()).hexdigest()
    with pytest.raises(ValueError, match="changed during review"):
        run(args, client)
    client.request.assert_not_called()
