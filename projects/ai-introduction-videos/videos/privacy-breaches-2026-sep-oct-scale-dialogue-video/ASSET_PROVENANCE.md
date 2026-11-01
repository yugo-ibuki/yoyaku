# 素材と制作の来歴

画像はユーザーが採用した共有こたつ素材assets/kotatsu-mikan/{base,left-speaking,right-speaking}.pngの3枚を直接参照する。生成元・プロンプトは共有素材ディレクトリに保持し、本版で新規画像生成・原画像上書きは行わない。実画像SHAと口元楕円はrender-config.jsonに固定している。

台本は2026-11-02の明示確認に基づく新8発話419文字。旧版の原音や時刻はコピーしていない。承認原文書SCRIPT_REVIEW_SCALE.mdはバイトコピーで、script-approval.jsonに対象SHAを固定した。音声入力はaudio/studio-input-original.json、共有設定適用後はaudio/studio-input.json。数字・SMSの発音変換と原表記はturns.jsonに対応付けた。

本版音声は親がAI Studio UIから新たに1回生成・保存したaudio/ai-studio-original.wav。78.600秒、mono PCM16、24kHz、SHA-256は05ab63d0d16a988d9a73d788a9bdb75a5d4afcdba2eb1ec3b05ee5e81dfd5836。原本を無変換で保存し、速度変更・音声編集は行っていない。実UI・ダウンロード・原本の来歴は親所有audio/generation-record.jsonに記録する。

制作コードのみ既存ローカルパイプラインを参考にして適応し、numeric_overlays.pyで新たに字幕連動の5数字状態を追加した。承認済み新台本・原音・資料基準日を固定し、新音声から全タイムラインとQAを生成する。主観的試聴はfalseとして、機械検証・親の視覚確認と区別する。
