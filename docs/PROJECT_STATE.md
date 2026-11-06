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
