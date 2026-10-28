# Autenticação unificada

Site e aplicativo usam Better Auth 1.7.14, com `@better-auth/expo` na mesma versão, Fastify e PostgreSQL do Neon. Não existe autenticação administrativa paralela. O cadastro público cria somente `user`; a API exige e-mail confirmado, papel `admin` e TOTP confirmado para cada operação do CRM. O formulário de interesse continua criando contatos, sem contas.

## Configuração

Instale com Node 24 e `npm ci`. O flag mantém a instalação reproduzível sem adaptadores/frameworks opcionais do Better Auth. Em produção:

- `DATABASE_URL`: conexão PostgreSQL com pool.
- `DATABASE_URL_UNPOOLED`: conexão direta para migrações e backup.
- `BETTER_AUTH_SECRET`: segredo exclusivo, aleatório, com pelo menos 32 caracteres. Mantê-lo estável; criptografa também os segredos de 2FA.
- `BETTER_AUTH_URL`: `https://www.silentvoice.com.br`.
- `APP_ORIGIN`: o mesmo domínio público. Origens HTTPS adicionais são explícitas, sem wildcard.
- `RESEND_API_KEY`: exclusiva do backend. Não usar prefixos `VITE_` ou `EXPO_PUBLIC_`.
- `AUTH_EMAIL_FROM`: `Silent Voice <conta@silentvoice.com.br>`; esse é o domínio exato criado e verificado pelo proprietário no Resend. Reply-To: `contato@silentvoice.com.br`.

O plano inicial citava `auth.silentvoice.com.br`; a configuração acompanha o domínio raiz que o proprietário criou. Não é necessário criar uma caixa postal para o remetente de envio. Os registros de recebimento existentes não são substituídos. Rastreamento de links não foi habilitado.

O frontend estático mantém o rewrite `/api/*` para o backend antes do fallback SPA. Cookies web são HttpOnly, Secure em produção, SameSite Lax e restritos ao host. Todo `Set-Cookie` retornado pelo framework é preservado, inclusive nos guards do CRM e no fluxo de 2FA. O native usa o plugin Expo/SecureStore e a origem confiável `silentvoicemobile://`.

## Administração

```sh
npm run admin:create -- --email administrador@exemplo.com
```

Comando interno, sem senha por argumento, variável ou log. Provisiona o administrador e envia instruções para definir a senha. Se a conta já for administrativa, reenvia a definição; uma conta comum não é promovida implicitamente. O proprietário define a senha, confirma o e-mail e configura o autenticador no navegador. Antes de concluir TOTP, somente a configuração de segurança está disponível.

Senhas têm 12–128 caracteres. Confirmação expira em 24h e recuperação em 1h. Sessões duram sete dias e são renovadas após um dia, com consulta ao banco e sem cache de autorização. Recuperação revoga sessões sem remover 2FA; troca de senha revoga as outras sessões e atualiza a identidade da sessão atual. Configuração/reconfiguração de 2FA revoga todas as sessões e exige novo login. Códigos de recuperação são de uso único, mostrados temporariamente; não são persistidos pela interface.

No Render em produção (`RENDER=true`), os limites usam o endereço do visitante informado em `CF-Connecting-IP`, sobrescrito pela borda Cloudflare da plataforma. Fora desse ambiente, a ponte usa o endereço resolvido pelo Fastify com a política limitada de proxy existente e ignora cabeçalhos Cloudflare do cliente. A ponte entrega um único IP validado ao Better Auth, sem escolher o primeiro item arbitrário de `X-Forwarded-For`. Isso evita tanto o contador global de fallback do SDK quanto o agrupamento por endereço interno do balanceador. Essa configuração pressupõe o ingresso público protegido do Render; não habilitar `RENDER=true` em um servidor exposto diretamente. [Contrato da infraestrutura](https://render.com/articles/how-render-handles-ddos-attacks), [cabeçalho da Cloudflare](https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/).

Login e cadastro continuam limitados a cinco requisições por endereço em uma janela de 15 minutos, incluindo requisições bem-sucedidas. Respostas 429 preservam o limite e informam `Retry-After`/`retryAfterSeconds`; a interface mostra o tempo restante. Uma tentativa já bloqueada não prolonga a janela.

`/admin/seguranca` permite configurar/reconfigurar TOTP, trocar senha, consultar e encerrar sessões. QR Code é gerado localmente. Nenhuma senha, cookie, código, chave ou link secreto é registrado nos logs. Login/cadastro, recuperação, reenvio e códigos possuem limites próprios de tentativas.

## Aplicativo

O onboarding é persistido separadamente. Depois dele, a autenticação protege permissões, conexão, calibração e área interna. O cache nativo contém somente identidade mínima e validade de uma sessão previamente confirmada. Ele libera funcionalidades locais offline, nunca permissões na API. Expiração ou sessão inválida bloqueia acesso; erro de rede preserva apenas um cache válido. Reconexão e retorno ao app revalidam a sessão.

Logout remove o acesso local imediatamente e persiste a intenção antes de aguardar rede. A revogação pendente pertence à sessão antiga e não pode encerrar outra conta. A troca de identidade desmonta estado privado. Operações de segurança enfileiradas pertencem à identidade que as iniciou.

Confirmação e recuperação chegam pelas páginas HTTPS `/conta/email-confirmado` e `/conta/redefinir-senha`. Quando originadas no app, oferecem um destino fixo `silentvoicemobile://auth/...`; parâmetros arbitrários de redirecionamento são ignorados. O fluxo pode ser concluído no navegador. A publicação nas lojas não faz parte desta entrega.

## Migração e retorno

`001` permanece inalterada. O executor aplica SQL numerado em transação, com trava e checksums. `002` cria o esquema gerado pelo Better Auth; `003` importa IDs/e-mails/datas administrativos sem hashes antigos, migra os vínculos das notas/status e encerra sessões legadas. As tabelas antigas permanecem privadas temporariamente.

Antes da publicação, usar backup PostgreSQL privado e testar sua restauração em um banco isolado. O ensaio deve comprovar repetição segura, vínculos e acesso completo com e-mail/2FA. A ferramenta antiga `db:import:sqlite` serve somente para o esquema legado anterior à migração; não deve ser executada no esquema Better Auth.

Em incidente, interromper novas alterações administrativas e voltar frontend/API juntos para a revisão anterior. Preservar o banco atual e os novos usuários/sessões/contatos; não restaurar um dump antigo sobre a produção. Restaurar o backup em uma branch isolada para investigação e recuperação seletiva. Não apagar o esquema novo nem reverter as referências sem conciliar dados criados após a migração. As contas administrativas legadas podem voltar a exigir sua senha anterior durante um retorno temporário.

## Verificação

```sh
npm test
npm run typecheck
npm run build
TEST_DATABASE_URL_FILE=/caminho/privado/url-isolada node --experimental-strip-types --test apps/api/tests/postgres.integration.test.mjs
AUTH_TEST_DATABASE_URL_FILE=/caminho/privado/url-isolada node --experimental-strip-types --test apps/api/tests/unified-auth-migration.test.mjs
```

No mobile: testes, lint, typecheck, formatação, verificação de dependências/Expo Doctor e exportações web/iOS/Android. Exportação não substitui teste nativo. Registre separadamente qualquer falha de simulador, deep link ou dispositivo físico. Nenhuma integração USB nova é introduzida por esta autenticação.
