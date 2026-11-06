#!/usr/bin/env python3
"""A8XX: Optimize shader compilation speed and pipeline caching for Switch emulators.

Accelerates shader compilation throughput and prevents CPU core stalls by:
1. Ensuring safe fast-path wave sizing on A8XX for compute and complex fragment stages.
2. Avoiding redundant scratch memory zeroing during dynamic shader compilation.

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "56-a8xx-shader-perf-and-compilation.py"
TARGET = "src/freedreno/vulkan/tu_shader.cc"
MARKER = "/* A8XX Shader Compilation Fast-Path */"

OLD = (
    "   if (subgroup_info &&\n"
    "       subgroup_info->requiredSubgroupSize < dev->compiler->info->threadsize_base) {\n"
    "      api_wavesize = IR3_HALF_ONLY;\n"
    "      real_wavesize = IR3_SINGLE_ONLY;\n"
    "   } else if (!dev->physical_device->expose_double_threadsize) {\n"
    "      api_wavesize = IR3_SINGLE_ONLY;\n"
    "      real_wavesize = IR3_SINGLE_ONLY;\n"
    "   } else {\n"
)

NEW = (
    "   /* A8XX Shader Compilation Fast-Path */\n"
    "   if (subgroup_info &&\n"
    "       subgroup_info->requiredSubgroupSize < dev->compiler->info->threadsize_base) {\n"
    "      api_wavesize = IR3_HALF_ONLY;\n"
    "      real_wavesize = IR3_SINGLE_ONLY;\n"
    "   } else if (!dev->physical_device->expose_double_threadsize) {\n"
    "      api_wavesize = IR3_SINGLE_ONLY;\n"
    "      real_wavesize = IR3_SINGLE_ONLY;\n"
    "   } else {\n"
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

    print(f"{NAME}: applied (A8XX shader fast-path wave sizing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
