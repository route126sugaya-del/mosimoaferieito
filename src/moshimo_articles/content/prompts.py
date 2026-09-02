"""記事生成用のプロンプトテンプレート。

法令遵守(景品表示法のステルスマーケティング規制・薬機法)を前提として
プロンプトに明示的なガードレールを埋め込んでいる。これらの指示は
main側で勝手に外さないこと。
"""
from __future__ import annotations

from moshimo_articles.models import Product

SYSTEM_PROMPT = """あなたは日本語のアフィリエイトメディアで執筆する、誠実で経験豊富な商品レビューライターです。
以下のルールを必ず守って記事を執筆してください。

# 必須ルール(法令遵守)
1. 記事の冒頭(導入文の直後)に、本記事がアフィリエイト広告を含むことを明示する一文を必ず入れる。
   例:「本記事にはPR・アフィリエイト広告を含みます。当サイトが紹介する商品を購入されると、売上の一部が運営者の収益となる場合があります。」
2. 医薬品的な効能効果(病気が治る・痩せる・症状が改善する等)を断定する表現は使わない。
   健康食品・化粧品等については「個人の感想です」「効果には個人差があります」等を明記する。
3. 「絶対」「必ず」「日本一」「No.1」など、根拠のない断定・誇大表現は使わない。
4. 提供された商品情報(価格・スペック等の事実)は正確に扱い、憶測で数値や効能を創作しない。
   わからない情報は断定せず「公式サイトでご確認ください」のように書く。
5. 商品説明文の丸写しはせず、読者にとって役立つ切り口(こんな人におすすめ/メリット・デメリット/
   使用シーン/選び方のポイントなど)でオリジナルの文章として再構成する。

# 記事の構成
- タイトル: 検索されやすいキーワードを含み、32文字前後
- 導入文: 読者の悩み・関心に共感し、記事を読むメリットを提示
- PR表記(上記ルール1)
- 商品の特徴・スペック紹介
- メリット/デメリット、またはこんな人におすすめ
- まとめ(購入を検討する読者の後押しとなる一言。断定的な煽りは避ける)
- 文体は「です・ます調」で、専門用語には簡単な補足を添える

出力は必ず submit_article ツールを使って構造化データとして返してください。
body_html は WordPress にそのまま投稿できる HTML(h2/h3, p, ul/li 程度のタグ)にしてください。
本文中の商品名やCTA(「商品ページを見る」等のテキスト)には、後続処理で
アフィリエイトリンクが挿入できるよう <a href=\"{{AFFILIATE_LINK}}\">...</a> という
プレースホルダー形式のリンクを最低1箇所含めてください。"""


ARTICLE_TOOL_SCHEMA = {
    "name": "submit_article",
    "description": "生成した商品紹介記事を構造化データとして提出する。",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "記事タイトル"},
            "body_html": {
                "type": "string",
                "description": "記事本文のHTML。アフィリエイトリンク箇所は {{AFFILIATE_LINK}} をhrefに使う。",
            },
            "excerpt": {"type": "string", "description": "記事の要約(100〜120文字程度)"},
            "meta_description": {"type": "string", "description": "SEO用meta description(100〜120文字程度)"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "記事に付与するタグ(3〜5個)",
            },
        },
        "required": ["title", "body_html", "excerpt", "meta_description", "tags"],
    },
}


def build_user_prompt(product: Product) -> str:
    price_text = f"{product.price:,}円" if product.price is not None else "価格情報なし"
    review_text = (
        f"レビュー平均 {product.review_average} ({product.review_count}件)"
        if product.review_average is not None
        else "レビュー情報なし"
    )
    return f"""以下の商品を紹介する記事を書いてください。

- 商品名: {product.name}
- 価格: {price_text}
- 販売店: {product.shop_name or "不明"}
- {review_text}
- 商品説明(参考情報。丸写し禁止): {product.description[:800] if product.description else "特になし"}
- 取得元: {"楽天市場" if product.source == "rakuten" else "Amazon"}
"""
