"""WordPress REST API への記事投稿。

認証は「アプリケーションパスワード」方式のBasic認証を前提とする
(WordPress 5.6+ で標準搭載。ユーザープロフィール画面で発行する)。
通常のログインパスワードは使わないこと。
"""
from __future__ import annotations

import logging
import mimetypes
import os
from urllib.parse import urlparse

import requests

from moshimo_articles.config import WordPressConfig
from moshimo_articles.models import GeneratedArticle, Product

logger = logging.getLogger(__name__)


class WordPressClient:
    def __init__(self, config: WordPressConfig):
        self._config = config
        self._auth = (config.username, config.app_password)
        self._api_root = f"{config.base_url}/wp-json/wp/v2"

    def upload_featured_image(self, product: Product) -> int | None:
        """商品画像をダウンロードしてメディアライブラリにアップロードし、media IDを返す。"""
        if not product.image_url:
            return None

        try:
            image_response = requests.get(product.image_url, timeout=20)
            image_response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("商品画像のダウンロードに失敗しました(%s): %s", product.image_url, exc)
            return None

        filename = os.path.basename(urlparse(product.image_url).path) or f"{product.key.replace(':', '_')}.jpg"
        content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"

        response = requests.post(
            f"{self._api_root}/media",
            auth=self._auth,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": content_type,
            },
            data=image_response.content,
            timeout=30,
        )
        response.raise_for_status()
        media_id = response.json()["id"]
        logger.info("アイキャッチ画像をアップロードしました (media_id=%s)", media_id)
        return media_id

    def resolve_tag_ids(self, tag_names: list[str]) -> list[int]:
        """タグ名リストから、既存タグは再利用し、無ければ新規作成してIDリストを返す。"""
        tag_ids: list[int] = []
        for name in tag_names:
            if not name:
                continue
            existing = requests.get(
                f"{self._api_root}/tags",
                auth=self._auth,
                params={"search": name},
                timeout=15,
            )
            existing.raise_for_status()
            matches = [t for t in existing.json() if t["name"] == name]
            if matches:
                tag_ids.append(matches[0]["id"])
                continue

            created = requests.post(
                f"{self._api_root}/tags",
                auth=self._auth,
                json={"name": name},
                timeout=15,
            )
            if created.status_code == 400 and created.json().get("code") == "term_exists":
                tag_ids.append(created.json()["data"]["term_id"])
            else:
                created.raise_for_status()
                tag_ids.append(created.json()["id"])
        return tag_ids

    def create_post(self, article: GeneratedArticle, product: Product) -> dict:
        """記事を投稿する。既定では下書き(draft)として作成される。"""
        featured_media = self.upload_featured_image(product)
        tag_ids = self.resolve_tag_ids(article.tags)

        payload = {
            "title": article.title,
            "content": article.body_html,
            "excerpt": article.excerpt,
            "status": self._config.post_status,
            "tags": tag_ids,
        }
        if featured_media:
            payload["featured_media"] = featured_media

        response = requests.post(
            f"{self._api_root}/posts",
            auth=self._auth,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(
            "WordPressに投稿しました: id=%s status=%s link=%s",
            result.get("id"),
            result.get("status"),
            result.get("link"),
        )
        return result
