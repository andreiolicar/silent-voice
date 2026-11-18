# Lia — anatomia discreta e LED

A imagem do Bento foi editada com a ferramenta nativa `image_gen`. O rosto permanece fotográfico, com detalhes suaves ao redor da boca, nos masseteres e na região do maxilar, conforme o último ajuste solicitado. O LED existente na neckband aparece aceso em verde, com brilho localizado e menos intenso que o do Caio.

## Arquivos finais

- `apps/site/public/assets/v2/lia-bento-refined.webp` — 1024 × 895, integrado em `agents.ts`.
- `docs/design/landing-v2/lia-bento-refined-master.png` — master gerado.
- O retrato anterior `lia-bento-brand.webp` foi preservado.

## Verificação

Build do workspace site e TypeScript passaram. Imagem conferida no navegador em 1440 e 390 pixels, com carregamento do novo asset confirmado e sem overflow horizontal no celular. Nenhuma mudança de comportamento ou dimensão do card. Evidências em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-48-lia-maxilar-led.png` e `revision-48-lia-mobile.png`.

## Prompts usados

### Edição 1

```text
Use case: precise-object-edit. Asset: Silent Voice dark Bento portrait of Lia. The attached image is the edit target, not merely an inspiration. Preserve this exact woman, her face and identity, frontal camera angle, neutral expression, hair, skin texture, neckband device, clothing, halftone photographic finish, black background, head size, head placement and complete softly fading shoulders. Preserve the original 1024:895 composition and aspect ratio. Change only the anatomical overlay. First REMOVE the existing glowing full-face green muscle mask and its green light spill, restoring the natural monochrome skin underneath. Then add a much more restrained, faint semi-transparent anatomical indication in ONLY THREE localized areas: (1) a narrow, delicate band of muscle fibers immediately surrounding the lips, representing the orbicularis oris; (2 and 3) two small, anatomically placed masseter patches on the far lateral lower cheeks in front of the ears, with short vertical fibers. The rest of the face must remain completely photographic and unmarked. Keep bare natural skin clearly separating those three areas. DO NOT show chin/mentalis muscles, the jawline or mandibular bone outline, any teeth or skeleton, nose muscles, upper cheek networks, eye muscles, forehead or neck anatomy. No whole-face overlay, no anatomical skin removal, no exposed flesh, no superhero mask. Color must be a very subtle desaturated gray-green inspired by #1AA99B: around one quarter of the visual intensity of the original overlay, roughly 15–20% translucent, fine sparse fibers, soft feathered edges, almost no glow. The portrait and skin must dominate; the muscle indication should be secondary and understated. Avoid neon green, filled luminous patches, full facial diagrams, extra muscles or labels. Do not add text, change the product design, move her head, crop her shoulders, make her face bigger, or change the lighting outside the three small overlay areas. This is a quiet photographic product illustration, not a dramatic sci-fi anatomical render.
```

### Edição 2

```text
Use case: precise-object-edit. Make ONE small local revision to this already-approved edited portrait of Lia: increase the visibility of ONLY the existing three small anatomical fiber overlays by about 60–80%, so the fine fibers can still be perceived when the full portrait is displayed at 385 pixels high. Keep the same very limited regions: a narrow band immediately around the lips and the two small vertical masseter patches in the far lateral lower cheeks. Do NOT enlarge the areas, add any additional fibers elsewhere, connect the patches together, or create a facial mask. Use muted gray-green around #5F9C96 with soft translucent fine lines, slight soft shading within the fibers, and no luminous bloom; still much quieter than a hologram or full green face overlay. The muscles should be clearly recognizable as secondary delicate details, not fluorescent or bright. Leave the chin, jawline, mandibular bone, nose, upper cheeks, eye area, forehead and neck completely natural and unmarked. Preserve everything else EXACTLY: face identity, expression, neutral monochrome skin, hairstyle, frontal pose, head dimensions and placement, black background, complete shoulder fade, lighting, halftone texture and neckband. Do not alter the eyes, lips, nose, face shape, device or clothes. Keep the same 1024:895 composition and aspect ratio. No labels, text or borders. Input is the edit target.
```

### Edição 3

```text
Use case: precise-object-edit. Image 1 is the EXACT edit target: Lia's frontal monochrome Silent Voice portrait with subtle localized muscle fibers. Image 2 is ONLY a reference for the neckband indicator light color; do not copy that man's face, angle, pose or scanning rays. Make only these two small changes to Image 1. (1) Gently indicate the maxillary region as well: a faint, delicate gray-green anatomical contour in the lower mid-cheeks beside and slightly above the mouth, between the existing perioral band and lateral masseter patches. Give it the same understated translucent treatment as those existing fibers, never a solid green patch or complete facial mask. The indication should be sparse and localized, softly feathered and separated by visible natural skin. Keep the chin and lower mandibular outline unmarked; no skeleton, teeth, exposed bone, eye muscles, forehead anatomy or broad green coating. Do not intensify the already-approved lip and masseter details. (2) Switch on the existing tiny pill-shaped indicator LED on the front left neckband arm, above the round button, in Silent Voice teal green #1AA99B. Make the LED softly lit with a very small localized halo, approximately half the intensity of the LED in Image 2. It must read as a real small status light, not a laser, lens flare or giant glowing patch. NO projected rays, scan lines, light beams or waves. Preserve EVERYTHING ELSE exactly: Lia's identity, face, eyes, lips, expression, hair, frontal camera, neckband shape, printed logo, clothing, dark photographic lighting, halftone texture, black background, head size/position and full faded shoulders. Keep the same 1024:895 composition and aspect ratio. No text labels, border, watermarks or additional equipment.
```
