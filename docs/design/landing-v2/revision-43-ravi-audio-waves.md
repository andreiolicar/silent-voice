# Ravi — retrato monocromático e ondas animadas

## Resultado

- O retrato mantém o perfil, rosto, neckband e textura fotográfica do Ravi. O efeito sonoro agora é cinza neutro; os círculos fixos foram removidos da imagem.
- Três ondas SVG se expandem a partir do microfone, com halo desfocado. A inspeção da referência Salte confirmou duração de 2,4 segundos, curva `ease-out` e intervalos de 0,8 segundo.
- O retrato e a animação usam o mesmo sistema de coordenadas, com origem em `(466, 675)` no arquivo de 1024 × 979 pixels. Ambos são reduzidos a 94%, com origem em `50% 20%`, para aproximar o enquadramento do Ravi ao dos outros agentes.
- A animação pausa quando o agente está inativo ou o carrossel não está rodando. Movimento reduzido mostra uma composição estática.

## Arquivos

- Asset integrado: `apps/site/public/assets/v2/ravi-bento-silver.webp` (1024 × 979, 63.350 bytes).
- Master: `docs/design/landing-v2/ravi-bento-silver-master.png`.
- Original verde preservado em `apps/site/public/assets/v2/ravi-bento-brand.webp`.
- Componente: `apps/site/src/v2/CapabilityPortrait.tsx`.
- Animação e escala: `apps/site/src/v2/capability-portrait.css`.

## Geração

Modo: ferramenta nativa `image_gen`, edição da imagem existente, fundo opaco. Master copiado para o repositório e convertido em WebP para uso na página.

Prompt final:

```text
Use case: precise-object-edit. Edit target: the attached Silent Voice portrait of Ravi. Make a restrained, faithful edit of THIS photograph, preserving the exact man's identity, facial features, right-facing 90-degree profile, camera angle, hairstyle, head shape, dark clothing, neckband device, near-black background, photographic lighting and halftone texture. Keep the same composition and complete fading shoulders. Do not beautify, restyle, add equipment, change face, zoom in, or turn his head. The only visual edit is to the audio graphic: remove ALL teal/green color and reflected green glow. Use subtle neutral silver-gray instead, with NO green, blue, cyan or any other hue. Retain ONE delicate horizontal sound waveform, gray and low contrast, passing through the microphone point of the neckband. Retain ONLY a small softly translucent neutral-gray central disk centered exactly at the existing microphone focus (roughly x45.5%, y69% of the image), about 4.5% of the image width in radius, so it can anchor live web animation. REMOVE the static outer concentric circles entirely; these expanding rings will be drawn and animated separately in the website. Inpaint the underlying neck, clothing and device naturally where those static outer rings and green glow were. Do not leave embossed circles or ghost remnants. This must remain a dark monochrome photographic portrait, NOT a futuristic hologram or neon AI render. Keep the original image framing and near-square 1024:979 aspect ratio. No text, labels, watermark, borders or UI. Output one edited photographic asset.
```

## Validação

- `npm run build --workspace @silent-voice/site`: passou, incluindo TypeScript.
- `npm test --workspace @silent-voice/site`: 113 testes passaram (38 Node + 75 UI).
- Auditoria no navegador em 1440, 390 e 320 pixels; sem overflow horizontal nas duas larguras mobile.
- Comparação visual dos três retratos e captura do efeito em execução.
- Amostragem confirmou expansão com desaparecimento gradual, centro estacionário, pausa em agente inativo e animação desabilitada com movimento reduzido.
- Nenhum erro de console observado.
- Evidências em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/`: `revision-43-ravi-silver-waves.png`, `revision-43-ravi-mobile.png`, `revision-43-wave-motion.json`.
- A auditoria foi feita no navegador Chromium integrado; Safari não foi executado nesta revisão.
