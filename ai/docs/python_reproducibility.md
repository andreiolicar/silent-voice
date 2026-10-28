# Python reproduzível — Live Tester C4.4

O arquivo `requirements-live-tester-win-cp312.lock` fixa, com SHA-256 de
wheels, as dependências diretas e transitivas do runtime visual e dos testes
(`live-tester` e `dev`), em Windows x86-64 com CPython 3.12.10. O lock não
cobre os extras opcionais `audio`, `training` ou `pretrained` como conjuntos
completos. A versão fixada de PyTorch é a distribuição CPU local.

Em um ambiente com um conjunto autorizado de wheels, apontado pela variável `SV_WHEELHOUSE`, que corresponda aos
hashes do lock, a instalação offline em uma virtualenv nova é:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links $env:SV_WHEELHOUSE --require-hashes -r requirements-live-tester-win-cp312.lock
.\.venv\Scripts\python.exe -m pip install --no-index --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

Os wheels não integram este repositório. Seu fornecimento deve respeitar suas
fontes e licenças. Disponibilidade futura em índices públicos e instalação por
rede não foram verificadas; o PyTorch CPU pode exigir índice autorizado próprio.
Sem os wheels corretos o pip deve falhar a verificação de hash.

A validação desta migração instalou os 51 pacotes fixados a partir de cache
local, sem rede, em uma virtualenv isolada, e instalou uma cópia pública do
projeto em modo editável. A suíte do diretório `ai/` teve 142 PASS e 3 SKIP:
os três documentos privados opcionais não estavam presentes em `ai/`. Foram
observados dois avisos de depreciação do `google._upb`. Os testes GV2.9 com
symlink real não fazem parte deste recorte e não foram declarados PASS.

A comparação operacional usou duas entradas de desenvolvimento existentes e
artefatos privados locais autorizados. O código original e o migrado produziram
scores e decisões GLOBAL e PERSONALIZED iguais nas entradas avaliadas; hashes
dos tensores nas chamadas dos modelos e as distâncias DTW também coincidiram.
O runtime migrado utilizou o diretório de origem como raiz de leitura dos
artefatos privados; os oito hashes de implementação R4 foram conferidos no
próprio `ai/`. Isso não valida a disponibilização dos artefatos em uma máquina
nova, desempenho em novos usuários, hardware ou integração com aplicativo.

Os manifestos privados e modelos devem ser obtidos de armazenamento autorizado
e não devem ser versionados. A lista de dependências privadas e sua verificação
estão em `c44_live_tester_reproducibility.md`. O congelamento e o manifesto de
migração originais permanecem inalterados.
