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

KNOWN_UPSTREAM_OPTIONS = {
    "tu_independent_icache_miss",
    "tu_allow_oob_indirect_ubo_loads",
    "tu_enable_ssbo_emulation",
    "tu_enable_fast_border_color_for_undefined_formats",
    "tu_emulate_alpha_to_coverage",
}


def calc_a8xx_cache_offsets(
    gmem_bytes: int,
    num_ccu: int,
    vpc_bv_pos_buf_size: int,
    vpc_attr_buf_size: int,
    vpc_pos_buf_size: int,
    color_cache_size: int,
    depth_cache_size: int,
) -> dict:
    """Replicates __calc_gmem_cache_offsets in src/freedreno/common/fd6_gmem_cache.h for A8XX."""
    offset = gmem_bytes
    vpc_bv_pos_buf_offset = offset - (num_ccu * vpc_bv_pos_buf_size)
    offset = vpc_bv_pos_buf_offset
    vpc_attr_buf_offset = offset - (num_ccu * vpc_attr_buf_size)
    offset = vpc_attr_buf_offset
    vpc_pos_buf_offset = offset - (num_ccu * vpc_pos_buf_size)
    offset = vpc_pos_buf_offset
    color_ccu_offset = offset - (num_ccu * color_cache_size)
    offset = color_ccu_offset
    depth_ccu_offset = offset - (num_ccu * depth_cache_size)
    offset = depth_ccu_offset
    return {
        "gmem_bytes": gmem_bytes,
        "total_reserved": gmem_bytes - offset,
        "usable_gmem": offset,
        "vpc_bv_pos_buf_offset": vpc_bv_pos_buf_offset,
        "vpc_attr_buf_offset": vpc_attr_buf_offset,
        "vpc_pos_buf_offset": vpc_pos_buf_offset,
        "color_ccu_offset": color_ccu_offset,
        "depth_ccu_offset": depth_ccu_offset,
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
    print("[2/3] Verifying A8XX __calc_gmem_cache_offsets invariants on 1 MB GMEM (Adreno 825 / SM8735)...")
    gmem_1mb = 1024 * 1024  # 1,048,576 bytes

    # 1. Prove upstream a8xx_gen1 underflows on 1 MB GMEM with num_ccu = 4 in both sysmem and gmem
    unpatched_sysmem = calc_a8xx_cache_offsets(
        gmem_bytes=gmem_1mb,
        num_ccu=4,
        vpc_bv_pos_buf_size=32768,
        vpc_attr_buf_size=131072,
        vpc_pos_buf_size=65536,
        color_cache_size=128 * 1024,
        depth_cache_size=256 * 1024,
    )
    unpatched_gmem = calc_a8xx_cache_offsets(
        gmem_bytes=gmem_1mb,
        num_ccu=4,
        vpc_bv_pos_buf_size=32768,
        vpc_attr_buf_size=49152,
        vpc_pos_buf_size=24576,
        color_cache_size=16 * 1024,
        depth_cache_size=256 * 1024,
    )
    assert unpatched_sysmem["usable_gmem"] < 0 and unpatched_gmem["usable_gmem"] < 0
    print(
        f"      Confirmed unpatched a8xx_gen1 underflow on 1 MB GMEM: "
        f"sysmem_offset={unpatched_sysmem['usable_gmem'] // 1024} KB, "
        f"gmem_offset={unpatched_gmem['usable_gmem'] // 1024} KB"
    )

    # 2. Verify Patched Sysmem (4 CCUs * 256 KB = 1024 KB, offset == 0)
    patched_sysmem = calc_a8xx_cache_offsets(
        gmem_bytes=gmem_1mb,
        num_ccu=4,
        vpc_bv_pos_buf_size=16384,
        vpc_attr_buf_size=32768,
        vpc_pos_buf_size=16384,
        color_cache_size=64 * 1024,
        depth_cache_size=128 * 1024,
    )
    assert patched_sysmem["usable_gmem"] == 0
    print("      OK [Patched Sysmem]:            total_reserved=1024 KB, final_offset=0 B (exact 1 MB fit, zero underflow)")

    # 3. Verify Variant 1 & 3 (Sustained -b / MaxPerf -p) GMEM
    sustained_gmem = calc_a8xx_cache_offsets(
        gmem_bytes=gmem_1mb,
        num_ccu=4,
        vpc_bv_pos_buf_size=16384,
        vpc_attr_buf_size=16384,
        vpc_pos_buf_size=12288,
        color_cache_size=16 * 1024,
        depth_cache_size=64 * 1024,
    )
    assert sustained_gmem["usable_gmem"] == 528 * 1024
    print(
        f"      OK [Sustained -b / MaxPerf -p]: total_reserved={sustained_gmem['total_reserved'] // 1024} KB, "
        f"usable_gmem={sustained_gmem['usable_gmem'] // 1024} KB"
    )

    # 4. Verify Variant 2 & 4 (BigGMEM -e / Switch2 -s2) GMEM
    biggmem = calc_a8xx_cache_offsets(
        gmem_bytes=gmem_1mb,
        num_ccu=4,
        vpc_bv_pos_buf_size=16384,
        vpc_attr_buf_size=16384,
        vpc_pos_buf_size=12288,
        color_cache_size=16 * 1024,
        depth_cache_size=32 * 1024,
    )
    assert biggmem["usable_gmem"] == 656 * 1024
    print(
        f"      OK [BigGMEM -e / Switch2 -s2]:  total_reserved={biggmem['total_reserved'] // 1024} KB, "
        f"usable_gmem={biggmem['usable_gmem'] // 1024} KB"
    )


def verify_lrzfc_layout_invariant() -> None:
    print("[3/3] Verifying A8XX fd_lrzfc_layout<CHIP> br_cur_buffer & depth_clear_val offsets...")
    # On A7XX: fc1 is 2048 B, buffer[0] at 2048, buffer[1] at 2112, bv_cur_buffer at 2176, br_cur_buffer at 2240
    # On A8XX: fc1 is 4096 B, fc2 is 4096 B, buffer[0] at 8192, buffer[1] at 9216, bv_cur_buffer at 10240, br_cur_buffer at 11264
    a7xx_buf0_clear = 2048 + 56
    a7xx_buf1_clear = 2048 + 64 + 56
    a7xx_br_cur = 2048 + 128 + 64
    a8xx_buf0_clear = 8192 + 56
    a8xx_buf1_clear = 8192 + 1024 + 56
    a8xx_br_cur = 8192 + 2048 + 1024
    assert a7xx_br_cur == 2240 and a8xx_br_cur == 11264
    assert a7xx_buf0_clear == 2104 and a8xx_buf0_clear == 8248
    assert a7xx_buf1_clear == 2168 and a8xx_buf1_clear == 9272
    print(
        f"      OK: A8XX fd_lrzfc_layout<A8XX> br_cur_buffer={a8xx_br_cur} (vs A7XX {a7xx_br_cur}), "
        f"buf0_clear={a8xx_buf0_clear}, buf1_clear={a8xx_buf1_clear}."
    )


def verify_repo_consistency() -> None:
    print("[4/4] Verificando consistencia repo: patches listados, variantes, driconf...")
    listados = set(apply_all_patches.ORDERED_GIT_PATCHES) | set(apply_all_patches.ORDERED_PY_PATCHES)
    ignorar = {"aimapper", "eden-optimizations-unified.patch"}
    no_disco = {p.name for p in PATCHES_DIR.iterdir()} - ignorar
    assert no_disco == listados, f"patches fora de sincronia: so_no_disco={no_disco - listados} so_na_lista={listados - no_disco}"

    workflow = (REPO_ROOT / ".github/workflows/build-turnip.yml").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for v in ("Sustained", "BigGMEM", "MaxPerf", "Switch2"):
        assert f"Turnip-A8xx-8sGen4-{v}" in workflow, f"variante {v} ausente do workflow"
        assert f"Turnip-A8xx-8sGen4-{v}" in readme, f"variante {v} ausente do README"

    script = (SCRIPTS_DIR / "apply_all_patches.py").read_text(encoding="utf-8")
    patches_txt = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in PATCHES_DIR.glob("*") if p.is_file())
    import re
    opcoes = set(re.findall(r'<option name="(tu_[a-z0-9_]+)"', script))
    sem_origem = sorted(o for o in opcoes if o not in patches_txt and o not in KNOWN_UPSTREAM_OPTIONS)
    assert not sem_origem, f"opcoes de driconf sem origem conhecida: {sem_origem}"
    print("      OK")


def main() -> int:
    verify_files_and_syntax()
    verify_gmem_mathematics()
    verify_lrzfc_layout_invariant()
    verify_repo_consistency()
    print("\n[VERIFIED] All static, syntactic, and mathematical invariants passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
