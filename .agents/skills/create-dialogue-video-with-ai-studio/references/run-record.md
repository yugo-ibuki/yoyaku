# AI Studio Speech 実行記録

この雛形を案件の既存形式へ合わせて保存する。分からない値は推測せず `不明` と書き、認証情報、API キー、Cookie は記録しない。

```yaml
run:
  checked_at: "YYYY-MM-DDTHH:MM:SS+TZ"
  account: "画面で識別できる非機密情報"
  project: "プロジェクト名または非機密 ID"
  page: "Speech UI"
  model: "実行時に画面で確認したモデル"
  mode: "実行時に確認した生成モード"
  language: "言語"
  style: "全体のスタイル設定"
  observed_limits:
    speaker_count: "画面または公式資料で確認した値 / 不明"
    input_length: "画面または公式資料で確認した値 / 不明"
  generation_strategy: "single_run または segmented"

speakers:
  - character_id: "stable-character-id"
    visible_label: "視聴者に見せる名前または役割"
    studio_speaker: "AI Studio 内の話者識別子"
    voice: "実行時に選択した声"
    direction: "声の演技指示"
    pronunciation_notes: []

script:
  intended_path: "意図した最終台本のパス"
  intended_sha256: "意図した最終台本の SHA-256"
  studio_input_path: "AI Studio に入力した正確な文字列のパス"
  studio_input_sha256: "AI Studio 入力ファイルの SHA-256"
  input_adjustments: []
  turn_count: 0

audio:
  source_clips:
    - id: "clip-001"
      script_turns: "このクリップに含む発話 ID"
      speakers: ["stable-character-id"]
      downloaded_file: "保存した原音のパス"
      sha256: "原音の SHA-256"
      settings: "この生成で実際に使った設定。共通設定との差分も記録"
      review_notes: []
  assembly:
    required: false
    recipe_file: "単一生成なら空。分割時の順序・入出点・変換・間・フェードを記録したファイル"
    command_or_tool: "使用したツールと再現可能な設定"
    seam_review_notes: []
  final_file: "タイムラインの正本にする採用音声のパス"
  final_sha256: "採用音声の SHA-256"
  container_or_codec: "検査結果"
  duration_seconds: 0
  review:
    complete_playback: false
    script_matches: false
    speakers_match: false
    pronunciation_ok: false
    no_cutoff_or_duplicate: false
    full_script_covered: false
    voice_continuity_ok: false
    seams_ok: null # 単一生成では null、分割生成では監査結果
    notes: []

provenance:
  user_provided: []
  generated: []
  transformed: []
  unknown: []

derived:
  timeline_file: ""
  video_file: ""
  verification_file: ""
  based_on_audio_sha256: ""

external_actions:
  published: false
  uploaded: false
  pushed: false
  billing_or_subscription_changed: false
```

生成し直して採用音声のハッシュが変わったら、`derived` にある旧音声由来のタイムライン、動画、検証結果を再利用しない。
