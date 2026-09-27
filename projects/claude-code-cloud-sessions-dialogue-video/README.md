# Claude Code Cloud Sessions Dialogue Video

Claude Codeのクラウドセッションを、左の生徒猫と右の先生猫が説明する縦型対話動画の再現用プロジェクト。

## 完成物

- 最終動画: `claude-code-cloud-sessions-cats.mp4`
- 最終音声原本: `audio/ai-studio-original.wav`
- 生成入力と声設定: `audio/studio-input.json`
- 実測ターン: `verified_turns.json`
- 字幕アラインメント: `dialogue_alignment.json`
- レンダーメタデータ: `dialogue_metadata.json`
- ASR・声質証拠: `audio/asr-transcript.json`、`audio/ctc-crosscheck.json`、`audio/voice-evidence.json`
- 視覚確認画像: `qa/review-2-27-64-95-155.png`

動画は720×1280、24fps、H.264/AAC、164.208秒。音声原本は164.200秒、24kHzモノラルPCM16、SHA-256 `14b714b180b715362159f2688a20f35ff94af405d8faace2e7053614f561d52c`。

## 検証結果

この環境では主観的な音声試聴を実施していない。Faster Whisper ASR、独立CTC ASR、-38dBの波形無音区間、ターン別ピッチ分離、WhisperX強制アラインメントを組み合わせた機械検証である。

- 16ターン、左右8ターンずつ。左話者のターン中央値261.4Hz、右話者118.8Hz。
- 38字幕カードすべてが強制アラインメントの先頭文字へ直接対応。最低スコア0.624。
- ターン8は生成入力「スキル」に対し、2種類のASRが「スクリプト」と一致したため最終字幕を音声側へ変更。
- ターン16はFaster Whisperが中盤を脱落したが、独立CTC ASRと波形が全文相当の発話を確認。
- 字幕全行の描画幅は600px以下。最大564px。
- 2秒、27秒、64秒、95秒、155秒を目視し、字幕欠けと二重の頭がないことを確認。

主観的な発音、話し方の自然さ、年齢・性別の聞こえ方は未確認として残る。

## 再生成

```bash
python3 align_dialogue.py \
  --audio audio/ai-studio-original.wav \
  --verified-turns verified_turns.json
python3 render.py --audio audio/ai-studio-original.wav
python3 verify_timeline.py --audio audio/ai-studio-original.wav
```

音声が変わった場合は、ハッシュ、ASR、ターン境界、強制アラインメント、メタデータ、動画をすべて作り直す。文字数比例、均等割り、目標時間からの逆算は使わない。

## 音声なしでの検証

```bash
uv run --with pillow python -m unittest discover -s tests -v
python3 -m py_compile \
  dialogue.py align_dialogue.py render.py verify_timeline.py \
  transcribe_audio.py ctc_crosscheck.py analyze_voice.py
```

レンダーにはPillow、アラインメントにはWhisperX、動画出力と検査にはffmpeg/ffprobeを使う。
