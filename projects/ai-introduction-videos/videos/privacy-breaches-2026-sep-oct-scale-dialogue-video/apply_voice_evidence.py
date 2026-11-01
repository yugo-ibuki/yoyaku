#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Attach audio-specific pitch evidence to reviewed speaker handoffs.")
    parser.add_argument("--turns", required=True, type=Path)
    parser.add_argument("--voice", required=True, type=Path)
    args = parser.parse_args()
    turns = json.loads(args.turns.read_text(encoding="utf-8"))
    voice = json.loads(args.voice.read_text(encoding="utf-8"))
    if turns.get("audioSha256") != voice.get("audioSha256"):
        raise ValueError("voice evidence audio hash mismatch")
    left = voice.get("speakers", {}).get("left_student", {}).get("medianOfTurnMediansHz")
    right = voice.get("speakers", {}).get("right_teacher", {}).get("medianOfTurnMediansHz")
    if left is None or right is None or abs(float(left) - float(right)) < 40:
        raise ValueError("voice groups are not sufficiently separated for machine speaker evidence")
    voice_turns = voice.get("turns", [])
    if len(voice_turns) != len(turns.get("turns", [])):
        raise ValueError("voice evidence does not cover every turn")
    previous_pitch = None
    for reviewed, measured in zip(turns["turns"], voice_turns):
        if (reviewed.get("id"), reviewed.get("speakerId")) != (measured.get("id"), measured.get("speakerId")):
            raise ValueError("voice evidence turn identity mismatch")
        pitch = measured.get("medianPitchHz")
        if pitch is None:
            raise ValueError(f"turn {reviewed['id']} has no measurable pitch evidence")
        handoff = "first turn" if previous_pitch is None else f"previous-turn median pitch {previous_pitch:.1f} Hz"
        reviewed["review"]["evidence"] += (
            f"; voice-evidence current median pitch {float(pitch):.1f} Hz, {handoff}; "
            f"speaker group medians left {float(left):.1f} Hz/right {float(right):.1f} Hz"
        )
        previous_pitch = float(pitch)
    turns["voiceEvidence"] = {
        "file": args.voice.name,
        "sha256": sha256(args.voice),
        "leftMedianHz": left,
        "rightMedianHz": right,
        "subjectiveListening": False,
    }
    args.turns.write_text(json.dumps(turns, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.turns)


if __name__ == "__main__":
    main()
