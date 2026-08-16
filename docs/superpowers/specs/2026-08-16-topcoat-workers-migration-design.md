# Topcoat Cloudflare Workers Migration Design

## 目的

Yoyakuの承認済みUIとGit管理の記事JSONを維持したまま、Hono、Vite、TypeScriptで構成された配信層をTopcoatと`workers-rs`によるRust Workerへ置き換える。公開テンプレートとしてフォークしやすく、Cloudflare以外のHTTPホストへも移植できる境界を保つ。

## 採用構成

- HTTPアプリ: Topcoat 0.5の`Router`
- Cloudflareアダプター: `workers-rs` 0.8のFetchイベント
- ブラウザUI: TopcoatがサーバーレンダリングするHTML、CSS、依存のないJavaScript
- 記事処理: 既存の`yoyaku` Rust CLI
- データ正本: `content/articles/*.json`
- 配信用索引: `public/data/articles.json`
- デプロイ: `worker-build`、Wrangler、GitHub Actions

Topcoatは`default-features = false`とし、TCPリスナーを必要とする`serve`を含めない。Cloudflare固有コードは、`worker::HttpRequest`のBodyをTopcoatのBodyへ変換して`Router::handle`を呼ぶモジュールだけに閉じ込める。アプリ本体は標準HTTP型とTopcoatだけに依存する。

## データフロー

1. `yoyaku build`が記事JSONを検証し、`public/data/articles.json`を生成する。
2. Rust Workerのビルド時に索引を`include_str!`でWasmへ埋め込む。
3. リクエストごとに索引を型付きの`ArticleIndex`として読み、TopcoatのApp Contextへ渡す。
4. `/`は記事カード、検索候補、モーダルを含むHTMLをサーバーレンダリングする。
5. ブラウザはカードに埋め込まれた安全な`data-*`と`template`を使い、検索、並び替え、モーダルを処理する。
6. `/api/articles`は同じ索引をJSONで返し、`/api/health`は稼働確認を返す。

実行時DB、R2、LLM、Cloudflare固有のストレージは共通リポジトリへ追加しない。

## ファイル境界

- `app/src/lib.rs`: Topcoat Routerと埋め込み索引の組み立て。
- `app/src/page.rs`: 画面とカードのサーバーレンダリング。
- `app/src/routes.rs`: JSON APIとCSS/JavaScriptレスポンス。
- `app/src/cloudflare.rs`: `workers-rs`だけに依存するWasmエントリーポイント。
- `app/src/config.rs`: フォーク利用者が変更するサイト名とリポジトリURL。
- `app/web/style.css`: 承認済みデザイン。
- `app/web/filter.js`: 検索と並び替えの純粋関数。
- `app/web/main.js`: フォーム、カード、モーダルのDOM接続。
- `cli`: 記事検証、OGP取得、索引生成を引き続き担当。

## UIと動作

現在の48pxヘッダー、20pxのYoyaku見出し、固定サイドバー、デスクトップ3列、タブレット2列、モバイル1列を維持する。カード全体はボタンで、クリックすると中央のネイティブ`dialog`へ記事情報と全要約を表示する。Escape、閉じるボタン、背景クリックで閉じ、開くたびにスクロール位置を先頭へ戻す。

検索はキーワード、ジャンル、技術、掲載元、作成日、読了時間をANDで適用し、更新日、作成日、タイトルで並び替える。初期HTMLへカードを含めるため、JavaScriptが無効でも記事情報は閲覧できる。記事が0件の場合は空状態を表示する。

## 安全性とエラー処理

- 記事由来の値はTopcoatのエスケープを通してテキストまたは属性へ出力する。
- 要約はカード外の`template`へ段落としてレンダリングし、ブラウザではDOMを複製する。記事文字列を`innerHTML`へ渡さない。
- 外部リンクは`noopener noreferrer`を付ける。
- OGP画像は遅延読込し、失敗時は画像要素を取り除いて代替表示を見せる。
- 埋め込み索引が不正ならWorkerエントリーポイントは明示的なエラーを返す。
- APIとアセットには用途に応じたContent-TypeとCache-Controlを設定する。

## ビルドとデプロイ

Rust 1.95以上と`wasm32-unknown-unknown`を使用する。Topcoat 0.5と`worker-build` 0.8を固定し、現行`worker-build`のパニック回復ラッパーとの互換性問題を避けるため`--no-panic-recovery`でバンドルする。Wranglerは生成された`app/build/worker/shim.mjs`を配信する。

Node.jsはWranglerの実行と依存のないJavaScriptテストにのみ使用する。Hono、Vite、TypeScript、Cloudflare Vite Pluginは削除する。

## テストと完了条件

- Rustテストで検索モデル、Topcoat HTML、エスケープ、API、アセットレスポンスを検証する。
- Node組み込みテストでキーワード、AND条件、並び替えを検証する。
- 既存CLIの全テストとClippyを維持する。
- `cargo test --workspace`、`cargo clippy --workspace --all-targets -- -D warnings`、JavaScriptテスト、Wasmビルドを成功させる。
- Wranglerローカル環境で`/`、`/api/health`、`/api/articles`、アセットを確認する。
- `wrangler deploy --dry-run`を成功させ、実デプロイは行わない。
