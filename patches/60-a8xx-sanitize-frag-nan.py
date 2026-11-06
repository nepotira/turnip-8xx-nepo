#!/usr/bin/env python3
"""A8XX: Sanitize fragment and compute shader outputs against NaNs, Infs and bloom blowouts.

When textures with uninitialized memory or out-of-bounds sampling are decoded
in Switch emulators (e.g. Nyushu/Eden/Citron without custom SIMD texture unswizzling),
sampling produces NaNs and Infs. In HDR fog, bloom downsamples, and tone-mapping passes
(e.g. Super Mario Odyssey), these NaNs propagate and saturate to pure white on Adreno 8xx,
creating whitish artifacts ("elementos esbranquiçados").

This patch inserts an IR3/NIR output sanitization pass in ir3_finalize_nir:
- Handles fragment shader color attachment outputs (nir_intrinsic_store_output)
- Handles compute shader and fragment shader image stores (image_store, bindless_image_store, image_deref_store)
- Replaces NaNs with 0.0 using nir_bcsel(nir_fisnan(src), 0.0, src)
- Clamps infinite values to finite fp16/fp32 bounds using nir_fclamp
- Leaves integer/uint render targets completely untouched

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "60-a8xx-sanitize-frag-nan.py"
TARGET = "src/freedreno/ir3/ir3_nir.c"
MARKER = "ir3_nir_sanitize_outputs"

FUNC_CODE = """
/* Sanitize fragment and compute shader outputs: replace NaN with 0.0 and clamp to finite range
 * to prevent bloom blowouts and whitish artifacts caused by out-of-bounds or
 * uninitialized texture samples (especially in emulators like Switch/Nyushu/Eden).
 */
static bool
ir3_nir_sanitize_outputs_cb(struct nir_builder *b, nir_intrinsic_instr *intr,
                            void *_data)
{
   nir_def *src = NULL;
   unsigned src_idx = 0;

   if (intr->intrinsic == nir_intrinsic_store_output) {
      nir_io_semantics sem = nir_intrinsic_io_semantics(intr);
      if (sem.location < FRAG_RESULT_DATA0 && sem.location != FRAG_RESULT_COLOR)
         return false;
      src = intr->src[0].ssa;
      src_idx = 0;
   } else if (intr->intrinsic == nir_intrinsic_image_store ||
              intr->intrinsic == nir_intrinsic_bindless_image_store ||
              intr->intrinsic == nir_intrinsic_image_deref_store) {
      src = intr->src[3].ssa;
      src_idx = 3;
   } else {
      return false;
   }

   if (!src)
      return false;

   unsigned bit_size = src->bit_size;
   if (bit_size != 16 && bit_size != 32)
      return false;

   if (intr->intrinsic == nir_intrinsic_store_output && nir_intrinsic_has_src_type(intr)) {
      nir_alu_type type = nir_intrinsic_src_type(intr);
      if (nir_alu_type_get_base_type(type) != nir_type_float &&
          nir_alu_type_get_base_type(type) != nir_type_invalid)
         return false;
   }

   b->cursor = nir_before_instr(&intr->instr);

   nir_def *zero = nir_imm_zero(b, src->num_components, bit_size);
   nir_def *max_val = nir_imm_floatN_t(b, bit_size == 16 ? 65504.0 : FLT_MAX, bit_size);

   nir_def *is_nan = nir_fisnan(b, src);
   nir_def *clean = nir_bcsel(b, is_nan, zero, src);
   clean = nir_fclamp(b, clean, nir_fneg(b, max_val), max_val);

   nir_src_rewrite(&intr->src[src_idx], clean);
   return true;
}

static bool
ir3_nir_sanitize_outputs(nir_shader *shader)
{
   if (shader->info.stage != MESA_SHADER_FRAGMENT &&
       shader->info.stage != MESA_SHADER_COMPUTE)
      return false;

   return nir_shader_intrinsics_pass(shader, ir3_nir_sanitize_outputs_cb,
                                     nir_metadata_control_flow, NULL);
}
"""

CALL_CODE = """
   if (s->info.stage == MESA_SHADER_FRAGMENT || s->info.stage == MESA_SHADER_COMPUTE)
      NIR_PASS(_, s, ir3_nir_sanitize_outputs);
"""


def main():
    try:
        content = open(TARGET, "r", encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
        return 0

    if MARKER in content:
        print(f"{NAME}: already applied ({MARKER} present)")
        return 0

    # 1. Insert helper function before ir3_finalize_nir
    fn_anchor = "void\nir3_finalize_nir("
    if fn_anchor not in content:
        print(f"{NAME}: WARNING anchor '{fn_anchor}' not found in {TARGET}; skipped")
        return 0

    content = content.replace(fn_anchor, FUNC_CODE.strip() + "\n\n" + fn_anchor, 1)

    # 2. Insert call inside ir3_finalize_nir
    call_anchor = "   if (compiler->info->props.cube_coord_hang_quirk)\n      NIR_PASS(_, s, ir3_nir_lower_cube_coord);\n"
    if call_anchor in content:
        content = content.replace(call_anchor, call_anchor + CALL_CODE, 1)
    else:
        # Fallback anchor if cube_coord_hang_quirk is absent
        fallback_anchor = "   NIR_PASS(_, s, ir3_nir_min_lod_workaround);\n"
        if fallback_anchor in content:
            content = content.replace(fallback_anchor, fallback_anchor + CALL_CODE, 1)
        else:
            print(f"{NAME}: WARNING call anchor not found in ir3_finalize_nir; skipped")
            return 0

    try:
        with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    except OSError as e:
        print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
        return 1

    print(f"{NAME}: applied (fragment and compute output NaN/Inf sanitization enabled in ir3_nir.c)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
