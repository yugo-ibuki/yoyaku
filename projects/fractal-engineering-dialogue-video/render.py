from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets"
OUTPUT = ROOT / "fractal-engineering-cats-aligned.mp4"
METADATA = ROOT / "dialogue_metadata.json"
ALIGNMENT = ROOT / "dialogue_alignment.json"
FONT = Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc")
FPS = 24
SIZE = (720, 1280)
TIMINGS = [
    (0.000, 4.452), (5.226, 22.143), (22.752, 28.280), (28.920, 48.190),
    (48.735, 52.744), (53.572, 73.459), (74.193, 76.810), (77.629, 87.758),
    (88.309, 90.732), (91.400, 102.008), (102.680, 106.309), (106.943, 115.330),
    (115.858, 119.996), (120.664, 139.815), (140.591, 148.516), (149.184, 157.561),
]

# The chunks are semantic subtitle units. Their exact concatenation is the supplied line.
DIALOGUE = [
    ("left", ["先生、フラクタルエンジニアリング|って、結局何をするんですか？"]),
    ("right", ["まず、一人では大きすぎる仕事を、|小さな仕事に分けます。", "その小さな仕事を任されたAIも、|必要ならさらに分ける。", "この記事では、|それがどこまでも続くと考えるんです"]),
    ("left", ["あ、先輩が私に仕事を渡して、私が|別の人に一部をお願いする感じですね"]),
    ("right", ["そのとおりです。", "どの担当者も、受け取る、|分ける、任せる、", "結果を確かめる、報告する、|という同じ手順で動きます。", "小さくしても同じ形が現れるので、|フラクタルと呼んでいます"]),
    ("left", ["でも、どこまでも分けたら、|AIが大量に動きませんか？"]),
    ("right", ["記事では、必要になった|担当者だけを動かす、としています。", "それでも費用が気になりますよね。", "そこで、最初の階層に百円、", "次に五十円、その次に二十五円、", "というように予算を減らす|話が出てきます"]),
    ("left", ["あ、ずっと足しても|二百円に近づくだけ！"]),
    ("right", ["ええ。ただし、|お金の計算が合うことと、", "無限の仕事が本当に終わることは|別です。そこがこの記事の冗談です"]),
    ("left", ["完成品の話も、冗談なんですか？"]),
    ("right", ["確認するたびに|間違いが必ず半分になるなら、", "何度も繰り返した先で|間違いはゼロになる、という話です"]),
    ("left", ["でも、確認したら新しい間違いが|見つかることもありますよね"]),
    ("right", ["まさにそこです。|都合のよい条件を置いて、", "夢のような完成品を|数学っぽく説明しているんです"]),
    ("left", ["なるほど。じゃあ、この記事から|持ち帰れることは何ですか？"]),
    ("right", ["AIがたくさんの案を|作れるようになるほど、", "どの案が正しいかを確かめることが|大切になる、", "という視点です。", "記事は最後に、|無限に仕事を分ける話を、", "AIに考える時間を使わせることへ|結び付けます"]),
    ("left", ["開発手法としてそのまま|使う話じゃなくて、笑いながら、", "検証って大事だな、|と考える記事なんですね"]),
    ("right", ["ええ。AI開発の手法に|大げさな名前や理論が", "次々と付く文化も、|楽しみながら風刺しています"]),
]


def file_sha256(path: Path) -> str:
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
        raise ValueError(f"Metadata requires project-local inputs: {resolved}")


def build_metadata(audio_path: Path, alignment_path: Path = ALIGNMENT) -> dict:
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    if alignment["audioSha256"] != file_sha256(audio_path):
        raise ValueError("Alignment audio hash does not match the render audio")
    aligned_by_id = {item["id"]: item for item in alignment["utterances"]}
    utterances = []
    for index, ((start, end), (speaker, chunks)) in enumerate(zip(TIMINGS, DIALOGUE), 1):
        aligned = aligned_by_id[index]
        expected_text = "".join(chunks).replace("|", "")
        if aligned["text"] != expected_text or aligned["speaker"] != speaker:
            raise ValueError(f"Alignment content mismatch for utterance {index}")
        if aligned["start"] != start or aligned["end"] != end:
            raise ValueError(f"Alignment bounds mismatch for utterance {index}")
        units = []
        for card in aligned["cards"]:
            units.append({
                "start": card["subtitleStart"],
                "end": card["subtitleEnd"],
                "text": card["text"],
                "lines": card["lines"],
                "alignmentEvidence": {
                    "alignedFirstChar": card["alignedFirstChar"],
                    "predictedStart": card["predictedStart"],
                    "score": card["score"],
                    "mappingStatus": card["mappingStatus"],
                },
            })
        utterances.append({
            "id": index,
            "speaker": speaker,
            "speakerLabel": "生徒" if speaker == "left" else "先生",
            "side": speaker,
            "start": start,
            "end": end,
            "text": expected_text,
            "subtitleUnits": units,
        })
    metadata = {
        "version": 1,
        "audio": portable_path(audio_path),
        "timingBasis": {
            "method": alignment["method"],
            "model": alignment["model"],
            "alignmentFile": portable_path(alignment_path),
            "silencedetect": {"noise": ["-38dB", "-42dB"], "duration": 0.25},
            "note": "Utterance bounds come from turn-gap review. Each later subtitle card starts at its first forced-aligned spoken character; the previous card remains visible until that instant.",
        },
        "video": {"width": SIZE[0], "height": SIZE[1], "fps": FPS},
        "utterances": utterances,
    }
    METADATA.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def feathered_mask(size: tuple[int, int], boxes: list[tuple[int, int, int, int]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(23))


def load_poses(source_dir: Path) -> tuple[list[Image.Image], list[Image.Image], Image.Image]:
    base_full = Image.open(source_dir / "base.png").convert("RGB")
    left_open = Image.open(source_dir / "left-speaking.png").convert("RGB")
    right_open = Image.open(source_dir / "right-speaking.png").convert("RGB")
    left_mask = feathered_mask(base_full.size, [(278, 555, 414, 698)])
    right_mask = feathered_mask(base_full.size, [(655, 570, 815, 725)])
    levels = (0.0, 0.35, 0.68, 1.0)
    left = [Image.composite(left_open, base_full, left_mask.point(lambda p, s=s: round(p * s))) for s in levels]
    right = [Image.composite(right_open, base_full, right_mask.point(lambda p, s=s: round(p * s))) for s in levels]
    # Work at delivery size after the source-space mouth composite.
    return (
        [image.resize(SIZE, Image.Resampling.LANCZOS) for image in left],
        [image.resize(SIZE, Image.Resampling.LANCZOS) for image in right],
        base_full.resize(SIZE, Image.Resampling.LANCZOS),
    )


def audio_envelope(audio_path: Path, frame_count: int) -> np.ndarray:
    with wave.open(str(audio_path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError("Audio input must be 16-bit mono PCM")
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    rms = np.zeros(frame_count, dtype=np.float32)
    half_window = round(rate * 0.035)
    for i in range(frame_count):
        center = round(i * rate / FPS)
        part = samples[max(0, center - half_window):min(len(samples), center + half_window)]
        if len(part):
            rms[i] = float(np.sqrt(np.mean(part * part)))
    # Light temporal smoothing preserves syllables while avoiding single-frame chatter.
    rms = np.convolve(rms, np.ones(3, dtype=np.float32) / 3, mode="same")
    active = rms[rms > 10 ** (-38 / 20)]
    scale = float(np.percentile(active, 88)) if len(active) else max(float(rms.max()), 1e-6)
    return np.clip(rms / max(scale, 1e-6), 0, 1)


def active_utterance(metadata: dict, time: float) -> dict | None:
    for utterance in metadata["utterances"]:
        if utterance["start"] <= time < utterance["end"]:
            return utterance
    return None


def mouth_level(utterance: dict | None, time: float, energy: float) -> int:
    if utterance is None:
        return 0
    start, end = utterance["start"], utterance["end"]
    edge = min(1.0, (time - start) / 0.10, (end - time) / 0.14)
    if edge <= 0 or energy < 0.055:
        return 0
    phase = 0.5 + 0.5 * math.sin(2 * math.pi * 3.7 * (time - start) + 0.35 * math.sin(time * 2.1))
    openness = edge * min(1.0, energy * 1.45) * (0.24 + 0.76 * phase)
    return max(0, min(3, round(openness * 3.2)))


def subtitle_at(metadata: dict, time: float) -> tuple[dict, dict] | None:
    utterance = active_utterance(metadata, time)
    if utterance is None:
        return None
    for unit in utterance["subtitleUnits"]:
        if unit["start"] <= time < unit["end"]:
            return utterance, unit
    return None


def wrap_japanese(text: str, max_chars: int = 18) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    if len(text) > max_chars * 2:
        raise ValueError(f"Subtitle card exceeds two lines: {text}")
    lower = len(text) - max_chars
    upper = max_chars
    target = len(text) / 2
    candidates = [i + 1 for i, char in enumerate(text) if char in "、。？！" and lower <= i + 1 <= upper]
    split = min(candidates, key=lambda i: abs(i - target), default=round(target))
    return [text[:split], text[split:]]


def draw_subtitle(frame: Image.Image, subtitle: tuple[dict, dict] | None, fonts: tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]) -> None:
    if subtitle is None:
        return
    utterance, unit = subtitle
    label_font, text_font = fonts
    draw = ImageDraw.Draw(frame, "RGBA")
    lines = unit.get("lines") or wrap_japanese(unit["text"])
    label = utterance["speakerLabel"]
    color = (255, 188, 104, 255) if utterance["speaker"] == "left" else (158, 218, 255, 255)
    line_h = 45
    box_h = 64 + line_h * len(lines)
    x0, x1 = 42, SIZE[0] - 42
    y0, y1 = SIZE[1] - 72 - box_h, SIZE[1] - 72
    draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=(12, 13, 18, 206), outline=(255, 255, 255, 34), width=2)
    draw.text((x0 + 28, y0 + 15), label, font=label_font, fill=color, stroke_width=1, stroke_fill=(0, 0, 0, 180))
    y = y0 + 57
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=text_font, stroke_width=2)
        width = bbox[2] - bbox[0]
        draw.text(((SIZE[0] - width) / 2, y), line, font=text_font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 230))
        y += line_h


def camera_frame(source: Image.Image, time: float, duration: float, speaker: str | None) -> Image.Image:
    # Slow breathing, slight hand-held drift, and a 4 px speaker bias retain the fixed composition.
    zoom = 1.018 + 0.009 * math.sin(2 * math.pi * time / 13.0) + 0.006 * (time / duration)
    crop_w, crop_h = round(SIZE[0] / zoom), round(SIZE[1] / zoom)
    bias = -4 if speaker == "left" else 4 if speaker == "right" else 0
    cx = SIZE[0] / 2 + bias + 2.5 * math.sin(2 * math.pi * time / 9.7)
    cy = SIZE[1] / 2 - 2.0 * math.sin(2 * math.pi * time / 4.8)
    box = (round(cx - crop_w / 2), round(cy - crop_h / 2), round(cx + crop_w / 2), round(cy + crop_h / 2))
    return source.crop(box).resize(SIZE, Image.Resampling.BILINEAR)


def render(audio_path: Path, source_dir: Path, output: Path, alignment_path: Path, font_path: Path) -> None:
    metadata = build_metadata(audio_path, alignment_path)
    with wave.open(str(audio_path), "rb") as wav:
        duration = wav.getnframes() / wav.getframerate()
        if wav.getframerate() != 24000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Expected a pcm_s16le/24000/mono WAV audio input")
    frame_count = math.ceil(duration * FPS)
    envelope = audio_envelope(audio_path, frame_count)
    left_poses, right_poses, base = load_poses(source_dir)
    fonts = (ImageFont.truetype(str(font_path), 25), ImageFont.truetype(str(font_path), 35))
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{SIZE[0]}x{SIZE[1]}", "-framerate", str(FPS), "-i", "-",
        "-i", str(audio_path), "-c:v", "libx264", "-preset", "fast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-af", "apad",
        "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for index in range(frame_count):
            time = min(index / FPS, duration)
            utterance = active_utterance(metadata, time)
            level = mouth_level(utterance, time, float(envelope[index]))
            speaker = utterance["speaker"] if utterance else None
            source = left_poses[level] if speaker == "left" else right_poses[level] if speaker == "right" else base
            frame = camera_frame(source, time, duration, speaker)
            draw_subtitle(frame, subtitle_at(metadata, time), fonts)
            fade = min(1.0, time / 0.45, (duration - time) / 0.45)
            if fade < 1:
                frame = Image.blend(Image.new("RGB", SIZE, (12, 10, 9)), frame, max(0.0, fade))
            process.stdin.write(frame.tobytes())
            if index and index % (FPS * 15) == 0:
                print(f"rendered {index / FPS:.0f}/{duration:.0f}s", flush=True)
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=ROOT / "dialogue-new.wav")
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--alignment", type=Path, default=ALIGNMENT)
    parser.add_argument("--font", type=Path, default=FONT, help="Japanese TrueType/OpenType font (defaults to macOS Hiragino)")
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    if args.metadata_only:
        build_metadata(args.audio, args.alignment)
        print(METADATA)
        return
    render(args.audio, args.source_dir, args.output, args.alignment, args.font)
    print(args.output)


if __name__ == "__main__":
    main()
