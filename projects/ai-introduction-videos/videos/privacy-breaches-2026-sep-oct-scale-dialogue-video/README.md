# 猫と学ぶ 情報漏洩の数字と規模

ユーザーが2026年11月2日に確認した、主観的な猫の反応と対策を含む8発話419文字の新しい動画です。**完成MP4は78.600秒（約1分19秒）**、20字幕、1280×720、24fps、H.264/AAC。情報の基準日は2026年11月1日に固定し、既存の4事例版とは別に制作しました。

完成ファイル：`privacy-breaches-2026-sep-oct-scale-cats.mp4`

## 台本の確認と新音声

確認対象の `SCRIPT_REVIEW_SCALE.md` は提示時点の文書をバイト一致で保存しています。内部のpending表記はその時点の履歴であり、その後のユーザー「おk、じゃ動画作って」（2026-11-02）による承認は `script-approval.json` に記録しました。正確な承認時刻は不明です。原文書と新canonical `turns.json` のSHAを固定し、レンダー前にも照合します。

本文・順序・数字・主観的な口調は維持しました。数字を意味の変わらない漢字へ、SMSをエスエムエスへ変換し、表示本文との対応を `pronunciationReplacements` に記録しています。`prepare_speech_input.py` で共有先生設定を適用しました。入力は `audio/studio-input-original.json` と `audio/studio-input.json`、実UIの照合・生成・保存の記録は親所有の `audio/generation-record.json` と `audio/ui-input-verification.json` です。

採用原音 `audio/ai-studio-original.wav` は新8発話を1回生成した原本で、78.600秒、mono PCM16、24kHz。SHA-256は `05ab63d0d16a988d9a73d788a9bdb75a5d4afcdba2eb1ec3b05ee5e81dfd5836`。音声編集・加速・旧音声の流用は行っていません。

## 数字を実測字幕に合わせて表示

顔と口を避けてこたつの中央下部へ数字パネルを置き、字幕と干渉しないようにしています。数字の切替時刻は新音声の検証済み字幕から得ています。

| 状態 | 主数字 | 限定・意味 |
|---|---|---|
| T2 | 1,654件 | 9～10月の公表・掲載事案数。漏洩のおそれ等を含む。音声は1600件以上。 |
| T4・メール配信 | 延べ約5,163万件 | 延べ件数を人数へ換算しない。 |
| T4・会員情報 | 約2,252万件 | 流出の可能性。 |
| T4・宿泊予約 | 最大約445万人 | 閲覧・取得の可能性。 |
| T6・比較 | 5,163万件 | 1秒に1件でも1年以上。件数の比較。 |

T1/3/5/7と対策のT8は数字パネルを表示せず、会話・字幕を読みやすくしました。個別企業・サービス・自治体名、URL、制作・調査過程を読み上げや公開caption/footer/hero/tagsへ入れていません。出典と原数値は `SOURCE_NOTES.md` と承認原文書に保持し、異なる事案の件数・人数は合算しません。

## 同期と検証

新音声のSHAだけからASR、局所ASR、独立CTC、焦点CTC、波形、話者ピッチを測定しました。左右4回ずつ・全7交代を検証し、8ターン内で正確なTTS本文をWhisperX強制アラインメントしました。低信頼・数値先頭2境界を新音声でレビューし、口元・字幕・数字パネルを同じ採用タイムラインで描画しています。

ASRの感染サイト/感染登録、SNS、利用名材等の不一致は、独立CTCの会員/員登録系、Mの発音、利用明細と比較して機械レビューしました。生の異なる結果と判断を `audio/turn-review-plan.json`、`audio/asr-local-crosscheck.json`、`audio/ctc-crosscheck.json`、`audio/phonetic-crosscheck.json` に残しています。

AAC復号と原音の開始ずれは0秒、全編波形相関0.99989195、復号尺差+0.034667秒（AAC末尾パディングを含む）でした。詳細は `qa/timeline-verification.json`、`audio/mp4-audio-verification.json`、`qa/MACHINE_QA.md` を参照してください。全字幕・全交代・全ピーク・数字5状態・冒頭末尾は `qa/frame-manifest.json` と `qa/contact-sheet-*.png` に保存し、親が全5ページ・50フレームを目視済みで、その正式記録は `qa/visual-review.json` に記録しています。

再現手順は `PIPELINE.md`、仕様・承認・実行・素材の来歴は `PRODUCTION_SPEC.md`、`script-approval.json`、`RUN_RECORD.md`、`ASSET_PROVENANCE.md` を参照してください。versionは1。旧版の音声・動画は流用せず、既存ファイルを保持しています。

主観的な全編試聴は未実施として `subjectiveListening: false` を維持します。機械認識や画像確認を耳での確認とは扱いません。Xへのアクセス・添付はユーザーの延期指定に従っています。課金設定は変更していません。完成後のGit pushはユーザーから別途指示されています。
