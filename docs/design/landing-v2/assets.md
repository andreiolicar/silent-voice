# Landing V2 — image provenance

> Superseded by the user-requested named personas in [revision-2.md](revision-2.md): `caio-master.png`, `lia-master.png`, `ravi-master.png`. Earlier prompts below are retained as provenance only; the live landing uses the revision 2 WebPs.

Generated with the built-in image_gen tool on 2026-11-10. Project masters are retained here; WebP runtime copies are in `apps/site/public/assets/v2`. Encoding: cwebp quality 86 / alpha 100, no crop, no pixel dimensions changed. Neckband reference: `apps/site/public/assets/silent-voice-device.png`. Visual composition reference: Salte screenshots supplied by the user, with original people generated for Silent Voice.

## User correction

Both shoulders and upper arms must be inside the image, with transparent padding on both sides. Never use the rejected tight portraits as site assets. The correction applies to responsive layout too: do not crop a shoulder merely to fit the hero.

## EMG persona

Master source: `exec-d04370d7-e275-4377-978c-9cf533c3878b.png` (built-in output directory). Reference identity: `exec-4a74e282-515a-408c-846b-7f4579a53902.png`.

Final edit prompt:

> EDIT this exact portrait. Required correction: ZOOM OUT substantially / expand canvas horizontally so BOTH SHOULDERS AND BOTH UPPER ARMS ARE COMPLETELY VISIBLE, with generous fully transparent empty space on BOTH sides. Do not let the silhouette touch the left or right image edge at any height. Use a WIDE 3:2 LANDSCAPE canvas with the woman centered and occupying only the central 55 percent of the width. At least 20 percent empty transparent padding to each side. Include her entire head, hair, shoulders, chest, both arms to elbows and torso to waist; the bottom may end at waist, but sides must never clip arms or shoulders. Preserve the EXACT SAME woman's facial identity, natural curly hairstyle, expression, dark shirt, white Silent Voice neckband, product details and lighting. No redesign, no new person. Extend the existing body anatomy naturally outwards. This is a website cutout asset, isolated on genuine transparent alpha with no rectangular studio backdrop, no ground. IMPORTANT: this is a framing correction, not another tight portrait. Camera much further back. Wide uncropped shoulder silhouette is the main acceptance condition.

## Vision persona

Master source: `exec-6fd8ba5a-d012-450c-80b6-b88f34bb13f7.png`. Supporting identity: `exec-a76425f3-c531-4abd-a05b-ba212a32f67c.png` and corrected EMG master for framing.

Final edit prompt:

> EDIT image 1 (the male portrait). Image 2 is ONLY reference for corrected wide framing and scale. Preserve the EXACT SAME East Asian man's face, hair, expression, dark shirt, white Silent Voice neckband and all product details from image 1. ZOOM OUT/extend canvas so both shoulders and both arms are entirely visible with generous transparent lateral margin. WIDE landscape 3:2 image. Man centered occupying about 42% of canvas width as in image 2, with at least 20% transparent margin to left and right. Full head with headroom, entire shoulders, both arms to below elbows, torso to waist. No part of silhouette touches the side edges. Camera farther back. Soft studio lighting with slight blue edge light. Clean transparent alpha background, no scenery, no rectangle backdrop, no text or UI. Match image 2 framing precisely for a coherent set of website cutout assets.

## Audio persona

Master source: `exec-1b432020-75b7-47aa-8f72-d77a9b2166be.png`. Supporting references: corrected EMG master and original neckband.

Final generation prompt:

> Create third original human AI persona for the Silent Voice campaign. First reference defines photographic art direction, wardrobe, WIDE framing and worn product; second shows exact product. NEW person: Brazilian Black man about 35, dark brown skin, close-cropped hair, subtle short beard, calm confident friendly direct gaze. Wearing the SAME simple graphite black long-sleeve crewneck and SAME white Silent Voice neckband with navy rear arc, curved white front arms and mint LED. Preserve product shape and natural wearable scale. Full head, complete shoulders, torso to waist and both upper arms/elbows entirely inside frame. Landscape 3:2 canvas; subject centered occupies ONLY central 42% width, at least 20% completely transparent blank padding on both sides. No shoulder, arm, hair or clothing can intersect either side edge. Match first reference head size and vertical placement. Photorealistic editorial studio lighting, subtle violet edge light, realistic skin. Premium hopeful human technology campaign. Transparent alpha background with clean cutout, no backdrop, no scenery, no text, no UI, no extra hardware or eyewear. This character represents audio/context; sound waves will be added in the website, not baked into this image.

## Display strategy

The same identities are reused for hero, avatar, team card and capability close-up. Dark treatments use CSS grayscale/brightness over a dark section; original generated portraits are not edited destructively. Signal overlays are local SVG/CSS. This avoids identity drift from generating independent portraits for each state. Small avatars intentionally show faces; full-size hero portraits preserve shoulder silhouettes. At narrow widths the hero emphasizes the central portrait; all three remain selectable in the team.
