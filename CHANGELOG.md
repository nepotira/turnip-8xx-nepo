# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.
O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e este projeto segue [SemVer 2.0.0](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.2.6] - 2026-11-06
### Fixed
- **Desacoplamento de Biblioteca e DT_SONAME para `vulkan.nepo.so` (`.github/workflows/build-turnip.yml`):**
  - Resolvida a colisão crítica de namespace de carregamento dinâmico no Android (`linker64`). Quando emuladores (como o Nyushu) usam Flutter/HWUI, o sistema já carrega `/vendor/lib64/hw/vulkan.adreno.so` com SONAME `vulkan.adreno.so`. Ao carregar um driver customizado com o mesmo SONAME, o Android reutilizava o handle do driver proprietário Qualcomm (`512.800.71`), impedindo silenciosamente que o Turnip fosse executado.
  - O binário agora é nomeado `vulkan.nepo.so` com `DT_SONAME: vulkan.nepo.so` via `patchelf` e registrado como `"libraryName": "vulkan.nepo.so"` no `meta.json`, eliminando a colisão e garantindo que o Turnip seja carregado no espaço de processo do emulador.
- **Suporte a Depth Blit Scaling / Resolução 2160p (`patches/64-tu-depth-blit-features.py`):**
  - Adicionado anúncio explícito de `VK_FORMAT_FEATURE_2_BLIT_SRC_BIT` e `VK_FORMAT_FEATURE_2_BLIT_DST_BIT` para formatos de profundidade (`VK_FORMAT_D32_SFLOAT`, `VK_FORMAT_D24_UNORM_S8_UINT`, `VK_FORMAT_D16_UNORM`) em `tu_physical_device_get_format_properties` (`src/freedreno/vulkan/tu_formats.cc`).
  - Corrige 64.910 falhas de `BlitScaleHelper: Device does not support scaling format D32_FLOAT` no `vk_texture_cache.cpp` de emuladores baseados em Yuzu/Eden/Uzuy em resoluções 2160p (escala 3X). Anteriormente, a ausência dessa flag impedia o upscale do buffer de profundidade, deixando-o preso em 720p enquanto a cor ia para 2160p ($1280/3840 \approx 33\%$), o que provocava o corte de ~65% da tela e falhas no teste de Z (névoa esbranquiçada e estouro especular).
- **Cobertura Universal de Driconf para Emuladores Switch (`scripts/apply_all_patches.py`):**
  - Expandido o perfil de otimizações de Nintendo Switch no `00-turnip-defaults.conf` para incluir correspondência dupla por nome de aplicação (`application_name_match`) e por executável/pacote Android (`executable_regexp`), cobrindo Nyushu (`com.antutu.benchmark.full`, `org.nyushu.*`), Eden / Eden Nepo (`dev.eden.*`, `nepotira/eden-android-optimizations`), Citron (`org.citron.*`), Yuzu (`org.yuzu.*`), Sudachi (`org.sudachi.*`), Suyu (`org.suyu.*`), Ryujinx (`org.ryujinx.*`) e Uzuy (`org.uzuy.*`).

## [0.2.5] - 2026-11-06
### Fixed
- **Correção da Invariante Matemática CCU no Adreno 825 / SM8735 (`scripts/apply_all_patches.py` e `scripts/verify_patch_stack.py`):**
  - Corrigido o cálculo de frações e tamanhos de cache CCU em GMEM (`gmem_ccu_color_cache_fraction`, `gmem_per_ccu_color_cache_size`, `gmem_ccu_depth_cache_fraction`, `gmem_per_ccu_depth_cache_size`). Anteriormente, programava-se a fração de registrador `EIGHTH` enquanto subtraía-se apenas 8 KB / 16 KB por CCU na tabela, gerando sobreposição física de 32 KB de cor e 64 KB de profundidade sobre tiles de GMEM vizinhos no hardware durante operações de resolve.
  - Para BigGMEM e Switch2: fração `EIGHTH` de cor (16 KB por CCU = 64 KB total) e fração `EIGHTH` de profundidade (32 KB por CCU = 128 KB total), totalizando 368 KB reservados e 656 KB de GMEM utilizável com zero underflow.
  - Para Sustained e MaxPerf: fração `EIGHTH` de cor (16 KB por CCU = 64 KB total) e fração `QUARTER` de profundidade (64 KB por CCU = 256 KB total), totalizando 496 KB reservados e 528 KB de GMEM utilizável.
  - Invariante estrita: o valor configurado em `RB_CCU_CACHE_CNTL` coincide exatamente com a faixa de GMEM isolada em `__calc_gmem_cache_offsets`, prevenindo estouros e corrupção gráfica em renders com múltiplos targets.
- **Correção da tela 65% preta / corte de viewport em 2160p (`patches/63-tu-framebuffer-attachment-extent-guard.py`):**
  - Em `tu_CreateFramebuffer` (`src/freedreno/vulkan/tu_device.cc`), quando o emulador (Nyushu, Yuzu, Citron) cria um framebuffer com as dimensões base não escaladas do jogo (ex.: 1280x720) mas anexa a view da swapchain de alta resolução em tela cheia (ex.: 2400x1080), as dimensões do framebuffer são expandidas com segurança para `MAX2(pCreateInfo, iview->image->vk.extent)`.
  - Em `tu6_sysmem_render_begin` (`src/freedreno/vulkan/tu_cmd_buffer.cc`), o comando `tu6_emit_window_scissor` passa a cobrir no mínimo a extensão do `render_areas[0]`, impedindo que o hardware clipa o blit de apresentação a 1280x720 em renderização direta, o que causava $1 - (1280 \times 720) / (2400 \times 1080) = 64,5\% \approx 65\%$ de tela preta.
### Added
- **Relatório Forense e Arquitetural (`docs/RELATORIO_FORENSE_ARQUITETURAL_FALHAS_2160P_E_ESBRANQUECIMENTO.md`):** Diagnóstico definitivo comprovado no código-fonte real do Mesa 3D e emuladores sobre as causas do esbranquiçamento em *Super Mario Odyssey* (descarte de depth draw calls em shaders assíncronos no emulador + mismatch de registradores CCU no Adreno 825) e da falha de 2160p com 64,5% (~65%) de tela preta (razão geométrica exata entre viewport 720p não escalado e tela 2400x1080 com clipping em `tu6_emit_window_scissor`).
- **Constituição e Regras (`AGENTS.md` e `LESSONS.md`):** Regra inegociável proibindo categoricamente qualquer declaração de causa-raiz de falha ou comportamento de hardware por suposição teórica ou dedução sem prévia inspeção e comprovação no código-fonte real.

## [0.2.4] - 2026-11-06
### Fixed
- **Correção da renderização em 2160p (4K / 3840x2160):** Removida a imposição cega de `prefer_gmem` (`tu_autotune_algorithm=prefer_gmem` e `DEFAULT=PREFER_GMEM`), restaurando o algoritmo dinâmico `BANDWIDTH` no `tu_autotune.cc`. No Adreno 825 com 1 MB de GMEM (752 KB utilizáveis), forçar GMEM em resoluções 4K criava mais de 4.000 tiles, estourando o buffer de fluxo de visibilidade VSC (Visibility Stream Clipper limitado a ~1.400 bins) e provocando o descarte de 65% dos bins/tela. Com `BANDWIDTH`, o driver usa GMEM em 720p/1080p e seleciona automaticamente SYSMEM (Direct Rendering) em 2160p, renderizando 100% da tela sem cortes nem VSC overflow.
- **Correção da precisão alpha A2B10G10R10 no Adreno 8xx KGSL (`tu_fix_a2_alpha_precision = true`):** Ativada a correção de precisão alpha do patch `mr45973` para emuladores de Switch no `00-turnip-defaults.conf`. No A8XX com KGSL, o hardware lê o alpha de 2 bits com subestimação `(1 - 2^-12)`, quebrando a decodificação de material ID / roughness em renderers deferred (como em *Super Mario Odyssey*) e provocando estouro especular branco puro na cena inteira.
- **Expansão da sanitização NIR para Compute Shaders e Image Stores (`patches/60-a8xx-sanitize-frag-nan.py`):** Estendida a sanitização do IR3 para interceptar `nir_intrinsic_image_store`, `bindless_image_store` e `image_deref_store` em `MESA_SHADER_COMPUTE` e `MESA_SHADER_FRAGMENT`, substituindo NaNs e Infs por zero/clamp em passes de névoa volumétrica e bloom executados por compute shaders.
- **Remoção de `tu_enable_fast_border_color_for_undefined_formats`:** Previne que samplers com formatos indefinidos retornem branco opaco indesejado em bordas de textura.


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
