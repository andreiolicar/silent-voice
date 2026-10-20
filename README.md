# Silent Voice Site

Landing page do Silent Voice, versão `0.1.0`, desenvolvida com React 19, TypeScript, Tailwind CSS 4, Vite e Motion for React. A interface usa Inter Variable local e assets em `public/`.

O escopo atual é desktop, com largura mínima de **1280 px**. A composição mobile ainda está pendente. Este repositório contém a apresentação do produto; a visualização do dispositivo e as telas do aplicativo são demonstrações visuais.

## Executar e validar

Requer Node.js **24 LTS** e npm.

```sh
npm ci
npm run dev:api # em um terminal
npm run dev     # em outro terminal
```

Abra o endereço informado pelo Vite. O servidor de desenvolvimento usa `127.0.0.1`.

```sh
npm test
npm run build
npm run preview
```

`npm test` mantém os testes de cards/dispositivo/abertura e inclui chat, OpenUI, captura de interesse e administração. `npm run build` gera o SVG da abertura, valida TypeScript e cria `dist/`. `npm run preview` serve esse build localmente. Para conferir somente os tipos, use `npm run typecheck`.

## Interface atual

- Header, hero e faixa “Silent Voice em números”.
- Comunicação assistiva com dispositivo em camadas: clicar nas peças, ou usar Enter/Espaço com o controle focado, alterna abertura e fechamento. Um novo acionamento durante a animação inverte o movimento. Quando aberto, passar o mouse sobre as placas mostra seus nomes.
- Apresentação do aplicativo com composição do celular e tela de conexão.
- Três cards para quem usa, quem cuida e o dia a dia, com ilustrações animadas.
- FAQ com sete perguntas independentes; a primeira inicia aberta. Card de contato e rodapé com navegação, contato e links para perguntas aos provedores de IA.

As duas miniaturas de vídeo são prévias visuais, ainda sem vídeo ou ação de reprodução. Contato abre `mailto:contato@silentvoice.com.br`. Os destinos ficam em `src/site-links.ts`: Institucional, Serviços, Investimento, Participe, Saiba mais, Falar com especialista, redes sociais, Termos e Privacidade ainda aguardam URLs. Controles sem destino recebem `aria-disabled="true"`, permanecem focáveis e não executam ações.

## Abertura e animações

Uma abertura com SVG e CSS aparece antes do React. `public/intro-bootstrap.js` coordena a espera por fontes e imagens do hero, a saída da cobertura e os limites de tempo. Tab, Escape ou foco por teclado encerram a abertura; movimento reduzido a dispensa.

`scripts/generate-intro-logo.mjs` deriva o SVG dos assets originais da marca e atualiza `src/intro/intro-logo.svg` e o trecho correspondente de `index.html`. É executado automaticamente antes do build e também pode ser chamado com `npm run generate:intro`.

Motion coordena as entradas e a interação do dispositivo. Os ciclos dos cards e a sequência do dispositivo suspendem quando saem da área visível ou a aba fica oculta. A interface respeita `prefers-reduced-motion`, mantém foco visível e oferece um link para pular ao conteúdo.

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `src/App.tsx` e `src/LandingPage.tsx` | Rotas e composição preservada da landing. |
| `src/components/` | Seções, controles compartilhados, cards e dispositivo interativo. |
| `src/styles/` e `src/entrance.ts` | Tokens, tipografia, estilos globais e entradas compartilhadas. |
| `src/intro/` e `public/intro-bootstrap.js` | SVG, CSS e coordenação da abertura. |
| `src/site-links.ts` e `src/footer-content.ts` | Destinos e conteúdo dos links. |
| `public/assets/` | Imagens e SVGs servidos pelo site, incluindo as camadas WebP do dispositivo. |
| `scripts/` | Gerador do SVG e testes automatizados. |

## Assets e produção offline

O build publicado reúne o código de `src/`, `index.html` e os arquivos de `public/`. Fontes e imagens usadas pela interface são locais; o build não depende de URLs temporárias do Figma ou de ferramentas de renderização.

As fontes editáveis das mídias, capturas e registros de produção em `docs/reference/`, assim como os planos em `docs/superpowers/`, permanecem preservados na cópia local e ficam fora do Git. Não serão enviados ao GitHub. Reproduzir essas mídias pode exigir Blender, cwebp, FFmpeg e Python com Pillow/NumPy, conforme o processo utilizado. Esses programas e registros não são necessários para instalar, testar ou compilar o site.

`tools/` e `.superpowers/` também são locais e ignorados. Dependências, builds, backups, logs e caches ficam fora do versionamento: instale `node_modules/` com `npm ci` e gere `dist/` com `npm run build`.

## Chatbot e backoffice

Assistente fixo no canto inferior direito, com GLM-4.5-Flash da Z.ai no servidor e respostas visuais em OpenUI, seguindo os tokens atuais. Contatos são gravados em PostgreSQL no Neon e consultados em `/admin`, com login obrigatório no servidor. Não há usuário/senha padrão.

Leia [setup, administração, limites e backup](docs/chatbot-backoffice.md). A chave Z.ai (`ZAI_API_KEY`) é configurada somente no `.env` do servidor; sem ela, contato e administração continuam disponíveis. Não há persistência de transcrição completa.

Código: `src/features/chatbot/`, `src/features/admin/`, `server/` e contratos em `shared/`. A API de desenvolvimento usa porta 3001, com proxy pelo Vite5173. Esta entrega não inclui publicação.
