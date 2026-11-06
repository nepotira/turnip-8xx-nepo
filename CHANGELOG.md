# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.
O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e este projeto segue [SemVer 2.0.0](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.2.3] - 2026-11-06
### Fixed
- **Correção da tela 65% preta / não renderizada:** Removida a ativação de `tu_binning_conservative_rast` em Adreno 8xx (`58-a8xx-conservative-rast.py`), restaurando estritamente `CHIP == A7XX`. No Adreno 8xx, a rasterização conservadora de binning provocava o corte da bounding box ao tamanho do buffer interno de 720p (`1280x720`) em telas de `2400x1080` (`(1280*720)/(2400*1080) = 35.5%`, resultando em exatamente 64.5% ≈ 65% da tela preta na apresentação).
- **Correção nativa do glitch de elementos esbranquiçados (`patches/60-a8xx-sanitize-frag-nan.py`):** Adicionado passe no compilador NIR/IR3 (`ir3_nir_sanitize_frag_outputs`) durante `ir3_finalize_nir` para sanitizar saídas de cor de fragment shaders float16 e float32. Valores `NaN` (gerados por amostragens de texturas com bordas não inicializadas em emuladores sem o patch SIMD do Eden) são substituídos por `0.0` via `nir_bcsel(nir_fisnan(src), 0.0, src)` e valores infinitos são limitados por `nir_fclamp`, impedindo que estourem em saturação branca pura no hardware Adreno 8xx em passes de névoa volumétrica e bloom (ex.: *Super Mario Odyssey*).
- **Suporte explícito ao emulador Nyushu:** Adicionado `[Nn]yushu` e `org.nyushu` ao perfil `Switch Emulators` no `00-turnip-defaults.conf`, ativando automaticamente `tu_independent_icache_miss`, `tu_autotune_algorithm=prefer_gmem`, `tu_allow_oob_indirect_ubo_loads` e `tu_enable_fast_border_color_for_undefined_formats`.


## [0.2.2] - 2026-11-06
### Added
- **Patch `58-a8xx-conservative-rast.py`:** Ativação de rasterização conservadora para binning com fragment density maps / VRS em `CHIP >= A7XX` (incluindo Adreno 8xx), reduzindo processamento de vértices em passes de sombreamento de taxa variável.
- **Patch `59-a8xx-ir3-coalesce-ubo-push-ranges.py`:** Coalescência de intervalos de push UBO estendida no compilador IR3 para o Adreno 825 (`0x44030000` / `0xffff44030000`) e Adreno 829 (`0x44030a20`), agrupando acessos de Uniform Buffers no arquivo de constantes on-chip e mitigando diretamente o gargalo do barramento de 3200 MHz da memória LPDDR5X.
### Added
- **Patch `56-a8xx-shader-perf-and-compilation.py`:** Fast-path wave sizing e otimização da alocação de scratch memory para acelerar o throughput do compilador de shaders em tempo real.
- **Patch `57-a8xx-switch2-dlss-extensions.py`:** Exposição no Vulkan das extensões `VK_KHR_shader_integer_dot_product` (`DP4a`) e `VK_KHR_shader_float16_int8` para aceleração matricial por hardware de modelos neurais (DLSS 5 / Qualcomm SGSR 2) e emulação de Switch 2 (T239/NVN2).
- **Perfis driconf expandidos:** Cobertura de executáveis de Switch e PC para Hogwarts Legacy (`Phoenix-Win64-Shipping.exe`, `HogwartsLegacy.exe`, `Phoenix`), Mortal Kombat 11 (`MK11.exe`, `MortalKombat11.exe`) e pacotes Android de emuladores (`dev.eden.emulator`, `org.citron.citron_emu`, `org.yuzu.yuzu_emu`).
- **Guia Completo de Transplante de Funções do Eden (`docs/GUIA_TRANSPLANTE_OTIMIZACOES_EMULADOR.md`):** Inventário minucioso de 100% das otimizações adicionadas ao Eden (`decoders.cpp` ARM NEON SIMD, `vk_scheduler.h` sleep pacing, `vk_pipeline_cache.cpp` 120s flush) e patch unificado pronto (`patches/eden-optimizations-unified.patch`) para migração instantânea para qualquer nova base.
- **Pesquisa Aprofundada sobre Hogwarts Legacy e Mortal Kombat 11 no Switch:** Seções dedicadas no `RELATORIO_HOGWARTS_MK11_ADRENO8XX.md` cobrindo as edições de console Nintendo Switch rodando em emuladores na Adreno 8xx.
- **Pesquisa Forense sobre Cutscenes de Mario Odyssey e Velocidade de Shaders:** Seções dedicadas no `RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md` cobrindo esvaziamento de ringbuffer no AAudio (estalos de som) e macroblocking visual na cinemática da nave do Bowser.
### Added
- Variante especializada **`Turnip-A8xx-8sGen4-Switch2` (`-s2`)** focada em emulação de Nintendo Switch e Switch 2 (T239/NVN2), com 752 KB de GMEM, `has_attachment_shading_rate` (VRS), `VK_EXT_mesh_shader` acelerado e calibração de histerese de SP balanceada.
- Perfis de aplicativo dedicados em `00-turnip-defaults.conf` para emuladores de Switch (`Eden`, `Citron`, `Sudachi`, `Yuzu`, `Ryujinx`), `Hogwarts Legacy` e `Mortal Kombat 11`.
- Relatório técnico aprofundado `RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md` com análise forense dos commits de `nepotira/eden-android-optimizations`, causa raiz do glitch esbranquiçado de *Super Mario Odyssey*, engenharia de stutters de shader e inovações disruptivas.
- Relatório técnico aprofundado `RELATORIO_HOGWARTS_MK11_ADRENO8XX.md` com diagnóstico e guia de mitigação para falhas gráficas em *Hogwarts Legacy* (DX12) e *Mortal Kombat 11* (DX11) via Winlator / GameHub.

### Changed
- `scripts/apply_all_patches.py` atualizado para orquestrar as 4 variantes (`sustained`, `biggmem`, `maxperf`, `switch2`) e injetar perfis driconf dinamicamente.
- `.github/workflows/build-turnip.yml` atualizado com a 4ª variante na matriz de compilação.
- `scripts/verify_patch_stack.py` atualizado para validar os invariantes matemáticos da variante `Switch2`.

## [0.1.0] - 2026-11-06
### Added
- Relatório técnico completo (`RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md`) dissecando a arquitetura Adreno 8xx (Gen 8), o gargalo do Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`) e a auditoria de código de mais de 25 forks comunitários de Turnip.
- Plano de implementação (`PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md`) com matriz de triagem de patches e arquitetura em 4 camadas sobre o `mesa/main >= d520ae90`.
- Stack modular de patches e scripts Python (`patches/` e `scripts/apply_all_patches.py`) cobrindo as 4 camadas de correção (GMEM/CCU do Adreno 825/829, LRZ fatiado em GMEM e SYSMEM + coerência bidirecional, `SP_*_HYSTERESIS`, `RB_RESOLVE_CR_CNTL`, MRs `!45937`/`!45973`, série `0001..0006` + `08` IB cache, correções de `kgsl_syncobj_merge`, `wait_timestamp_safe` `poll_timestamp`, `kgsl_sparse_vma_init` e `u_gralloc_aimapper.c`).
- Workflow GitHub Actions (`.github/workflows/build-turnip.yml`) para compilação das 3 variantes (`Sustained`, `BigGMEM` e `MaxPerf`) com Android NDK r29.
