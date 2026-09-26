from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
import whisperx

from render import DIALOGUE, TIMINGS


ROOT = Path(__file__).resolve().parent
MODEL_ID = "jonatasgrosman/wav2vec2-large-xlsr-53-japanese"


def plain(text: str) -> str:
    return text.replace("|", "")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        raise ValueError(f"Output metadata requires a project-local audio path: {resolved}")


def load_samples(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Expected mono pcm_s16le WAV")
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return samples, rate


def rms_db(samples: np.ndarray, rate: int, start: float, end: float) -> float | None:
    part = samples[max(0, round(start * rate)):min(len(samples), round(end * rate))]
    if not len(part):
        return None
    rms = float(np.sqrt(np.mean(part * part)))
    return round(20 * math.log10(max(rms, 1e-9)), 2)


def detect_silences(path: Path) -> list[dict]:
    command = [
        "ffmpeg", "-hide_banner", "-i", str(path),
        "-af", "silencedetect=noise=-38dB:d=0.25", "-f", "null", "-",
    ]
    completed = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False)
    starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", completed.stderr)]
    ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", completed.stderr)]
    return [{"start": round(start, 3), "end": round(end, 3)} for start, end in zip(starts, ends)]


def find_char(chars: list[dict], index: int, card_end: int) -> tuple[dict | None, str]:
    if index < len(chars) and chars[index].get("start") is not None:
        return chars[index], "exact_first_char"
    for offset in range(index + 1, min(card_end, len(chars))):
        if chars[offset].get("start") is not None:
            return chars[offset], "first_char_unmapped_used_next_char"
    return None, "unmapped"


def legacy_proportional_starts(start: float, end: float, cards: list[str]) -> list[float]:
    weights = np.array([
        max(4, len(text) + 2 * sum(text.count(mark) for mark in "、。？！"))
        for text in cards
    ], dtype=float)
    minimum = min(3.0, (end - start) / len(cards))
    durations = minimum + max(0.0, end - start - minimum * len(cards)) * weights / weights.sum()
    starts = [start]
    for duration in durations[:-1]:
        starts.append(starts[-1] + float(duration))
    return starts


def align_utterances(audio_path: Path, utterance_ids: list[int]) -> dict:
    model, model_metadata = whisperx.load_align_model(language_code="ja", device="cpu")
    audio = whisperx.load_audio(str(audio_path))
    segments = []
    for utterance_id in utterance_ids:
        start, end = TIMINGS[utterance_id - 1]
        chunks = DIALOGUE[utterance_id - 1][1]
        segments.append({"start": start, "end": end, "text": "".join(plain(chunk) for chunk in chunks)})
    result = whisperx.align(
        segments,
        model,
        model_metadata,
        audio,
        "cpu",
        return_char_alignments=True,
    )
    if len(result["segments"]) != len(segments):
        raise RuntimeError(f"Expected {len(segments)} aligned segments, got {len(result['segments'])}")

    samples, rate = load_samples(audio_path)
    silences = detect_silences(audio_path)
    utterances = []
    for utterance_id, aligned in zip(utterance_ids, result["segments"]):
        speaker, marked_cards = DIALOGUE[utterance_id - 1]
        utterance_start, utterance_end = TIMINGS[utterance_id - 1]
        transcript = "".join(plain(card) for card in marked_cards)
        chars = aligned.get("chars", [])
        aligned_text = "".join(item.get("char", "") for item in chars)
        if aligned_text != transcript:
            raise RuntimeError(f"Utterance {utterance_id} char sequence mismatch: {aligned_text!r}")

        boundaries = []
        cursor = 0
        clean_cards = [plain(card) for card in marked_cards]
        legacy_starts = legacy_proportional_starts(utterance_start, utterance_end, clean_cards)
        for card_index, marked in enumerate(marked_cards, 1):
            text = plain(marked)
            char, status = find_char(chars, cursor, cursor + len(text))
            if char is None:
                raise RuntimeError(f"Utterance {utterance_id} card {card_index} has no aligned character")
            predicted = round(float(char["start"]), 3)
            preceding = next((silence for silence in reversed(silences) if silence["end"] <= predicted), None)
            boundaries.append({
                "utteranceId": utterance_id,
                "cardIndex": card_index,
                "text": text,
                "lines": marked.split("|"),
                "transcriptCharIndex": cursor,
                "alignedFirstChar": char.get("char"),
                "predictedStart": predicted,
                "score": None if char.get("score") is None else round(float(char["score"]), 3),
                "mappingStatus": status,
                "legacyProportionalStart": round(legacy_starts[card_index - 1], 3),
                "deltaFromLegacySeconds": round(predicted - legacy_starts[card_index - 1], 3),
                "rmsDbBefore160ms": rms_db(samples, rate, predicted - 0.16, predicted),
                "rmsDbAfter160ms": rms_db(samples, rate, predicted, predicted + 0.16),
                "precedingSilenceEnd": preceding["end"] if preceding and predicted - preceding["end"] <= 1.5 else None,
                "secondsAfterSilenceEnd": round(predicted - preceding["end"], 3) if preceding and predicted - preceding["end"] <= 1.5 else None,
            })
            cursor += len(text)

        for index, card in enumerate(boundaries):
            card["subtitleStart"] = utterance_start if index == 0 else card["predictedStart"]
            card["subtitleEnd"] = utterance_end if index == len(boundaries) - 1 else boundaries[index + 1]["predictedStart"]
        if any(a["subtitleEnd"] > b["subtitleStart"] for a, b in zip(boundaries, boundaries[1:])):
            raise RuntimeError(f"Utterance {utterance_id} card boundaries overlap")
        utterances.append({
            "id": utterance_id,
            "speaker": speaker,
            "speakerLabel": "生徒" if speaker == "left" else "先生",
            "start": utterance_start,
            "end": utterance_end,
            "text": transcript,
            "alignedSpeechStart": aligned.get("start"),
            "alignedSpeechEnd": aligned.get("end"),
            "cards": boundaries,
        })

    return {
        "method": "WhisperX Japanese CTC forced alignment using supplied exact transcripts; no ASR transcript used for timing",
        "model": MODEL_ID,
        "language": "ja",
        "device": "cpu",
        "returnCharAlignments": True,
        "waveformQa": {"rmsWindowMilliseconds": 160, "silencedetectNoise": "-38dB", "silencedetectDuration": 0.25},
        "audio": portable_path(audio_path),
        "audioSha256": sha256(audio_path),
        "utterances": utterances,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=ROOT / "dialogue-new.wav")
    parser.add_argument("--utterance", type=int, choices=range(1, 17))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ids = [args.utterance] if args.utterance else list(range(1, 17))
    output = args.output or (ROOT / (f"dialogue_alignment_turn{args.utterance}.json" if args.utterance else "dialogue_alignment.json"))
    data = align_utterances(args.audio, ids)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    for utterance in data["utterances"]:
        for card in utterance["cards"]:
            print(
                f"u{utterance['id']:02d} c{card['cardIndex']}: "
                f"{card['predictedStart']:.3f}s {card['alignedFirstChar']} "
                f"score={card['score']} {card['mappingStatus']}"
            )


if __name__ == "__main__":
    main()
