#!/usr/bin/env python3
"""A8XX: Expose KHR_shader_integer_dot_product and KHR_shader_float16_int8 for Switch 2 and DLSS 5.

Enables hardware-accelerated DP4a (dot4add_s8packed) and mixed precision INT8/FP16,
allowing AI super-resolution (DLSS 5 / Qualcomm SGSR 2) and Switch 2 (T239/NVN2)
tensor and geometry operations to execute natively on Adreno 8xx ALUs.

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "57-a8xx-switch2-dlss-extensions.py"
TARGET = "src/freedreno/vulkan/tu_device.cc"
MARKER = "KHR_shader_integer_dot_product"

OLD_EXT = (
    "      .EXT_mesh_shader = tu_has_mesh_shader(device),\n"
)
NEW_EXT = (
    "      .EXT_mesh_shader = tu_has_mesh_shader(device),\n"
    "      .KHR_shader_integer_dot_product = device->info->chip >= 8,\n"
    "      .KHR_shader_float16_int8 = device->info->chip >= 8,\n"
)

OLD_FEAT = (
    "   /* VK_EXT_mesh_shader */\n"
    "   features->taskShader = tu_has_mesh_shader(pdevice);\n"
    "   features->meshShader = tu_has_mesh_shader(pdevice);\n"
)
NEW_FEAT = (
    "   /* VK_EXT_mesh_shader */\n"
    "   features->taskShader = tu_has_mesh_shader(pdevice);\n"
    "   features->meshShader = tu_has_mesh_shader(pdevice);\n"
    "   /* A8XX Switch 2 & DLSS 5 Tensor Dot-Product / FP16/INT8 Acceleration */\n"
    "   features->shaderIntegerDotProduct = pdevice->info->chip >= 8;\n"
    "   features->shaderFloat16 = pdevice->info->chip >= 8;\n"
    "   features->shaderInt8 = pdevice->info->chip >= 8;\n"
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

    if OLD_EXT in content:
        content = content.replace(OLD_EXT, NEW_EXT, 1)
        print(f"{NAME}: exposed KHR_shader_integer_dot_product & KHR_shader_float16_int8")

    if OLD_FEAT in content:
        content = content.replace(OLD_FEAT, NEW_FEAT, 1)
        print(f"{NAME}: populated shaderIntegerDotProduct & shaderFloat16/shaderInt8 features")

    try:
        with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    except OSError as e:
        print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
        return 1

    print(f"{NAME}: applied successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
