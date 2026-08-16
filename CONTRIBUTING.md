# Contributing

IssueやPull Requestを歓迎します。個人用の記事データや秘密情報は含めず、共通テンプレートとして再利用できる変更だけを送ってください。

## 開発手順

```bash
rustup target add wasm32-unknown-unknown
cargo install worker-build --version 0.8.5 --locked
npm install
cargo fmt --all --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
npm test
npm run build
npm run deploy:dry-run
```

記事データの仕様を変更する場合は、Rustのモデル、`article.schema.json`、README、記事保存スキルを同じPull Requestで更新してください。Cloudflare以外でも使えるアプリ境界を保ち、プラットフォーム固有コードは専用アダプターへ置いてください。

検索UIは実験的なTopcoat Runtime 0.5のsignalとShardで実装しています。ブラウザ用の手書きJavaScriptは追加せず、検索ロジックは`app/src/search.rs`へ置いてRustテストを追加してください。Runtime APIを更新する場合はWasmビルドと実ブラウザ操作も確認してください。

## サンプルデータ

- 実在人物の個人情報、秘密URL、有料記事の本文を含めないでください。
- 要約は著作物の長い引用ではなく、自分の言葉で作成してください。
- OGP画像URLは元サイトの利用条件を確認してください。
