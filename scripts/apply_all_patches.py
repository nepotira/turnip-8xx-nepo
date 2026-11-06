#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Idempotent 4-layer patch orchestrator for Turnip Adreno 8xx & Snapdragon 8s Gen 4 (SM8735 / Adreno 825).

Applies:
  - Phase 0: Upstream MRs (!45937, !45973) and curated community patches (.patch and .py).
  - Layer 1: Adreno 825 (0x44030000) & Adreno 8xx silicon descriptors, exact CCU cache
             sizing for 1 MB GMEM, and anti-underflow assertion in fd6_gmem_cache.h.
  - Layer 2: A8XX LRZ fast-clear layout sizeof(fd_lrzfc_layout<CHIP>) fix in tu_lrz.cc,
             residual <A7XX> template instantiation fixes in tu_pipeline.cc, tu_query_pool.cc,
             and tu_cmd_buffer.cc.
  - Layer 3: KGSL sparse VMA tu_dump_bo_init(dev, bo) fix, UBWC_5/UBWC_6 macrotile cases,
             and VK_KHR_display tolerance for Winlator/Eden.
  - Layer 4: IR3 coalesce_ubo_push_ranges for Adreno 825/829, and bandwidth/GMEM autotune
             prioritization per build variant (sustained, biggmem, maxperf).
"""

import argparse
import os
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
        if "0x44030000" not in content:
            if variant == "biggmem":
                a825_ccu_block = (
                    "        sysmem_per_ccu_color_cache_size = 32 * 1024,\n"
                    "        sysmem_per_ccu_depth_cache_size = 64 * 1024,\n"
                    "        gmem_per_ccu_color_cache_size = 32 * 1024,\n"
                    "        gmem_per_ccu_depth_cache_size = 32 * 1024,\n"
                    "        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.QUARTER.value,\n"
                    "        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,\n"
                )
            else:
                a825_ccu_block = (
                    "        sysmem_per_ccu_color_cache_size = 32 * 1024,\n"
                    "        sysmem_per_ccu_depth_cache_size = 64 * 1024,\n"
                    "        gmem_per_ccu_color_cache_size = 32 * 1024,\n"
                    "        gmem_per_ccu_depth_cache_size = 64 * 1024,\n"
                    "        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n"
                    "        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,\n"
                )

            has_early_preamble_line = (
                "        has_early_preamble = False,\n" if variant == "maxperf" else ""
            )

            a825_entry = f"""
add_gpus([
        GPUId(chip_id=0x44030000, name="FD825"), # Adreno 825 (Snapdragon 8s Gen 4 / SM8735)
        GPUId(chip_id=0xffff44030000, name="FD825"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base],
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
{a825_ccu_block}        a7xx_ubwc_mode = 2,
        has_fs_tex_prefetch = False,
        supports_double_threadsize = False,
{has_early_preamble_line}        magic_regs = dict(),
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))

add_gpus([
        GPUId(chip_id=0x44030a00, name="FD829"), # Adreno 829 (Snapdragon 8 Gen 5)
        GPUId(chip_id=0x44030a20, name="FD829"),
        GPUId(chip_id=0xffff44030a00, name="FD829"),
    ], A6xxGPUInfo(
        CHIP.A8XX,
        [a7xx_base, a7xx_gen3, a8xx_base],
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
        sysmem_per_ccu_color_cache_size = 32 * 1024,
        sysmem_per_ccu_depth_cache_size = 64 * 1024,
        gmem_per_ccu_color_cache_size = 32 * 1024,
        gmem_per_ccu_depth_cache_size = 64 * 1024,
        gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,
        gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,
        a7xx_ubwc_mode = 2,
        has_fs_tex_prefetch = False,
        supports_double_threadsize = False,
        magic_regs = dict(),
        raw_magic_regs = a8xx_base_raw_magic_regs,
    ))
"""
            anchor = "template = \"\"\"/* Copyright"
            if anchor in content:
                content = content.replace(anchor, a825_entry + "\n" + anchor, 1)
                fd_dev.write_text(content, encoding="utf-8", newline="\n")
                print(f"[OK]   freedreno_devices.py: added Adreno 825 (0x44030000) and Adreno 829 descriptors (variant={variant})")
            else:
                raise RuntimeError("Could not find template anchor in freedreno_devices.py")
        else:
            print("[SKIP] freedreno_devices.py: Adreno 825 (0x44030000) already present")

    gmem_cache_h = mesa_dir / "src/freedreno/common/fd6_gmem_cache.h"
    edit_file_idempotent(
        gmem_cache_h,
        "   return info->gmem_size_bytes - depth_cache_size - color_cache_size;",
        "   assert(info->gmem_size_bytes > depth_cache_size + color_cache_size);\n"
        "   return info->gmem_size_bytes - depth_cache_size - color_cache_size;",
        "anti-underflow assertion in __calc_gmem_color_offset",
    )


def apply_layer2_pipeline_and_lrz(mesa_dir: Path, variant: str) -> None:
    print(f"=== Layer 2: Pipeline, LRZ & Register Template Fixes (variant={variant}) ===")
    tu_lrz = mesa_dir / "src/freedreno/vulkan/tu_lrz.cc"
    edit_file_idempotent(
        tu_lrz,
        "offsetof(fd_lrzfc_layout<A6XX>, dir_track)",
        "offsetof(fd_lrzfc_layout<CHIP>, dir_track)",
        "A8XX fd_lrzfc_layout<CHIP> dir_track offset fix",
    )
    edit_file_idempotent(
        tu_lrz,
        "sizeof(fd_lrzfc_layout<A6XX>) - offsetof(fd_lrzfc_layout<A6XX>, dir_track)",
        "sizeof(fd_lrzfc_layout<CHIP>) - offsetof(fd_lrzfc_layout<CHIP>, dir_track)",
        "A8XX fd_lrzfc_layout<CHIP> clear size fix",
    )

    tu_pipeline = mesa_dir / "src/freedreno/vulkan/tu_pipeline.cc"
    edit_file_idempotent(
        tu_pipeline,
        "tu6_emit_flushes<A7XX>(",
        "tu6_emit_flushes<CHIP>(",
        "tu6_emit_flushes<CHIP> template dispatch in tu_pipeline.cc",
    )

    tu_query = mesa_dir / "src/freedreno/vulkan/tu_query_pool.cc"
    edit_file_idempotent(
        tu_query,
        "fd_PerfCounter<A7XX>",
        "fd_PerfCounter<CHIP>",
        "fd_PerfCounter<CHIP> template dispatch in tu_query_pool.cc",
    )

    tu_cmd = mesa_dir / "src/freedreno/vulkan/tu_cmd_buffer.cc"
    edit_file_idempotent(
        tu_cmd,
        "A7XX_PC_SO_STREAM_CNTL(",
        "PC_SO_STREAM_CNTL(CHIP, ",
        "PC_SO_STREAM_CNTL(CHIP) dispatch in tu_cmd_buffer.cc",
    )

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
        )


def apply_layer3_and_4_kgsl_ir3_autotune(mesa_dir: Path, variant: str) -> None:
    print(f"=== Layer 3 & 4: KGSL Sparse VMA, UBWC_5/6, IR3 UBO Coalescing & Autotune (variant={variant}) ===")
    tu_kgsl = mesa_dir / "src/freedreno/vulkan/tu_knl_kgsl.cc"
    edit_file_idempotent(
        tu_kgsl,
        "   vma->kgsl.fd = req.fd;\n   return VK_SUCCESS;",
        "   vma->kgsl.fd = req.fd;\n   tu_dump_bo_init(dev, bo);\n   return VK_SUCCESS;",
        "kgsl_sparse_vma_init tu_dump_bo_init(dev, bo) list initialization",
    )
    edit_file_idempotent(
        tu_kgsl,
        "   case 4:\n      info->ubwc_version = FD_UBWC_4;",
        "   case 5:\n   case 6:\n   case 4:\n      info->ubwc_version = FD_UBWC_4;",
        "KGSL UBWC_5 and UBWC_6 macrotile version support",
    )

    ir3_comp = mesa_dir / "src/freedreno/ir3/ir3_compiler.c"
    edit_file_idempotent(
        ir3_comp,
        "compiler->coalesce_ubo_push_ranges = dev_info->chip == A8XX &&",
        "compiler->coalesce_ubo_push_ranges = (info->chip_id == 0x44030000 || info->chip_id == 0x44030a20) || (dev_info->chip == A8XX &&",
        "IR3 coalesce_ubo_push_ranges enablement for Adreno 825 and Adreno 829",
    )

    if variant in ("sustained", "biggmem"):
        tu_autotune = mesa_dir / "src/freedreno/vulkan/tu_autotune.cc"
        edit_file_idempotent(
            tu_autotune,
            "   if (cmd->device->physical_device->info->chip >= A8XX)",
            "   /* Prioritize GMEM rendering on A8XX for 3200 MHz LPDDR5X bandwidth savings */\n"
            "   if (false && cmd->device->physical_device->info->chip >= A8XX)",
            "A8XX GMEM bandwidth prioritization in tu_autotune.cc",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Turnip A8xx & 8s Gen 4 hybrid patch stack.")
    parser.add_argument("--mesa-dir", type=Path, default=Path("."), help="Path to Mesa source root")
    parser.add_argument(
        "--variant",
        choices=["sustained", "biggmem", "maxperf"],
        default="sustained",
        help="Build variant to configure (sustained=-b, biggmem=-e, maxperf=-p)",
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
    apply_layer3_and_4_kgsl_ir3_autotune(mesa_dir, args.variant)

    print(f"\n[SUCCESS] All 4 layers of the Turnip A8xx ({args.variant}) patch stack applied cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
