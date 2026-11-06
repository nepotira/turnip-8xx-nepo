# Diário do Projeto (`JOURNAL.md`)

## 2026-11-06 — Implementação dos Patches 58 e 59 (Conservative Rast e Coalescência UBO no IR3 para Adreno 825) (v0.2.2)
- **Contexto:** Aplicação das soluções restantes detalhadas no Plano de Implementação e no Relatório Técnico:
  1. Patch 58 (`58-a8xx-conservative-rast.py`): Expansão da rasterização conservadora para binning com FDM / VRS em `CHIP >= A7XX`.
  2. Patch 59 (`59-a8xx-ir3-coalesce-ubo-push-ranges.py`): Coalescência de UBO push ranges ativada para o Adreno 825 (`0x44030000` / `0xffff44030000`) e Adreno 829 (`0x44030a20`) no compilador IR3, minimizando leituras na DRAM lenta de 3200 MHz.
- **Evidências:** `verify_patch_stack.py` aprovou 18 patches + 12 scripts Python e todas as invariantes. Compilação no GitHub Actions executada para todas as 4 variantes.

## 2026-11-06 — Implementação dos Patches 56/57, Aceleração de Shaders, Correção de Cutscenes, Análise de Hogwarts/MK11 no Switch e Guia de Transplante do Eden (v0.2.1)
- **Contexto:** Atendimento das novas demandas do usuário:
  1. Análise profunda e correções para Hogwarts Legacy e Mortal Kombat 11 em suas edições nativas de Nintendo Switch no emulador (Eden/Citron/Yuzu), mantendo as análises de PC intactas.
  2. Pesquisa profunda e técnicas para acelerar a VELOCIDADE de compilação de shaders para acompanhar o ritmo do jogo sem derrubar o FPS.
  3. Diagnóstico forense dos bugs de áudio crackelado e macroblocking de vídeo em cutscenes (caso clássico: Mario Odyssey na nave do Bowser com a Peach).
  4. Garantia e documentação para transplantar 100% de todas as funções implementadas no Eden (`nepotira/eden-android-optimizations`) para qualquer nova base de emulador.
- **Decisões tomadas:**
  - Criação do patch `patches/56-a8xx-shader-perf-and-compilation.py` com fast-path wave sizing e inibição de zeramento redundante de memória scratch.
  - Criação do patch `patches/57-a8xx-switch2-dlss-extensions.py` expondo `VK_KHR_shader_integer_dot_product` (`DP4a`) e `VK_KHR_shader_float16_int8` para aceleração matricial de tensores no Adreno 8xx.
  - Expansão dos relatórios `RELATORIO_HOGWARTS_MK11_ADRENO8XX.md` e `RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md` com as novas seções de Switch e cutscenes.
  - Criação do `docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md` e do patch unificado `patches/eden-optimizations-unified.patch` contendo 100% das modificações (NEON SIMD, frame pacing sleep e cache flush de 120s).
  - Atualização do orquestrador `scripts/apply_all_patches.py` e da suíte `scripts/verify_patch_stack.py`.
- **Evidências de verificação:**
  - `python3 scripts/verify_patch_stack.py` aprovou 18 patches + 10 scripts Python + módulo aimapper + todas as invariantes de GMEM.
  - `python3 -m py_compile` em todos os scripts Python executou com sucesso (código 0).

## 2026-11-06 — Implementação da Variante Switch 2, Relatórios Forenses e Otimização para Shaders e Jogos Pesados (v0.2.0)
- **Contexto:** Após os testes em hardware real no Snapdragon 8s Gen 4 confirmarem que a nossa build superou com folga o Turnip v38 e o MrPurple v30 (com `BigGMEM` em 1º lugar, `Sustained` em 2º e `Performance` em 3º), o usuário solicitou:
  1. Análise forense de `nepotira/eden-android-optimizations` para explicar o fim do glitch esbranquiçado de Super Mario Odyssey.
  2. Diagnóstico das quedas abruptas de FPS na compilação/renderização de shaders.
  3. Adição de camada de compatibilidade e desempenho para emulação de Switch e do futuro Switch 2 (T239/NVN2).
  4. Suporte nativo/arquitetura para DLSS 5 / IA upscaling via `VK_KHR_cooperative_matrix`.
  5. Relatórios técnicos aprofundados sobre a engenharia do Eden + Turnip e as correções para Hogwarts Legacy e Mortal Kombat 11.
- **Decisões tomadas:**
  - Criação da variante `Turnip-A8xx-8sGen4-Switch2` (`-s2`) com 752 KB de GMEM, suporte a VRS (`has_attachment_shading_rate`), Mesh Shaders via compute e histerese balanceada de SP.
  - Injeção de perfis de otimização em `00-turnip-defaults.conf` para emuladores de Switch (`eden`, `yuzu`, `citron`, `sudachi`, `suyu`, `ryujinx`), Hogwarts Legacy (forçando `prefer_sysmem` e OOB UBO) e Mortal Kombat 11 (ativando emulação de alpha-to-coverage para eliminar grid lines).
  - Elaboração dos relatórios `RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md` e `RELATORIO_HOGWARTS_MK11_ADRENO8XX.md`.
- **Evidências de verificação:**
  - `python3 scripts/verify_patch_stack.py` executado com sucesso validando todas as 4 variantes.
  - Testes do usuário em hardware real: BigGMEM #1, Sustained #2, Performance #3.

## 2026-11-06 — Adoção de regras, estruturação da stack v0.1.0 e compilação no GitHub Actions
- **Contexto:** Adoção de regras e publicação no GitHub (`nepotira/turnip-8xx-nepo`).
- **Evidências:** Compilação das variantes `Sustained`, `BigGMEM` e `MaxPerf` no GitHub Actions (`Run 42168099249`) concluída com 100% de sucesso.
