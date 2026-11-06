#!/usr/bin/env python3
"""A8XX: Enable conservative rasterization binning for fragment density maps / VRS.

Upstream only enabled conservative rasterization binning on A7XX (CHIP == A7XX),
missing A8XX. This patch extends the check to CHIP >= A7XX so Adreno 8xx GPUs
benefit from reduced vertex processing on variable rate shading / FDM render passes.

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "58-a8xx-conservative-rast.py"
TARGET = "src/freedreno/vulkan/tu_pipeline.cc"
MARKER = "CHIP >= A7XX && fdm && !TU_DRIRC(dev, misc.disable_conservative_fdm_binning)"

OLD = "   return CHIP == A7XX && fdm && !TU_DRIRC(dev, misc.disable_conservative_fdm_binning);\n"
NEW = "   return CHIP >= A7XX && fdm && !TU_DRIRC(dev, misc.disable_conservative_fdm_binning);\n"


def main():
    try:
        content = open(TARGET, "r", encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
        return 0

    if MARKER in content:
        print(f"{NAME}: already applied ({MARKER} present)")
        return 0

    found = content.count(OLD)
    if found != 1:
        print(f"{NAME}: WARNING anchor matched {found}x (want 1) in {TARGET}; skipped")
        return 0

    try:
        with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace(OLD, NEW, 1))
    except OSError as e:
        print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
        return 1

    print(f"{NAME}: applied (conservative rasterization binning enabled for A8XX)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
