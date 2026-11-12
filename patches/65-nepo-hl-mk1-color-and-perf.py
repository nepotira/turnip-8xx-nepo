#!/usr/bin/env python3
"""65-nepo-hl-mk1-color-and-perf.py: Hogwarts Legacy & Mortal Kombat 1 Color Precision + Performance Pack for Adreno 8xx.

Fixes applied idempotently on Mesa source tree:
1. [PERF+COLOR] Sample Shading Gate in tu_pipeline.cc: only force per-sample interpolation when minSampleShading > 0.5f or FS uses sample shading.
2. [COLOR+PERF] Mutable Format UBWC & BGRA8 Tiled Fast-Path in tu_image.cc: keeps UE4/Switch R11G11B10, RGBA8, BGRA8, RGB10A2 and RGBA16F render targets in Tiled+UBWC mode.
3. [COLOR] R11G11B10_FLOAT Half-Precision fix in tu_clear_blit.cc: sets .half_precision when dst_format OR src_format is PIPE_FORMAT_R11G11B10_FLOAT.
4. [COLOR] A8XX Category-4 (SFU: log2, exp2, rsq, sqrt) repeat latency guard in ir3_legalize.c: prevents broken sRGB gamma and ACES tonemapping curves.
5. [PERF] A8XX UBO Push Range Coalescing in freedreno_devices.py / ir3: enables coalesce_ubo_push_ranges across Adreno 825 (0x44030000) and A8xx family.
6. [STABILITY] UE4 Split/Resumed RenderPass Flush in tu_cmd_buffer.cc: ensures pending cache flushes are preserved across suspending/resuming dynamic render passes.
"""

import pathlib
import re
import sys

NAME = "65-nepo-hl-mk1-color-and-perf"


def fix_1_sample_shading_gate(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/vulkan/tu_pipeline.cc"
    if not p.exists():
        return "ERROR: tu_pipeline.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_65_SAMPLE_GATE */" in txt:
        return "ALREADY"

    old = (
        "      keys[MESA_SHADER_FRAGMENT].force_sample_interp =\n"
        "         !builder->rasterizer_discard && msaa_info && msaa_info->sampleShadingEnable;"
    )
    new = (
        "      /* NEPO_65_SAMPLE_GATE */\n"
        "      keys[MESA_SHADER_FRAGMENT].force_sample_interp =\n"
        "         !builder->rasterizer_discard && msaa_info && msaa_info->sampleShadingEnable &&\n"
        "         (msaa_info->minSampleShading > 0.5f ||\n"
        "          (nir[MESA_SHADER_FRAGMENT] &&\n"
        "           nir[MESA_SHADER_FRAGMENT]->info.fs.uses_sample_shading));"
    )
    if old in txt:
        p.write_text(txt.replace(old, new, 1), encoding="utf-8")
        return "OK"
    return "SKIP"


def fix_2_mutable_format_ubwc_and_bgra_fastpath(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/vulkan/tu_image.cc"
    if not p.exists():
        return "ERROR: tu_image.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_65_MUTABLE_UBWC */" in txt:
        return "ALREADY"

    # Parte A: BGRA8 HIC Tiled fast-path (linha ~576)
    old_hic = (
        "   if ((pCreateInfo->usage & VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT) &&\n"
        "       fd6_color_swap(vk_format_to_pipe_format(image->vk.format),\n"
        "                                               TILE6_LINEAR, false) != WZYX)\n"
        "      force_linear_tile = true;"
    )
    new_hic = (
        "   /* NEPO_65_BGRA_TILED_FASTPATH: Allow BGRA8 UNORM/SRGB to stay tiled */\n"
        "   if ((pCreateInfo->usage & VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT) &&\n"
        "       image->vk.format != VK_FORMAT_B8G8R8A8_UNORM &&\n"
        "       image->vk.format != VK_FORMAT_B8G8R8A8_SRGB &&\n"
        "       fd6_color_swap(vk_format_to_pipe_format(image->vk.format),\n"
        "                                               TILE6_LINEAR, false) != WZYX)\n"
        "      force_linear_tile = true;"
    )
    if old_hic in txt:
        txt = txt.replace(old_hic, new_hic, 1)

    # Parte B: Mutable format UBWC preservation (linha ~612)
    old_mut = "         bool mutable_ubwc_fc = device->physical_device->info->props.ubwc_all_formats_compatible;"
    new_mut = (
        "         /* NEPO_65_MUTABLE_UBWC: Keep UE4/Switch R11G11B10, RGBA8, BGRA8, RGB10A2 and RGBA16F\n"
        "          * mutable render targets in Tiled+UBWC mode to preserve color LUT & SceneColor precision.\n"
        "          */\n"
        "         bool mutable_ubwc_fc = device->physical_device->info->props.ubwc_all_formats_compatible ||\n"
        "            ((!fmt_list || fmt_list->viewFormatCount <= 2) &&\n"
        "             (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||\n"
        "              image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||\n"
        "              image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||\n"
        "              image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||\n"
        "              image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||\n"
        "              image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||\n"
        "              image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));"
    )
    if old_mut in txt:
        txt = txt.replace(old_mut, new_mut, 1)
        p.write_text(txt, encoding="utf-8")
        return "OK"
    return "ERROR: anchor not found in tu_image.cc"


def fix_3_r11g11b10_half_precision(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/vulkan/tu_clear_blit.cc"
    if not p.exists():
        return "ERROR: tu_clear_blit.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_65_R11G11B10_PREC */" in txt:
        return "ALREADY"

    old = "         .half_precision = util_format_is_float16(src_format) || src_format == PIPE_FORMAT_R11G11B10_FLOAT,"
    new = (
        "         /* NEPO_65_R11G11B10_PREC */\n"
        "         .half_precision = util_format_is_float16(src_format) ||\n"
        "                           src_format == PIPE_FORMAT_R11G11B10_FLOAT ||\n"
        "                           dst_format == PIPE_FORMAT_R11G11B10_FLOAT,"
    )
    if old in txt:
        p.write_text(txt.replace(old, new, 1), encoding="utf-8")
        return "OK"
    return "ERROR: anchor not found in tu_clear_blit.cc"


def fix_4_cat4_sfu_repeat_delay(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/ir3/ir3_legalize.c"
    if not p.exists():
        return "ERROR: ir3_legalize.c not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_65_CAT4_SFU_RPT */" in txt:
        return "ALREADY"

    old = "         if (instr->repeat && !(dst->flags & IR3_REG_RELATIV))\n            dst_cycle++;"
    new = (
        "         /* NEPO_65_CAT4_SFU_RPT: Ensure full SFU (cat4) latency on A8xx repeated instructions */\n"
        "         if (instr->repeat && !(dst->flags & IR3_REG_RELATIV))\n"
        "            dst_cycle += (opc_cat(instr->opc) == 4 && compiler->gen >= 8) ? 2 : 1;"
    )
    if old in txt:
        p.write_text(txt.replace(old, new, 1), encoding="utf-8")
        return "OK"
    return "ERROR: anchor not found in ir3_legalize.c"


def fix_5_ubo_push_range_coalescing_a8xx(mesa_root: pathlib.Path) -> str:
    """Enable coalesce_ubo_push_ranges for A8XX (including A825/A829) in freedreno_devices.py or ir3_compiler.c."""
    dev_py = mesa_root / "src/freedreno/common/freedreno_devices.py"
    ir3_c = mesa_root / "src/freedreno/ir3/ir3_compiler.c"

    # 1. Check freedreno_devices.py (where modern Mesa defines coalesce_ubo_push_ranges as a GPUProp)
    if dev_py.exists():
        dtxt = dev_py.read_text(encoding="utf-8")
        if "# NEPO_65_UBO_COALESCE" in dtxt:
            return "ALREADY"
        if "coalesce_ubo_push_ranges" in dtxt:
            # Enable coalesce_ubo_push_ranges = True in a8xx_base if not already there
            anchor = "cube_coord_hang_quirk = True,"
            if anchor in dtxt and "coalesce_ubo_push_ranges = True," not in dtxt[dtxt.find("a8xx_base"):dtxt.find("a8xx_base") + 900]:
                dtxt = dtxt.replace(
                    anchor,
                    anchor + "\n        # NEPO_65_UBO_COALESCE\n        coalesce_ubo_push_ranges = True,",
                    1,
                )
                dev_py.write_text(dtxt, encoding="utf-8")
                return "OK(freedreno_devices.py)"

    # 2. Also ensure ir3_compiler.c enables it for A825/A8xx if compiler->coalesce_ubo_push_ranges exists
    if ir3_c.exists():
        ctxt = ir3_c.read_text(encoding="utf-8")
        if "/* NEPO_65_UBO_COALESCE */" in ctxt:
            return "ALREADY"
        m = re.search(r"compiler->coalesce_ubo_push_ranges\s*=\s*[^;]+;", ctxt)
        if m:
            rep = (
                "/* NEPO_65_UBO_COALESCE */\n"
                "   compiler->coalesce_ubo_push_ranges = (compiler->gen >= 8) || "
                + m.group(0).split("=", 1)[1].strip()
            )
            ctxt = ctxt[:m.start()] + rep + ctxt[m.end():]
            ir3_c.write_text(ctxt, encoding="utf-8")
            return "OK(ir3_compiler.c)"
        # Fallback: inject at end of ir3_compiler_create if field exists in ir3_compiler.h
        ir3_h = mesa_root / "src/freedreno/ir3/ir3_compiler.h"
        if ir3_h.exists() and "coalesce_ubo_push_ranges" in ir3_h.read_text(encoding="utf-8"):
            anchor2 = "compiler->has_preamble ="
            if anchor2 in ctxt:
                ctxt = ctxt.replace(
                    anchor2,
                    "/* NEPO_65_UBO_COALESCE */ compiler->coalesce_ubo_push_ranges = (compiler->gen >= 8);\n   " + anchor2,
                    1,
                )
                ir3_c.write_text(ctxt, encoding="utf-8")
                return "OK(ir3_compiler.c injected)"
    return "SKIP"


def fix_6_split_renderpass_flush(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/vulkan/tu_cmd_buffer.cc"
    if not p.exists():
        return "ERROR: tu_cmd_buffer.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_65_RESUMING_FLUSH */" in txt:
        return "ALREADY"

    old = (
        "   bool resuming = pRenderingInfo->flags & VK_RENDERING_RESUMING_BIT;\n"
        "   bool suspending = pRenderingInfo->flags & VK_RENDERING_SUSPENDING_BIT;"
    )
    new = (
        "   /* NEPO_65_RESUMING_FLUSH: Ensure compute-to-indirect/render barriers flush across split UE4 passes */\n"
        "   bool resuming = pRenderingInfo->flags & VK_RENDERING_RESUMING_BIT;\n"
        "   bool suspending = pRenderingInfo->flags & VK_RENDERING_SUSPENDING_BIT;\n"
        "   if (resuming) {\n"
        "      cmd->state.cache.pending_flush_bits |=\n"
        "         TU_CMD_FLAG_WAIT_FOR_IDLE | TU_CMD_FLAG_CACHE_INVALIDATE;\n"
        "   }"
    )
    if old in txt:
        p.write_text(txt.replace(old, new, 1), encoding="utf-8")
        return "OK"
    return "SKIP"


def main() -> int:
    mesa_root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd()
    r1 = fix_1_sample_shading_gate(mesa_root)
    r2 = fix_2_mutable_format_ubwc_and_bgra_fastpath(mesa_root)
    r3 = fix_3_r11g11b10_half_precision(mesa_root)
    r4 = fix_4_cat4_sfu_repeat_delay(mesa_root)
    r5 = fix_5_ubo_push_range_coalescing_a8xx(mesa_root)
    r6 = fix_6_split_renderpass_flush(mesa_root)

    results = (r1, r2, r3, r4, r5, r6)
    summary = f"sample_gate={r1} mutable_ubwc={r2} r11g11b10={r3} cat4_sfu={r4} ubo_coalesce={r5} rp_flush={r6}"
    if any(r.startswith("ERROR") for r in results):
        print(f"{NAME}: ERROR ({summary})", file=sys.stderr)
        return 1
    if all(r == "ALREADY" for r in results):
        print(f"{NAME}: already applied ({summary})")
        return 0
    print(f"{NAME}: applied ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
