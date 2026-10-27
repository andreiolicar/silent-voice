# Design System

O código em `src/theme/` é a fonte de verdade estrutural; o Figma é a referência visual. Valores equivalentes são normalizados antes de entrar em componentes React Native.

## Tokens

- **Cores:** fundo `#F6F5F8`, superfície branca, primária `#051B34`, accent `#1AA99B` e cinza `#929CAD`. Papéis semânticos incluem texto primário/secundário, accent suave, bordas, disabled, overlay e feedback success/warning/error. O texto auxiliar usa `textSecondary`; os tamanhos foram aumentados em vez de escurecer arbitrariamente a marca.
- **Tipografia:** Manrope Regular, Medium, SemiBold e Bold. As variantes são `display`, `screenTitle`, `sectionTitle`, `subtitle`, `body`, `bodySmall`, `cardTitle`, `metric`, `supporting`, `caption`, `label`, `button`, `navigation` e `badge`.
- **Espaçamento:** escala de 4, 6, 8, 10, 12, 16, 20, 24, 30 e 35. `screen` representa o padding horizontal responsivo de 30.
- **Radius:** 10 para cards/controles, 20 para badges e 999 para pills/círculos.
- **Linguagem flat:** O Silent Voice utiliza linguagem visual flat. Shadows não fazem parte do padrão de cards, containers ou interações. A separação visual usa surface, spacing, contraste, radius e bordas sutis quando semanticamente necessárias. O card do módulo conectado por USB também permanece sem glow ou elevação.
- **Motion:** Reanimated usa tokens compartilhados para entrada de tela (fade de 220 ms), entrada de seção (fade e deslocamento vertical de 20 px em 320 ms, com intervalo de 60 ms limitado a 180 ms), feedback de pressão (140 ms) e Toggle (200 ms). Botões chegam a escala 0,97, cards acionáveis a 0,985 e o item ativo da navegação a 1,08. Animações acontecem apenas em entradas, ações e mudanças de estado; não há movimento decorativo contínuo. Hover, focus e estados visuais mantêm contraste e indicação de interação. Com redução de movimento, deslocamento, escala, intervalo e duração são removidos sem ocultar feedback de estado.

Cards com estados dinâmicos permanecem montados enquanto o conteúdo muda. A entrada é reservada à tela, seção ou etapa; mudanças de status atualizam imediatamente texto e semântica, e podem animar indicadores internos como a barra de progresso.

## Componentes

- `ui`: `AppText`, `Button`, `IconButton`, `Card`, `Badge` e `Toggle`.
- `layout`: `Screen`, `AppHeader`, `ScreenHeading` e `BottomNavigation`.
- `silent-voice`: `PrivacyNotice`, `StatusBadge`, `RadarIndicator`, `MetricCard`, `DeviceCard` e `ModuleCard`.

Componentes interativos possuem touch target mínimo de 44 px, papéis e estados de acessibilidade. Os ícones usam exclusivamente `lucide-react-native` quando o glyph corresponde ao Lucide do Figma.

No web, o indicador de foco discreto aparece somente em navegação por teclado com `focus-visible`; clique de mouse não deixa ring persistente. Hovers usam cor, background ou opacidade, sem adicionar sombras. Cards informativos permanecem estáticos; cards com ação recebem feedback de pressão. Entradas usam deslocamento curto e opacidade, e controles acionáveis usam escala breve. Não há bounce, sombras novas ou animações em loop.

## Normalização

Padding 11/12/13 converge para 12; radius 9/10 converge para 10; gaps próximos usam a escala existente. Textos de 7–10 px do wireframe foram normalizados para 11–12 px quando auxiliares e 14 px quando corpo ou ação. O botão visual de aproximadamente 42 px usa altura interativa de 48 px. A navegação preserva a pill de 72 px e o destaque central de 52 px.

Layouts usam flexbox, largura disponível, conteúdo intrínseco e Safe Area. A largura de 402 px é apenas referência; não deve ser codificada como viewport fixa. Posicionamento absoluto fica restrito a composição genuinamente sobreposta, como os anéis do radar.

## Novas telas e Figma

Para telas existentes, consultar o frame específico com Figma MCP e executar `get_design_context`; o React/Tailwind retornado serve somente de referência. Converter para React Native, reutilizar tokens/componentes, normalizar inconsistências, não recriar a status bar e versionar localmente qualquer asset real necessário. Telas novas seguem o mesmo sistema.
