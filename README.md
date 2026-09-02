# もしもアフィリエイト記事自動生成システム

楽天市場・Amazonの商品情報を取得し、Claude APIで商品紹介記事を生成して、
もしもアフィリエイト経由のアフィリエイトリンクを埋め込んだ上でWordPressに
自動投稿するシステムです。GitHub Actionsで定期実行します。

## 処理の流れ

```
[config/keywords.yaml からキーワードを選択]
        ↓
[楽天市場API / Amazon PA-API で商品検索]
        ↓
[data/published_history.json と照合し、未紹介の商品を選択]
        ↓
[もしもアフィリエイトの a_id/p_id/pc_id/pl_id でアフィリエイトリンクを生成]
        ↓
[Claude API で記事本文(タイトル/本文HTML/抜粋/タグ)を生成]
        ↓
[WordPress REST API に下書き(既定)として投稿]
        ↓
[published_history.json を更新してコミット]
```

## 重要な前提知識

- **もしもアフィリエイトは商品検索・記事投稿の公開APIを提供していません。**
  「かんたんリンク」は管理画面上のGUI機能であり、外部から自動呼び出しはできません。
  そのため本システムは、①楽天市場API・Amazon PA-APIで商品データを取得し、
  ②もしもアフィリエイトの管理画面で提携ごとに発行される `a_id`/`p_id`/`pc_id`/`pl_id` を使って
  通常の商品URLを `https://af.moshimo.com/af/c/click?...&url=<商品URL>` 形式の
  アフィリエイトリンクに変換する、という構成を取っています。
- Amazon PA-APIは**直近180日で3件以上の紹介実績**が無いとアクセスキーが失効するため、
  新規サイトでは楽天市場API(無料・審査不要)を主データソースにすることを推奨します。
- Googleは機械的な商品情報の羅列だけの自動生成記事を低く評価します。本システムは
  Claude APIで商品説明文を丸写しせず再構成する設計にしていますが、**最終的な記事品質・
  一次情報としての価値は運用者の責任で担保してください。**

## 法令遵守に関する注意(必ずお読みください)

- **景品表示法のステルスマーケティング規制(2023年10月施行)**: アフィリエイト広告を含む記事には、
  広告であることを一般消費者が判別できるよう明示する義務があります。本システムのプロンプトには
  記事冒頭にPR表記を必ず入れる指示を組み込んでいますが、**生成結果を都度確認してください。**
- **薬機法**: 化粧品・健康食品等について効能効果を断定する表現は規制対象です。プロンプト側で
  断定表現を避けるよう指示していますが、最終的な内容確認は運用者の責任です。
- これらの理由から、`WP_POST_STATUS` の既定値は `draft`(下書き)にしています。
  内容を人がレビューしてから公開することを強く推奨します。

## セットアップ

### 1. 必要なアカウント・キーの準備

| サービス | 用途 | 取得先 |
|---|---|---|
| Anthropic API | 記事本文生成 | https://console.anthropic.com/ |
| 楽天ウェブサービス | 商品検索(無料・審査不要) | https://webservice.rakuten.co.jp/ |
| Amazon PA-API(任意) | 商品検索 | Amazonアソシエイト管理画面(紹介実績が必要) |
| もしもアフィリエイト | アフィリエイトリンク発行 | 各広告主と提携後、プロモーション詳細の「広告リンクタグ」から `a_id`/`p_id`/`pc_id`/`pl_id` を取得 |
| WordPress | 記事投稿先 | 対象サイトのユーザープロフィール画面で「アプリケーションパスワード」を発行(通常のログインパスワードは使わない) |

### 2. ローカルでの動作確認

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

cp .env.example .env
# .env を編集して各種キー・IDを入力

python -m moshimo_articles.main
```

### 3. テストの実行

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### 4. GitHub Actionsでの自動実行設定

リポジトリの **Settings > Secrets and variables > Actions** で以下を設定してください。

**Secrets(必須)**
- `ANTHROPIC_API_KEY`
- `WP_BASE_URL` / `WP_USERNAME` / `WP_APP_PASSWORD`
- `RAKUTEN_APP_ID`(楽天を使う場合)
- `AMAZON_ACCESS_KEY` / `AMAZON_SECRET_KEY` / `AMAZON_PARTNER_TAG`(Amazonを使う場合)
- `MOSHIMO_RAKUTEN_A_ID` / `MOSHIMO_RAKUTEN_P_ID` / `MOSHIMO_RAKUTEN_PC_ID` / `MOSHIMO_RAKUTEN_PL_ID`(楽天を使う場合)
- `MOSHIMO_AMAZON_A_ID` / `MOSHIMO_AMAZON_P_ID` / `MOSHIMO_AMAZON_PC_ID` / `MOSHIMO_AMAZON_PL_ID`(Amazonを使う場合)

**Variables(任意、未設定時は既定値を使用)**
- `CLAUDE_MODEL`(既定: `claude-sonnet-5`)
- `AMAZON_COUNTRY`(既定: `JP`)
- `WP_POST_STATUS`(既定: `draft`。即時公開する場合のみ `publish` に変更)
- `ARTICLES_PER_RUN`(既定: `1`)

設定後、`.github/workflows/generate-articles.yml` が毎日 UTC 23:00(JST 翌8:00)に自動実行されます。
Actionsタブから `workflow_dispatch` で手動実行して動作確認することもできます。

## キーワードのカスタマイズ

`config/keywords.yaml` に紹介したい商品ジャンルの検索キーワードを追記・編集してください。
実行のたびにこの中から1つが選ばれ、商品検索に使われます。

## 重複投稿の防止

`data/published_history.json` に紹介済み商品のキー(`{ソース}:{商品ID}`)を記録し、
同じ商品を二重に記事化しないようにしています。GitHub Actions実行後、このファイルの
更新は自動的にコミット・プッシュされます。

## ディレクトリ構成

```
src/moshimo_articles/
  config.py              環境変数の読み込み
  models.py              Product / GeneratedArticle データモデル
  keywords.py            config/keywords.yaml の読み込み
  history.py             重複投稿防止の履歴管理
  main.py                全体のオーケストレーション
  product_sources/
    rakuten.py           楽天市場 商品検索API
    amazon.py            Amazon PA-API
  affiliate/
    moshimo.py           もしもアフィリエイトのリンク変換
  content/
    prompts.py           Claude APIへのプロンプト(法令遵守のガードレールを含む)
    generator.py          記事生成
  publish/
    wordpress.py         WordPress REST API投稿
config/keywords.yaml      検索キーワード一覧
data/published_history.json  紹介済み商品の履歴
.github/workflows/generate-articles.yml  定期実行ワークフロー
```

## 既知の制限事項

- もしもアフィリエイトの `a_id` 等は広告主(楽天/Amazonなど)ごとに個別に発行されるため、
  紹介するASPを増やす場合はコードとSecretsの両方に追加が必要です。
- WordPress側のSEOプラグイン(Yoast SEO / Rank Mathなど)のmeta description欄は
  プラグインごとにAPIフィールドが異なるため、本システムでは自動反映していません
  (`GeneratedArticle.meta_description` に値は保持しているので、必要に応じて拡張してください)。
- 1回の実行で複数記事を生成する場合、`ARTICLES_PER_RUN` を増やしてください。
