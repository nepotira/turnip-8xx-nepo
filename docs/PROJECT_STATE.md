# Estado do Projeto — Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) Patch Stack

- **Versão atual:** `v0.2.5`
- **Repositório público:** `https://github.com/nepotira/turnip-8xx-nepo`
- **Fase atual:** Implementação comprovada das correções de arquitetura do Adreno 825 e do driver Turnip (correção da invariante matemática de CCU fraction/offset no Adreno 825 eliminando corrupção de GMEM/depth e novo patch 63 expandindo framebuffer/window scissor para eliminar o corte de 65% de tela preta em 2160p/Nyushu).
- **Ramo ativo:** `fix/09-a825-ccu-math-and-2160p-viewport`
- **Status de verificação:**
  - `python3 scripts/verify_patch_stack.py`: **VERIFICADO (PASS)**.
  - Testes em árvore real Mesa 3D (`.scratch/mesa-src`): As 4 variantes (`biggmem`, `sustained`, `maxperf`, `switch2`) aplicam 100% dos patches cleanly sem conflito.
  - Correção matemática exata de frações CCU em `scripts/apply_all_patches.py` e `scripts/verify_patch_stack.py`.
  - Novo patch `patches/63-tu-framebuffer-attachment-extent-guard.py` implementado em `tu_device.cc` e `tu_cmd_buffer.cc`.

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
