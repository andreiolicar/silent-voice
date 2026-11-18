# Hero humano — 2026-11-16

Atualização aprovada: removidas as abas “Em uso / Explorar dispositivo” e a visualização alternativa do hero. A abertura agora apresenta somente a mulher e os três sinais, sem espaço reservado ao seletor. Componentes históricos do dispositivo permanecem no repositório.

Implementação local do plano aprovado: retrato editorial como usuário ilustrativo, três agentes como inteligência de apoio e abas Em uso / Explorar dispositivo. Mantidos título, CTA, dispositivo interativo e seções posteriores. Nenhuma publicação.

## Asset e origem

- Ferramenta: image_gen integrada (sem CLI).
- Asset inicial: `apps/site/public/assets/v2/person-hero.png`, transparência preservada.
- Asset intermediário: `apps/site/public/assets/v2/person-hero-emg-camera.png` (volume excessivo e orientação da câmera rejeitados).
- Asset ativo corrigido: `apps/site/public/assets/v2/person-hero-hardware-refined.png`.
- Referência de hardware: `apps/site/public/assets/device-interactive/closed.webp`.
- Pessoa fictícia ilustrativa; não é cliente, depoimento ou agente de IA do produto.

Prompt utilizado:

> Use case: photorealistic-natural. Create a new transparent-background editorial portrait asset for Silent Voice assistive communication website. Reference image is ONLY the exact hardware design to be worn, not composition. A real-looking adult woman about 40, warm medium complexion, short dark curly hair tucked clear of jaw, natural skin texture, calm attentive expression and gently parted relaxed lips. Chest-up including complete shoulders, slight three-quarter turn looking toward viewer's left. Wearing a simple oatmeal crew-neck everyday knit with neckline low enough to clearly expose the neckband. Fit the reference Silent Voice neckband naturally around the base of her neck: navy back band, two rounded white elongated front modules, small turquoise light, subtle existing brand mark, exact reference proportions, not headphones on ears, no invented cables or sensors. Both front modules visible. Elegant soft studio lighting, understated human warmth, realistic editorial photography rather than glossy AI avatar. Subject centered with all head and both shoulders inside frame, margin above hair, portrait 4:5 composition, crop at lower chest. Genuine transparent alpha surrounding person. No background, no card, no text labels, no UI, no phone, no medical attire, no hands, no dramatic smile, no extra people. This person represents an illustrative user, NOT an AI assistant. Save the resulting image for use in this project and return its local file path.

## Revisão de hardware solicitada pelo usuário

Neckband aproximadamente 1,6× maior em relação ao retrato inicial; seis eletrodos EMG (três em cada face) conectados por fios; haste e módulo de câmera brancos. Referência funcional fornecida: `prototipo-visual.png`. Mantidos pessoa, roupa, enquadramento, transparência e layout. Alteração somente do retrato em uso; o asset anterior continua preservado.

Ferramenta: image_gen integrada. Prompt da revisão:

> Edit image 1 only, preserving the EXACT same woman identity, facial expression, curly hair, oatmeal clothing, lighting, pose, portrait crop and transparent background. Image 2 is ONLY a functional hardware reference for electrode placement and camera arm; do not copy its man, black neckband or background. Make these three changes: (1) enlarge the current Silent Voice neckband hardware to approximately 1.6 times its current linear size, visibly bulkier longer white front housings and thicker navy rear band, fitting naturally on shoulders/base of neck rather than tight against neck; retain its white/navy design, turquoise indicator and brand. (2) Add EXACTLY THREE separate round white adhesive EMG electrode pads on EACH cheek, total SIX visible electrodes, like reference image 2: one upper cheek near masseter, one lower cheek beside mouth and one along lower jaw on each side, naturally perspective-scaled. Each electrode has a small central snap connector and a thin pale gray wire running neatly down to the corresponding side of the neckband. No electrodes on forehead, nose or lips. (3) Mount a slim rigid WHITE camera boom arm on one white neckband housing. It extends forward and rises to a small WHITE camera module with a dark lens window in front of and slightly below the mouth, lens aimed back toward the lips to capture lip movement, physically attached with a small hinge. Match the practical arm geometry in image 2 but WHITE, not black. Keep mouth visible; don't place module on top of lips or cover face. This is a photorealistic editorial product illustration, preserve clean sophisticated style and skin detail. Genuine transparent alpha, no background, no UI, no extra people or text overlays. Keep full hair and both shoulders in frame, same image aspect ratio as image 1.

Refinamento de orientação da câmera:

> Rotate only the white camera module inward toward the lips, showing its white rear/side to the viewer. Preserve identity, larger neckband, six electrodes, wires, arm, crop and transparency.

## Verificação

Correção seguinte: retomada do retrato original para preservar arco fino e carcaças alongadas. Módulo deslocado à frente do queixo, mostrando sua traseira branca, com face óptica voltada à mulher. Gerado com image_gen integrada; transparência preservada. Direção do prompt final: Restarted from original person-hero.png with closed.webp as strict geometry reference. Enlarge original elongated flat housings about 1.6x, retain slim navy rear band (no neck-pillow tube), add six electrodes and white boom, camera opaque rear facing viewer and lens facing inward/upward toward lips.

- Testes novos: seleção inicial, montagem condicional do dispositivo, setas/Home/End, Tab até o painel e o dispositivo, fallback e liberação da intro em falha da imagem.
- Conferência no navegador: 1440×900, 1280×800, 390×844, 360×800; abertura do dispositivo por Enter e movimento reduzido.
- Revisão independente encontrou ordem de foco inadequada: corrigida com tablist antes dos painéis no DOM, mantendo posição visual inferior. Teste de regressão observado falhando e depois passando.
- Limitação da suíte Node neste Windows: teste preexistente `private-files.test.mjs` concatena `/@fs` com caminho Windows absoluto e recebe 200 em vez de 403/404. Não alterado nesta tarefa visual; requer correção específica do teste e validação das URLs normalizadas.
