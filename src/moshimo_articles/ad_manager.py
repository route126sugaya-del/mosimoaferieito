"""Explicit, offline-first placement of reviewed Moshimo HTML. Never scheduled."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from uuid import uuid4

from moshimo_articles.purchase_card import render_purchase_card, validate_amazon


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_ads(master: Path) -> list[dict]:
    root = master.resolve().parent.parent
    document = json.loads(master.read_text(encoding="utf-8"))
    if document.get("version") != 1 or not isinstance(document.get("ads"), list):
        raise ValueError("Invalid ad master")
    seen = set()
    result = []
    for ad in document["ads"]:
        ident = ad.get("id", "")
        if not re.fullmatch(r"[a-z0-9_-]{1,64}", ident) or ident in seen:
            raise ValueError("Invalid or duplicate ad id")
        seen.add(ident)
        if type(ad.get("enabled")) is not bool:
            raise ValueError("enabled must be boolean")
        keywords = ad.get("keywords")
        if not isinstance(keywords, list) or not keywords or any(not isinstance(k, str) or not k.strip() for k in keywords):
            raise ValueError("Nonempty keywords required")
        if not ad["enabled"]:
            continue
        if "amazon" in ad:
            validate_amazon(ad["amazon"])
        path = (root / ad["html_file"]).resolve()
        if not path.is_relative_to((root / "ads").resolve()) or path.suffix != ".html":
            raise ValueError("HTML must be inside ads/")
        data = path.read_bytes()
        if ad.get("source") != "moshimo-issued" or ad.get("reviewed") is not True or digest(data) != ad.get("sha256"):
            raise ValueError("Reviewed issued HTML and matching SHA256 required")
        html = data.decode("utf-8")
        if not html.strip():
            raise ValueError("Empty HTML")
        # Hash and human review attest provenance; this is not an HTML sanitizer.
        result.append({**ad, "html": html})
    return result


def insert(content: str, ads: list[dict]) -> tuple[str, str | None]:
    if "<!-- moshimo-ad:" in content:
        return content, None
    text = re.sub(r"<[^>]*>", " ", content).casefold()
    ranked = sorted(ads, key=lambda a: -sum(k.casefold() in text for k in a["keywords"]))
    if not ranked or not any(k.casefold() in text for k in ranked[0]["keywords"]):
        return content, None
    ad = ranked[0]
    return (content + '\n<!-- moshimo-ad:' + ad["id"] + ':start -->\n'
            '<!-- wp:html -->\n<p>広告・PR</p>\n' + render_purchase_card(ad) +
            '\n<!-- /wp:html -->\n<!-- moshimo-ad:' + ad["id"] + ':end -->\n', ad["id"])


class WordPress:
    def __init__(self):
        import requests
        base = os.environ["WP_URL"].rstrip("/")
        parts = urlsplit(base)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("WP_URL must be an HTTPS site URL")
        self.base = base
        self.session = requests.Session()
        self.session.auth = (os.environ["WP_USERNAME"], os.environ["WP_APPLICATION_PASSWORD"])

    def request(self, method, post_id, **kwargs):
        response = self.session.request(method, f"{self.base}/wp-json/wp/v2/posts/{post_id}",
                                        timeout=30, allow_redirects=False, **kwargs)
        if response.status_code != 200:
            raise ValueError(f"WordPress request failed: HTTP {response.status_code}")
        return response.json()

    def get(self, post_id):
        return self.request("GET", post_id, params={"context": "edit"})


def run(args, client=None):
    if args.apply and args.dry_run:
        raise ValueError("Choose dry-run or apply")
    if args.post_id is not None and args.post_id <= 0:
        raise ValueError("Positive post id required")
    if args.input and args.apply:
        raise ValueError("Offline input cannot be applied")
    ads = load_ads(args.master)
    wp = None
    if args.input:
        post = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        wp = client or WordPress()
        post = wp.get(args.post_id)
    original = post["content"]["raw"]
    content, chosen = insert(original, ads)
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    (out / "before.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "preview.html").write_text(content, encoding="utf-8")
    plan_hash = digest(content.encode("utf-8"))
    report = {"mode": "apply" if args.apply else "dry-run", "post_id": post.get("id"),
              "ad_id": chosen, "changed": content != original, "content_sha256": plan_hash}
    if args.apply and chosen:
        if args.approve_sha256 != plan_hash:
            raise ValueError("Approval hash must match reviewed dry-run preview")
        if post["status"] != "draft":
            raise ValueError("Only draft posts may be updated; public posts require a separate reviewed release")
        current = wp.get(args.post_id)
        if current["content"]["raw"] != original or current["modified_gmt"] != post["modified_gmt"] or current["status"] != "draft":
            raise ValueError("Post changed during review")
        saved = wp.request("POST", args.post_id, json={"content": content, "status": "draft"})
        if saved["content"].get("raw") != content or saved["status"] != "draft":
            raise ValueError("WordPress changed the saved HTML; inspect backup and post manually")
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("data/ad_master.json"))
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--input", type=Path, help="Offline post JSON with content.raw")
    target.add_argument("--post-id", type=int)
    parser.add_argument("--output", type=Path, default=Path("local_ad_runs") / uuid4().hex)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--approve-sha256")
    try:
        print(json.dumps(run(parser.parse_args()), ensure_ascii=False))
    except (ValueError, KeyError, OSError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
