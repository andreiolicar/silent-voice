# Estilos e componentes do Silent Voice

Atualizado em 2026-10-03. A organização preserva a composição desktop e centraliza as decisões visuais.

## Tokens

`src/styles/tokens.css` concentra os valores compartilhados. `@theme static` expõe fonte, pesos e cores ao Tailwind e mantém as variáveis usadas em SVGs disponíveis na folha final, conforme a [documentação do Tailwind](https://tailwindcss.com/docs/theme).

Componentes usam tokens semânticos; não devem repetir cores hexadecimais, escolher outra família ou criar um tamanho para um papel já existente.

| Papel | Token | Tamanho / linha |
| --- | --- | --- |
| Fonte | `--font-sans` | Inter Variable, Inter, sans-serif |
| Hero | `--type-display-*` | 44 px / 53 px |
| Título de seção ou card | `--type-heading-*` | 32 px / 38,4 px, peso 700 |
| Pergunta do FAQ | `--type-question-*` | 20 px / 28 px, peso 500 |
| Corpo | `--type-body-*` | 16 px / 24 px, peso 400 |
| Rótulo e navegação | `--type-label-*` | 14 px / 21 px |
| Controle | `--type-control-*` | 14 px / 21 px |
| Legenda | `--type-caption-*` | 12 px / 18 px |
| CTAs originais do hero | `--type-cta-*` | 12 px / 14 px, peso 400 |
| CTA original do header | `--type-cta-compact-*` | 10 px / 12 px, peso 400 |

Os três CTAs originais são uma exceção visual solicitada pelo usuário: mantêm tipografia, gradiente, texto branco no primário e verde principal no secundário. Marca e textos incorporados em imagens preservam o desenho dos assets.

A chamada do footer usa o mesmo tamanho de título, com peso 500, conforme a revisão visual solicitada. `Brand size="small"` reduz a marca a 88% apenas onde aplicado; o header mantém a dimensão original. O copyright fica integrado à coluna de contato, sobre o fundo branco do card. `SocialIcon` fornece os ícones decorativos das três redes em `currentColor`.

## Cores e efeitos

| Uso | Tokens |
| --- | --- |
| Marca | `--color-brand`, `--color-brand-light`, `--color-brand-deep`, `--color-ink` |
| Texto | `--color-text`, `--color-text-muted`, `--color-text-accent`, `--color-text-inverse`, `--color-text-on-brand` |
| Fundos | `--color-surface*` |
| Bordas e foco | `--color-border*`, `--color-focus` |
| Ilustrações | `--color-illustration-*` |
| Gradientes | `--gradient-*` |
| Sombras | `--shadow-*` |
| Liquid glass | `--glass-*` |

O verde principal continua `#1aa99b`. Destaques de texto usam `#117d73`; texto secundário mistura 64% do azul-marinho com branco. Contrastes calculados: destaque sobre branco 4,99:1; texto secundário sobre branco 5,28:1 e sobre o fundo do hero 4,78:1. O critério de referência para texto comum é 4,5:1, conforme a [W3C](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html). Esses cálculos preservam a exceção visual dos CTAs originais.

SVGs inline também usam variáveis, incluindo gradientes e sombras. A máscara da onda utiliza `--color-mask`, sempre branco, para não depender de uma futura mudança de superfície.

## Composição e componentes

`.page-container` concentra a largura máxima de 1344 px e o gutter mínimo de 48 px. Fundos de seção e faixa azul continuam ocupando toda a viewport. Novas seções devem reutilizar esse container.

| Componente | Responsabilidade |
| --- | --- |
| `Brand` | Marca completa e link para o início |
| `ActionControl` | Link nativo com destino; botão focável e sem ação quando o destino está pendente |
| `CtaButton` | CTAs originais, variantes primária, secundária e compacta |
| `ContactPill` | Contato compartilhado entre FAQ e footer |
| `SectionHeading` | Título Motion; `as="h3"` preserva a semântica dos cards |
| `SectionEyebrow` | Rótulo Motion com gradiente e estrela |
| `AccordionItem` | Expansão independente, numeração opcional, ARIA e resposta fechada inerte |
| `ContactCard` | Retrato e balão de contato com entrada Motion |
| `ExplodedDeviceMedia` | Mídia 2:1, poster, imagem aberta, controle de pausa e legendas reservadas |
| `useExplodedDevicePlayback` | Observadores de proximidade/visibilidade e preferência; integra o vídeo nativo à sessão de reprodução |
| `createPlaybackSession` | Máquina de reprodução testável; controla entrada, pausa, retomada, conclusão e pedidos assíncronos |
| `useSectionEntrance` | Entrada única a 20% de visibilidade e revelação imediata por foco ou movimento reduzido |

Os títulos produzem diretamente a tag semântica, sem wrappers adicionais para aplicar tipografia. Cada componente importa seu CSS; estilos globais ficam em `src/styles`. Destinos continuam centralizados em `src/site-links.ts`. Inter é carregada localmente via Fontsource; os arquivos e declarações de Satoshi sem uso foram removidos.

Os cards mantêm seu observador contínuo separado, pois ele também suspende os ciclos fora da tela. `useSectionEntrance` atende entradas únicas e não substitui esse relógio. Todas as animações continuam dentro do `LazyMotion` existente.

A seção Comunicação assistiva usa mídia larga acima de duas colunas de texto com intervalo de 48 px. A entrada Motion libera o vídeo quando sua animação termina. O vídeo é produzido offline no Blender com camadas RGBA; o frontend usa apenas o elemento HTML `video`. A sessão carrega a 300 px, começa ou retoma a 35% de visibilidade e pausa abaixo de 20%. Movimento reduzido, erro e conclusão apresentam a imagem aberta; as legendas só aparecem quando ela estiver decodificada. A fonte, os tokens e o hover da demonstração continuam compartilhados com o site.

## Validação

Verificados no navegador: Inter em todas as tags de texto; hierarquia e alinhamento em 1920, 1440 e 1280 px; ausência de overflow horizontal; cores dos SVGs e máscara; três CTAs restaurados; Tab/Enter/Espaço em controles pendentes; FAQ por mouse e teclado; âncoras; movimento reduzido na recarga e durante a entrada. Relatório em `docs/reference/silent-voice-typography-validation.json`.
