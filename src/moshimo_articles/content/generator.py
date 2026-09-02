"""Claude APIを使った記事本文生成。"""
from __future__ import annotations

import logging

import anthropic

from moshimo_articles.content.prompts import ARTICLE_TOOL_SCHEMA, SYSTEM_PROMPT, build_user_prompt
from moshimo_articles.models import GeneratedArticle, Product

logger = logging.getLogger(__name__)

_AFFILIATE_LINK_PLACEHOLDER = "{{AFFILIATE_LINK}}"


def generate_article(
    product: Product,
    affiliate_link: str,
    api_key: str,
    model: str,
    max_tokens: int = 4096,
) -> GeneratedArticle:
    """商品情報からClaude APIで記事を生成し、アフィリエイトリンクを埋め込んで返す。"""
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[ARTICLE_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_article"},
        messages=[{"role": "user", "content": build_user_prompt(product)}],
    )

    tool_input = _extract_tool_input(response)

    body_html = tool_input["body_html"].replace(_AFFILIATE_LINK_PLACEHOLDER, affiliate_link)
    if affiliate_link not in body_html:
        # モデルがプレースホルダーを入れ忘れた場合のフォールバック: 記事末尾にCTAを追記する。
        body_html += (
            f'\n<p><a href="{affiliate_link}" rel="nofollow sponsored" '
            f'target="_blank">{product.name} の商品ページを見る</a></p>'
        )
    else:
        body_html = body_html.replace(f'href="{affiliate_link}"', f'rel="nofollow sponsored" href="{affiliate_link}"')

    article = GeneratedArticle(
        title=tool_input["title"],
        body_html=body_html,
        excerpt=tool_input["excerpt"],
        meta_description=tool_input["meta_description"],
        tags=list(tool_input.get("tags", [])),
    )
    logger.info("記事生成完了: %s", article.title)
    return article


def _extract_tool_input(response: anthropic.types.Message) -> dict:
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_article":
            return block.input
    raise RuntimeError("Claude APIのレスポンスに submit_article ツール呼び出しが含まれていません。")
