# Landing mobile — 2026-10-20

Preservados todos os textos, imagens, seções, CTAs, SVGs e interação de abrir/fechar o dispositivo. Desktop mantém a composição aprovada; abaixo de 960 px, hero e seções passam a uma coluna e a navegação fica em um menu acessível. Indicadores ficam em 2 × 2 no celular. Footer e FAQ se adaptam sem remover conteúdo.

Validação local no Chromium: document.scrollWidth igual à viewport em 320, 360, 375, 390, 430, 600, 768, 960, 1024, 1280 e 1440 px. Menu testado por clique e Escape; dispositivo testado por teclado. Teste automatizado do menu incluído.

Build e suíte passaram antes do push. Deploy automático na branch deploy/static-frontend. Backend e integração de banco seguem fora desta entrega.
