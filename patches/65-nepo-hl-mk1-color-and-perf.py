#!/usr/bin/env python3
"""65-nepo-hl-mk1-color-and-perf.py: Hogwarts Legacy & Mortal Kombat 1 Color Precision + Performance Pack for Adreno 8xx.

Fixes applied idempotently on Mesa source tree:
1. [PERF+COLOR] Sample Shading Gate in tu_pipeline.cc (line ~1980): only force per-sample interpolation when minSampleShading > 0.5f or FS actually uses sample shading, avoiding 50% FPS loss and MSAA resolve corruption in MK1/HL.
2. [COLOR+PERF] Mutable Format UBWC & Tiling preservation in tu_image.cc (line ~612): allows game-internal VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT render targets (UE4 SceneColor R11G11B10, 3D LUTs, RGBA8/BGRA8/sRGB swaps) to stay Tiled + UBWC.
3. [COLOR] R11G11B10_FLOAT Half-Precision fix in tu_clear_blit.cc (line ~760): ensures SP_A2D_OUTPUT_INFO sets .half_precision when dst_format OR src_format is PIPE_FORMAT_R11G11B10_FLOAT, eliminating color banding and blown-out HDR gradients in UE4.
4. [COLOR] A8XX Category-4 (SFU: log2, exp2, rsq, sqrt) repeat (rptN) guard in ir3_legalize.c: prevents broken sRGB gamma and ACES tonemapping curves on Adreno 8xx.
"""

import pathlib
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


def fix_2_mutable_format_ubwc(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/vulkan/tu_image.cc"
    if not p.exists():
        return "ERROR: tu_image.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_65_MUTABLE_UBWC */" in txt:
        return "ALREADY"

    old = "         bool mutable_ubwc_fc = device->physical_device->info->props.ubwc_all_formats_compatible;"
    new = (
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
    if old in txt:
        p.write_text(txt.replace(old, new, 1), encoding="utf-8")
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


def main() -> int:
    mesa_root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd()
    r1 = fix_1_sample_shading_gate(mesa_root)
    r2 = fix_2_mutable_format_ubwc(mesa_root)
    r3 = fix_3_r11g11b10_half_precision(mesa_root)
    r4 = fix_4_cat4_sfu_repeat_delay(mesa_root)

    results = (r1, r2, r3, r4)
    summary = f"sample_gate={r1} mutable_ubwc={r2} r11g11b10={r3} cat4_sfu={r4}"
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
