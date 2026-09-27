---
name: sync-dialogue-video
description: Use when producing or repairing narrated multi-speaker videos where subtitles, speaker handoffs, mouth movement, or regenerated audio may be out of sync.
---

# Sync Dialogue Video

## Overview

Treat the final audio as the source of truth. A valid timeline has two layers: verified speaker turns from what is actually audible, then forced-aligned subtitle boundaries from the exact confirmed script.

## Workflow

1. Hash the final audio. If it changes, invalidate every turn, subtitle, mouth-animation, metadata, and video timestamp derived from the old hash.
2. Transcribe or inspect actual speech and review the waveform around every proposed handoff. Confirm speaker identity and words before using the supplied script. Stop when speech and script differ; report observed audio separately from intended text.
3. Establish utterance turns from transcript plus waveform evidence. A silence may be a pause inside one speaker, so silence gaps alone cannot define handoffs.
4. After turns are verified, force-align the exact confirmed script within each turn. Use aligned word or character onsets for later caption cards; keep the first card from the turn start.
5. Render subtitles and mouth movement from the same verified turns. Validate every handoff, complete caption coverage without gaps/overlaps, speaker mapping/counts, low-confidence boundaries, audio hash, and the final MP4 streams and duration.

Never allocate turns or cards by character count, equal duration, or uniform 3–5 second blocks.

## Low-confidence boundaries

An unmapped character, weak score, transcript disagreement, or ambiguous waveform is a review item. Record the observed transcript, nearby silence/energy, chosen boundary, and review result. Do not silently accept or average it.

## Quick reference

| Symptom | Required response |
|---|---|
| Audio regenerated | Recompute the entire timeline from the new audio hash |
| Long pause mid-answer | Keep the turn unless transcript and voice prove a handoff |
| Caption changes early/late | Re-align its first spoken character inside the verified turn |
| Speaker or script mismatch | Stop rendering and preserve the mismatch as unknown/unresolved |

## Red flags

- “The silence detector found a gap, so the speaker changed.”
- “Text length is close enough for caption timing.”
- “Only the new audio file changed; the old JSON can stay.”
- “The MP4 exported, so synchronization is correct.”

For an executable example and its validation gate, see `projects/ai-introduction-videos/videos/fractal-engineering-dialogue-video/`. This skill does not authorize publishing, pushing, replacing source media, or other external writes.
