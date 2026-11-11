# Revisão 10 — estrela gerada no hero

A estrela vetorial foi substituída por uma imagem renderizada com volume suave e paleta baseada no verde Silent Voice `#1AA99B`. A abertura central é maior e o corpo é mais delicado, conforme a referência enviada pelo usuário. O halo circular continua no CSS, derivado do token oficial da marca.

## Arquivos e geração

- Ferramenta: `image_gen` nativa, edição da referência; sem fallback CLI.
- Referência de estilo/forma: `Captura de Tela 2026-11-10 às 23.26.15.png`, enviada pelo usuário.
- Master: `docs/design/landing-v2/ai-star-brand-master.png`, 1254 × 1254, com alpha.
- Asset no site: `apps/site/public/assets/v2/ai-star-brand.webp`, 256 × 256, 9994 bytes, com alpha.
- Conversão: `cwebp -q 95 -m 6 -resize 256 256`.
- Aplicação: `apps/site/src/v2/Hero.tsx`, `apps/site/src/v2/landing-v2.css`.
- Renderização: caixa de 64 px no desktop e 54 px no celular, com margens transparentes no próprio arquivo. `alt=""` dentro de decoração `aria-hidden`.

## Prompt final

```text
Use case: precise-object-edit / stylized 3D icon.
Edit the reference sparkle into a finished standalone raster website asset for Silent Voice.
The attached screenshot is the STYLE AND SHAPE reference. Extract/recreate only its single soft four-point star/sparkle with a star-shaped opening in the center. Remove the entire large circular halo and white screenshot background: the output must have a genuinely transparent background, including the central opening.
Keep the reference's elegant four softly rounded tapered arms, front-on orientation, subtle organic dimensionality, pearlescent satin-gel material, luminous soft highlights, and softly blurred polished rendering. Make the colored ribbon/body about 20 percent thinner than the reference: a larger central opening and more delicate arms, while still visibly three-dimensional and readable at 48 px. This must look like a premium rendered 3D object, not a flat vector or a uniform stroked outline.
Replace all rainbow colors with a monochromatic Silent Voice teal-green palette based on EXACT #1AA99B (RGB 26,169,155): saturated brand teal midtones, pale mint highlights and slightly deeper teal shading. No blue, purple, pink, yellow or lime. Smooth ambient lighting from upper left, a subtle glow on the material only, no hard specular glitter.
One icon only, centered in a square transparent PNG, icon silhouette occupies 84 percent of canvas height and width with complete unclipped extremities and equal margins. Camera frontal, no perspective tilt. No text, letters, frame, backdrop, floor, extra shapes, external orbit, or large shadow. Preserve the central negative-space sparkle and the softly sculpted depth of the reference.
```

`transparent_background: true`. A transparência foi preservada na conversão.

## Verificação visual

Conferido no navegador em desktop 1440 × 1000 e celular 390 × 844: arquivo final carregado, dimensões corretas, transparência integrada ao halo e sem rolagem horizontal. A alteração preserva o restante do hero e o carrossel.

Capturas:
- `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-10-generated-star.png`
- `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-10-generated-star-mobile.png`
