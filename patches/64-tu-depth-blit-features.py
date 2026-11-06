#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A8XX: Advertise BLIT_SRC and BLIT_DST features for depth/stencil formats in Turnip.

Resolves the 64,910 BlitScaleHelper errors and depth buffer upscale failures in Switch
emulators (e.g. Nyushu, Eden, Citron, Yuzu, Sudachi, Suyu) when running at 2160p (4K / 3X scale):
- Turnip already implements shader and hardware depth blitting in tu_clear_blit.cc,
  but previously only advertised VK_FORMAT_FEATURE_2_DEPTH_STENCIL_ATTACHMENT_BIT in tu_formats.cc.
- By adding VK_FORMAT_FEATURE_2_BLIT_SRC_BIT and VK_FORMAT_FEATURE_2_BLIT_DST_BIT to optimal
  features for depth formats, emulators can scale depth attachments to 2160p alongside color
  targets, eliminating the ~65% unrendered black screen and specular white-out glitches.

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys
from pathlib import Path

NAME = "64-tu-depth-blit-features.py"
TARGET = "src/freedreno/vulkan/tu_formats.cc"
MARKER = "/* Depth/stencil attachment and scaling blit features */"

OLD = (
    "   linear = optimal;\n"
    "   if (tu6_pipe2depth(vk_format) != DEPTH6_NONE)\n"
    "      optimal |= VK_FORMAT_FEATURE_2_DEPTH_STENCIL_ATTACHMENT_BIT;\n"
)

NEW = (
    "   linear = optimal;\n"
    "   if (tu6_pipe2depth(vk_format) != DEPTH6_NONE) {\n"
    "      /* Depth/stencil attachment and scaling blit features */\n"
    "      optimal |= VK_FORMAT_FEATURE_2_DEPTH_STENCIL_ATTACHMENT_BIT |\n"
    "                 VK_FORMAT_FEATURE_2_BLIT_SRC_BIT |\n"
    "                 VK_FORMAT_FEATURE_2_BLIT_DST_BIT;\n"
    "   }\n"
)


def main():
    path = Path(TARGET)
    if not path.is_file():
        print(f"{NAME}: WARNING: {TARGET} not found; skipped")
        return 0

    content = path.read_text(encoding="utf-8")
    if MARKER in content:
        print(f"{NAME}: already applied in {TARGET}")
        return 0

    if OLD not in content:
        print(f"{NAME}: ERROR: expected target snippet not found in {TARGET}", file=sys.stderr)
        return 1

    updated = content.replace(OLD, NEW, 1)
    path.write_text(updated, encoding="utf-8")
    print(f"{NAME}: successfully applied depth blit features to {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
