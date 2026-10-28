# Arquitetura

Os apps são unidades de execução distintas. `site` entrega a apresentação pública; `admin` entrega `/admin/*` e `/conta/*`; ambos consomem `/api/*`. `infra/build-web.mjs` combina os builds em `dist/` e `dist/admin/`, sem misturar os diretórios de assets. A publicação continua usando dois serviços gratuitos: um static site e uma API. O banco fica no Neon.

Better Auth é a única autoridade de identidade. O cadastro público cria `user`; CRM exige `admin`, e-mail confirmado e 2FA. O aplicativo usa o mesmo servidor com armazenamento nativo seguro. Detalhes em [autenticação](authentication.md).

`contracts` contém DTOs e o contrato visual OpenUI. `web-ui` reúne somente controles/estilos realmente usados pelos dois clientes web; `http-client` contém a política compartilhada de disponibilidade. Não há compartilhamento de componentes DOM com React Native.

O núcleo de reconhecimento será incorporado em `ai` pelo João, com ambiente e testes próprios. Não existe dependência fictícia dele na API do site. [Limites de hardware do mobile](../apps/mobile/AGENTS.md) continuam valendo.

## Dependências

Npm workspaces com instalação `hoisted`. A raiz fixa React/React DOM 19.2.3 como âncora de desenvolvimento do runtime nativo; os frontends web mantêm React 19.3 nos seus próprios workspaces, com deduplicação explícita no Vite. Testes verificam que o renderer e o React Native compartilham a instância do app. Isso evita a duplicação de módulos nativos e peers ausentes observada na instalação nested. Instalações de produção selecionam apenas os workspaces necessários. `legacy-peer-deps` mantém os peers opcionais não usados fora da instalação; os providers efetivamente exigidos pelo Better Auth estão declarados diretamente, em versões iguais às do código de origem.

Não acrescente Turborepo/Nx, ORM ou novos serviços sem necessidade demonstrada. O lockfile raiz é a fonte reproduzível; não execute `npm install` dentro de um app para criar outro lockfile.
