# Yoyaku

URL、要約、ジャンル、技術、日付、読了時間をGitで管理し、検索できる記事アーカイブです。リポジトリをフォークして、`content/articles`だけを自分の記事へ置き換えて使えます。

![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-F38020?logo=cloudflare&logoColor=white)
![Topcoat](https://img.shields.io/badge/Topcoat-0.5-242424)
![Rust](https://img.shields.io/badge/Rust-1.95-000000?logo=rust)

## 構成

- Topcoat/Rust: HTML、3列カード、固定サイドバー、APIを提供
- `workers-rs`: Cloudflare FetchイベントをTopcoat Routerへ接続
- Topcoat Runtime: signalとShardによる複合検索、並び替え
- CSS: URLフラグメントによる要約モーダル
- Rust CLI: 記事JSONの検証、OGP取得、配信用索引の生成
- GitHub Actions: pull requestと主要ブランチのCI、`release`ブランチからのCloudflareデプロイ

Hono、Vite、TypeScript、手書きのブラウザJavaScriptは使用しません。WorkerはRustからWebAssemblyへコンパイルし、Cloudflare公式の[`workers-rs`](https://developers.cloudflare.com/workers/languages/rust/)で実行します。TopcoatのHTTPアプリとCloudflareアダプターを分離しているため、別のRustホストへ移す場合は`app/src/cloudflare.rs`だけを置き換えられます。

Topcoat Runtime 0.5は実験的な機能です。検索条件はブラウザのsignalへ保持し、変更時にRustのShardが結果領域だけをサーバーレンダリングします。ブラウザへ配信するJavaScriptはCargo.lockで固定したTopcoat Runtime本体だけです。

## 必要な環境

- Rust 1.95.0（`rust-toolchain.toml`で固定）
- `wasm32-unknown-unknown`ターゲット
- Node.js 22.12以降（Wrangler用、CIは24）
- npm
- `worker-build` 0.8.5

```bash
rustup target add wasm32-unknown-unknown
cargo install worker-build --version 0.8.5 --locked
npm install
cp .dev.vars.example .dev.vars
```

`.dev.vars`の`YOYAKU_REPOSITORY_URL`をフォーク先のURLへ変更します。未設定なら画面のGitHubリンクは表示されません。

## ローカルで起動

```bash
npm run validate:data
npm run dev
```

Wranglerが表示した`http://localhost:8787`を開きます。起動前にRust CLIが`public/data/articles.json`を再生成し、`worker-build`がTopcoatアプリをWasmへコンパイルします。

## 記事を追加

1. `article.schema.json`に従って`content/articles/<id>.json`を作り、重複しない`id`と`url`を設定します。
2. ローカルで作成・確認した要約を`summary`の配列へ入れます。
3. ジャンル、技術、読了時間、作成日、更新日を設定します。
4. 必要ならURLからOGPを取得します。
5. 検証と索引生成を実行します。

```bash
cargo run -p yoyaku -- enrich content/articles/my-article.json
npm run validate:data
npm run generate:data
```

`enrich`は対象URLへアクセスし、`og:title`、`og:description`、`og:image`を保存します。10秒のタイムアウト、5回までのリダイレクト、2MBのHTML上限があります。LLMは使いません。外部から渡された未確認URLでは実行しないでください。

このリポジトリには表示用のモック記事を同梱していません。記事を追加するまで一覧は0件で表示されます。記事スキーマは[article.schema.json](./article.schema.json)にあり、Rust CLIは次も検証します。

- 必須文字列、技術、要約が空でない
- URLがHTTPまたはHTTPS
- 日付が`YYYY-MM-DD`
- `updated_at`が`created_at`以降
- `reading_minutes`が1以上
- IDとURLがコレクション内で重複しない

## 検索と表示

キーワード、ジャンル、使用技術、掲載元、作成日の範囲、読了時間をANDで組み合わせます。キーワードはタイトル、全要約、掲載元、ジャンル、技術を対象にし、更新日、作成日、タイトルで並び替えられます。条件変更のたびにTopcoat RuntimeがShardへ問い合わせ、Rust側の同じ検索実装で一覧を差し替えます。

カード全体でURLフラグメントのモーダルを開きます。ページ遷移や追加のJavaScriptはなく、元記事へ移動するのはモーダル内の「元記事を開く」リンクだけです。

サイト名は[app/src/config.rs](./app/src/config.rs)で変更します。GitHubリンクは環境変数`YOYAKU_REPOSITORY_URL`から読み込みます。Rust CLIでOGPを取得するときも、同じ環境変数がUser-Agentへ使われます。

```bash
export YOYAKU_REPOSITORY_URL=https://github.com/your-name/your-repository
cargo run -p yoyaku -- enrich content/articles/my-article.json
```

## テストとビルド

```bash
cargo fmt --all --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
npm test
npm run build
npm run deploy:dry-run
```

`worker-build 0.8.5`のパニック回復ラッパーとTopcoat 0.5の組み合わせを避けるため、ビルドは`--no-panic-recovery`を使用します。通常のエラーはHTTPレスポンスとして処理されますが、Rustのpanicが発生したリクエストではWasmインスタンスが終了し、Cloudflare側で次のインスタンスが起動します。

## Cloudflareへデプロイ

手元から確認してデプロイする場合:

```bash
npm run deploy:dry-run
npm run deploy
```

GitHub Actionsから自動デプロイする場合は、フォーク先のSettingsで次を設定します。

- Actions secret `CLOUDFLARE_API_TOKEN`
- Actions secret `CLOUDFLARE_ACCOUNT_ID`

Cloudflare DashboardのWorker設定には、非機密の環境変数`YOYAKU_REPOSITORY_URL`としてフォーク先のURLを設定します。`wrangler.jsonc`は`keep_vars: true`なので、Dashboardの値は次回デプロイでも保持されます。

`release`ブランチへpushするとCIが実行され、成功した同じコミットだけがCloudflare Workersへデプロイされます。Secretsを設定していないフォークでは`release`ブランチを使わず、CI対象のpull requestまたは`main`ブランチだけを利用してください。トークン、アカウントID、カスタムドメイン、非公開記事をリポジトリへコミットしないでください。

## Commonと個人フォークの境界

このリポジトリへ含めるもの:

- Topcoatアプリ、Cloudflareアダプター、Rust CLI
- 汎用スキーマ、テスト、CI
- 空の`content/articles`ディレクトリ

個人用フォークだけへ置くもの:

- 自分の記事JSON
- 自分のサイト名と環境変数`YOYAKU_REPOSITORY_URL`
- Cloudflare Secretsとドメイン設定
- D1、管理画面、LLM分析など個人運用向け機能

上流の更新を取り込むときは、共通コードと自分の記事データを別コミットに分けておくと衝突を整理しやすくなります。

## License

MIT
