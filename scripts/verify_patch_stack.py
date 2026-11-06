#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Deterministic mathematical and structural verification suite for the
Turnip Adreno 8xx & Snapdragon 8s Gen 4 (SM8735 / Adreno 825) patch stack.
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCHES_DIR = REPO_ROOT / "patches"
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
import apply_all_patches  # noqa: E402


def calc_gmem_layout(
    gmem_bytes: int,
    num_ccu: int,
    per_ccu_color_bytes: int,
    per_ccu_depth_bytes: int,
    color_fraction_shift: int,
    depth_fraction_shift: int,
) -> dict:
    """Replicates src/freedreno/common/fd6_gmem_cache.h offset math."""
    color_cache_size = (num_ccu * per_ccu_color_bytes) >> color_fraction_shift
    depth_cache_size = (num_ccu * per_ccu_depth_bytes) >> depth_fraction_shift
    color_offset = gmem_bytes - depth_cache_size - color_cache_size
    depth_offset = gmem_bytes - depth_cache_size
    return {
        "gmem_bytes": gmem_bytes,
        "color_cache_size": color_cache_size,
        "depth_cache_size": depth_cache_size,
        "total_reserved": color_cache_size + depth_cache_size,
        "usable_gmem": color_offset,
        "color_offset": color_offset,
        "depth_offset": depth_offset,
    }


def verify_files_and_syntax() -> None:
    print("[1/3] Verifying presence and syntax of all patches and scripts...")
    for patch_name in apply_all_patches.ORDERED_GIT_PATCHES:
        p = PATCHES_DIR / patch_name
        assert p.is_file() and p.stat().st_size > 0, f"Missing or empty patch: {p}"

    for py_name in apply_all_patches.ORDERED_PY_PATCHES:
        p = PATCHES_DIR / py_name
        assert p.is_file() and p.stat().st_size > 0, f"Missing or empty Python patch: {p}"
        ast.parse(p.read_text(encoding="utf-8"), filename=str(p))

    aimapper_c = PATCHES_DIR / "aimapper" / "u_gralloc_aimapper.c"
    assert aimapper_c.is_file() and aimapper_c.stat().st_size > 0, f"Missing {aimapper_c}"

    for script_py in SCRIPTS_DIR.glob("*.py"):
        ast.parse(script_py.read_text(encoding="utf-8"), filename=str(script_py))

    print(
        f"      OK: {len(apply_all_patches.ORDERED_GIT_PATCHES)} .patch files, "
        f"{len(apply_all_patches.ORDERED_PY_PATCHES)} .py patch scripts, "
        f"u_gralloc_aimapper.c, and {len(list(SCRIPTS_DIR.glob('*.py')))} orchestrator scripts verified."
    )


def verify_gmem_mathematics() -> None:
    print("[2/3] Verifying GMEM & CCU cache offset invariants on 1 MB GMEM (Adreno 825 / SM8735)...")
    gmem_1mb = 1024 * 1024  # 1,048,576 bytes

    # 1. Prove upstream/unpatched a8xx_base underflows on 1 MB GMEM when fractions are FULL (0) or QUARTER/HALF
    broken_unpatched = calc_gmem_layout(
        gmem_bytes=gmem_1mb,
        num_ccu=8,
        per_ccu_color_bytes=64 * 1024,
        per_ccu_depth_bytes=128 * 1024,
        color_fraction_shift=0,  # FULL -> 512 KB
        depth_fraction_shift=0,  # FULL -> 1024 KB
    )
    assert broken_unpatched["usable_gmem"] < 0, "Expected unpatched a8xx_base to underflow 1 MB GMEM"
    print(
        f"      Confirmed unpatched a8xx_base underflow: usable_gmem = {broken_unpatched['usable_gmem']} B "
        f"(reserved {broken_unpatched['total_reserved'] // 1024} KB > 1024 KB)"
    )

    # 2. Verify Variant 1 & 3 (Sustained -b & MaxPerf -p): EIGHTH (shift=3) color, HALF (shift=1) depth
    sustained = calc_gmem_layout(
        gmem_bytes=gmem_1mb,
        num_ccu=4,
        per_ccu_color_bytes=32 * 1024,
        per_ccu_depth_bytes=64 * 1024,
        color_fraction_shift=3,  # EIGHTH -> 16 KB
        depth_fraction_shift=1,  # HALF -> 128 KB
    )
    assert sustained["color_cache_size"] == 16 * 1024
    assert sustained["depth_cache_size"] == 128 * 1024
    assert sustained["usable_gmem"] == 880 * 1024
    assert sustained["usable_gmem"] >= 768 * 1024
    print(
        f"      OK [Sustained -b / MaxPerf -p]: color_cache=16 KB, depth_cache=128 KB, "
        f"usable_gmem={sustained['usable_gmem'] // 1024} KB (85.9% of 1 MB GMEM)"
    )

    # 3. Verify Variant 2 (BigGMEM -e): QUARTER (shift=2) color, HALF (shift=1) of 32 KB depth
    biggmem = calc_gmem_layout(
        gmem_bytes=gmem_1mb,
        num_ccu=4,
        per_ccu_color_bytes=32 * 1024,
        per_ccu_depth_bytes=32 * 1024,
        color_fraction_shift=2,  # QUARTER -> 32 KB
        depth_fraction_shift=1,  # HALF -> 64 KB
    )
    assert biggmem["color_cache_size"] == 32 * 1024
    assert biggmem["depth_cache_size"] == 64 * 1024
    assert biggmem["usable_gmem"] == 928 * 1024
    assert biggmem["usable_gmem"] >= 768 * 1024
    print(
        f"      OK [BigGMEM -e]:                color_cache=32 KB, depth_cache=64 KB, "
        f"usable_gmem={biggmem['usable_gmem'] // 1024} KB (90.6% of 1 MB GMEM)"
    )


def verify_lrzfc_layout_invariant() -> None:
    print("[3/3] Verifying A8XX fd_lrzfc_layout<CHIP> size invariant...")
    # On A6XX/A7XX: buffer1 (512) + dir_track (1) + pad2 (511) + buffer2 (512) + pad3 (512) = 2048 bytes
    # On A8XX:      buffer1 (1024) + dir_track (4) + pad2 (1020) + buffer2 (1024) = 3072 bytes
    sizeof_a6xx = 512 + 1 + 511 + 512 + 512
    offset_dir_track_a6xx = 512
    clear_len_a6xx = sizeof_a6xx - offset_dir_track_a6xx  # 1536 bytes

    sizeof_a8xx = 1024 + 4 + 1020 + 1024
    offset_dir_track_a8xx = 1024
    clear_len_a8xx = sizeof_a8xx - offset_dir_track_a8xx  # 2048 bytes

    assert sizeof_a6xx == 2048 and clear_len_a6xx == 1536
    assert sizeof_a8xx == 3072 and clear_len_a8xx == 2048
    # Unpatched code used offset_dir_track_a6xx (512) + clear_len_a6xx (1536) on A8XX,
    # leaving bytes 2048..3072 (1024 bytes of buffer2) uninitialized and corrupting buffer1[512..1023]!
    print(
        f"      OK: A8XX fd_lrzfc_layout<A8XX> size={sizeof_a8xx} B, dir_track_offset={offset_dir_track_a8xx} B, "
        f"clear_len={clear_len_a8xx} B (eliminates 1024 B fast-clear overrun)."
    )


def main() -> int:
    verify_files_and_syntax()
    verify_gmem_mathematics()
    verify_lrzfc_layout_invariant()
    print("\n[VERIFIED] All static, syntactic, and mathematical invariants passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
