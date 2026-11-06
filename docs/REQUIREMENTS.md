# Requisitos do Sistema (`REQUIREMENTS.md`)

## Requisitos Funcionais
- **RF-01:** Mapear nativamente o **Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`, `chip_id = 0x44030000`)** no `freedreno_devices.py` e `freedreno_noop.c` com geometria exata de 2 fatias (`num_slices = 2`, `num_ccu = 4`, `tile_align_w = 64`, `tile_max_w = 16384`).
- **RF-02:** Sincronizar matematicamente os enums de `RB_CCU_CACHE_CNTL` com os tamanhos subtraídos em `fd6_calc_gmem_cache_offsets`, garantindo ausência de *underflow* e liberando $1.056\text{ KB}$ (`Sustained`) a $1.312\text{ KB}$ (`BigGMEM`) para tiles na GMEM de $2\text{ MB}$.
- **RF-03:** Corrigir o layout `fd_lrzfc_layout<CHIP>` em `tu_lrz_before_sysmem_br<CHIP>()` e emitir `FORCE_BI_DIR_LRZ_DISABLE` + `GRAS_LRZ_COLOR_COMP_MASK` para operação estável do LRZ sem `TU_DEBUG=nolrz`.
- **RF-04:** Corrigir os 4 bugs de sincronização/memória no `tu_knl_kgsl.cc` (`kgsl_syncobj_merge`, `wait_timestamp_safe` `timeout=0`, `kgsl_sparse_vma_init` `tu_dump_bo_init` e `VK_KHR_display`) mais VBO alias e cache de IBs retirados.
- **RF-05:** Produzir 3 variantes instaláveis via AdrenoTools (`Sustained`, `BigGMEM` e `MaxPerf`).
