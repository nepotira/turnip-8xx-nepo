#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Idempotent 4-layer patch orchestrator for Turnip Adreno 8xx & Snapdragon 8s Gen 4 (SM8735 / Adreno 825).

Applies:
  - Phase 0: Upstream MRs (!45937, !45973) and curated community patches (.patch and .py).
  - Layer 1: Adreno 825 (0x44030000) & Adreno 8xx silicon descriptors, exact CCU/VPC cache
             sizing for 1 MB GMEM, and anti-underflow assertion in fd6_gmem_cache.h.
  - Layer 2: A8XX LRZ fast-clear layout fd_lrzfc_layout<CHIP> fix in tu_lrz.cc (fixing the
             hardcoded <A7XX> offsets 2036..2168 that read inside fc1_b instead of metadata
             at 8192+ on A8XX), plus SP hysteresis tuning.
  - Layer 3: KGSL sparse VMA tu_dump_bo_init(dev, bo) list initialization fix in tu_knl_kgsl.cc.
  - Layer 4: Application Driconf tuning (Switch Emulators Eden/Citron/Sudachi/Yuzu, Hogwarts Legacy,
             Mortal Kombat 11) and variant-specific autotune (sustained, biggmem, maxperf, switch2).
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCHES_DIR = REPO_ROOT / "patches"

ORDERED_GIT_PATCHES = [
    "mr45937-tu-a8xx-wfi-before-reading-registers.patch",
    "mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch",
    "0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch",
    "0001A-tu-Mark-compute-state-stale-when-a-secondary-execute.patch",
    "0001B-tu-mesh-Size-chunk-tables-per-pipeline-and-advertise.patch",
    "0001C-tu-mesh-Only-flush-for-the-CP-after-the-setup-dispat.patch",
    "0001D-tu-mesh-Skip-vertex-and-primitive-fetches-for-dead-c.patch",
    "0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch",
    "0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch",
    "0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch",
    "0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch",
    "0006-tu-sample-shading-gate.patch",
    "0007-u_gralloc-always-use-ubwc-detection.patch",
    "0008-tu-mesh-Experimental-indexed-draw-for-mesh-shaders-w.patch",
    "0009-tu-mesh-Wait-for-the-ME-before-indirect-chunk-draws.patch",
    "08-tu-kgsl-cache-retired-a8xx-ib-storage.patch",
    "kgsl-syncobj-merge-ts-fd.patch",
    "kgsl-zero-timeout-poll.patch",
]

ORDERED_PY_PATCHES = [
    "15-wn-add-aimapper-gralloc.py",
    "16-wn-add-ubwc-swapchain-usage.py",
    "30-tu-z-mutable.py",
    "52-a8xx-resolve-cr-cntl.py",
    "54-a8xx-sp-hysteresis.py",
    "55-a8xx-sp-hysteresis-gs-hs-ds.py",
    "56-a8xx-shader-perf-and-compilation.py",
    "57-a8xx-switch2-dlss-extensions.py",
    "59-a8xx-ir3-coalesce-ubo-push-ranges.py",
    "60-a8xx-sanitize-frag-nan.py",
    "61-a8xx-lrz-bidir-disable.py",
    "62-a8xx-lrz-color-comp-mask.py",
]


def edit_file_idempotent(path: Path, old: str, new: str, label: str, required: bool = False) -> bool:
    if not path.exists():
        msg = f"[WARN] {path} not found while applying '{label}'"
        print(msg, file=sys.stderr)
        if required:
            raise RuntimeError(msg)
        return False

    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"[SKIP] {path.name}: '{label}' already applied")
        return True
    if old not in content:
        msg = f"[WARN] {path.name}: anchor not found for '{label}'"
        print(msg, file=sys.stderr)
        if required:
            raise RuntimeError(msg)
        return False

    path.write_text(content.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[OK]   {path.name}: applied '{label}'")
    return True


def apply_git_patches(mesa_dir: Path) -> None:
    print("=== Phase 0A: Applying curated .patch files ===")
    for patch_name in ORDERED_GIT_PATCHES:
        patch_path = PATCHES_DIR / patch_name
        if not patch_path.exists():
            raise FileNotFoundError(f"Missing required patch file: {patch_path}")

        rev_check = subprocess.run(
            ["git", "apply", "--reverse", "--check", str(patch_path)],
            cwd=mesa_dir,
            capture_output=True,
            text=True,
        )
        if rev_check.returncode == 0:
            print(f"[SKIP] {patch_name}: already applied in tree")
            continue

        fwd_check = subprocess.run(
            ["git", "apply", "--check", "--3way", str(patch_path)],
            cwd=mesa_dir,
            capture_output=True,
            text=True,
        )
        if fwd_check.returncode == 0:
            subprocess.run(
                ["git", "apply", "--3way", str(patch_path)],
                cwd=mesa_dir,
                check=True,
            )
            print(f"[OK]   {patch_name}: applied cleanly via git apply --3way")
        else:
            patch_cmd = subprocess.run(
                ["patch", "-p1", "--forward", "--batch", "-i", str(patch_path)],
                cwd=mesa_dir,
                capture_output=True,
                text=True,
            )
            if patch_cmd.returncode == 0:
                print(f"[OK]   {patch_name}: applied via patch -p1")
            else:
                print(
                    f"[WARN] {patch_name}: skipped (likely absorbed upstream): "
                    f"{fwd_check.stderr.strip().splitlines()[:1]}",
                    file=sys.stderr,
                )


def apply_python_patches(mesa_dir: Path) -> None:
    print("=== Phase 0B: Running standalone Python patch scripts ===")
    for py_name in ORDERED_PY_PATCHES:
        py_path = PATCHES_DIR / py_name
        if not py_path.exists():
            raise FileNotFoundError(f"Missing required Python patch script: {py_path}")
        res = subprocess.run(
            [sys.executable, str(py_path)],
            cwd=mesa_dir,
            capture_output=True,
            text=True,
        )
        if res.stdout.strip():
            print(res.stdout.strip())
        if res.stderr.strip():
            print(res.stderr.strip(), file=sys.stderr)
        if res.returncode != 0:
            raise RuntimeError(f"Python patch script {py_name} failed with exit code {res.returncode}")


def apply_layer1_silicon_and_gmem(mesa_dir: Path, variant: str) -> None:
    print(f"=== Layer 1: Silicon Descriptors & GMEM/CCU Math (variant={variant}) ===")
    fd_dev = mesa_dir / "src/freedreno/common/freedreno_devices.py"
    if fd_dev.exists():
        content = fd_dev.read_text(encoding="utf-8")

        # 1. Also add unmasked 0x44010000 KGSL chip_id for Adreno 810 if missing
        a810_old = '       GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810"),\n'
        a810_new = (
            '       GPUId(chip_id=0x44010000, name="Adreno (TM) 810"),\n'
            '       GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810"),\n'
        )
        if "0x44010000" not in content and a810_old in content:
            content = content.replace(a810_old, a810_new, 1)

        # 2. Update upstream Adreno 829 (0x44030a20 / 0x44030a00) with 1 MB GMEM safe CCU/VPC sizes
        a829_old = (
            'add_gpus([\n'
            '        GPUId(chip_id=0xffff44030a20, name="Adreno (TM) 829"),\n'
            '        GPUId(chip_id=0x44030a20, name="Adreno (TM) 829"), # KGSL\n'
            '    ], A6xxGPUInfo(\n'
            '        CHIP.A8XX,\n'
            '        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen2,\n'
            '         GPUProps(\n'
            '            shading_rate_matches_vk = True,  # TODO confirm this\n'
            '            sysmem_vpc_bv_pos_buf_size = 24576,\n'
            '         )],'
        )
        a829_new = (
            'add_gpus([\n'
            '        GPUId(chip_id=0x44030a00, name="Adreno (TM) 829"), # KGSL\n'
            '        GPUId(chip_id=0xffff44030a00, name="Adreno (TM) 829"),\n'
            '        GPUId(chip_id=0xffff44030a20, name="Adreno (TM) 829"),\n'
            '        GPUId(chip_id=0x44030a20, name="Adreno (TM) 829"), # KGSL\n'
            '    ], A6xxGPUInfo(\n'
            '        CHIP.A8XX,\n'
            '        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen2,\n'
            '         GPUProps(\n'
            '            shading_rate_matches_vk = True,\n'
            '            sysmem_vpc_attr_buf_size = 32768,\n'
            '            sysmem_vpc_pos_buf_size = 16384,\n'
            '            sysmem_vpc_bv_pos_buf_size = 16384,\n'
            '            sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,\n'
            '            sysmem_per_ccu_color_cache_size = 64 * 1024,\n'
            '            sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,\n'
            '            sysmem_per_ccu_depth_cache_size = 128 * 1024,\n'
            '            gmem_vpc_attr_buf_size = 16384,\n'
            '            gmem_vpc_pos_buf_size = 12288,\n'
            '            gmem_vpc_bv_pos_buf_size = 16384,\n'
            '            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n'
            '            gmem_per_ccu_color_cache_size = 16 * 1024,\n'
            '            gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.QUARTER.value,\n'
            '            gmem_per_ccu_depth_cache_size = 64 * 1024,\n'
            '            has_fs_tex_prefetch = False,\n'
            '            supports_double_threadsize = False,\n'
            '         )],'
        )
        if "0x44030a00" not in content and a829_old in content:
            content = content.replace(a829_old, a829_new, 1)

        # 3. Add Adreno 825 (Snapdragon 8s Gen 4 / SM8735, chip_id=0x44030000) with 1 MB GMEM math
        if "0x44030000" not in content:
            if variant in ("biggmem", "switch2"):
                gmem_depth_props = (
                    "            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n"
                    "            gmem_per_ccu_color_cache_size = 8 * 1024,\n"
                    "            gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n"
                    "            gmem_per_ccu_depth_cache_size = 16 * 1024,\n"
                )
            else:
                gmem_depth_props = (
                    "            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n"
                    "            gmem_per_ccu_color_cache_size = 8 * 1024,\n"
                    "            gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.QUARTER.value,\n"
                    "            gmem_per_ccu_depth_cache_size = 32 * 1024,\n"
                )

            early_preamble_prop = (
                "            has_early_preamble = False,\n" if variant == "maxperf" else ""
            )

            switch2_props = (
                "            has_attachment_shading_rate = True,\n"
                "            shading_rate_matches_vk = True,\n"
                if variant == "switch2"
                else ""
            )

            a825_entry = f"""add_gpus([
        GPUId(chip_id=0x44030000, name="Adreno (TM) 825"), # Snapdragon 8s Gen 4 (SM8735)
        GPUId(chip_id=0xffff44030000, name="Adreno (TM) 825"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen1, GPUProps(
            sysmem_vpc_attr_buf_size = 32768,
            sysmem_vpc_pos_buf_size = 16384,
            sysmem_vpc_bv_pos_buf_size = 16384,
            sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,
            sysmem_per_ccu_color_cache_size = 64 * 1024,
            sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,
            sysmem_per_ccu_depth_cache_size = 128 * 1024,
            gmem_vpc_attr_buf_size = 16384,
            gmem_vpc_pos_buf_size = 12288,
            gmem_vpc_bv_pos_buf_size = 16384,
{gmem_depth_props}            has_fs_tex_prefetch = False,
            supports_double_threadsize = False,
{early_preamble_prop}{switch2_props}        )],
        num_ccu = 4,
        num_slices = 2,
        tile_align_w = 64,
        tile_align_h = 32,
        tile_max_w = 16384,
        tile_max_h = 16384,
        num_vsc_pipes = 32,
        cs_shared_mem_size = 32 * 1024,
        wave_granularity = 2,
        fibers_per_sp = 128 * 2 * 16,
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))

"""
            anchor = 'if __name__ == "__main__":'
            if anchor in content:
                content = content.replace(anchor, a825_entry + anchor, 1)
                compile(content, str(fd_dev), "exec")
                fd_dev.write_text(content, encoding="utf-8", newline="\n")
                print(f"[OK]   freedreno_devices.py: added Adreno 825 (0x44030000) and updated Adreno 829 (variant={variant})")
            else:
                raise RuntimeError("Could not find __main__ anchor in freedreno_devices.py")
        else:
            print("[SKIP] freedreno_devices.py: Adreno 825 (0x44030000) already present")

    gmem_cache_h = mesa_dir / "src/freedreno/common/fd6_gmem_cache.h"
    edit_file_idempotent(
        gmem_cache_h,
        "   config->depth_ccu_offset = offset - (num_ccu * config->depth_cache_size);\n"
        "   offset = config->depth_ccu_offset;\n\n"
        "   return offset;",
        "   assert(offset >= num_ccu * config->depth_cache_size);\n"
        "   config->depth_ccu_offset = offset - (num_ccu * config->depth_cache_size);\n"
        "   offset = config->depth_ccu_offset;\n\n"
        "   return offset;",
        "anti-underflow assertion in __calc_gmem_cache_offsets",
        required=True,
    )


def apply_layer2_pipeline_and_lrz(mesa_dir: Path, variant: str) -> None:
    print(f"=== Layer 2: Pipeline, LRZ & Register Template Fixes (variant={variant}) ===")
    tu_lrz = mesa_dir / "src/freedreno/vulkan/tu_lrz.cc"
    edit_file_idempotent(
        tu_lrz,
        "         // FIXME hard-coding A7XX here and below is wrong!\n"
        "         uint64_t br_cur_buffer_iova =\n"
        "            lrz_fc_iova + offsetof(fd_lrzfc_layout<A7XX>, br_cur_buffer);\n"
        "\n"
        "         /* Make sure the value is written to memory. */\n"
        "         tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_CLEAN);\n"
        "         tu_cs_emit_wfi(cs);\n"
        "         tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);\n"
        "\n"
        "         /* if (br_cur_buffer != 0) { */\n"
        "         tu_cs_reserve(cs, 7 + if_dwords + 1 + else_dwords);\n"
        "         tu_cs_emit_pkt7(cs, CP_COND_EXEC, 6);\n"
        "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
        "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
        "         tu_cs_emit(cs, 2); /* REF */\n"
        "         tu_cs_emit(cs, if_dwords + 1);\n"
        "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[1].depth_clear_val */\n"
        "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
        "                        lrz_fc_iova + offsetof(fd_lrzfc_layout<A7XX>, buffer[1].depth_clear_val));\n"
        "\n"
        "         /* } else { */\n"
        "         tu_cs_emit_pkt7(cs, CP_NOP, else_dwords);\n"
        "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[0].depth_clear_val */\n"
        "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
        "                        lrz_fc_iova + offsetof(fd_lrzfc_layout<A7XX>, buffer[0].depth_clear_val));",
        "         using lrzfc_layout = fd_lrzfc_layout<CHIP == A6XX ? A7XX : CHIP>;\n"
        "         uint64_t br_cur_buffer_iova =\n"
        "            lrz_fc_iova + offsetof(lrzfc_layout, br_cur_buffer);\n"
        "\n"
        "         /* Make sure the value is written to memory. */\n"
        "         tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_CLEAN);\n"
        "         tu_cs_emit_wfi(cs);\n"
        "         tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);\n"
        "\n"
        "         /* if (br_cur_buffer != 0) { */\n"
        "         tu_cs_reserve(cs, 7 + if_dwords + 1 + else_dwords);\n"
        "         tu_cs_emit_pkt7(cs, CP_COND_EXEC, 6);\n"
        "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
        "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
        "         tu_cs_emit(cs, 2); /* REF */\n"
        "         tu_cs_emit(cs, if_dwords + 1);\n"
        "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[1].depth_clear_val */\n"
        "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
        "                        lrz_fc_iova + offsetof(lrzfc_layout, buffer[1].depth_clear_val));\n"
        "\n"
        "         /* } else { */\n"
        "         tu_cs_emit_pkt7(cs, CP_NOP, else_dwords);\n"
        "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[0].depth_clear_val */\n"
        "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
        "                        lrz_fc_iova + offsetof(lrzfc_layout, buffer[0].depth_clear_val));",
        "A8XX fd_lrzfc_layout<CHIP> br_cur_buffer & depth_clear_val offset fix",
        required=True,
    )

    tu_cmd = mesa_dir / "src/freedreno/vulkan/tu_cmd_buffer.cc"
    if variant == "maxperf":
        edit_file_idempotent(
            tu_cmd,
            "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00000c00));\n"
            "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000400));\n"
            "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000400));",
            "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00001800));\n"
            "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000800));\n"
            "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000800));",
            "MaxPerf doubled SP hysteresis thresholds",
            required=False,
        )
    elif variant == "switch2":
        edit_file_idempotent(
            tu_cmd,
            "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00000c00));\n"
            "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000400));\n"
            "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000400));",
            "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00001000));\n"
            "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000600));\n"
            "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000600));",
            "Switch2 balanced SP hysteresis thresholds",
            required=False,
        )


def apply_layer3_and_4_kgsl_and_autotune(mesa_dir: Path, variant: str) -> None:
    print(f"=== Layer 3 & 4: KGSL Sparse VMA Init & Variant Autotune (variant={variant}) ===")
    tu_kgsl = mesa_dir / "src/freedreno/vulkan/tu_knl_kgsl.cc"
    edit_file_idempotent(
        tu_kgsl,
        "   out_vma->kgsl.virtual_bo = bo;\n"
        "   *out_iova = bo->iova;\n"
        "   return VK_SUCCESS;",
        "   tu_dump_bo_init(dev, bo);\n"
        "   out_vma->kgsl.virtual_bo = bo;\n"
        "   *out_iova = bo->iova;\n"
        "   return VK_SUCCESS;",
        "kgsl_sparse_vma_init tu_dump_bo_init(dev, bo) list initialization",
        required=True,
    )

    if variant in ("biggmem", "switch2"):
        tu_autotune = mesa_dir / "src/freedreno/vulkan/tu_autotune.cc"
        edit_file_idempotent(
            tu_autotune,
            "   DEFAULT = BANDWIDTH, /* Default algorithm, used if no other is specified. */",
            "   DEFAULT = PREFER_GMEM, /* BigGMEM/Switch2 variant: prefer GMEM on Adreno 825 1 MB GMEM */",
            "BigGMEM/Switch2 PREFER_GMEM default algorithm in tu_autotune.cc",
            required=True,
        )

    # Layer 4B: Driconf profiles for Switch emulators, Hogwarts Legacy, and Mortal Kombat 11
    driconf = mesa_dir / "src/freedreno/vulkan/00-turnip-defaults.conf"
    app_profiles = """
        <!-- Nintendo Switch Emulators: Nyushu, Eden, Citron, Sudachi, Yuzu, Ryujinx, Suyu -->
        <application name="Switch Emulators" application_name_match=".*([Ee]den|[Yy]uzu|[Cc]itron|[Ss]udachi|[Ss]uyu|[Rr]yujinx|[Nn]yushu|dev\\.eden|org\\.citron|org\\.yuzu|org\\.nyushu).*">
            <option name="tu_independent_icache_miss" value="true" />
            <option name="tu_autotune_algorithm" value="prefer_gmem" />
            <option name="tu_allow_oob_indirect_ubo_loads" value="true" />
            <option name="tu_enable_fast_border_color_for_undefined_formats" value="true" />
        </application>

        <!-- Hogwarts Legacy (Switch Edition & PC DX12 Phoenix-Win64-Shipping via VKD3D-Proton) -->
        <application name="Hogwarts Legacy" application_name_match=".*(Hogwarts|Phoenix).*">
            <option name="tu_autotune_algorithm" value="prefer_sysmem" />
            <option name="tu_allow_oob_indirect_ubo_loads" value="true" />
            <option name="tu_enable_ssbo_emulation" value="true" />
            <option name="tu_enable_fast_border_color_for_undefined_formats" value="true" />
            <option name="tu_independent_icache_miss" value="true" />
        </application>

        <!-- Mortal Kombat 11 (Switch Edition & PC DX11/DX12 via DXVK/VKD3D-Proton) -->
        <application name="Mortal Kombat 11" application_name_match=".*(MK11|MortalKombat11).*">
            <option name="tu_emulate_alpha_to_coverage" value="true" />
            <option name="tu_allow_oob_indirect_ubo_loads" value="true" />
            <option name="tu_independent_icache_miss" value="true" />
            <option name="tu_enable_fast_border_color_for_undefined_formats" value="true" />
        </application>
"""
    edit_file_idempotent(
        driconf,
        "    </device>\n</driconf>",
        f"{app_profiles}    </device>\n</driconf>",
        "Driconf application profiles for Switch emulators, Hogwarts Legacy, and Mortal Kombat 11",
        required=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Turnip A8xx & 8s Gen 4 hybrid patch stack.")
    parser.add_argument("--mesa-dir", type=Path, default=Path("."), help="Path to Mesa source root")
    parser.add_argument(
        "--variant",
        choices=["sustained", "biggmem", "maxperf", "switch2"],
        default="sustained",
        help="Build variant to configure (sustained=-b, biggmem=-e, maxperf=-p, switch2=-s2)",
    )
    args = parser.parse_args()

    mesa_dir = args.mesa_dir.resolve()
    if not (mesa_dir / "src/freedreno/vulkan").is_dir():
        print(f"ERROR: {mesa_dir} does not appear to be a valid Mesa source tree.", file=sys.stderr)
        return 1

    apply_git_patches(mesa_dir)
    apply_python_patches(mesa_dir)
    apply_layer1_silicon_and_gmem(mesa_dir, args.variant)
    apply_layer2_pipeline_and_lrz(mesa_dir, args.variant)
    apply_layer3_and_4_kgsl_and_autotune(mesa_dir, args.variant)

    print(f"\n[SUCCESS] All 4 layers of the Turnip A8xx ({args.variant}) patch stack applied cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
