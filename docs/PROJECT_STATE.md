# Estado do Projeto — Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) Patch Stack

- **Versão atual:** `v0.2.6`
- **Repositório público:** `https://github.com/nepotira/turnip-8xx-nepo`
- **Fase atual:** Implementação da versão `v0.2.6` com desacoplamento de DT_SONAME para `vulkan.nepo.so` (eliminando colisão de biblioteca com o HWUI do Android), suporte a Depth Blit Scaling (`BLIT_DST_BIT` em formatos de profundidade `D32_SFLOAT`, `D24_UNORM_S8_UINT`, `D16_UNORM`) para escala 2160p/4K e suporte driconf universal para todos os emuladores de Switch (Nyushu, Eden Nepo, Citron, Yuzu, Sudachi, Suyu, Ryujinx, Uzuy).
- **Ramo ativo:** `fix/10-vulkan-nepo-so-and-depth-blit`
- **Status de verificação:**
  - `python3 scripts/verify_patch_stack.py`: **VERIFICADO (PASS)** (18 patches Git, 14 patches Python, u_gralloc_aimapper.c).
  - Testes em árvore real Mesa 3D (`.scratch/mesa-src`): Novo patch `patches/64-tu-depth-blit-features.py` aplica cleanly e com idempotência.
  - CI Workflow atualizado para empacotar `vulkan.nepo.so` com `patchelf --set-soname vulkan.nepo.so` e `minApi: 30`.

- **Release publicada:** [v0.2.6](https://github.com/nepotira/turnip-8xx-nepo/releases/tag/v0.2.6) (Build CI GitHub Actions Run [42295905061](https://github.com/nepotira/turnip-8xx-nepo/actions/runs/42295905061)).

### Checksums dos Binários v0.2.6 (AdrenoTools .zip)
| Arquivo | SHA256 |
| :--- | :--- |
| `Turnip-A8xx-8sGen4-BigGMEM-v0.2.6-8fc45e20.zip` | `c7c469bd831146d5c82b97df671e0c463d52d9b5f09a5c05f773c0c4239918c7` |
| `Turnip-A8xx-8sGen4-MaxPerf-v0.2.6-8fc45e20.zip` | `5b21f7aa1c912afe6529e5add066b723dfefaf0723e9b3160e48e8d6a54520be` |
| `Turnip-A8xx-8sGen4-Sustained-v0.2.6-8fc45e20.zip` | `5a4925951897640f8824cc2f6f59c18c49e218395e36c6b71f965a93266bb61e` |
| `Turnip-A8xx-8sGen4-Switch2-v0.2.6-8fc45e20.zip` | `01a7db55aac68fa38775306c0c523abc5436edb26bfb45b6ea336c3b9ab0af13` |


## Entregáveis Concluídos
1. [RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md) — Auditoria completa da arquitetura `Adreno 8xx` e 25+ forks comunitários.
2. [PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md) — Plano de implementação em 4 camadas e matriz de triagem.
3. [RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md) — Análise do `eden-android-optimizations`, causa do glitch esbranquiçado de Mario Odyssey, mitigação de stutters de shader, aceleração radical de compilação, bugs de áudio/vídeo em cutscenes e DLSS 5.
4. [RELATORIO_HOGWARTS_MK11_ADRENO8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_HOGWARTS_MK11_ADRENO8XX.md) — Engenharia de correção e otimização para Hogwarts Legacy e Mortal Kombat 11 em suas versões de Nintendo Switch e PC.
5. [PLANO_EXECUCAO_SOLUCOES_RELATORIO_7_8.md](file:///home/nepo/Downloads/TURNIP/PLANO_EXECUCAO_SOLUCOES_RELATORIO_7_8.md) — Plano expandido de execução técnica das demandas 1, 2, 3 e 4.
6. [docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md](file:///home/nepo/Downloads/TURNIP/docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md) e [patches/eden-optimizations-unified.patch](file:///home/nepo/Downloads/TURNIP/patches/eden-optimizations-unified.patch) — Guia de transplante e patch unificado contendo 100% das otimizações do Eden para migração em qualquer nova base.
7. Orquestrador atualizado [scripts/apply_all_patches.py](file:///home/nepo/Downloads/TURNIP/scripts/apply_all_patches.py) com 10 scripts Python e suporte a 4 variantes (`sustained`, `biggmem`, `maxperf`, `switch2`).
8. Workflow de compilação [.github/workflows/build-turnip.yml](file:///home/nepo/Downloads/TURNIP/.github/workflows/build-turnip.yml) compilando as 4 variantes com Android NDK r29.
