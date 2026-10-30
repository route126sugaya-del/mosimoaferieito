# もしもアフィリエイト商品キュー収集システム

楽天市場・Amazonの商品情報を取得し、もしもアフィリエイト経由のリンクを
生成して、商品候補を `data/product_queue.json` に積むシステムです。
GitHub Actionsで定期実行します。

**記事の執筆・WordPress投稿はこのリポジトリでは行いません。**
kamidera.comの既存ブログ運用(別リポジトリ `note-blog-auto`)側のClaude実行が、
このキューを読み、既存ブログの文体・カテゴリ運用ルール
(`wp-blog-auto/CLAUDE.md` および `wp-blog-auto/config/週刊企画_家電子育てグッズ.md`)
に沿って商品紹介記事を書き、WordPressに投稿します(2026-10-12方針変更。以前は
このリポジトリのClaude APIで記事本文も生成していましたが、既存ブログの文体・
カテゴリと噛み合わない記事が直接投稿されてしまったため、記事化は note-blog-auto
側の既存ワークフローに統合しました)。

## 処理の流れ

```
[config/keywords.yaml からキーワードを選択]
        ↓
[楽天市場API / Amazon Creators API で商品検索]
        ↓
[data/product_queue.json と照合し、未登録の商品を選択]
        ↓
[もしもアフィリエイトの a_id/p_id/pc_id/pl_id でアフィリエイトリンクを生成]
        ↓
[data/product_queue.json に status: "pending" として追加]
        ↓
[(別リポジトリ) note-blog-auto側のClaudeが、このキューを参照して記事を書き、
 WordPressに投稿する。使用した候補は status: "used" に更新してこのリポジトリに
 コミット・プッシュする]
```

## 重要な前提知識

- **もしもアフィリエイトは商品検索・リンク発行の公開APIを提供していません。**
  「かんたんリンク」は管理画面上のGUI機能であり、外部から自動呼び出しはできません。
  そのため本システムは、①楽天市場API・Amazon Creators APIで商品データを取得し、
  ②もしもアフィリエイトの管理画面で提携ごとに発行される `a_id`/`p_id`/`pc_id`/`pl_id` を使って
  通常の商品URLを `https://af.moshimo.com/af/c/click?...&url=<商品URL>` 形式の
  アフィリエイトリンクに変換する、という構成を取っています。
- **楽天市場APIは2026年2月の認証システム刷新により、`applicationId` に加えて
  `accessKey` の指定が必須になりました。** 古いアプリのままだと400エラーになるため、
  新規にアプリ登録をやり直す必要があります。またリクエスト元検証のため `Referer` ヘッダーも
  必須になっており、事前にアプリ管理画面の「許可されたWebサイト」へ登録したURLを
  `RAKUTEN_REFERER` として送る必要があります(未設定だとHTTP 403エラー)。
- **Amazon Product Advertising API (PA-API) は2026年5月に完全終了し、
  後継の Amazon Creators API への移行が必須になりました。** 認証方式もAWS Signature V4から
  OAuth 2.0(`Credential ID` / `Credential Secret`)に変わっており、Amazonアソシエイト管理画面の
  「CreatorsAPI」タブから新規に発行する必要があります。

## セットアップ

### 1. 必要なアカウント・キーの準備

| サービス | 用途 | 取得先 |
|---|---|---|
| 楽天ウェブサービス | 商品検索(無料・審査不要) | https://webservice.rakuten.co.jp/ で新規アプリ登録し `applicationId` と `accessKey`(`pk_`から始まる値)の両方を取得。2026年2月の認証刷新以前に発行した古いIDは使えないため、既存のものがあっても登録し直すこと。さらにアプリ管理画面の「許可されたWebサイト」に任意のURL(例: 投稿先WordPressのURL)を登録し、同じURLを `RAKUTEN_REFERER` に設定すること(未設定だとHTTP 403エラーになる) |
| Amazon Creators API(任意) | 商品検索 | Amazonアソシエイト管理画面(Associates Central)の「CreatorsAPI」タブから `Credential ID` / `Credential Secret` を発行(旧PA-APIのキーは使用不可) |
| もしもアフィリエイト | アフィリエイトリンク発行 | 各広告主と提携後、プロモーション詳細の「広告リンクタグ」から `a_id`/`p_id`/`pc_id`/`pl_id` を取得 |

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

**Secrets**
- `RAKUTEN_APP_ID` / `RAKUTEN_ACCESS_KEY` / `RAKUTEN_REFERER`(楽天を使う場合。3つとも必須)
- `AMAZON_CREDENTIAL_ID` / `AMAZON_CREDENTIAL_SECRET` / `AMAZON_PARTNER_TAG`(Amazonを使う場合)
- `MOSHIMO_RAKUTEN_A_ID` / `MOSHIMO_RAKUTEN_P_ID` / `MOSHIMO_RAKUTEN_PC_ID` / `MOSHIMO_RAKUTEN_PL_ID`(楽天を使う場合)
- `MOSHIMO_AMAZON_A_ID` / `MOSHIMO_AMAZON_P_ID` / `MOSHIMO_AMAZON_PC_ID` / `MOSHIMO_AMAZON_PL_ID`(Amazonを使う場合)

**Variables(任意、未設定時は既定値を使用)**
- `AMAZON_COUNTRY`(既定: `JP`)
- `PRODUCTS_PER_RUN`(既定: `5`。note-blog-auto側が毎日の記事でも商品紹介の機会を
  積極的に探すようになったため、2026-10-13にデフォルトを1→5に変更した)

設定後、`.github/workflows/generate-articles.yml` が毎日 UTC 23:00(JST 翌8:00)に自動実行されます。
Actionsタブから `workflow_dispatch` で手動実行して動作確認することもできます。

## キーワードのカスタマイズ

`config/keywords.yaml` に紹介したい商品ジャンルの検索キーワードを追記・編集してください。
実行のたびにこの中から1つが選ばれ、商品検索に使われます。kamidera.comの既存の
週刊企画(家電・子育てグッズ紹介)に合う、家電・子育てグッズ系のキーワードにして
おくと、note-blog-auto側で記事化しやすくなります。

## 重複登録の防止

`data/product_queue.json` に商品のキー(`{ソース}:{商品ID}`)を記録し、同じ商品を
二重にキューへ追加しないようにしています。GitHub Actions実行後、このファイルの
更新は自動的にコミット・プッシュされます。note-blog-auto側が商品を使用したら、
該当エントリの `status` を `"pending"` から `"used"` に更新し、このリポジトリに
コミット・プッシュします。

## ディレクトリ構成

```
src/moshimo_articles/
  config.py              環境変数の読み込み
  models.py              Product データモデル
  keywords.py            config/keywords.yaml の読み込み
  queue.py               商品キューの管理(重複登録防止)
  main.py                全体のオーケストレーション
  product_sources/
    rakuten.py           楽天市場 商品検索API
    amazon.py            Amazon Creators API
  affiliate/
    moshimo.py           もしもアフィリエイトのリンク変換
config/keywords.yaml      検索キーワード一覧
data/product_queue.json  商品キュー(note-blog-auto側が読んで記事化する)
.github/workflows/generate-articles.yml  定期実行ワークフロー
```

## 既知の制限事項

- もしもアフィリエイトの `a_id` 等は広告主(楽天/Amazonなど)ごとに個別に発行されるため、
  紹介するASPを増やす場合はコードとSecretsの両方に追加が必要です。
- 1回の実行で複数商品をキューに積む場合、`PRODUCTS_PER_RUN` を増やしてください。

## 正規HTML広告の手動掲載（追加機能）

既存の候補収集・別リポジトリの記事化とは独立しています。定期実行には接続していません。
`data/product_queue.json` の生成リンクを広告マスターへ自動転用しません。

1. もしも管理画面で正規発行されたHTML全文を `ads/sandisk_256gb.html` に保存します。
   このファイルはGit管理から除外されます。サンプル広告や推測したURLは使用しません。
2. `data/ad_master.json` の商品名・keywords・html_fileを編集します。
   HTMLを人が確認し、ファイルのSHA256を `sha256` に記録し、`reviewed` と `enabled` をtrueにします。
   Windowsでは `Get-FileHash ads/sandisk_256gb.html -Algorithm SHA256` で確認できます（小文字で記録）。
   SHA256はファイルの改変確認用です。もしも発行元の真正性やHTMLの安全性を自動保証するものではありません。
3. まずオフラインで確認します（初期台帳は全広告無効なので変更なしが正常です）。

```sh
python -m moshimo_articles.ad_manager --input tests/fixtures/ad_post.json --dry-run
```

`local_ad_runs/<実行ID>/` にbefore.json、preview.html、report.jsonが作られます。
HTMLは原文を保持して広告・PR表記付きで末尾に1件追加します。既存の広告マーカーがあれば追加しません。
キーワード不一致・全広告無効なら変更しません。プレビューはネット接続時に外部スクリプトを実行する可能性があるため、確認済み正規HTMLのみ登録してください。

実サイトの読取確認は、環境変数 `WP_URL`（例: https://kamidera.com）、`WP_USERNAME`、
`WP_APPLICATION_PASSWORD` を安全なローカル環境に設定し、以下を実行します。
パスワードをGitやチャットに保存しないでください。このツールは.envを自動読込しません。

```sh
python -m moshimo_articles.ad_manager --post-id 123 --dry-run
```

確認したreport.jsonのcontent_sha256を使い、承認後に下書きだけを更新できます。

```sh
python -m moshimo_articles.ad_manager --post-id 123 --apply --approve-sha256 <確認したハッシュ>
```

標準はdry-runで、--apply以外の実行はWordPressへ書き込みません。
公開済み・予約・非公開・承認待ち記事の更新は禁止しています。公開操作は実装していません。
更新前バックアップを必ず保存し、直前の本文・更新時刻を再確認します。
WordPress REST APIにはこの処理で利用できる原子的な比較更新がないため、最終確認と更新の間の競合は完全には防げません。
他の編集や自動運用を止めて下書きで検証してください。HTMLがWordPressに除去・変更された場合は失敗扱いにし、再実行せずバックアップと記事を確認します。
復元はbefore.jsonのcontent.rawを下書きへ手動で戻します。バックアップには非公開本文を含むためGit管理対象外です。

API仕様: https://developer.wordpress.org/rest-api/reference/posts/
