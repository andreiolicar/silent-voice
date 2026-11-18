# Conversão BGR8 e aquisição 4:3 no laboratório iOS

## Situação verificada

A build anterior foi ensaiada no iPhone 13: 121 frames, 4.000 s, 30 FPS, perdas reportadas 0, BGRA32, 480 × 640 em retrato, sem espelhamento dos dados. O teste Swift → Hermes passou, assim como cancelamento, background e retorno ao aplicativo.

O Python em `ai/src/silent_voice/inference/live_visual_tester.py` pede 640 × 480 à câmera (`open_camera`) e rejeita qualquer entrada diferente de `(480, 640, 3)` na aquisição. Não existe nesse caminho uma regra de recorte ou redimensionamento que possamos simplesmente portar para transformar retrato em paisagem.

## Abordagens e recomendação

**Recomendada: primeiro ensaio horizontal 4:3.** O operador segura o iPhone na horizontal. O adaptador configura a orientação de aquisição correspondente, exige buffer BGRA32 640 × 480 não espelhado e produz BGR8 com as mesmas dimensões e ordem espacial. Remove somente o alfa e o padding das linhas. Não corta, redimensiona, interpola ou altera proporções. Esta escolha simplifica a comparação com a entrada exigida pelo núcleo.

**Alternativa: aquisição com o iPhone vertical.** Seria necessário aprovar uma política adicional, como recorte central e escala para 4:3 ou letterbox, e demonstrar seus efeitos sobre enquadramento e pré-processamento. Isso cria uma adaptação que não está definida no código Python recebido. Pode ser uma etapa posterior orientada pela experiência final do aplicativo.

A recomendação é minha decisão técnica proposta, ainda sujeita à escolha de Andrei. Não define como o produto final deverá ser usado nem muda a orientação global da interface.

## Entrega proposta

1. Adicionar ao módulo Swift uma função pura para empacotar BGRA32 em BGR8. Validar tamanho, dimensões, stride e limites de memória. Respeitar `bytesPerRow`, descartar alfa/padding e manter exatamente B, G, R em ordem row-major. Falhar com estado controlado para buffer incompatível.
2. Produzir uma fixture pequena de referência com Python de biblioteca padrão: padrões aritméticos, amostras de pixels, contagem de bytes e SHA-256 do BGR esperado. Sem OpenCV, modelos ou dados reais. Conferir a mesma fixture nos testes Swift e no ensaio nativo/Hermes.
3. Manter disponível o ensaio de origem em retrato e adicionar uma captura de conversão 4:3 identificada separadamente. A UI pede para segurar o telefone na horizontal antes de iniciar; em vertical/posição indeterminada, bloqueia sem abrir a câmera.
4. Fotografias/vídeos e pixels reais não são salvos, transmitidos, retornados ao JavaScript ou incluídos em logs. O buffer BGR existe apenas durante o processamento nativo de cada frame e é descartado. Hashes e amostras são emitidos somente para a entrada sintética, nunca para uma imagem de pessoa.
5. A captura horizontal usa um snapshot explícito da orientação física. A correspondência UIDevice/AVCaptureVideoOrientation é testada; rotação durante a aquisição, cancelamento, perda de foco e background interrompem a captura. A interface normal continua em retrato; este é um ensaio técnico.
6. Reportar separadamente os metadados da origem e do buffer convertido: dimensões, formato, tamanho de bytes e sucesso da conversão. Os timestamps permanecem relativos e calculados na precisão nativa. Somente os metadados de um buffer efetivamente convertido podem alimentar o gate congelado.
7. A UI distingue “Conversão sintética PASS”, “Gate técnico PASS/BLOCKED” e “Reconhecimento indisponível”. Passar em formato/cadência não habilita inferência nem constitui validação R4.

## Escopo e limites

- Reutilizar a área de ensaio privada e o adaptador atual, sem alterar autenticação, fluxo Live, gateway USB ou arquitetura Android.
- Preservar SDK/versões e o contrato do João. Não instalar dependências npm ou Python de ML.
- Não implementar FaceMesh, ROI, tensor, DTW ou modelos. Não alterar thresholds ou aceitar automaticamente tolerâncias propostas no handoff.
- A referência Python proposta verifica a conversão de bytes, não equivalência de câmeras, corimetria, orientação de rostos, detector ou inferência. A orientação declarada deriva da configuração de captura; não de análise facial.
- Sem commit, push ou publicação. Preservar todas as alterações locais anteriores.

## Verificação e aceite

- Testes de cores assimétricas, ordem espacial, alfa variado, padding, buffer truncado, stride inválido, limites de dimensões e orientação.
- Comparação exata do hash sintético Swift/Python e teste da ligação ao Hermes no aparelho.
- Build Release assinada em série e instalada no iPhone. Ensaiar captura horizontal nas duas posições, bloqueio em retrato, rotação/cancelamento/background e retorno normal.
- Medir FPS e perdas depois da conversão; não pressupor que o desempenho da aquisição sem conversão será mantido.
- Checks do monorepo, testes Swift e revisão independente. Registrar separadamente observações do operador e evidências automatizadas.

## Referências consultadas

- Código local: `ai/src/silent_voice/inference/live_visual_tester.py`, funções `open_camera` e aquisição temporal.
- Expo SDK 57: https://docs.expo.dev/versions/v57.0.0/
- Rotação física de buffers AVFoundation: https://developer.apple.com/documentation/avfoundation/avcaptureconnection/videoorientation
- Acesso CPU ao pixel buffer: https://developer.apple.com/documentation/corevideo/cvpixelbufferlockbaseaddress(_:_:)

## Estado

Andrei aprovou explicitamente implementar e testar primeiro na horizontal, nesta sessão. A revisão de planejamento não encontrou perguntas técnicas importantes pendentes.
