# こたつとみかんの発話画像生成記録

2026-11-01 に Codex 組み込み `image_gen` で生成しました。両方とも、採用済みの `base-sample.png` のみを編集対象にしています。`base.png` は採用済み画像のバイト不変コピーです。

## left-speaking.png

```text
Use case: precise-object-edit
Asset type: LEFT-speaking variant for a reusable two-cat dialogue-video scene.
Edit target: the supplied kotatsu image ONLY. Preserve this image as exactly as possible. Make ONE localized edit: open the mouth of the ORANGE TABBY CAT ON THE LEFT in a clear, restrained, natural feline speaking/meow pose. Gently lower its jaw just enough to show the dark mouth opening and a little tongue; this should read as calmly speaking, not yawning, shouting, smiling like a human, or baring teeth. Preserve its muzzle identity and head position.
The SILVER-GRAY TABBY CAT ON THE RIGHT must remain exactly as in the source, listening with its mouth fully CLOSED. Both cats' eyes remain open. Do not move either cat's head, eyes, ears, whiskers, body or paws except the minimum left jaw adjustment needed for speech.
Lock composition and all other pixels as closely as possible: same 1672x941 landscape framing, scale, camera, natural photorealistic fur and markings, orange-left/gray-right identities, warm lighting, tatami, shoji, background, kotatsu tabletop, red patterned blanket and its folds, basket and individual mikan, exactly two cups and coasters, paws and their positions.
No added objects, text, logo, watermark, people, animals, clothing, human teeth/hands, anatomy changes, reframing, cropping, camera movement, lighting shift or background redesign. Only the LEFT ORANGE cat's mouth is open.
```

## right-speaking.png

```text
Use case: precise-object-edit
Asset type: RIGHT-speaking variant for a reusable two-cat dialogue-video scene.
Edit target: the supplied CLOSED-MOUTH kotatsu BASE image ONLY. Preserve this image as exactly as possible. Make ONE localized edit: open the mouth of the SILVER-GRAY TABBY CAT ON THE RIGHT in a clear, restrained, natural feline speaking/meow pose. Gently lower its jaw just enough to show the dark mouth opening and a little tongue; this should read as calmly speaking, not yawning, shouting, smiling like a human, or baring teeth. Preserve its muzzle identity and head position.
The ORANGE TABBY CAT ON THE LEFT must remain exactly as in the source, listening with its mouth fully CLOSED. Both cats' eyes remain open. Do not move either cat's head, eyes, ears, whiskers, body or paws except the minimum right jaw adjustment needed for speech.
Lock composition and all other pixels as closely as possible: same 1672x941 landscape framing, scale, camera, natural photorealistic fur and markings, orange-left/gray-right identities, warm lighting, tatami, shoji, background, kotatsu tabletop, red patterned blanket and its folds, basket and individual mikan, exactly two cups and coasters, paws and their positions.
No added objects, text, logo, watermark, people, animals, clothing, human teeth/hands, anatomy changes, reframing, cropping, camera movement, lighting shift or background redesign. Only the RIGHT GRAY cat's mouth is open.
```
