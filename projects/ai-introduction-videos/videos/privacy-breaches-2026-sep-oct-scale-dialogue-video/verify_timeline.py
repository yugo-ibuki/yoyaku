#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from dialogue import LEFT, RIGHT, TURNS, SCRIPT
from render import SOURCE_LABELS, VIDEO_TAGS, source_footer, validate_approval
from privacy_guard import assert_company_names_absent
from review_machine_evidence import needs_review
from numeric_overlays import PANEL, build_timeline


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent.parent / "assets" / "kotatsu-mikan"
CONFIG = ROOT / "render-config.json"
ASSET_NAMES = ("base.png", "left-speaking.png", "right-speaking.png")
EPSILON = 0.002


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= EPSILON


def require_relative(value: str, field: str) -> None:
    if not value or Path(value).is_absolute() or value.startswith("~"):
        raise ValueError(f"{field} must be a portable relative path")


def check_coverage(turn_id: int, start: float, end: float, cards: list[dict[str, Any]], start_key: str, end_key: str) -> None:
    if not cards or not close(cards[0][start_key], start) or not close(cards[-1][end_key], end):
        raise ValueError(f"turn {turn_id} subtitle coverage differs from turn bounds")
    for left, right in zip(cards, cards[1:]):
        if not close(left[end_key], right[start_key]):
            raise ValueError(f"turn {turn_id} subtitle gap or overlap")
    if any(float(card[start_key]) >= float(card[end_key]) for card in cards):
        raise ValueError(f"turn {turn_id} has an empty subtitle card")


def validate(
    audio_path: Path,
    alignment: dict[str, Any],
    metadata: dict[str, Any],
    assets_dir: Path = ASSETS,
    config_path: Path = CONFIG,
) -> dict[str, Any]:
    if metadata.get("scriptApproval") != validate_approval():
        raise ValueError("render metadata differs from approved script")
    assert_company_names_absent(alignment, "aligned captions")
    assert_company_names_absent(metadata, "render metadata")
    if metadata.get("embeddedMetadata") != VIDEO_TAGS:
        raise ValueError("embedded metadata differs from anonymous settings")
    require_relative(alignment["audio"], "alignment.audio")
    require_relative(metadata["audio"], "metadata.audio")
    require_relative(metadata["timingBasis"]["alignmentFile"], "metadata.timingBasis.alignmentFile")
    require_relative(metadata["renderConfig"]["path"], "metadata.renderConfig.path")
    if metadata.get("publicationRange") != SCRIPT["publicationRange"]:
        raise ValueError("publication range differs from canonical script")
    if metadata.get("asOf") != SCRIPT["asOf"] or metadata.get("sourceLabels") != SOURCE_LABELS:
        raise ValueError("source attribution context differs from the script")
    if metadata.get("numericPanel") != list(PANEL) or metadata.get("numericOverlays") != build_timeline(metadata.get("utterances", [])):
        raise ValueError("numeric overlay is detached from confirmed subtitle boundaries")
    audio_hash = sha256(audio_path)
    if alignment.get("audioSha256") != audio_hash or metadata.get("audioSha256") != audio_hash:
        raise ValueError("audio hash mismatch invalidates timeline")
    expected_video = {
        "width": 1280,
        "height": 720,
        "fps": 24,
        "composition": "fixed-base-with-speaker-mouth-patch",
        "subtitlePosition": "bottom",
        "visibleSpeakerLabels": False,
    }
    if metadata.get("video") != expected_video:
        raise ValueError("unexpected output video specification")
    if metadata["renderConfig"].get("sha256") != sha256(config_path):
        raise ValueError("render config hash mismatch")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("status") != "ready":
        raise ValueError("render config is not ready")
    for name in ASSET_NAMES:
        entry = metadata.get("assets", {}).get(name, {})
        require_relative(entry.get("path", ""), f"metadata.assets.{name}.path")
        actual = sha256(assets_dir / name)
        if entry.get("sha256") != actual or config.get("expectedAssets", {}).get(name) != actual:
            raise ValueError(f"asset hash mismatch for {name}")
    aligned, rendered = alignment.get("utterances", []), metadata.get("utterances", [])
    if len(aligned) != len(TURNS) or len(rendered) != len(TURNS):
        raise ValueError(f"timeline must contain all {len(TURNS)} turns")
    previous_end, cards_total, counts = 0.0, 0, Counter()
    for expected, source, output in zip(TURNS, aligned, rendered):
        identity = (expected.id, expected.speaker_id, "", expected.text)
        if (source.get("id"), source.get("speakerId"), source.get("speakerLabel"), source.get("text")) != identity:
            raise ValueError(f"turn {expected.id} alignment differs from script")
        if (output.get("id"), output.get("speakerId"), output.get("speakerLabel"), output.get("text")) != identity:
            raise ValueError(f"turn {expected.id} render metadata differs from script")
        if output.get("sourceIds") != list(expected.source_ids) or output.get("sourceAttribution") != source_footer(expected.id):
            raise ValueError(f"turn {expected.id} source attribution differs from script")
        start, end = float(source["start"]), float(source["end"])
        if start < previous_end - EPSILON or start >= end:
            raise ValueError(f"turn {expected.id} bounds overlap or reverse")
        if not close(output["start"], start) or not close(output["end"], end):
            raise ValueError(f"turn {expected.id} rendered bounds mismatch")
        motion = output.get("mouthMotion", {})
        wanted_asset = "left-speaking.png" if expected.speaker_id == LEFT else "right-speaking.png"
        if motion.get("speakingAsset") != wanted_asset or motion.get("listenerMouthMotion") is not False:
            raise ValueError(f"turn {expected.id} mouth motion violates speaker-only compositing")
        if motion.get("method") != "speaker-only masked mouth patch gated by local RMS":
            raise ValueError(f"turn {expected.id} does not use RMS-gated mouth compositing")
        cards, units = source.get("cards", []), output.get("subtitleUnits", [])
        expected_cards = [card.replace("|", "") for card in expected.cards]
        if [card.get("text") for card in cards] != expected_cards or [unit.get("text") for unit in units] != expected_cards:
            raise ValueError(f"turn {expected.id} cards differ from script")
        if any(len(unit.get("lines", [])) > 2 for unit in units):
            raise ValueError(f"turn {expected.id} subtitle exceeds two lines")
        check_coverage(expected.id, start, end, cards, "subtitleStart", "subtitleEnd")
        check_coverage(expected.id, start, end, units, "start", "end")
        for index, (card, unit) in enumerate(zip(cards, units)):
            if not close(unit["start"], start if index == 0 else card["predictedStart"]):
                raise ValueError(f"turn {expected.id} subtitle detached from alignment")
            low_confidence = needs_review(card, index)
            review = card.get("manualReview", {})
            if low_confidence and (review.get("status") != "reviewed" or not review.get("evidence")):
                raise ValueError(f"turn {expected.id} has an unreviewed low-confidence boundary")
        previous_end, cards_total = end, cards_total + len(cards)
        counts[expected.speaker_id] += 1
    with wave.open(str(audio_path), "rb") as audio:
        if audio.getcomptype() != "NONE" or audio.getsampwidth() != 2 or audio.getnchannels() != 1:
            raise ValueError("audio must be mono uncompressed 16-bit PCM WAV")
        duration = audio.getnframes() / audio.getframerate()
    if previous_end > duration + EPSILON or counts != Counter(turn.speaker_id for turn in TURNS):
        raise ValueError("final bounds or speaker counts are invalid")
    return {
        "turns": len(TURNS),
        "cards": cards_total,
        "speakers": dict(counts),
        "audioSha256": audio_hash,
        "audioDuration": duration,
    }


def probe_video(path: Path, expected_duration: float) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:format_tags:stream=codec_name,codec_type,width,height,r_frame_rate:stream_tags",
        "-of", "json", str(path),
    ]
    data = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
    assert_company_names_absent(data, "MP4 embedded metadata")
    for key, value in VIDEO_TAGS.items():
        if data["format"].get("tags", {}).get(key) != value:
            raise ValueError(f"MP4 embedded {key} differs from anonymous settings")
    streams = {item["codec_type"]: item for item in data["streams"]}
    video, audio = streams.get("video", {}), streams.get("audio", {})
    duration = float(data["format"]["duration"])
    limit = SCRIPT.get("durationPolicy", {}).get("targetMaximumSeconds")
    if limit is not None and duration > float(limit):
        raise ValueError("MP4 exceeds canonical duration limit")
    if (video.get("codec_name"), video.get("width"), video.get("height"), video.get("r_frame_rate")) != ("h264", 1280, 720, "24/1"):
        raise ValueError("video must be H.264 1280x720 at 24fps")
    if audio.get("codec_name") != "aac" or abs(duration - expected_duration) > 1 / 24 + 0.01:
        raise ValueError("video audio codec or duration mismatch")
    return {"duration": duration, "video": "h264", "audio": "aac", "size": "1280x720", "fps": 24}


def extract_and_compare_audio(video_path: Path, reference_path: Path, extracted_path: Path) -> dict[str, Any]:
    """Decode the rendered AAC track and compare it with the adopted PCM source."""
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path), "-vn",
            "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(extracted_path),
        ],
        check=True,
    )

    def read_pcm(path: Path) -> tuple[int, np.ndarray]:
        with wave.open(str(path), "rb") as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                raise ValueError(f"comparison PCM must be mono 16-bit: {path}")
            rate = stream.getframerate()
            values = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float64)
        return rate, values / 32768.0

    reference_rate, reference = read_pcm(reference_path)
    extracted_rate, extracted = read_pcm(extracted_path)
    if reference_rate != 24000 or extracted_rate != reference_rate:
        raise ValueError("audio comparison requires matching 24 kHz PCM")

    # Search the first 30 seconds at 1 kHz. This resolves AAC priming/start shift
    # without treating a lossy decode as byte-identical to the source WAV.
    decimation = 24
    reference_probe = reference[: reference_rate * 30 : decimation]
    extracted_probe = extracted[: extracted_rate * 30 : decimation]
    maximum_lag = round(0.25 * reference_rate / decimation)
    best_lag, best_score = 0, -1.0
    for lag in range(-maximum_lag, maximum_lag + 1):
        if lag >= 0:
            left, right = reference_probe[: len(extracted_probe) - lag], extracted_probe[lag:]
        else:
            left, right = reference_probe[-lag:], extracted_probe[: len(reference_probe) + lag]
        if len(left) < 1000:
            continue
        left, right = left - left.mean(), right - right.mean()
        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        score = float(np.dot(left, right) / denominator) if denominator else -1.0
        if score > best_score:
            best_lag, best_score = lag, score

    lag_samples = best_lag * decimation
    if lag_samples >= 0:
        reference_aligned, extracted_aligned = reference[: len(extracted) - lag_samples], extracted[lag_samples:]
    else:
        reference_aligned, extracted_aligned = reference[-lag_samples:], extracted[: len(reference) + lag_samples]
    length = min(len(reference_aligned), len(extracted_aligned))
    reference_aligned, extracted_aligned = reference_aligned[:length], extracted_aligned[:length]
    reference_aligned -= reference_aligned.mean()
    extracted_aligned -= extracted_aligned.mean()
    denominator = float(np.linalg.norm(reference_aligned) * np.linalg.norm(extracted_aligned))
    waveform_correlation = float(np.dot(reference_aligned, extracted_aligned) / denominator) if denominator else -1.0
    reference_duration = len(reference) / reference_rate
    extracted_duration = len(extracted) / extracted_rate
    result = {
        "referenceSha256": sha256(reference_path),
        "extractedPcm": str(extracted_path.relative_to(ROOT)),
        "extractedPcmSha256": sha256(extracted_path),
        "sampleRate": reference_rate,
        "referenceDuration": round(reference_duration, 6),
        "extractedDuration": round(extracted_duration, 6),
        "durationDifference": round(extracted_duration - reference_duration, 6),
        "startOffsetSeconds": round(lag_samples / reference_rate, 6),
        "probeCorrelation": round(best_score, 8),
        "waveformCorrelation": round(waveform_correlation, 8),
    }
    if abs(result["durationDifference"]) > 1 / 24 + 0.02:
        raise ValueError(f"extracted audio duration mismatch: {result}")
    if abs(result["startOffsetSeconds"]) > 0.05:
        raise ValueError(f"rendered audio start shift is too large: {result}")
    if result["waveformCorrelation"] < 0.99:
        raise ValueError(f"rendered audio waveform correlation is too low: {result}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the final personal-data-breach cat-video timeline.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--alignment", type=Path, default=ROOT / "dialogue_alignment.json")
    parser.add_argument("--metadata", type=Path, default=ROOT / "dialogue_metadata.json")
    parser.add_argument("--video", type=Path, default=ROOT / "privacy-breaches-2026-sep-oct-scale-cats.mp4")
    parser.add_argument("--assets", type=Path, default=ASSETS)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--extracted-audio", type=Path, default=ROOT / "audio" / "verification-from-mp4.wav")
    parser.add_argument("--audio-verification", type=Path, default=ROOT / "audio" / "mp4-audio-verification.json")
    parser.add_argument("--skip-video", action="store_true")
    args = parser.parse_args()
    result = validate(
        args.audio,
        json.loads(args.alignment.read_text(encoding="utf-8")),
        json.loads(args.metadata.read_text(encoding="utf-8")),
        args.assets,
        args.config,
    )
    if not args.skip_video:
        result["video"] = probe_video(args.video, result["audioDuration"])
        result["renderedAudio"] = extract_and_compare_audio(args.video, args.audio, args.extracted_audio)
        args.audio_verification.write_text(
            json.dumps(result["renderedAudio"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
