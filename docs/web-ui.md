# Interfaces web

Landing e administração compartilham Inter, tokens em `packages/web-ui/src/styles`, botões e inputs aprovados. Verde: `#1AA99B`; azul-marinho: `#051B34`. Não redefina um componente equivalente em cada app. O mobile preserva Manrope e seus próprios componentes nativos.

A landing mantém responsividade, splash, movimento reduzido, cards animados e dispositivo que abre/fecha por clique ou teclado. O snapshot mobile da landing já inclui navegação compacta e seções em uma coluna. O dispositivo preserva camadas, tracejados e tooltips; não foi convertido em Three.js ou vídeo.

Admin usa sidebar, tabela paginada, filtros, detalhes/notas e estados de acompanhamento. Inputs e botões em pílula, foco discreto, card de login de 24 px, sem redesenho nesta migração. As páginas públicas de conta pertencem ao mesmo app administrativo.

O assistente carrega sob demanda e renderiza somente o catálogo aprovado de OpenUI. O gerador `npm run generate:chat --workspace @silent-voice/site` atualiza `packages/contracts/src/openui-spec.json`; o prebuild também executa esse passo. A API lê a especificação compartilhada sem importar código do site.

Os destinos públicos continuam em `apps/site/src/site-links.ts`. Recursos ilustrativos ou controles sem destino não devem ser apresentados como funcionalidades comerciais prontas.
