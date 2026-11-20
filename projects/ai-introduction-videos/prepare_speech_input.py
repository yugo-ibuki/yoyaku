#!/usr/bin/env python3
"""AI紹介猫対話のTTS入力へ共有の先生音声設定を適用する。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS = Path(__file__).resolve().parent / "settings" / "speech.json"


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"{label}を読み込めません: {path}: {exc}") from exc
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}が有効なJSONではありません: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}のルートはJSONオブジェクトである必要があります: {path}")
    return value, raw


def prepare_payload(
    payload: dict[str, Any],
    settings: dict[str, Any],
    settings_path: Path,
    settings_raw: bytes,
    teacher_direction_override: str | None,
) -> dict[str, Any]:
    mapping = payload.get("speakerMapping")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("入力のspeakerMappingは空でないJSONオブジェクトである必要があります")

    teacher_character_id = settings.get("teacherCharacterId")
    teacher = settings.get("teacher")
    if not isinstance(teacher_character_id, str) or not teacher_character_id:
        raise ValueError("設定のteacherCharacterIdは空でない文字列である必要があります")
    if not isinstance(teacher, dict):
        raise ValueError("設定のteacherはJSONオブジェクトである必要があります")
    configured_direction = teacher.get("direction")
    relative_target = teacher.get("relativeTempoTarget")
    if not isinstance(configured_direction, str) or not configured_direction.strip():
        raise ValueError("設定のteacher.directionは空でない文字列である必要があります")
    if not isinstance(relative_target, (int, float)) or isinstance(relative_target, bool):
        raise ValueError("設定のteacher.relativeTempoTargetは数値である必要があります")
    if settings.get("automaticAudioTempoPostprocess") is not False:
        raise ValueError("設定のautomaticAudioTempoPostprocessはfalseである必要があります")

    prepared = copy.deepcopy(payload)
    prepared_mapping = prepared["speakerMapping"]
    teacher_speakers: list[str] = []
    for studio_speaker, speaker in prepared_mapping.items():
        if not isinstance(studio_speaker, str) or not studio_speaker:
            raise ValueError("speakerMappingの話者キーは空でない文字列である必要があります")
        if not isinstance(speaker, dict):
            raise ValueError(f"speakerMapping.{studio_speaker}はJSONオブジェクトである必要があります")
        direction = speaker.get("direction")
        if not isinstance(direction, str) or not direction.strip():
            raise ValueError(f"speakerMapping.{studio_speaker}.directionは空でない文字列である必要があります")
        if speaker.get("characterId") == teacher_character_id:
            teacher_speakers.append(studio_speaker)

    if len(teacher_speakers) != 1:
        raise ValueError(
            f"このプリセットの対象であるcharacterId={teacher_character_id!r}が"
            f"speakerMappingに1件必要です（検出: {len(teacher_speakers)}件）"
        )

    direction = teacher_direction_override or configured_direction
    prepared_mapping[teacher_speakers[0]]["direction"] = direction
    prepared["status"] = "speech_input_prepared_not_executed"
    prepared["styleInstructions"] = "\n".join(
        f"{studio_speaker}: {speaker['direction']}"
        for studio_speaker, speaker in prepared_mapping.items()
    )

    using_override = teacher_direction_override is not None
    prepared["speechSettings"] = {
        "status": "prepared_not_executed",
        "configPath": str(settings_path),
        "configSha256": hashlib.sha256(settings_raw).hexdigest(),
        "teacherCharacterId": teacher_character_id,
        "directionSource": "command_line_override" if using_override else "shared_config",
        "relativeTempoTarget": None if using_override else relative_target,
        "relativeTempoTargetStatus": (
            "not_applied_due_to_command_line_override"
            if using_override
            else "prompt_target_not_verified_in_ai_studio"
        ),
        "automaticAudioTempoPostprocess": False,
    }
    return prepared


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="既存TTS入力を保ったまま、AI紹介猫動画の先生音声設定を適用します。"
    )
    parser.add_argument("--input", required=True, type=Path, help="既存TTS入力JSON")
    parser.add_argument("--output", required=True, type=Path, help="新規作成する準備済みJSON")
    parser.add_argument(
        "--settings",
        type=Path,
        default=DEFAULT_SETTINGS,
        help=f"共有音声設定JSON（既定: {DEFAULT_SETTINGS}）",
    )
    parser.add_argument(
        "--teacher-direction",
        help="案件固有の先生向け演技指示。指定時は共有の約10%%目標を適用済みとして記録しません。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    settings_path = args.settings.resolve()
    if input_path == output_path:
        raise SystemExit("エラー: --inputと--outputに同じファイルは指定できません")
    if output_path.exists():
        raise SystemExit(f"エラー: 出力先は既に存在します: {output_path}")
    if args.teacher_direction is not None and not args.teacher_direction.strip():
        raise SystemExit("エラー: --teacher-directionに空文字列は指定できません")

    try:
        payload, _ = read_json_object(input_path, "入力")
        settings, settings_raw = read_json_object(settings_path, "設定")
        prepared = prepare_payload(
            payload,
            settings,
            settings_path,
            settings_raw,
            args.teacher_direction,
        )
        serialized = json.dumps(prepared, ensure_ascii=False, indent=2) + "\n"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8") as output_file:
            output_file.write(serialized)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"エラー: {exc}") from exc

    print(f"準備済み入力を作成しました（AI Studio未実行）: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
