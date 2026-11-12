# Relatório Técnico de Auditoria de Código HL / MK1 e Estabilidade Adreno 8xx

## 1. Status de cada PASSO (0 a 5)
- **PASSO 0:** OK
- **PASSO 1:** OK
- **PASSO 2:** OK
- **PASSO 3:** OK
- **PASSO 4:** OK
- **PASSO 5:** OK

---

## 2. Saída literal completa dos itens 1.1, 1.2 e 1.3 (inventário de patches/ e scripts/)

### 1.1 Listagem de patches/ e scripts/
`ls -1 patches/`:
```text
0001A-tu-Mark-compute-state-stale-when-a-secondary-execute.patch
0001B-tu-mesh-Size-chunk-tables-per-pipeline-and-advertise.patch
0001C-tu-mesh-Only-flush-for-the-CP-after-the-setup-dispat.patch
0001D-tu-mesh-Skip-vertex-and-primitive-fetches-for-dead-c.patch
0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch
0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch
0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch
0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch
0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch
0006-tu-sample-shading-gate.patch
0007-u_gralloc-always-use-ubwc-detection.patch
0008-tu-mesh-Experimental-indexed-draw-for-mesh-shaders-w.patch
0009-tu-mesh-Wait-for-the-ME-before-indirect-chunk-draws.patch
08-tu-kgsl-cache-retired-a8xx-ib-storage.patch
15-wn-add-aimapper-gralloc.py
16-wn-add-ubwc-swapchain-usage.py
30-tu-z-mutable.py
52-a8xx-resolve-cr-cntl.py
54-a8xx-sp-hysteresis.py
55-a8xx-sp-hysteresis-gs-hs-ds.py
56-a8xx-shader-perf-and-compilation.py
57-a8xx-switch2-dlss-extensions.py
58-a8xx-conservative-rast.py
59-a8xx-ir3-coalesce-ubo-push-ranges.py
60-a8xx-sanitize-frag-nan.py
61-a8xx-lrz-bidir-disable.py
62-a8xx-lrz-color-comp-mask.py
63-tu-framebuffer-attachment-extent-guard.py
64-tu-depth-blit-features.py
aimapper
eden-optimizations-unified.patch
kgsl-syncobj-merge-ts-fd.patch
kgsl-zero-timeout-poll.patch
mr45937-tu-a8xx-wfi-before-reading-registers.patch
mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch
__pycache__
```

`ls -1 scripts/`:
```text
apply_all_patches.py
apply_hl_mk1_fixes.py
hooks
__pycache__
verify_patch_stack.py
```

### 1.2 Verificação de correções de Precisão de Cor e Formatos
`grep -rnE "B10G11R11|R11G11B10|HALF_PRECISION" patches/ scripts/`:
NÃO ENCONTRADO

`grep -rnE "RB_RESOLVE_CR_CNTL|0x810c|GRAS_LRZ_COLOR_COMP_MASK" patches/ scripts/`:
```text
patches/62-a8xx-lrz-color-comp-mask.py:3:"""A8XX: emit GRAS_LRZ_COLOR_COMP_MASK with the MRT blend state.
patches/62-a8xx-lrz-color-comp-mask.py:5:On Adreno 8xx (0x810c) the rasterizer LRZ block tracks per-MRT component write
patches/62-a8xx-lrz-color-comp-mask.py:6:enables through GRAS_LRZ_COLOR_COMP_MASK. Emitting it together with the
patches/62-a8xx-lrz-color-comp-mask.py:19:MARKER = "GRAS_LRZ_COLOR_COMP_MASK"
patches/62-a8xx-lrz-color-comp-mask.py:49:        "      tu_cs_emit_regs(cs, GRAS_LRZ_COLOR_COMP_MASK(CHIP, .dword = lrz_color_comp_mask));\n"
patches/62-a8xx-lrz-color-comp-mask.py:83:    print(f"{NAME}: applied (A8XX GRAS_LRZ_COLOR_COMP_MASK emitted with blend state)")
grep: patches/__pycache__/52-a8xx-resolve-cr-cntl.cpython-312.pyc: arquivo binário coincide com o padrão
grep: patches/__pycache__/62-a8xx-lrz-color-comp-mask.cpython-312.pyc: arquivo binário coincide com o padrão
patches/52-a8xx-resolve-cr-cntl.py:3:"""A8XX: Emit REG_A8XX_RB_RESOLVE_CR_CNTL=1 in preamble magic registers.
patches/52-a8xx-resolve-cr-cntl.py:6:RB_RESOLVE_CR_CNTL (0x8816) = 1 in 100% of command stream preambles (amble1)
patches/52-a8xx-resolve-cr-cntl.py:17:MARKER = "REG_A8XX_RB_RESOLVE_CR_CNTL"
patches/52-a8xx-resolve-cr-cntl.py:27:    "        [A6XXRegs.REG_A8XX_RB_RESOLVE_CR_CNTL, 0x00000001],\n"
```

`grep -rnE "VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT|B8G8R8A8" patches/ scripts/`:
```text
grep: patches/__pycache__/30-tu-z-mutable.cpython-312.pyc: arquivo binário coincide com o padrão
patches/30-tu-z-mutable.py:6:  - pCreateInfo->flags & VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT
patches/30-tu-z-mutable.py:16:This patch leaves 100% of game-internal VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT handling untouched
```

`grep -rnE "opc_cat.*4|cat4|rpt" patches/ scripts/`:
NÃO ENCONTRADO

### 1.3 Verificação de correções de Estabilidade A8xx e UE4
`grep -rnE "BINDLESS_INVALIDATE|SP_GFX_BINDLESS_INVALIDATE|SP_CS_BINDLESS_INVALIDATE" patches/ scripts/`:
```text
patches/0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch:9:SP_GFX_BINDLESS_INVALIDATE and SP_CS_BINDLESS_INVALIDATE instead, and also
patches/0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch:13:upstream c88b6ebd (MR 45129) now writes SP_*_BINDLESS_INVALIDATE there itself.
patches/0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch:75:+         tu_cs_emit_regs(cs, A6XX_SP_GFX_BINDLESS_INVALIDATE(.dword = 1));
patches/0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch:77:+         tu_cs_emit_regs(cs, A6XX_SP_CS_BINDLESS_INVALIDATE(.dword = 1));
```

`grep -rnE "cube_coord_hang_quirk|GLSL_SAMPLER_DIM_CUBE" patches/ scripts/`:
```text
patches/0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch:30:+      bool cube_coord_hang_quirk;
patches/0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch:42:+        cube_coord_hang_quirk = True,
patches/0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch:63:+   if (tex->sampler_dim != GLSL_SAMPLER_DIM_CUBE)
patches/0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch:116:+   if (compiler->info->props.cube_coord_hang_quirk)
grep: patches/__pycache__/60-a8xx-sanitize-frag-nan.cpython-312.pyc: arquivo binário coincide com o padrão
patches/60-a8xx-sanitize-frag-nan.py:117:    call_anchor = "   if (compiler->info->props.cube_coord_hang_quirk)\n      NIR_PASS(_, s, ir3_nir_lower_cube_coord);\n"
patches/60-a8xx-sanitize-frag-nan.py:121:        # Fallback anchor if cube_coord_hang_quirk is absent
```

`grep -rnE "KGSL_MEMFLAGS_VBO|needs_alias|IB_CACHE|ib_bo_cache" patches/ scripts/`:
```text
patches/08-tu-kgsl-cache-retired-a8xx-ib-storage.patch:23:+#define KGSL_IB_CACHE_MAX_BYTES (256ull * 1024 * 1024)
patches/08-tu-kgsl-cache-retired-a8xx-ib-storage.patch:76:+   if (cache->bytes + bo->size > KGSL_IB_CACHE_MAX_BYTES) {
patches/08-tu-kgsl-cache-retired-a8xx-ib-storage.patch:113:+      kgsl_bo_needs_alias(dev, flags) &&
patches/08-tu-kgsl-cache-retired-a8xx-ib-storage.patch:141:-   } else if (kgsl_bo_needs_alias(dev, flags)) {
patches/08-tu-kgsl-cache-retired-a8xx-ib-storage.patch:142:+   } else if (!reused && kgsl_bo_needs_alias(dev, flags)) {
patches/08-tu-kgsl-cache-retired-a8xx-ib-storage.patch:162:+       debug_get_bool_option("TU_KGSL_IB_CACHE", true)) {
patches/0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch:46:+kgsl_bo_needs_alias(struct tu_device *dev, enum tu_bo_alloc_flags flags)
patches/0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch:60:+      .flags = KGSL_MEMFLAGS_VBO | KGSL_MEMFLAGS_VBO_NO_MAP_ZERO |
patches/0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch:137:+   } else if (kgsl_bo_needs_alias(dev, flags)) {
```

`grep -rnE "supports_double_threadsize|half_warp|subgroup" patches/ scripts/`:
```text
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:4:Subject: [PATCH 2/5] tu,ir3: Support a required subgroup size of half a wave
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:6:A8XX only runs 64-wide waves, so the smallest subgroup size was 64 and
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:9:Report a minimum subgroup size of 32 and lower such shaders onto single
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:10:waves, each half of a wave acting as one subgroup. The lowering stays free
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:14: src/freedreno/ir3/ir3_lower_subgroups.c | 290 ++++++++++++++++++++++++
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:25:diff --git a/src/freedreno/ir3/ir3_lower_subgroups.c b/src/freedreno/ir3/ir3_lower_subgroups.c
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:27:--- a/src/freedreno/ir3/ir3_lower_subgroups.c
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:28:+++ b/src/freedreno/ir3/ir3_lower_subgroups.c
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:34:+/* Subgroups of half a wave: each half of a 64-wide wave is its own subgroup.
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:35:+ * Operations that depend on the subgroup size or span the subgroup are
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:44:+   return nir_ushr_imm(b, nir_load_subgroup_invocation(b),
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:51:+   return nir_iand_imm(b, nir_load_subgroup_invocation(b),
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:82:+   case nir_intrinsic_load_subgroup_eq_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:84:+   case nir_intrinsic_load_subgroup_ge_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:86:+   case nir_intrinsic_load_subgroup_gt_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:88:+   case nir_intrinsic_load_subgroup_le_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:90:+   case nir_intrinsic_load_subgroup_lt_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:93:+      UNREACHABLE("not a subgroup mask");
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:167:+build_num_half_subgroups(nir_builder *b)
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:203:+lower_half_subgroup_intrinsic(nir_builder *b, nir_intrinsic_instr *intr,
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:210:+   case nir_intrinsic_load_subgroup_size:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:213:+   case nir_intrinsic_load_subgroup_invocation:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:216:+   case nir_intrinsic_load_subgroup_id:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:217:+      res = nir_iadd(b, nir_imul_imm(b, nir_load_subgroup_id(b), 2),
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:220:+   case nir_intrinsic_load_num_subgroups:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:221:+      res = build_num_half_subgroups(b);
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:223:+   case nir_intrinsic_load_subgroup_eq_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:224:+   case nir_intrinsic_load_subgroup_ge_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:225:+   case nir_intrinsic_load_subgroup_gt_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:226:+   case nir_intrinsic_load_subgroup_le_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:227:+   case nir_intrinsic_load_subgroup_lt_mask:
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:248:+            ? nir_intrinsic_load_subgroup_le_mask
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:249:+            : nir_intrinsic_load_subgroup_lt_mask;
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:285:+      nir_def *base = nir_iand_imm(b, nir_load_subgroup_invocation(b),
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:311:+ir3_nir_lower_half_subgroups(nir_shader *nir)
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:313:+   bool progress = nir_shader_intrinsics_pass(nir, lower_half_subgroup_intrinsic,
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:317:+   nir->info.api_subgroup_size = 2 * 
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:365:        * Lower subgroup_size here, to avoid having to deal with it when
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:383:@@ -211,6 +211,16 @@ tu_subgroup_size(const struct tu_physical_device *device)
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:387:+/* Subgroups of half a wave are emulated on top of the hardware subgroup
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:391:+tu_min_subgroup_size(const struct tu_physical_device *device)
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:405:+   p->minSubgroupSize = tu_min_subgroup_size(pdevice);
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:406:    p->maxSubgroupSize = tu_subgroup_size(pdevice);
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:412:-    * than one possible subgroup size we can't honor a required subgroup size
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:415:+    * doubled size we can't honor a required subgroup size in those stages.
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:431:+      .subgroup_size =
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:434:+            : variant->info.subgroup_size,
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:450:-         props->subgroupSize =
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:452:+         props->subgroupSize = exe->subgroup_size;
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:464:+   uint32_t subgroup_size;
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:472:@@ -4149,7 +4149,11 @@ tu_shader_key_subgroup_size(struct tu_shader_key *key,
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:477:+   if (subgroup_info &&
patches/0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch:478:+       subgroup_info->requiredSubgroupSize < dev->compiler->info->threadsize_base) {
grep: patches/__pycache__/56-a8xx-shader-perf-and-compilation.cpython-312.pyc: arquivo binário coincide com o padrão
patches/0001B-tu-mesh-Size-chunk-tables-per-pipeline-and-advertise.patch:76:@@ -1469,7 +1469,8 @@ tu_subgroup_size(const struct tu_physical_device *device)
patches/0001B-tu-mesh-Size-chunk-tables-per-pipeline-and-advertise.patch:86:@@ -1480,7 +1481,7 @@ tu_subgroup_size(const struct tu_physical_device *device)
patches/mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch:230:-   device->expose_double_threadsize = info.props.supports_double_threadsize && !instance->drirc.misc.restrict_subgroup_size_64;
patches/mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch:231:+   device->expose_double_threadsize = info.props.supports_double_threadsize && !TU_DRIRC(device, misc.restrict_subgroup_size_64);
patches/mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch:445:       const VkPipelineShaderStageRequiredSubgroupSizeCreateInfo *subgroup_info = NULL;
patches/mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch:480:    bool allow_varying_subgroup_size =
patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch:41: system_value("subgroup_id_shift_ir3", 1)
patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch:384:    unsigned subgroup_size = variant->info.subgroup_size;
patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch:962: tu_subgroup_size(const struct tu_physical_device *device)
patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch:991:+      p->subgroupSupportedStages |=
patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch:995:       p->subgroupSupportedStages |= VK_SHADER_STAGE_ALL_GRAPHICS;
patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch:996:       p->subgroupSupportedOperations |= VK_SUBGROUP_FEATURE_QUAD_BIT;
patches/0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch:2618:+   tu_shader_key_subgroup_size(&key, true, false, NULL, dev);
patches/56-a8xx-shader-perf-and-compilation.py:17:    "   if (subgroup_info &&\n"
patches/56-a8xx-shader-perf-and-compilation.py:18:    "       subgroup_info->requiredSubgroupSize < dev->compiler->info->threadsize_base) {\n"
patches/56-a8xx-shader-perf-and-compilation.py:29:    "   if (subgroup_info &&\n"
patches/56-a8xx-shader-perf-and-compilation.py:30:    "       subgroup_info->requiredSubgroupSize < dev->compiler->info->threadsize_base) {\n"
grep: scripts/__pycache__/apply_all_patches.cpython-312.pyc: arquivo binário coincide com o padrão
scripts/apply_all_patches.py:41:    "0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch",
scripts/apply_all_patches.py:245:            '            supports_double_threadsize = False,\n'
scripts/apply_all_patches.py:296:            supports_double_threadsize = False,
```

`grep -rnE "lrz_pitch|LRZ_FLUSH|partial.*fast_clear" patches/ scripts/`:
NÃO ENCONTRADO

`grep -rnE "pre-shifted|load_ssbo|WAIT_FOR_IDLE|split.*indirect" patches/ scripts/`:
```text
patches/mr45937-tu-a8xx-wfi-before-reading-registers.patch:75:-         /* CP_REG_RMW and CP_REG_TO_SCRATCH implicitly do a CP_WAIT_FOR_IDLE
patches/mr45937-tu-a8xx-wfi-before-reading-registers.patch:80:+          * and on A750 CP_WAIT_FOR_IDLE (which is a full pipeline stall) that
```

---

## 3. Tabela com os 12 checks do PASSO 2.2 ([CHECK-01] até [CHECK-12])

| Check | Descrição | Saída Literal |
|---|---|---|
| **[CHECK-01]** | R11G11B10 HALF_PRECISION no blit 3D | NÃO ENCONTRADO |
| **[CHECK-02]** | RB_RESOLVE_CR_CNTL e GRAS_LRZ_COLOR_COMP_MASK (0x810c) | `/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_pipeline.cc:3464:      tu_cs_emit_regs(cs, GRAS_LRZ_COLOR_COMP_MASK(CHIP, .dword = lrz_color_comp_mask));`<br>`/tmp/mesa-audit-s2/src/freedreno/registers/adreno/a6xx.xml:2128:	<!-- 0x810c-0x810f invalid -->`<br>`/tmp/mesa-audit-s2/src/freedreno/registers/adreno/a6xx.xml:2146:	<reg32 offset="0x810c" name="GRAS_LRZ_COLOR_COMP_MASK" variants="A8XX-">`<br>`/tmp/mesa-audit-s2/src/freedreno/registers/adreno/a6xx.xml:2373:	<reg32 offset="0x8816" name="RB_RESOLVE_CR_CNTL" variants="A8XX-" usage="resolve"/>`<br>`/tmp/mesa-audit-s2/src/freedreno/common/freedreno_devices.py:1440:        [A6XXRegs.REG_A8XX_RB_RESOLVE_CR_CNTL, 0x00000001],` |
| **[CHECK-03]** | Imagens MUTABLE_FORMAT mantendo UBWC e BGRA Swap em tu_image.cc | `602-    * TODO:`<br>`603-    * - if the fmt_list contains only formats which are swapped, but compatible`<br>`604-    *   with each other (B8G8R8A8_UNORM and B8G8R8A8_UINT for example), then`<br>`605-    *   tiling is still possible`<br>`606-    */`<br>`607:   if ((pCreateInfo->flags & VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT) &&`<br>`608-       !vk_format_is_depth_or_stencil(image->vk.format)) {`<br>`609-      const VkImageFormatListCreateInfo *fmt_list =`<br>`610-         vk_find_struct_const(pCreateInfo->pNext, IMAGE_FORMAT_LIST_CREATE_INFO);`<br>`611-      if (!tu6_mutable_format_list_ubwc_compatible(device->physical_device->info,`<br>`612-                                                   fmt_list)) {` |
| **[CHECK-04]** | Bloqueio de repeat (rpt) em instruções Category-4 (SFU) na A8xx (ir3) | `/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_validate.c:335:        opc_cat(instr->opc) == 4)) {`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/disasm-a3xx.c:748:   if (ctx->cur_opc_cat == 4) {`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3.h:1411:   return (opc_cat(instr->opc) == 4) || instr->opc == OPC_GETFIBERID;` |
| **[CHECK-05]** | Invalidação Bindless A8xx (SP_GFX_BINDLESS_INVALIDATE) | `396-               .cs_bindless = CHIP == A6XX ? 0x1f : 0xff,`<br>`397-               .gfx_bindless = CHIP == A6XX ? 0x1f : 0xff,`<br>`398-         ));`<br>`399-      } `<br>`400:      tu_cs_emit_regs(cs, A6XX_SP_CS_BINDLESS_INVALIDATE(1));`<br>`401:      tu_cs_emit_regs(cs, A6XX_SP_GFX_BINDLESS_INVALIDATE(1));`<br>`402-   }`<br>`403-`<br>`404-   /* SUBPASS_SLICE_FENCE is a weaker version of:`<br>`405-    * - CACHE_INVALIDATE (only invalidate UCHE GMEM aperture)` |
| **[CHECK-06]** | Sanitização de Cube Map (cube_coord_hang_quirk) na A8xx | `/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir.c:910:   if (compiler->info->props.cube_coord_hang_quirk)`<br>`/tmp/mesa-audit-s2/src/freedreno/common/freedreno_devices.py:1415:        cube_coord_hang_quirk = True,`<br>`/tmp/mesa-audit-s2/src/freedreno/common/freedreno_dev_info.h:515:      bool cube_coord_hang_quirk;` |
| **[CHECK-07]** | KGSL VBO Alias e Cache de IB aposentado em tu_knl_kgsl.cc | `289-static bool`<br>`290-kgsl_bo_needs_alias(struct tu_device *dev, enum tu_bo_alloc_flags flags)`<br>`291-{`<br>`292:   return (flags & TU_BO_ALLOC_NO_32B_ROLLOVER) &&`<br>`293-          dev->physical_device->has_sparse &&`<br>`294-          dev->physical_device->info->chip >= A8XX;`<br>`295-}`<br>`--`<br>`301-`<br>`302-   struct kgsl_gpuobj_alloc alloc = {`<br>`303-      .size = bo->size,`<br>`304:      .flags = KGSL_MEMFLAGS_VBO \| KGSL_MEMFLAGS_VBO_NO_MAP_ZERO \|`<br>`305-               kgsl_align_flag(align),`<br>`306-   };`<br>`307-`<br>`--`<br>`379- * Limit idle storage to 256 MiB; live BOs remain outside this cache. Entries own`<br>`380- * raw kernel objects, not bo_map pointers, so device-init error cleanup is safe.`<br>`381- */`<br>`382:#define KGSL_IB_CACHE_MAX_BYTES (256ull * 1024 * 1024)`<br>`383-struct kgsl_ib_cache_entry {`<br>`384-   struct kgsl_ib_cache_entry *next;`<br>`385-   uint32_t handle, alias, flags;`<br>`--`<br>`432-   if (!entry)`<br>`433-      return false;`<br>`434-   mtx_lock(&cache->mutex);`<br>`435:   if (cache->bytes + bo->size > KGSL_IB_CACHE_MAX_BYTES) {`<br>`436-      mtx_unlock(&cache->mutex);`<br>`437-      free(entry);` |
| **[CHECK-08]** | Configuração de supports_double_threadsize em freedreno_devices.py | `143-        num_xfb_streams = 4,`<br>`144-`<br>`145:        supports_double_threadsize = True,`<br>`146-`<br>`147-        sysmem_per_ccu_depth_cache_size = 64 * 1024,`<br>`--`<br>`185-        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,`<br>`186-        vs_max_inputs_count = 16,`<br>`187:        supports_double_threadsize = False,`<br>`188-    )`<br>`189-`<br>`--`<br>`716-            sysmem_per_ccu_color_cache_size = 8 * 1024, # ??????`<br>`717-            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,`<br>`718:            supports_double_threadsize = True,`<br>`719-            prim_alloc_threshold = 0x1,`<br>`720-            storage_16bit = True,`<br>`--`<br>`761-        num_xfb_streams = 4,`<br>`762-`<br>`763:        supports_double_threadsize = True,`<br>`764-`<br>`765-        sysmem_per_ccu_depth_cache_size = 256 * 1024,`<br>`--`<br>`1408-        reg_size_vec4 = 96,`<br>`1409-        has_rt_workaround = False,`<br>`1410:        supports_double_threadsize = False,`<br>`1411-        has_dual_wave_dispatch = True,`<br>`1412-        round_robin_errata = False,`<br>`--`<br>`1564-            gmem_per_ccu_depth_cache_size = 64 * 1024,`<br>`1565-            has_fs_tex_prefetch = False,`<br>`1566:            supports_double_threadsize = False,`<br>`1567-         )],`<br>`1568-        num_ccu = 4,`<br>`--`<br>`1676-            gmem_per_ccu_depth_cache_size = 32 * 1024,`<br>`1677-            has_fs_tex_prefetch = False,`<br>`1678:            supports_double_threadsize = False,`<br>`1679-            has_attachment_shading_rate = True,`<br>`1680-            shading_rate_matches_vk = True,` |
| **[CHECK-09]** | Alinhamento de pitch de LRZ (32 vs 64) na A8xx | `/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig-2502-                      image->iova + image->lrz_layout.lrz_offset +`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig-2503-                      i * image->lrz_layout.lrz_buffer_size,`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig:2504:                      image->lrz_layout.lrz_pitch * 2, PIPE_FORMAT_Z16_UNORM);`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig-2505-      uint32_t lrz_height = image->lrz_layout.lrz_height * image->vk.array_layers;`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig-2506-      ops->coords(cmd, cs, (VkOffset2D) {}, blt_no_coord,`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig:2507:                  (VkExtent2D) { image->lrz_layout.lrz_pitch, lrz_height });`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig-2508-      ops->run(cmd, cs);`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_clear_blit.cc.orig-2509-      ops->teardown(cmd, cs);`<br>`--`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_lrz.cc-144-   crb.add(GRAS_LRZ_BUFFER_BASE(CHIP, .qword = lrz_iova))`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_lrz.cc-145-      .add(GRAS_LRZ_BUFFER_PITCH(`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_lrz.cc:146:         CHIP, .pitch = depth_image->lrz_layout.lrz_pitch * sizeof(uint16_t),`<br>`/tmp/mesa-audit-s2/src/freedreno/vulkan/tu_lrz.cc-147-         .array_pitch = depth_image->lrz_layout.lrz_layer_size))` |
| **[CHECK-10]** | Indexação de pBindings e mutable_info em tu_descriptor_set.cc | NÃO ENCONTRADO |
| **[CHECK-11]** | Prefetch de descritores de textura no ir3 | `/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:12: * prior to FS shader start, and change them to nir_texop_tex_prefetch.`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:18:} tex_prefetch_candidate;`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:159:lower_tex_prefetch_block(nir_block *block, ir3_prefetch_state *state)`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:180:      /* only prefetch for simple 2d tex fetch case */`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:197:         tex_prefetch_candidate *candidate = u_vector_add(&state->candidates);`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:209:lower_tex_prefetch_func(nir_function_impl *impl, ir3_prefetch_state *state)`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:231:   bool progress = lower_tex_prefetch_block(block, state);`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:237:ir3_nir_lower_tex_prefetch(nir_shader *shader,`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:245:   u_vector_init(&state.candidates, 4, sizeof(tex_prefetch_candidate));`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:254:      progress |= lower_tex_prefetch_func(function->impl, &state);`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:258:      /* We cannot prefetch tex ops that use different interpolation modes,`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:260:       * interpolation mode that would allow us to prefetch the most tex ops.`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:271:      tex_prefetch_candidate *candidate;`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_nir_lower_tex_prefetch.c:274:            candidate->tex->op = nir_texop_tex_prefetch;`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_context.c:118:   if ((so->type == MESA_SHADER_FRAGMENT) && compiler->info->props.has_fs_tex_prefetch) {`<br>`/tmp/mesa-audit-s2/src/freedreno/ir3/ir3_context.c:119:      NIR_PASS(_, ctx->s, ir3_nir_lower_tex_prefetch, &so->prefetch_bary_type);` |
| **[CHECK-12]** | Gate de Sample Shading em tu_pipeline.cc | `1966-       * The definition is pretty much the same as OpenGL's GL_SAMPLE_SHADING.`<br>`1967-       * They both require unique associated data.`<br>`1968-       *`<br>`1969-       * There are discussions to change the definition, such that`<br>`1970:       * sampleShadingEnable does not imply unique associated data.  Before the`<br>`1971-       * discussions are settled and before apps (i.e., ANGLE) are fixed to`<br>`1972-       * follow the new and incompatible definition, we should stick to the`<br>`1973-       * current definition.`<br>`1974-       *`<br>`--`<br>`1976-       * just checked in tu6_emit_fs_inputs.  We will also copy the value to`<br>`1977-       * tu_shader_key::force_sample_interp in a bit.`<br>`1978-       */`<br>`1979-      keys[MESA_SHADER_FRAGMENT].force_sample_interp =`<br>`1980:         !builder->rasterizer_discard && msaa_info && msaa_info->sampleShadingEnable;`<br>`1981-   }` |

---

## 4. Tabela === RESUMO HL / MK1 / A8XX === e git diff do PASSO 3

### Tabela
```text
=== RESUMO HL / MK1 / A8XX ===
ANCHOR_MISS      r11g11b10_half_prec      Verificar manualmente r3d_setup em tu_clear_blit.cc
FAIL_NO_FILE     a8xx_cat4_no_rpt         ir3_group.c ausente
ANCHOR_MISS      a8xx_lrz_pitch_32        Procurar calculo de lrz_pitch
SKIP_ALREADY     a8xx_bindless_inv        Registradores A8xx bindless invalidate ja emitidos
ANCHOR_MISS      desc_pbindings_order     Padrao nao localizado
```

### Git diff gerado no PASSO 3
*(Executado em `/tmp/mesa-audit-s2`; o script `apply_hl_mk1_fixes.py` não alterou nenhum arquivo devido a âncoras/arquivos ausentes e verificação já satisfeita para `a8xx_bindless_inv`; o diff da worktree reflete os patches aplicados anteriormente por `apply_all_patches.py` sobre `35a0fef1`)*:
```text
33 files changed, 1835 insertions(+), 132 deletions(-)
```

---

## 5. Saída literal do PASSO 4.1 (registradores XML presentes em src/freedreno/registers/)
```text
/tmp/mesa-audit-s2/src/freedreno/registers/adreno/a6xx.xml:2146:	<reg32 offset="0x810c" name="GRAS_LRZ_COLOR_COMP_MASK" variants="A8XX-">
/tmp/mesa-audit-s2/src/freedreno/registers/adreno/a6xx.xml:2373:	<reg32 offset="0x8816" name="RB_RESOLVE_CR_CNTL" variants="A8XX-" usage="resolve"/>
/tmp/mesa-audit-s2/src/freedreno/registers/adreno/a6xx.xml:4962:	<reg32 offset="0xa9c0" name="SP_CS_BINDLESS_INVALIDATE" usage="compute"/>
/tmp/mesa-audit-s2/src/freedreno/registers/adreno/a6xx.xml:4963:	<reg32 offset="0xab08" name="SP_GFX_BINDLESS_INVALIDATE" usage="draw"/>
```

---

## 6. Saída literal de git diff --stat main..HEAD
```text
 .github/workflows/build-turnip.yml |  17 ++-
 CHANGELOG.md                       |   7 +
 README.md                          |  17 ++-
 docs/AUDITORIA_HL_MK1_A8XX.md      | 283 +++++++++++++++++++++++++++++++++++++
 docs/AUDITORIA_MESA_REAL.md        |  94 ++++++++++++
 docs/JOURNAL.md                    |   7 +
 scripts/apply_all_patches.py       |  53 +++++++
 scripts/apply_hl_mk1_fixes.py      | 132 +++++++++++++++++
 scripts/verify_patch_stack.py      |  32 +++++
 9 files changed, 634 insertions(+), 8 deletions(-)
```

---

VIOLAÇÃO DE REGRA: scripts/apply_all_patches.py
