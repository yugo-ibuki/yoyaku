# Topcoat Cloudflare Workers Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hono、Vite、TypeScriptの配信層をTopcoatと`workers-rs`のRust Workerへ置き換え、既存のYoyaku UIと記事JSON運用を維持する。

**Architecture:** `yoyaku` CLIが生成した索引をRust Workerへ埋め込み、TopcoatがHTMLとAPIを返す。Cloudflare固有処理はFetchアダプターだけに限定し、検索とモーダルは依存のないブラウザJavaScriptで初期HTMLを操作する。

**Tech Stack:** Rust 1.95、Topcoat 0.5、workers-rs 0.8、worker-build 0.8、Wrangler 4、Node.js組み込みテスト

---

## File map

- `Cargo.toml`: `app`と`cli`のWorkspace。
- `rust-toolchain.toml`: Rust 1.95とWasmターゲット。
- `app/Cargo.toml`: Topcoat Workerクレート。
- `app/src/lib.rs`: 埋め込み索引とRouter。
- `app/src/page.rs`: SSR画面。
- `app/src/routes.rs`: APIとアセット。
- `app/src/cloudflare.rs`: Cloudflare Fetchアダプター。
- `app/src/config.rs`: サイト設定。
- `app/web/filter.js`: 純粋な検索・並び替え。
- `app/web/main.js`: DOM接続。
- `app/web/style.css`: 既存デザイン。
- `app/tests/app.rs`: Topcoat RouterとHTMLの統合テスト。
- `app/web/filter.test.js`: ブラウザ検索ロジックのNodeテスト。
- `wrangler.jsonc`: Wasm Worker設定。
- `package.json`: WranglerとJavaScriptテスト用コマンド。

### Task 1: Rust Workspaceと失敗するWorkerテスト

- [ ] `Cargo.toml`に`members = ["app", "cli"]`のWorkspaceを作り、`app/Cargo.toml`へTopcoat、serde、`yoyaku`を追加する。
- [ ] `app/tests/app.rs`へ、ルートHTMLがYoyaku、3列グリッド用クラス、記事タイトル、要約テンプレートを含むことを期待するテストを書く。
- [ ] `cargo test -p yoyaku-app`を実行し、`yoyaku_app`が存在しないため失敗することを確認する。
- [ ] `app/src/lib.rs`、`page.rs`、`config.rs`を最小実装し、同じテストを成功させる。

### Task 2: APIとアセットをテスト駆動で追加

- [ ] `app/tests/app.rs`へ`/api/health`のJSON、`/api/articles`のCache-Control、`/assets/style.css`とJavaScriptのContent-Typeを期待するテストを追加する。
- [ ] テストを実行し、未登録ルートが404になることを確認する。
- [ ] `app/src/routes.rs`へTopcoatの`#[route]`を追加し、Routerへ登録してテストを成功させる。
- [ ] 不正な記事文字列がHTML要素として解釈されないことを期待するテストを追加し、Topcoatのテキスト・属性エスケープで成功させる。

### Task 3: 検索と並び替えをテスト駆動で移植

- [ ] `app/web/filter.test.js`へ、NFKC正規化キーワード、複合AND条件、更新日・作成日・タイトル順を期待するNodeテストを書く。
- [ ] `npm test`を実行し、`filter.js`がないため失敗することを確認する。
- [ ] `app/web/filter.js`へ`normalize`、`matchesArticle`、`compareArticles`を実装してテストを成功させる。
- [ ] `app/web/main.js`へフォーム読取、カード非表示、DOM並び替え、件数、条件表示、リセットを接続する。

### Task 4: モーダルと承認済みCSSを移植

- [ ] Rust統合テストへカードがボタンであり、モーダルが1つだけ存在し、要約段落が`template`へ出力される期待を追加する。
- [ ] テストを実行し、不足するマークアップで失敗することを確認する。
- [ ] `page.rs`へモーダルとカードメタデータを追加し、`main.js`へ開閉、背景クリック、スクロールリセット、元記事リンクを実装する。
- [ ] 既存`src/client/style.css`を`app/web/style.css`へ移し、記事ラッパーに必要な最小調整を加える。

### Task 5: CloudflareアダプターとWasmビルド

- [ ] `app/src/cloudflare.rs`へ`worker::HttpRequest`をTopcoat Bodyへ変換し、`Router::handle`へ渡すFetchイベントを追加する。
- [ ] `rust-toolchain.toml`へRust 1.95と`wasm32-unknown-unknown`を設定する。
- [ ] `worker-build --release --no-panic-recovery app`で`app/build/worker/shim.mjs`とWasmが生成されることを確認する。
- [ ] `wrangler.jsonc`を生成物へ向け、互換日、Observability、ビルドコマンドを設定する。

### Task 6: Node依存、CI/CD、文書を更新

- [ ] Hono、Vite、TypeScript、Vitest、Cloudflare Vite Pluginと旧`src`、`worker`、`index.html`を削除する。
- [ ] `package.json`をWrangler、JavaScriptテスト、Rust CLI、Workerビルド用コマンドだけに縮小し、lockfileを再生成する。
- [ ] CIをRust 1.95、Workspace fmt/test/clippy、Nodeテスト、Wasm dry-runへ更新する。
- [ ] `release`成功後のデプロイWorkflowを新しい`npm run deploy`へ接続する。
- [ ] READMEとCONTRIBUTINGへTopcoat構成、Rust 1.95、ローカル起動、フォーク設定を記載する。

### Task 7: 完全検証

- [ ] `cargo fmt --all --check`、`cargo test --workspace`、`cargo clippy --workspace --all-targets -- -D warnings`を実行する。
- [ ] `npm test`、`npm run build`を実行する。
- [ ] Wranglerローカル環境で`/`、`/api/health`、`/api/articles`、CSS、JavaScriptをHTTP確認する。
- [ ] `npm run deploy:dry-run`と`git diff --check`を成功させる。
- [ ] `git status --short`で既存の記事削除とCI変更を保持し、秘密情報や実デプロイがないことを確認する。
