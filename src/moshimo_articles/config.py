"""環境変数から設定を読み込むモジュール。

すべての秘匿情報(APIキー・a_id等)は環境変数(ローカルでは.env、GitHub Actionsでは
Secrets)から読み込み、コードやリポジトリには一切書き込まない。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is a soft dependency locally
    pass


class ConfigError(RuntimeError):
    """必須の環境変数が不足している場合に送出する。"""


def _get(name: str, default: str | None = None, required: bool = False) -> str | None:
    # GitHub Actionsでは未設定のsecrets/varsが空文字列として渡ってくるため、
    # 空文字列もdefault扱いにフォールバックする。
    value = os.environ.get(name) or default
    if required and not value:
        raise ConfigError(f"環境変数 {name} が設定されていません。.env.example を参照してください。")
    return value


@dataclass(frozen=True)
class MoshimoLinkConfig:
    """もしもアフィリエイトの広告リンクタグ発行値(提携ごとに固有)。"""

    a_id: str | None
    p_id: str | None
    pc_id: str | None
    pl_id: str | None

    @property
    def is_configured(self) -> bool:
        return bool(self.a_id and self.p_id and self.pc_id and self.pl_id)


@dataclass(frozen=True)
class RakutenConfig:
    app_id: str | None
    access_key: str | None
    affiliate_id: str | None
    moshimo_link: MoshimoLinkConfig

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.access_key)


@dataclass(frozen=True)
class AmazonConfig:
    """Amazon Creators API(旧PA-API。2026年5月にPA-APIは終了し移行必須)の認証情報。"""

    credential_id: str | None
    credential_secret: str | None
    partner_tag: str | None
    country: str
    moshimo_link: MoshimoLinkConfig

    @property
    def is_configured(self) -> bool:
        return bool(self.credential_id and self.credential_secret and self.partner_tag)


@dataclass(frozen=True)
class WordPressConfig:
    base_url: str
    username: str
    app_password: str
    post_status: str


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    claude_model: str
    rakuten: RakutenConfig
    amazon: AmazonConfig
    wordpress: WordPressConfig
    articles_per_run: int


def load_config() -> Config:
    """環境変数から Config を組み立てる。

    記事生成(Claude)とWordPress投稿は必須。楽天/Amazonの商品ソースは
    どちらか一方でも設定されていれば動作する(main側でチェックする)。
    """
    rakuten_moshimo = MoshimoLinkConfig(
        a_id=_get("MOSHIMO_RAKUTEN_A_ID"),
        p_id=_get("MOSHIMO_RAKUTEN_P_ID"),
        pc_id=_get("MOSHIMO_RAKUTEN_PC_ID"),
        pl_id=_get("MOSHIMO_RAKUTEN_PL_ID"),
    )
    amazon_moshimo = MoshimoLinkConfig(
        a_id=_get("MOSHIMO_AMAZON_A_ID"),
        p_id=_get("MOSHIMO_AMAZON_P_ID"),
        pc_id=_get("MOSHIMO_AMAZON_PC_ID"),
        pl_id=_get("MOSHIMO_AMAZON_PL_ID"),
    )

    return Config(
        anthropic_api_key=_get("ANTHROPIC_API_KEY", required=True),
        claude_model=_get("CLAUDE_MODEL", default="claude-sonnet-5"),
        rakuten=RakutenConfig(
            app_id=_get("RAKUTEN_APP_ID"),
            access_key=_get("RAKUTEN_ACCESS_KEY"),
            affiliate_id=_get("RAKUTEN_AFFILIATE_ID"),
            moshimo_link=rakuten_moshimo,
        ),
        amazon=AmazonConfig(
            credential_id=_get("AMAZON_CREDENTIAL_ID"),
            credential_secret=_get("AMAZON_CREDENTIAL_SECRET"),
            partner_tag=_get("AMAZON_PARTNER_TAG"),
            country=_get("AMAZON_COUNTRY", default="JP"),
            moshimo_link=amazon_moshimo,
        ),
        wordpress=WordPressConfig(
            base_url=(_get("WP_BASE_URL", required=True) or "").rstrip("/"),
            username=_get("WP_USERNAME", required=True),
            app_password=_get("WP_APP_PASSWORD", required=True),
            post_status=_get("WP_POST_STATUS", default="draft"),
        ),
        articles_per_run=int(_get("ARTICLES_PER_RUN", default="1")),
    )
