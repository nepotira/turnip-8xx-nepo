# RELATÓRIO FINAL

1. Para cada PASSO 0 a 7:
- PASSO 0: OK
- PASSO 1: OK
- PASSO 2: FALHOU
  - sustained: CODIGO_SAIDA=2
  - biggmem: CODIGO_SAIDA=2
  - maxperf: CODIGO_SAIDA=2
  - switch2: CODIGO_SAIDA=2
- PASSO 3: OK
- PASSO 4: FALHOU
  - Erro: AssertionError: patches fora de sincronia: so_no_disco={'58-a8xx-conservative-rast.py', '__pycache__'} so_na_lista=set()
  - CODIGO_SAIDA=1
- PASSO 5: OK
- PASSO 6: OK
- PASSO 7: OK

2. PASSO 2:
| variante | TOTAL | OK | SKIP_ALREADY | FAIL | CODIGO_SAIDA |
| :--- | :--- | :--- | :--- | :--- | :--- |
| sustained | 36 | 33 | 1 | 2 | 2 |
| biggmem | 36 | 33 | 1 | 2 | 2 |
| maxperf | 37 | 34 | 1 | 2 | 2 |
| switch2 | 37 | 34 | 1 | 2 | 2 |

Lista dos patches que deram FAIL em cada variante:
- sustained:
  - git kgsl-syncobj-merge-ts-fd.patch: error: src/freedreno/vulkan/tu_knl_kgsl.cc: não corresponde ao índice
  - py 59-a8xx-ir3-coalesce-ubo-push-ranges.py: 59-a8xx-ir3-coalesce-ubo-push-ranges.py: WARNING anchor not found in src/freedreno/ir3/ir3_compiler.c; skipped
- biggmem:
  - git kgsl-syncobj-merge-ts-fd.patch: error: src/freedreno/vulkan/tu_knl_kgsl.cc: não corresponde ao índice
  - py 59-a8xx-ir3-coalesce-ubo-push-ranges.py: 59-a8xx-ir3-coalesce-ubo-push-ranges.py: WARNING anchor not found in src/freedreno/ir3/ir3_compiler.c; skipped
- maxperf:
  - git kgsl-syncobj-merge-ts-fd.patch: error: src/freedreno/vulkan/tu_knl_kgsl.cc: não corresponde ao índice
  - py 59-a8xx-ir3-coalesce-ubo-push-ranges.py: 59-a8xx-ir3-coalesce-ubo-push-ranges.py: WARNING anchor not found in src/freedreno/ir3/ir3_compiler.c; skipped
- switch2:
  - git kgsl-syncobj-merge-ts-fd.patch: error: src/freedreno/vulkan/tu_knl_kgsl.cc: não corresponde ao índice
  - py 59-a8xx-ir3-coalesce-ubo-push-ranges.py: 59-a8xx-ir3-coalesce-ubo-push-ranges.py: WARNING anchor not found in src/freedreno/ir3/ir3_compiler.c; skipped

3. PASSO 3:
- 3.1:
  - tu_independent_icache_miss: DEFINIDA em .scratch/mesa-src/src/freedreno/vulkan/00-turnip-defaults.conf:107 e .scratch/mesa-src/src/freedreno/common/freedreno_dev_info.h:410
  - tu_allow_oob_indirect_ubo_loads: DEFINIDA em .scratch/mesa-src/src/freedreno/vulkan/00-turnip-defaults.conf:19, 87, 98
  - tu_enable_ssbo_emulation: DEFINIDA em .scratch/mesa-src/src/freedreno/vulkan/00-turnip-defaults.conf:56, 130
  - tu_enable_fast_border_color_for_undefined_formats: DEFINIDA em .scratch/mesa-src/src/freedreno/vulkan/00-turnip-defaults.conf:26
  - tu_emulate_alpha_to_coverage: DEFINIDA em .scratch/mesa-src/src/freedreno/vulkan/00-turnip-defaults.conf:42, 104
- 3.2:
  - 289:      .KHR_shader_float16_int8 = true,
  - 292:      .KHR_shader_integer_dot_product = true,
  - 533:   features->shaderFloat16                       = true;
  - 534:   features->shaderInt8                          = true;
  - 591:   features->shaderIntegerDotProduct             = true;
  - VK_KHR_shader_float16_int8: JÁ EXISTE no upstream (linha 289)
  - VK_KHR_shader_integer_dot_product: JÁ EXISTE no upstream (linha 292)
- 3.3:
  - freedreno_devices.py:
1494:       GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810"),
1519:        GPUId(chip_id=0xffff44050000, name="Adreno (TM) 830"),
1520:        GPUId(chip_id=0xffff44050001, name="Adreno (TM) 830v1"),
1521:        GPUId(chip_id=0x44050001, name="Adreno (TM) 830"), # KGSL
1539:        GPUId(chip_id=0xffff44030a20, name="Adreno (TM) 829"),
1540:        GPUId(chip_id=0x44030a20, name="Adreno (TM) 829"), # KGSL
1562:        GPUId(chip_id=0xffff44050A31, name="Adreno (TM) 840"),
1582:        GPUId(chip_id=0xffff44050A21, name="Adreno (TM) 840"),
  - tu_knl_kgsl.cc:
1985:   device->gmem_size = debug_get_num_option("TU_GMEM", info.gmem_sizebytes);
- 3.4:
  - meson.build:
12:    'b_ndebug=if-release',
62:# This means the final value of b_ndebug==true
63:with_mesa_ndebug = get_option('b_ndebug') == 'true' or (get_option('buildtype') == 'release' and get_option('b_ndebug') == 'if-release')
83:if with_mesa_ndebug
1486:  if with_mesa_ndebug
  - .github/workflows/build-turnip.yml:
174:            -Dbuildtype=release \
- 3.5:
  - patches/ bases:
      3 Mesa base 4da08cb
      1 Rebased onto Mesa 3923c345
  - .scratch/mesa-src HEAD:
35a0fef1

4. Lista de arquivos alterados (git diff --stat main..HEAD):
 .github/workflows/build-turnip.yml |  7 ++++---
 CHANGELOG.md                       |  7 +++++++
 README.md                          | 15 +++++++++++----
 docs/AUDITORIA_MESA_REAL.md        | 78 ++++++++++++++++++++++++++++++++++++++
 docs/JOURNAL.md                    |  7 +++++++
 scripts/apply_all_patches.py       | 35 +++++++++++++++++++++++++++++++++++
 scripts/verify_patch_stack.py      | 31 +++++++++++++++++++++++++++++++
 7 files changed, 173 insertions(+), 7 deletions(-)

5. CONFIRMO: nenhum arquivo em patches/ foi alterado
