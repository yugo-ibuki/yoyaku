#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path

from dialogue import TURNS


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an unmeasured canonical-script turn template tied to one adopted WAV hash.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--asr", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "verified_turns.json")
    args = parser.parse_args()
    with wave.open(str(args.audio), "rb") as audio:
        if audio.getcomptype() != "NONE" or audio.getsampwidth() != 2 or audio.getnchannels() != 1:
            raise ValueError("adopted audio must be mono uncompressed 16-bit PCM WAV")
        info = {
            "channels": audio.getnchannels(),
            "sampleWidth": audio.getsampwidth(),
            "sampleRate": audio.getframerate(),
            "frames": audio.getnframes(),
            "duration": audio.getnframes() / audio.getframerate(),
        }
    asr = json.loads(args.asr.read_text(encoding="utf-8"))
    document = {
        "version": 1,
        "audio": relative(args.audio),
        "audioSha256": sha256(args.audio),
        "audioInfo": info,
        "asrEvidence": relative(args.asr),
        "asrSegmentCount": len(asr.get("segments", [])),
        "status": "pending_audio_and_boundary_review",
        "note": "No prior ASR slices or equal-duration timing is reused. Fill bounds only after reviewing this audio's transcript, waveform, and speaker handoffs.",
        "turns": [{
            "id": turn.id,
            "speakerId": turn.speaker_id,
            "scriptText": turn.text,
            "ttsText": turn.tts_text,
            "observedText": "",
            "asrReferences": [],
            "textAssessment": {"status": "pending", "evidence": ""},
            "start": None,
            "end": None,
            "review": {"status": "pending", "subjectiveListening": False, "evidence": ""},
        } for turn in TURNS],
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
