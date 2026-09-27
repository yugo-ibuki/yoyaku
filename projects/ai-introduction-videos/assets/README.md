# 猫対話シーン共通素材

橙色のトラ猫の生徒を左、銀灰色のトラ猫の先生を右に置いた、複数の対話動画で再利用できる画像素材です。各場面は `base.png`、`left-speaking.png`、`right-speaking.png` の3枚で構成します。

## 場面一覧

| ディレクトリ | 画像サイズ | 内容 |
|---|---:|---|
| `outdoor-cafe/` | 941×1672（縦） | 屋外カフェ。基準の閉口画像と左右それぞれの発話画像 |
| `dining-room/` | 941×1672（縦） | 食卓。基準の食事画像と左右それぞれの発話画像 |
| `snow-campfire/` | 1672×941（横） | 雪中の焚き火。左右の椅子に座り、交互にマシュマロを食べながら話す画像 |

雪中シーンの `base.png` では2匹とも口を閉じ、食べていません。`left-speaking.png` では左の橙色猫が話し、右の灰色猫が皿上のマシュマロを舐めます。`right-speaking.png` では右の灰色猫が話し、左の橙色猫が食べます。実際に組み込み `image_gen` で使用したプロンプトは [`snow-campfire/PROMPTS.md`](snow-campfire/PROMPTS.md) に記録しています。

## 来歴と利用方法

- `outdoor-cafe/` は、Fractal Engineering 動画で使われていた3枚をバイト不変で移した共有保存先です。現在は `../fractal-engineering-dialogue-video/render.py` がこのディレクトリを直接参照します。
- `dining-room/` は、Fractal Engineering プロジェクトに追加素材として保存され、Claude Code Cloud Sessions 動画へバイト単位でコピーされていた3枚です。現在は `../claude-code-cloud-sessions-dialogue-video/render.py` がこのディレクトリを直接参照します。
- `snow-campfire/` は、2026-09-27 に Codex の組み込み `image_gen` で作成し、Fractal Engineering プロジェクトから移動した未使用の追加素材です。既存の縦動画には使用していません。

2本の動画プロジェクトは、このカタログ内の対応する3枚を共有入力として直接参照します。画像を変更すると再レンダー結果も変わるため、変更前後に `SHA256SUMS` を更新して整合性を確認してください。

## 整合性確認

```bash
cd projects/ai-introduction-videos/assets
shasum -a 256 -c SHA256SUMS
```
