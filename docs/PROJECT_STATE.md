# Estado do Projeto — Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) Patch Stack

- **Versão atual:** `v0.2.6`
- **Repositório público:** `https://github.com/nepotira/turnip-8xx-nepo`
- **Fase atual:** Implementação da versão `v0.2.6` com desacoplamento de DT_SONAME para `vulkan.nepo.so` (eliminando colisão de biblioteca com o HWUI do Android), suporte a Depth Blit Scaling (`BLIT_DST_BIT` em formatos de profundidade `D32_SFLOAT`, `D24_UNORM_S8_UINT`, `D16_UNORM`) para escala 2160p/4K e suporte driconf universal para todos os emuladores de Switch (Nyushu, Eden Nepo, Citron, Yuzu, Sudachi, Suyu, Ryujinx, Uzuy).
- **Ramo ativo:** `fix/10-vulkan-nepo-so-and-depth-blit`
- **Status de verificação:**
  - `python3 scripts/verify_patch_stack.py`: **VERIFICADO (PASS)** (18 patches Git, 14 patches Python, u_gralloc_aimapper.c).
  - Testes em árvore real Mesa 3D (`.scratch/mesa-src`): Novo patch `patches/64-tu-depth-blit-features.py` aplica cleanly e com idempotência.
  - CI Workflow atualizado para empacotar `vulkan.nepo.so` com `patchelf --set-soname vulkan.nepo.so` e `minApi: 30`.

- **Release publicada:** [v0.2.5](https://github.com/nepotira/turnip-8xx-nepo/releases/tag/v0.2.5) (Build CI GitHub Actions Run [42220390281](https://github.com/nepotira/turnip-8xx-nepo/actions/runs/42220390281)).

### Checksums dos Binários v0.2.5 (AdrenoTools .zip)
| Arquivo | SHA256 |
| :--- | :--- |
| `Turnip-A8xx-8sGen4-BigGMEM-v0.2.5-1991790a.zip` | `21e136203dac8d713f178395636ed5d42bf6128ab80f2ca68bd8e5762e0e9dc7` |
| `Turnip-A8xx-8sGen4-MaxPerf-v0.2.5-1991790a.zip` | `29851afe8088f14382cf86d8b42a43f9b722b0b21e89790cbb1d1d1786775eea` |
| `Turnip-A8xx-8sGen4-Sustained-v0.2.5-1991790a.zip` | `593f2b9915bcb71db4183a81c799fca763fae028362737226bb69fed5c7722cf` |
| `Turnip-A8xx-8sGen4-Switch2-v0.2.5-1991790a.zip` | `1ae6acb69c8f01b97f2ba3718f80bbe1385bf40c82e8e283a9edf47e3319a63d` |


## Entregáveis Concluídos
1. [RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md) — Auditoria completa da arquitetura `Adreno 8xx` e 25+ forks comunitários.
2. [PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md) — Plano de implementação em 4 camadas e matriz de triagem.
3. [RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md) — Análise do `eden-android-optimizations`, causa do glitch esbranquiçado de Mario Odyssey, mitigação de stutters de shader, aceleração radical de compilação, bugs de áudio/vídeo em cutscenes e DLSS 5.
4. [RELATORIO_HOGWARTS_MK11_ADRENO8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_HOGWARTS_MK11_ADRENO8XX.md) — Engenharia de correção e otimização para Hogwarts Legacy e Mortal Kombat 11 em suas versões de Nintendo Switch e PC.
5. [PLANO_EXECUCAO_SOLUCOES_RELATORIO_7_8.md](file:///home/nepo/Downloads/TURNIP/PLANO_EXECUCAO_SOLUCOES_RELATORIO_7_8.md) — Plano expandido de execução técnica das demandas 1, 2, 3 e 4.
6. [docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md](file:///home/nepo/Downloads/TURNIP/docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md) e [patches/eden-optimizations-unified.patch](file:///home/nepo/Downloads/TURNIP/patches/eden-optimizations-unified.patch) — Guia de transplante e patch unificado contendo 100% das otimizações do Eden para migração em qualquer nova base.
7. Orquestrador atualizado [scripts/apply_all_patches.py](file:///home/nepo/Downloads/TURNIP/scripts/apply_all_patches.py) com 10 scripts Python e suporte a 4 variantes (`sustained`, `biggmem`, `maxperf`, `switch2`).
8. Workflow de compilação [.github/workflows/build-turnip.yml](file:///home/nepo/Downloads/TURNIP/.github/workflows/build-turnip.yml) compilando as 4 variantes com Android NDK r29.
