# Plano de Implementação e Arquitetura de Patches: Correção Estrutural do Driver Turnip para Adreno 8xx (Foco no Snapdragon 8s Gen 4 / Adreno 825)

**Data de Elaboração:** 06 de Novembro de 2026  
**Documento de Origem:** [RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md)  
**Escopo:** Decisão fundamentada da árvore-base do Mesa Turnip, auditoria forense dos forks comunitários existentes e plano completo de implementação em código (C/C++/Python/NIR) para sanar as 9 falhas críticas mapeadas no relatório técnico, com foco prioritário no **Qualcomm Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`, `chip_id = 0x44030000`)**.

---

## 1. Investigação Forense e Decisão da Base Turnip (Matriz Decisória)

Seguindo o protocolo de pesquisa técnica profunda (auditoria direta de commits, árvores Git e scripts de patches em múltiplas infraestruturas até **06/11/2026**), foram inspecionadas cinco bases ativas no ecossistema Adreno 8xx:

1. **Mesa Upstream (`gitlab.freedesktop.org/mesa/mesa` — branch `main`, `27.0.0-devel`, commit `d520ae90` de 06/11/2026)**
2. **`whitebelyash/mesa-unified` (branch `turnip/gen8` — base direta do `Turnip Gen8 V38 / v27.0.0-R1` de StevenMXZ)**
3. **`MrPurple666/purple-turnip` (release `T30-toasted` de 17/08/2026 — `26.3.0-devel`)**
4. **`WinNative-Emu/Drivers` (branch `main` — MaxsTechReview / `maxjivi05`) & `Leb-Sun/Drivers` (`Redmagic-11-Pro-fixes` e `eco-variant`)**
5. **`The412Banner/Banners-Turnip` (branch `A8xx`, atualizado em 06/11/2026)**

### 1.1 Auditoria de Código: Por Que Não Usar `whitebelyash/mesa-unified` (Turnip V38) ou `MrPurple666` Como Base Bruta?

A inspeção forense dos commits das árvores estáticas comunitárias revelou que **tanto a branch `turnip/gen8` do `whitebelyash` (usada no Turnip Gen8 V38) quanto o pacote `MrPurple666 T30` possuem regressões graves no código-fonte e estão defasados em relação a correções críticas que acabaram de entrar no Mesa Upstream entre 22/10/2026 e 05/11/2026**:

> [!CAUTION]
> **Evidências de Bugs Encontrados no Código das Bases Comunitárias Atuais (Ground Truth):**
> 1. **Destruição de Subgroups por `supports_double_threadsize = True` (`whitebelyash` commit `031918ec` / Turnip V38):** O commit `"freedreno/common: update a8xx family configs"` (DVD) alterou `supports_double_threadsize` de `False` para `True` em `a8xx_base`. Auditoria com o Vulkan CTS no Adreno 8xx (confirmada em 05/11/2026) comprova que ativar `supports_double_threadsize = True` faz **660 de 660 testes de compute subgroup e reconvergência falharem** (`subgroupAdd`, `shuffle`, `ballot`, `clustered`), quebrando shaders Shader Model 6.0–6.6 no VKD3D-Proton e Unreal Engine 5.
> 2. **Expressão Booleana Quebrada em C++ (`whitebelyash` commit `6a415c50` em `src/freedreno/vulkan/tu_pipeline.cc`):**
>    ```cpp
>    const bool is_a830 = chip_id == 0xffff44050000 || 0x44050001;
>    const bool is_target_gpu = is_a810 || is_a825 || is_a829 || is_a830;
>    ```
>    Como `0x44050001` é uma constante inteira diferente de zero, `|| 0x44050001` avalia incondicionalmente para `true` em C++, desativando `fdm_per_layer` e `force_sample_interp` (MSAA sample shading) para **todas as GPUs** da árvore.
> 3. **Corrupção Matemática do Cache CCU e GMEM no Adreno 825 (Snapdragon 8s Gen 4) em TODAS as árvores comunitárias:**
>    * No **Turnip V38 (`whitebelyash` commit `70e2d6f3` / `136323c4`)**, no **WinNative (`apply_a8xx_gpus.py`)** e no **Banners-Turnip (`apply_a8xx_gpus.py`)**, o Adreno 825 foi configurado no modo `sysmem` com `sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.THREE_QUARTER.value` (que instrui o registrador de hardware `RB_CCU_CACHE_CNTL` a usar $\frac{3}{4} \times 256\text{ KB} = 192\text{ KB}$ por CCU, ou $768\text{ KB}$ nos 4 CCUs), mas reservou apenas `sysmem_per_ccu_depth_cache_size = 96 * 1024` ($96\text{ KB} \times 4 = 384\text{ KB}$) na aritmética de offsets (`fd6_calc_gmem_cache_offsets`). Resultado: **o cache de profundidade CCU sobrescreve $384\text{ KB}$ do cache de cor CCU dentro da SRAM mesmo em modo `sysmem`!**
>    * No modo `gmem`, o **Banners-Turnip** definiu `gmem_ccu_depth_cache_fraction = FULL` ($256\text{ KB} \times 4 = 1024\text{ KB}$ no hardware) com `gmem_per_ccu_depth_cache_size = 127 * 1024` ($508\text{ KB}$ reservados e desalinhados em $4\text{ KB}$), fazendo o hardware **atropelar $516\text{ KB}$ da memória de tiles GMEM**. Já o **WinNative** deixou `tile_align_w = 96` (alinhamento de 3 fatias do A830) no Adreno 825 (que possui **2 fatias**, exigindo `tile_align_w = 64`), enquanto o **Turnip V38** corrigiu `tile_align_w = 64` mas esqueceu `tile_max_w = 16416` (que não é divisível por $64$: $16416 \div 64 = 256,5$).
> 4. **Ausência dos Commits Críticos do Mesa Upstream de Outubro/Novembro de 2026:** Nem o Turnip V38 (19/10/2026) nem o MrPurple666 T30 (17/08/2026) contêm as correções estruturais de LRZ fatiado (`2ce86eed` e `e1852a33` de 04/11/2026), descritores de buffer A8XX (`5b2db4b8` de 04/11/2026) e divisão de *indirect draws* (`14656cee` e `7638039f` de 22/10/2026).

---

### 1.2 Matriz Comparativa das Bases Candidatas

| Critério Técnico | `MrPurple666/purple-turnip` (T30) | `whitebelyash/mesa-unified` (`turnip/gen8` / V38) | `WinNative-Emu/Drivers` / `Banners-Turnip` | **Decisão Escolhida: Mesa Upstream `main` (`>= d520ae90`) + Patch Stack Modular Híbrido** |
| :--- | :--- | :--- | :--- | :--- |
| **Recência da Base Mesa** | Estagnada em Ago/2026 (`26.3.0-devel`) | Defasada (Set/Out 2026); rebase manual difícil | Clona `mesa/main` HEAD dinamicamente | **Tempo Real (`mesa/main` HEAD `>= 2026-11-06`)** |
| **Correções LRZ A8XX (`2ce86eed` / `e1852a33`)** | Ausentes (LRZ quebrado) | Ausentes (LRZ quebrado) | Presentes ao compilar sob `main` atual | **Presentes nativamente no `main`** |
| **Descritores de Buffer A8XX (`5b2db4b8`)** | Ausente (usa split 2D legado do A6xx) | Ausente | Presente ao compilar sob `main` atual | **Presente nativamente no `main`** |
| **Chunking de Indirect Draws (`14656cee`)** | Ausente (CP trava em buffers $>4\text{ MB}$) | Ausente | Presente ao compilar sob `main` atual | **Presente nativamente no `main`** |
| **Geometria e Cache CCU do Adreno 825** | Ausente (apenas `drm-shim`) | Quebrado (`tile_max_w=16416`, `HALF=128KB`, `THREE_QUARTER=96KB`) | Quebrado (`tile_align_w=96` no WN; `127*1024` no Banners) | **Corrigido matematicamente (`tile_align_w=64`, `tile_max_w=16384`, frações CCU exatas)** |
| **Subgroups Wave32 / Double Threadsize** | Quebrado (`supports_double_threadsize=True`) | Quebrado (`supports_double_threadsize=True`) | Corrigido no Banners (`0002` + `a8xx_no_double_threadsize.py`) | **Mantém `supports_double_threadsize=False` + patch `0002` Half-Wave Subgroup 32** |

### 1.3 Veredito da Base Escolhida

A base escolhida para aplicar a implementação é:
* **Árvore Fonte Primária:** **Upstream `gitlab.freedesktop.org/mesa/mesa` (branch `main`, a partir do commit `d520ae90` de 06/11/2026, Mesa `27.0.0-devel`)**.
* **Arquitetura de Aplicação:** Sistema de patches modulares idempotentes sobre o `mesa/main` limpo, dividido em **4 Camadas de Intervenção**, incorporando as descobertas validadas por traces de hardware e testes reais dos 25+ forks comunitários (`Vauzi-17`, `Droid-VM`, `faux123`, `WinNative-Emu`, `Hugo223`, `AlexSanz0902`) e descartando integralmente os commits defeituosos (`031918ec`, `6a415c50`, `4a067910`, `bc16322d`, `70e2d6f3`).

---

### 1.4 Matriz de Triagem dos Patches dos Forks Modificados (Adotar / Adaptar / Rejeitar)

A tabela abaixo documenta a decisão de engenharia para cada grupo de patches encontrado nos mais de 25 repositórios de Turnip modificados auditados:

| Origem (Fork / Autor) | Patch / Commit Auditado | Decisão | Justificativa Técnica de Engenharia |
| :--- | :--- | :--- | :--- |
| **`Droid-VM/turnip` (`HuJK`) & `WinterMist010`** | `486c973` / `kgsl-zero-timeout-poll.patch` (`wait_timestamp_safe` com `timeout == 0`) | **ADOTAR** | No kernel KGSL, `timeout = 0` significa esperar infinitamente. Substituir por `poll_timestamp` (`READTIMESTAMP_CTXTID`) quando `get_relative_ms == 0` reduz o bloqueio de `vkWaitSemaphores` de $250\text{ ms/s}$ para $5\text{ ms/s}$ (+35% FPS). |
| **`WinterMist010` (`patches/sync2`) & `faux123`** | `kgsl-syncobj-merge-ts-fd.patch` (`kgsl_syncobj_merge` em `tu_knl_kgsl.cc`) | **ADOTAR** | Corrige `SIGSEGV` ao desreferenciar `sync->queue` nulo quando `sync` é `FD` e `ret` é `TS`, e corrige uso de `ret.fd` não inicializado quando `ret` e `sync` são `TS` de filas diferentes. |
| **`Droid-VM/turnip` (`HuJK`)** | `b43c434` (`kgsl_sparse_vma_init` chamar `tu_dump_bo_init`) | **ADOTAR** | Sem `tu_dump_bo_init(dev, bo)`, `dump_bo_list_idx` fica `0` em vez de `~0`, causando crash em `tu_dump_bo_del()` ao liberar memória sparse (VKD3D-Proton / DX12). |
| **`Droid-VM/turnip` (`HuJK`)** | `bf2112c` (Tolerar `VK_KHR_display` em `tu_knl_kgsl_load`) | **ADOTAR** | Impede falha `VK_ERROR_INITIALIZATION_FAILED ("I can't KHR_display")` quando Zink ou contêineres ativam a extensão de instância. |
| **`Vauzi-17/710` & `sherft2607`** | `52-a8xx-resolve-cr-cntl.py` (`REG_A8XX_RB_RESOLVE_CR_CNTL = 1`) | **ADOTAR** | Confirmado em 100% dos traces `.rd` do blob Qualcomm A8xx para inicializar o bloco *Color/Clear Resolve* das fatias RB. |
| **`Vauzi-17/710` & `sherft2607`** | `54-a8xx-sp-hysteresis.py` & `55-a8xx-sp-hysteresis-gs-hs-ds.py` (`SP_*_HYSTERESIS`) | **ADOTAR** | Como `has_rt_workaround = False` no A8xx, os 6 registradores `SP_*_HYSTERESIS` ficavam em `0x0`. Gravar `0xc00` (PS) e `0x400` (VS/HS/DS/GS/CS) evita *power-gating* prematuro das ALUs entre draws. |
| **`Vauzi-17/710` & `sherft2607`** | `61-a8xx-lrz-bidir-disable.py` & `62-a8xx-lrz-color-comp-mask.py` | **ADOTAR** | Seta `FORCE_BI_DIR_LRZ_DISABLE` em `sysmem` e `disable_lrz`, e emite `GRAS_LRZ_COLOR_COMP_MASK` (`0x810c`), eliminando conflitos bidirecionais de LRZ entre fatias (ex.: *RDR2*). |
| **`Hugo223` / `WinterMist010`** | `0006-tu-sample-shading-gate.patch` (`tu_lower_nir` em `tu_shader.cc`) | **ADOTAR** | Exige `key->force_sample_interp && nir->info.fs.uses_sample_shading`, bloqueando o falso-positivo de `sampleShadingEnable` do `vkd3d-proton` (+37,5% FPS em *Teardown*). |
| **`WinNative-Emu` (`MaxsTechReview`)** | Série `0001..0005` + `08-tu-kgsl-cache-retired-a8xx-ib-storage.patch` | **ADOTAR** | Mesh Shader em compute (`0001`), Half-Wave Subgroup 32 (`0002`), Cube Map NaN/Zero sanitize (`0003`), `SP_*_BINDLESS_INVALIDATE` (`0004`) e VBO alias + cache de IBs retirados no KGSL (`0005` + `08`). |
| **`WinNative-Emu` & `Vauzi-17` & `Frane12`** | `add_aimapper_gralloc.py` + `add_ubwc_swapchain_usage.py` + `01-u_gralloc-always-use-ubwc-detection.patch` | **ADOTAR** | Carrega `AIMapper5` via SP-HAL no Android 15/16 e detecta UBWC no fallback **mantendo** a checagem de segurança `if (hnd->handle->numInts >= 2)`. |
| **`AlexSanz0902/turnip-sd865-z`** | `30-tu-z-mutable.py` (Guarda `DRM_FORMAT_MOD_QCOM_COMPRESSED` em `tu_image.cc`) | **ADOTAR** | Impede que imagens `MUTABLE_FORMAT` com UBWC caiam para `TILE6_LINEAR` em `CHIP >= A8XX` (preservando `TILE6_3`). |
| **`WinNative-Emu` / `Leb-Sun` / `Banners` / `V38`** | `apply_a8xx_gpus.py` / `tu_gen8` (Tabela do `Adreno 825` e `829`) | **ADAPTAR (Corrigir Matemática)** | Aproveita a estrutura de `GPUId(0x44030000)` e coalescência de UBOs, mas **substitui** `tile_align_w=96`/`tile_max_w=16416` por `64`/`16384` e sincroniza as frações CCU (`FULL`/`HALF`/`EIGHTH`) para eliminar o atropelamento de GMEM e liberar $1.056\text{ KB}$ ($66\text{ blocos}$). |
| **`DiskDVD` / `WinterMist010`** | `0000-a8xx.patch` (commits `bc16322d`, `d854a454`, `70e2d6f3`) | **REJEITAR** | Contém ~100 linhas de código morto gerado por LLM (`ir3_get_gpu_profile` sem nenhum chamador), booleano C++ quebrado (`|| 0x44050001` sempre `true`) e configuração CCU `HALF + HALF` que desperdiça 50% da GMEM do `Adreno 825`. |
| **`whitebelyash` / `Banners-Turnip` / `s1mptom`** | `fd6_gmem_cache.h` (`offset -= 0x78000`), `reg_size_vec4 = 96` em `a8xx_gen1` e `supports_double_threadsize = True` | **REJEITAR** | `offset -= 0x78000` causa *underflow* (`0xFFFC8000`) nos $2\text{ MB}$ do `Adreno 825/829`; `reg_size_vec4=96` mutila GPRs do A830; `supports_double_threadsize=True` quebra 660/660 testes de subgrupo no CTS. |

---

## 2. Mapeamento Rastreável: Problemas do Relatório $\rightarrow$ Módulos de Correção

```mermaid
flowchart TD
    subgraph Relatorio["11 Problemas Evidenciados no Relatório Técnico (Upstream + Forks)"]
        P1["P1/P4: Colapso da GMEM Fatiada, Colisão CCU e Forçamento de sysmem"]
        P2["P2/P9/P10: Crashes KGSL (syncobj_merge, wait_timestamp=0, sparse_vma, IB free, Gralloc UBWC)"]
        P3["P3: Throttling Térmico Severo e Gargalo de Bandwidth no 8s Gen 4"]
        P5["P5: Corrupção do LRZ (GMEM slice pitch, SYSMEM fd_lrzfc_layout, BI_DIR_LRZ)"]
        P6["P6/P7: Bugs ir3, Subgroups Wave32, Cube NaN, SP_HYSTERESIS, CP WFI e sampleShading"]
        P7["P8: Orfandade e Offsets Incorretos do Adreno 825 (0x44030000) e 829"]
        P8["P11: Falhas em Jogos DX11/DX12 (A2B10G10R10 Alpha, Bindless, Indirect Draws)"]
    end

    subgraph Plano["Camadas do Plano de Implementação (Sobre Mesa main >= d520ae90)"]
        C1["Camada 1: Calibração Exata do Adreno 825/829, RB_RESOLVE_CR_CNTL e Blindagem GMEM/CCU"]
        C2["Camada 2: Estabilização GMEM, LRZ Fatiado (GMEM+SYSMEM+BI_DIR), SP_HYSTERESIS e TILE6_3"]
        C3["Camada 3: Correções A8xx no ir3, CP WFI, Descritores, sampleShading Gate e Patches 0001-0004"]
        C4["Camada 4: Correções KGSL (syncobj, poll_ts, sparse, VBO+IB cache), AIMapper5 UBWC e Governança 8s"]
    end

    P1 --> C1 & C2
    P7 --> C1
    P5 --> C2
    P6 --> C2 & C3
    P8 --> C3
    P2 --> C4
    P3 --> C1 & C4
```

---

## 3. Especificação Técnica Detalhada por Camada de Implementação

### Camada 1: Calibração Matemática do Adreno 825 (Snapdragon 8s Gen 4) e Blindagem de GMEM/CCU

**Problemas Resolvidos:** Problemas **6.1.1**, **6.2.4** e **6.2.8** do Relatório Técnico (Ausência do Adreno 825 no Mesa Upstream, ausência de `REG_A8XX_RB_RESOLVE_CR_CNTL = 1`, erros de alinhamento de fatias `tile_align_w`/`tile_max_w` e estouro silencioso de offsets de cache CCU dentro dos $2\text{ MB}$ de GMEM).

#### 3.1.1 Aritmética Exata dos Registradores CCU e GMEM para o Adreno 825 (`0x44030000`)
O Adreno 825 (`SM8735`, família `gen8_6_0`) possui especificações físicas estritas:
* **`gmem_size` físico:** $2\text{ MB} = 2.097.152\text{ bytes} = 2.048\text{ KB}$ (`0x200000`).
* **Topologia de Fatias e CCUs:** `num_slices = 2`, `num_ccu = 4` ($2\text{ CCUs por fatia}$).
* **Capacidade física total por CCU:** Color Cache (`FULL`) = $128\text{ KB}$; Depth Cache (`FULL`) = $256\text{ KB}$.
* **Invariante de Hardware (`RB_CCU_CACHE_CNTL` vs. `fd6_calc_gmem_cache_offsets`):** A fração programada no registrador (`FULL = 1/1`, `THREE_QUARTER = 3/4`, `HALF = 1/2`, `QUARTER = 1/4`, `EIGHTH = 1/8`) **deve corresponder exatamente** ao tamanho em bytes subtraído do topo da GMEM:
  * **Em modo `sysmem` (orçamento total = $2.048\text{ KB}$):**
    * `sysmem_vpc_bv_pos_buf_size = 24576` ($24\text{ KB} \times 4 = 96\text{ KB}$)
    * `sysmem_vpc_attr_buf_size = 131072` ($128\text{ KB} \times 4 = 512\text{ KB}$)
    * `sysmem_vpc_pos_buf_size = 65536` ($64\text{ KB} \times 4 = 256\text{ KB}$)
    * `sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value` $\rightarrow$ `sysmem_per_ccu_color_cache_size = 128 * 1024` ($128\text{ KB} \times 4 = 512\text{ KB}$)
    * `sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value` $\rightarrow$ `sysmem_per_ccu_depth_cache_size = 128 * 1024` ($128\text{ KB} \times 4 = 512\text{ KB}$)
    * **Soma `sysmem`:** $96 + 512 + 256 + 512 + 512 = \mathbf{1.888\text{ KB}} \le 2.048\text{ KB}$ (`depth_ccu_offset = 160 KB = 0x28000`, sem underflow e sem colisão entre caches!).
  * **Em modo `gmem` (orçamento total = $2.048\text{ KB}$):**
    * `gmem_vpc_bv_pos_buf_size = 32768` ($32\text{ KB} \times 4 = 128\text{ KB}$)
    * `gmem_vpc_attr_buf_size = 49152` ($48\text{ KB} \times 4 = 192\text{ KB}$)
    * `gmem_vpc_pos_buf_size = 24576` ($24\text{ KB} \times 4 = 96\text{ KB}$)
    * `gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value` $\rightarrow$ `gmem_per_ccu_color_cache_size = 16 * 1024` ($16\text{ KB} \times 4 = 64\text{ KB}$)
    * `gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value` $\rightarrow$ `gmem_per_ccu_depth_cache_size = 128 * 1024` ($128\text{ KB} \times 4 = 512\text{ KB}$)
    * **Soma de reservas não-tile em `gmem`:** $128 + 192 + 96 + 64 + 512 = \mathbf{992\text{ KB}}$.
    * **GMEM Utilizável para Tiles (`usable_gmem_size_gmem`):** $2.048\text{ KB} - 992\text{ KB} = \mathbf{1.056\text{ KB}}$ (`0x108000` bytes = exatamente **66 blocos** de `gmem_align = 16 KB`), um ganho de **$+448\text{ KB}$ ($+73\%$)** sobre o Turnip V38 / `DiskDVD` ($608\text{ KB}$) e **$+512\text{ KB}$ ($+94\%$)** sobre o WinNative ($544\text{ KB}$)!

#### 3.1.2 Alinhamento Geométrico das 2 Fatias (`tile_align_w` e `tile_max_w`)
* Como o Adreno 825 possui `num_slices = 2`, a tabela de blocos LRZ do Gen 8 (`lrz_block_sizes[1]` em `src/freedreno/fdl/freedreno_lrz_layout.h`) define blocos de $128 \times 128$ pixels em `MSAA_ONE`.
* Portanto, `tile_align_w` **deve ser `64`** ($2\text{ fatias} \times 32\text{ pixels}$, divisor exato de $128$) e `tile_max_w` **deve ser `16384`** ($256 \times 64$), eliminando a corrupção de bordas de tiles causada por `tile_align_w = 96` ou `tile_max_w = 16416`.

#### 3.1.3 Especificação do Código para `src/freedreno/common/freedreno_devices.py` e `freedreno_noop.c`
* **Arquivo 1:** `src/freedreno/common/freedreno_devices.py`
  * Mover `has_fs_tex_prefetch = False` para `a8xx_base` (resolvendo o `TODO` do Mesa Upstream e impedindo que o Adreno 825 e o Adreno 830 emitam instruções `FS_TEX_PREFETCH` legadas da família A7xx).
  * Garantir `supports_double_threadsize = False` em `a8xx_base`.
  * Adicionar `[A6XXRegs.REG_A8XX_RB_RESOLVE_CR_CNTL, 0x00000001]` em `a8xx_base_raw_magic_regs` (`52-a8xx-resolve-cr-cntl.py` de `Vauzi-17`).
  * Adicionar o perfil dedicado `a8xx_825` e registrar `chip_id = 0x44030000` (KGSL) e `0xffff44030000` (drm-shim / fallback):

```python
a8xx_825 = GPUProps(
        reg_size_vec4 = 96,
        sysmem_vpc_attr_buf_size = 131072,
        sysmem_vpc_pos_buf_size = 65536,
        sysmem_vpc_bv_pos_buf_size = 24576,
        sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.FULL.value,
        sysmem_per_ccu_color_cache_size = 128 * 1024,
        sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,
        sysmem_per_ccu_depth_cache_size = 128 * 1024,
        gmem_vpc_attr_buf_size = 49152,
        gmem_vpc_pos_buf_size = 24576,
        gmem_vpc_bv_pos_buf_size = 32768,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_per_ccu_color_cache_size = 16 * 1024,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,
        gmem_per_ccu_depth_cache_size = 128 * 1024,
        has_fs_tex_prefetch = False,
        has_salu_int_narrowing_quirk = True,
        shading_rate_matches_vk = True,
        enable_tp_ubwc_flag_hint = True,
)

add_gpus([
        GPUId(chip_id=0x44030000, name="Adreno (TM) 825"), # KGSL
        GPUId(chip_id=0xffff44030000, name="Adreno (TM) 825"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_825],
        num_ccu = 4,
        num_slices = 2,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 16384,
        tile_max_h = 16384,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 64 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))
```
* **Correção concomitante da entrada `Adreno (TM) 829` no `freedreno_devices.py`:** Adicionar os overrides `sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value`, `sysmem_per_ccu_depth_cache_size = 128 * 1024`, `gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value` e `gmem_per_ccu_depth_cache_size = 128 * 1024` (pois o `a8xx_gen2` upstream reserva $192\text{ KB} \times 4 = 768\text{ KB}$ em `sysmem`, causando underflow de $-96\text{ KB}$ nos $2.048\text{ KB}$ de GMEM do Adreno 829!).
* **Arquivo 2:** `src/freedreno/common/fd6_gmem_cache.h`
  * **PROIBIÇÃO ABSOLUTA do patch `offset -= 0x78000` (`PATCH 9/9` do `tu_gen8_clean.patch` / `tu_gen8_infra.patch`):** O Mesa Upstream removeu `offset -= 0x78000` ($480\text{ KB}$) no commit `04f9a827` (28/03/2026), mas o `Banners-Turnip` continuou aplicando `if (info->chip >= 8 && info->num_slices > 1) offset -= 0x78000;`. Como tanto o **Adreno 825** quanto o **Adreno 829** possuem `num_slices = 2 > 1` e apenas $2.048\text{ KB}$ de GMEM, subtrair $480\text{ KB}$ adicionais causa um **underflow imediato de inteiro sem sinal (`-224 KB` = `0xFFFC8000`)** em `depth_ccu_offset`! Portanto, esse patch **jamais** deve ser aplicado.
  * Inserir verificação de integridade (`assert(offset >= num_ccu * config->depth_cache_size)`) em `__calc_gmem_cache_offsets` para impedir silenciosamente qualquer underflow de `unsigned offset` em GPUs com GMEM reduzida.

---

### Camada 2: Estabilização de GMEM (TBDR), LRZ Fatiado (GMEM + SYSMEM + Coerência Bidirecional), `SP_*_HYSTERESIS` e Redução Dinâmica de Cache em MRT

**Problemas Resolvidos:** Problemas **6.1.1**, **6.2.4**, **6.2.5** e **6.2.6** do Relatório Técnico (Dependência de `TU_DEBUG=sysmem` e `TU_DEBUG=nolrz`, corrupção de LRZ no modo `SYSMEM`, conflitos bidirecionais de LRZ entre fatias, desligamento prematuro de ALUs por `SP_*_HYSTERESIS = 0`, rebaixamento de `TILE6_3` em imagens `MUTABLE_FORMAT` e condicionais `<A7XX>` residuais).

#### 3.2.1 Correção do Layout e Fast-Clear do LRZ por Fatia em GMEM (Nativo no `mesa/main >= 2026-11-04`)
Ao adotar o `mesa/main` pós-04/11/2026 como base, incorporamos diretamente dois commits fundamentais de Danylo Piliaiev:
* **Commit `2ce86eed` (`tu/lrz: Fix partial LRZ fast-clear on A8XX`):** Introduz `lrz_fc_slice_pitch` em `src/freedreno/fdl/freedreno_lrz_layout.h` e reescreve `fdl6_lrz_fc_first_uncovered_offset` e `tu6_clear_lrz_partial` (`src/freedreno/vulkan/tu_clear_blit.cc`) para respeitar o particionamento da Fast-Clear RAM entre as fatias (`num_slices = 2` no Adreno 825 e `num_slices = 3` no Adreno 830).
* **Commit `e1852a33` (`tu/lrz: Align LRZ pitch to 32 instead of 64 on A8XX`):** Corrige o alinhamento de `lrz_pitch` de 64 para 32 blocos em `fdl6_lrz_layout_init`.
* Combinados com `tile_align_w = 64` no Adreno 825 (Camada 1), os blocos LRZ de $128 \times 128$ ficam perfeitamente alinhados às fronteiras dos tiles da GMEM, eliminando o *Z-fighting* invertido e os *page faults* de LRZ sem precisar de `TU_DEBUG=nolrz`.

#### 3.2.2 Correção Crítica do Bug de LRZ no Modo SYSMEM (`src/freedreno/vulkan/tu_lrz.cc:852-876`), Coerência `FORCE_BI_DIR_LRZ_DISABLE` / `GRAS_LRZ_COLOR_COMP_MASK` e `SP_*_HYSTERESIS`
1. **Correção do Layout `fd_lrzfc_layout<CHIP>` em `tu_lrz_before_sysmem_br<CHIP>()` (`src/freedreno/vulkan/tu_lrz.cc:852-876`):**
   * **O Bug no Código Atual:** Embora `tu_lrz_before_sysmem_br<CHIP>` seja uma função template instanciada para `A6XX`, `A7XX` e `A8XX`, as linhas 854, 870 e 876 usam `fd_lrzfc_layout<A7XX>` hardcoded (`// FIXME hard-coding A7XX here and below is wrong!`).
   * Em `fd_lrzfc_layout<A8XX>`, os offsets reais são **`0x2038`** (`buffer[0].depth_clear_val`), **`0x2438`** (`buffer[1].depth_clear_val`) e **`0x2C00`** (`br_cur_buffer`), em vez de `0x838`, `0x878` e `0x8C0` do A7XX! Ler os offsets do A7XX no A8XX carrega bits de `fc1_b` (`0xffffffff` = `NaN`) no registrador `GRAS_LRZ_DEPTH_CLEAR`!
   * **Correção Exata em `src/freedreno/vulkan/tu_lrz.cc`:**
```cpp
      } else if constexpr (CHIP >= A7XX) {
         const unsigned if_dwords = 4, else_dwords = if_dwords;
         uint64_t lrz_fc_iova =
            lrz->image_view->image->iova + lrz->image_view->image->lrz_layout.lrz_fc_offset;
         uint64_t br_cur_buffer_iova =
            lrz_fc_iova + offsetof(fd_lrzfc_layout<CHIP>, br_cur_buffer);
         ...
         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),
                        lrz_fc_iova + offsetof(fd_lrzfc_layout<CHIP>, buffer[1].depth_clear_val));
         ...
         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),
                        lrz_fc_iova + offsetof(fd_lrzfc_layout<CHIP>, buffer[0].depth_clear_val));
      }
```
2. **Emissão de `FORCE_BI_DIR_LRZ_DISABLE` e `GRAS_LRZ_COLOR_COMP_MASK` (`61-a8xx-lrz-bidir-disable.py` & `62-a8xx-lrz-color-comp-mask.py` de `Vauzi-17`):**
   * Em `src/freedreno/vulkan/tu_cmd_buffer.cc` (`tu6_emit_bin_size` e `tu6_sysmem_render_begin`): quando `CHIP >= A8XX`, setar `.force_bi_dir_lrz_disable = disable_lrz` em `tu6_emit_bin_size` e `.force_bi_dir_lrz_disable = true` em `tu6_sysmem_render_begin` dentro de `GRAS_SC_BIN_CNTL(CHIP)`.
   * Em `src/freedreno/vulkan/tu_pipeline.cc` (`tu6_emit_mrt_blend_state`): quando `CHIP >= A8XX`, emitir `tu_cs_emit_regs(cs, A6XX_GRAS_LRZ_COLOR_COMP_MASK(mrt_comp_mask));`.
3. **Inicialização de Histerese das Unidades SP (`54-a8xx-sp-hysteresis.py` & `55-a8xx-sp-hysteresis-gs-hs-ds.py` de `Vauzi-17`):**
   * Em `src/freedreno/vulkan/tu_cmd_buffer.cc` (`tu6_init_hw<CHIP>`), logo após `tu_cs_emit_regs(cs, SP_ALPHA_TEST_CNTL(CHIP));`:
```cpp
   if constexpr (CHIP >= A8XX) {
      tu_cs_emit_regs(cs, A6XX_SP_VS_HYSTERESIS(0x00000400));
      tu_cs_emit_regs(cs, A6XX_SP_HS_HYSTERESIS(0x00000400));
      tu_cs_emit_regs(cs, A6XX_SP_DS_HYSTERESIS(0x00000400));
      tu_cs_emit_regs(cs, A6XX_SP_GS_HYSTERESIS(0x00000400));
      tu_cs_emit_regs(cs, A6XX_SP_PS_HYSTERESIS(0x00000c00));
      tu_cs_emit_regs(cs, A6XX_SP_CS_HYSTERESIS(0x00000400));
   }
```
4. **Proteção de `TILE6_3` em Imagens `MUTABLE_FORMAT` Comprimidas (`30-tu-z-mutable.py` de `AlexSanz0902`) e Condicionais `<A7XX>` Residuais:**
   * Em `src/freedreno/vulkan/tu_image.cc` (`tu_image_init`): alterar o fallback de formatos mutáveis com blocos diferentes para `if (image->vk.drm_format_mod != DRM_FORMAT_MOD_QCOM_COMPRESSED && cmd_device_chip < A8XX) layout->tile_mode = TILE6_LINEAR;`, preservando `TILE6_3` no Adreno 8xx.
   * `src/freedreno/vulkan/tu_pipeline.cc:3479` (`tu_binning_conservative_rast<CHIP>`): alterar `CHIP == A7XX` para `CHIP >= A7XX`.
   * `src/freedreno/vulkan/tu_query_pool.cc:2178` (`tu_CmdWriteAccelerationStructuresPropertiesKHR`): substituir `tu_emit_cache_flush<A7XX>(cmd);` por `TU_CALLX(cmd->device, tu_emit_cache_flush)(cmd);`.
   * `src/freedreno/vulkan/tu_cmd_buffer.cc:345-351, 438, 6967, 6991`: substituir chamadas `tu_emit_event_write<A7XX>` e `tu_emit_raw_event_write<A7XX>` em `tu_emit_rt_workaround<CHIP>` e `tu_emit_subpass_fsr<CHIP>` por `<CHIP>`, e permitir `TU_CMD_FLAG_RTU_INVALIDATE` em `CHIP >= A7XX`.

#### 3.2.3 Ajuste Dinâmico do Cache CCU de Profundidade para Render Passes Pesados em GPUs de 2 MB (`src/freedreno/vulkan/tu_device.cc`)
Mesmo com $1.056\text{ KB}$ de GMEM utilizável no Adreno 825, jogos DirectX 12 / Unreal Engine 5 com *Deferred Shading* pesado (múltiplos Render Targets de 64-bit/32-bit simultâneos) podem demandar mais blocos de GMEM para evitar a queda para `sysmem` ou o excesso de divisões de bins.
* **Intervenção em `src/freedreno/vulkan/tu_device.cc` (baseada e aprimorada a partir da engenharia do `Leb-Sun/Drivers` `eco-variant`):**
  * Para GPUs `CHIP == A8XX` com `device->gmem_size <= 2 * 1024 * 1024` (Adreno 825 e 829), permitir a redução sincronizada do cache CCU de profundidade em modo GMEM para `CCUColorCacheFraction.QUARTER.value` (`64 * 1024` por CCU = $256\text{ KB}$ totais em vez de $512\text{ KB}$), liberando mais **$+256\text{ KB}$** para o tile buffer (**$1.312\text{ KB}$ / 82 blocos de GMEM utilizáveis**, ou **64% de toda a SRAM física do Adreno 825 dedicada exclusivamente a tiles**!), mantendo o enum `RB_CCU_CACHE_CNTL` e o cálculo de offset 100% sincronizados.

---

### Camada 3: Correções de Hardware A8xx no Compilador `ir3`, Command Processor, Descritores e `sampleShadingEnable`

**Problemas Resolvidos:** Problemas **6.2.6**, **6.2.7** e **6.3.11** do Relatório Técnico (Falhas de compilação/execução no `ir3`, *hangs* de Shader Processor/Texture Processor, falso-positivo de `sampleShadingEnable` no VKD3D-Proton, corrupção de materiais em DXVK/VKD3D e estouro de *indirect draws*).

#### 3.3.1 Integração dos Merge Requests Abertos do Mesa Upstream (Cherry-Pick Direto)
1. **MR `!45937` (`tu: WFI before reading registers that were just written` — Danylo Piliaiev, 04/11/2026):**
   * **Causa Raiz no Hardware A8xx:** Ao contrário do firmware do Adreno 750, os pacotes `CP_REG_RMW`, `CP_REG_TO_MEM` e `CP_REG_TO_SCRATCH` no Adreno 8xx **não executam `CP_WAIT_FOR_IDLE` (WFI) implicitamente**, lendo valores obsoletos de registradores recém-escritos.
   * **Arquivos Modificados:** `src/freedreno/vulkan/tu_clear_blit.cc` (`store_3d_blit`) e `src/freedreno/vulkan/tu_cmd_buffer.cc` (`tu_CmdBeginTransformFeedbackEXT` e `tu_dispatch` antes de `CP_WAIT_FOR_ME` quando `CHIP >= A8XX`).
   * **Impacto:** Corrige falhas em *Transform Feedback* (`VK_EXT_transform_feedback` usado pelo DXVK para *Stream Output* do D3D11), blits 3D de GMEM e *indirect compute dispatches* desalinhados.
2. **MR `!45973` (`tu: Workaround the 2-bit alpha precision of 10_10_10_2_UNORM on A8XX KGSL` — Danylo Piliaiev, 05/11/2026):**
   * **Causa Raiz no Kernel KGSL + Hardware A8xx:** O driver KGSL do Android nos aparelhos Snapdragon 8xx não seta o bit 20 de `TPL1_DBG_ECO_CNTL` nem o bit 25 de `TPL1_DBG_ECO_CNTL1`. Sem esses bits, o Texture Processor (TP) converte o canal alfa de 2 bits de texturas `A2B10G10R10_UNORM` com precisão `fp16` (`fp16(1/3)` em vez de `1/3`), corrompendo a decodificação de IDs de materiais em G-Buffers de jogos DXVK/VKD3D (como *Resident Evil 3*, *War Thunder* e engines deferred).
   * **Arquivos Modificados:** `src/freedreno/fdl/fd6_view.cc` (grava a máscara do canal A2 no dword 15 não utilizado do descritor), `src/freedreno/vulkan/tu_shader.cc` (passo NIR `tu_nir_lower_a2_alpha` que recompõe a precisão exata `1/3` e `2/3`) e `src/freedreno/vulkan/00-turnip-defaults.conf` (ativa automaticamente para `DXVK|vkd3d` em `A8XX` sobre `kgsl`).

#### 3.3.2 Série de Patches de Hardware A8xx para Emulação PC/Console (`a8xx-winnative` 0001–0004 + `0006` Sample Shading Gate)
1. **Patch `0002` (`tu,ir3: Support a required subgroup size of half a wave` — `src/freedreno/ir3/ir3_lower_subgroups.c` e `tu_device.cc`):**
   * Como o A8xx opera fisicamente apenas em ondas de 64 fibras (`real_wavesize = 64`, `supports_double_threadsize = False`), jogos DirectX 12 (VKD3D-Proton) que exigem `WaveSize(32)` via `VK_EXT_subgroup_size_control` falhariam ao criar pipelines. Este patch particiona as operações de subgrupo no `ir3` em meias-ondas de 32 fibras (`HALF_SUBGROUP_SIZE 32`), permitindo expor `minSubgroupSize = 32, maxSubgroupSize = 64` sem corromper o estado de reconvergência do hardware.
2. **Patch `0003` (`ir3: Sanitize cube map directions on A8XX` — `src/freedreno/ir3/ir3_nir.c`):**
   * Adiciona a propriedade `cube_coord_hang_quirk = True` em `a8xx_base` e o passo NIR `ir3_nir_lower_cube_coord`. Quando um jogo (ex.: *Final Fantasy VII Rebirth*) amostra um Cube Map com um vetor direção nulo `(0,0,0)` ou `NaN`, o passo NIR substitui `NaN` por `0`, limita a valores finitos (`FLT_MAX` / `65504.0`) e converte o vetor zero em `+Z (0,0,1)`, impedindo o travamento físico (*GPU hang*) da unidade de textura do Adreno 8xx.
3. **Patch `0004` (`tu: Invalidate bindless descriptors through the A8XX registers` — `src/freedreno/vulkan/tu_cmd_buffer.cc`, `tu_cmd_buffer.h`, `tu_clear_blit.cc`):**
   * O Adreno 8xx removeu os bits `.cs_bindless` e `.gfx_bindless` do registrador `SP_UPDATE_CNTL`. Embora o Mesa Upstream já tenha corrigido `tu6_emit_flushes` (MR `!45129`), as funções `r3d_common`, `tu_init_hw` e `tu6_emit_bindless_bases` ainda tentavam invalidar o cache bindless via `SP_UPDATE_CNTL`, deixando descritores obsoletos no cache e causando corrupção de texturas em jogos *Bindless* (DXVK/VKD3D). O patch substitui essas chamadas pela emissão explícita de `SP_GFX_BINDLESS_INVALIDATE` e `SP_CS_BINDLESS_INVALIDATE`.
4. **Patch `0001` (`tu: Emulate VK_EXT_mesh_shader with compute` — `src/freedreno/vulkan/tu_mesh.cc`):**
   * Implementa a emulação de *Task/Mesh Shaders* (`VK_EXT_mesh_shader`) via compute shaders utilizando um *ring buffer* de dispositivo e `cs_shared_mem_size = 64 * 1024`, viabilizando títulos DirectX 12 Ultimate (como *Alan Wake 2* e *Unreal Engine 5* com Nanite) no Adreno 8xx.
5. **Patch `0006` (`tu: Only force sample interpolation when shader uses sample shading` — `src/freedreno/vulkan/tu_shader.cc` de `Hugo223`):**
   * Em `tu_lower_nir()`, altera `if (key->force_sample_interp)` para `if (key->force_sample_interp && nir->info.fs.uses_sample_shading)`, impedindo que o falso-positivo de `sampleShadingEnable` do `vkd3d-proton` force execução por amostra em Fragment Shaders que não utilizam interpolação por amostra (+37,5% de FPS em títulos afetados).

---

### Camada 4: Subsistema Android KGSL (Correções de Syncobj, Poll Timestamp, Sparse VMA, VBO Alias + IB Cache), AIMapper5 UBWC e Governança Térmica/UBO no 8s Gen 4

**Problemas Resolvidos:** Problemas **6.1.2**, **6.1.3**, **6.3.9** e **6.3.10** do Relatório Técnico (Crashes `SIGSEGV` em `kgsl_syncobj_merge` e `kgsl_sparse_vma_init`, bloqueio de CPU por `timeout=0` em `wait_timestamp_safe`, travamentos no kernel `kgsl` ao desalocar buffers de comando, distorção de imagem por falha de detecção UBWC no Gralloc do Android 15/16, estrangulamento de banda de memória LPDDR5X e *thermal throttling* severo no Snapdragon 8s Gen 4).

#### 3.4.1 Correção dos 4 Bugs de Sincronização e Memória no `src/freedreno/vulkan/tu_knl_kgsl.cc` (Descobertos na Auditoria dos Forks `Droid-VM`, `faux123` e `WinterMist010`)
1. **Correção de `kgsl_syncobj_merge()` (`tu_knl_kgsl.cc:1136-1169` — `kgsl-syncobj-merge-ts-fd.patch`):**
```cpp
   case KGSL_SYNCOBJ_STATE_TS:
      if (ret.state == KGSL_SYNCOBJ_STATE_TS) {
         if (ret.queue == sync->queue) {
            if (timestamp_cmp(ret.timestamp, sync->timestamp) < 0)
               ret.timestamp = sync->timestamp;
         } else {
            int ret_fd = kgsl_syncobj_ts_to_fd(&ret);
            int sync_fd = kgsl_syncobj_ts_to_fd(sync);
            ret.state = KGSL_SYNCOBJ_STATE_FD;
            ret.fd = sync_merge_close("tu_sync", ret_fd, sync_fd, true);
         }
      } else {
         int sync_fd = kgsl_syncobj_ts_to_fd(sync);
         ret.fd = sync_merge_close("tu_sync", ret.fd, sync_fd, true);
      }
      break;

   case KGSL_SYNCOBJ_STATE_FD:
      if (ret.state == KGSL_SYNCOBJ_STATE_FD) {
         ret.fd = sync_merge_close("tu_sync", ret.fd, sync->fd, false);
      } else {
         int ret_fd = kgsl_syncobj_ts_to_fd(&ret);
         ret.state = KGSL_SYNCOBJ_STATE_FD;
         ret.fd = sync_merge_close("tu_sync", ret_fd, sync->fd, false);
      }
      break;
```
2. **Eliminação do Bloqueio Infinito por `timeout = 0` em `wait_timestamp_safe()` (`tu_knl_kgsl.cc:833-862` — `Droid-VM/turnip@486c973`):**
   * Adicionar o helper `poll_timestamp(int fd, unsigned int context_id, unsigned int timestamp)` que consulta `IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID` (`KGSL_TIMESTAMP_RETIRED`) e retorna `VK_SUCCESS` se `timestamp_cmp(req.timestamp, timestamp) >= 0` ou `VK_TIMEOUT` caso contrário.
   * Em `wait_timestamp_safe()`, quando `get_relative_ms(abs_timeout_ns) == 0` (tanto na entrada da função quanto após `EINTR`), retornar imediatamente `poll_timestamp(fd, context_id, timestamp)` sem invocar `IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID` com `timeout = 0`!
3. **Inicialização de `dump_bo_list_idx` em `kgsl_sparse_vma_init()` (`Droid-VM/turnip@b43c434`):**
   * Adicionar `tu_dump_bo_init(dev, bo);` dentro de `kgsl_sparse_vma_init()`, garantindo que `bo->dump_bo_list_idx` seja inicializado com `~0` e não cause `SIGSEGV` em `tu_dump_bo_del()` ao destruir VMAs sparse.
4. **Tolerância a `VK_KHR_display` em `tu_knl_kgsl_load()` (`Droid-VM/turnip@bf2112c`):**
   * Remover o retorno de erro `vk_errorf(instance, VK_ERROR_INITIALIZATION_FAILED, "I can't KHR_display")` em `tu_knl_kgsl_load()`.

#### 3.4.2 Eliminação do Hang de Desalocação de Command Streams no KGSL + Cache de IBs Retirados (`0005` + `08-tu-kgsl-cache-retired-a8xx-ib-storage.patch`)
* **Causa Raiz no Adreno 8xx + KGSL:** No Adreno 8xx, liberar a memória de um buffer de comandos (`TU_BO_ALLOC_CMD_STREAM` / Indirect Buffers `ib1`/`ib2`) diretamente via `IOCTL_KGSL_GPUMEM_FREE_ID` causa travamento completo da GPU (*GPU hang*) mesmo quando a GPU já está ociosa, pois o pré-buscador do Command Processor (CP) retém referências especulativas à página no SMMU.
* **Implementação em `src/freedreno/vulkan/tu_knl_kgsl.cc`, `tu_knl.h` e `tu_cs.cc`:**
  * Toda alocação de BO de command stream em `CHIP >= A8XX` cria um **Virtual BO Alias** (`KGSL_MEMFLAGS_VBO | KGSL_MEMFLAGS_VBO_NO_MAP_ZERO` via `IOCTL_KGSL_GPUOBJ_ALLOC`) e mapeia o intervalo físico via `IOCTL_KGSL_GPUMEM_BIND_RANGES` (`KGSL_GPUMEM_RANGE_OP_BIND`).
  * A GPU recebe o endereço virtual (`bo->iova`) do alias.
  * Ao liberar um BO de command stream em `kgsl_bo_finish()`, os BOs aposentados (`check_timestamp >= max_point`) são reciclados em um pool por dispositivo (`a8xx_ib_bo_cache`, até $256\text{ MB}$), e quando precisam ser efetivamente destruídos, o driver executa `KGSL_GPUMEM_RANGE_OP_UNBIND` no alias antes de chamar `IOCTL_KGSL_GPUMEM_FREE_ID`, erradicando 100% dos travamentos por desalocação de command streams sem overhead de syscalls.

#### 3.4.3 Suporte a UBWC_5/UBWC_6, Backend Gralloc AIMapper5 (SP-HAL) e Detecção UBWC Segura no Fallback
1. **Mapeamento `UBWC_5` e `UBWC_6` em `src/freedreno/vulkan/tu_knl_kgsl.cc`:**
   * Adicionar `case 5:` e `case 6:` junto ao `case KGSL_UBWC_4_0:` em `tu_knl_kgsl_load()`, configurando `bank_swizzle_levels = 0x6` e `macrotile_mode = FDL_MACROTILE_8_CHANNEL`.
2. **Backend `u_gralloc_aimapper.c` (`add_aimapper_gralloc.py`) + Detecção UBWC Segura em `u_gralloc_fallback.c` (`01-u_gralloc-always-use-ubwc-detection.patch`):**
   * Carrega a interface estável C `AIMapper_loadIMapper()` v5 diretamente via `android_load_sphal_library()` (`u_gralloc_aimapper.c`).
   * No `u_gralloc_fallback.c`, remove a exigência do magic `'gmsm'` **preservando obrigatoriamente a verificação de limites `if (hnd->handle->numInts >= 2)`** (evitando o bug de leitura fora dos limites do commit `742f5776` do `whitebelyash`).
3. **Bit de Uso UBWC na Alocação de Swapchain (`add_ubwc_swapchain_usage.py` em `src/vulkan/runtime/vk_android.c`):**
   * Injeta o bit de vendor da Qualcomm `ahb_vendor_usage_compressed = 0x10000000` exclusivamente quando `VkAndroidHardwareBufferUsageANDROID` está encadeado na saída de `vk_android_get_ahb_image_properties()` e nenhum bit de acesso de CPU está presente.

#### 3.4.4 Otimizações Específicas Contra o Gargalo de Banda de Memória e Throttling Térmico do Snapdragon 8s Gen 4 (`Adreno 825`)
Para atacar diretamente o problema central do **Snapdragon 8s Gen 4** (barramento LPDDR5X mais estreito, apenas $2\text{ MB}$ de GMEM e chassi intermediário propenso a *thermal throttling* severo após 3 minutos):

1. **Coalescência de Promoção de UBOs no Compilador `ir3` para o Adreno 825 (`src/freedreno/ir3/ir3_compiler.c` e `ir3_nir_analyze_ubo_ranges.c`):**
   * Estender `compiler->coalesce_ubo_push_ranges` para o **Adreno 825 (`chip_id == 0x44030000ull || chip_id == 0xffff44030000ull`)** e **Adreno 829 (`0x44030a20ull`)**.
   * **Mecanismo no Código:** No passo `gather_ubo_ranges()` / `merge_neighbors()`, permite mesclar janelas próximas de *Uniform Buffer Objects* no arquivo de constantes on-chip (`const file`) mesmo quando há um pequeno intervalo (*gap*) entre elas, reduzindo drasticamente leituras de memória externa (`ldc` / UBO fetches na DRAM LPDDR5X).
2. **Política de Autotune (`tu_autotune.cc`), Driconf (`00-turnip-defaults.conf`) e Governança Térmica Consciente (Matriz de 3 Variantes Especializadas):**
   * **Correção da Sabotagem Oculta do `00-turnip-defaults.conf:48`:** Alterar `tu_autotune_algorithm` de `"prefer_sysmem"` para `"bandwidth"` no bloco `DXVK|vkd3d` de `src/freedreno/vulkan/00-turnip-defaults.conf`, permitindo que o autotuner efetivamente utilize a GMEM nos passes de geometria/G-Buffer densos e use `SYSMEM` (agora com `tu_lrz_before_sysmem_br<A8XX>`, `FORCE_BI_DIR_LRZ_DISABLE` e caches CCU corrigidos!) apenas em passes leves.
   * **Especificação das 3 Variantes de Compilação no Pipeline (Matriz GitHub Actions):**
     1. **Variante 1 — Padrão Recomendada: `Turnip-A8xx-8sGen4-Sustained` (`-b` Balanced / GMEM-First):**
        * **Configuração:** `usable_gmem_size_gmem = 1.056 KB` (`66 blocos`), `00-turnip-defaults.conf` em `"bandwidth"`, multiplicador de banda GMEM reduzido no `tu_autotune.cc` para priorizar o uso da SRAM on-chip e **sem** `KGSL_CONSTRAINT_PWR_MAX` forçado (permitindo ao governador DCVS escalar a tensão entre frames).
        * **Alvo:** Uso diário em smartphones com **Snapdragon 8s Gen 4 (`Adreno 825`)** sem cooler externo, economizando até 50% de energia no controlador LPDDR5X e impedindo que o SoC atinja $85^\circ\text{C}$ e sofra *downclock* para $300\text{ MHz}$.
     2. **Variante 2 — Jogos Pesados DX12 / UE5: `Turnip-A8xx-8sGen4-BigGMEM` (`-e` Eco-CCU / Max Tile):**
        * **Configuração:** Inclui toda a base da Variante 1 + aplica em `src/freedreno/vulkan/tu_device.cc` (para GPUs `CHIP == A8XX` com `gmem_size <= 2 MB`, i.e., `Adreno 825` e `829`) a redução sincronizada do Depth CCU em modo GMEM de `HALF` ($512\text{ KB}$) para `QUARTER` (`64 * 1024` por CCU = $256\text{ KB}$ totais), liberando **$1.312\text{ KB}$ (`82 blocos` — 64% de toda a SRAM física)** para tiles!
        * **Alvo:** Jogos DirectX 12 / Unreal Engine 5 com *Deferred Shading* pesado (múltiplos Render Targets de 64/32 bits simultâneos) que estourariam os $1.056\text{ KB}$ normais e cairiam para `sysmem`.
     3. **Variante 3 — Força Bruta (Com Cooler): `Turnip-A8xx-8sGen4-MaxPerf` (`-p` Performance `PWR_MAX`):**
        * **Configuração:** Inclui toda a base + injeta `KGSL_CONTEXT_PWR_CONSTRAINT` (`KGSL_CONSTRAINT_PWR_MAX` com refresh temporal de $40\text{ ms}$ em `tu_knl_kgsl.cc`), travando a GPU e o barramento no maior P-State possível continuamente.
        * **Alvo:** Exclusivo para usuários com cooler Peltier externo ou aparelhos com ventoinha ativa.

---

## 4. Roteiro Passo a Passo de Execução e Verificação (Workflow de Engenharia)

Quando este plano for executado, deverá seguir estritamente a sequência abaixo:

### Fase 1: Preparação da Árvore Base (`mesa/main`)
1. Clonar o repositório oficial `https://gitlab.freedesktop.org/mesa/mesa.git` na branch `main` (commit `>= d520ae90`).
2. Validar a presença dos commits nativos obrigatórios na árvore clonada:
   * `5b2db4b8` (`freedreno/fdl: Use NUM_ELEMENTS for A8XX buffer descriptors`)
   * `2ce86eed` (`tu/lrz: Fix partial LRZ fast-clear on A8XX`)
   * `e1852a33` (`tu/lrz: Align LRZ pitch to 32 instead of 64 on A8XX`)
   * `14656cee` & `7638039f` (`tu: Split large indirect [count] draws on A8xx`)
   * `1da50a1b` & `e984ef29` (commits base de `kgsl_syncobj_merge` e `kgsl_poll_timestamp`)

### Fase 2: Aplicação dos Patches de Arquitetura A8xx (Camadas 1 a 4)
1. **Cherry-pick dos MRs Upstream Pendentes:**
   * Aplicar diff do MR `!45937` (`WFI before reading registers that were just written`).
   * Aplicar diff do MR `!45973` (`Workaround the 2-bit alpha precision of 10_10_10_2_UNORM on A8XX KGSL`).
2. **Correção dos Bugs de LRZ SYSMEM, Coerência Bidirecional, `SP_*_HYSTERESIS` e Condicionais `<A7XX>` Residuais:**
   * Em `src/freedreno/vulkan/tu_lrz.cc:852-876` (`tu_lrz_before_sysmem_br<CHIP>`): proteger o bloco `else` com `else if constexpr (CHIP >= A7XX)` e substituir as 3 ocorrências de `fd_lrzfc_layout<A7XX>` por `fd_lrzfc_layout<CHIP>`.
   * Em `src/freedreno/vulkan/tu_cmd_buffer.cc`: emitir `SP_VS/HS/DS/GS/CS_HYSTERESIS(0x400)` e `SP_PS_HYSTERESIS(0xc00)` em `tu6_init_hw<A8XX>` (`54`/`55` de `Vauzi-17`), setar `.force_bi_dir_lrz_disable` em `tu6_emit_bin_size` e `tu6_sysmem_render_begin` (`61` de `Vauzi-17`), e substituir `<A7XX>` por `<CHIP>` em `tu_emit_rt_workaround` e `tu_emit_subpass_fsr`.
   * Em `src/freedreno/vulkan/tu_pipeline.cc`: emitir `A6XX_GRAS_LRZ_COLOR_COMP_MASK(mrt_comp_mask)` em `tu6_emit_mrt_blend_state` (`62` de `Vauzi-17`) e alterar `CHIP == A7XX` para `CHIP >= A7XX` em `tu_binning_conservative_rast<CHIP>`.
   * Em `src/freedreno/vulkan/tu_image.cc` (`tu_image_init`): proteger `TILE6_3` em imagens `MUTABLE_FORMAT` com `DRM_FORMAT_MOD_QCOM_COMPRESSED` em `CHIP >= A8XX` (`30-tu-z-mutable.py`).
   * Em `src/freedreno/vulkan/tu_query_pool.cc:2178`: substituir `tu_emit_cache_flush<A7XX>(cmd)` por `TU_CALLX(cmd->device, tu_emit_cache_flush)(cmd)`.
3. **Aplicação da Série `a8xx-winnative` (0001 a 0005) + `08` IB Cache + `0006` Sample Shading Gate:**
   * `0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch`
   * `0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch`
   * `0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch`
   * `0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch`
   * `0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch` + `08-tu-kgsl-cache-retired-a8xx-ib-storage.patch`
   * `0006-tu-sample-shading-gate.patch` (`key->force_sample_interp && nir->info.fs.uses_sample_shading` em `tu_shader.cc`)
4. **Aplicação das Correções Críticas de KGSL (`tu_knl_kgsl.cc`) e Gralloc / UBWC Android:**
   * Aplicar `kgsl-syncobj-merge-ts-fd.patch` (corrige `SIGSEGV` e `ret.fd` inválido em `kgsl_syncobj_merge`).
   * Aplicar `kgsl-zero-timeout-poll.patch` / `Droid-VM@486c973` (substitui `wait.timeout = 0` por `poll_timestamp` não-bloqueante em `wait_timestamp_safe`).
   * Aplicar `Droid-VM@b43c434` (`tu_dump_bo_init(dev, bo)` em `kgsl_sparse_vma_init`) e `Droid-VM@bf2112c` (tolerar `VK_KHR_display` em `tu_knl_kgsl_load`).
   * Aplicar `add_aimapper_gralloc.py` (`u_gralloc_aimapper.c` via SP-HAL), `01-u_gralloc-always-use-ubwc-detection.patch` (remoção da trava `'gmsm'` em `u_gralloc_fallback.c` **mantendo** `if (hnd->handle->numInts >= 2)`), `add_ubwc_swapchain_usage.py` e `case 5:`/`case 6:` (`UBWC_5`/`UBWC_6`) em `tu_knl_kgsl.cc`.
5. **Aplicação da Calibração Dedicada do Adreno 825 (Snapdragon 8s Gen 4) e A8xx:**
   * Inserir `[A6XXRegs.REG_A8XX_RB_RESOLVE_CR_CNTL, 0x00000001]` em `a8xx_base_raw_magic_regs` (`52-a8xx-resolve-cr-cntl.py`).
   * Inserir `a8xx_825` e `GPUId(0x44030000 / 0xffff44030000)` em `src/freedreno/common/freedreno_devices.py` e `src/freedreno/drm-shim/freedreno_noop.c` com `tile_align_w = 64`, `tile_max_w = 16384`, `has_fs_tex_prefetch = False`, `supports_double_threadsize = False`, e frações CCU `HALF` ($128\text{ KB}$) / `EIGHTH` ($16\text{ KB}$) matematicamente sincronizadas (corrigindo também os overrides do `Adreno 829`).
   * Garantir que `src/freedreno/common/fd6_gmem_cache.h` **NÃO** contenha `offset -= 0x78000` e inserir asserção anti-underflow.
   * Ativar `coalesce_ubo_push_ranges` para `0x44030000` (Adreno 825) e `0x44030a20` (Adreno 829) em `src/freedreno/ir3/ir3_compiler.c`.
   * Atualizar `src/freedreno/vulkan/00-turnip-defaults.conf` (`tu_autotune_algorithm = "bandwidth"` para `DXVK|vkd3d`) e `src/freedreno/vulkan/tu_autotune.cc` para engajar GMEM em render passes densos sem forçar `TU_DEBUG=sysmem` ou `TU_DEBUG=nolrz`.

### Fase 3: Compilação Cross-Target (Android NDK r29 / SDK 34–36 via GitHub Actions `gh`)
Seguindo a regra de compilação priorizada via GitHub Actions (`compilacao-github-cli`), o build de `libvulkan_freedreno.so` será configurado com Meson + Ninja para `aarch64-linux-android`:
```bash
meson setup build-android-aarch64 \
  --cross-file android-aarch64.txt \
  --native-file native.txt \
  -Dbuildtype=release \
  -Dstrip=true \
  -Dplatforms=android \
  -Dplatform-sdk-version=36 \
  -Dandroid-stub=true \
  -Dgallium-drivers= \
  -Dvulkan-drivers=freedreno \
  -Dvulkan-beta=true \
  -Dfreedreno-kmds=kgsl \
  -Degl=disabled \
  -Dandroid-libbacktrace=disabled
ninja -C build-android-aarch64 install
```

### Fase 4: Critérios de Verificação e Validação Rigorosa
1. **Verificação Estática de Código e Invariantes (Pré-Build):**
   * Validar sintaxe de `freedreno_devices.py` via `python3 -c "compile(open('src/freedreno/common/freedreno_devices.py').read(), 'f', 'exec')"`.
   * Executar teste unitário/simulação via `drm-shim` (`FD_DRM_SHIM_GPU_ID=825`) validando que `fd6_calc_gmem_cache_offsets` retorna `usable_gmem_size_gmem = 1081344` ($1.056\text{ KB}$) sem underflow em `sysmem` (`depth_ccu_offset = 163840` = $160\text{ KB}$).
   * Confirmar ausência de `supports_double_threadsize = True` em `a8xx_base` e ausência de funções órfãs de LLM em `ir3_compiler.c`.
2. **Verificação em Dispositivo Real (Snapdragon 8s Gen 4 / Adreno 825 — Winlator / Eden):**
   * Executar **sem** as flags paliativas `TU_DEBUG=sysmem` e `TU_DEBUG=nolrz`.
   * Inspecionar logs com `TU_DEBUG=startup,gmem` confirmando detecção de `Adreno (TM) 825 (chip_id = 0x44030000)`, alocação de GMEM ativa (`gmem_size=2097152 usable_gmem=1081344 blocks=66`) e ausência de *Write Page Faults* em `/dev/kgsl-3d0`.
   * Validar ausência de travamento em `vkWaitSemaphores` (`wait_timestamp_safe` com `timeout=0`), liberação limpa de recursos Sparse D3D12 (`kgsl_sparse_vma_init`), renderização de sombras/materiais `A2B10G10R10_UNORM` e estabilidade de frame time em sessões $>15\text{ minutos}$ (Status atual: *not tested* em hardware físico até a execução da implementação).
