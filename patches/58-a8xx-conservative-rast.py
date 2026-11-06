#!/usr/bin/env python3
"""A8XX: Safety guard ensuring conservative rasterization binning remains disabled on A8XX.

Conservative rasterization binning (tu_binning_conservative_rast) on Adreno 8xx
clips the tile bounding box to the internal 720p resolution, leaving 65% of the
screen black on 2400x1080 displays in Switch emulators (e.g. Nyushu). This script
ensures upstream 'CHIP == A7XX' is strictly preserved.

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "58-a8xx-conservative-rast.py"
TARGET = "src/freedreno/vulkan/tu_pipeline.cc"
BAD = "   return CHIP >= A7XX && fdm && !TU_DRIRC(dev, misc.disable_conservative_fdm_binning);\n"
GOOD = "   return CHIP == A7XX && fdm && !TU_DRIRC(dev, misc.disable_conservative_fdm_binning);\n"


def main():
    try:
        content = open(TARGET, "r", encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
        return 0

    if BAD in content:
        content = content.replace(BAD, GOOD, 1)
        try:
            with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            print(f"{NAME}: reverted (conservative binning disabled on A8XX to fix 65% black cutoff)")
            return 0
        except OSError as e:
            print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
            return 1

    print(f"{NAME}: safe (conservative binning disabled on A8XX)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
