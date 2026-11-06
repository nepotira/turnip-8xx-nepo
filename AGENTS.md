# AGENTS.md — Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) Patch Stack
> Manual de operação para agentes de IA. Curto de propósito: o detalhe está em `docs/` e `.agents/rules/`.

## Projeto
Stack modular de patches e CI para compilação do driver Vulkan Mesa Turnip otimizado para GPUs Qualcomm Adreno 8xx (com foco no Snapdragon 8s Gen 4 / `Adreno 825`) · Stack: C/C++20, Python 3, Meson/Ninja, Android NDK r29, GitHub Actions · Dono: `nepotira` · Licença: `MIT` (SPDX)

## Perfil do projeto (o agente adapta o rigor e as ferramentas a isto)
- Tipo: driver gráfico user-space (Vulkan ICD / AdrenoTools `.zip`) + automação de patches sobre Mesa 3D
- Equipe: solo
- Risco de ações: baixo no repositório; médio no dispositivo alvo (driver Vulkan user-space carregado via AdrenoTools)
- Distribuição: público (código, relatórios, patches e binários `.zip` via GitHub Releases) · Dados pessoais: não
- Plataforma de trabalho atual: Linux (`aarch64`/`x86_64`) com compilação remota via GitHub Actions (`ubuntu-latest` + Android NDK r29)
- Compilação: GitHub Actions via `gh` (`build-turnip.yml`)

## Comandos (manter sempre verdadeiros)
- Instalar: `não aplicável (compilado via CI sobre Mesa main)`
- Rodar: `python3 scripts/apply_all_patches.py --mesa-dir ./mesa-src --variant sustained`
- Testar: `python3 scripts/verify_patch_stack.py`
- Lint: `python3 -m py_compile scripts/*.py`
- Build: `gh workflow run build-turnip.yml --ref "$(git branch --show-current)" -f variant=all`

## Regras essenciais
1. Início de sessão: ler este arquivo, `docs/PROJECT_STATE.md`, último handoff, `git status -sb`, `git log --oneline -10`.
2. Um ramo por tarefa: `tipo/NN-descricao-curta`. Nunca commitar direto na `main` (exceto o 1º commit).
3. Commits: Conventional Commits `tipo(escopo)!: descrição` (até 72 caracteres, imperativo, em inglês), atômicos. Rodapés: `Refs: #N`, `BREAKING CHANGE: ...`, `Assisted-by: <agente/modelo>`.
4. Versão: SemVer 2.0.0. Fonte única: `VERSION`. Tag anotada `vX.Y.Z`.
5. Toda mudança atualiza `CHANGELOG.md [Unreleased]` e `docs/JOURNAL.md`; mudou o estado → `docs/PROJECT_STATE.md`.
6. Decisão arquitetural, de tecnologia ou de licença → ADR em `docs/adr/`.
7. "Pronto" = testes/build rodados e evidência registrada (sem evidência em hardware real, escrever `not tested`).
8. Segredos nunca no repositório. `GEMINI.md` local permanece ignorado no `.gitignore` (nunca subir para público).
9. Ação destrutiva = backup + explicação + confirmação. Instalar ferramenta = perguntar antes.
10. Compilar via GitHub Actions com `gh` e monitorar até o fim; local só em último caso, com o motivo registrado.
11. Licenças: todo código novo segue a licença `MIT` (compatível com Mesa 3D); terceiros e créditos em `THIRD_PARTY_LICENSES.md` e `NOTICE`.
12. Antes de parar ou trocar de agente: `/handoff`. Ao chegar: `/retomar`.
13. Passo a passo para o usuário sempre com o COMO (caminho, clique/toque, comando completo).
14. Proibição absoluta de suposições técnicas: NUNCA declarar causas-raiz de falhas gráficas, bugs de driver ou limites de hardware sem inspeção direta e comprovada no código real do Mesa, kernel KGSL e emulador. É terminantemente proibido chutar números, registradores ou limites de buffer sem conferência no código-fonte real.

## Regras locais deste projeto
- O arquivo `GEMINI.md` na raiz local fica apenas na pasta local e está listado no `.gitignore` para nunca ser publicado.
- Jamais aplicar `offset -= 0x78000` em `fd6_gmem_cache.h` nem `supports_double_threadsize = True` em `a8xx_base`.
- Toda alteração nas frações CCU do `Adreno 825` (`0x44030000`) e `Adreno 829` (`0x44030a20`) deve preservar a invariante matemática `RB_CCU_CACHE_CNTL == bytes subtraídos` e `tile_align_w = 64` / `tile_max_w = 16384`.

## Mapa da documentação
`README.md` · `RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md` · `PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md` · `CONTRIBUTING.md` · `SECURITY.md` · `LICENSE` · `NOTICE` · `THIRD_PARTY_LICENSES.md` · `CHANGELOG.md` · `docs/` (PROJECT_STATE, REQUIREMENTS, ARCHITECTURE, RUNBOOK, TESTING, TROUBLESHOOTING, GLOSSARY, JOURNAL, RETROFIT, LICENSING, ENVIRONMENT) · `docs/adr/` · `docs/handoffs/`

## Nunca
- Afirmar, deduzir ou declarar causas de bugs ou limites de hardware por especulação teórica sem ler o código-fonte real correspondente.
- Reescrever histórico publicado, mexer em tag publicada ou apagar branch sem pedido explícito.
- Adicionar dependência sem registrar motivo e licença.
- Ampliar o escopo além da tarefa aprovada.
- Publicar arquivo proprietário (ROM, firmware, blob proprietário Qualcomm `vulkan.adreno.so`) no repositório.
