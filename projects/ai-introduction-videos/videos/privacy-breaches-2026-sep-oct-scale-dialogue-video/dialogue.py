from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from privacy_guard import assert_company_names_absent

LEFT = "left_student"
RIGHT = "right_teacher"

@dataclass(frozen=True)
class Turn:
    id: int
    speaker_id: str
    speaker_label: str
    cards: tuple[str, ...]
    tts_text: str
    source_ids: tuple[str, ...]

    @property
    def text(self) -> str:
        return "".join(card.replace("|", "") for card in self.cards)

SCRIPT = json.loads((Path(__file__).parent / "turns.json").read_text(encoding="utf-8"))
TURNS = tuple(Turn(item["id"], item["speakerId"], item["speakerLabel"], tuple(item["cards"]), item["ttsText"], tuple(item["sourceIds"])) for item in SCRIPT["turns"])
PRONUNCIATION_REPLACEMENTS = {item["id"]: tuple(tuple(pair) for pair in item["pronunciationReplacements"]) for item in SCRIPT["turns"]}

def display_prefix_to_tts(turn: Turn, display_prefix: str) -> tuple[str, list[dict[str, str]]]:
    converted = display_prefix
    applied = []
    for display, spoken in PRONUNCIATION_REPLACEMENTS.get(turn.id, ()):
        if display in converted:
            converted = converted.replace(display, spoken)
            applied.append({"display": display, "spoken": spoken})
    return converted, applied


def validate_script() -> None:
    assert_company_names_absent(SCRIPT, "canonical video script")
    if not TURNS or [turn.id for turn in TURNS] != list(range(1, len(TURNS) + 1)):
        raise ValueError("turn IDs must be consecutive from 1 through the canonical turn count")
    if [turn.speaker_id for turn in TURNS] != [(LEFT, RIGHT)[index % 2] for index in range(len(TURNS))]:
        raise ValueError("turns must alternate left student and right teacher")
    if any(turn.speaker_label != "" for turn in TURNS):
        raise ValueError("visible speaker labels must remain empty")
    for turn, source in zip(TURNS, SCRIPT["turns"]):
        if turn.text != source["text"]:
            raise ValueError(f"turn {turn.id} caption text differs from canonical script")
        if not turn.cards or not turn.text or not turn.tts_text:
            raise ValueError(f"turn {turn.id} is empty")
        for card in turn.cards:
            lines = card.split("|")
            if len(lines) > 2 or any(not line or len(line) > 25 for line in lines):
                raise ValueError(f"turn {turn.id} has a non-caption-safe card: {card}")
        transformed, _ = display_prefix_to_tts(turn, turn.text)
        if transformed != turn.tts_text:
            raise ValueError(f"turn {turn.id} pronunciation mapping does not reproduce tts_text")


validate_script()
