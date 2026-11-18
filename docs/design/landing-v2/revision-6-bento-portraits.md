# Revisão 6 — retratos exclusivos para o Bento

## Direção e implementação

Três imagens geradas com a ferramenta nativa `image_gen`, usando os masters aprovados como referência de identidade e neckband e os três prints enviados pelo usuário como referência de direção visual. Fundo preto, retrato com luz baixa, textura pontilhada discreta e efeitos translúcidos azuis. Caio em três quartos com projeção da câmera; Lia frontal com fibras musculares ilustrativas sobre boca, bochechas e mandíbula; Ravi de perfil com ondas centradas na neckband.

A anatomia é uma representação conceitual: não define um mapa clínico de músculos ou a posição validada de sensores. Nenhum nome anatômico ou especificação técnica foi acrescentado à página.

Masters preservados nesta pasta: `caio-bento-master.png`, `lia-bento-master.png`, `ravi-bento-master.png`. Publicação local: `apps/site/public/assets/v2/{caio,lia,ravi}-bento.webp`, 1024 × 1024, conversão com cwebp qualidade 88, sem edição de pixels. As imagens novas são usadas somente em Capabilities, via `bentoPortrait`; os retratos do hero e do carrossel permanecem os aprovados. Efeitos já integrados nas imagens substituem os overlays genéricos anteriores. Imagens contidas integralmente no quadro, com transição de opacidade e respeito ao movimento reduzido.

## Verificação

- Prévia em 1440 × 1000 e 390 × 844; três retratos carregados, seleção conferida, ombros contidos no quadro e nenhuma rolagem horizontal no celular.
- Movimento reduzido conferido no navegador: duração da transição de opacidade igual a 0s. Console sem erros na sessão de verificação.
- `npm test`, `npm run typecheck`, `npm run build` e `git diff --check` concluídos com código 0.
- Capturas em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-6-bento-{caio,lia,ravi,mobile}.png`.

## Prompts finais

### caio

```text
Use case: ads-marketing.
Asset type: dedicated portrait for the black capabilities Bento section of the Silent Voice website.
Create one NEW square cinematic portrait using the input images as references. Image 1 defines our specific character identity, haircut, face and Silent Voice neckband product. Image 2 defines only the art direction: near-black photographic portrait, subtle fine halftone/dot texture and elegant luminous translucent ice-blue holographic visualization. Do NOT use the person or headset from image 2.
Keep the same character identity from image 1, the same physical white U-shaped Silent Voice neckband with navy rear band and two separated rounded front arms, and the same technical jacket over a black crewneck. The clothing is subdued charcoal/silver under low-key lighting, not a brightly lit white area. Keep the neckband recognizable. No goggles, VR visor, headphones, helmet or additional wearables.
Composition: square 1024x1024, head and upper chest portrait, person centered, crown at roughly 9% of image height, eyes near 35%, neckband near 64%. Both outer shoulder contours MUST fit inside the canvas with at least 7% empty black margin on each side. Never cut shoulders at the left or right edge. Torso gradually dissolves to pure black at the bottom, no hard horizontal crop. Leave a little space for the holographic visualization without touching frame edges.
Lighting/style: premium restrained cinematic grayscale portrait, realistic recognizable face, medium-low-key studio illumination so details remain readable at 350px display size, subtle fine dot texture on clothing and shadow regions. Deep clean pure black background (#000000), soft controlled blue glow only from the visualization. No large fog cloud, no decorative background, no border, no card UI. Holographic lines are light ice-blue and translucent, technically elegant, integrated with perspective. No captions, labels, legends, floating numbers or watermarks. No red tissue, no gore.
Specific subject: Caio, the East Asian man in reference image 1. Turn him to a three-quarter view facing toward image right, head slightly lifted, calm intent gaze. Preserve his recognizable face. Camera capability visualization: emphasize a small lens integrated into the front arm of his neckband. A fine cone of 5-7 translucent blue perspective scan lines projects from that neckband lens forward and gently upward toward the right, accompanied by a subtle sparse facial tracking mesh around the lips and jaw. The camera lens and mouth are visually connected, showing visual articulation capture. The projection originates at the actual neckband, never at his eyes. Make the optical effect readable yet delicate, similar restraint to the reference.
```

### lia

```text
Use case: ads-marketing.
Asset type: dedicated portrait for the black capabilities Bento section of the Silent Voice website.
Create one NEW square cinematic portrait using the input images as references. Image 1 defines our specific character identity, haircut, face and Silent Voice neckband product. Image 2 defines only the art direction: near-black photographic portrait, subtle fine halftone/dot texture and elegant luminous translucent ice-blue holographic visualization. Do NOT use the person or headset from image 2.
Keep the same character identity from image 1, the same physical white U-shaped Silent Voice neckband with navy rear band and two separated rounded front arms, and the same technical jacket over a black crewneck. The clothing is subdued charcoal/silver under low-key lighting, not a brightly lit white area. Keep the neckband recognizable. No goggles, VR visor, headphones, helmet or additional wearables.
Composition: square 1024x1024, head and upper chest portrait, person centered, crown at roughly 9% of image height, eyes near 35%, neckband near 64%. Both outer shoulder contours MUST fit inside the canvas with at least 7% empty black margin on each side. Never cut shoulders at the left or right edge. Torso gradually dissolves to pure black at the bottom, no hard horizontal crop. Leave a little space for the holographic visualization without touching frame edges.
Lighting/style: premium restrained cinematic grayscale portrait, realistic recognizable face, medium-low-key studio illumination so details remain readable at 350px display size, subtle fine dot texture on clothing and shadow regions. Deep clean pure black background (#000000), soft controlled blue glow only from the visualization. No large fog cloud, no decorative background, no border, no card UI. Holographic lines are light ice-blue and translucent, technically elegant, integrated with perspective. No captions, labels, legends, floating numbers or watermarks. No red tissue, no gore.
Specific subject: Lia, the woman in reference image 1 with wavy brown hair. Front-facing, direct calm gaze, symmetrical composition. Muscular signal visualization: an elegant translucent blue anatomical layer aligned exactly to the lower half of HER face. Show delicate glass-like facial muscle fiber bundles around the lips, cheeks, jaw and chin, gently extending below the jaw toward the neckband. The muscle fibers fan along natural facial contours and curve around the mouth; realistic skin and facial identity remain visible through the blue layer. Similar to the translucent blue brain in reference image 2, but located over the facial musculature instead of the brain. Small subtle blue sensing points and fine signal paths visually connect this muscular layer to the neckband. This is an aspirational illustrative visualization, without anatomical labels. Do not show a brain, skull, teeth, bones, mechanical mask, blue solid face paint, or exposed flesh. The eyes and forehead remain unobscured. Keep the layered glass fibers elegant and legible, not a generic triangular wireframe.
```

### ravi

```text
Use case: ads-marketing.
Asset type: dedicated portrait for the black capabilities Bento section of the Silent Voice website.
Create one NEW square cinematic portrait using the input images as references. Image 1 defines our specific character identity, haircut, face and Silent Voice neckband product. Image 2 defines only the art direction: near-black photographic portrait, subtle fine halftone/dot texture and elegant luminous translucent ice-blue holographic visualization. Do NOT use the person or headset from image 2.
Keep the same character identity from image 1, the same physical white U-shaped Silent Voice neckband with navy rear band and two separated rounded front arms, and the same technical jacket over a black crewneck. The clothing is subdued charcoal/silver under low-key lighting, not a brightly lit white area. Keep the neckband recognizable. No goggles, VR visor, headphones, helmet or additional wearables.
Composition: square 1024x1024, head and upper chest portrait, person centered, crown at roughly 9% of image height, eyes near 35%, neckband near 64%. Both outer shoulder contours MUST fit inside the canvas with at least 7% empty black margin on each side. Never cut shoulders at the left or right edge. Torso gradually dissolves to pure black at the bottom, no hard horizontal crop. Leave a little space for the holographic visualization without touching frame edges.
Lighting/style: premium restrained cinematic grayscale portrait, realistic recognizable face, medium-low-key studio illumination so details remain readable at 350px display size, subtle fine dot texture on clothing and shadow regions. Deep clean pure black background (#000000), soft controlled blue glow only from the visualization. No large fog cloud, no decorative background, no border, no card UI. Holographic lines are light ice-blue and translucent, technically elegant, integrated with perspective. No captions, labels, legends, floating numbers or watermarks. No red tissue, no gore.
Specific subject: Ravi, the Black man with short textured hair from reference image 1. True side profile facing image right with enough near shoulder visible to clearly reveal the Silent Voice neckband microphone. Preserve his recognizable facial structure and haircut. Audio/context visualization: thin concentric translucent ice-blue listening rings centered precisely on a microphone aperture on the visible side/front arm of the neckband at the base of the neck, with a fine horizontal sound waveform passing through that same point. Rings have varying subtle opacity and extend around the lower jaw/neck and shoulders; they must NOT be centered on the ear. No headphones. The profile silhouette, neckband, microphone and blue wave rings should form the main visual composition, restrained and cinematic like the reference.
```
