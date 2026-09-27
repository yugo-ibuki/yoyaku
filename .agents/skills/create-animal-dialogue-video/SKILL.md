---
name: create-animal-dialogue-video
description: Use when creating or adapting a dialogue video whose visible speakers are animals, including variations in species, cast size, roles, scene, style, voices, subtitles, and source materials.
---

# Create Animal Dialogue Video

## Overview

Create a reproducible animal dialogue video from an explicit brief instead of inheriting the cast, layout, timing, or voices from an earlier example. Preserve the identity and composition of user-provided characters, then use the final audio as the timing source of truth.

## Define the brief

Before generating assets, resolve or leave visibly unknown these inputs:

- purpose, aspect ratio, resolution, frame rate, target duration, visual style, camera behavior
- species and number of characters; each character's identity, markings, clothing, role, screen position, and visible subtitle label
- each character's voice direction, speaking expression, mouth/beak motion, listening expression, and allowed body motion
- background, lighting, props, composition, caption-safe area, and unwanted elements
- script, pronunciation notes, final or provisional audio, subtitle rules, and any source image/video

Do not invent missing details that would materially change character identity, composition, or dialogue. Voice direction such as age, gender presentation, pitch, or texture is production metadata. The visible subtitle label must use the user-approved name or role, such as `司書` or `利用者`; never expose voice metadata as a label.

If source media is provided, retain the same character identity, markings, wardrobe, relative positions, and overall composition unless the user requests a change. Record intentional deviations.

Use [references/prompt-templates-ja.md](references/prompt-templates-ja.md) for copy-ready Japanese intake, still-image, and completed-video prompts. Fill every bracket that affects output; keep unresolved brackets explicit instead of guessing.

## Production workflow

1. Save or identify the source brief, script, reference media, and permissions. Distinguish user-provided, generated, transformed, and final files.
2. Create a character and scene specification from the brief. Use a stable character ID separate from the visible role label.
3. Generate or select the base visual. Confirm character count, identity, positions, unobstructed mouths/beaks, composition, style, aspect ratio, and subtitle-safe area before animating.
4. Produce one final audio track from the confirmed script and voice assignments. If the audio changes, invalidate all derived timing.
5. **REQUIRED SUB-SKILL:** Use `sync-dialogue-video` to establish speaker turns from actual audio, force-align confirmed text, drive subtitles and mouth motion from the verified timeline, and validate the final MP4.
6. Render expressions and mouth/beak states for each species without changing character identity. During a turn, animate only the verified speaker's speech mechanism; listeners may blink, breathe, shift gaze, or react subtly.
7. Package the final video with the exact final audio, script, character/scene specification, timing evidence, source or generation prompts, tool/model settings when known, and a provenance manifest.

Never derive timing from character count, text length, equal spacing, a requested total duration, or uniform blocks. A target duration is a planning constraint; measured final audio determines the actual timeline.

## Adapt examples safely

An existing project may demonstrate a pipeline, but its constants are not defaults. Reconfigure character count, species, positions, image assets, voice assignments, duration, script, timeline, canvas, frame rate, and validation thresholds for the current brief.

`projects/ai-introduction-videos/videos/fractal-engineering-dialogue-video/` is a two-cat, 16-turn reproduction example with project-specific assets and values. Treat its `render.py` as an example renderer, not a generic animal-video generator.

## Completion gate

Report these as separate states:

- base image selected or generated and visually checked
- final audio created and hashed
- script and speaker mapping confirmed
- alignment and low-confidence boundaries reviewed
- subtitles and mouth/beak motion rendered from the same verified turns
- final video streams, duration, handoffs, captions, and inactive listeners checked
- reproduction inputs and provenance saved

An exported file is not proof of synchronization. Do not claim publication, upload, commit, push, or replacement of source media unless that action was requested and verified.
