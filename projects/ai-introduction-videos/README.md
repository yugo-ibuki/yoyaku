# AI紹介動画

左の橙色の生徒猫と右の灰色の先生猫がAI関連の話題を説明する動画、音声、台本、同期情報、共有画像をまとめた制作ディレクトリです。

## 構成

- [`assets/`](assets/README.md): 2本の動画が直接参照する縦画像と、追加の横長画像
  - `outdoor-cafe/`: 941×1672。Fractal Engineering 動画で使用
  - `dining-room/`: 941×1672。Claude Code Cloud Sessions 動画で使用
  - `snow-campfire/`: 1672×941。既存の縦動画には未使用の追加素材
- `videos/`: 動画プロジェクト
  - [`fractal-engineering-dialogue-video/`](videos/fractal-engineering-dialogue-video/README.md): Fractal Engineering の縦型対話動画と再現資料
  - [`claude-code-cloud-sessions-dialogue-video/`](videos/claude-code-cloud-sessions-dialogue-video/README.md): Claude Code Cloud Sessions の縦型対話動画と再現資料

画像は動画プロジェクトごとに複製せず、`assets/` の場面別3枚へ一本化しています。各レンダラーの既定値は、対応する共有画像を参照します。

## 整合性確認

```bash
cd projects/ai-introduction-videos
(cd assets && shasum -a 256 -c SHA256SUMS)
(cd videos/fractal-engineering-dialogue-video && shasum -a 256 -c SHA256SUMS)
(cd videos/claude-code-cloud-sessions-dialogue-video && shasum -a 256 -c SHA256SUMS)
```

動画を再生成するときは各動画プロジェクトの README に従い、音声、字幕アラインメント、共有画像の整合性を確認してからレンダラーを実行してください。横長の雪中焚き火素材は 16:9 であり、720×1280 の縦動画へそのまま差し替える用途ではありません。
