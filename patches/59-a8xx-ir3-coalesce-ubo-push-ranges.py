#!/usr/bin/env python3
"""A8XX: Enable UBO push range coalescing for Adreno 825 and 829.

Upstream only enabled coalesce_ubo_push_ranges for Adreno 810 (0xffff44010000ull).
Extending it to Adreno 825 (0x44030000 / 0xffff44030000) and Adreno 829 allows the
compiler to spend extra constant-file slots to fuse nearby UBO ranges, cutting down
external memory reads across the 3200 MHz LPDDR5X DRAM bus.

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "59-a8xx-ir3-coalesce-ubo-push-ranges.py"
TARGET = "src/freedreno/ir3/ir3_compiler.c"
MARKER = "0x44030000ull"

OLD = "   compiler->coalesce_ubo_push_ranges = dev_id->chip_id == 0xffff44010000ull;\n"
NEW = (
    "   compiler->coalesce_ubo_push_ranges =\n"
    "      dev_id->chip_id == 0xffff44010000ull ||\n"
    "      dev_id->chip_id == 0x44010000ull ||\n"
    "      dev_id->chip_id == 0x44030000ull ||\n"
    "      dev_id->chip_id == 0xffff44030000ull ||\n"
    "      dev_id->chip_id == 0x44030a20ull ||\n"
    "      dev_id->chip_id == 0xffff44030a20ull;\n"
)


def main():
    try:
        content = open(TARGET, "r", encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
        return 0

    if MARKER in content:
        print(f"{NAME}: already applied ({MARKER} present)")
        return 0

    if OLD not in content:
        print(f"{NAME}: WARNING anchor not found in {TARGET}; skipped")
        return 0

    try:
        with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace(OLD, NEW, 1))
    except OSError as e:
        print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
        return 1

    print(f"{NAME}: applied (UBO push range coalescing enabled for A825 & A829)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
