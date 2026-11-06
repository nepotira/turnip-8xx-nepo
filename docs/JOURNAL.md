# Diário do Projeto (`JOURNAL.md`)

## 2026-11-06 — Investigação Profunda, Auditoria de 25+ Forks e Criação da Stack Híbrida v0.1.0
- **Contexto:** O diretório `/home/nepo/Downloads/TURNIP` iniciou em `2026-11-05` / `2026-11-06` como área de pesquisa sobre a baixa performance e instabilidade dos drivers para GPUs Adreno 8xx (especialmente o Snapdragon 8s Gen 4 / `Adreno 825`). *(registro retroativo: fato ocorrido em 2026-11-06 00:18–01:50; reconstruído em 2026-11-06; confiança alta; evidência: timestamps stat de `RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md` e `PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md` e histórico desta sessão).*
- **Ações Realizadas:**
  1. Elaboração do `RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md` e do `PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md`.
  2. Clonagem e auditoria de código de mais de 25 repositórios e forks comunitários de Turnip (`whitebelyash`, `WinNative-Emu`, `Leb-Sun`, `The412Banner`, `DiskDVD`, `WinterMist010`, `Droid-VM`, `faux123`, `Vauzi-17`, `sherft2607`, `MrPurple666`, `AlexSanz0902`, `Balemuni`, `Frane12`, `s1mptom`, etc.).
  3. Adoção das regras de desenvolvimento (`bootstrap-projeto.sh`), mantendo `GEMINI.md` apenas localmente via `.gitignore` conforme orientação do usuário.
  4. Implementação da pilha modular de patches (`patches/` + `scripts/apply_all_patches.py`) e workflow GitHub Actions (`.github/workflows/build-turnip.yml`) para as 3 variantes (`Sustained`, `BigGMEM`, `MaxPerf`).
- **Status de Testes:** Scripts e invariantes matemáticas verificados localmente; execução do binário em dispositivo físico: `not tested`.
