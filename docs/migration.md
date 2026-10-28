# Consolidação dos repositórios — 27/10/2026

Destino: `andreiolicar/silent-voice`. Importações com `git subtree add`, **sem squash**, preservando commits e autores:

| Origem | Referência importada | Destino inicial |
| --- | --- | --- |
| silent-voice | `ad50641019cff2744eb4d60e2c24d8d790f4e600` | histórico legado |
| silent-voice-site | `f6d4c9c714a182e3873f60ddc405f9d0fdb8cf4d` | `apps/site` antes da separação |
| silent-voice-mobile | `15b0f24` + working tree local | `apps/mobile` |

O commit `6d9d8d9` preserva o snapshot dos 172 arquivos publicáveis do mobile, incluindo alterações ainda não commitadas na origem. Os clones de origem não foram modificados. Manifestos privados SHA256 comprovaram a igualdade dos arquivos no snapshot. Os três heads originais são ancestrais do monorepo.

Em seguida API e admin foram separados e contratos/UI compartilhados extraídos. Os três arquivos SQL de migração permanecem byte a byte iguais à origem; esta mudança não modifica esquema ou dados.

Os PDFs antigos foram removidos da árvore atual, mas continuam acessíveis nos commits anteriores. A marca original está em `assets/brand`. Dados privados, backups, fontes pesadas de mídia e segredos não foram importados.

Após a publicação e conferência dos dois serviços, `silent-voice-site` e `silent-voice-mobile` foram arquivados reversivelmente, com suas descrições apontando para este monorepo. Não havia PRs ou issues abertos nessas origens. Para contribuir, clone o destino e abra uma branch nova; não continue fazendo pushes nos repositórios antigos. `CODEOWNERS` ajuda a encaminhar revisões, sem impor isolamento de leitura/escrita por pasta.
