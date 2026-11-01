#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from dialogue import LEFT, RIGHT, TURNS, SCRIPT
from privacy_guard import assert_company_names_absent
from numeric_overlays import PANEL, STATES, build_timeline, draw_hero, overlay_at


ROOT = Path(__file__).resolve().parent
SIZE = (1280, 720)
FPS = 24
DEFAULT_ASSETS = ROOT.parent.parent / "assets" / "kotatsu-mikan"
DEFAULT_CONFIG = ROOT / "render-config.json"
DEFAULT_FONT = Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc")
DEFAULT_OUTPUT = ROOT / "privacy-breaches-2026-sep-oct-scale-cats.mp4"
ASSET_NAMES = ("base.png", "left-speaking.png", "right-speaking.png")


SOURCE_LABELS = {
    "L9":"公表一覧 2026-09", "L10":"公表一覧 2026-10",
    "A":"事例A 2026-10-26", "B":"事例B 2026-10-15", "C":"事例C 2026-10-09",
    "MATH":"件数の算術比較", "CAA":"消費者庁 対策資料",
}
VIDEO_TAGS = {
    "title": SCRIPT["title"],
    "comment": "企業・サービス・自治体名なし版・公表期間 " + SCRIPT["publicationRange"]["from"] + "–" + SCRIPT["publicationRange"]["through"] + "・確認時点 " + SCRIPT["asOf"],
}
assert_company_names_absent(SOURCE_LABELS, "source footer labels")
assert_company_names_absent(STATES, "numeric panel states")
assert_company_names_absent(VIDEO_TAGS, "embedded video metadata")


def source_footer(turn_id: int) -> str:
    turn = next(turn for turn in TURNS if turn.id == turn_id)
    return ("出典：" + " ／ ".join(SOURCE_LABELS[source] for source in turn.source_ids)) if turn.source_ids else ""


def draw_context(frame: Image.Image, turn_id: int | None, font_path: Path = DEFAULT_FONT) -> None:
    draw = ImageDraw.Draw(frame, "RGBA")
    font = ImageFont.truetype(str(font_path), 18)
    as_of = SCRIPT["asOf"] + "時点"
    box = draw.textbbox((0, 0), as_of, font=font)
    draw.text((SIZE[0] - 24 - box[2], 17), as_of, font=font, fill="white", stroke_width=2, stroke_fill=(0, 0, 0, 220))
    period = SCRIPT["publicationRange"]
    draw.text((24, 17), "公表期間 " + period["from"] + "～" + period["through"], font=font, fill="white", stroke_width=2, stroke_fill=(0, 0, 0, 220))
    if turn_id is not None:
        footer = source_footer(turn_id)
        if not footer:
            return
        if draw.textlength(footer, font=font) > SIZE[0] - 48:
            raise ValueError("source footer exceeds the safe width")
        draw.rectangle((0, 680, SIZE[0], SIZE[1]), fill=(8, 15, 27, 210))
        draw.text((24, 687), footer, font=font, fill="white")


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
        raise ValueError(f"metadata input must be inside the project: {path}") from exc


def asset_reference(name: str) -> str:
    return Path("../../assets/kotatsu-mikan").joinpath(name).as_posix()


def load_render_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("version") != 1:
        raise ValueError("render config version must remain 1 for this unreleased project")
    if config.get("status") != "ready":
        raise ValueError("render config is not ready; speaking images and measured mouth regions are required")
    if config.get("sourceSize") != [1672, 941]:
        raise ValueError("render config sourceSize must match the adopted 1672x941 image")
    for speaker in (LEFT, RIGHT):
        region = config.get("mouthRegions", {}).get(speaker)
        if not isinstance(region, dict) or region.get("shape") != "ellipse":
            raise ValueError(f"{speaker} mouth region must be a measured ellipse")
        box = region.get("box")
        if not isinstance(box, list) or len(box) != 4 or not all(isinstance(value, int) for value in box):
            raise ValueError(f"{speaker} mouth box must contain four source-pixel integers")
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= 1672 and 0 <= y0 < y1 <= 941):
            raise ValueError(f"{speaker} mouth box is outside the source image")
    threshold = float(config.get("openThresholdDbfs", -999))
    window = float(config.get("rmsWindowSeconds", 0))
    if not -80 <= threshold <= -10 or not 0.02 <= window <= 0.12:
        raise ValueError("RMS mouth settings are outside reviewed bounds")
    return config


def load_assets(source_dir: Path, config: dict[str, Any]) -> dict[str, Image.Image]:
    images = {name: Image.open(source_dir / name).convert("RGB") for name in ASSET_NAMES}
    if {image.size for image in images.values()} != {(1672, 941)}:
        raise ValueError("all kotatsu images must be 1672x941")
    expected = config.get("expectedAssets", {})
    for name in ASSET_NAMES:
        wanted = expected.get(name)
        if not isinstance(wanted, str) or len(wanted) != 64:
            raise ValueError(f"expected SHA-256 is not recorded for {name}")
        if sha256(source_dir / name) != wanted:
            raise ValueError(f"asset hash mismatch for {name}")
    return {name: image.resize(SIZE, Image.Resampling.LANCZOS) for name, image in images.items()}


def scaled_box(box: list[int]) -> tuple[int, int, int, int]:
    sx, sy = SIZE[0] / 1672, SIZE[1] / 941
    return (
        round(box[0] * sx),
        round(box[1] * sy),
        round(box[2] * sx),
        round(box[3] * sy),
    )


def compose_open_mouth(base: Image.Image, speaking: Image.Image, region: dict[str, Any]) -> Image.Image:
    box = scaled_box(region["box"])
    mask = Image.new("L", SIZE, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    feather = max(1, round(float(region.get("featherPx", 6)) * SIZE[0] / 1672))
    mask = mask.filter(ImageFilter.GaussianBlur(feather))
    result = base.copy()
    result.paste(speaking, (0, 0), mask)
    return result


def prepare_frames(source_dir: Path, config: dict[str, Any]) -> dict[str, Image.Image]:
    assets = load_assets(source_dir, config)
    base = assets["base.png"]
    return {
        "base": base,
        LEFT: compose_open_mouth(base, assets["left-speaking.png"], config["mouthRegions"][LEFT]),
        RIGHT: compose_open_mouth(base, assets["right-speaking.png"], config["mouthRegions"][RIGHT]),
    }


def load_pcm(audio_path: Path) -> tuple[np.ndarray, int, float]:
    with wave.open(str(audio_path), "rb") as audio:
        if audio.getcomptype() != "NONE" or audio.getsampwidth() != 2 or audio.getnchannels() != 1:
            raise ValueError("render audio must be mono uncompressed 16-bit PCM WAV")
        rate = audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return samples, rate, len(samples) / rate


def rms_dbfs(samples: np.ndarray, rate: int, time: float, window_seconds: float) -> float:
    half = max(1, round(window_seconds * rate / 2))
    center = round(time * rate)
    part = samples[max(0, center - half):min(len(samples), center + half)]
    if not len(part):
        return -180.0
    rms = math.sqrt(float(np.mean(part * part)))
    return 20 * math.log10(max(rms, 1e-9))


def peak_mouth_evidence(samples: np.ndarray, rate: int, start: float, end: float, window: float) -> tuple[float, float]:
    times = np.arange(start, end, 1 / FPS)
    if not len(times):
        raise ValueError("empty turn cannot produce mouth evidence")
    values = [rms_dbfs(samples, rate, float(time), window) for time in times]
    index = int(np.argmax(values))
    return round(float(times[index]), 3), round(float(values[index]), 2)


def validate_approval(path: Path = ROOT / "script-approval.json") -> dict[str, Any]:
    approval = json.loads(path.read_text(encoding="utf-8"))
    if approval.get("approved") is not True:
        raise ValueError("current script is not user-approved")
    if approval.get("canonicalScriptSha256") != sha256(ROOT / "turns.json"):
        raise ValueError("approved script hash mismatch")
    if approval.get("reviewDocumentSha256") != sha256(ROOT / approval["reviewDocument"]):
        raise ValueError("approved review snapshot hash mismatch")
    return {"approved":True,"scriptSha256":approval["canonicalScriptSha256"],"reviewSha256":approval["reviewDocumentSha256"]}


def build_metadata(audio_path: Path, alignment_path: Path, source_dir: Path, config_path: Path) -> dict[str, Any]:
    approval = validate_approval()
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    audio_hash = sha256(audio_path)
    if alignment.get("audioSha256") != audio_hash:
        raise ValueError("audio hash mismatch: alignment does not match render audio")
    if len(alignment.get("utterances", [])) != len(TURNS):
        raise ValueError(f"alignment must contain all {len(TURNS)} turns")
    config = load_render_config(config_path)
    load_assets(source_dir, config)
    samples, rate, duration = load_pcm(audio_path)
    limit = SCRIPT.get("durationPolicy", {}).get("targetMaximumSeconds")
    if limit is not None and duration > float(limit):
        raise ValueError("adopted audio exceeds canonical duration limit")
    utterances = []
    for expected, aligned in zip(TURNS, alignment["utterances"]):
        identity = (expected.id, expected.speaker_id, expected.speaker_label, expected.text)
        if (aligned.get("id"), aligned.get("speakerId"), aligned.get("speakerLabel"), aligned.get("text")) != identity:
            raise ValueError(f"turn {expected.id} alignment differs from the confirmed script")
        cards = aligned.get("cards", [])
        if [card.get("text") for card in cards] != [card.replace("|", "") for card in expected.cards]:
            raise ValueError(f"turn {expected.id} subtitle cards differ from the confirmed script")
        peak_time, peak_dbfs = peak_mouth_evidence(
            samples,
            rate,
            float(aligned["start"]),
            float(aligned["end"]),
            float(config["rmsWindowSeconds"]),
        )
        if peak_dbfs < float(config["openThresholdDbfs"]):
            raise ValueError(f"turn {expected.id} never exceeds the configured mouth-open RMS threshold")
        utterances.append({
            "id": expected.id,
            "speakerId": expected.speaker_id,
            "speakerLabel": "",
            "start": aligned["start"],
            "end": aligned["end"],
            "text": expected.text,
            "sourceIds": list(expected.source_ids),
            "sourceAttribution": source_footer(expected.id),
            "mouthMotion": {
                "method": "speaker-only masked mouth patch gated by local RMS",
                "speakingAsset": "left-speaking.png" if expected.speaker_id == LEFT else "right-speaking.png",
                "listenerMouthMotion": False,
                "openThresholdDbfs": config["openThresholdDbfs"],
                "rmsWindowSeconds": config["rmsWindowSeconds"],
                "peakTime": peak_time,
                "peakDbfs": peak_dbfs,
            },
            "subtitleUnits": [{
                "start": card["subtitleStart"],
                "end": card["subtitleEnd"],
                "text": card["text"],
                "lines": card["lines"],
                "alignmentEvidence": {
                    "predictedStart": card["predictedStart"],
                    "alignedFirstChar": card.get("alignedFirstChar"),
                    "score": card.get("score"),
                    "mappingStatus": card.get("mappingStatus"),
                    "pronunciationMapping": card.get("pronunciationMapping"),
                },
            } for card in cards],
        })
    assets = {
        name: {"path": asset_reference(name), "sha256": sha256(source_dir / name)}
        for name in ASSET_NAMES
    }
    metadata = {
        "version": 1,
        "audio": relative_to_root(audio_path),
        "audioSha256": audio_hash,
        "audioDuration": duration,
        "scriptApproval": approval,
        "timingBasis": {"alignmentFile": relative_to_root(alignment_path), "method": alignment.get("method")},
        "video": {
            "width": SIZE[0],
            "height": SIZE[1],
            "fps": FPS,
            "composition": "fixed-base-with-speaker-mouth-patch",
            "subtitlePosition": "bottom",
            "visibleSpeakerLabels": False,
        },
        "renderConfig": {"path": relative_to_root(config_path), "sha256": sha256(config_path)},
        "asOf": SCRIPT["asOf"],
        "publicationRange": SCRIPT["publicationRange"],
        "sourceLabels": SOURCE_LABELS,
        "embeddedMetadata": VIDEO_TAGS,
        "numericPanel": list(PANEL),
        "numericOverlays": build_timeline(utterances),
        "assets": assets,
        "utterances": utterances,
    }
    assert_company_names_absent(metadata, "render metadata")
    return metadata


def active_turn(metadata: dict[str, Any], time: float) -> dict[str, Any] | None:
    return next((turn for turn in metadata["utterances"] if turn["start"] <= time < turn["end"]), None)


def subtitle_at(metadata: dict[str, Any], time: float) -> tuple[dict[str, Any], dict[str, Any]] | None:
    turn = active_turn(metadata, time)
    if turn is None:
        return None
    unit = next((item for item in turn["subtitleUnits"] if item["start"] <= time < item["end"]), None)
    return (turn, unit) if unit else None


def speaker_color(speaker_id: str) -> tuple[int, int, int, int]:
    return (255, 174, 84, 255) if speaker_id == LEFT else (159, 211, 255, 255)


def draw_subtitle(frame: Image.Image, subtitle: tuple[dict[str, Any], dict[str, Any]] | None, font: Any) -> None:
    if subtitle is None:
        return
    turn, unit = subtitle
    if turn.get("speakerLabel"):
        raise ValueError("visible speaker labels are forbidden for this video")
    lines = unit["lines"]
    if len(lines) > 2:
        raise ValueError("subtitle cards may contain at most two lines")
    draw = ImageDraw.Draw(frame, "RGBA")
    box_h = 16 + 40 * len(lines)
    x0, x1, y1 = 110, SIZE[0] - 110, SIZE[1] - 52
    y0 = y1 - box_h
    color = speaker_color(turn["speakerId"])
    draw.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=(8, 15, 27, 218), outline=None)
    y = y0 + 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        draw.text(
            ((SIZE[0] - (bbox[2] - bbox[0])) / 2, y),
            line,
            font=font,
            fill="white",
            stroke_width=3,
            stroke_fill=(0, 0, 0, 230),
        )
        y += 40


def validate_subtitle_width(font_path: Path, max_width: int = 980) -> dict[str, Any]:
    font = ImageFont.truetype(str(font_path), 30)
    draw = ImageDraw.Draw(Image.new("RGB", SIZE))
    widest = {"width": 0, "turn": None, "text": ""}
    for turn in TURNS:
        for card in turn.cards:
            lines = card.split("|")
            if len(lines) > 2:
                raise ValueError(f"turn {turn.id} subtitle card exceeds two lines")
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font, stroke_width=3)
                width = bbox[2] - bbox[0]
                if width > widest["width"]:
                    widest = {"width": width, "turn": turn.id, "text": line}
                if width > max_width:
                    raise ValueError(f"turn {turn.id} subtitle line exceeds {max_width}px: {line}")
    return widest


def render(
    audio_path: Path,
    alignment_path: Path,
    source_dir: Path,
    config_path: Path,
    output: Path,
    metadata_path: Path,
    font_path: Path,
) -> None:
    metadata = build_metadata(audio_path, alignment_path, source_dir, config_path)
    from verify_timeline import validate
    validate(audio_path, json.loads(alignment_path.read_text(encoding="utf-8")), metadata, source_dir, config_path)
    validate_subtitle_width(font_path)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    config = load_render_config(config_path)
    frames = prepare_frames(source_dir, config)
    samples, rate, duration = load_pcm(audio_path)
    font = ImageFont.truetype(str(font_path), 30)
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", "1280x720", "-framerate", str(FPS), "-i", "-", "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-map_metadata", "-1", "-metadata", "title=" + VIDEO_TAGS["title"], "-metadata", "comment=" + VIDEO_TAGS["comment"],
        "-c:a", "aac", "-b:a", "160k", "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for index in range(math.ceil(duration * FPS)):
            time = min(index / FPS, duration)
            turn = active_turn(metadata, time)
            frame_key = "base"
            if turn is not None:
                level = rms_dbfs(samples, rate, time, float(config["rmsWindowSeconds"]))
                if level >= float(config["openThresholdDbfs"]):
                    frame_key = turn["speakerId"]
            frame = frames[frame_key].copy()
            draw_hero(frame, overlay_at(metadata, time), font_path)
            draw_subtitle(frame, subtitle_at(metadata, time), font)
            draw_context(frame, None if turn is None else turn["id"], font_path)
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg render failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the verified personal-data-breach cat dialogue.")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--alignment", type=Path, default=ROOT / "dialogue_alignment.json")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=ROOT / "dialogue_metadata.json")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    if args.metadata_only:
        args.metadata.write_text(
            json.dumps(build_metadata(args.audio, args.alignment, args.source_dir, args.config), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        render(args.audio, args.alignment, args.source_dir, args.config, args.output, args.metadata, args.font)
    print(args.metadata if args.metadata_only else args.output)


if __name__ == "__main__":
    main()
