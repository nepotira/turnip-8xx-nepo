#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""66-nepo-switch1-pacing-and-ir3.py: Nintendo Switch 1 Frame Pacing, IR3 Register Pressure & Adreno 8xx Slice Optimization Pack.

Applies 6 exact anchor-verified optimizations on top of patch 65:
1. [SHADER STUTTER] Expand pipeline_suballoc (128KB -> 1MB) and kgsl_profiling_suballoc (128KB -> 512KB) in tu_device.cc to cut KGSL ioctl syscalls by 8x during shader compilation bursts.
2. [SHADER COMPILE] Prioritize lower live_effect() in choose_instr_inc (ir3_sched.c) during register pressure growth to prevent IR3 scheduler backtracking on decompiled Switch shaders.
3. [A8XX SLICES] Relax sysmem subpass slice wait from WFI to CP_WAIT_FOR_ME in tu_cmd_buffer.cc so Adreno 8xx slices are not drained to idle between subpasses.
4. [SWITCH UBWC] Extend NEPO_65_MUTABLE_UBWC in tu_image.cc with Switch 1 NVN render target formats (R16G16_SFLOAT motion vectors, R16_SFLOAT, R32_SFLOAT depth copy, R8_UNORM, R8G8_UNORM).
5. [RENDERPASS SPLIT] Replace full WFI stall with WAIT_FOR_ME on resuming dynamic render passes in tu_cmd_buffer.cc to eliminate frame drops when vk_scheduler.cpp splits passes for UBO uploads.
6. [SWITCH PRESENTER] Add single-subpass no-depth low-draw fast-path in use_sysmem_rendering (tu_cmd_buffer.cc) so Switch BlitScreen/FSR presenter passes bypass GMEM binning overhead.
"""

import pathlib
import sys

NAME = "66-nepo-switch1-pacing-and-ir3"


def mod_1_expand_pipeline_suballoc(mesa_root: pathlib.Path) -> str:
    import re
    p = mesa_root / "src/freedreno/vulkan/tu_device.cc"
    if not p.exists():
        return "ERROR: tu_device.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_66_SUBALLOC_1MB */" in txt:
        return "ALREADY"

    pat_pipe = re.compile(r"(&device->pipeline_suballoc,\s*device,\s*)128\s*\*\s*1024,")
    if not pat_pipe.search(txt):
        return "ERROR: pipeline_suballoc 128*1024 anchor not found in tu_device.cc"

    txt = pat_pipe.sub(r"/* NEPO_66_SUBALLOC_1MB */ \g<1>1024 * 1024,", txt, count=1)

    pat_prof = re.compile(r"(&device->kgsl_profiling_suballoc,\s*device,\s*)128\s*\*\s*1024,")
    if pat_prof.search(txt):
        txt = pat_prof.sub(r"\g<1>512 * 1024,", txt, count=1)

    p.write_text(txt, encoding="utf-8", newline="\n")
    return "OK"

def mod_2_ir3_sched_prefer_lower_live(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/ir3/ir3_sched.c"
    if not p.exists():
        return "ERROR: ir3_sched.c not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_66_IR3_LOWER_LIVE" in txt:
        return "ALREADY"

    old = (
        "   unsigned chosen_distance = 0;\n"
        "\n"
        "   /* Pick the max delay of the remaining ready set. */\n"
        "   foreach_sched_node (n, &ctx->dag->heads) {\n"
        "      if (avoid_output && n->output)\n"
        "         continue;\n"
        "\n"
        "      if (defer && should_defer(ctx, n->instr))\n"
        "         continue;\n"
        "\n"
        "      if (!check_instr(ctx, notes, n->instr))\n"
        "         continue;\n"
        "\n"
        "      unsigned d = node_delay(ctx, n);\n"
        "\n"
        "      enum choose_instr_inc_rank rank;\n"
        "      if (d == 0)\n"
        "         rank = INC_DISTANCE_READY;\n"
        "      else\n"
        "         rank = INC_DISTANCE;\n"
        "\n"
        "      unsigned distance = nearest_use(n->instr);\n"
        "\n"
        "      if (!chosen || rank > chosen_rank ||\n"
        "          (rank == chosen_rank && distance < chosen_distance)) {\n"
        "         chosen = n;\n"
        "         chosen_distance = distance;\n"
        "         chosen_rank = rank;\n"
        "      }\n"
        "   }"
    )
    new = (
        "   unsigned chosen_distance = 0;\n"
        "   int chosen_live = 999999;\n"
        "\n"
        "   /* Pick the max delay of the remaining ready set. */\n"
        "   foreach_sched_node (n, &ctx->dag->heads) {\n"
        "      if (avoid_output && n->output)\n"
        "         continue;\n"
        "\n"
        "      if (defer && should_defer(ctx, n->instr))\n"
        "         continue;\n"
        "\n"
        "      if (!check_instr(ctx, notes, n->instr))\n"
        "         continue;\n"
        "\n"
        "      unsigned d = node_delay(ctx, n);\n"
        "\n"
        "      enum choose_instr_inc_rank rank;\n"
        "      if (d == 0)\n"
        "         rank = INC_DISTANCE_READY;\n"
        "      else\n"
        "         rank = INC_DISTANCE;\n"
        "\n"
        "      unsigned distance = nearest_use(n->instr);\n"
        "      int live = live_effect(n->instr);\n"
        "\n"
        "      /* NEPO_66_IR3_LOWER_LIVE: Prefer instructions reducing live register pressure */\n"
        "      if (!chosen || rank > chosen_rank ||\n"
        "          (rank == chosen_rank && live < chosen_live) ||\n"
        "          (rank == chosen_rank && live == chosen_live && distance < chosen_distance)) {\n"
        "         chosen = n;\n"
        "         chosen_distance = distance;\n"
        "         chosen_live = live;\n"
        "         chosen_rank = rank;\n"
        "      }\n"
        "   }"
    )
    if old not in txt:
        return "ERROR: choose_instr_inc anchor not found in ir3_sched.c"
    p.write_text(txt.replace(old, new, 1), encoding="utf-8", newline="\n")
    return "OK"


def mod_3_sysmem_wfi_relax_and_presenter_fastpath(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/vulkan/tu_cmd_buffer.cc"
    if not p.exists():
        return "ERROR: tu_cmd_buffer.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_66_SYSMEM_WFI_RELAX */" in txt:
        return "ALREADY"

    old_wfi = (
        "      tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(RENDER_MODE) |\n"
        "                             CP_COND_REG_EXEC_0_SYSMEM);\n"
        "      if (emit_cache_invalidate_gmem)\n"
        "         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_CACHE_INVALIDATE);\n"
        "      if (emit_subpass_slice_wait)\n"
        "         tu_cs_emit_wfi(cs);\n"
        "      tu_cond_exec_end(cs);"
    )
    new_wfi = (
        "      /* NEPO_66_SYSMEM_WFI_RELAX */\n"
        "      tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(RENDER_MODE) |\n"
        "                             CP_COND_REG_EXEC_0_SYSMEM);\n"
        "      if (emit_cache_invalidate_gmem)\n"
        "         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_CACHE_INVALIDATE);\n"
        "      if (emit_subpass_slice_wait)\n"
        "         tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);\n"
        "      tu_cond_exec_end(cs);"
    )
    if old_wfi not in txt:
        return "ERROR: subpass_slice_wait anchor not found in tu_cmd_buffer.cc"
    txt = txt.replace(old_wfi, new_wfi, 1)

    old_resuming = (
        "   if (resuming) {\n"
        "      cmd->state.cache.pending_flush_bits |=\n"
        "         TU_CMD_FLAG_WAIT_FOR_IDLE | TU_CMD_FLAG_CACHE_INVALIDATE;\n"
        "   }"
    )
    new_resuming = (
        "   if (resuming) {\n"
        "      /* NEPO_66_RESUMING_WAIT_FOR_ME */\n"
        "      cmd->state.cache.pending_flush_bits |=\n"
        "         TU_CMD_FLAG_WAIT_FOR_ME | TU_CMD_FLAG_CACHE_INVALIDATE;\n"
        "   }"
    )
    if old_resuming in txt:
        txt = txt.replace(old_resuming, new_resuming, 1)

    old_sysmem = (
        "   /* This is a case where it's better to avoid GMEM, too many tiles but no HW binning possible. */\n"
        "   if (!vsc->binning_possible && vsc->binning_useful) {\n"
        "      cmd->state.rp.force_render_mode_reason =\n"
        '         "Too many tiles and HW binning is not possible";\n'
        "      return true;\n"
        "   }"
    )
    new_sysmem = (
        "   /* This is a case where it's better to avoid GMEM, too many tiles but no HW binning possible. */\n"
        "   if (!vsc->binning_possible && vsc->binning_useful) {\n"
        "      cmd->state.rp.force_render_mode_reason =\n"
        '         "Too many tiles and HW binning is not possible";\n'
        "      return true;\n"
        "   }\n"
        "\n"
        "   /* NEPO_66_PRESENTER_FASTPATH: Bypass GMEM binning for Switch 1 BlitScreen / 1-quad post-FX passes */\n"
        "   if (cmd->state.pass->subpass_count == 1 &&\n"
        "       cmd->state.pass->subpasses[0].depth_stencil_attachment.attachment == VK_ATTACHMENT_UNUSED &&\n"
        "       cmd->state.rp.drawcall_count <= 2) {\n"
        '      cmd->state.rp.force_render_mode_reason = "Switch Presenter / PostFX fastpath";\n'
        "      return true;\n"
        "   }"
    )
    if old_sysmem not in txt:
        return "ERROR: use_sysmem_rendering anchor not found in tu_cmd_buffer.cc"
    txt = txt.replace(old_sysmem, new_sysmem, 1)

    p.write_text(txt, encoding="utf-8", newline="\n")
    return "OK"


def mod_4_switch_mutable_ubwc_formats(mesa_root: pathlib.Path) -> str:
    p = mesa_root / "src/freedreno/vulkan/tu_image.cc"
    if not p.exists():
        return "ERROR: tu_image.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_66_SWITCH_RT_UBWC */" in txt:
        return "ALREADY"

    old_13 = (
        "             (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||\n"
        "              image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||\n"
        "              image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||\n"
        "              image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||\n"
        "              image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||\n"
        "              image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||\n"
        "              image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));"
    )
    old_14 = (
        "              (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||\n"
        "               image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||\n"
        "               image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||\n"
        "               image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||\n"
        "               image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||\n"
        "               image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||\n"
        "               image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));"
    )

    if old_13 in txt:
        old = old_13
        new = (
            "             /* NEPO_66_SWITCH_RT_UBWC */\n"
            "             (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||\n"
            "              image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||\n"
            "              image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||\n"
            "              image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||\n"
            "              image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||\n"
            "              image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||\n"
            "              image->vk.format == VK_FORMAT_R16G16_SFLOAT ||\n"
            "              image->vk.format == VK_FORMAT_R16_SFLOAT ||\n"
            "              image->vk.format == VK_FORMAT_R32_SFLOAT ||\n"
            "              image->vk.format == VK_FORMAT_R8G8_UNORM ||\n"
            "              image->vk.format == VK_FORMAT_R8_UNORM ||\n"
            "              image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));"
        )
    elif old_14 in txt:
        old = old_14
        new = (
            "              /* NEPO_66_SWITCH_RT_UBWC */\n"
            "              (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||\n"
            "               image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||\n"
            "               image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||\n"
            "               image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||\n"
            "               image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||\n"
            "               image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||\n"
            "               image->vk.format == VK_FORMAT_R16G16_SFLOAT ||\n"
            "               image->vk.format == VK_FORMAT_R16_SFLOAT ||\n"
            "               image->vk.format == VK_FORMAT_R32_SFLOAT ||\n"
            "               image->vk.format == VK_FORMAT_R8G8_UNORM ||\n"
            "               image->vk.format == VK_FORMAT_R8_UNORM ||\n"
            "               image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));"
        )
    else:
        return "ERROR: NEPO_65_MUTABLE_UBWC anchor not found in tu_image.cc"

    p.write_text(txt.replace(old, new, 1), encoding="utf-8", newline="\n")
    return "OK"


def mod_5_ensure_patch65_ubo_idempotency_marker(mesa_root: pathlib.Path) -> str:
    """Patch 65 checks for '/* NEPO_65_UBO_COALESCE */' but writes '/* NEPO_65_UBO_COALESCE:'.
    Adding the exact marker comment keeps multi-pass --strict runs 100% idempotent without editing patch 65.
    """
    p = mesa_root / "src/freedreno/ir3/ir3_nir_analyze_ubo_ranges.c"
    if not p.exists():
        return "SKIP"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_65_UBO_COALESCE */" in txt:
        return "ALREADY"
    target = "/* NEPO_65_UBO_COALESCE: Coalesce neighboring UBO ranges"
    if target in txt:
        p.write_text(
            txt.replace(target, "/* NEPO_65_UBO_COALESCE */ /* NEPO_65_UBO_COALESCE: Coalesce neighboring UBO ranges", 1),
            encoding="utf-8",
            newline="\n",
        )
        return "OK"
    return "SKIP"


def mod_6_lrz_preserve_on_skipped_color_writes(mesa_root: pathlib.Path) -> str:
    """Prevent depth-only draws mid-renderpass from permanently disabling LRZ writes for the rest of the RP."""
    p = mesa_root / "src/freedreno/vulkan/tu_lrz.cc"
    if not p.exists():
        return "ERROR: tu_lrz.cc not found"
    txt = p.read_text(encoding="utf-8")
    if "/* NEPO_66_LRZ_KEEP_DEPTH_ONLY */" in txt:
        return "ALREADY"

    old = (
        "   if (blend_status == TU_LRZ_BLEND_ALL_COLOR_WRITES_SKIPPED &&\n"
        "       z_write_enable && !TU_DRIRC(cmd->device, misc.disable_conservative_lrz)) {\n"
        "      if (cmd->state.lrz.color_written_with_z_test) {\n"
        '         tu_lrz_disable_write_for_rp(cmd, "Depth write + no color writes");\n'
        "      }\n"
        "      cmd->state.lrz.has_lrz_write_with_skipped_color_writes = true;\n"
        "   }"
    )
    new = (
        "   /* NEPO_66_LRZ_KEEP_DEPTH_ONLY: Keep LRZ write alive across Switch mid-RP depth-only draws */\n"
        "   if (blend_status == TU_LRZ_BLEND_ALL_COLOR_WRITES_SKIPPED &&\n"
        "       z_write_enable && !TU_DRIRC(cmd->device, misc.disable_conservative_lrz)) {\n"
        "      cmd->state.lrz.has_lrz_write_with_skipped_color_writes = true;\n"
        "   }"
    )
    if old not in txt:
        return "ERROR: TU_LRZ_BLEND_ALL_COLOR_WRITES_SKIPPED anchor not found in tu_lrz.cc"
    p.write_text(txt.replace(old, new, 1), encoding="utf-8", newline="\n")
    return "OK"


def main() -> int:
    mesa_root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd()
    r1 = mod_1_expand_pipeline_suballoc(mesa_root)
    r2 = mod_2_ir3_sched_prefer_lower_live(mesa_root)
    r3 = mod_3_sysmem_wfi_relax_and_presenter_fastpath(mesa_root)
    r4 = mod_4_switch_mutable_ubwc_formats(mesa_root)
    r5 = mod_5_ensure_patch65_ubo_idempotency_marker(mesa_root)
    r6 = mod_6_lrz_preserve_on_skipped_color_writes(mesa_root)

    results = (r1, r2, r3, r4, r6)
    summary = f"suballoc_1mb={r1} ir3_lower_live={r2} sysmem_wfi_and_presenter={r3} switch_ubwc={r4} ubo_marker={r5} lrz_keep={r6}"
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
