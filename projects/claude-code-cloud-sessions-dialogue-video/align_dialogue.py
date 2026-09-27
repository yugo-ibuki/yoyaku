#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path
from typing import Any

from dialogue import TURNS


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise ValueError(f"input must be inside the project: {path}") from exc


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24_000):
            raise ValueError("final audio must be mono 16-bit PCM WAV at 24 kHz")
        return audio.getnframes() / audio.getframerate()


def validate_verified_turns(audio_path: Path, document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("audioSha256") != sha256(audio_path):
        raise ValueError("verified turns audio hash does not match final audio")
    items = document.get("turns", [])
    if len(items) != len(TURNS):
        raise ValueError(f"expected {len(TURNS)} verified turns")
    duration = audio_duration(audio_path)
    previous_end = 0.0
    for expected, item in zip(TURNS, items):
        if item.get("id") != expected.id or item.get("speakerId") != expected.speaker_id:
            raise ValueError(f"turn {expected.id} identity mismatch")
        if item.get("scriptText") != expected.text or not item.get("asrText"):
            raise ValueError(f"turn {expected.id} needs the confirmed script and observed ASR text")
        assessment = item.get("textAssessment", {})
        if assessment.get("status") not in {"machine_compatible", "asr_disagreement"} or not assessment.get("evidence"):
            raise ValueError(f"turn {expected.id} needs an explicit ASR/script assessment")
        review = item.get("review", {})
        if review.get("status") not in {"machine_reviewed", "human_reviewed"} or not review.get("evidence"):
            raise ValueError(f"turn {expected.id} needs speaker/text review evidence")
        if review["status"] == "machine_reviewed" and review.get("subjectiveListening") is not False:
            raise ValueError(f"turn {expected.id} machine review must record subjectiveListening=false")
        if item.get("start") is None or item.get("end") is None:
            raise ValueError(f"turn {expected.id} start/end must be measured from the final audio")
        start, end = float(item["start"]), float(item["end"])
        if start < previous_end or start >= end or end > duration + 0.002:
            raise ValueError(f"turn {expected.id} has invalid or overlapping bounds")
        previous_end = end
    return items


def find_aligned_char(chars: list[dict[str, Any]], index: int, limit: int) -> tuple[dict[str, Any], str]:
    if index < len(chars) and chars[index].get("start") is not None:
        return chars[index], "exact_first_char"
    for offset in range(index + 1, min(limit, len(chars))):
        if chars[offset].get("start") is not None:
            return chars[offset], "first_char_unmapped_used_next_char"
    raise ValueError("subtitle card has no aligned character; manual repair is required")


def align(audio_path: Path, verified_path: Path) -> dict[str, Any]:
    verified = json.loads(verified_path.read_text(encoding="utf-8"))
    bounds = validate_verified_turns(audio_path, verified)
    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError("whisperx is required only for final-audio alignment") from exc

    model, model_metadata = whisperx.load_align_model(language_code="ja", device="cpu")
    segments = [
        {"start": float(item["start"]), "end": float(item["end"]), "text": turn.text}
        for turn, item in zip(TURNS, bounds)
    ]
    result = whisperx.align(
        segments,
        model,
        model_metadata,
        whisperx.load_audio(str(audio_path)),
        "cpu",
        return_char_alignments=True,
    )
    if len(result.get("segments", [])) != len(TURNS):
        raise RuntimeError("forced alignment did not return all 16 turns")

    utterances = []
    for turn, verified_turn, aligned in zip(TURNS, bounds, result["segments"]):
        chars = aligned.get("chars", [])
        if "".join(char.get("char", "") for char in chars) != turn.text:
            raise RuntimeError(f"turn {turn.id} alignment character sequence differs from script")
        cursor = 0
        cards = []
        for index, marked in enumerate(turn.cards):
            text = marked.replace("|", "")
            found, status = find_aligned_char(chars, cursor, cursor + len(text))
            predicted = round(float(found["start"]), 3)
            cards.append({
                "text": text,
                "lines": marked.split("|"),
                "predictedStart": predicted,
                "alignedFirstChar": found.get("char"),
                "score": None if found.get("score") is None else round(float(found["score"]), 3),
                "mappingStatus": status,
            })
            cursor += len(text)
        for index, card in enumerate(cards):
            card["subtitleStart"] = round(float(verified_turn["start"]), 3) if index == 0 else card["predictedStart"]
            card["subtitleEnd"] = (
                cards[index + 1]["predictedStart"] if index + 1 < len(cards) else round(float(verified_turn["end"]), 3)
            )
        utterances.append({
            "id": turn.id,
            "speakerId": turn.speaker_id,
            "speakerLabel": turn.speaker_label,
            "start": round(float(verified_turn["start"]), 3),
            "end": round(float(verified_turn["end"]), 3),
            "text": turn.text,
            "turnReview": verified_turn["review"],
            "textAssessment": verified_turn["textAssessment"],
            "asrText": verified_turn["asrText"],
            "cards": cards,
        })
    return {
        "version": 1,
        "audio": relative_to_root(audio_path),
        "audioSha256": sha256(audio_path),
        "verifiedTurns": relative_to_root(verified_path),
        "method": "Faster Whisper ASR and -38 dB waveform silence machine review, independent CTC cross-check for disputed spans, then WhisperX Japanese forced character alignment; no subjective listening",
        "utterances": utterances,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Align caption cards inside ASR/waveform machine-reviewed speaker turns.")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--verified-turns", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dialogue_alignment.json")
    args = parser.parse_args()
    output = align(args.audio, args.verified_turns)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
