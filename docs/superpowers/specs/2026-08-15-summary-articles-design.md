# Summary Articles Design

## 目的

技術記事のURL、要約、分類情報をGitで管理し、Cloudflare Workers上で検索・閲覧できる公開テンプレートを作る。利用者はリポジトリをフォークし、記事JSONとサイト設定だけを差し替えて自分用のアーカイブを運用できる。

## 採用構成

- 配信: Hono 4 + TypeScriptのCloudflare Worker
- フロントエンド: Viteでビルドするフレームワーク非依存のTypeScript/CSS
- 静的配信: Cloudflare Workers Static AssetsとCloudflare Vite Plugin
- 記事処理: Rust CLI
- データ正本: `content/articles/*.json`
- 配信用索引: Rust CLIが生成する`public/data/articles.json`
- 自動化: GitHub Actionsで検証・ビルド・Cloudflareへのデプロイ

HonoはTypeScript/JavaScriptのフレームワークであり、Rustフレームワークではない。そのためWorkerをHono、ローカル記事処理をRustに分離する。Cloudflare Workers自体は`workers-rs`経由でRustを実行できるが、このサイトでは実行時にRustを置く利点より、OGP取得やJSON検証をローカルCLIに置く利点が大きい。

## データモデル

各記事は1ファイルのJSONとして保存する。

```json
{
  "id": "cloudflare-workers-rust",
  "url": "https://example.com/articles/cloudflare-workers-rust",
  "title": "Cloudflare WorkersでRustを動かすための実践ガイド",
  "source": "Zenn",
  "genre": "Web開発",
  "technologies": ["Rust", "WebAssembly", "Cloudflare"],
  "reading_minutes": 8,
  "created_at": "2026-08-14",
  "updated_at": "2026-08-15",
  "summary": ["要約の段落1", "要約の段落2"],
  "ogp": {
    "image_url": "https://example.com/ogp.png",
    "title": "OGPタイトル",
    "description": "OGP説明"
  }
}
```

必須項目は`id`、`url`、`title`、`source`、`genre`、`technologies`、`reading_minutes`、`created_at`、`updated_at`、`summary`とする。`ogp`は任意で、画像がない場合はカード内にタイトルと技術名を使った代替表示を出す。日付は`YYYY-MM-DD`、URLはHTTPまたはHTTPS、読了時間は1以上、要約は1段落以上とする。

## Rust CLI

CLI名は`yoyaku`とする。

- `yoyaku validate`: 全記事を読み、スキーマ、重複ID、重複URL、日付順序を検証する。
- `yoyaku build`: 検証後、更新日の新しい順に並べた`articles.json`を生成する。ジャンル、技術、掲載元の候補一覧も同じJSONに含める。
- `yoyaku enrich <file>`: 記事URLを取得し、`og:title`、`og:description`、`og:image`を解析して対象JSONへ保存する。相対画像URLは記事URLを基準に絶対URLへ変換する。

OGP取得は10秒でタイムアウトし、4xx/5xx、HTMLでない応答、解析不能を明示的なエラーとして返す。既存の要約や分類情報は変更しない。LLM処理はCLIにもWorkerにも含めず、利用者がローカルで作成した要約をJSONへ入れる。

## WorkerとAPI

WorkerはHonoで次のAPIだけを提供する。

- `GET /api/health`: `{"ok":true}`を返す。
- `GET /api/articles`: 生成済み索引を返す。

画面資産はWorkers Static Assetsが直接配信する。`/api/*`だけWorkerを先に実行し、その他はSPAの`index.html`へフォールバックする。実行時のデータベースや秘密情報は不要である。

## 画面

承認済みモックアップを次の仕様で実装する。

- 上部は48pxの簡潔なヘッダーと20pxの`Yoyaku`見出し。
- デスクトップは左215pxの検索サイドバーと記事領域。サイドバーは画面内に固定し、内部だけスクロールできる。
- 記事はデスクトップ3列、タブレット2列、モバイル1列。
- カードはOGP、掲載元、ジャンル、読了時間、タイトル、短い要約、技術、作成日、更新日を表示する。
- カード全体をボタンとして扱い、押すとページ遷移せずモーダルを開く。
- モーダルは画面中央、角丸8px、最大幅680px、画面高から40pxを引いた高さまで。本文だけでなくモーダル全体を縦スクロールできる。
- モーダル上部にジャンル、読了時間、タイトル、技術、日付、元記事リンクを置き、その後に長い要約を表示する。OGP用の大きな領域は置かない。
- Escape、閉じるボタン、背景クリックで閉じる。開くたびスクロール位置を先頭へ戻す。

## 検索

検索条件はすべてANDで組み合わせる。

- キーワード: タイトル、要約、掲載元、ジャンル、技術を部分一致検索
- ジャンル
- 使用技術
- 掲載元
- 作成日の開始・終了
- 読了時間の上限
- 並び順: 更新日、作成日、タイトル
- 条件の一括解除

条件変更時に件数とカード一覧を即時更新する。検索条件はURLへは保存せず、ページ再読込で初期化する。

## アクセシビリティと安全性

- ネイティブ`dialog`と`button`を使い、キーボード操作を維持する。
- フォーカス表示を消さず、`focus-visible`で明示する。
- 記事由来の文字列は`innerHTML`へ入れず、`textContent`またはDOM生成で表示する。
- 外部リンクは`target="_blank"`と`rel="noopener noreferrer"`を付ける。
- OGP画像には遅延読込、代替テキスト、読込失敗時のフォールバックを付ける。
- 秘密情報、個人URL、個人用記事はサンプルへ含めない。

## テストと完了条件

- TypeScriptの検索・並び替え・APIレスポンスをVitestで検証する。
- Rustのスキーマ検証、重複検知、索引生成、OGP解析を`cargo test`で検証する。
- `npm run typecheck`、`npm test`、`npm run build`、`cargo test`、`cargo clippy`、`wrangler deploy --dry-run`が成功する。
- 実ブラウザで3列、固定サイドバー、複合検索、モーダル、長文スクロール、モバイル1列を確認する。

## 公開テンプレートの境界

共通リポジトリへ含めるのはアプリ本体、Rust CLI、サンプル記事、スキーマ、CI、デプロイ手順だけとする。フォーク利用者固有のCloudflareアカウントID、APIトークン、カスタムドメイン、非公開記事は含めない。GitHub ActionsのデプロイはSecretsが設定されたフォークだけで動作する。
