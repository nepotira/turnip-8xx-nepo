# Estado do Projeto — Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) Patch Stack

- **Versão atual:** `v0.2.4`
- **Repositório público:** `https://github.com/nepotira/turnip-8xx-nepo`
- **Fase atual:** Resolução definitiva da renderização em 2160p (restauração do autotune BANDWIDTH com fallback dinâmico para SYSMEM sem estouro de VSC) e eliminação do esbranquiçado no Adreno 8xx KGSL (`tu_fix_a2_alpha_precision=true` para emuladores e sanitização NIR expandida para compute shaders e image stores).
- **Ramo ativo:** `main`
- **Status de verificação:**
  - `python3 scripts/verify_patch_stack.py` (validação de 18 patches + 12 scripts Python + módulo aimapper + GMEM math): **VERIFICADO (PASS)**.
  - Scratch tests para patches 58 e 60: **PASS**.
  - Testes em hardware físico (`SM8735` / `POCO F7` com `Adreno 825`):
    - Confirmação de benchmark informada pelo usuário: **BigGMEM em 1º lugar**, **Sustained em 2º lugar**, **Performance em 3º lugar**.
    - Desempenho significativamente superior ao Turnip V38 e MrPurple v30.
    - Glitch esbranquiçado de *Super Mario Odyssey* corrigido nativamente no driver Turnip (NIR flush NaN -> 0.0 + fclamp) e no `nepotira/eden-android-optimizations`.
    - Bug de 65% de tela preta no Nyushu resolvido pela remoção de conservative binning em A8XX.
  - Release publicada: [v0.2.4](https://github.com/nepotira/turnip-8xx-nepo/releases/tag/v0.2.4) (Build CI GitHub Actions Run [42203616305](https://github.com/nepotira/turnip-8xx-nepo/actions/runs/42203616305)).

### Checksums dos Binários v0.2.4 (AdrenoTools .zip)
| Arquivo | SHA256 |
| :--- | :--- |
| `Turnip-A8xx-8sGen4-BigGMEM-v0.2.4-35a0fef1.zip` | `92356fc5d274ad6ba44f61a8a8fb7b8fd8043d31d6f4cd2e95c5385160c76a86` |
| `Turnip-A8xx-8sGen4-MaxPerf-v0.2.4-35a0fef1.zip` | `698b22cd9599a97f5b870446f3086831a16087302a083f79f2527f36e1004d13` |
| `Turnip-A8xx-8sGen4-Sustained-v0.2.4-35a0fef1.zip` | `75ff5aac43a45653e04aa0f9f211e2798e44233956c0e64cd283800777407452` |
| `Turnip-A8xx-8sGen4-Switch2-v0.2.4-35a0fef1.zip` | `07f68c275c374864a008cfa9ee2814df605c5fc7caae2d58dc0cee009167c21f` |


## Entregáveis Concluídos
1. [RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md) — Auditoria completa da arquitetura `Adreno 8xx` e 25+ forks comunitários.
2. [PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md) — Plano de implementação em 4 camadas e matriz de triagem.
3. [RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md) — Análise do `eden-android-optimizations`, causa do glitch esbranquiçado de Mario Odyssey, mitigação de stutters de shader, aceleração radical de compilação, bugs de áudio/vídeo em cutscenes e DLSS 5.
4. [RELATORIO_HOGWARTS_MK11_ADRENO8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_HOGWARTS_MK11_ADRENO8XX.md) — Engenharia de correção e otimização para Hogwarts Legacy e Mortal Kombat 11 em suas versões de Nintendo Switch e PC.
5. [PLANO_EXECUCAO_SOLUCOES_RELATORIO_7_8.md](file:///home/nepo/Downloads/TURNIP/PLANO_EXECUCAO_SOLUCOES_RELATORIO_7_8.md) — Plano expandido de execução técnica das demandas 1, 2, 3 e 4.
6. [docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md](file:///home/nepo/Downloads/TURNIP/docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md) e [patches/eden-optimizations-unified.patch](file:///home/nepo/Downloads/TURNIP/patches/eden-optimizations-unified.patch) — Guia de transplante e patch unificado contendo 100% das otimizações do Eden para migração em qualquer nova base.
7. Orquestrador atualizado [scripts/apply_all_patches.py](file:///home/nepo/Downloads/TURNIP/scripts/apply_all_patches.py) com 10 scripts Python e suporte a 4 variantes (`sustained`, `biggmem`, `maxperf`, `switch2`).
8. Workflow de compilação [.github/workflows/build-turnip.yml](file:///home/nepo/Downloads/TURNIP/.github/workflows/build-turnip.yml) compilando as 4 variantes com Android NDK r29.
