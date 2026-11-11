# Revisão 9 — verde oficial Silent Voice

## Escopo e implementação

Cor base: `#1AA99B` / RGB 26, 169, 155, definida por `--color-brand` em `packages/web-ui/src/styles/tokens.css`.

- Bento: anel de progresso, ícones ativos, fundos, textos de destaque, diagramas e efeitos das três imagens usam o verde da marca. Os ícones mantêm preenchimento sólido e `currentColor`; o ciclo de 5 segundos e a seleção por clique/teclado continuam intactos.
- Lia: retrato principal e miniaturas, LED e reflexos da neckband, gradiente do hero, progresso, badge IA, avatar da equipe, container e demonstração EMG usam a mesma cor base e suas tintas. Preload e imagem social apontam para a nova imagem.
- Seção final: botão, fundo, círculos, foco do campo e confirmação usam o verde oficial. Texto do botão usa `--color-ink` para contraste.
- Azul de Caio e rosa de Ravi permanecem como cores de identificação no hero e na equipe; a solicitação de unificação do Bento abrange todos os três agentes.
- Alteração visual local, sem publicar ou alterar integrações.

## Imagens

Edições pela ferramenta nativa `image_gen` (sem fallback CLI), a partir dos masters aprovados. Conversão dos resultados para WebP com `cwebp -q 90 -m 6`; os retratos Bento têm largura 1024 px. O recorte transparente de Lia mantém 1254 × 1254 e canal alpha. Os arquivos anteriores continuam preservados.

| Alvo original | Master final no repositório | Asset usado pelo site |
| --- | --- | --- |
| `docs/design/landing-v2/caio-bento-v2-master.png` | `docs/design/landing-v2/caio-bento-brand-master.png` | `apps/site/public/assets/v2/caio-bento-brand.webp` |
| `docs/design/landing-v2/lia-bento-v2-master.png` | `docs/design/landing-v2/lia-bento-brand-master.png` | `apps/site/public/assets/v2/lia-bento-brand.webp` |
| `docs/design/landing-v2/ravi-bento-v2-master.png` | `docs/design/landing-v2/ravi-bento-brand-master.png` | `apps/site/public/assets/v2/ravi-bento-brand.webp` |
| `docs/design/landing-v2/lia-master.png` | `docs/design/landing-v2/lia-brand-master.png` | `apps/site/public/assets/v2/lia-brand.webp` |

### Prompt final — cada um dos três retratos Bento

```text
Use case: precise-object-edit. This is a COLOR-ONLY EDIT of the supplied approved Silent Voice portrait, not a new generation.
Change ONLY the existing BLUE holographic effects and any blue illumination to the Silent Voice brand green/teal, exact base hue #1AA99B (RGB 26,169,155). Lighter translucent highlights must be pale mint tints of this SAME teal-green hue, never blue or lime. Preserve precisely the existing overlay geometry, line positions, anatomy shapes, line weights, transparency, brightness hierarchy and softness.
Preserve everything else: identical face/identity, pose, camera, expression, crop, framing, black background, halftone dot texture, grayscale skin/clothes/neckband, logo, shoulder edges. Do not relight, beautify, sharpen, redraw, add effects, move any pixels unnecessarily or change the composition. Output the same aspect ratio and full image bounds. The intended result is the identical original image with a selective hue replacement of blue effects by #1AA99B green.
```

Cada chamada recebeu seu próprio master como imagem-alvo; `transparent_background: false`.

### Prompt final — Lia no hero e carrossel

```text
Use case: precise-object-edit. COLOR-ONLY edit of this approved transparent portrait.
Replace ONLY the bright grass/lime green accents (the small neckband status LED, the green edge reflections on the back of the neckband, and subtle green rim lighting on hair/shoulders) with the brand teal-green #1AA99B (RGB 26,169,155). Maintain their original intensity and subtlety but use the exact brand hue. Preserve the existing teal logo.
All other pixels and composition should stay as close to identical as possible: same woman, face, hair, expression, natural skin color, white jacket, dark top, neckband geometry and logo lettering, image dimensions/aspect ratio, crown/head position, COMPLETE shoulder contours, and bottom crop. Do not regenerate her face or clothes, zoom, rotate, move or add anything. Preserve the original transparent background and alpha edges exactly. Output a transparent PNG cutout, identical framing to input.
```

Imagem-alvo `lia-master.png`; `transparent_background: true`.

## Verificação

- Navegador desktop 1440 × 1000 e mobile 390 × 844. Hero, seleção da Lia na equipe, três estados do Bento e formulário final inspecionados. Sem rolagem horizontal.
- Computed styles confirmam RGB 26, 169, 155 no aro, no destaque textual do Bento e no botão final; gradientes e foco derivados do mesmo token.
- Anel normal: `v2-cap-ring-fill`, 5 s, traço RGB 26, 169, 155. Movimento reduzido conserva seleção manual e anel estático.
- Assets finais carregados no navegador: Caio 1024 × 916, Lia Bento 1024 × 895, Ravi 1024 × 979. Retrato Lia 1254 × 1254 com alpha.
- `npm test`: 305 testes passaram, 3 integrações PostgreSQL ignoradas por configuração; nenhum teste falhou.
- `npm run typecheck`, `npm run build` e `git diff --check` passaram.

Capturas salvas em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/`:
- `revision-9-brand-hero.png`
- `revision-9-brand-team.png`
- `revision-9-brand-bento.png`
- `revision-9-brand-footer.png`
- `revision-9-brand-mobile.png`
- `revision-9-brand-footer-mobile.png`
