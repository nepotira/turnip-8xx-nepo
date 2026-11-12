# Auditoria dos 28 Pontos de Switch 1 e Adreno 8xx (Mesa Pós-Patch `maxperf`)

Data: 2026-11-12  
Ramo: `chore/12-switch1-28points-audit`  
Base Mesa: `35a0fef1`

---

## PASSO 1 — Inventário Completo de Patches e Camadas Atuais

```text
=== 1.1 ARQUIVOS EM patches/ ===
  patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch (104936 bytes)
  patches/0001A-tu-Mark-compute-state-stale-when-a-secondary-execute.patch (1839 bytes)
  patches/0001B-tu-mesh-Size-chunk-tables-per-pipeline-and-advertise.patch (11045 bytes)
  patches/0001C-tu-mesh-Only-flush-for-the-CP-after-the-setup-dispat.patch (2942 bytes)
  patches/0001D-tu-mesh-Skip-vertex-and-primitive-fetches-for-dead-c.patch (5211 bytes)
  patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch (19099 bytes)
  patches/0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch (4813 bytes)
  patches/0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch (3653 bytes)
  patches/0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch (4803 bytes)
  patches/0006-tu-sample-shading-gate.patch (2723 bytes)
  patches/0007-u_gralloc-always-use-ubwc-detection.patch (1749 bytes)
  patches/0008-tu-mesh-Experimental-indexed-draw-for-mesh-shaders-w.patch (19763 bytes)
  patches/0009-tu-mesh-Wait-for-the-ME-before-indirect-chunk-draws.patch (1875 bytes)
  patches/08-tu-kgsl-cache-retired-a8xx-ib-storage.patch (7346 bytes)
  patches/15-wn-add-aimapper-gralloc.py (4233 bytes)
  patches/16-wn-add-ubwc-swapchain-usage.py (9074 bytes)
  patches/30-tu-z-mutable.py (2348 bytes)
  patches/52-a8xx-resolve-cr-cntl.py (1871 bytes)
  patches/54-a8xx-sp-hysteresis.py (2117 bytes)
  patches/55-a8xx-sp-hysteresis-gs-hs-ds.py (2171 bytes)
  patches/56-a8xx-shader-perf-and-compilation.py (2294 bytes)
  patches/57-a8xx-switch2-dlss-extensions.py (2492 bytes)
  patches/58-a8xx-conservative-rast.py (1553 bytes)
  patches/59-a8xx-ir3-coalesce-ubo-push-ranges.py (1872 bytes)
  patches/60-a8xx-sanitize-frag-nan.py (5250 bytes)
  patches/61-a8xx-lrz-bidir-disable.py (3427 bytes)
  patches/62-a8xx-lrz-color-comp-mask.py (3113 bytes)
  patches/63-tu-framebuffer-attachment-extent-guard.py (5320 bytes)
  patches/64-tu-depth-blit-features.py (2260 bytes)
  patches/65-nepo-hl-mk1-color-and-perf.py (9678 bytes)
  patches/__pycache__/15-wn-add-aimapper-gralloc.cpython-312.pyc (5026 bytes)
  patches/__pycache__/16-wn-add-ubwc-swapchain-usage.cpython-312.pyc (9748 bytes)
  patches/__pycache__/30-tu-z-mutable.cpython-312.pyc (3109 bytes)
  patches/__pycache__/52-a8xx-resolve-cr-cntl.cpython-312.pyc (2654 bytes)
  patches/__pycache__/54-a8xx-sp-hysteresis.cpython-312.pyc (2865 bytes)
  patches/__pycache__/55-a8xx-sp-hysteresis-gs-hs-ds.cpython-312.pyc (3040 bytes)
  patches/__pycache__/56-a8xx-shader-perf-and-compilation.cpython-312.pyc (3131 bytes)
  patches/__pycache__/57-a8xx-switch2-dlss-extensions.cpython-312.pyc (3354 bytes)
  patches/__pycache__/58-a8xx-conservative-rast.cpython-312.pyc (2367 bytes)
  patches/__pycache__/59-a8xx-ir3-coalesce-ubo-push-ranges.cpython-312.pyc (2735 bytes)
  patches/__pycache__/60-a8xx-sanitize-frag-nan.cpython-312.pyc (5938 bytes)
  patches/__pycache__/61-a8xx-lrz-bidir-disable.cpython-312.pyc (4262 bytes)
  patches/__pycache__/62-a8xx-lrz-color-comp-mask.cpython-312.pyc (3751 bytes)
  patches/__pycache__/63-tu-framebuffer-attachment-extent-guard.cpython-312.pyc (6256 bytes)
  patches/__pycache__/64-tu-depth-blit-features.cpython-312.pyc (2834 bytes)
  patches/__pycache__/65-nepo-hl-mk1-color-and-perf.cpython-312.pyc (11139 bytes)
  patches/aimapper/u_gralloc_aimapper.c (19730 bytes)
  patches/eden-optimizations-unified.patch (9791 bytes)
  patches/kgsl-syncobj-merge-ts-fd.patch (1925 bytes)
  patches/kgsl-zero-timeout-poll.patch (1453 bytes)
  patches/mr45937-tu-a8xx-wfi-before-reading-registers.patch (3865 bytes)
  patches/mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch (53014 bytes)

=== 1.2 ESTRUTURA DE scripts/apply_all_patches.py ===
  funcao: record
  funcao: edit_file_idempotent
  funcao: apply_git_patches
  funcao: apply_python_patches
  funcao: apply_layer1_silicon_and_gmem
  funcao: apply_layer2_pipeline_and_lrz
  funcao: apply_layer3_and_4_kgsl_and_autotune
  funcao: main

=== 1.3 ARQUIVOS TOCADOS POR eden-optimizations-unified.patch ===
  src/video_core/renderer_vulkan/vk_pipeline_cache.cpp
  src/video_core/renderer_vulkan/vk_pipeline_cache.h
  src/video_core/renderer_vulkan/vk_scheduler.h
  src/video_core/renderer_vulkan/vk_swapchain.cpp
  src/video_core/textures/decoders.cpp
```

---

## PASSO 2 — Auditoria dos 28 Mecanismos no Mesa Pós-Patch (`maxperf`)

`APPLY_EXIT=0`

```text
=== TABELA DOS 28 PONTOS (UPSTREAM vs POS-PATCH MAXPERF) ===
ID | NOME                             | DIFF_NO_PATCH? | MATCH_POS_PATCH?
--------------------------------------------------------------------------------
01 | IR3_SCHED_LOWER_LIVE             | INTACTO        | SIM (live_effect)
02 | IR3_GCM_ENABLED                  | INTACTO        | NAO
03 | IR3_ONLY_UBO_PREFETCH            | INTACTO        | NAO
04 | TU_REMOVE_TEX_PREFETCH           | MODIFICADO     | NAO
05 | IR3_COALESCE_UBO_RANGES          | MODIFICADO     | NAO
06 | TU_SAMPLE_SHADING_GATE           | MODIFICADO     | SIM (uses_sample_shading)
07 | A8XX_CUBE_COORD_SANITIZE         | MODIFICADO     | SIM (cube)
08 | PIPELINE_SUBALLOC_512K_1M        | MODIFICADO     | NAO
09 | LRZ_KEEP_ON_LOAD_OP_LOAD         | MODIFICADO     | NAO
10 | LRZ_RESCUE_IN_RP_CLEAR           | MODIFICADO     | SIM (tu_lrz_clear)
11 | LRZ_REUSE_DONT_CARE_SYSMEM       | MODIFICADO     | NAO
12 | MUTABLE_FORMAT_KEEP_UBWC         | MODIFICADO     | SIM (VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT)
13 | LRZ_FS_SIDEEFFECTS_NO_INVAL      | MODIFICADO     | NAO
14 | LRZ_DIR_CHANGE_NO_INVAL          | MODIFICADO     | SIM (prev_direction)
15 | SKIP_IDENTICAL_DRAW_STATE        | MODIFICADO     | SIM (TU_DRAW_STATE_DYNAMIC)
16 | AUTOTUNE_HYSTERESIS_OR_NO_PP     | MODIFICADO     | SIM (history)
17 | SWITCH_PRESENTER_SYSMEM_FAST     | MODIFICADO     | SIM (use_sysmem_rendering)
18 | U_GRALLOC_ALWAYS_UBWC            | MODIFICADO     | SIM (DRM_FORMAT_MOD_QCOM_COMPRESSED)
19 | WSI_SWAPCHAIN_UBWC_USAGE         | MISSING_FILE   | MISSING (src/vulkan/wsi/wsi_common_android.c)
20 | KGSL_ZERO_TIMEOUT_POLL           | MODIFICADO     | SIM (kgsl_poll_timestamp)
21 | KGSL_SYNCOBJ_MERGE_FIX           | MODIFICADO     | SIM (kgsl_syncobj_merge)
22 | SYSMEM_WFI_TO_WAIT_FOR_ME        | MODIFICADO     | NAO
23 | A8XX_NO_DOUBLE_THREADSIZE        | MODIFICADO     | SIM (supports_double_threadsize = False)
24 | A8XX_SUBGROUP_HALF_WARP          | MODIFICADO     | SIM (subgroup_size)
25 | A8XX_BINDLESS_INVALIDATE_REG     | MODIFICADO     | SIM (BINDLESS_INVALIDATE)
26 | A8XX_KGSL_IB_VBO_ALIAS           | MODIFICADO     | SIM (GPUMEM_FREE_ID)
27 | A8XX_SP_HYSTERESIS_AND_CR        | MODIFICADO     | SIM (HYSTERESIS)
28 | A8XX_ENFORCE_NOCB_OR_DISABLE_GMEM | MODIFICADO     | SIM (disable_gmem)
```

---

## PASSO 3 — Snippets Exatos de Código (Âncoras Reais)

```text
==================== SNIPPET_1_PIPELINE_SUBALLOC (src/freedreno/vulkan/tu_device.cc) ====================
 3155:    }
 3156: 
 3157:    if (device->vk.enabled_features.customBorderColors)
 3158:       global_size += TU_BORDER_COLOR_COUNT * sizeof(struct bcolor_entry);
 3159: 
 3160:    tu_bo_suballocator_init(
 3161:       &device->pipeline_suballoc, device, 128 * 1024,
 3162:       static_cast<enum tu_bo_alloc_flags>(TU_BO_ALLOC_GPU_READ_ONLY |
 3163:                                           TU_BO_ALLOC_ALLOW_DUMP |
 3164:                                           TU_BO_ALLOC_INTERNAL_RESOURCE |
 3165:                                           tu_bo_ib_flags(device)),
 3166:       "pipeline_suballoc");
 3167:    if (is_kgsl(physical_device->instance)) {
 3168:       tu_bo_suballocator_init(&device->kgsl_profiling_suballoc, device,
------------------------------------------------------------

==================== SNIPPET_2_MUTABLE_FORMAT_UBWC (src/freedreno/vulkan/tu_image.cc) ====================
  600:     * This is a problem with UBWC (compression for different formats is different),
  601:     * but also tiling ("swap" affects how tiled formats are stored in memory)
  602:     * Depth and stencil formats cannot be reintepreted as another format, and
  603:     * cannot be linear with sysmem rendering, so don't fall back for those.
  604:     *
  605:     * TODO:
  606:     * - if the fmt_list contains only formats which are swapped, but compatible
  607:     *   with each other (B8G8R8A8_UNORM and B8G8R8A8_UINT for example), then
  608:     *   tiling is still possible
  609:     */
  610:    if ((pCreateInfo->flags & VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT) &&
  611:        !vk_format_is_depth_or_stencil(image->vk.format)) {
  612:       const VkImageFormatListCreateInfo *fmt_list =
  613:          vk_find_struct_const(pCreateInfo->pNext, IMAGE_FORMAT_LIST_CREATE_INFO);
  614:       if (!tu6_mutable_format_list_ubwc_compatible(device->physical_device->info,
  615:                                                    fmt_list)) {
  616:          /* NEPO_65_MUTABLE_UBWC: Keep UE4/Switch R11G11B10, RGBA8, BGRA8, RGB10A2 and RGBA16F
  617:           * mutable render targets in Tiled+UBWC mode to preserve color LUT & SceneColor precision.
  618:           */
  619:          bool mutable_ubwc_fc = device->physical_device->info->props.ubwc_all_formats_compatible ||
  620:             ((!fmt_list || fmt_list->viewFormatCount <= 2) &&
  621:              (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||
  622:               image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||
  623:               image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||
  624:               image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||
  625:               image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||
  626:               image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||
  627:               image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));
  628: 
  629:          /* NV12 uses a special compression scheme for the Y channel which
  630:           * doesn't support reinterpretation. We have to fall back to linear
  631:           * always.
  632:           */
  633:          if (pCreateInfo->format == VK_FORMAT_G8_B8R8_2PLANE_420_UNORM) {
  634:             if (ubwc_enabled) {
------------------------------------------------------------

==================== SNIPPET_3_LRZ_BEGIN_RP (src/freedreno/vulkan/tu_lrz.cc) ====================
ANCORA 'VK_ATTACHMENT_LOAD_OP_DONT_CARE' NAO ENCONTRADA EM src/freedreno/vulkan/tu_lrz.cc

==================== SNIPPET_4_LRZ_SIDEEFFECTS (src/freedreno/vulkan/tu_lrz.cc) ====================
ANCORA 'has_side_effects' NAO ENCONTRADA EM src/freedreno/vulkan/tu_lrz.cc

==================== SNIPPET_5_USE_SYSMEM_RENDERING (src/freedreno/vulkan/tu_cmd_buffer.cc) ====================
 1132:    struct tu_physical_device *phys_dev = cmd->device->physical_device;
 1133:    const VkRect2D *render_area = &cmd->state.render_areas[view];
 1134: 
 1135:    /* Avoid assertion fails with an empty render area at (0, 0) where the
 1136:     * subtraction below wraps around. Empty render areas should be forced to
 1137:     * the sysmem path by use_sysmem_rendering(). It's not even clear whether
 1138:     * an empty scissor here works, and the blob seems to force sysmem too as
 1139:     * it sets something wrong (non-empty) for the scissor.
 1140:     */
 1141:    if (render_area->extent.width == 0 ||
 1142:        render_area->extent.height == 0)
 1143:       return;
 1144: 
 1145:    uint32_t x1 = render_area->offset.x;
 1146:    uint32_t y1 = render_area->offset.y;
 1147:    uint32_t x2 = x1 + render_area->extent.width - 1;
 1148:    uint32_t y2 = y1 + render_area->extent.height - 1;
 1149: 
 1150:    if (align) {
 1151:       x1 = x1 & ~(phys_dev->info->gmem_align_w - 1);
 1152:       y1 = y1 & ~(phys_dev->info->gmem_align_h - 1);
 1153:       x2 = ALIGN_POT(x2 + 1, phys_dev->info->gmem_align_w) - 1;
 1154:       y2 = ALIGN_POT(y2 + 1, phys_dev->info->gmem_align_h) - 1;
 1155:    }
 1156: 
 1157:    tu_cs_emit_regs(cs,
 1158:                    A6XX_RB_RESOLVE_CNTL_1(.x = x1, .y = y1),
 1159:                    A6XX_RB_RESOLVE_CNTL_2(.x = x2, .y = y2));
 1160: }
 1161: 
 1162: template <chip CHIP>
 1163: void
 1164: tu6_emit_window_scissor(struct tu_cs *cs,
 1165:                         uint32_t x1,
 1166:                         uint32_t y1,
 1167:                         uint32_t x2,
 1168:                         uint32_t y2)
 1169: {
 1170:    tu_cs_emit_regs(cs,
 1171:                    GRAS_SC_WINDOW_SCISSOR_TL(CHIP, .x = x1, .y = y1),
 1172:                    GRAS_SC_WINDOW_SCISSOR_BR(CHIP, .x = x2, .y = y2));
 1173: 
 1174:    tu_cs_emit_regs(cs,
 1175:                    GRAS_A2D_SCISSOR_TL(CHIP, .x = x1, .y = y1),
 1176:                    GRAS_A2D_SCISSOR_BR(CHIP, .x = x2, .y = y2));
 1177: }
 1178: TU_GENX(tu6_emit_window_scissor);
 1179: 
 1180: template <chip CHIP>
 1181: void
------------------------------------------------------------

==================== SNIPPET_6_IR3_SCHED_NODE (src/freedreno/ir3/ir3_sched.c) ====================
  151:     * register pressure (or at least are neutral)
  152:     */
  153:    bool output;
  154: };
  155: 
  156: #define foreach_sched_node(__n, __list)                                        \
  157:    list_for_each_entry (struct ir3_sched_node, __n, __list, dag.link)
  158: 
  159: static void sched_node_init(struct ir3_sched_ctx *ctx,
  160:                             struct ir3_instruction *instr);
  161: static void sched_node_add_dep(struct ir3_sched_ctx *ctx,
  162:                                struct ir3_instruction *instr,
  163:                                struct ir3_instruction *src, int i);
  164: 
  165: static bool
  166: is_scheduled(struct ir3_instruction *instr)
  167: {
  168:    return !!(instr->flags & IR3_INSTR_MARK);
  169: }
  170: 
  171: /* check_src_cond() passing the user and ir3_sched_ctx. */
  172: static bool
  173: sched_check_src_cond(struct ir3_instruction *instr,
  174:                      bool (*cond)(struct ir3_instruction *,
  175:                                   struct ir3_instruction *,
  176:                                   struct ir3_sched_ctx *),
  177:                      struct ir3_sched_ctx *ctx)
  178: {
  179:    foreach_ssa_src (src, instr) {
  180:       /* meta:split/collect aren't real instructions, the thing that
  181:        * we actually care about is *their* srcs
  182:        */
  183:       if ((src->opc == OPC_META_SPLIT) || (src->opc == OPC_META_COLLECT)) {
  184:          if (sched_check_src_cond(src, cond, ctx))
  185:             return true;
  186:       } else {
  187:          if (cond(src, instr, ctx))
  188:             return true;
  189:       }
  190:    }
------------------------------------------------------------

==================== SNIPPET_7_IR3_COMPILER_CREATE (src/freedreno/ir3/ir3_compiler.c) ====================
  218:    static util_once_flag once = UTIL_ONCE_FLAG_INIT;
  219:    util_call_once(&once, __debug_init);
  220: }
  221: 
  222: struct ir3_compiler *
  223: ir3_compiler_create(struct fd_device *dev, const struct fd_dev_id *dev_id,
  224:                     const struct fd_dev_info *dev_info,
  225:                     const struct ir3_compiler_options *options)
  226: {
  227:    struct ir3_compiler *compiler = rzalloc(NULL, struct ir3_compiler);
  228: 
  229:    ir3_compiler_debug_init();
  230: 
  231:    compiler->dev = dev;
  232:    compiler->dev_id = dev_id;
  233:    compiler->gen = fd_dev_gen(dev_id);
  234:    compiler->is_64bit = fd_dev_64b(dev_id);
  235:    compiler->options = *options;
  236:    compiler->info = dev_info;
  237: 
  238:    /* TODO see if older GPU's were different here */
  239:    compiler->branchstack_size = dev_info->props.has_dual_wave_dispatch ? 512 : 256;
  240:    compiler->max_branchstack = 64;
  241: 
  242:    compiler->max_variable_workgroup_size = 1024;
  243: 
  244:    compiler->num_predicates = 1;
  245:    compiler->bitops_can_write_predicates = false;
  246:    compiler->has_branch_and_or = false;
  247:    compiler->has_rpt_bary_f = false;
  248:    compiler->has_alias_tex = false;
  249:    compiler->delay_slots.alu_to_alu = 3;
  250:    compiler->delay_slots.non_alu = 6;
  251:    compiler->delay_slots.cat3_src2_read = 2;
  252: 
------------------------------------------------------------

==================== SNIPPET_8_A8XX_BASE_PROPS (src/freedreno/common/freedreno_devices.py) ====================
 1404:     ))
 1405: 
 1406: a8xx_base = GPUProps(
 1407:         has_dp2acc = False,
 1408:         reg_size_vec4 = 96,
 1409:         has_rt_workaround = False,
 1410:         supports_double_threadsize = False,
 1411:         has_dual_wave_dispatch = True,
 1412:         round_robin_errata = False,
 1413:         max_texel_buffer_range_elements = (1 << 29) - 1,
 1414:         max_storage_buffer_range_bytes = (1 << 31) - 1,
 1415:         cube_coord_hang_quirk = True,
 1416: 
 1417:         QCTDD10204462 = False,
 1418:         QCTDD11147232 = False,
 1419:     )
 1420: 
 1421: # For a8xx, the chicken bit and most other non-ctx reg
 1422: # programming moves into the kernel, and what remains
 1423: # should be easier to share between devices
 1424: a8xx_base_raw_magic_regs = [
 1425:         [A6XXRegs.REG_A8XX_GRAS_BIN_FOVEAT_XY_FDM_OFFSET + 0, 0x00000000],
 1426:         [A6XXRegs.REG_A8XX_GRAS_BIN_FOVEAT_XY_FDM_OFFSET + 1, 0x00000000],
 1427:         [A6XXRegs.REG_A8XX_GRAS_BIN_FOVEAT_XY_FDM_OFFSET + 2, 0x00000000],
 1428:         [A6XXRegs.REG_A8XX_GRAS_BIN_FOVEAT_XY_FDM_OFFSET + 3, 0x00000000],
 1429:         [A6XXRegs.REG_A8XX_GRAS_BIN_FOVEAT_XY_FDM_OFFSET + 4, 0x00000000],
 1430:         [A6XXRegs.REG_A8XX_GRAS_BIN_FOVEAT_XY_FDM_OFFSET + 5, 0x00000000],
 1431: 
 1432:         [A6XXRegs.REG_A6XX_RB_UNKNOWN_8818,   0x00000000],
 1433:         [A6XXRegs.REG_A6XX_RB_UNKNOWN_8819,   0x00000000],
 1434:         [A6XXRegs.REG_A6XX_RB_UNKNOWN_881A,   0x00000000],
 1435:         [A6XXRegs.REG_A6XX_RB_UNKNOWN_881B,   0x00000000],
 1436:         [A6XXRegs.REG_A6XX_RB_UNKNOWN_881C,   0x00000000],
 1437:         [A6XXRegs.REG_A6XX_RB_UNKNOWN_881D,   0x00000000],
 1438:         [A6XXRegs.REG_A6XX_RB_UNKNOWN_881E,   0x00000000],
 1439:         [A6XXRegs.REG_A7XX_RB_LRZ_CNTL2,      0x00000000],
 1440:         [A6XXRegs.REG_A8XX_RB_RESOLVE_CR_CNTL, 0x00000001],
------------------------------------------------------------

==================== SNIPPET_9_A825_PROPS (src/freedreno/common/freedreno_devices.py) ====================
 1653:         fibers_per_sp = 128 * 2 * 16,
 1654:         raw_magic_regs = a8xx_base_raw_magic_regs,
 1655:     ))
 1656: 
 1657: add_gpus([
 1658:         GPUId(chip_id=0x44030000, name="Adreno (TM) 825"), # Snapdragon 8s Gen 4 (SM8735)
 1659:         GPUId(chip_id=0xffff44030000, name="Adreno (TM) 825"),
 1660:     ], A6xxGPUInfo(
 1661:         CHIP.A8XX,
 1662:         [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen1, GPUProps(
 1663:             sysmem_vpc_attr_buf_size = 32768,
 1664:             sysmem_vpc_pos_buf_size = 16384,
 1665:             sysmem_vpc_bv_pos_buf_size = 16384,
 1666:             sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,
 1667:             sysmem_per_ccu_color_cache_size = 64 * 1024,
 1668:             sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,
 1669:             sysmem_per_ccu_depth_cache_size = 128 * 1024,
 1670:             gmem_vpc_attr_buf_size = 16384,
 1671:             gmem_vpc_pos_buf_size = 12288,
 1672:             gmem_vpc_bv_pos_buf_size = 16384,
 1673:             gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
 1674:             gmem_per_ccu_color_cache_size = 16 * 1024,
 1675:             gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.QUARTER.value,
 1676:             gmem_per_ccu_depth_cache_size = 64 * 1024,
 1677:             has_fs_tex_prefetch = False,
 1678:             supports_double_threadsize = False,
 1679:             has_early_preamble = False,
 1680:         )],
 1681:         num_ccu = 4,
 1682:         num_slices = 2,
 1683:         tile_align_w = 64,
 1684:         tile_align_h = 32,
 1685:         tile_max_w = 16384,
 1686:         tile_max_h = 16384,
 1687:         num_vsc_pipes = 32,
 1688:         cs_shared_mem_size = 32 * 1024,
 1689:         wave_granularity = 2,
 1690:         fibers_per_sp = 128 * 2 * 16,
 1691:         raw_magic_regs = a8xx_base_raw_magic_regs,
 1692:     ))
------------------------------------------------------------

==================== SNIPPET_10_AUTOTUNE (src/freedreno/vulkan/tu_autotune.cc) ====================
ANCORA 'tu_autotune_use_bypass(' NAO ENCONTRADA EM src/freedreno/vulkan/tu_autotune.cc
```
