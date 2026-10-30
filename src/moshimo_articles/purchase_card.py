"""Shared product frame; keep issued Moshimo HTML and Amazon URL intact."""
from html import escape
import re
from urllib.parse import parse_qs, urlsplit


def validate_amazon(amazon: object) -> str:
    if not isinstance(amazon, dict):
        raise ValueError("amazon must be an object")
    if amazon.get("source") != "amazon-associates-issued" or amazon.get("reviewed") is not True:
        raise ValueError("Reviewed Amazon Associates issued link required")
    url = amazon.get("url")
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError("Invalid Amazon URL")
    parts = urlsplit(url)
    hosts = {"amazon.co.jp", "www.amazon.co.jp", "amzn.to", "amzn.asia", "link.amazon"}
    if (parts.scheme != "https" or parts.hostname not in hosts or parts.username is not None
            or parts.password is not None or parts.port not in (None, 443)
            or parts.fragment or not parts.path.strip("/")):
        raise ValueError("Amazon URL must be an issued HTTPS product link")
    if parts.hostname in {"amazon.co.jp", "www.amazon.co.jp"}:
        if not parse_qs(parts.query).get("tag", [""])[0]:
            raise ValueError("Direct Amazon URL must retain its Associates tag")
    # Human review checks the destination/product; validation does not prove attribution.
    return url


def render_purchase_card(ad: dict) -> str:
    original = ad["html"]
    if "amazon" not in ad:
        return original
    ident = ad["id"]
    if not re.fullmatch(r"[a-z0-9_-]{1,64}", ident):
        raise ValueError("Invalid ad id")
    url = escape(validate_amazon(ad["amazon"]), quote=True)
    frame = f"moshimo-purchase-{ident}"
    return f'''<style>
#{frame}{{box-sizing:border-box;width:100%;border:1px solid #ddd;border-radius:8px;padding:20px;background:#fff;}}
#{frame} .easyLink-box{{box-sizing:border-box;border:0!important;margin:0!important;padding:0!important;width:100%!important;max-width:100%!important;}}
#{frame} .purchase-amazon-button{{display:flex;align-items:center;justify-content:center;box-sizing:border-box;width:238px;max-width:100%;min-height:40px;margin:16px auto 0;padding:10px 16px;background:#ff9900;color:#111;border-radius:4px;font-size:14px;font-weight:700;line-height:1.5;text-decoration:none;text-align:center;}}
</style>
<div id="{frame}">
{original}
<a class="purchase-amazon-button" href="{url}" target="_blank" rel="sponsored nofollow noopener">Amazonで見る</a>
</div>
<p style="font-size:12px;line-height:1.6;">Amazonのアソシエイトとして、当メディアは適格販売により収入を得ています。</p>'''
