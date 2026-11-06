# Estado do Projeto — Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) Patch Stack

- **Versão atual:** `v0.2.0`
- **Repositório público:** `https://github.com/nepotira/turnip-8xx-nepo`
- **Fase atual:** Implementação da 4ª variante (`Turnip-A8xx-8sGen4-Switch2` / `-s2`), perfis driconf para emulação de Switch, Hogwarts Legacy e MK11, e relatórios técnicos aprofundados.
- **Ramo ativo:** `main`
- **Status de verificação:**
  - `python3 scripts/verify_patch_stack.py` (validação sintática e matemática de offsets GMEM/CCU para 1 MB nas variantes `Sustained`, `BigGMEM`, `MaxPerf` e `Switch2`): **VERIFICADO (PASS)**.
  - Testes em hardware físico (`SM8735` / `POCO F7` com `Adreno 825`):
    - Confirmação de benchmark informada pelo usuário: **BigGMEM em 1º lugar**, **Sustained em 2º lugar**, **Performance em 3º lugar**.
    - Desempenho significativamente superior ao Turnip V38 e MrPurple v30.
    - Glitch esbranquiçado de *Super Mario Odyssey* corrigido com sucesso no `nepotira/eden-android-optimizations` (desentrelaçamento ARM NEON SIMD + fim do spin-wait de CPU).

## Entregáveis Concluídos
1. [RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md) — Auditoria completa da arquitetura `Adreno 8xx` e 25+ forks comunitários.
2. [PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md) — Plano de implementação em 4 camadas e matriz de triagem.
3. [RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md) — Análise do `eden-android-optimizations`, causa do glitch esbranquiçado de Mario Odyssey, mitigação de stutters de shader, arquitetura do Switch 2 (T239/NVN2) e DLSS 5 via Cooperative Matrix.
4. [RELATORIO_HOGWARTS_MK11_ADRENO8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_HOGWARTS_MK11_ADRENO8XX.md) — Engenharia de correção e otimização para Hogwarts Legacy (DX12) e Mortal Kombat 11 (DX11) na Adreno 8xx.
5. Orquestrador atualizado [scripts/apply_all_patches.py](file:///home/nepo/Downloads/TURNIP/scripts/apply_all_patches.py) com suporte a 4 variantes (`sustained`, `biggmem`, `maxperf`, `switch2`) e injeção de perfis driconf.
6. Workflow de compilação [.github/workflows/build-turnip.yml](file:///home/nepo/Downloads/TURNIP/.github/workflows/build-turnip.yml) com a nova variante `Switch2`.
