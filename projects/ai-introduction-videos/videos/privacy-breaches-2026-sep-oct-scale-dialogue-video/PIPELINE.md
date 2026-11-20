# 新8発話・数字強調版の再現

承認と正本は `script-approval.json`、`turns.json`、新原音 `audio/ai-studio-original.wav`。本文や構成を変える場合は再確認し、音声が変わったら全てのASR・波形・話者・CTC・時刻・レビュー・MP4・抽出PCM・QAを作り直す。旧版の音声や時刻は使わない。

```bash
PY=/Users/yugo/.cache/uv/environments-v2/5286873ba2a43076/814f1ff8aa6f350a/bin/python
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4
"$PY" -m unittest discover -s tests -v
"$PY" render_sample_frames.py
"$PY" transcribe_audio.py --audio audio/ai-studio-original.wav \
  --model /Users/yugo/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120 \
  --output audio/asr-transcript.json
```

既存キャッシュのPillow/numpy/WhisperX/faster-whisper/torch/transformers/scipy、FFmpeg、Hiraginoフォントを使用する。パッケージ・モデルの新規取得は不要。WhisperXはキャッシュ限定で読み込む。音声生成とUI操作は親の担当で、本コードはブラウザ・X・課金設定を操作しない。

全文と数値・単位・延べ/最大/可能性・匿名性を照合する。低信頼語は無提示の局所ASRと独立CTCで確認し、生の不一致も保存する。CTCコマンドは `ctc_crosscheck.py --audio ... --model /Users/yugo/.cache/huggingface/hub/models--jonatasgrosman--wav2vec2-large-xlsr-53-japanese/snapshots/cf031e020336460d15a417eba710bbc5bb43be9a --span '<識別子>:<実測開始>:<実測終了>' --output ...`。今回の対象区間は `audio/ctc-crosscheck.json` と `audio/phonetic-crosscheck.json` にある。

`audio/turn-review-plan.json` に新audioSha256/asrSha256、各発話のASR対応、波形を確認する範囲、意味と話者の判断を明示する。文字数・等分・固定秒数・無音だけから話者や時刻を決めない。

```bash
"$PY" measure_reviewed_turns.py --audio audio/ai-studio-original.wav \
  --asr audio/asr-transcript.json --plan audio/turn-review-plan.json
"$PY" analyze_voice.py --audio audio/ai-studio-original.wav \
  --turns verified_turns.json --output audio/voice-evidence.json
"$PY" apply_voice_evidence.py --turns verified_turns.json --voice audio/voice-evidence.json
"$PY" align_dialogue.py --audio audio/ai-studio-original.wav --verified-turns verified_turns.json
```

WhisperX自動結果を `dialogue_alignment.raw.json` に保持する。数値先頭や低スコア境界は新音声固有のASR・波形でレビューし、`boundary-reviews.json` を作成して適用する。音声を変えた後に旧レビューの時刻を流用しない。

```bash
"$PY" review_machine_evidence.py --audio audio/ai-studio-original.wav \
  --alignment dialogue_alignment.json --reviews boundary-reviews.json
"$PY" render.py --audio audio/ai-studio-original.wav
"$PY" verify_timeline.py --audio audio/ai-studio-original.wav > qa/timeline-verification.json
"$PY" extract_qa_frames.py
```

レンダー前に承認対象SHA・原音SHA・素材SHA・120秒上限・全字幕・匿名性を検証する。`numeric_overlays.build_timeline` は各字幕カードの実測start/endから5状態を作り、`verify_timeline` で数字の区間が字幕から離れていないことを再検証する。T4の切替は文・字幕境界、T2とT6は各ターンの採用字幕範囲を使用する。

完成MP4のcodec/fps/尺・匿名title/comment、原音とAAC復号のずれ・尺差・相関を確認する。全字幕、全交代の前後、全発話ピーク、数字5状態、先頭末尾を元MP4から毎回抽出してページ分割する。主観試聴は機械検証と区別し、実施していなければfalseを維持する。
