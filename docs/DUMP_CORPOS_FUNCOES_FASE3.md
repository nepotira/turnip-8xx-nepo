# Dump Corpos de Funcoes - Fase 3

## PASSO 1 - Scripts restantes em patches/ (30, 58, 60, 63, 64)

```text

==================== ARQUIVO: patches/30-tu-z-mutable.py ====================
   1: #!/usr/bin/env python3
   2: """Protect DRM_FORMAT_MOD_QCOM_COMPRESSED swapchain images from TILE6_LINEAR in tu_image_init.
   3: 
   4: On Android 16 with 15-wn-add-aimapper-gralloc.py and 16-wn-add-ubwc-swapchain-usage.py,
   5: swapchain AHardwareBuffers arrive in tu_image_init() with:
   6:   - pCreateInfo->flags & VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT
   7:   - fmt_list == NULL
   8:   - modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED
   9: 
  10: In upstream Mesa, when !mutable_ubwc_fc (A710/A720/A722), fmt_list_has_swaps is true
  11: when fmt_list is NULL, setting force_linear_tile = true -> tile_mode = TILE6_LINEAR.
  12: Then at `if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED)`, assert(!force_linear_tile)
  13: is compiled out in release builds (-DNDEBUG) and ubwc_enabled = true is set while
  14: tile_mode remains TILE6_LINEAR, corrupting the swapchain with purple vertical lines.
  15: 
  16: This patch leaves 100% of game-internal VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT handling untouched
  17: (pure upstream Mesa behavior, identical to T30 / build-0 where the Mario Kart 8 Deluxe item
  18: roulette icon renders properly), and ONLY ensures that when modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED,
  19: force_linear_tile is cleared and tile_mode = TILE6_3 is restored.
  20: """
  21: import sys
  22: 
  23: NAME = "30-tu-z-mutable.py"
  24: IMAGE = "src/freedreno/vulkan/tu_image.cc"
  25: 
  26: OLD = (
  27:     '   if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) {\n'
  28:     '      assert(!force_linear_tile);\n'
  29:     '      ubwc_enabled = true;\n'
  30:     '      force_ubwc = true;\n'
  31:     '   }\n'
  32: )
  33: 
  34: NEW = (
  35:     '   if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) {\n'
  36:     '      force_linear_tile = false;\n'
  37:     '      tile_mode = TILE6_3;\n'
  38:     '      ubwc_enabled = true;\n'
  39:     '      force_ubwc = true;\n'
  40:     '   }\n'
  41: )
  42: 
  43: 
  44: def main():
  45:     try:
  46:         s = open(IMAGE, encoding="utf-8").read()
  47:     except OSError as e:
  48:         print(f"{NAME}: WARNING cannot read {IMAGE}: {e}; skipped")
  49:         return 0
  50: 
  51:     if NEW in s:
  52:         print(f"{NAME}: already applied")
  53:         return 0
  54: 
  55:     if s.count(OLD) != 1:
  56:         print(f"{NAME}: WARNING anchor matched {s.count(OLD)}x in {IMAGE}; skipped")
  57:         return 0
  58: 
  59:     s = s.replace(OLD, NEW, 1)
  60:     with open(IMAGE, "w", encoding="utf-8", newline="\n") as f:
  61:         f.write(s)
  62: 
  63:     print(f"{NAME}: applied (pure upstream mutable handling + QCOM_COMPRESSED TILE6_3 guard)")
  64:     return 0
  65: 
  66: 
  67: if __name__ == "__main__":
  68:     sys.exit(main())

==================== ARQUIVO: patches/58-a8xx-conservative-rast.py ====================
   1: #!/usr/bin/env python3
   2: """A8XX: Safety guard ensuring conservative rasterization binning remains disabled on A8XX.
   3: 
   4: Conservative rasterization binning (tu_binning_conservative_rast) on Adreno 8xx
   5: clips the tile bounding box to the internal 720p resolution, leaving 65% of the
   6: screen black on 2400x1080 displays in Switch emulators (e.g. Nyushu). This script
   7: ensures upstream 'CHIP == A7XX' is strictly preserved.
   8: 
   9: Run from Mesa source root. Idempotent and safe to run multiple times.
  10: """
  11: import sys
  12: 
  13: NAME = "58-a8xx-conservative-rast.py"
  14: TARGET = "src/freedreno/vulkan/tu_pipeline.cc"
  15: BAD = "   return CHIP >= A7XX && fdm && !TU_DRIRC(dev, misc.disable_conservative_fdm_binning);\n"
  16: GOOD = "   return CHIP == A7XX && fdm && !TU_DRIRC(dev, misc.disable_conservative_fdm_binning);\n"
  17: 
  18: 
  19: def main():
  20:     try:
  21:         content = open(TARGET, "r", encoding="utf-8").read()
  22:     except OSError as e:
  23:         print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
  24:         return 0
  25: 
  26:     if BAD in content:
  27:         content = content.replace(BAD, GOOD, 1)
  28:         try:
  29:             with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
  30:                 f.write(content)
  31:             print(f"{NAME}: reverted (conservative binning disabled on A8XX to fix 65% black cutoff)")
  32:             return 0
  33:         except OSError as e:
  34:             print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
  35:             return 1
  36: 
  37:     print(f"{NAME}: safe (conservative binning disabled on A8XX)")
  38:     return 0
  39: 
  40: 
  41: if __name__ == "__main__":
  42:     sys.exit(main())

==================== ARQUIVO: patches/60-a8xx-sanitize-frag-nan.py ====================
   1: #!/usr/bin/env python3
   2: """A8XX: Sanitize fragment and compute shader outputs against NaNs, Infs and bloom blowouts.
   3: 
   4: When textures with uninitialized memory or out-of-bounds sampling are decoded
   5: in Switch emulators (e.g. Nyushu/Eden/Citron without custom SIMD texture unswizzling),
   6: sampling produces NaNs and Infs. In HDR fog, bloom downsamples, and tone-mapping passes
   7: (e.g. Super Mario Odyssey), these NaNs propagate and saturate to pure white on Adreno 8xx,
   8: creating whitish artifacts ("elementos esbranquiçados").
   9: 
  10: This patch inserts an IR3/NIR output sanitization pass in ir3_finalize_nir:
  11: - Handles fragment shader color attachment outputs (nir_intrinsic_store_output)
  12: - Handles compute shader and fragment shader image stores (image_store, bindless_image_store, image_deref_store)
  13: - Replaces NaNs with 0.0 using nir_bcsel(nir_fisnan(src), 0.0, src)
  14: - Clamps infinite values to finite fp16/fp32 bounds using nir_fclamp
  15: - Leaves integer/uint render targets completely untouched
  16: 
  17: Run from Mesa source root. Idempotent and safe to run multiple times.
  18: """
  19: import sys
  20: 
  21: NAME = "60-a8xx-sanitize-frag-nan.py"
  22: TARGET = "src/freedreno/ir3/ir3_nir.c"
  23: MARKER = "ir3_nir_sanitize_outputs"
  24: 
  25: FUNC_CODE = """
  26: /* Sanitize fragment and compute shader outputs: replace NaN with 0.0 and clamp to finite range
  27:  * to prevent bloom blowouts and whitish artifacts caused by out-of-bounds or
  28:  * uninitialized texture samples (especially in emulators like Switch/Nyushu/Eden).
  29:  */
  30: static bool
  31: ir3_nir_sanitize_outputs_cb(struct nir_builder *b, nir_intrinsic_instr *intr,
  32:                             void *_data)
  33: {
  34:    nir_def *src = NULL;
  35:    unsigned src_idx = 0;
  36: 
  37:    if (intr->intrinsic == nir_intrinsic_store_output) {
  38:       nir_io_semantics sem = nir_intrinsic_io_semantics(intr);
  39:       if (sem.location < FRAG_RESULT_DATA0 && sem.location != FRAG_RESULT_COLOR)
  40:          return false;
  41:       src = intr->src[0].ssa;
  42:       src_idx = 0;
  43:    } else if (intr->intrinsic == nir_intrinsic_image_store ||
  44:               intr->intrinsic == nir_intrinsic_bindless_image_store ||
  45:               intr->intrinsic == nir_intrinsic_image_deref_store) {
  46:       src = intr->src[3].ssa;
  47:       src_idx = 3;
  48:    } else {
  49:       return false;
  50:    }
  51: 
  52:    if (!src)
  53:       return false;
  54: 
  55:    unsigned bit_size = src->bit_size;
  56:    if (bit_size != 16 && bit_size != 32)
  57:       return false;
  58: 
  59:    if (intr->intrinsic == nir_intrinsic_store_output && nir_intrinsic_has_src_type(intr)) {
  60:       nir_alu_type type = nir_intrinsic_src_type(intr);
  61:       if (nir_alu_type_get_base_type(type) != nir_type_float &&
  62:           nir_alu_type_get_base_type(type) != nir_type_invalid)
  63:          return false;
  64:    }
  65: 
  66:    b->cursor = nir_before_instr(&intr->instr);
  67: 
  68:    nir_def *zero = nir_imm_zero(b, src->num_components, bit_size);
  69:    nir_def *max_val = nir_imm_floatN_t(b, bit_size == 16 ? 65504.0 : FLT_MAX, bit_size);
  70: 
  71:    nir_def *is_nan = nir_fisnan(b, src);
  72:    nir_def *clean = nir_bcsel(b, is_nan, zero, src);
  73:    clean = nir_fclamp(b, clean, nir_fneg(b, max_val), max_val);
  74: 
  75:    nir_src_rewrite(&intr->src[src_idx], clean);
  76:    return true;
  77: }
  78: 
  79: static bool
  80: ir3_nir_sanitize_outputs(nir_shader *shader)
  81: {
  82:    if (shader->info.stage != MESA_SHADER_FRAGMENT &&
  83:        shader->info.stage != MESA_SHADER_COMPUTE)
  84:       return false;
  85: 
  86:    return nir_shader_intrinsics_pass(shader, ir3_nir_sanitize_outputs_cb,
  87:                                      nir_metadata_control_flow, NULL);
  88: }
  89: """
  90: 
  91: CALL_CODE = """
  92:    if (s->info.stage == MESA_SHADER_FRAGMENT || s->info.stage == MESA_SHADER_COMPUTE)
  93:       NIR_PASS(_, s, ir3_nir_sanitize_outputs);
  94: """
  95: 
  96: 
  97: def main():
  98:     try:
  99:         content = open(TARGET, "r", encoding="utf-8").read()
 100:     except OSError as e:
 101:         print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
 102:         return 0
 103: 
 104:     if MARKER in content:
 105:         print(f"{NAME}: already applied ({MARKER} present)")
 106:         return 0
 107: 
 108:     # 1. Insert helper function before ir3_finalize_nir
 109:     fn_anchor = "void\nir3_finalize_nir("
 110:     if fn_anchor not in content:
 111:         print(f"{NAME}: WARNING anchor '{fn_anchor}' not found in {TARGET}; skipped")
 112:         return 0
 113: 
 114:     content = content.replace(fn_anchor, FUNC_CODE.strip() + "\n\n" + fn_anchor, 1)
 115: 
 116:     # 2. Insert call inside ir3_finalize_nir
 117:     call_anchor = "   if (compiler->info->props.cube_coord_hang_quirk)\n      NIR_PASS(_, s, ir3_nir_lower_cube_coord);\n"
 118:     if call_anchor in content:
 119:         content = content.replace(call_anchor, call_anchor + CALL_CODE, 1)
 120:     else:
 121:         # Fallback anchor if cube_coord_hang_quirk is absent
 122:         fallback_anchor = "   NIR_PASS(_, s, ir3_nir_min_lod_workaround);\n"
 123:         if fallback_anchor in content:
 124:             content = content.replace(fallback_anchor, fallback_anchor + CALL_CODE, 1)
 125:         else:
 126:             print(f"{NAME}: WARNING call anchor not found in ir3_finalize_nir; skipped")
 127:             return 0
 128: 
 129:     try:
 130:         with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
 131:             f.write(content)
 132:     except OSError as e:
 133:         print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
 134:         return 1
 135: 
 136:     print(f"{NAME}: applied (fragment and compute output NaN/Inf sanitization enabled in ir3_nir.c)")
 137:     return 0
 138: 
 139: 
 140: if __name__ == "__main__":
 141:     sys.exit(main())

==================== ARQUIVO: patches/63-tu-framebuffer-attachment-extent-guard.py ====================
   1: #!/usr/bin/env python3
   2: # SPDX-License-Identifier: MIT
   3: """A8XX: Framebuffer attachment extent guard and render area window scissor safety.
   4: 
   5: Prevents the 64.5% (~65%) black viewport cutoff in emulators (e.g. Nyushu/Yuzu/Citron)
   6: when presenting scaled frames (e.g. 2160p / 4K) to mobile displays (e.g. 2400x1080):
   7: 1. In tu_CreateFramebuffer: expands framebuffer dimensions to match attachment image
   8:    extents if larger than pCreateInfo (fixing emulators creating framebuffers with 720p base
   9:    dimensions for 2400x1080 swapchain views).
  10: 2. In tu6_sysmem_render_begin: ensures the emitted hardware GRAS_SC_WINDOW_SCISSOR covers
  11:    the full render area extent (preventing clipping of the presentation blit quad).
  12: 
  13: Run from Mesa source root. Idempotent and safe to run multiple times.
  14: """
  15: import sys
  16: 
  17: NAME = "63-tu-framebuffer-attachment-extent-guard.py"
  18: DEV_TARGET = "src/freedreno/vulkan/tu_device.cc"
  19: CMD_TARGET = "src/freedreno/vulkan/tu_cmd_buffer.cc"
  20: 
  21: DEV_MARKER = "/* Framebuffer attachment extent guard */"
  22: CMD_MARKER = "/* Window scissor render area guard */"
  23: 
  24: DEV_OLD = """   if (!imageless) {
  25:       for (uint32_t i = 0; i < pCreateInfo->attachmentCount; i++) {
  26:          VkImageView _iview = pCreateInfo->pAttachments[i];
  27:          struct tu_image_view *iview = tu_image_view_from_handle(_iview);
  28:          framebuffer->attachments[i] = iview;
  29:       }
  30:    }"""
  31: 
  32: DEV_NEW = """   if (!imageless) {
  33:       for (uint32_t i = 0; i < pCreateInfo->attachmentCount; i++) {
  34:          VkImageView _iview = pCreateInfo->pAttachments[i];
  35:          struct tu_image_view *iview = tu_image_view_from_handle(_iview);
  36:          framebuffer->attachments[i] = iview;
  37:          /* Framebuffer attachment extent guard:
  38:           * In emulators (e.g. Nyushu/Yuzu/Citron), the presentation blit pass creates
  39:           * a VkFramebuffer passing the base unscaled render dimensions (1280x720) while
  40:           * attaching a full-screen swapchain image view (e.g. 2400x1080).
  41:           * Expanding framebuffer dimensions to the attachment extent prevents hardware
  42:           * GRAS_SC_WINDOW_SCISSOR from clipping the presentation draw call to 1280x720,
  43:           * which otherwise leaves 64.5% (~65%) of a 2400x1080 display pitch black.
  44:           */
  45:          if (iview && iview->image) {
  46:             framebuffer->width = MAX2(framebuffer->width, iview->image->vk.extent.width);
  47:             framebuffer->height = MAX2(framebuffer->height, iview->image->vk.extent.height);
  48:          }
  49:       }
  50:    }"""
  51: 
  52: CMD_OLD = """   assert(fb->width > 0 && fb->height > 0);
  53:    tu6_emit_window_scissor<CHIP>(cs, 0, 0, fb->width - 1, fb->height - 1);
  54:    tu6_emit_window_offset<CHIP>(cs, 0, 0);"""
  55: 
  56: CMD_NEW = """   assert(fb->width > 0 && fb->height > 0);
  57:    /* Window scissor render area guard:
  58:     * In direct/sysmem rendering passes, ensure the emitted window scissor is never
  59:     * smaller than the active render area, preventing presentation blits from clipping.
  60:     */
  61:    uint32_t scissor_w = fb->width;
  62:    uint32_t scissor_h = fb->height;
  63:    if (cmd->state.render_areas[0].offset.x + cmd->state.render_areas[0].extent.width > scissor_w)
  64:       scissor_w = cmd->state.render_areas[0].offset.x + cmd->state.render_areas[0].extent.width;
  65:    if (cmd->state.render_areas[0].offset.y + cmd->state.render_areas[0].extent.height > scissor_h)
  66:       scissor_h = cmd->state.render_areas[0].offset.y + cmd->state.render_areas[0].extent.height;
  67: 
  68:    tu6_emit_window_scissor<CHIP>(cs, 0, 0, scissor_w - 1, scissor_h - 1);
  69:    tu6_emit_window_offset<CHIP>(cs, 0, 0);"""
  70: 
  71: 
  72: def main():
  73:     # 1. Patch tu_device.cc
  74:     try:
  75:         dev_content = open(DEV_TARGET, "r", encoding="utf-8").read()
  76:     except OSError as e:
  77:         print(f"{NAME}: WARNING cannot read {DEV_TARGET}: {e}; skipped")
  78:         return 0
  79: 
  80:     if DEV_MARKER not in dev_content:
  81:         if DEV_OLD in dev_content:
  82:             dev_content = dev_content.replace(DEV_OLD, DEV_NEW, 1)
  83:             try:
  84:                 with open(DEV_TARGET, "w", encoding="utf-8", newline="\n") as f:
  85:                     f.write(dev_content)
  86:                 print(f"{NAME}: applied attachment extent guard in {DEV_TARGET}")
  87:             except OSError as e:
  88:                 print(f"{NAME}: ERROR cannot write {DEV_TARGET}: {e}", file=sys.stderr)
  89:                 return 1
  90:         else:
  91:             print(f"{NAME}: WARNING anchor not found in {DEV_TARGET}; skipped")
  92: 
  93:     # 2. Patch tu_cmd_buffer.cc
  94:     try:
  95:         cmd_content = open(CMD_TARGET, "r", encoding="utf-8").read()
  96:     except OSError as e:
  97:         print(f"{NAME}: WARNING cannot read {CMD_TARGET}: {e}; skipped")
  98:         return 0
  99: 
 100:     if CMD_MARKER not in cmd_content:
 101:         if CMD_OLD in cmd_content:
 102:             cmd_content = cmd_content.replace(CMD_OLD, CMD_NEW, 1)
 103:             try:
 104:                 with open(CMD_TARGET, "w", encoding="utf-8", newline="\n") as f:
 105:                     f.write(cmd_content)
 106:                 print(f"{NAME}: applied window scissor guard in {CMD_TARGET}")
 107:             except OSError as e:
 108:                 print(f"{NAME}: ERROR cannot write {CMD_TARGET}: {e}", file=sys.stderr)
 109:                 return 1
 110:         else:
 111:             print(f"{NAME}: WARNING anchor not found in {CMD_TARGET}; skipped")
 112: 
 113:     print(f"{NAME}: safe/applied (framebuffer extent & window scissor guard active)")
 114:     return 0
 115: 
 116: 
 117: if __name__ == "__main__":
 118:     sys.exit(main())

==================== ARQUIVO: patches/64-tu-depth-blit-features.py ====================
   1: #!/usr/bin/env python3
   2: # SPDX-License-Identifier: MIT
   3: """A8XX: Advertise BLIT_SRC and BLIT_DST features for depth/stencil formats in Turnip.
   4: 
   5: Resolves the 64,910 BlitScaleHelper errors and depth buffer upscale failures in Switch
   6: emulators (e.g. Nyushu, Eden, Citron, Yuzu, Sudachi, Suyu) when running at 2160p (4K / 3X scale):
   7: - Turnip already implements shader and hardware depth blitting in tu_clear_blit.cc,
   8:   but previously only advertised VK_FORMAT_FEATURE_2_DEPTH_STENCIL_ATTACHMENT_BIT in tu_formats.cc.
   9: - By adding VK_FORMAT_FEATURE_2_BLIT_SRC_BIT and VK_FORMAT_FEATURE_2_BLIT_DST_BIT to optimal
  10:   features for depth formats, emulators can scale depth attachments to 2160p alongside color
  11:   targets, eliminating the ~65% unrendered black screen and specular white-out glitches.
  12: 
  13: Run from Mesa source root. Idempotent and safe to run multiple times.
  14: """
  15: import sys
  16: from pathlib import Path
  17: 
  18: NAME = "64-tu-depth-blit-features.py"
  19: TARGET = "src/freedreno/vulkan/tu_formats.cc"
  20: MARKER = "/* Depth/stencil attachment and scaling blit features */"
  21: 
  22: OLD = (
  23:     "   linear = optimal;\n"
  24:     "   if (tu6_pipe2depth(vk_format) != DEPTH6_NONE)\n"
  25:     "      optimal |= VK_FORMAT_FEATURE_2_DEPTH_STENCIL_ATTACHMENT_BIT;\n"
  26: )
  27: 
  28: NEW = (
  29:     "   linear = optimal;\n"
  30:     "   if (tu6_pipe2depth(vk_format) != DEPTH6_NONE) {\n"
  31:     "      /* Depth/stencil attachment and scaling blit features */\n"
  32:     "      optimal |= VK_FORMAT_FEATURE_2_DEPTH_STENCIL_ATTACHMENT_BIT |\n"
  33:     "                 VK_FORMAT_FEATURE_2_BLIT_SRC_BIT |\n"
  34:     "                 VK_FORMAT_FEATURE_2_BLIT_DST_BIT;\n"
  35:     "   }\n"
  36: )
  37: 
  38: 
  39: def main():
  40:     path = Path(TARGET)
  41:     if not path.is_file():
  42:         print(f"{NAME}: WARNING: {TARGET} not found; skipped")
  43:         return 0
  44: 
  45:     content = path.read_text(encoding="utf-8")
  46:     if MARKER in content:
  47:         print(f"{NAME}: already applied in {TARGET}")
  48:         return 0
  49: 
  50:     if OLD not in content:
  51:         print(f"{NAME}: ERROR: expected target snippet not found in {TARGET}", file=sys.stderr)
  52:         return 1
  53: 
  54:     updated = content.replace(OLD, NEW, 1)
  55:     path.write_text(updated, encoding="utf-8")
  56:     print(f"{NAME}: successfully applied depth blit features to {TARGET}")
  57:     return 0
  58: 
  59: 
  60: if __name__ == "__main__":
  61:     sys.exit(main())
```

## PASSO 2 - Corpos reais de ir3_sched.c, tu_lrz.cc, tu_cmd_buffer.cc, tu_autotune.cc e WFI sites

```text

==================== IR3_SCHED_CHOOSE_INSTR_BODY (src/freedreno/ir3/ir3_sched.c:715-865) ====================
  715: 
  716: /**
  717:  * Chooses an instruction to schedule using the Goodman/Hsu (1988) CSR (Code
  718:  * Scheduling for Register pressure) heuristic.
  719:  *
  720:  * Only handles the case of choosing instructions that reduce register pressure
  721:  * or are even.
  722:  */
  723: static struct ir3_sched_node *
  724: choose_instr_dec(struct ir3_sched_ctx *ctx, struct ir3_sched_notes *notes,
  725:                  bool defer)
  726: {
  727:    const char *mode = defer ? "-d" : "";
  728:    struct ir3_sched_node *chosen = NULL;
  729:    enum choose_instr_dec_rank chosen_rank = DEC_NEUTRAL;
  730: 
  731:    foreach_sched_node (n, &ctx->dag->heads) {
  732:       if (defer && should_defer(ctx, n->instr))
  733:          continue;
  734: 
  735:       unsigned d = node_delay(ctx, n);
  736: 
  737:       int live = live_effect(n->instr);
  738:       if (live > 0)
  739:          continue;
  740: 
  741:       if (!check_instr(ctx, notes, n->instr))
  742:          continue;
  743: 
  744:       enum choose_instr_dec_rank rank;
  745:       if (live < 0) {
  746:          /* Prioritize instrs which free up regs and can be scheduled with no
  747:           * delay.
  748:           */
  749:          if (d == 0)
  750:             rank = DEC_FREED_READY;
  751:          else
  752:             rank = DEC_FREED;
  753:       } else {
  754:          /* Contra the paper, pick a leader with no effect on used regs.  This
  755:           * may open up new opportunities, as otherwise a single-operand instr
  756:           * consuming a value will tend to block finding freeing that value.
  757:           * This had a massive effect on reducing spilling on V3D.
  758:           *
  759:           * XXX: Should this prioritize ready?
  760:           */
  761:          if (d == 0)
  762:             rank = DEC_NEUTRAL_READY;
  763:          else
  764:             rank = DEC_NEUTRAL;
  765:       }
  766: 
  767:       /* Prefer higher-ranked instructions, or in the case of a rank tie, the
  768:        * highest latency-to-end-of-program instruction.
  769:        */
  770:       if (!chosen || rank > chosen_rank ||
  771:           (rank == chosen_rank && chosen->max_delay < n->max_delay)) {
  772:          chosen = n;
  773:          chosen_rank = rank;
  774:       }
  775:    }
  776: 
  777:    if (chosen) {
  778:       di(chosen->instr, "dec%s: chose (%s)", mode, dec_rank_name(chosen_rank));
  779:       return chosen;
  780:    }
  781: 
  782:    return choose_instr_inc(ctx, notes, defer, true);
  783: }
  784: 
  785: enum choose_instr_inc_rank {
  786:    INC_DISTANCE,
  787:    INC_DISTANCE_READY,
  788: };
  789: 
  790: static const char *
  791: inc_rank_name(enum choose_instr_inc_rank rank)
  792: {
  793:    switch (rank) {
  794:    case INC_DISTANCE:
  795:       return "distance";
  796:    case INC_DISTANCE_READY:
  797:       return "distance+ready";
  798:    default:
  799:       return NULL;
  800:    }
  801: }
  802: 
  803: /**
  804:  * When we can't choose an instruction that reduces register pressure or
  805:  * is neutral, we end up here to try and pick the least bad option.
  806:  */
  807: static struct ir3_sched_node *
  808: choose_instr_inc(struct ir3_sched_ctx *ctx, struct ir3_sched_notes *notes,
  809:                  bool defer, bool avoid_output)
  810: {
  811:    const char *mode = defer ? "-d" : "";
  812:    struct ir3_sched_node *chosen = NULL;
  813:    enum choose_instr_inc_rank chosen_rank = INC_DISTANCE;
  814: 
  815:    /*
  816:     * From hear on out, we are picking something that increases
  817:     * register pressure.  So try to pick something which will
  818:     * be consumed soon:
  819:     */
  820:    unsigned chosen_distance = 0;
  821: 
  822:    /* Pick the max delay of the remaining ready set. */
  823:    foreach_sched_node (n, &ctx->dag->heads) {
  824:       if (avoid_output && n->output)
  825:          continue;
  826: 
  827:       if (defer && should_defer(ctx, n->instr))
  828:          continue;
  829: 
  830:       if (!check_instr(ctx, notes, n->instr))
  831:          continue;
  832: 
  833:       unsigned d = node_delay(ctx, n);
  834: 
  835:       enum choose_instr_inc_rank rank;
  836:       if (d == 0)
  837:          rank = INC_DISTANCE_READY;
  838:       else
  839:          rank = INC_DISTANCE;
  840: 
  841:       unsigned distance = nearest_use(n->instr);
  842: 
  843:       if (!chosen || rank > chosen_rank ||
  844:           (rank == chosen_rank && distance < chosen_distance)) {
  845:          chosen = n;
  846:          chosen_distance = distance;
  847:          chosen_rank = rank;
  848:       }
  849:    }
  850: 
  851:    if (chosen) {
  852:       di(chosen->instr, "inc%s: chose (%s)", mode, inc_rank_name(chosen_rank));
  853:       return chosen;
  854:    }
  855: 
  856:    return NULL;
  857: }
  858: 
  859: /* Handles instruction selections for instructions we want to prioritize
  860:  * even if csp/csr would not pick them.
  861:  */
  862: static struct ir3_sched_node *
  863: choose_instr_prio(struct ir3_sched_ctx *ctx, struct ir3_sched_notes *notes)
  864: {
  865:    struct ir3_sched_node *chosen = NULL;

==================== TU_LRZ_BODY_PART1 (src/freedreno/vulkan/tu_lrz.cc:100-420) ====================
  100: {
  101:    assert(reason);
  102:    if (cmd->state.rp.lrz_write_disabled)
  103:       return;
  104: 
  105:    cmd->state.rp.lrz_write_disabled = true;
  106:    cmd->state.rp.lrz_write_disabled_at_draw = cmd->state.rp.drawcall_count;
  107:    cmd->state.rp.lrz_write_disable_reason = reason;
  108:    perf_debug(
  109:       cmd->device,
  110:       "Disabling LRZ write for the rest of the RP because '%s' at draw %u",
  111:       reason, cmd->state.rp.lrz_write_disabled_at_draw);
  112:    trace_warning_lrz_write_disabled(&cmd->rp_trace, &cmd->draw_cs, cmd, reason);
  113: }
  114: 
  115: template <chip CHIP>
  116: static void
  117: tu6_emit_lrz_buffer(struct tu_cs *cs, struct tu_image *depth_image)
  118: {
  119:    tu_crb crb = cs->crb(8);
  120: 
  121:    if (!depth_image) {
  122:       crb.add(GRAS_LRZ_BUFFER_BASE(CHIP, 0))
  123:          .add(GRAS_LRZ_BUFFER_PITCH(CHIP, 0))
  124:          .add(A6XX_GRAS_LRZ_FAST_CLEAR_BUFFER_BASE(0));
  125: 
  126:       if (CHIP >= A7XX) {
  127:          crb.add(GRAS_LRZ_DEPTH_BUFFER_INFO(CHIP));
  128:          crb.add(GRAS_LRZ_CB_CNTL(CHIP));
  129:       }
  130: 
  131:       if (CHIP >= A8XX) {
  132:          crb.add(GRAS_LRZ_BUFFER_SLICE_PITCH(CHIP));
  133:       }
  134: 
  135:       return;
  136:    }
  137: 
  138:    uint64_t lrz_iova = depth_image->iova + depth_image->lrz_layout.lrz_offset;
  139:    uint64_t lrz_fc_iova =
  140:       depth_image->iova + depth_image->lrz_layout.lrz_fc_offset;
  141:    if (!depth_image->lrz_layout.lrz_fc_offset)
  142:       lrz_fc_iova = 0;
  143: 
  144:    crb.add(GRAS_LRZ_BUFFER_BASE(CHIP, .qword = lrz_iova))
  145:       .add(GRAS_LRZ_BUFFER_PITCH(
  146:          CHIP, .pitch = depth_image->lrz_layout.lrz_pitch * sizeof(uint16_t),
  147:          .array_pitch = depth_image->lrz_layout.lrz_layer_size))
  148:       .add(A6XX_GRAS_LRZ_FAST_CLEAR_BUFFER_BASE(.qword = lrz_fc_iova));
  149: 
  150:    if (CHIP >= A7XX) {
  151:       crb.add(GRAS_LRZ_DEPTH_BUFFER_INFO(CHIP, .depth_format = tu6_pipe2depth(
  152:                                                  depth_image->vk.format)));
  153:       crb.add(GRAS_LRZ_CB_CNTL(CHIP, .double_buffer_pitch =
  154:                                    depth_image->lrz_layout.lrz_buffer_size));
  155:    }
  156: 
  157:    if (CHIP >= A8XX) {
  158:       crb.add(GRAS_LRZ_BUFFER_SLICE_PITCH(CHIP,
  159:          depth_image->lrz_layout.lrz_slice_pitch
  160:       ));
  161:    }
  162: }
  163: 
  164: static void
  165: tu6_write_lrz_reg(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
  166:                   struct tu_reg_value reg)
  167: {
  168:    if (cmd->device->physical_device->info->props.lrz_track_quirk) {
  169:       tu_cs_emit_pkt7(cs, CP_REG_WRITE, 3);
  170:       tu_cs_emit(cs, CP_REG_WRITE_0_TRACKER(TRACK_LRZ));
  171:       tu_cs_emit(cs, reg.reg);
  172:       tu_cs_emit(cs, reg.value);
  173:    } else {
  174:       tu_cs_emit_pkt4(cs, reg.reg, 1);
  175:       tu_cs_emit(cs, reg.value);
  176:    }
  177: }
  178: 
  179: template <chip CHIP>
  180: static void
  181: tu6_write_lrz_cntl(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
  182:                    struct __GRAS_LRZ_CNTL cntl)
  183: {
  184:    if (CHIP >= A7XX) {
  185:       /* A7XX split LRZ_CNTL into two seperate registers. */
  186:       struct tu_reg_value cntl2 = GRAS_LRZ_CNTL2(CHIP,
  187:          .disable_on_wrong_dir = cntl.disable_on_wrong_dir,
  188:          .fc_enable = cntl.fc_enable,
  189:       );
  190:       cntl.disable_on_wrong_dir = false;
  191:       cntl.fc_enable = false;
  192: 
  193:       tu6_write_lrz_reg(cmd, cs, __GRAS_LRZ_CNTL<CHIP>(cntl));
  194:       tu6_write_lrz_reg(cmd, cs, cntl2);
  195:    } else {
  196:       tu6_write_lrz_reg(cmd, cs, __GRAS_LRZ_CNTL<CHIP>(cntl));
  197:    }
  198: }
  199: 
  200: template <chip CHIP>
  201: static void
  202: tu_lrz_emit_force_disable_for_rp(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
  203: {
  204:    cmd->state.rp.lrz_disable_for_next_rp = true;
  205: 
  206:    if (CHIP >= A7XX) {
  207:       const struct tu_reg_value reg = GRAS_SC_BIN_CNTL(CHIP, .force_lrz_dis = true,
  208:                                                              .force_bi_dir_lrz_disable = CHIP >= A8XX);
  209: 
  210:       cs->rmw(reg, { .src0 = ~0u, .src1 = reg.value });
  211:    } else {
  212:       /* A6XX does not support GRAS_SC_BIN_CNTL.FORCE_LRZ_DIS */
  213:       tu6_write_lrz_reg(cmd, cs, A6XX_GRAS_LRZ_VIEW_INFO(
  214:          .base_layer = 0b11111111111,
  215:          .layer_count = 0b11111111111,
  216:          .base_mip_level = 0b1111,
  217:       ));
  218:    }
  219: }
  220: 
  221: template <chip CHIP>
  222: static void
  223: tu6_disable_lrz_via_depth_view(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
  224: {
  225:    /* Disable direction by writing invalid depth view. */
  226:    tu6_write_lrz_reg(cmd, cs, A6XX_GRAS_LRZ_VIEW_INFO(
  227:       .base_layer = 0b11111111111,
  228:       .layer_count = 0b11111111111,
  229:       .base_mip_level = 0b1111,
  230:    ));
  231: 
  232:    tu6_write_lrz_cntl<CHIP>(cmd, cs, {
  233:       .enable = true,
  234:       .disable_on_wrong_dir = true,
  235:    });
  236: 
  237:    tu_emit_event_write<CHIP>(cmd, cs, FD_LRZ_CLEAR);
  238:    tu_emit_event_write<CHIP>(cmd, cs, FD_LRZ_FLUSH);
  239: }
  240: 
  241: static void
  242: tu_lrz_init_state(struct tu_cmd_buffer *cmd,
  243:                   const struct tu_render_pass_attachment *att,
  244:                   const struct tu_image_view *view)
  245: {
  246:    if (!view->image->lrz_layout.lrz_total_size) {
  247:       trace_warning_depth_image_no_lrz(&cmd->trace, &cmd->draw_cs, cmd);
  248:       return;
  249:    }
  250: 
  251:    bool clears_depth = att->clear_mask &
  252:       (VK_IMAGE_ASPECT_COLOR_BIT | VK_IMAGE_ASPECT_DEPTH_BIT);
  253:    bool has_gpu_tracking =
  254:       cmd->device->physical_device->info->props.has_lrz_dir_tracking;
  255: 
  256:    if (!has_gpu_tracking && (!clears_depth || cmd->state.resuming))
  257:       return;
  258: 
  259:    /* We need to always have an LRZ view just to disable it if there is a
  260:     * depth attachment, there are any secondaries, and GPU tracking is
  261:     * enabled, in order not to rely on loadOp state which doesn't exist with
  262:     * dynamic rendering in secondaries. Otherwise the secondary will have LRZ
  263:     * enabled and there will be a NULL/garbage LRZ buffer.
  264:     */
  265:    cmd->state.lrz.image_view = view;
  266:    cmd->state.lrz.store = att->store;
  267: 
  268:    /* Reusing previous state doesn't work with FDM offset because the LRZ
  269:     * image is offsetted.
  270:     */
  271:    if ((view->image->vk.create_flags &
  272:         VK_IMAGE_CREATE_FRAGMENT_DENSITY_MAP_OFFSET_BIT_EXT) &&
  273:        !clears_depth) {
  274:       tu_lrz_invalidate(cmd, "FRAGMENT_DENSITY_MAP_OFFSET_BIT attachment used without depth attachment clear");
  275:       return;
  276:    }
  277: 
  278:    if (!clears_depth && !att->load) {
  279:       tu_lrz_invalidate(cmd, "Depth attachment isn't loaded or cleared");
  280:       return;
  281:    }
  282: 
  283:    cmd->state.lrz.valid = true;
  284:    cmd->state.lrz.valid_at_start = true;
  285:    /* We have to assume previous draws may have set color_written_with_z_test */
  286:    cmd->state.lrz.color_written_with_z_test = cmd->state.resuming;
  287:    cmd->state.lrz.has_lrz_write_with_skipped_color_writes = false;
  288:    cmd->state.lrz.prev_direction = TU_LRZ_UNKNOWN;
  289:    /* Be optimistic and unconditionally enable fast-clear in
  290:     * secondary cmdbufs and when reusing previous LRZ state.
  291:     */
  292:    cmd->state.lrz.fast_clear =
  293:       view->image->lrz_layout.lrz_fc_size > 0 && !TU_DEBUG(NOLRZFC);
  294: 
  295:    cmd->state.lrz.gpu_dir_tracking = has_gpu_tracking;
  296:    cmd->state.lrz.reuse_previous_state = !clears_depth;
  297: 
  298:    if (clears_depth) {
  299:       const uint32_t render_area_count = cmd->state.per_layer_render_area ? cmd->state.pass->num_views : 1;
  300: 
  301:       for (uint32_t i = 0; i < render_area_count; i++) {
  302:          const VkRect2D *render_area = &cmd->state.render_areas[i];
  303: 
  304:          /* The LRZ clear doesn't take render area into account and clears the whole LRZ image.
  305:           * If the render area is smaller than the depth image, then clear corrupts the LRZ outside
  306:           * of the render area and we won't be able to reuse LRZ in the next render pass.
  307:           */
  308:          if (render_area->offset.x != 0 || render_area->offset.y != 0 ||
  309:              render_area->extent.width != view->vk.extent.width ||
  310:              render_area->extent.height != view->vk.extent.height) {
  311:             cmd->state.rp.lrz_disable_for_next_rp = true;
  312:             break;
  313:          }
  314:       }
  315:    }
  316: }
  317: 
  318: /* Note: if we enable LRZ here, then tu_lrz_init_state() must at least set
  319:  * lrz.image_view, so that an LRZ buffer is present (even if LRZ is
  320:  * dynamically disabled).
  321:  */
  322: 
  323: static void
  324: tu_lrz_init_secondary(struct tu_cmd_buffer *cmd,
  325:                       const struct tu_render_pass_attachment *att)
  326: {
  327:    bool has_gpu_tracking =
  328:       cmd->device->physical_device->info->props.has_lrz_dir_tracking;
  329: 
  330:    if (!has_gpu_tracking)
  331:       return;
  332: 
  333:    if (!cmd->device->use_lrz || TU_DEBUG(NOLRZ))
  334:       return;
  335: 
  336:    if (!vk_format_has_depth(att->format))
  337:       return;
  338: 
  339:    cmd->state.lrz.valid = true;
  340:    cmd->state.lrz.valid_at_start = true;
  341:    /* We will disable LRZ via tu_lrz_flush_valid_at_secondary_rp_boundary
  342:     * if assumption about color_written_with_z_test is wrong.
  343:     */
  344:    cmd->state.lrz.color_written_with_z_test = false;
  345:    cmd->state.lrz.has_lrz_write_with_skipped_color_writes = false;
  346:    cmd->state.lrz.prev_direction = TU_LRZ_UNKNOWN;
  347:    cmd->state.lrz.gpu_dir_tracking = has_gpu_tracking;
  348: 
  349:    /* We may not have the depth attachment when executing in a secondary
  350:     * inside a render pass. This means we have to be even more optimistic than
  351:     * the normal case and enable fast clear even if the depth image doesn't
  352:     * support it.
  353:     */
  354:    cmd->state.lrz.fast_clear = true;
  355: 
  356:    /* These are not used inside secondaries */
  357:    cmd->state.lrz.image_view = NULL;
  358:    cmd->state.lrz.reuse_previous_state = false;
  359: }
  360: 
  361: template <chip CHIP>
  362: bool
  363: tu_lrzfc_depth_supported(float depth) {
  364:    /* A7XX supports fast-clearing to any value, while A6XX only supports 0.0/1.0 */
  365:    return CHIP >= A7XX || depth == 0.0f || depth == 1.0f;
  366: }
  367: 
  368: /* This is generally the same as tu_lrz_begin_renderpass(), but we skip
  369:  * actually emitting anything. The lrz state needs to be consistent between
  370:  * renderpasses, but only the first should actually emit commands to disable
  371:  * lrz etc.
  372:  */
  373: template <chip CHIP>
  374: void
  375: tu_lrz_begin_resumed_renderpass(struct tu_cmd_buffer *cmd)
  376: {
  377:     /* Track LRZ valid state */
  378:    memset(&cmd->state.lrz, 0, sizeof(cmd->state.lrz));
  379: 
  380:    if (TU_DEBUG(NOLRZ)) {
  381:       cmd->state.dirty |= TU_CMD_DIRTY_LRZ;
  382:       return;
  383:    }
  384: 
  385:    uint32_t a = VK_ATTACHMENT_UNUSED;
  386:    for (uint32_t subpass_idx = 0; subpass_idx < cmd->state.pass->subpass_count; subpass_idx++) {
  387:       const struct tu_subpass *subpass = &cmd->state.pass->subpasses[subpass_idx];
  388: 
  389:       if (subpass->custom_resolve)
  390:          continue;
  391: 
  392:       a = subpass->depth_stencil_attachment.attachment;
  393: 
  394:       if (a != VK_ATTACHMENT_UNUSED && cmd->state.attachments[a]->image->lrz_layout.lrz_total_size) {
  395:          break;
  396:       }
  397:    }
  398: 
  399:    if (a != VK_ATTACHMENT_UNUSED) {
  400:       const struct tu_render_pass_attachment *att = &cmd->state.pass->attachments[a];
  401:       tu_lrz_init_state(cmd, att, cmd->state.attachments[a]);
  402:       if (att->clear_mask & (VK_IMAGE_ASPECT_COLOR_BIT | VK_IMAGE_ASPECT_DEPTH_BIT)) {
  403:          VkClearValue clear = cmd->state.clear_values[a];
  404:          cmd->state.lrz.depth_clear_value = clear;
  405:          cmd->state.lrz.fast_clear = cmd->state.lrz.fast_clear &&
  406:                                      tu_lrzfc_depth_supported<CHIP>(clear.depthStencil.depth);
  407:       }
  408:       cmd->state.dirty |= TU_CMD_DIRTY_LRZ;
  409:    }
  410: }
  411: TU_GENX(tu_lrz_begin_resumed_renderpass);
  412: 
  413: template <chip CHIP>
  414: void
  415: tu_lrz_begin_renderpass(struct tu_cmd_buffer *cmd)
  416: {
  417:    const struct tu_render_pass *pass = cmd->state.pass;
  418: 
  419:    cmd->state.rp.lrz_write_disabled = false;
  420:    cmd->state.rp.lrz_disable_reason = NULL;

==================== TU_LRZ_BODY_PART2 (src/freedreno/vulkan/tu_lrz.cc:421-760) ====================
  421:    cmd->state.rp.lrz_disabled_at_draw = 0;
  422:    cmd->state.rp.lrz_write_disable_reason = NULL;
  423:    cmd->state.rp.lrz_write_disabled_at_draw = 0;
  424: 
  425:    bool multiple_lrz_attachments = false;
  426:    uint32_t prev_depth_a = VK_ATTACHMENT_UNUSED;
  427:    for (uint32_t subpass_idx = 0; subpass_idx < cmd->state.pass->subpass_count; subpass_idx++) {
  428:       const struct tu_subpass *subpass = &cmd->state.pass->subpasses[subpass_idx];
  429: 
  430:       if (subpass->custom_resolve)
  431:          continue;
  432: 
  433:       uint32_t a = subpass->depth_stencil_attachment.attachment;
  434: 
  435:       if (a != VK_ATTACHMENT_UNUSED && cmd->state.attachments[a]->image->lrz_layout.lrz_total_size) {
  436:          if (prev_depth_a != VK_ATTACHMENT_UNUSED && prev_depth_a != a) {
  437:             multiple_lrz_attachments = true;
  438:             break;
  439:          }
  440:          prev_depth_a = a;
  441:       }
  442:    }
  443: 
  444:    if (cmd->device->physical_device->info->props.has_lrz_dir_tracking && multiple_lrz_attachments) {
  445:       /* Theoretically we could switch between LRZ buffers during the binning
  446:        * and tiling passes, but it is untested and would add complexity for
  447:        * presumably extremely rare case.
  448:        */
  449:       tu_lrz_invalidate(cmd, "Several subpasses with different depth attachments");
  450: 
  451:       for (unsigned i = 0; i < pass->attachment_count; i++) {
  452:          struct tu_image *image = cmd->state.attachments[i]->image;
  453:          tu_disable_lrz<CHIP>(cmd, &cmd->cs, image);
  454:       }
  455: 
  456:       /* We need a valid LRZ fast-clear base, in case the render pass contents
  457:        * are in secondaries that enable LRZ, so that they can read that LRZ is
  458:        * dynamically disabled. It doesn't matter which we use, so just leave
  459:        * the last one as emitted in tu_disable_lrz().
  460:        */
  461:       memset(&cmd->state.lrz, 0, sizeof(cmd->state.lrz));
  462:       return;
  463:    }
  464: 
  465:    for (uint32_t subpass_idx = 0; subpass_idx < pass->subpass_count; subpass_idx++) {
  466:       const struct tu_subpass *subpass = &pass->subpasses[subpass_idx];
  467:       uint32_t a = subpass->depth_stencil_attachment.attachment;
  468: 
  469:       if (subpass->custom_resolve && a != VK_ATTACHMENT_UNUSED) {
  470:          struct tu_image *image = cmd->state.attachments[a]->image;
  471:          tu_disable_lrz<CHIP>(cmd, &cmd->cs, image);
  472:       }
  473: 
  474:       if (subpass->resolve_depth_stencil) {
  475:          for (unsigned i = 0; i < subpass->resolve_count; i++) {
  476:             uint32_t a = subpass->resolve_attachments[i].attachment;
  477:             if (a == VK_ATTACHMENT_UNUSED || cmd->state.attachments[a]->image->lrz_layout.lrz_total_size == 0)
  478:                continue;
  479: 
  480:             tu_disable_lrz<CHIP>(cmd, &cmd->cs, cmd->state.attachments[a]->image);
  481:          }
  482:       }
  483:    }
  484: 
  485:     /* Track LRZ valid state */
  486:    tu_lrz_begin_resumed_renderpass<CHIP>(cmd);
  487: 
  488:    if (!cmd->state.lrz.valid_at_start) {
  489:       tu6_write_lrz_cntl<CHIP>(cmd, &cmd->cs, {});
  490:       tu6_emit_lrz_buffer<CHIP>(&cmd->cs, NULL);
  491:    }
  492: 
  493:    /* Multisample and single-sample LRZ layout are different, so when
  494:     * unresolving a depth image we have to disable LRZ for the entirety of the
  495:     * render pass.
  496:     */
  497:    for (unsigned i = 0; i < cmd->state.pass->subpass_count; i++) {
  498:       const struct tu_subpass *subpass = &cmd->state.pass->subpasses[i];
  499:       if (subpass->depth_stencil_attachment.attachment != VK_ATTACHMENT_UNUSED &&
  500:           subpass->unresolve_count > subpass->color_count &&
  501:           subpass->unresolve_attachments[subpass->color_count].attachment !=
  502:           VK_ATTACHMENT_UNUSED) {
  503:          tu_lrz_disable_during_renderpass<CHIP>(cmd, "multisampled_render_to_single_sample with LOAD_OP_LOAD");
  504:       }
  505:    }
  506: }
  507: TU_GENX(tu_lrz_begin_renderpass);
  508: 
  509: void
  510: tu_lrz_begin_secondary_cmdbuf(struct tu_cmd_buffer *cmd)
  511: {
  512:    memset(&cmd->state.lrz, 0, sizeof(cmd->state.lrz));
  513: 
  514:    uint32_t a = cmd->state.subpass->depth_stencil_attachment.attachment;
  515: 
  516:    if (cmd->state.subpass->custom_resolve) {
  517:       cmd->state.lrz.valid = a == VK_ATTACHMENT_UNUSED;
  518:       return;
  519:    }
  520: 
  521:    if (a != VK_ATTACHMENT_UNUSED) {
  522:       const struct tu_render_pass_attachment *att = &cmd->state.pass->attachments[a];
  523:       tu_lrz_init_secondary(cmd, att);
  524:    }
  525: }
  526: 
  527: void
  528: tu_lrz_cb_begin(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
  529: {
  530:    /* The LRZ double-buffering guarantees that passes that clear or discard
  531:     * depth don't have to worry about LRZ dependencies. However we do have to
  532:     * worry about renderpasses that load depth, because we cannot flip LRZ
  533:     * then and have to reuse what the previous pass wrote. There is then a
  534:     * write-after-read dependency from an earlier subpass reading LRZ. We
  535:     * solve this using CP_RESOURCE_LIST, because the Vulkan user doesn't have
  536:     * to track render-and-clear dependencies vs. render-and-render depdencies
  537:     * (LOAD_OP_CLEAR happens in the same stage as rendering).
  538:     */
  539:    if (!cmd->state.lrz.image_view)
  540:       return;
  541: 
  542:    uint64_t iova =
  543:       cmd->state.lrz.image_view->image->iova +
  544:       cmd->state.lrz.image_view->image->lrz_layout.lrz_offset;
  545:    uint64_t fc_iova =
  546:       cmd->state.lrz.image_view->image->iova +
  547:       cmd->state.lrz.image_view->image->lrz_layout.lrz_fc_offset;
  548: 
  549:    if (cmd->state.lrz.reuse_previous_state) {
  550:       tu_cs_emit_pkt7(cs, CP_RESOURCE_LIST, 4);
  551:       tu_cs_emit(cs, 1); /* BV count */
  552:       tu_cs_emit_qw(cs, iova | CP_BV_RESOURCE_0_WRITE);
  553:       tu_cs_emit(cs, 0); /* BR count */
  554:    }
  555: 
  556:    if (cmd->state.lrz.store) {
  557:       tu_cs_emit_pkt7(cs, CP_RESOURCE_LIST, 4);
  558:       tu_cs_emit(cs, 0); /* BV count */
  559:       tu_cs_emit(cs, CP_RESOURCE_LIST_BR_0_BR_COUNT(1) |
  560:                      CP_RESOURCE_LIST_BR_0_OVERFLOW |
  561:                      CP_RESOURCE_LIST_BR_0_OVERFLOW_ONCHIP_ADDR(TU_ONCHIP_CB_RESLIST_OVERFLOW));
  562:       tu_cs_emit_qw(cs, iova);
  563:    }
  564: 
  565:    /* See tu_lrz_before_tiles() */
  566:    tu_cs_emit_pkt7(cs, CP_RESOURCE_LIST, 4);
  567:    tu_cs_emit(cs, 1); /* BV count */
  568:    tu_cs_emit_qw(cs, CP_BV_RESOURCE_0_ENCODING(BV_RES_LRZ) | fc_iova);
  569:    tu_cs_emit(cs, 0); /* BR count */
  570: }
  571: 
  572: template <chip CHIP>
  573: static void
  574: tu_lrz_clear(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
  575:              struct tu_image *image, const VkClearValue *clear_value,
  576:              bool fast_clear)
  577: {
  578:    bool has_gpu_tracking =
  579:       cmd->device->physical_device->info->props.has_lrz_dir_tracking;
  580: 
  581:    if (fast_clear || has_gpu_tracking) {
  582:       tu6_write_lrz_cntl<CHIP>(cmd, cs, {
  583:          .enable = true,
  584:          .fc_enable = fast_clear,
  585:          .disable_on_wrong_dir = has_gpu_tracking,
  586:       });
  587: 
  588:       /* LRZ_CLEAR.fc_enable + LRZ_CLEAR - clears fast-clear buffer;
  589:        * LRZ_CLEAR.disable_on_wrong_dir + LRZ_CLEAR - sets direction to
  590:        *  CUR_DIR_UNSET.
  591:        *
  592:        * We do the clear event even if fast-clear is disabled to set the
  593:        * direction to CUR_DIR_UNSET.
  594:        */
  595:       if (CHIP >= A7XX)
  596:          tu_cs_emit_regs(cs, GRAS_LRZ_DEPTH_CLEAR(CHIP, clear_value->depthStencil.depth));
  597:       tu_emit_event_write<CHIP>(cmd, cs, FD_LRZ_CLEAR);
  598: 
  599:       /* The flag RAM may not cover the whole LRZ image. FD_LRZ_CLEAR only
  600:        * clears the part it does cover, so clear the rest explicitly.
  601:        */
  602:       if (fast_clear) {
  603:          if (!fdl6_lrz_fc_fully_covered(&image->lrz_layout)) {
  604:             tu6_clear_lrz_partial<CHIP>(cmd, cs, image, clear_value);
  605:          }
  606:       }
  607:    }
  608: 
  609:    if (!fast_clear) {
  610:       tu6_clear_lrz<CHIP>(cmd, cs, image, clear_value);
  611:       /* Even though we disable fast-clear we still have to dirty
  612:        * fast-clear buffer because both secondary cmdbufs and following
  613:        * renderpasses won't know that fast-clear is disabled.
  614:        *
  615:        * TODO: we could avoid this in renderpass clears if we don't store
  616:        * depth and don't expect secondary cmdbufs.
  617:        */
  618:       if (image->lrz_layout.lrz_fc_size > 0) {
  619:          tu6_dirty_lrz_fc<CHIP>(cmd, cs, image);
  620:       }
  621:    }
  622: }
  623: 
  624: template <chip CHIP>
  625: void
  626: tu_lrz_tiling_begin(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
  627: {
  628:    /* TODO: If lrz was never valid for the entire renderpass, we could exit
  629:     * early here. Sometimes we know this ahead of time and null out
  630:     * image_view, but with LOAD_OP_DONT_CARE this only happens if there were
  631:     * no secondaries.
  632:     */
  633:    if (!cmd->state.lrz.image_view)
  634:       return;
  635: 
  636:    struct tu_lrz_state *lrz = &cmd->state.lrz;
  637: 
  638:    tu6_emit_lrz_buffer<CHIP>(cs, lrz->image_view->image);
  639: 
  640:    if (lrz->reuse_previous_state) {
  641:       /* Reuse previous LRZ state, LRZ cache is assumed to be
  642:        * already invalidated by previous renderpass.
  643:        */
  644:       assert(lrz->gpu_dir_tracking);
  645: 
  646:       tu6_write_lrz_reg(cmd, cs,
  647:          A6XX_GRAS_LRZ_VIEW_INFO(.dword = lrz->image_view->view.GRAS_LRZ_VIEW_INFO));
  648:       return;
  649:    }
  650: 
  651:    /* If CB is dynamically enabled, then this is executed on BV. Flip the
  652:     * buffer BV is using.
  653:     */
  654:    if (CHIP >= A7XX) {
  655:       tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(PRED_TEST) |
  656:                              CP_COND_REG_EXEC_0_PRED_BIT(TU_PREDICATE_CB_ENABLED));
  657:       tu_emit_event_write<CHIP>(cmd, cs, FD_LRZ_FLIP);
  658:       tu_cond_exec_end(cs);
  659:    }
  660: 
  661:    if (!lrz->valid_at_start) {
  662:       /* If LRZ was never valid so disable it manually here.
  663:        * This is accomplished by making later GRAS_LRZ_CNTL (in binning pass)
  664:        * to fail the comparison of depth views.
  665:        */
  666:       if (lrz->gpu_dir_tracking) {
  667:          tu6_disable_lrz_via_depth_view<CHIP>(cmd, cs);
  668:          tu6_write_lrz_reg(cmd, cs, A6XX_GRAS_LRZ_VIEW_INFO(.dword = 0));
  669:       }
  670:       return;
  671:    }
  672: 
  673:    if (lrz->gpu_dir_tracking) {
  674:       tu6_write_lrz_reg(cmd, cs,
  675:          A6XX_GRAS_LRZ_VIEW_INFO(.dword = lrz->image_view->view.GRAS_LRZ_VIEW_INFO));
  676:    }
  677: 
  678:    tu_lrz_clear<CHIP>(cmd, cs, lrz->image_view->image,
  679:                       &lrz->depth_clear_value, lrz->fast_clear);
  680: }
  681: TU_GENX(tu_lrz_tiling_begin);
  682: 
  683: template <chip CHIP>
  684: void
  685: tu_lrz_after_bv(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
  686: {
  687:    if (CHIP < A7XX)
  688:       return;
  689: 
  690:    /* BV and BR have different LRZ caches, so flush LRZ cache to be read by
  691:     * BR.
  692:     */
  693:    tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(PRED_TEST) |
  694:                           CP_COND_REG_EXEC_0_PRED_BIT(TU_PREDICATE_CB_ENABLED));
  695:    tu_emit_event_write<CHIP>(cmd, cs, FD_LRZ_FLUSH);
  696:    tu_cond_exec_end(cs);
  697: }
  698: TU_GENX(tu_lrz_after_bv);
  699: 
  700: static void
  701: tu_lrz_clear_resource(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
  702: {
  703:    uint64_t fc_iova =
  704:       cmd->state.lrz.image_view->image->iova +
  705:       cmd->state.lrz.image_view->image->lrz_layout.lrz_fc_offset;
  706: 
  707:    tu_cs_emit_pkt7(cs, CP_EVENT_WRITE7, 3);
  708:    tu_cs_emit(cs, CP_EVENT_WRITE7_0_EVENT(DUMMY_EVENT) |
  709:                   CP_EVENT_WRITE7_0_CLEAR_LRZ_RESOURCE);
  710:    tu_cs_emit_qw(cs, fc_iova); /* resource to clear */
  711: }
  712: 
  713: template <chip CHIP>
  714: void
  715: tu_lrz_before_tiles(struct tu_cmd_buffer *cmd, struct tu_cs *cs, bool use_cb)
  716: {
  717:    if (CHIP < A7XX)
  718:       return;
  719: 
  720:    tu7_set_pred_bit(cs, TU_PREDICATE_FIRST_TILE, true);
  721: 
  722:    if (!cmd->state.lrz.image_view)
  723:       return;
  724: 
  725:    /* By clearing the LRZ resource before rendering, we make any future
  726:     * binning pass writing to the same LRZ image wait for all renderpasses
  727:     * before this one. Crucially this includes any earlier renderpass reading
  728:     * from the same LRZ buffer. Because LRZ is only double-buffered but it's
  729:     * possible to have more than two visibility streams, this is necessary to
  730:     * prevent write-after-read hazards if BV writes the same LRZ image more
  731:     * than once before BR reads it.
  732:     *
  733:     * For example, consider the sequence:
  734:     *
  735:     * RP 1 clears + writes depth image A
  736:     * - BV: Clear + write LRZ image A
  737:     * - BR: Read LRZ image A
  738:     * RP 2 clears + writes depth image A
  739:     * - BV: Clear + write LRZ image A
  740:     * - BR: Read LRZ image A
  741:     * RP 3 clears + writes depth image A
  742:     * - BV: Clear + write LRZ image A
  743:     * - BR: Read LRZ image A
  744:     *
  745:     * RP 1 BV will write to one LRZ image, RP 2 BV will write to the other,
  746:     * and then RP 3 BV must stall until RP 1 BR is done reading/writing the
  747:     * first LRZ image. Specifiying the LRZ resource before BV starts and
  748:     * clearing it before BR starts will cause RP 2 BV to stall until RP 1 BR
  749:     * starts, which technically isn't necessary, but it will also cause RP 3
  750:     * BV to stall until RP 2 BR has started and RP 1 BR has finished.
  751:     *
  752:     * This pairs with the last CP_RESOURCE_LIST in tu_lrz_cb_begin().
  753:     */
  754:    if (use_cb)
  755:       tu_lrz_clear_resource(cmd, cs);
  756: }
  757: TU_GENX(tu_lrz_before_tiles);
  758: 
  759: static void
  760: tu_lrz_emit_view_info(struct tu_cmd_buffer *cmd, struct tu_cs *cs)

==================== USE_SYSMEM_RENDERING_PART2 (src/freedreno/vulkan/tu_cmd_buffer.cc:1490-1610) ====================
 1490:       cmd->state.rp.force_render_mode_reason =
 1491:          "QUERY_TYPE_PRIMITIVES_GENERATED is incompatible with non-hw binning GMEM rendering";
 1492:       return true;
 1493:    }
 1494: 
 1495:    if (TU_DEBUG(GMEM)) {
 1496:       cmd->state.rp.force_render_mode_reason = "TU_DEBUG(GMEM)";
 1497:       return false;
 1498:    }
 1499: 
 1500:    /* This is a case where it's better to avoid GMEM, too many tiles but no HW binning possible. */
 1501:    if (!vsc->binning_possible && vsc->binning_useful) {
 1502:       cmd->state.rp.force_render_mode_reason =
 1503:          "Too many tiles and HW binning is not possible";
 1504:       return true;
 1505:    }
 1506: 
 1507:    tu_autotune::render_mode optimal_mode =
 1508:       cmd->device->autotune->get_optimal_mode(cmd, rp_ctx, rp_key);
 1509: 
 1510:    return optimal_mode == tu_autotune::render_mode::SYSMEM;
 1511: }
 1512: 
 1513: /* Optimization: there is no reason to load gmem if there is no
 1514:  * geometry to process. COND_REG_EXEC predicate is set here,
 1515:  * but the actual skip happens in tu_load_gmem_attachment() and tile_store_cs,
 1516:  * for each blit separately.
 1517:  */
 1518: template <chip CHIP>
 1519: static void
 1520: tu6_emit_cond_for_load_stores(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
 1521:                               uint32_t pipe, uint32_t slot, bool skip_wfm)
 1522: {
 1523:    const struct tu_vsc_config *vsc = tu_vsc_config(cmd, cmd->state.tiling);
 1524: 
 1525:    if (vsc->binning_possible &&
 1526:        cmd->state.pass->has_cond_load_store) {
 1527:       if (CHIP >= A7XX) {
 1528:          tu_cs_emit_pkt7(cs, CP_REG_TEST, 1);
 1529:          tu_cs_emit(cs, A6XX_CP_REG_TEST_0_OC_MEM_OFFSET(pipe) |
 1530:                         A6XX_CP_REG_TEST_0_SOURCE(SOURCE_OC_MEM) |
 1531:                         A6XX_CP_REG_TEST_0_BIT(slot) |
 1532:                         A6XX_CP_REG_TEST_0_SKIP_WAIT_FOR_ME);
 1533:       } else {
 1534:          tu_cs_emit_pkt7(cs, CP_REG_TEST, 1);
 1535:          tu_cs_emit(cs, A6XX_CP_REG_TEST_0_REG(REG_A6XX_VSC_CHANNEL_VISIBILITY(pipe)) |
 1536:                         A6XX_CP_REG_TEST_0_BIT(slot) |
 1537:                         COND(skip_wfm, A6XX_CP_REG_TEST_0_SKIP_WAIT_FOR_ME));
 1538:       }
 1539:    } else {
 1540:       /* COND_REG_EXECs are not emitted in non-binning case */
 1541:    }
 1542: }
 1543: 
 1544: template <chip CHIP>
 1545: static void
 1546: tu6_emit_bin_size_gmem(struct tu_cmd_buffer *cmd,
 1547:                        struct tu_cs *cs,
 1548:                        VkExtent2D gmem_extent,
 1549:                        enum a6xx_buffers_location buffers_location,
 1550:                        bool disable_lrz)
 1551: {
 1552:    struct tu_physical_device *phys_dev = cmd->device->physical_device;
 1553:    const struct tu_tiling_config *tiling = cmd->state.tiling;
 1554:    bool hw_binning = use_hw_binning(cmd);
 1555: 
 1556:    tu6_emit_bin_size<CHIP>(
 1557:       cs, buffers_location == BUFFERS_IN_GMEM ?
 1558:       tiling->tile0.width * gmem_extent.width : 0,
 1559:       buffers_location == BUFFERS_IN_GMEM ?
 1560:       tiling->tile0.height * gmem_extent.height : 0,
 1561:       {
 1562:          .render_mode = RENDERING_PASS,
 1563:          .force_lrz_write_dis = !phys_dev->info->props.has_lrz_feedback,
 1564:          .buffers_location = buffers_location,
 1565:          .lrz_feedback_zmode_mask =
 1566:             phys_dev->info->props.has_lrz_feedback
 1567:                ? (hw_binning ? LRZ_FEEDBACK_EARLY_Z_OR_EARLY_Z_LATE_Z :
 1568:                   LRZ_FEEDBACK_EARLY_Z_LATE_Z)
 1569:                : LRZ_FEEDBACK_NONE,
 1570:          .force_lrz_dis = CHIP >= A7XX && disable_lrz,
 1571:          .force_bi_dir_lrz_disable = CHIP >= A8XX && disable_lrz,
 1572:       });
 1573: 
 1574: }
 1575: 
 1576: /* Set always-identical registers used specifically for GMEM */
 1577: template <chip CHIP>
 1578: static void
 1579: tu7_emit_tile_render_begin_regs(struct tu_cs *cs)
 1580: {
 1581:    tu_cs_emit_regs(cs, RB_BUFFER_CNTL(CHIP, 0x0));
 1582:    tu_cs_emit_regs(cs, RB_CLEAR_TARGET(CHIP, .clear_mode = CLEAR_MODE_GMEM));
 1583: }
 1584: 
 1585: /* Set always-identical registers used specifically for sysmem */
 1586: template <chip CHIP>
 1587: static void
 1588: tu7_emit_sysmem_render_begin_regs(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
 1589: {
 1590:    tu_cs_emit_regs(cs, RB_BUFFER_CNTL(CHIP,
 1591:       .z_sysmem = true,
 1592:       .s_sysmem = true,
 1593:       .rt0_sysmem = true,
 1594:       .rt1_sysmem = true,
 1595:       .rt2_sysmem = true,
 1596:       .rt3_sysmem = true,
 1597:       .rt4_sysmem = true,
 1598:       .rt5_sysmem = true,
 1599:       .rt6_sysmem = true,
 1600:       .rt7_sysmem = true,
 1601:    ));
 1602: 
 1603:    tu_cs_emit_regs(cs, RB_CLEAR_TARGET(CHIP, .clear_mode = CLEAR_MODE_SYSMEM));
 1604: }
 1605: 
 1606: template <chip CHIP>
 1607: static void
 1608: tu6_emit_tile_select(struct tu_cmd_buffer *cmd,
 1609:                      struct tu_cs *cs,
 1610:                      const struct tu_tile_config *tile,

==================== TU_AUTOTUNE_FULL (src/freedreno/vulkan/tu_autotune.cc:1-320) ====================
    1: /*
    2:  * Copyright © 2021 Igalia S.L.
    3:  * SPDX-License-Identifier: MIT
    4:  */
    5: 
    6: #include "tu_autotune.h"
    7: 
    8: #include <algorithm>
    9: #include <array>
   10: #include <atomic>
   11: #include <cmath>
   12: #include <string>
   13: #include <string_view>
   14: 
   15: #include "util/rand_xor.h"
   16: 
   17: #define XXH_INLINE_ALL
   18: #include "util/xxhash.h"
   19: 
   20: #include "tu_cmd_buffer.h"
   21: #include "tu_cs.h"
   22: #include "tu_device.h"
   23: #include "tu_image.h"
   24: #include "tu_pass.h"
   25: 
   26: /** Compile-time debug options **/
   27: 
   28: #define TU_AUTOTUNE_DEBUG_LOG_BASE      0
   29: #define TU_AUTOTUNE_DEBUG_LOG_BANDWIDTH 0
   30: #define TU_AUTOTUNE_DEBUG_LOG_PROFILED  0
   31: #define TU_AUTOTUNE_DEBUG_LOG_PREEMPT   0
   32: 
   33: #if TU_AUTOTUNE_DEBUG_LOG_BASE
   34: #define at_log_base(fmt, ...)         mesa_logi("autotune: " fmt, ##__VA_ARGS__)
   35: #define at_log_base_h(fmt, hash, ...) mesa_logi("autotune %016" PRIx64 ": " fmt, hash, ##__VA_ARGS__)
   36: #else
   37: #define at_log_base(fmt, ...)
   38: #define at_log_base_h(fmt, hash, ...)
   39: #endif
   40: 
   41: #if TU_AUTOTUNE_DEBUG_LOG_BANDWIDTH
   42: #define at_log_bandwidth_h(fmt, hash, ...) mesa_logi("autotune-bw %016" PRIx64 ": " fmt, hash, ##__VA_ARGS__)
   43: #else
   44: #define at_log_bandwidth_h(fmt, hash, ...)
   45: #endif
   46: 
   47: #if TU_AUTOTUNE_DEBUG_LOG_PROFILED
   48: #define at_log_profiled_h(fmt, hash, ...) mesa_logi("autotune-prof %016" PRIx64 ": " fmt, hash, ##__VA_ARGS__)
   49: #else
   50: #define at_log_profiled_h(fmt, hash, ...)
   51: #endif
   52: 
   53: #if TU_AUTOTUNE_DEBUG_LOG_PREEMPT
   54: #define at_log_preempt_h(fmt, hash, ...) mesa_logi("autotune-preempt %016" PRIx64 ": " fmt, hash, ##__VA_ARGS__)
   55: #else
   56: #define at_log_preempt_h(fmt, hash, ...)
   57: #endif
   58: 
   59: /* Process any pending entries on autotuner finish, could be used to gather data from traces. */
   60: #define TU_AUTOTUNE_FLUSH_AT_FINISH 0
   61: 
   62: /** Global constants and helpers **/
   63: 
   64: /* GPU always-on timer constants */
   65: constexpr uint64_t ALWAYS_ON_FREQUENCY_HZ = 19'200'000;
   66: constexpr double GPU_TICKS_PER_US = ALWAYS_ON_FREQUENCY_HZ / 1'000'000.0;
   67: 
   68: constexpr uint64_t
   69: ticks_to_us(uint64_t ticks)
   70: {
   71:    return ticks / GPU_TICKS_PER_US;
   72: }
   73: 
   74: constexpr bool
   75: fence_before(uint32_t a, uint32_t b)
   76: {
   77:    /* Essentially a < b, but handles wrapped values. */
   78:    return static_cast<int32_t>(a - b) < 0;
   79: }
   80: 
   81: constexpr const char *
   82: render_mode_str(tu_autotune::render_mode mode)
   83: {
   84:    switch (mode) {
   85:    case tu_autotune::render_mode::SYSMEM:
   86:       return "SYSMEM";
   87:    case tu_autotune::render_mode::GMEM:
   88:       return "GMEM";
   89:    default:
   90:       return "UNKNOWN";
   91:    }
   92: }
   93: 
   94: /** Configuration **/
   95: 
   96: enum class tu_autotune::algorithm : uint8_t {
   97:    BANDWIDTH = 0,     /* Uses estimated BW for determining rendering mode. */
   98:    PROFILED = 1,      /* Uses dynamically profiled results for determining rendering mode. */
   99:    PROFILED_IMM = 2,  /* Same as PROFILED but immediately resolves the SYSMEM/GMEM probability. */
  100:    PREFER_SYSMEM = 3, /* Always use SYSMEM unless we have strong evidence that GMEM is better. */
  101:    PREFER_GMEM = 4,   /* Always use GMEM unless we have strong evidence that SYSMEM is better. */
  102: 
  103:    DEFAULT = BANDWIDTH, /* Default algorithm, used if no other is specified. */
  104: };
  105: 
  106: /* Modifier flags, these modify the behavior of the autotuner in a user-defined way. */
  107: enum class tu_autotune::mod_flag : uint8_t {
  108:    BIG_GMEM = BIT(1),         /* All RPs with >= 10 draws use GMEM. */
  109:    TUNE_SMALL = BIT(2),       /* Try tuning all RPs with <= 5 draws, ignored by default. */
  110:    PREEMPT_OPTIMIZE = BIT(3),  /* Attempts to minimize the preemption latency. */
  111: };
  112: 
  113: /* Metric flags, for internal tracking of enabled metrics. */
  114: enum class tu_autotune::metric_flag : uint8_t {
  115:    SAMPLES = BIT(1), /* Enable tracking samples passed metric. */
  116:    TS = BIT(2),      /* Enable tracking per-RP timestamp metric. */
  117:    TS_TILE = BIT(3), /* Enable tracking per-tile timestamp metric. */
  118: };
  119: 
  120: struct PACKED tu_autotune::config_t {
  121:  private:
  122:    algorithm algo = algorithm::DEFAULT;
  123:    uint8_t mod_flags = 0;    /* See mod_flag enum. */
  124:    uint8_t metric_flags = 0; /* See metric_flag enum. */
  125: 
  126:    constexpr void update_metric_flags()
  127:    {
  128:       /* Note: Always keep in sync with rp_history to prevent UB. */
  129:       if (algo == algorithm::BANDWIDTH) {
  130:          metric_flags |= static_cast<uint8_t>(metric_flag::SAMPLES);
  131:       } else if (algo == algorithm::PROFILED || algo == algorithm::PROFILED_IMM) {
  132:          metric_flags |= static_cast<uint8_t>(metric_flag::TS);
  133:       }
  134: 
  135:       if (mod_flags & static_cast<uint8_t>(mod_flag::PREEMPT_OPTIMIZE)) {
  136:          metric_flags |= static_cast<uint8_t>(metric_flag::TS) | static_cast<uint8_t>(metric_flag::TS_TILE);
  137:       }
  138:    }
  139: 
  140:  public:
  141:    constexpr config_t() = default;
  142: 
  143:    constexpr config_t(algorithm algo, uint8_t mod_flags): algo(algo), mod_flags(mod_flags)
  144:    {
  145:       update_metric_flags();
  146:    }
  147: 
  148:    constexpr bool is_enabled(algorithm a) const
  149:    {
  150:       return algo == a;
  151:    }
  152: 
  153:    constexpr bool test(mod_flag f) const
  154:    {
  155:       return mod_flags & static_cast<uint32_t>(f);
  156:    }
  157: 
  158:    constexpr bool test(metric_flag f) const
  159:    {
  160:       return metric_flags & static_cast<uint32_t>(f);
  161:    }
  162: 
  163:    constexpr bool set_algo(algorithm a)
  164:    {
  165:       if (algo == a)
  166:          return false;
  167: 
  168:       algo = a;
  169:       update_metric_flags();
  170:       return true;
  171:    }
  172: 
  173:    constexpr bool disable(mod_flag f)
  174:    {
  175:       if (!(mod_flags & static_cast<uint8_t>(f)))
  176:          return false;
  177: 
  178:       mod_flags &= ~static_cast<uint8_t>(f);
  179:       update_metric_flags();
  180:       return true;
  181:    }
  182: 
  183:    constexpr bool enable(mod_flag f)
  184:    {
  185:       if (mod_flags & static_cast<uint8_t>(f))
  186:          return false;
  187: 
  188:       mod_flags |= static_cast<uint8_t>(f);
  189:       update_metric_flags();
  190:       return true;
  191:    }
  192: 
  193:    std::string to_string() const
  194:    {
  195: #define ALGO_STR(algo_name)                                                                                            \
  196:    if (algo == algorithm::algo_name)                                                                                   \
  197:       str += #algo_name;
  198: #define MODF_STR(flag)                                                                                                 \
  199:    if (mod_flags & static_cast<uint8_t>(mod_flag::flag)) {                                                             \
  200:       str += #flag " ";                                                                                                \
  201:    }
  202: #define METRICF_STR(flag)                                                                                              \
  203:    if (metric_flags & static_cast<uint8_t>(metric_flag::flag)) {                                                       \
  204:       str += #flag " ";                                                                                                \
  205:    }
  206: 
  207:       std::string str = "Algorithm: ";
  208: 
  209:       ALGO_STR(BANDWIDTH);
  210:       ALGO_STR(PROFILED);
  211:       ALGO_STR(PROFILED_IMM);
  212:       ALGO_STR(PREFER_SYSMEM);
  213:       ALGO_STR(PREFER_GMEM);
  214: 
  215:       str += ", Mod Flags: 0x" + std::to_string(mod_flags) + " (";
  216:       MODF_STR(BIG_GMEM);
  217:       MODF_STR(TUNE_SMALL);
  218:       MODF_STR(PREEMPT_OPTIMIZE);
  219:       str += ")";
  220: 
  221:       str += ", Metric Flags: 0x" + std::to_string(metric_flags) + " (";
  222:       METRICF_STR(SAMPLES);
  223:       METRICF_STR(TS);
  224:       METRICF_STR(TS_TILE);
  225:       str += ")";
  226: 
  227:       return str;
  228: 
  229: #undef ALGO_STR
  230: #undef MODF_STR
  231: #undef METRICF_STR
  232:    }
  233: };
  234: 
  235: union PACKED tu_autotune::packed_config_t {
  236:    config_t config;
  237:    uint32_t bits = 0;
  238:    static_assert(sizeof(bits) >= sizeof(config));
  239:    static_assert(std::is_trivially_copyable<config_t>::value,
  240:                  "config_t must be trivially copyable to be automatically packed");
  241: 
  242:    constexpr packed_config_t(config_t p_config): bits(0)
  243:    {
  244:       config = p_config; /* Set after bits(0) to avoid UB in sizeof(bits) > sizeof(config) case.*/
  245:    }
  246: 
  247:    constexpr packed_config_t(uint32_t bits): bits(bits)
  248:    {
  249:    }
  250: };
  251: 
  252: tu_autotune::atomic_config_t::atomic_config_t(config_t initial): config_bits(packed_config_t { initial }.bits)
  253: {
  254: }
  255: 
  256: tu_autotune::config_t
  257: tu_autotune::atomic_config_t::load() const
  258: {
  259:    return config_t(packed_config_t { config_bits.load(std::memory_order_relaxed) }.config);
  260: }
  261: 
  262: bool
  263: tu_autotune::atomic_config_t::compare_and_store(config_t expected, config_t updated)
  264: {
  265:    uint32_t expected_bits = packed_config_t { expected }.bits;
  266:    return config_bits.compare_exchange_strong(expected_bits, packed_config_t { updated }.bits,
  267:                                               std::memory_order_acquire, std::memory_order_relaxed);
  268: }
  269: 
  270: tu_autotune::config_t
  271: tu_autotune::get_env_config()
  272: {
  273:    static std::once_flag once;
  274:    static config_t at_config;
  275:    std::call_once(once, [&] {
  276:       algorithm algo = algorithm::DEFAULT;
  277:       const char *algo_str = os_get_option("TU_AUTOTUNE_ALGO");
  278:       std::string_view algo_strv;
  279: 
  280:       if (algo_str)
  281:          algo_strv = algo_str;
  282:       else if (TU_DRIRC(device, perf.autotune_algo))
  283:          algo_strv = TU_DRIRC(device, perf.autotune_algo);
  284: 
  285:       if (!algo_strv.empty()) {
  286:          if (algo_strv == "bandwidth") {
  287:             algo = algorithm::BANDWIDTH;
  288:          } else if (algo_strv == "profiled") {
  289:             algo = algorithm::PROFILED;
  290:          } else if (algo_strv == "profiled_imm") {
  291:             algo = algorithm::PROFILED_IMM;
  292:          } else if (algo_strv == "prefer_sysmem") {
  293:             algo = algorithm::PREFER_SYSMEM;
  294:          } else if (algo_strv == "prefer_gmem") {
  295:             algo = algorithm::PREFER_GMEM;
  296:          } else {
  297:             mesa_logw("Unknown TU_AUTOTUNE_ALGO '%s', using default", algo_strv.data());
  298:          }
  299: 
  300:          if (TU_DEBUG(STARTUP))
  301:             mesa_logi("TU_AUTOTUNE_ALGO=%u (%s)", static_cast<uint8_t>(algo), algo_strv.data());
  302:       }
  303: 
  304:       /* Parse the flags from the environment variable. */
  305:       const char *flags_env_str = os_get_option("TU_AUTOTUNE_FLAGS");
  306:       uint32_t mod_flags = 0;
  307:       if (flags_env_str) {
  308:          static const struct debug_control tu_at_flags_control[] = {
  309:             { "big_gmem", static_cast<uint32_t>(mod_flag::BIG_GMEM) },
  310:             { "tune_small", static_cast<uint32_t>(mod_flag::TUNE_SMALL) },
  311:             { "preempt_optimize", static_cast<uint32_t>(mod_flag::PREEMPT_OPTIMIZE) },
  312:             { NULL, 0 }
  313:          };
  314: 
  315:          mod_flags = parse_debug_string(flags_env_str, tu_at_flags_control);
  316:          if (TU_DEBUG(STARTUP))
  317:             mesa_logi("TU_AUTOTUNE_FLAGS=0x%x (%s)", mod_flags, flags_env_str);
  318: 
  319:          if ((mod_flags & ~supported_mod_flags) != 0) {
  320:             mesa_logw("Unsupported TU_AUTOTUNE_FLAGS=0x%x, supported flags: 0x%x", mod_flags, supported_mod_flags);

==================== TU_CMD_BUFFER_WFI_SITES ====================
--- Match at line 153: tu_cs_emit_wfi(cs); ---
  147: 
  148:       tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(THREAD_MODE) | CP_COND_REG_EXEC_0_BV);
  149:       tu_wait_for_rb_done(cs, TU_ONCHIP_BV_U_TRACE_BARRIER, value);
  150:       tu_cond_exec_end(cs);
  151:    }
  152: 
  153:    tu_cs_emit_wfi(cs);
  154:    tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
  155:    u_trace_clone_append(begin, end, dst, cs, tu_copy_buffer);
  156: }
  157: 
  158: template <chip CHIP>
  159: static void
  160: tu_clone_trace(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
  161:                struct u_trace *dst, struct u_trace *src)
  162: {
  163:    tu_clone_trace_range<CHIP>(cmd, cs, dst, u_trace_begin_iterator(src), u_trace_end_iterator(src));
  164: }
  165: 
  166: template <chip CHIP>
  167: void
--- Match at line 435: tu_cs_emit_wfi(cs); ---
  429:    if (CHIP >= A7XX && (flushes & TU_CMD_FLAG_CCHE_INVALIDATE) &&
  430:        /* Invalidating UCHE seems to also invalidate CCHE */
  431:        !(flushes & TU_CMD_FLAG_CACHE_INVALIDATE)) {
  432:       /* CP_CCHE_INVALIDATE is just a plain register write underneath, so
  433:        * it needs WFI before it, in order to invalidate at the right point.
  434:        */
  435:       tu_cs_emit_wfi(cs);
  436:       tu_cs_emit_pkt7(cs, CP_CCHE_INVALIDATE, 0);
  437:    }
  438:    if (CHIP == A7XX && (flushes & TU_CMD_FLAG_RTU_INVALIDATE) &&
  439:        cmd_buffer->device->physical_device->info->props.has_rt_workaround)
  440:       tu_emit_rt_workaround<CHIP>(cmd_buffer, cs);
  441:    if (flushes & TU_CMD_FLAG_WAIT_MEM_WRITES)
  442:       tu_cs_emit_pkt7(cs, CP_WAIT_MEM_WRITES, 0);
  443:    if (emit_subpass_slice_fence) {
  444:       /* Emit the stronger flushes in sysmem mode. We need this from
  445:        * experimentation.
  446:        */
  447:       tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(RENDER_MODE) |
  448:                              CP_COND_REG_EXEC_0_SYSMEM);
  449:       if (emit_cache_invalidate_gmem)
--- Match at line 452: tu_cs_emit_wfi(cs); ---
  446:        */
  447:       tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(RENDER_MODE) |
  448:                              CP_COND_REG_EXEC_0_SYSMEM);
  449:       if (emit_cache_invalidate_gmem)
  450:          tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_CACHE_INVALIDATE);
  451:       if (emit_subpass_slice_wait)
  452:          tu_cs_emit_wfi(cs);
  453:       tu_cond_exec_end(cs);
  454: 
  455:       if (CHIP >= A8XX) {
  456:          tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_LABEL);
  457:          tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_SUBPASS_SLICE_FENCE);
  458:          tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_LABEL);
  459:       } else {
  460:          tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_SUBPASS_FENCE);
  461:       }
  462:    }
  463:    if (flushes & TU_CMD_FLAG_WAIT_FOR_IDLE)
  464:       tu_cs_emit_wfi(cs);
  465:    if (flushes & TU_CMD_FLAG_WAIT_FOR_ME)
  466:       tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
--- Match at line 464: tu_cs_emit_wfi(cs); ---
  458:          tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_LABEL);
  459:       } else {
  460:          tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_SUBPASS_FENCE);
  461:       }
  462:    }
  463:    if (flushes & TU_CMD_FLAG_WAIT_FOR_IDLE)
  464:       tu_cs_emit_wfi(cs);
  465:    if (flushes & TU_CMD_FLAG_WAIT_FOR_ME)
  466:       tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
  467: }
  468: 
  469: static void
  470: tu7_write_onchip_val(struct tu_cs *cs, enum tu_onchip_addr addr,
  471:                      uint32_t val)
  472: {
  473:    tu_cs_emit_pkt7(cs, CP_EVENT_WRITE7, 4);
  474:    tu_cs_emit(cs, CP_EVENT_WRITE7_0_WRITE_DST(EV_DST_ONCHIP) |
  475:                   CP_EVENT_WRITE7_0_WRITE_SRC(EV_WRITE_USER_32B) |
  476:                   CP_EVENT_WRITE7_0_EVENT(DUMMY_EVENT) |
  477:                   CP_EVENT_WRITE7_0_WRITE_ENABLED);
  478:    tu_cs_emit_qw(cs, addr);
--- Match at line 1906: tu_cs_emit_wfi(cs); ---
 1900:        * land. When loading FS params via UBOs, we also need to invalidate
 1901:        * UCHE because the FS param patchpoint is read through UCHE.
 1902:        */
 1903:       tu_cs_emit_pkt7(cs, CP_WAIT_MEM_WRITES, 0);
 1904:       if (cmd->device->compiler->info->props.load_shader_consts_via_preamble) {
 1905:          tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
 1906:          tu_cs_emit_wfi(cs);
 1907:       }
 1908:       tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
 1909:    } else if (cmd->device->physical_device->info->props.has_hw_bin_scaling) {
 1910:       tu_cs_emit_regs(cs, GRAS_BIN_FOVEAT(CHIP, 0));
 1911:       tu_cs_emit_regs(cs, RB_BIN_FOVEAT(CHIP, 0));
 1912:    }
 1913: }
 1914: 
 1915: template <chip CHIP>
 1916: static void
 1917: tu6_emit_sysmem_resolve(struct tu_cmd_buffer *cmd,
 1918:                         struct tu_cs *cs,
 1919:                         uint32_t layer_mask,
 1920:                         uint32_t a,
--- Match at line 1967: tu_cs_emit_wfi(cs); ---
 1961:       if (subpass->resolve_depth_stencil)
 1962:          tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_CLEAN_DEPTH);
 1963: 
 1964:       tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
 1965: 
 1966:       /* Wait for the flushes to land before using the 2D engine */
 1967:       tu_cs_emit_wfi(cs);
 1968: 
 1969:       for (unsigned i = 0; i < subpass->resolve_count; i++) {
 1970:          uint32_t a = subpass->resolve_attachments[i].attachment;
 1971:          if (a == VK_ATTACHMENT_UNUSED)
 1972:             continue;
 1973: 
 1974:          uint32_t gmem_a = tu_subpass_get_attachment_to_resolve(subpass, i);
 1975: 
 1976:          tu6_emit_sysmem_resolve<CHIP>(cmd, cs, subpass->multiview_mask, a, gmem_a);
 1977:       }
 1978:    }
 1979: }
 1980: 
 1981: template <chip CHIP>
--- Match at line 2014: tu_cs_emit_wfi(cs); ---
 2008:        * need to manually flush for that case.
 2009:        */
 2010:       tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_CLEAN_COLOR);
 2011:       tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
 2012: 
 2013:       /* Wait for the flushes to land before using the 2D engine */
 2014:       tu_cs_emit_wfi(cs);
 2015: 
 2016:       bool unresolve_ds = false;
 2017:       for (unsigned i = 0; i < subpass->unresolve_count; i++) {
 2018:          uint32_t a = subpass->unresolve_attachments[i].attachment;
 2019:          if (a == VK_ATTACHMENT_UNUSED)
 2020:             continue;
 2021: 
 2022:          if (vk_format_is_depth_or_stencil(cmd->state.pass->attachments[a].format))
 2023:             unresolve_ds = true;
 2024: 
 2025:          uint32_t gmem_a = tu_subpass_get_attachment_to_unresolve(subpass, i);
 2026: 
 2027:          tu6_emit_sysmem_unresolve<CHIP>(cmd, cs, subpass->multiview_mask, a, gmem_a);
 2028:       }
--- Match at line 2036: tu_cs_emit_wfi(cs); ---
 2030:       tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_CLEAN_COLOR);
 2031:       tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_INVALIDATE_COLOR);
 2032:       if (unresolve_ds) {
 2033:          tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_CLEAN_DEPTH);
 2034:          tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_INVALIDATE_DEPTH);
 2035:       }
 2036:       tu_cs_emit_wfi(cs);
 2037:    }
 2038: }
 2039: template <chip CHIP>
 2040: static void
 2041: tu6_emit_gmem_resolves(struct tu_cmd_buffer *cmd,
 2042:                        const struct tu_subpass *subpass,
 2043:                        struct tu_resolve_group *resolve_group,
 2044:                        struct tu_cs *cs)
 2045: {
 2046:    const struct tu_render_pass *pass = cmd->state.pass;
 2047:    const struct tu_framebuffer *fb = cmd->state.framebuffer;
 2048:    bool per_layer_render_area = cmd->state.per_layer_render_area;
 2049: 
 2050:    if (subpass->resolve_attachments) {
--- Match at line 2504: tu_cs_emit_wfi(cs); ---
 2498:       tu7_thread_control(cs, CP_SET_THREAD_BOTH);
 2499: 
 2500:       tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_INVALIDATE_COLOR);
 2501:       tu_emit_event_write<CHIP>(cmd, cs, FD_CCU_INVALIDATE_DEPTH);
 2502:       tu_emit_event_write<CHIP>(cmd, cs, FD_LRZ_INVALIDATE);
 2503:       tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
 2504:       tu_cs_emit_wfi(cs);
 2505:    }
 2506: 
 2507:    tu_cs_emit_regs(cs, SP_UPDATE_CNTL(CHIP,
 2508:          .vs_state = true,
 2509:          .hs_state = true,
 2510:          .ds_state = true,
 2511:          .gs_state = true,
 2512:          .fs_state = true,
 2513:          .cs_state = true,
 2514:          .cs_uav = true,
 2515:          .gfx_uav = true,
 2516:          .cs_shared_const = true,
 2517:          .gfx_shared_const = true,
 2518:          .cs_bindless = CHIP == A6XX ? 0x1f : 0xff,
--- Match at line 2523: tu_cs_emit_wfi(cs); ---
 2517:          .gfx_shared_const = true,
 2518:          .cs_bindless = CHIP == A6XX ? 0x1f : 0xff,
 2519:          .gfx_bindless = CHIP == A6XX ? 0x1f : 0xff,));
 2520:    if (CHIP >= A8XX)
 2521:       tu_emit_bindless_invalidate<CHIP>(cs, true, true);
 2522: 
 2523:    tu_cs_emit_wfi(cs);
 2524: 
 2525:    if (dev->dbg_cmdbuf_stomp_cs) {
 2526:       tu_cs_emit_call(cs, dev->dbg_cmdbuf_stomp_cs);
 2527:    }
 2528: 
 2529:    cmd->state.cache.pending_flush_bits &=
 2530:       ~(TU_CMD_FLAG_WAIT_FOR_IDLE | TU_CMD_FLAG_CACHE_INVALIDATE);
 2531: 
 2532:    tu6_init_static_regs<CHIP>(cmd->device, cs);
 2533:    tu_init_hw_rp<CHIP>(cs);
 2534: 
 2535:    emit_rb_ccu_cntl<CHIP>(cs, cmd->device, false);
 2536:    emit_vpc_attr_buf<CHIP>(cs, cmd->device, false);
 2537:    cmd->state.ccu_state = TU_CMD_CCU_SYSMEM;
--- Match at line 2785: tu_cs_emit_wfi(cs); ---
 2779:    tu_cs_emit_pkt7(cs, CP_SET_VISIBILITY_OVERRIDE, 1);
 2780:    tu_cs_emit(cs, 0x1);
 2781: 
 2782:    tu_cs_emit_pkt7(cs, CP_SET_MODE, 1);
 2783:    tu_cs_emit(cs, 0x1);
 2784: 
 2785:    tu_cs_emit_wfi(cs);
 2786: 
 2787:    tu_cs_emit_regs(cs,
 2788:                    A6XX_VFD_RENDER_MODE(.render_mode = BINNING_PASS));
 2789: 
 2790:    update_vsc_pipe<CHIP>(cmd, cs, phys_dev->info->num_vsc_pipes);
 2791: 
 2792:    tu_emit_event_write<CHIP>(cmd, cs, FD_VSC_BINNING_START);
 2793: 
 2794:    tu_cs_emit_regs(cs,
 2795:                    A6XX_RB_WINDOW_OFFSET(.x = 0, .y = 0));
 2796: 
 2797:    tu_cs_emit_regs(cs,
 2798:                    A6XX_TPL1_WINDOW_OFFSET(.x = 0, .y = 0));
 2799: 
--- Match at line 2851: tu_cs_emit_wfi(cs); ---
 2845:     * submitted are finished before reading the VSC regs (in
 2846:     * emit_vsc_overflow_test) or the VSC_DATA buffer directly (implicitly as
 2847:     * part of draws).
 2848:     */
 2849:    tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_CLEAN);
 2850: 
 2851:    tu_cs_emit_wfi(cs);
 2852: 
 2853:    tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
 2854: 
 2855:    emit_vsc_overflow_test(cmd, cs);
 2856: 
 2857:    tu_cs_emit_pkt7(cs, CP_SET_VISIBILITY_OVERRIDE, 1);
 2858:    tu_cs_emit(cs, 0x0);
 2859: 
 2860:    tu_cs_emit_pkt7(cs, CP_SET_MODE, 1);
 2861:    tu_cs_emit(cs, 0x0);
 2862: 
 2863:    cmd->device->autotune->end_binning(cs, rp_ctx);
 2864: }
 2865: 
--- Match at line 3877: tu_cs_emit_wfi(cs); ---
 3871:       tu_cs_emit(cs, 0x0);
 3872:    }
 3873: 
 3874:    tu_cs_emit_call(cs, &cmd->tile_store_cs);
 3875: 
 3876:    tu_clone_trace_range<CHIP>(cmd, cs, &cmd->trace, cmd->trace_renderpass_start, u_trace_end_iterator(&cmd->rp_trace));
 3877:    tu_cs_emit_wfi(cs);
 3878: 
 3879:    tu_set_render_mode<CHIP>(cs, {RM6_BIN_RENDER_END});
 3880: 
 3881:    tu_cs_sanity_check(cs);
 3882: 
 3883:    trace_end_draw_ib_gmem(&cmd->trace, &cmd->cs);
 3884: }
 3885: 
 3886: template <chip CHIP>
 3887: static void
 3888: tu6_tile_render_end(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
 3889:                     tu_autotune::rp_ctx_t rp_ctx)
 3890: {
 3891:    tu_cs_emit_call(cs, &cmd->draw_epilogue_cs);
--- Match at line 5407: tu_cs_emit_wfi(cs); ---
 5401:       cs->mem_to_reg(VPC_SO_BUFFER_OFFSET(CHIP, idx),
 5402:                      vk_buffer_address(&buf->vk, counter_buffer_offset),
 5403:                      { .cnt = 1, .wait_cache_flush = true });
 5404: 
 5405:       if (offset) {
 5406:          /* Without a WFI, CP_REG_RMW may read a stale value. */
 5407:          tu_cs_emit_wfi(cs);
 5408: 
 5409:          cs->rmw(VPC_SO_BUFFER_OFFSET(CHIP, idx), {
 5410:             .src1_add = true,
 5411:             .src0 = 0xffffffff,
 5412:             .src1 = offset,
 5413:          });
 5414:       }
 5415:    }
 5416: 
 5417:    tu_cond_exec_end(cs);
 5418: }
 5419: TU_GENX(tu_CmdBeginTransformFeedbackEXT);
 5420: 
 5421: template <chip CHIP>
--- Match at line 7369: tu_CmdBeginRendering(VkCommandBuffer commandBuffer, ---
 7363:       cache->flush_bits |= TU_CMD_FLAG_WAIT_FOR_IDLE;
 7364:    }
 7365: }
 7366: 
 7367: template <chip CHIP>
 7368: VKAPI_ATTR void VKAPI_CALL
 7369: tu_CmdBeginRendering(VkCommandBuffer commandBuffer,
 7370:                      const VkRenderingInfo *pRenderingInfo)
 7371: {
 7372:    VK_FROM_HANDLE(tu_cmd_buffer, cmd, commandBuffer);
 7373: 
 7374:    tu_setup_dynamic_render_pass(cmd, pRenderingInfo);
 7375:    tu_setup_dynamic_framebuffer(cmd, pRenderingInfo);
 7376: 
 7377:    cmd->state.pass = &cmd->dynamic_pass;
 7378:    cmd->state.subpass = &cmd->dynamic_subpasses[0];
 7379:    cmd->state.framebuffer = &cmd->dynamic_framebuffer;
 7380:    tu_set_render_area(cmd, &pRenderingInfo->renderArea,
 7381:                       pRenderingInfo->pNext);
 7382:    cmd->state.fdm_per_layer =
 7383:       pRenderingInfo->flags & VK_RENDERING_PER_LAYER_FRAGMENT_DENSITY_BIT_VALVE;
--- Match at line 7581: /* Even resuming vkCmdBeginRendering resets RT and input attachment locations, so we have to re-emit them. */ ---
 7575:    if (!cmd->patchpoints_ctx)
 7576:       cmd->patchpoints_ctx = ralloc_context(NULL);
 7577: 
 7578:    if (!resuming) {
 7579:       tu_emit_subpass_begin<CHIP>(cmd);
 7580:    } else {
 7581:       /* Even resuming vkCmdBeginRendering resets RT and input attachment locations, so we have to re-emit them. */
 7582:       tu_emit_rendering_attachment_locations<CHIP>(cmd);
 7583:       tu_set_input_attachments<CHIP>(cmd, cmd->state.subpass);
 7584:    }
 7585: 
 7586:    if (suspending && !resuming) {
 7587:       /* entering a chain */
 7588:       switch (cmd->state.suspend_resume) {
 7589:       case SR_NONE:
 7590:          cmd->state.suspend_resume = SR_IN_CHAIN;
 7591:          break;
 7592:       case SR_AFTER_PRE_CHAIN:
 7593:          cmd->state.suspend_resume = SR_IN_CHAIN_AFTER_PRE_CHAIN;
 7594:          break;
 7595:       case SR_IN_PRE_CHAIN:
--- Match at line 7606: TU_GENX(tu_CmdBeginRendering); ---
 7600:       }
 7601:    }
 7602: 
 7603:    if (resuming && cmd->state.suspend_resume == SR_NONE)
 7604:       cmd->state.suspend_resume = SR_IN_PRE_CHAIN;
 7605: }
 7606: TU_GENX(tu_CmdBeginRendering);
 7607: 
 7608: template <chip CHIP>
 7609: VKAPI_ATTR void VKAPI_CALL
 7610: tu_CmdSetRenderingAttachmentLocationsKHR(
 7611:    VkCommandBuffer commandBuffer,
 7612:    const VkRenderingAttachmentLocationInfoKHR *pLocationInfo)
 7613: {
 7614:    VK_FROM_HANDLE(tu_cmd_buffer, cmd, commandBuffer);
 7615: 
 7616:    vk_common_CmdSetRenderingAttachmentLocationsKHR(commandBuffer, pLocationInfo);
 7617: 
 7618:    tu_emit_rendering_attachment_locations<CHIP>(cmd);
 7619: }
 7620: TU_GENX(tu_CmdSetRenderingAttachmentLocationsKHR);
--- Match at line 10023: tu_cs_emit_wfi(cs); ---
10017:           * However, CP_LOAD_STATE.EXT_SRC_ADDR needs 16 byte alignment.
10018:           */
10019: 
10020:          uint64_t indirect_iova = info->indirect;
10021: 
10022:          /* Wait for any previous uses to finish. */
10023:          tu_cs_emit_wfi(cs);
10024: 
10025:          for (uint32_t i = 0; i < 3; i++) {
10026:             tu_cs_emit_pkt7(cs, CP_MEM_TO_MEM, 5);
10027:             tu_cs_emit(cs, 0);
10028:             tu_cs_emit_qw(cs, global_iova_arr(cmd, cs_indirect_xyz, i));
10029:             tu_cs_emit_qw(cs, indirect_iova + i * sizeof(uint32_t));
10030:          }
10031: 
10032:          /* Fill out IR3_DP_CS_SUBGROUP_SIZE and IR3_DP_SUBGROUP_ID_SHIFT for
10033:           * indirect dispatch.
10034:           */
10035:          if (info->indirect && num_consts > IR3_DP_CS(base_group_x)) {
10036:             uint32_t indirect_driver_params[8] = {
10037:                0, 0, 0, subgroup_size,
--- Match at line 10052: tu_cs_emit_wfi(cs); ---
10046:                tu_cs_emit(cs, indirect_driver_params[i]);
10047:             }
10048:          }
10049: 
10050:          tu_cs_emit_pkt7(cs, CP_WAIT_MEM_WRITES, 0);
10051:          tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
10052:          tu_cs_emit_wfi(cs);
10053: 
10054:          iova = global_iova(cmd, cs_indirect_xyz[0]);
10055:       }
10056: 
10057:       tu_cs_emit_pkt7(cs, tu6_stage2opcode(type), 5);
10058:       tu_cs_emit(cs, CP_LOAD_STATE6_0_DST_OFF(const_state->driver_params_ubo.idx) |
10059:                CP_LOAD_STATE6_0_STATE_TYPE(ST6_UBO) |
10060:                CP_LOAD_STATE6_0_STATE_SRC(SS6_DIRECT) |
10061:                CP_LOAD_STATE6_0_STATE_BLOCK(tu6_stage2shadersb(type)) |
10062:                CP_LOAD_STATE6_0_NUM_UNIT(1));
10063:       tu_cs_emit(cs, CP_LOAD_STATE6_1_EXT_SRC_ADDR(0));
10064:       tu_cs_emit(cs, CP_LOAD_STATE6_2_EXT_SRC_ADDR_HI(0));
10065:       int size_vec4s = DIV_ROUND_UP(num_consts, 4);
10066:       tu_cs_emit_qw(cs, iova | (static_cast<uint64_t>(A6XX_UBO_1_SIZE(size_vec4s)) << 32));
--- Match at line 10109: tu_cs_emit_wfi(cs); ---
10103:       } else {
10104:          /* Vulkan guarantees only 4 byte alignment for indirect_offset.
10105:           * However, CP_LOAD_STATE.EXT_SRC_ADDR needs 16 byte alignment.
10106:           */
10107: 
10108:          /* Wait for any previous uses to finish. */
10109:          tu_cs_emit_wfi(cs);
10110: 
10111:          for (uint32_t i = 0; i < 3; i++) {
10112:             tu_cs_emit_pkt7(cs, CP_MEM_TO_MEM, 5);
10113:             tu_cs_emit(cs, 0);
10114:             tu_cs_emit_qw(cs, global_iova_arr(cmd, cs_indirect_xyz, i));
10115:             tu_cs_emit_qw(cs, info->indirect + i * 4);
10116:          }
10117: 
10118:          tu_cs_emit_pkt7(cs, CP_WAIT_MEM_WRITES, 0);
10119:          tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
10120:          tu_cs_emit_wfi(cs);
10121: 
10122:          tu_cs_emit_pkt7(cs, tu6_stage2opcode(type), 3);
10123:          tu_cs_emit(cs, CP_LOAD_STATE6_0_DST_OFF(offset) |
--- Match at line 10120: tu_cs_emit_wfi(cs); ---
10114:             tu_cs_emit_qw(cs, global_iova_arr(cmd, cs_indirect_xyz, i));
10115:             tu_cs_emit_qw(cs, info->indirect + i * 4);
10116:          }
10117: 
10118:          tu_cs_emit_pkt7(cs, CP_WAIT_MEM_WRITES, 0);
10119:          tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
10120:          tu_cs_emit_wfi(cs);
10121: 
10122:          tu_cs_emit_pkt7(cs, tu6_stage2opcode(type), 3);
10123:          tu_cs_emit(cs, CP_LOAD_STATE6_0_DST_OFF(offset) |
10124:                      CP_LOAD_STATE6_0_STATE_TYPE(ST6_CONSTANTS) |
10125:                      CP_LOAD_STATE6_0_STATE_SRC(SS6_INDIRECT) |
10126:                      CP_LOAD_STATE6_0_STATE_BLOCK(tu6_stage2shadersb(type)) |
10127:                      CP_LOAD_STATE6_0_NUM_UNIT(1));
10128:          tu_cs_emit_qw(cs, global_iova(cmd, cs_indirect_xyz[0]));
10129:       }
10130: 
10131:       /* Fill out IR3_DP_CS_SUBGROUP_SIZE and IR3_DP_SUBGROUP_ID_SHIFT for
10132:        * indirect dispatch.
10133:        */
10134:       if (info->indirect && num_consts > IR3_DP_CS(base_group_x)) {
--- Match at line 10269: tu_cs_emit_wfi(cs); ---
10263:           * we don't want, so manually wait for the CP_MEM_TO_REG write to land
10264:           * and then skip waiting below with SKIP_WAIT_FOR_ME.
10265:           *
10266:           * On A8XX, the RMWs may still read a stale SP_CS_NDRANGE_1 without a WFI.
10267:           */
10268:          if (CHIP >= A8XX)
10269:             tu_cs_emit_wfi(cs);
10270:          tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
10271: 
10272:          /* scratch0 = ((scratch0 & CS_NDRANGE_1) + -1
10273:           *          = ((~0 & CS_NDRANGE_1) + -1
10274:           *          =  CS_NDRANGE_1 - 1
10275:           */
10276:          cs->rmw(tu_scratch(tu_dispatch.scratch0), {
10277:             .skip_wfm = true,
10278:             .src1_add = true,
10279:             .src0 = SP_CS_NDRANGE_1(CHIP),
10280:             .src1 = -1,
10281:          });
10282: 
10283:          /* scratch0 = ((scratch0 & (local_size - 1)) rot 2
--- Match at line 10552: tu_cs_emit_wfi(cs); ---
10546:  * All of them access the data through UCHE, so no cache maintenance is needed.
10547:  */
10548: template <chip CHIP>
10549: static void
10550: tu_mesh_emit_shader_barrier(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
10551: {
10552:    tu_cs_emit_wfi(cs);
10553: }
10554: 
10555: /* Makes the writes of the setup shader visible to the CP, which reads the
10556:  * chunk arguments (dispatch size, enable flag, draw arguments) from memory.
10557:  * The cleaned lines stay valid for the shaders reading the table afterwards.
10558:  */
10559: template <chip CHIP>
10560: static void
10561: tu_mesh_emit_cp_read_barrier(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
10562: {
10563:    tu_cs_emit_wfi(cs);
10564:    tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_CLEAN);
10565:    tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
10566: }
--- Match at line 10563: tu_cs_emit_wfi(cs); ---
10557:  * The cleaned lines stay valid for the shaders reading the table afterwards.
10558:  */
10559: template <chip CHIP>
10560: static void
10561: tu_mesh_emit_cp_read_barrier(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
10562: {
10563:    tu_cs_emit_wfi(cs);
10564:    tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_CLEAN);
10565:    tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);
10566: }
10567: 
10568: /* Makes CP memory writes visible to shaders. */
10569: template <chip CHIP>
10570: static void
10571: tu_mesh_emit_cp_barrier(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
10572: {
10573:    tu_cs_emit_pkt7(cs, CP_WAIT_MEM_WRITES, 0);
10574:    tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
10575:    tu_cs_emit_wfi(cs);
10576: }
10577: 
--- Match at line 10575: tu_cs_emit_wfi(cs); ---
10569: template <chip CHIP>
10570: static void
10571: tu_mesh_emit_cp_barrier(struct tu_cmd_buffer *cmd, struct tu_cs *cs)
10572: {
10573:    tu_cs_emit_pkt7(cs, CP_WAIT_MEM_WRITES, 0);
10574:    tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_INVALIDATE);
10575:    tu_cs_emit_wfi(cs);
10576: }
10577: 
10578: /* Loads one of the compute shaders of a mesh draw. Dispatches can't use draw
10579:  * states and the draw CS can't call another IB, so the shader state is copied
10580:  * inline.
10581:  */
10582: template <chip CHIP>
10583: static void
10584: tu_mesh_emit_program(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
10585:                      const struct tu_shader *shader)
10586: {
10587:    const uint32_t *state = (const uint32_t *)
10588:       ((const char *) shader->bo.bo->map +
10589:        (shader->state.iova - shader->bo.bo->iova));
--- Match at line 10843: tu_cs_emit_wfi(cs); ---
10837:       tu_cs_emit(cs, tu_draw_initiator(cmd, DI_SRC_SEL_AUTO_INDEX));
10838:       tu_cs_emit(cs, 1);
10839:       tu_cs_emit(cs, groups * ms->mesh.max_primitives * ms->mesh.verts_per_prim);
10840:    }
10841: 
10842:    /* The next chunk reuses the records this draw reads. */
10843:    tu_cs_emit_wfi(cs);
10844: }
10845: 
10846: /* Runs the mesh shader over the mesh table: count workgroups when known on
10847:  * the CPU, otherwise the chunks enabled by the setup shader.
10848:  */
10849: template <chip CHIP>
10850: static void
10851: tu_mesh_emit_ms_chunks(struct tu_cmd_buffer *cmd, struct tu_cs *cs,
10852:                        bool gpu_driven, uint32_t count)
10853: {
10854:    const struct tu_shader *ms = cmd->state.shaders[MESA_SHADER_MESH];
10855:    uint32_t chunk = ms->mesh.chunk_workgroups;
10856: 
10857:    tu_mesh_emit_program<CHIP>(cmd, cs, ms);
```
