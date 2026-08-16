# Topcoat Runtime UI Migration Design

## 目的

Yoyakuの検索、並び替え、記事モーダルを手書きJavaScriptからTopcoat Runtime 0.5へ移し、配信層をRust中心にする。現在の見た目、Git管理の記事JSON、Cloudflare Workersへのデプロイ構成は維持する。

## 採用構成

- 検索条件はTopcoatの`signal`でブラウザ内に保持する。
- 条件変更時はTopcoatの`#[shard]`がRust側で記事を絞り込み、結果領域だけを再描画する。
- 検索と並び替えは`app/src/search.rs`の純粋関数へ集約し、通常のRustテストで検証する。
- 記事カードは要約モーダルへのアンカーとし、モーダルの表示と終了はURLフラグメントとCSSの`:target`で処理する。
- ブラウザへ配信するJavaScriptはTopcoat 0.5.0が生成したRuntimeだけとし、`app/web/main.js`と`app/web/filter.js`は削除する。

Topcoat Runtimeは実験的であるため、機能範囲を複合検索、並び替え、結果差し替えに限定する。検索条件をURLへ永続化する機能、クライアント側キャッシュ、楽観的更新は追加しない。

## Runtimeアセット

Topcoatの`runtime::script()`はAsset Contextを必要とする。Workerではファイルシステム上のAsset Bundleを実行時に読み込めないため、RuntimeのAsset IDを`/assets/topcoat-runtime.js`へ解決する埋め込みManifestをRouterへ登録する。

Runtime本体はCargoが取得した`topcoat-runtime` 0.5.0の`browser/dist/index.js`を`build.rs`で特定し、`include_str!`でWorkerへ埋め込む。これによりリポジトリには生成済みJavaScriptを複製せず、バージョンはCargo.lockで固定する。

## 検索データフロー

1. ルート画面は記事索引とファセットをTopcoatでSSRする。
2. 各検索入力の`@input`または`@change`が対応するsignalを書き換える。
3. Shardの引数が変わると、Topcoat Runtimeが`/_topcoat/shards/...`へPOSTする。
4. Workerは全入力を未信頼値として受け取り、長さ、日付、読了時間、並び順を正規化する。
5. `search.rs`がキーワード、ジャンル、技術、掲載元、作成日、読了時間をANDで適用し、指定順に並べる。
6. Shardは件数、適用中の条件、記事カード、空状態をまとめて返し、Runtimeが結果領域を置き換える。

## モーダル

各カードは`href="#article-<id>"`のリンクにする。同じShard内に記事ごとの要約パネルを置き、対象IDが`:target`になったときだけ中央に表示する。背景と閉じるリンクは`href="#"`でフラグメントを解除する。元記事リンクだけは新しいタブで開く。

この方式は追加の手書きJavaScriptを必要とせず、カード全体がリンクという既存要件も保つ。ページ遷移は発生せず、長い要約はパネル内部でスクロールする。

## エラー処理と安全性

- Shard引数は最大200文字へ制限し、未知の並び順は更新日の新しい順へ戻す。
- 日付は`YYYY-MM-DD`形式だけを検索条件として採用する。
- 読了時間は許可した値へ変換できない場合に無指定として扱う。
- 記事由来の値はTopcoatのエスケープを通し、記事文字列をHTMLとして評価しない。
- Runtimeアセットは固定バージョンからビルド時に取得し、見つからない場合は理由付きでビルドを失敗させる。
- JavaScriptが無効でも初期記事一覧と各カードの情報は読める。

## テストと完了条件

- Rust単体テストでNFKCキーワード、複合AND検索、日付範囲、読了時間、3種類の並び順、不正入力を検証する。
- RouterテストでTopcoat Runtimeタグ、Shardの初期HTML、RuntimeアセットのContent-Type、旧JavaScriptルートの404を検証する。
- `cargo fmt --all --check`、`cargo test --workspace`、`cargo clippy --workspace --all-targets -- -D warnings`、Wasmビルド、Wrangler dry-runを成功させる。
- ローカルWorkerで入力に応じたShard更新、カードからのモーダル表示、閉じる操作、長文要約のスクロールをブラウザ確認する。

## 対象外

D1、R2、管理画面、LLM要約、記事JSON同期、デプロイ先の追加は今回変更しない。個人記事JSONとそこから生成された`public/data/articles.json`も編集しない。
