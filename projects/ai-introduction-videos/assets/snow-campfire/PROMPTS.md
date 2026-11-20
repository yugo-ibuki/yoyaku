# Snow Campfire 画像生成プロンプト

2026-09-27 に Codex の組み込み `image_gen` で使用した最終プロンプトです。`base.png` はユーザー提供写真を横長 16:9 の構図参照、制作時の `projects/fractal-engineering-dialogue-video/assets/base.png` を猫の識別参照、直前の雪中画像を衣装と雰囲気だけの参照として生成しました。制作時の識別参照と同一バイトの現在の共通保存版は [`../outdoor-cafe/base.png`](../outdoor-cafe/base.png) です。左右の発話画像は新しい `base.png` だけを編集対象にしました。

## base.png

```text
Use case: identity-preserve
Asset type: horizontal dialogue-video scene base image
Input images: Image 1 is the primary COMPOSITION reference only. Match its horizontal wide shot: two separate folding camp chairs left and right, subjects seated well apart, a modest campfire centered in the near foreground, flat open snow behind them, and all chairs and subjects fully visible. Do not copy the people, human faces, human anatomy, masks, or their clothing. Image 2 is the CAT IDENTITY reference only: orange tabby student on the LEFT and silver-gray tabby teacher on the RIGHT. Image 3 is the WINTER CLOTHING/ATMOSPHERE reference only: snow-covered cat-shaped hoods, teal and burgundy pet coats, blizzard, white breath, and firelight. Do not copy Image 3's vertical framing, giant fire, or cats sitting on the ground.
Primary request: Create a photorealistic HORIZONTAL 16:9 wide image that translates Image 1's spatial layout into a natural two-cat scene. Put one black folding outdoor camp chair on the left and a separate matching chair on the right. Put the orange cat on the LEFT chair and gray cat on the RIGHT chair. Place a modest low campfire centered in the near foreground, clearly smaller than either cat-and-chair group, matching the fire-to-subject scale of Image 1.
Cats and chairs: each cat is fully visible in a natural feline loaf or compact cat-sitting pose entirely ON the chair seat. All forepaws, hind paws, haunches, and tail stay on the seat; no leg or paw hangs down. Chairs remain recognizable and fully visible, including fabric seats, backs, and crossed metal legs. Cats face the camera in a three-quarter frontal angle and glance toward each other across the fire. Both mouths are fully closed in this neutral pause image; neither cat is eating.
Clothing and cold: both wear four-legged-pet puffer coats with hoods fully raised, dark teal on orange and deep burgundy on gray. Hoods follow natural cat skull and ear shapes while leaving faces and mouths visible. Add snow on hoods/coats, frosty fur, slightly narrowed cold eyes, soft white breath, and a huddled enduring-the-blizzard feeling.
Marshmallows: on each chair seat directly in front of that cat's paws, place exactly one small shallow dark heatproof saucer resting flat and visibly supported by the chair seat. Each saucer contains exactly two bite-size toasted marshmallow pieces resting flat. In this base image the cats are not touching the food.
Scene: simple open snowy campsite with a low snowbank or gentle snowy hill, sparse distant winter trees, and subdued overcast background. Do not let a dramatic mountain, forest, or huge fire dominate.
Composition/framing: exact 16:9 landscape orientation; pulled-back eye-level frontal shot; full cats and full chairs visible; chairs well separated; modest fire centered foreground; preserve clear negative snow space along the lower edge for subtitles.
Constraints: exactly two cats, two chairs, two saucers, four marshmallow pieces, one modest campfire; natural feline anatomy; no human posture; no paws hanging like legs; no human hands, fingers, arms, pants, shoes, sleeves reshaping forelegs, held objects, floating food, skewers, sticks, utensils, extra props, people, text, logos, watermark, speech bubbles, extra animals, duplicate limbs, or deformed paws.
```

## left-speaking.png

```text
Use case: precise-object-edit
Asset type: horizontal dialogue-video speaking-pose variant
Primary request: Preserve the supplied image almost exactly. Make only the ORANGE TABBY CAT ON THE LEFT speak with its head raised and mouth clearly open in a restrained feline meow. The SILVER-GRAY CAT ON THE RIGHT listens while eating: lower the gray cat's whole muzzle close to the right saucer and extend only the tip of its tongue downward until it touches the top surface of the nearest toasted marshmallow.
Critical food physics: exactly two toasted marshmallow pieces remain lying flat inside each saucer. The right cat does not lift, bite up, hold, carry, or raise a marshmallow. There must be no marshmallow between the saucer and the cat's mouth. The contacted marshmallow's entire bottom remains visibly seated against the saucer, with contact shadow. Move the gray cat's head down to the food; do not move food up to its mouth.
Composition invariants: horizontal 16:9; two complete black folding chairs well separated left and right; each cat's entire natural quadruped body, paws, haunches, and tail remain on its own chair seat; modest campfire centered in the near foreground and smaller than the cat-and-chair groups; pulled-back frontal camera; flat open snowy campsite and low background.
Prop invariants: one small dark saucer lies flat on each chair seat directly before the paws, exactly two bite-size toasted marshmallow pieces lie flat inside each saucer. Keep chair legs, saucers, fire, logs, and snow positions as close to the input as possible.
Appearance invariants: orange-left/gray-right identities; natural feline anatomy; snow-covered raised cat-shaped hoods; teal and burgundy pet puffer coats; frosty fur; narrowed cold eyes; visible white breath; blizzard; lighting and colors.
Constraints: only orange left has a speaking-open mouth and no food near its mouth. Gray right mouth stays mostly closed except the small downward tongue touching food on the plate. No floating, suspended, stacked, lifted, held, or airborne food. No human hands, fingers, arms, gestures, dangling legs, human posture, skewers, sticks, utensils, extra dishes, extra food, people, text, logo, watermark, speech bubble, extra animals, duplicate limbs, or anatomy changes.
```

## right-speaking.png

```text
Use case: precise-object-edit
Asset type: horizontal dialogue-video speaking-pose variant
Primary request: Preserve the supplied image almost exactly. Raise only the SILVER-GRAY CAT ON THE RIGHT's face and give it one clear open feline speaking mouth. Lower the ORANGE TABBY CAT ON THE LEFT's face all the way to its left saucer so its nose is almost at the saucer rim and its tongue touches a toasted marshmallow that is still lying inside the saucer.
Nonnegotiable food placement: show no food at the orange cat's mouth and no food in the vertical space between mouth and saucer. Do not put a marshmallow under the tongue above the plate. Both marshmallows on the left remain low, lying flat, and visibly in contact with the bottom of the left saucer. The orange cat reaches down to them. Both marshmallows on the right also remain lying flat inside the right saucer. No piece is lifted, stacked, held, bitten up, suspended, or airborne.
Keep unchanged: horizontal 16:9 wide framing; complete separated black folding chairs; orange cat on left chair and gray cat on right chair; all paws, bodies, and tails on chair seats; saucers flat on seats; modest campfire centered in near foreground; flat snowy campsite; snow-covered teal and burgundy raised pet-coat hoods; blizzard, white breath, natural feline anatomy, lighting, and colors.
Constraints: only gray right cat speaks and has an open mouth; no food near gray mouth. Orange left cat listens, head fully lowered, tongue reaching down to the plate-supported food. No humans, hands, fingers, held objects, skewers, utensils, extra props, floating food, dangling paws, deformed anatomy, duplicate limbs, text, logo, watermark, speech bubble, or extra animals.
```
