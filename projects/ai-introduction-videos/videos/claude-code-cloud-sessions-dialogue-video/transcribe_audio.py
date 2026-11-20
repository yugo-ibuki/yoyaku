#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def transcribe(audio_path: Path, model_path: Path) -> dict:
    from faster_whisper import WhisperModel

    model = WhisperModel(str(model_path), device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(audio_path),
        language="ja",
        beam_size=5,
        temperature=0.0,
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    observed = []
    for segment in segments:
        observed.append({
            "start": round(float(segment.start), 3),
            "end": round(float(segment.end), 3),
            "text": segment.text.strip(),
            "avgLogprob": round(float(segment.avg_logprob), 4),
            "noSpeechProb": round(float(segment.no_speech_prob), 4),
            "words": [
                {
                    "start": None if word.start is None else round(float(word.start), 3),
                    "end": None if word.end is None else round(float(word.end), 3),
                    "text": word.word,
                    "probability": round(float(word.probability), 4),
                }
                for word in segment.words or []
            ],
        })
    return {
        "engine": "faster-whisper",
        "model": model_path.name,
        "language": info.language,
        "languageProbability": round(float(info.language_probability), 4),
        "settings": {
            "beamSize": 5,
            "temperature": 0.0,
            "wordTimestamps": True,
            "vadFilter": True,
            "conditionOnPreviousText": False,
        },
        "segments": observed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create timestamped ASR evidence without changing the source audio.")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = transcribe(args.audio, args.model)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
