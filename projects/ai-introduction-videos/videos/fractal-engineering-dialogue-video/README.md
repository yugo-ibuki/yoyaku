# Fractal Engineering 猫対話動画

フラクタルエンジニアリングの記事を題材にした、猫の生徒と先生による縦型対話動画の完成版と再現用素材です。リポジトリに収録していますが、動画の配信・サイトへの掲載・デプロイはしていません。

## 出典と来歴

- 元記事: [Fractal Engineering](https://torus-engineering.uhyo.workers.dev/ja/fractal/)
- リポジトリ内の記事要約: [`../../../../content/articles/fractal-engineering.json`](../../../../content/articles/fractal-engineering.json)
- 元画像を作成した Codex タスク: `codex://threads/01a0dd4d-b4e4-7652-8e4a-30710bf51284`
- 画像、音声、台本、アラインメント、完成動画は 2026-09-26〜27 の制作セッションから完成版を収録した。元記事の全文は複製していない。
- 使用画像を含む屋外カフェ、食卓、雪中焚き火の画像は、共通の[猫対話シーン素材カタログ](../../assets/README.md)に整理している。この動画は `../../assets/outdoor-cafe/` の3枚を直接参照する。

## 収録内容

- `../../assets/outdoor-cafe/base.png`, `../../assets/outdoor-cafe/left-speaking.png`, `../../assets/outdoor-cafe/right-speaking.png`: 閉口・左右発話の完成画像
- `dialogue-new.wav`: 24 kHz、16-bit、mono、157.920秒の完成音声
- `dialogue_alignment.json`: WhisperX による文字単位の強制アラインメントと波形確認結果
- `dialogue_metadata.json`: レンダリングに使う16ターン・34字幕カード
- `fractal-engineering-cats-aligned.mp4`: H.264/AAC、720×1280、24 fps、157.920秒の完成動画
- `align_dialogue.py`, `render.py`: アラインメントと描画の再現スクリプト
- `verify_timeline.py`: 音声ハッシュ、話者、台本、カード連続性、強制アラインメント、動画形式の検証ゲート
- [`DIALOGUE.md`](DIALOGUE.md): 完成台本と音声ペルソナ
- `SHA256SUMS`: 同梱ファイルの整合性一覧

旧152.48秒音声と、字幕修正前の2本の動画は意図的に含めていません。

## 同期不具合と修正根拠

最初の方式は、文字数比例で字幕時間を配り、無音区間だけで話者ターンを推定していました。長い発話内の自然な間を話者交代と誤認できるため、第6ターンの先生の開始を48.735秒付近として扱い、生徒の発話と重なりました。

完成版では実際の音声トランスクリプトと波形で16ターンを先に確認し、第6ターンを53.572秒へ修正しました。その後に確定台本を各ターン内で強制アラインメントし、34カードの切替時刻を求めています。低信頼だった第6ターン第3カードは、文字・波形の立ち上がり・直前の無音を手動確認した記録を JSON に残しています。

## 再現

macOS、`uv`、Python 3.11、`ffmpeg`、`jq` が必要です。既定フォントは macOS のヒラギノ角ゴシックです。別環境では `render.py --font /path/to/japanese-font.ttf` を指定してください。

同梱スナップショットを変更する前に、現在のファイルが保存時点と一致することを確認します。

```bash
cd projects/ai-introduction-videos/videos/fractal-engineering-dialogue-video
shasum -a 256 -c SHA256SUMS
```

`SHA256SUMS` は同梱したスナップショットの整合性確認用です。アラインメントや動画を再生成すれば出力のハッシュは変わるため、再生成後にこの一覧との一致は期待しません。

再生成は、重い動画描画の前にタイムライン検証を通します。

```bash
cd projects/ai-introduction-videos/videos/fractal-engineering-dialogue-video
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python whisperx numpy pillow

.venv/bin/python align_dialogue.py
jq '.utterances[] | .cards[] | select((.score // 0) < 0.5 or .mappingStatus != "exact_first_char") | {utteranceId, cardIndex, text, score, mappingStatus, manualReview}' dialogue_alignment.json

# 低信頼境界を再確認し、manualReview に status: "reviewed" と具体的な evidence を記録する
.venv/bin/python render.py --metadata-only
.venv/bin/python verify_timeline.py --skip-video

.venv/bin/python render.py --font "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
.venv/bin/python verify_timeline.py
```

`align_dialogue.py` は日本語アラインメントモデルを初回に取得し、`dialogue_alignment.json` を作り直します。その際、既存の `manualReview` 記録は引き継がれないため、第6ターン第3カードを含む低信頼境界を再確認して記録してください。

モデル重みとキャッシュはこのプロジェクトに含めません。音声を再生成した場合は古い JSON と動画を流用せず、アラインメントから全工程を再実行します。MP4 の出力成功だけでは同期が正しい証拠にならないため、描画前後の検証を省略しないでください。

## 検証

```bash
python3 -m unittest discover -s tests -v
python3 verify_timeline.py --skip-video
python3 verify_timeline.py
ffprobe -v error -show_entries format=duration:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels -of json fractal-engineering-cats-aligned.mp4
```

`verify_timeline.py --skip-video` は16ターン、左右各8ターン、34カード、カード間の空白・重複なし、台本一致、低信頼境界の確認記録、後続カードの強制アラインメント一致、音声 SHA-256 一致を描画前に確認します。引数なしでは、さらに完成 MP4 のストリームと長さを検証します。音声ハッシュが変わったまま古いタイムラインを使うと失敗します。
