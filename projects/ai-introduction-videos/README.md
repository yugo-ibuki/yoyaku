# AI紹介動画

左の橙色の生徒猫と右の灰色の先生猫がAI関連の話題を説明する動画、音声、台本、同期情報、共有画像をまとめた制作ディレクトリです。

## 構成

- [`assets/`](assets/README.md): 動画が直接参照する縦画像と横長画像
  - `outdoor-cafe/`: 941×1672。Fractal Engineering 動画で使用
  - `dining-room/`: 941×1672。Claude Code Cloud Sessions 動画で使用
  - `snow-campfire/`: 1672×941。既存の縦動画には未使用の追加素材
  - [`kotatsu-mikan/`](assets/kotatsu-mikan/README.md): 1672×941。数字・規模中心の個人情報漏洩解説動画で使用
- `videos/`: 動画プロジェクト
  - [`fractal-engineering-dialogue-video/`](videos/fractal-engineering-dialogue-video/README.md): Fractal Engineering の縦型対話動画と再現資料
  - [`claude-code-cloud-sessions-dialogue-video/`](videos/claude-code-cloud-sessions-dialogue-video/README.md): Claude Code Cloud Sessions の縦型対話動画と再現資料
  - [`privacy-breaches-2026-sep-oct-scale-dialogue-video/`](videos/privacy-breaches-2026-sep-oct-scale-dialogue-video/README.md): 承認済み8発話・78.6秒。9〜10月の関連事案と数千万件規模を大きな数字で伝える、対策付きの横型猫対話動画

画像は動画プロジェクトごとに複製せず、`assets/` の場面別3枚へ一本化しています。各レンダラーの既定値は、対応する共有画像を参照します。

## 整合性確認

```bash
cd projects/ai-introduction-videos
(cd assets && shasum -a 256 -c SHA256SUMS)
(cd videos/fractal-engineering-dialogue-video && shasum -a 256 -c SHA256SUMS)
(cd videos/claude-code-cloud-sessions-dialogue-video && shasum -a 256 -c SHA256SUMS)
(cd videos/privacy-breaches-2026-sep-oct-scale-dialogue-video && shasum -a 256 -c SHA256SUMS)
```

動画を再生成するときは各動画プロジェクトの README に従い、音声、字幕アラインメント、共有画像の整合性を確認してからレンダラーを実行してください。横長の雪中焚き火素材は 16:9 であり、720×1280 の縦動画へそのまま差し替える用途ではありません。

## 音声生成設定

この猫先生・生徒シリーズの共通設定は [`settings/speech.json`](settings/speech.json) にあります。先生だけを自然な会話より少し速め（従来の先生の話速より約10%速めが目安）にする演技指示で、生徒の声と話速は各制作入力のまま維持します。この値はAI Studioに入力する目安であり、実在を確認した数値速度パラメーターではありません。

AI Studioで生成する前に、既存のTTS入力から準備済み入力を新規作成します。次の `<動画>` を対象のディレクトリ名に置き換えて実行します。

```bash
python3 prepare_speech_input.py --input "videos/<動画>/tts-input.json" --output "/tmp/<動画>-tts-prepared.json"
```

出力の `styleInstructions` と話者ごとの声を実際のSpeech UIへ設定し、聞いた印象で話速を確認してください。ヘルパーは音声へ `atempo` などの後処理を自動適用しないため、再生成時の二重加速を防げます。案件ごとに話速の明示指定がある場合は `--teacher-direction` でその指示を優先します。
