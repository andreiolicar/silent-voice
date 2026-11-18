# Interfaces web

Landing e administração compartilham Inter, tokens em `packages/web-ui/src/styles`, botões e inputs aprovados. Verde: `#1AA99B`; azul-marinho: `#051B34`. Não redefina um componente equivalente em cada app. O mobile preserva Manrope e seus próprios componentes nativos.

A landing mantém responsividade, splash, movimento reduzido, cards animados e dispositivo que abre/fecha por clique ou teclado. O snapshot mobile da landing já inclui navegação compacta e seções em uma coluna. O dispositivo preserva camadas, tracejados e tooltips; não foi convertido em Three.js ou vídeo.

Admin usa sidebar, tabela paginada, filtros, detalhes/notas e estados de acompanhamento. Inputs e botões em pílula, foco discreto, card de login de 24 px, sem redesenho nesta migração. As páginas públicas de conta pertencem ao mesmo app administrativo.

O assistente carrega sob demanda e renderiza somente o catálogo aprovado de OpenUI. O gerador `npm run generate:chat --workspace @silent-voice/site` atualiza `packages/contracts/src/openui-spec.json`; o prebuild também executa esse passo. A API lê a especificação compartilhada sem importar código do site.

Os destinos públicos continuam em `apps/site/src/site-links.ts`. Recursos ilustrativos ou controles sem destino não devem ser apresentados como funcionalidades comerciais prontas.

## Tipografia da landing V2

A família única é **Inter Variable**, carregada localmente por `@fontsource-variable/inter` no pacote web-ui e referenciada por `--font-sans`. O FAQ também usa Inter; a antiga declaração de Plus Jakarta Sans foi removida. Os logotipos e badges em SVG continuam sendo arte da marca.

Use `Typography` de `@silent-voice/web-ui/Typography` para títulos e textos da landing. A escala responsiva fica em `packages/web-ui/src/ui/typography.css`; os estilos de seção cuidam apenas de cor, gradiente, largura, alinhamento e espaçamento.

| Variante visual | Desktop: tamanho / entrelinha | Mobile até 540 px | Peso | Uso |
| --- | --- | --- | --- | --- |
| `h1` | 56 / 62 px | 28 / 32 px | 600 | Hero, equipe, capacidades e lista de interesse |
| `h2` | 40 / 44 px | 24 / 30 px | 600 | Títulos menores, como FAQ |
| `h3` | 24 / 30 px | 20 / 26 px | 600 | Títulos dos cards e assistentes |
| `body` | 18 / 26 px | 16 / 24 px | 400 | Parágrafos, descrições e respostas |
| `label` | 14 / 21 px | 14 / 21 px | 400 | Rótulos auxiliares |
| `caption` | 12 / 18 px | 12 / 18 px | 400 | Rodapé e mensagens de formulário |

Há degraus intermediários em 1024 e 768 px; até 360 px, todos os títulos grandes passam juntos a 26 / 30 px. Controles como botões e navegação mantêm seus tokens próprios e a mesma família Inter.

O atributo `as` define a semântica HTML, e `variant` define a aparência. Só o hero usa `as="h1"`; os demais títulos grandes usam `as="h2" variant="h1"`. Perguntas do FAQ usam `as="h3" variant="body" weight="semibold"`, mantendo a hierarquia acessível com tamanho de texto.

```tsx
<Typography as="h2" variant="h1">Uma equipe de IA trabalhando pela sua expressão.</Typography>
<Typography as="h2" variant="h2">Perguntas frequentes</Typography>
<Typography as="h3" variant="h3">Pequenos sinais. Novas possibilidades.</Typography>
<Typography as="p" variant="body">Uma tecnologia que reúne diferentes sinais.</Typography>
```
