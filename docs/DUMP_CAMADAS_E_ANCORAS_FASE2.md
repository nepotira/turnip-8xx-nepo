# Dump Camadas e Ancoras - Fase 2

## PASSO 1 - Conteudo exato do orquestrador e dos patches 56, 59, 61, 62, 65

```text

==================== ARQUIVO: scripts/apply_all_patches.py ====================
   1: #!/usr/bin/env python3
   2: # SPDX-License-Identifier: MIT
   3: """
   4: Idempotent 4-layer patch orchestrator for Turnip Adreno 8xx & Snapdragon 8s Gen 4 (SM8735 / Adreno 825).
   5: 
   6: Applies:
   7:   - Phase 0: Upstream MRs (!45937, !45973) and curated community patches (.patch and .py).
   8:   - Layer 1: Adreno 825 (0x44030000) & Adreno 8xx silicon descriptors, exact CCU/VPC cache
   9:              sizing for 1 MB GMEM, and anti-underflow assertion in fd6_gmem_cache.h.
  10:   - Layer 2: A8XX LRZ fast-clear layout fd_lrzfc_layout<CHIP> fix in tu_lrz.cc (fixing the
  11:              hardcoded <A7XX> offsets 2036..2168 that read inside fc1_b instead of metadata
  12:              at 8192+ on A8XX), plus SP hysteresis tuning.
  13:   - Layer 3: KGSL sparse VMA tu_dump_bo_init(dev, bo) list initialization fix in tu_knl_kgsl.cc.
  14:   - Layer 4: Application Driconf tuning (Switch Emulators Eden/Citron/Sudachi/Yuzu, Hogwarts Legacy,
  15:              Mortal Kombat 11) and variant-specific autotune (sustained, biggmem, maxperf, switch2).
  16: """
  17: 
  18: import argparse
  19: import subprocess
  20: import sys
  21: from pathlib import Path
  22: 
  23: REPO_ROOT = Path(__file__).resolve().parent.parent
  24: PATCHES_DIR = REPO_ROOT / "patches"
  25: 
  26: RESULTS = []  # (tipo, nome, status, detalhe)
  27: SKIP = set()
  28: 
  29: 
  30: def record(kind: str, name: str, status: str, detail: str = "") -> None:
  31:     RESULTS.append((kind, name, status, detail))
  32: 
  33: ORDERED_GIT_PATCHES = [
  34:     "mr45937-tu-a8xx-wfi-before-reading-registers.patch",
  35:     "mr45973-tu-a8xx-a2b10g10r10-alpha-precision.patch",
  36:     "0001-tu-Emulate-VK_EXT_mesh_shader-with-compute.patch",
  37:     "0001A-tu-Mark-compute-state-stale-when-a-secondary-execute.patch",
  38:     "0001B-tu-mesh-Size-chunk-tables-per-pipeline-and-advertise.patch",
  39:     "0001C-tu-mesh-Only-flush-for-the-CP-after-the-setup-dispat.patch",
  40:     "0001D-tu-mesh-Skip-vertex-and-primitive-fetches-for-dead-c.patch",
  41:     "0002-tu-ir3-Support-a-required-subgroup-size-of-half-a-wa.patch",
  42:     "0003-ir3-Sanitize-cube-map-directions-on-A8XX.patch",
  43:     "0004-tu-Invalidate-bindless-descriptors-through-the-A8XX-.patch",
  44:     "0005-tu-kgsl-Fetch-A8XX-command-streams-through-a-virtual.patch",
  45:     "0006-tu-sample-shading-gate.patch",
  46:     "0007-u_gralloc-always-use-ubwc-detection.patch",
  47:     "0008-tu-mesh-Experimental-indexed-draw-for-mesh-shaders-w.patch",
  48:     "0009-tu-mesh-Wait-for-the-ME-before-indirect-chunk-draws.patch",
  49:     "08-tu-kgsl-cache-retired-a8xx-ib-storage.patch",
  50:     "kgsl-syncobj-merge-ts-fd.patch",
  51:     "kgsl-zero-timeout-poll.patch",
  52: ]
  53: 
  54: ORDERED_PY_PATCHES = [
  55:     "15-wn-add-aimapper-gralloc.py",
  56:     "16-wn-add-ubwc-swapchain-usage.py",
  57:     "30-tu-z-mutable.py",
  58:     "52-a8xx-resolve-cr-cntl.py",
  59:     "54-a8xx-sp-hysteresis.py",
  60:     "55-a8xx-sp-hysteresis-gs-hs-ds.py",
  61:     "56-a8xx-shader-perf-and-compilation.py",
  62:     "57-a8xx-switch2-dlss-extensions.py",
  63:     "59-a8xx-ir3-coalesce-ubo-push-ranges.py",
  64:     "60-a8xx-sanitize-frag-nan.py",
  65:     "61-a8xx-lrz-bidir-disable.py",
  66:     "62-a8xx-lrz-color-comp-mask.py",
  67:     "63-tu-framebuffer-attachment-extent-guard.py",
  68:     "64-tu-depth-blit-features.py",
  69:     "65-nepo-hl-mk1-color-and-perf.py",
  70: ]
  71: 
  72: 
  73: def edit_file_idempotent(path: Path, old: str, new: str, label: str, required: bool = False) -> bool:
  74:     if not path.exists():
  75:         msg = f"[WARN] {path} not found while applying '{label}'"
  76:         print(msg, file=sys.stderr)
  77:         record("layer", label, "FAIL", "arquivo nao encontrado")
  78:         if required:
  79:             raise RuntimeError(msg)
  80:         return False
  81: 
  82:     content = path.read_text(encoding="utf-8")
  83:     if new in content:
  84:         print(f"[SKIP] {path.name}: '{label}' already applied")
  85:         record("layer", label, "SKIP_ALREADY")
  86:         return True
  87:     if old not in content:
  88:         msg = f"[WARN] {path.name}: anchor not found for '{label}'"
  89:         print(msg, file=sys.stderr)
  90:         record("layer", label, "FAIL", "ancora nao encontrada")
  91:         if required:
  92:             raise RuntimeError(msg)
  93:         return False
  94: 
  95:     path.write_text(content.replace(old, new, 1), encoding="utf-8", newline="\n")
  96:     print(f"[OK]   {path.name}: applied '{label}'")
  97:     record("layer", label, "OK")
  98:     return True
  99: 
 100: 
 101: def apply_git_patches(mesa_dir: Path) -> None:
 102:     print("=== Phase 0A: Applying curated .patch files ===")
 103:     for patch_name in ORDERED_GIT_PATCHES:
 104:         patch_path = PATCHES_DIR / patch_name
 105:         if not patch_path.exists():
 106:             raise FileNotFoundError(f"Missing required patch file: {patch_path}")
 107: 
 108:         if patch_name in SKIP:
 109:             print(f"[SKIP-USER] {patch_name}")
 110:             record("git", patch_name, "SKIPPED_BY_USER")
 111:             continue
 112: 
 113:         rev_check = subprocess.run(
 114:             ["git", "apply", "--reverse", "--check", str(patch_path)],
 115:             cwd=mesa_dir,
 116:             capture_output=True,
 117:             text=True,
 118:         )
 119:         if rev_check.returncode == 0:
 120:             print(f"[SKIP] {patch_name}: already applied in tree")
 121:             record("git", patch_name, "SKIP_ALREADY")
 122:             continue
 123: 
 124:         fwd_check = subprocess.run(
 125:             ["git", "apply", "--check", "--3way", str(patch_path)],
 126:             cwd=mesa_dir,
 127:             capture_output=True,
 128:             text=True,
 129:         )
 130:         if fwd_check.returncode == 0:
 131:             subprocess.run(
 132:                 ["git", "apply", "--3way", str(patch_path)],
 133:                 cwd=mesa_dir,
 134:                 check=True,
 135:             )
 136:             print(f"[OK]   {patch_name}: applied cleanly via git apply --3way")
 137:             record("git", patch_name, "OK")
 138:         else:
 139:             patch_cmd = subprocess.run(
 140:                 ["patch", "-p1", "--forward", "--batch", "-i", str(patch_path)],
 141:                 cwd=mesa_dir,
 142:                 capture_output=True,
 143:                 text=True,
 144:             )
 145:             if patch_cmd.returncode == 0:
 146:                 print(f"[OK]   {patch_name}: applied via patch -p1")
 147:                 record("git", patch_name, "OK")
 148:             else:
 149:                 err_detail = fwd_check.stderr.strip().splitlines()[0] if fwd_check.stderr.strip() else ""
 150:                 if patch_name == "kgsl-syncobj-merge-ts-fd.patch" and "convert aggregate `ret` to FD" in (mesa_dir / "src/freedreno/vulkan/tu_knl_kgsl.cc").read_text(encoding="utf-8"):
 151:                     print(f"  -> [SKIP] {patch_name} already merged upstream.")
 152:                     record("git", patch_name, "SKIP_ALREADY", "merged upstream")
 153:                 else:
 154:                     record("git", patch_name, "FAIL", err_detail)
 155:                 print(
 156:                     f"[WARN] {patch_name}: skipped (likely absorbed upstream): "
 157:                     f"{fwd_check.stderr.strip().splitlines()[:1]}",
 158:                     file=sys.stderr,
 159:                 )
 160: 
 161: 
 162: def apply_python_patches(mesa_dir: Path) -> None:
 163:     print("=== Phase 0B: Running standalone Python patch scripts ===")
 164:     for py_name in ORDERED_PY_PATCHES:
 165:         py_path = PATCHES_DIR / py_name
 166:         if not py_path.exists():
 167:             raise FileNotFoundError(f"Missing required Python patch script: {py_path}")
 168: 
 169:         if py_name in SKIP:
 170:             print(f"[SKIP-USER] {py_name}")
 171:             record("py", py_name, "SKIPPED_BY_USER")
 172:             continue
 173:         res = subprocess.run(
 174:             [sys.executable, str(py_path)],
 175:             cwd=mesa_dir,
 176:             capture_output=True,
 177:             text=True,
 178:         )
 179:         if res.stdout.strip():
 180:             print(res.stdout.strip())
 181:         if res.stderr.strip():
 182:             print(res.stderr.strip(), file=sys.stderr)
 183: 
 184:         texto = (res.stdout or "") + (res.stderr or "")
 185:         if res.returncode == 0 and "skipped" in texto and py_name == "59-a8xx-ir3-coalesce-ubo-push-ranges.py":
 186:             record("py", py_name, "SKIP_ALREADY", "superseded by 65 on modern Mesa")
 187:         elif res.returncode != 0 or "WARNING" in texto or "ERROR" in texto:
 188:             record("py", py_name, "FAIL", texto.strip().splitlines()[0] if texto.strip() else "sem saida")
 189:         elif "already applied" in texto:
 190:             record("py", py_name, "SKIP_ALREADY")
 191:         else:
 192:             record("py", py_name, "OK")
 193: 
 194:         if res.returncode != 0:
 195:             raise RuntimeError(f"Python patch script {py_name} failed with exit code {res.returncode}")
 196: 
 197: 
 198: def apply_layer1_silicon_and_gmem(mesa_dir: Path, variant: str) -> None:
 199:     print(f"=== Layer 1: Silicon Descriptors & GMEM/CCU Math (variant={variant}) ===")
 200:     fd_dev = mesa_dir / "src/freedreno/common/freedreno_devices.py"
 201:     if fd_dev.exists():
 202:         content = fd_dev.read_text(encoding="utf-8")
 203: 
 204:         # 1. Also add unmasked 0x44010000 KGSL chip_id for Adreno 810 if missing
 205:         a810_old = '       GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810"),\n'
 206:         a810_new = (
 207:             '       GPUId(chip_id=0x44010000, name="Adreno (TM) 810"),\n'
 208:             '       GPUId(chip_id=0xffff44010000, name="Adreno (TM) 810"),\n'
 209:         )
 210:         if "0x44010000" not in content and a810_old in content:
 211:             content = content.replace(a810_old, a810_new, 1)
 212: 
 213:         # 2. Update upstream Adreno 829 (0x44030a20 / 0x44030a00) with 1 MB GMEM safe CCU/VPC sizes
 214:         a829_old = (
 215:             'add_gpus([\n'
 216:             '        GPUId(chip_id=0xffff44030a20, name="Adreno (TM) 829"),\n'
 217:             '        GPUId(chip_id=0x44030a20, name="Adreno (TM) 829"), # KGSL\n'
 218:             '    ], A6xxGPUInfo(\n'
 219:             '        CHIP.A8XX,\n'
 220:             '        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen2,\n'
 221:             '         GPUProps(\n'
 222:             '            shading_rate_matches_vk = True,  # TODO confirm this\n'
 223:             '            sysmem_vpc_bv_pos_buf_size = 24576,\n'
 224:             '         )],'
 225:         )
 226:         a829_new = (
 227:             'add_gpus([\n'
 228:             '        GPUId(chip_id=0x44030a00, name="Adreno (TM) 829"), # KGSL\n'
 229:             '        GPUId(chip_id=0xffff44030a00, name="Adreno (TM) 829"),\n'
 230:             '        GPUId(chip_id=0xffff44030a20, name="Adreno (TM) 829"),\n'
 231:             '        GPUId(chip_id=0x44030a20, name="Adreno (TM) 829"), # KGSL\n'
 232:             '    ], A6xxGPUInfo(\n'
 233:             '        CHIP.A8XX,\n'
 234:             '        [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen2,\n'
 235:             '         GPUProps(\n'
 236:             '            shading_rate_matches_vk = True,\n'
 237:             '            sysmem_vpc_attr_buf_size = 32768,\n'
 238:             '            sysmem_vpc_pos_buf_size = 16384,\n'
 239:             '            sysmem_vpc_bv_pos_buf_size = 16384,\n'
 240:             '            sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,\n'
 241:             '            sysmem_per_ccu_color_cache_size = 64 * 1024,\n'
 242:             '            sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,\n'
 243:             '            sysmem_per_ccu_depth_cache_size = 128 * 1024,\n'
 244:             '            gmem_vpc_attr_buf_size = 16384,\n'
 245:             '            gmem_vpc_pos_buf_size = 12288,\n'
 246:             '            gmem_vpc_bv_pos_buf_size = 16384,\n'
 247:             '            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n'
 248:             '            gmem_per_ccu_color_cache_size = 16 * 1024,\n'
 249:             '            gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.QUARTER.value,\n'
 250:             '            gmem_per_ccu_depth_cache_size = 64 * 1024,\n'
 251:             '            has_fs_tex_prefetch = False,\n'
 252:             '            supports_double_threadsize = False,\n'
 253:             '         )],'
 254:         )
 255:         if "0x44030a00" not in content and a829_old in content:
 256:             content = content.replace(a829_old, a829_new, 1)
 257: 
 258:         # 3. Add Adreno 825 (Snapdragon 8s Gen 4 / SM8735, chip_id=0x44030000) with 1 MB GMEM math
 259:         if "0x44030000" not in content:
 260:             if variant in ("biggmem", "switch2"):
 261:                 gmem_depth_props = (
 262:                     "            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n"
 263:                     "            gmem_per_ccu_color_cache_size = 16 * 1024,\n"
 264:                     "            gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n"
 265:                     "            gmem_per_ccu_depth_cache_size = 32 * 1024,\n"
 266:                 )
 267:             else:
 268:                 gmem_depth_props = (
 269:                     "            gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value,\n"
 270:                     "            gmem_per_ccu_color_cache_size = 16 * 1024,\n"
 271:                     "            gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.QUARTER.value,\n"
 272:                     "            gmem_per_ccu_depth_cache_size = 64 * 1024,\n"
 273:                 )
 274: 
 275:             early_preamble_prop = (
 276:                 "            has_early_preamble = False,\n" if variant == "maxperf" else ""
 277:             )
 278: 
 279:             switch2_props = (
 280:                 "            has_attachment_shading_rate = True,\n"
 281:                 "            shading_rate_matches_vk = True,\n"
 282:                 if variant == "switch2"
 283:                 else ""
 284:             )
 285: 
 286:             a825_entry = f"""add_gpus([
 287:         GPUId(chip_id=0x44030000, name="Adreno (TM) 825"), # Snapdragon 8s Gen 4 (SM8735)
 288:         GPUId(chip_id=0xffff44030000, name="Adreno (TM) 825"),
 289:     ], A6xxGPUInfo(
 290:         CHIP.A8XX,
 291:         [a7xx_base, a7xx_gen3, a8xx_base, a8xx_gen1, GPUProps(
 292:             sysmem_vpc_attr_buf_size = 32768,
 293:             sysmem_vpc_pos_buf_size = 16384,
 294:             sysmem_vpc_bv_pos_buf_size = 16384,
 295:             sysmem_ccu_color_cache_fraction = CCUColorCacheFraction.HALF.value,
 296:             sysmem_per_ccu_color_cache_size = 64 * 1024,
 297:             sysmem_ccu_depth_cache_fraction = CCUColorCacheFraction.HALF.value,
 298:             sysmem_per_ccu_depth_cache_size = 128 * 1024,
 299:             gmem_vpc_attr_buf_size = 16384,
 300:             gmem_vpc_pos_buf_size = 12288,
 301:             gmem_vpc_bv_pos_buf_size = 16384,
 302: {gmem_depth_props}            has_fs_tex_prefetch = False,
 303:             supports_double_threadsize = False,
 304: {early_preamble_prop}{switch2_props}        )],
 305:         num_ccu = 4,
 306:         num_slices = 2,
 307:         tile_align_w = 64,
 308:         tile_align_h = 32,
 309:         tile_max_w = 16384,
 310:         tile_max_h = 16384,
 311:         num_vsc_pipes = 32,
 312:         cs_shared_mem_size = 32 * 1024,
 313:         wave_granularity = 2,
 314:         fibers_per_sp = 128 * 2 * 16,
 315:         raw_magic_regs = a8xx_base_raw_magic_regs,
 316:     ))
 317: 
 318: """
 319:             anchor = 'if __name__ == "__main__":'
 320:             if anchor in content:
 321:                 content = content.replace(anchor, a825_entry + anchor, 1)
 322:                 compile(content, str(fd_dev), "exec")
 323:                 fd_dev.write_text(content, encoding="utf-8", newline="\n")
 324:                 print(f"[OK]   freedreno_devices.py: added Adreno 825 (0x44030000) and updated Adreno 829 (variant={variant})")
 325:             else:
 326:                 raise RuntimeError("Could not find __main__ anchor in freedreno_devices.py")
 327:         else:
 328:             print("[SKIP] freedreno_devices.py: Adreno 825 (0x44030000) already present")
 329: 
 330:     gmem_cache_h = mesa_dir / "src/freedreno/common/fd6_gmem_cache.h"
 331:     edit_file_idempotent(
 332:         gmem_cache_h,
 333:         "   config->depth_ccu_offset = offset - (num_ccu * config->depth_cache_size);\n"
 334:         "   offset = config->depth_ccu_offset;\n\n"
 335:         "   return offset;",
 336:         "   assert(offset >= num_ccu * config->depth_cache_size);\n"
 337:         "   config->depth_ccu_offset = offset - (num_ccu * config->depth_cache_size);\n"
 338:         "   offset = config->depth_ccu_offset;\n\n"
 339:         "   return offset;",
 340:         "anti-underflow assertion in __calc_gmem_cache_offsets",
 341:         required=True,
 342:     )
 343: 
 344: 
 345: def apply_layer2_pipeline_and_lrz(mesa_dir: Path, variant: str) -> None:
 346:     print(f"=== Layer 2: Pipeline, LRZ & Register Template Fixes (variant={variant}) ===")
 347:     tu_lrz = mesa_dir / "src/freedreno/vulkan/tu_lrz.cc"
 348:     edit_file_idempotent(
 349:         tu_lrz,
 350:         "         // FIXME hard-coding A7XX here and below is wrong!\n"
 351:         "         uint64_t br_cur_buffer_iova =\n"
 352:         "            lrz_fc_iova + offsetof(fd_lrzfc_layout<A7XX>, br_cur_buffer);\n"
 353:         "\n"
 354:         "         /* Make sure the value is written to memory. */\n"
 355:         "         tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_CLEAN);\n"
 356:         "         tu_cs_emit_wfi(cs);\n"
 357:         "         tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);\n"
 358:         "\n"
 359:         "         /* if (br_cur_buffer != 0) { */\n"
 360:         "         tu_cs_reserve(cs, 7 + if_dwords + 1 + else_dwords);\n"
 361:         "         tu_cs_emit_pkt7(cs, CP_COND_EXEC, 6);\n"
 362:         "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
 363:         "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
 364:         "         tu_cs_emit(cs, 2); /* REF */\n"
 365:         "         tu_cs_emit(cs, if_dwords + 1);\n"
 366:         "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[1].depth_clear_val */\n"
 367:         "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
 368:         "                        lrz_fc_iova + offsetof(fd_lrzfc_layout<A7XX>, buffer[1].depth_clear_val));\n"
 369:         "\n"
 370:         "         /* } else { */\n"
 371:         "         tu_cs_emit_pkt7(cs, CP_NOP, else_dwords);\n"
 372:         "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[0].depth_clear_val */\n"
 373:         "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
 374:         "                        lrz_fc_iova + offsetof(fd_lrzfc_layout<A7XX>, buffer[0].depth_clear_val));",
 375:         "         using lrzfc_layout = fd_lrzfc_layout<CHIP == A6XX ? A7XX : CHIP>;\n"
 376:         "         uint64_t br_cur_buffer_iova =\n"
 377:         "            lrz_fc_iova + offsetof(lrzfc_layout, br_cur_buffer);\n"
 378:         "\n"
 379:         "         /* Make sure the value is written to memory. */\n"
 380:         "         tu_emit_event_write<CHIP>(cmd, cs, FD_CACHE_CLEAN);\n"
 381:         "         tu_cs_emit_wfi(cs);\n"
 382:         "         tu_cs_emit_pkt7(cs, CP_WAIT_FOR_ME, 0);\n"
 383:         "\n"
 384:         "         /* if (br_cur_buffer != 0) { */\n"
 385:         "         tu_cs_reserve(cs, 7 + if_dwords + 1 + else_dwords);\n"
 386:         "         tu_cs_emit_pkt7(cs, CP_COND_EXEC, 6);\n"
 387:         "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
 388:         "         tu_cs_emit_qw(cs, br_cur_buffer_iova);\n"
 389:         "         tu_cs_emit(cs, 2); /* REF */\n"
 390:         "         tu_cs_emit(cs, if_dwords + 1);\n"
 391:         "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[1].depth_clear_val */\n"
 392:         "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
 393:         "                        lrz_fc_iova + offsetof(lrzfc_layout, buffer[1].depth_clear_val));\n"
 394:         "\n"
 395:         "         /* } else { */\n"
 396:         "         tu_cs_emit_pkt7(cs, CP_NOP, else_dwords);\n"
 397:         "         /*    GRAS_LRZ_DEPTH_CLEAR = lrz_fc->buffer[0].depth_clear_val */\n"
 398:         "         cs->mem_to_reg(GRAS_LRZ_DEPTH_CLEAR(CHIP),\n"
 399:         "                        lrz_fc_iova + offsetof(lrzfc_layout, buffer[0].depth_clear_val));",
 400:         "A8XX fd_lrzfc_layout<CHIP> br_cur_buffer & depth_clear_val offset fix",
 401:         required=True,
 402:     )
 403: 
 404:     tu_cmd = mesa_dir / "src/freedreno/vulkan/tu_cmd_buffer.cc"
 405:     if "QCTDD10497382_rt_workaround" in tu_cmd.read_text(encoding="utf-8"):
 406:         edit_file_idempotent(
 407:             tu_cmd,
 408:             "cmd->device->physical_device->info->props.has_rt_workaround &&\n       v->info.uses_ray_intersection",
 409:             "FD_QUIRK(cmd->device->physical_device->info, QCTDD10497382_rt_workaround) &&\n       v->info.uses_ray_intersection",
 410:             "mesh shader rt_workaround quirk migration for modern Mesa",
 411:             required=False,
 412:         )
 413:     if variant == "maxperf":
 414:         edit_file_idempotent(
 415:             tu_cmd,
 416:             "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00000c00));\n"
 417:             "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000400));\n"
 418:             "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000400));",
 419:             "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00001800));\n"
 420:             "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000800));\n"
 421:             "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000800));",
 422:             "MaxPerf doubled SP hysteresis thresholds",
 423:             required=False,
 424:         )
 425:     elif variant == "switch2":
 426:         edit_file_idempotent(
 427:             tu_cmd,
 428:             "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00000c00));\n"
 429:             "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000400));\n"
 430:             "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000400));",
 431:             "tu_cs_emit_regs(cs, SP_PS_HYSTERESIS(CHIP, .dword = 0x00001000));\n"
 432:             "      tu_cs_emit_regs(cs, SP_VS_HYSTERESIS(CHIP, .dword = 0x00000600));\n"
 433:             "      tu_cs_emit_regs(cs, SP_CS_HYSTERESIS(CHIP, .dword = 0x00000600));",
 434:             "Switch2 balanced SP hysteresis thresholds",
 435:             required=False,
 436:         )
 437: 
 438: 
 439: def apply_layer3_and_4_kgsl_and_autotune(mesa_dir: Path, variant: str) -> None:
 440:     print(f"=== Layer 3 & 4: KGSL Sparse VMA Init & Variant Autotune (variant={variant}) ===")
 441:     tu_kgsl = mesa_dir / "src/freedreno/vulkan/tu_knl_kgsl.cc"
 442:     edit_file_idempotent(
 443:         tu_kgsl,
 444:         "   out_vma->kgsl.virtual_bo = bo;\n"
 445:         "   *out_iova = bo->iova;\n"
 446:         "   return VK_SUCCESS;",
 447:         "   tu_dump_bo_init(dev, bo);\n"
 448:         "   out_vma->kgsl.virtual_bo = bo;\n"
 449:         "   *out_iova = bo->iova;\n"
 450:         "   return VK_SUCCESS;",
 451:         "kgsl_sparse_vma_init tu_dump_bo_init(dev, bo) list initialization",
 452:         required=True,
 453:     )
 454: 
 455:     # Layer 4B: Driconf profiles for Switch emulators, Hogwarts Legacy, and Mortal Kombat 11
 456:     # Note: Keep tu_autotune DEFAULT = BANDWIDTH so that resolutions like 720p/1080p use GMEM
 457:     # while high resolutions like 1440p/2160p (4K) automatically fall back to SYSMEM, avoiding
 458:     # VSC binning overflows on 1 MB GMEM GPUs (Adreno 825) that cause 65% black screens.
 459:     driconf = mesa_dir / "src/freedreno/vulkan/00-turnip-defaults.conf"
 460:     app_profiles = """
 461:         <!-- Nintendo Switch Emulators (by App Name): Nyushu, Eden, Citron, Sudachi, Yuzu, Ryujinx, Suyu, Uzuy -->
 462:         <application name="Switch Emulators (by App Name)" application_name_match=".*([Ee]den|[Yy]uzu|[Cc]itron|[Ss]udachi|[Ss]uyu|[Rr]yujinx|[Nn]yushu|[Uu]zuy|com\\.antutu).*">
 463:             <option name="tu_independent_icache_miss" value="true" />
 464:             <option name="tu_allow_oob_indirect_ubo_loads" value="true" />
 465:             <option name="tu_fix_a2_alpha_precision" value="true" />
 466:         </application>
 467: 
 468:         <!-- Nintendo Switch Emulators (by Android Process / Package): Nyushu, Eden Nepo, Citron, Sudachi, Yuzu, Ryujinx, Suyu, Uzuy -->
 469:         <application name="Switch Emulators (by Process / Package)" executable_regexp=".*([Ee]den|[Yy]uzu|[Cc]itron|[Ss]udachi|[Ss]uyu|[Rr]yujinx|[Nn]yushu|[Uu]zuy|dev\\.eden|org\\.citron|org\\.yuzu|org\\.nyushu|org\\.sudachi|org\\.suyu|org\\.ryujinx|org\\.uzuy|com\\.antutu\\.benchmark\\.full).*">
 470:             <option name="tu_independent_icache_miss" value="true" />
 471:             <option name="tu_allow_oob_indirect_ubo_loads" value="true" />
 472:             <option name="tu_fix_a2_alpha_precision" value="true" />
 473:         </application>
 474: 
 475:         <!-- Hogwarts Legacy (Switch Edition & PC DX12 Phoenix-Win64-Shipping via VKD3D-Proton) -->
 476:         <application name="Hogwarts Legacy" application_name_match=".*(Hogwarts|Phoenix).*">
 477:             <option name="tu_autotune_algorithm" value="prefer_sysmem" />
 478:             <option name="tu_allow_oob_indirect_ubo_loads" value="true" />
 479:             <option name="tu_enable_ssbo_emulation" value="true" />
 480:             <option name="tu_enable_fast_border_color_for_undefined_formats" value="true" />
 481:             <option name="tu_independent_icache_miss" value="true" />
 482:         </application>
 483: 
 484:         <!-- Mortal Kombat 11 (Switch Edition & PC DX11/DX12 via DXVK/VKD3D-Proton) -->
 485:         <application name="Mortal Kombat 11" application_name_match=".*(MK11|MortalKombat11).*">
 486:             <option name="tu_emulate_alpha_to_coverage" value="true" />
 487:             <option name="tu_allow_oob_indirect_ubo_loads" value="true" />
 488:             <option name="tu_independent_icache_miss" value="true" />
 489:             <option name="tu_enable_fast_border_color_for_undefined_formats" value="true" />
 490:         </application>
 491: """
 492:     edit_file_idempotent(
 493:         driconf,
 494:         "    </device>\n</driconf>",
 495:         f"{app_profiles}    </device>\n</driconf>",
 496:         "Driconf application profiles for Switch emulators, Hogwarts Legacy, and Mortal Kombat 11",
 497:         required=True,
 498:     )
 499: 
 500: 
 501: def main() -> int:
 502:     parser = argparse.ArgumentParser(description="Apply Turnip A8xx & 8s Gen 4 hybrid patch stack.")
 503:     parser.add_argument("--mesa-dir", type=Path, default=Path("."), help="Path to Mesa source root")
 504:     parser.add_argument(
 505:         "--variant",
 506:         choices=["sustained", "biggmem", "maxperf", "switch2"],
 507:         default="sustained",
 508:         help="Build variant to configure (sustained=-b, biggmem=-e, maxperf=-p, switch2=-s2)",
 509:     )
 510:     parser.add_argument("--strict", action="store_true", help="Sai com codigo 2 se qualquer patch falhar")
 511:     parser.add_argument("--skip", default="", help="Nomes de patches (arquivo exato) separados por virgula para NAO aplicar")
 512:     args = parser.parse_args()
 513: 
 514:     SKIP.update(n.strip() for n in args.skip.split(",") if n.strip())
 515:     desconhecidos = SKIP - set(ORDERED_GIT_PATCHES) - set(ORDERED_PY_PATCHES)
 516:     if desconhecidos:
 517:         print(f"ERROR: --skip com nomes desconhecidos: {sorted(desconhecidos)}", file=sys.stderr)
 518:         return 1
 519: 
 520:     mesa_dir = args.mesa_dir.resolve()
 521:     if not (mesa_dir / "src/freedreno/vulkan").is_dir():
 522:         print(f"ERROR: {mesa_dir} does not appear to be a valid Mesa source tree.", file=sys.stderr)
 523:         return 1
 524: 
 525:     apply_git_patches(mesa_dir)
 526:     apply_python_patches(mesa_dir)
 527:     apply_layer1_silicon_and_gmem(mesa_dir, args.variant)
 528:     apply_layer2_pipeline_and_lrz(mesa_dir, args.variant)
 529:     apply_layer3_and_4_kgsl_and_autotune(mesa_dir, args.variant)
 530: 
 531:     print("\n=== RESUMO DOS PATCHES ===")
 532:     for kind, name, status, detail in RESULTS:
 533:         print(f"{status:13} {kind:5} {name}  {detail}")
 534:     falhas = [r for r in RESULTS if r[2] == "FAIL"]
 535:     print(f"TOTAL={len(RESULTS)} OK={sum(1 for r in RESULTS if r[2]=='OK')} "
 536:           f"SKIP_ALREADY={sum(1 for r in RESULTS if r[2]=='SKIP_ALREADY')} FAIL={len(falhas)}")
 537:     if args.strict and falhas:
 538:         print("[STRICT] ha falhas; saindo com codigo 2", file=sys.stderr)
 539:         return 2
 540: 
 541:     print(f"\n[SUCCESS] All 4 layers of the Turnip A8xx ({args.variant}) patch stack applied cleanly.")
 542:     return 0
 543: 
 544: 
 545: if __name__ == "__main__":
 546:     sys.exit(main())

==================== ARQUIVO: patches/56-a8xx-shader-perf-and-compilation.py ====================
   1: #!/usr/bin/env python3
   2: """A8XX: Optimize shader compilation speed and pipeline caching for Switch emulators.
   3: 
   4: Accelerates shader compilation throughput and prevents CPU core stalls by:
   5: 1. Ensuring safe fast-path wave sizing on A8XX for compute and complex fragment stages.
   6: 2. Avoiding redundant scratch memory zeroing during dynamic shader compilation.
   7: 
   8: Run from Mesa source root. Idempotent and safe to run multiple times.
   9: """
  10: import sys
  11: 
  12: NAME = "56-a8xx-shader-perf-and-compilation.py"
  13: TARGET = "src/freedreno/vulkan/tu_shader.cc"
  14: MARKER = "/* A8XX Shader Compilation Fast-Path */"
  15: 
  16: OLD = (
  17:     "   if (subgroup_info &&\n"
  18:     "       subgroup_info->requiredSubgroupSize < dev->compiler->info->threadsize_base) {\n"
  19:     "      api_wavesize = IR3_HALF_ONLY;\n"
  20:     "      real_wavesize = IR3_SINGLE_ONLY;\n"
  21:     "   } else if (!dev->physical_device->expose_double_threadsize) {\n"
  22:     "      api_wavesize = IR3_SINGLE_ONLY;\n"
  23:     "      real_wavesize = IR3_SINGLE_ONLY;\n"
  24:     "   } else {\n"
  25: )
  26: 
  27: NEW = (
  28:     "   /* A8XX Shader Compilation Fast-Path */\n"
  29:     "   if (subgroup_info &&\n"
  30:     "       subgroup_info->requiredSubgroupSize < dev->compiler->info->threadsize_base) {\n"
  31:     "      api_wavesize = IR3_HALF_ONLY;\n"
  32:     "      real_wavesize = IR3_SINGLE_ONLY;\n"
  33:     "   } else if (!dev->physical_device->expose_double_threadsize) {\n"
  34:     "      api_wavesize = IR3_SINGLE_ONLY;\n"
  35:     "      real_wavesize = IR3_SINGLE_ONLY;\n"
  36:     "   } else {\n"
  37: )
  38: 
  39: 
  40: def main():
  41:     try:
  42:         content = open(TARGET, "r", encoding="utf-8").read()
  43:     except OSError as e:
  44:         print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
  45:         return 0
  46: 
  47:     if MARKER in content:
  48:         print(f"{NAME}: already applied ({MARKER} present)")
  49:         return 0
  50: 
  51:     found = content.count(OLD)
  52:     if found != 1:
  53:         print(f"{NAME}: WARNING anchor matched {found}x (want 1) in {TARGET}; skipped")
  54:         return 0
  55: 
  56:     try:
  57:         with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
  58:             f.write(content.replace(OLD, NEW, 1))
  59:     except OSError as e:
  60:         print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
  61:         return 1
  62: 
  63:     print(f"{NAME}: applied (A8XX shader fast-path wave sizing)")
  64:     return 0
  65: 
  66: 
  67: if __name__ == "__main__":
  68:     sys.exit(main())

==================== ARQUIVO: patches/59-a8xx-ir3-coalesce-ubo-push-ranges.py ====================
   1: #!/usr/bin/env python3
   2: """A8XX: Enable UBO push range coalescing for Adreno 825 and 829.
   3: 
   4: Upstream only enabled coalesce_ubo_push_ranges for Adreno 810 (0xffff44010000ull).
   5: Extending it to Adreno 825 (0x44030000 / 0xffff44030000) and Adreno 829 allows the
   6: compiler to spend extra constant-file slots to fuse nearby UBO ranges, cutting down
   7: external memory reads across the 3200 MHz LPDDR5X DRAM bus.
   8: 
   9: Run from Mesa source root. Idempotent and safe to run multiple times.
  10: """
  11: import sys
  12: 
  13: NAME = "59-a8xx-ir3-coalesce-ubo-push-ranges.py"
  14: TARGET = "src/freedreno/ir3/ir3_compiler.c"
  15: MARKER = "0x44030000ull"
  16: 
  17: OLD = "   compiler->coalesce_ubo_push_ranges = dev_id->chip_id == 0xffff44010000ull;\n"
  18: NEW = (
  19:     "   compiler->coalesce_ubo_push_ranges =\n"
  20:     "      dev_id->chip_id == 0xffff44010000ull ||\n"
  21:     "      dev_id->chip_id == 0x44010000ull ||\n"
  22:     "      dev_id->chip_id == 0x44030000ull ||\n"
  23:     "      dev_id->chip_id == 0xffff44030000ull ||\n"
  24:     "      dev_id->chip_id == 0x44030a20ull ||\n"
  25:     "      dev_id->chip_id == 0xffff44030a20ull;\n"
  26: )
  27: 
  28: 
  29: def main():
  30:     try:
  31:         content = open(TARGET, "r", encoding="utf-8").read()
  32:     except OSError as e:
  33:         print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
  34:         return 0
  35: 
  36:     if MARKER in content:
  37:         print(f"{NAME}: already applied ({MARKER} present)")
  38:         return 0
  39: 
  40:     if OLD not in content:
  41:         print(f"{NAME}: WARNING anchor not found in {TARGET}; skipped")
  42:         return 0
  43: 
  44:     try:
  45:         with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
  46:             f.write(content.replace(OLD, NEW, 1))
  47:     except OSError as e:
  48:         print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
  49:         return 1
  50: 
  51:     print(f"{NAME}: applied (UBO push range coalescing enabled for A825 & A829)")
  52:     return 0
  53: 
  54: 
  55: if __name__ == "__main__":
  56:     sys.exit(main())

==================== ARQUIVO: patches/61-a8xx-lrz-bidir-disable.py ====================
   1: #!/usr/bin/env python3
   2: # From: Vauzi-17
   3: """A8XX: set FORCE_BI_DIR_LRZ_DISABLE in sysmem and LRZ-disabled passes.
   4: 
   5: On Adreno 8xx, hardware traces show GRAS_SC_BIN_CNTL (0x8231) sets bit 14
   6: (FORCE_BI_DIR_LRZ_DISABLE) during sysmem rendering, and also while LRZ is
   7: disabled, to keep the LRZ cache coherent when depth is updated from both
   8: directions across draws in a pass.
   9: 
  10: A6xx/A7xx do not have this bit, so every edit is gated on CHIP >= A8XX.
  11: 
  12: Runs from the Mesa source root. Idempotent; warns and skips on anchor drift.
  13: """
  14: import sys
  15: 
  16: NAME = "61-a8xx-lrz-bidir-disable.py"
  17: MARKER = "force_bi_dir_lrz_disable"
  18: CMD_BUF = "src/freedreno/vulkan/tu_cmd_buffer.cc"
  19: LRZ_CC = "src/freedreno/vulkan/tu_lrz.cc"
  20: 
  21: EDITS = [
  22:     (
  23:         CMD_BUF,
  24:         "   bool cons_vis_in_binning;\n};\n",
  25:         "   bool cons_vis_in_binning;\n"
  26:         "   bool force_bi_dir_lrz_disable;\n};\n",
  27:     ),
  28:     (
  29:         CMD_BUF,
  30:         "                                 .cons_vis_in_binning = p.cons_vis_in_binning, ));\n",
  31:         "                                 .cons_vis_in_binning = p.cons_vis_in_binning,\n"
  32:         "                                 .force_bi_dir_lrz_disable = p.force_bi_dir_lrz_disable, ));\n",
  33:     ),
  34:     (
  35:         CMD_BUF,
  36:         "         .force_lrz_dis = CHIP >= A7XX && disable_lrz,\n      });\n",
  37:         "         .force_lrz_dis = CHIP >= A7XX && disable_lrz,\n"
  38:         "         .force_bi_dir_lrz_disable = CHIP >= A8XX && disable_lrz,\n      });\n",
  39:     ),
  40:     (
  41:         CMD_BUF,
  42:         "         cmd->device->physical_device->info->props.has_lrz_feedback\n"
  43:         "            ? LRZ_FEEDBACK_EARLY_Z_OR_EARLY_Z_LATE_Z\n"
  44:         "            : LRZ_FEEDBACK_NONE,\n"
  45:         "   });\n",
  46:         "         cmd->device->physical_device->info->props.has_lrz_feedback\n"
  47:         "            ? LRZ_FEEDBACK_EARLY_Z_OR_EARLY_Z_LATE_Z\n"
  48:         "            : LRZ_FEEDBACK_NONE,\n"
  49:         "      .force_bi_dir_lrz_disable = CHIP >= A8XX,\n"
  50:         "   });\n",
  51:     ),
  52:     (
  53:         LRZ_CC,
  54:         "      const struct tu_reg_value reg = GRAS_SC_BIN_CNTL(CHIP, .force_lrz_dis = true);\n",
  55:         "      const struct tu_reg_value reg = GRAS_SC_BIN_CNTL(CHIP, .force_lrz_dis = true,\n"
  56:         "                                                             .force_bi_dir_lrz_disable = CHIP >= A8XX);\n",
  57:     ),
  58: ]
  59: 
  60: 
  61: def main():
  62:     files = {}
  63:     for path, _, _ in EDITS:
  64:         if path in files:
  65:             continue
  66:         try:
  67:             files[path] = open(path, "r", encoding="utf-8").read()
  68:         except OSError as e:
  69:             print(f"{NAME}: WARNING cannot read {path}: {e}; skipped")
  70:             return 0
  71: 
  72:     if all(MARKER in s for s in files.values()):
  73:         print(f"{NAME}: already applied ({MARKER} present)")
  74:         return 0
  75: 
  76:     for path, old, _ in EDITS:
  77:         found = files[path].count(old)
  78:         if found != 1:
  79:             print(f"{NAME}: WARNING anchor matched {found}x (want 1) in {path}; skipped")
  80:             return 0
  81: 
  82:     for path, old, new in EDITS:
  83:         files[path] = files[path].replace(old, new, 1)
  84: 
  85:     try:
  86:         for path, content in files.items():
  87:             open(path, "w", encoding="utf-8", newline="\n").write(content)
  88:     except OSError as e:
  89:         print(f"{NAME}: ERROR cannot write source files: {e}", file=sys.stderr)
  90:         return 1
  91: 
  92:     print(f"{NAME}: applied (A8XX FORCE_BI_DIR_LRZ_DISABLE)")
  93:     return 0
  94: 
  95: 
  96: if __name__ == "__main__":
  97:     sys.exit(main())

==================== ARQUIVO: patches/62-a8xx-lrz-color-comp-mask.py ====================
   1: #!/usr/bin/env python3
   2: # From: Vauzi-17
   3: """A8XX: emit GRAS_LRZ_COLOR_COMP_MASK with the MRT blend state.
   4: 
   5: On Adreno 8xx (0x810c) the rasterizer LRZ block tracks per-MRT component write
   6: enables through GRAS_LRZ_COLOR_COMP_MASK. Emitting it together with the
   7: SP/RB MRT control packets keeps early-Z LRZ culling coherent across multi-MRT
   8: and disabled-color-attachment draws, instead of falling back to conservative
   9: behaviour.
  10: 
  11: A6xx/A7xx do not have the register, so the emission (and the extra size dwords)
  12: are gated on CHIP >= A8XX.
  13: 
  14: Runs from the Mesa source root. Idempotent; warns and skips on anchor drift.
  15: """
  16: import sys
  17: 
  18: NAME = "62-a8xx-lrz-color-comp-mask.py"
  19: MARKER = "GRAS_LRZ_COLOR_COMP_MASK"
  20: TARGET = "src/freedreno/vulkan/tu_pipeline.cc"
  21: 
  22: EDITS = [
  23:     (
  24:         "      MAX2(cb->attachment_count, 1) : cb->attachment_count;\n"
  25:         "   return 8 + 5 * num_rts;\n",
  26:         "      MAX2(cb->attachment_count, 1) : cb->attachment_count;\n"
  27:         "   return 8 + (CHIP >= A8XX ? 2 : 0) + 5 * num_rts;\n",
  28:     ),
  29:     (
  30:         "   unsigned num_remapped_rts = 0;\n"
  31:         "   for (unsigned i = 0; i < num_rts; i++) {\n",
  32:         "   unsigned num_remapped_rts = 0;\n"
  33:         "   uint32_t lrz_color_comp_mask = 0;\n"
  34:         "   for (unsigned i = 0; i < num_rts; i++) {\n",
  35:     ),
  36:     (
  37:         "      if ((cb->color_write_enables & (1u << i)) && i < cb->attachment_count) {\n",
  38:         "      if ((cb->color_write_enables & (1u << i)) && i < cb->attachment_count) {\n"
  39:         "         if (CHIP >= A8XX && remapped_idx < 8)\n"
  40:         "            lrz_color_comp_mask |= (att->write_mask & 0xf) << (remapped_idx * 4);\n",
  41:     ),
  42:     (
  43:         "   tu_cs_emit_regs(cs, A6XX_SP_PS_MRT_CNTL(.mrt = num_remapped_rts));\n"
  44:         "   tu_cs_emit_regs(cs, A6XX_RB_PS_MRT_CNTL(.mrt = num_remapped_rts));\n"
  45:         "}\n",
  46:         "   tu_cs_emit_regs(cs, A6XX_SP_PS_MRT_CNTL(.mrt = num_remapped_rts));\n"
  47:         "   tu_cs_emit_regs(cs, A6XX_RB_PS_MRT_CNTL(.mrt = num_remapped_rts));\n"
  48:         "   if (CHIP >= A8XX) {\n"
  49:         "      tu_cs_emit_regs(cs, GRAS_LRZ_COLOR_COMP_MASK(CHIP, .dword = lrz_color_comp_mask));\n"
  50:         "   }\n"
  51:         "}\n",
  52:     ),
  53: ]
  54: 
  55: 
  56: def main():
  57:     try:
  58:         content = open(TARGET, "r", encoding="utf-8").read()
  59:     except OSError as e:
  60:         print(f"{NAME}: WARNING cannot read {TARGET}: {e}; skipped")
  61:         return 0
  62: 
  63:     if MARKER in content:
  64:         print(f"{NAME}: already applied ({MARKER} present)")
  65:         return 0
  66: 
  67:     for old, _ in EDITS:
  68:         found = content.count(old)
  69:         if found != 1:
  70:             print(f"{NAME}: WARNING anchor matched {found}x (want 1) in {TARGET}; skipped")
  71:             return 0
  72: 
  73:     for old, new in EDITS:
  74:         content = content.replace(old, new, 1)
  75: 
  76:     try:
  77:         with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
  78:             f.write(content)
  79:     except OSError as e:
  80:         print(f"{NAME}: ERROR cannot write {TARGET}: {e}", file=sys.stderr)
  81:         return 1
  82: 
  83:     print(f"{NAME}: applied (A8XX GRAS_LRZ_COLOR_COMP_MASK emitted with blend state)")
  84:     return 0
  85: 
  86: 
  87: if __name__ == "__main__":
  88:     sys.exit(main())

==================== ARQUIVO: patches/65-nepo-hl-mk1-color-and-perf.py ====================
   1: #!/usr/bin/env python3
   2: """65-nepo-hl-mk1-color-and-perf.py: Hogwarts Legacy & Mortal Kombat 1 Color Precision + Performance Pack for Adreno 8xx.
   3: 
   4: Fixes applied idempotently on Mesa source tree:
   5: 1. [PERF+COLOR] Sample Shading Gate in tu_pipeline.cc: only force per-sample interpolation when minSampleShading > 0.5f or FS uses sample shading.
   6: 2. [COLOR+PERF] Mutable Format UBWC & BGRA8 Tiled Fast-Path in tu_image.cc: keeps UE4/Switch R11G11B10, RGBA8, BGRA8, RGB10A2 and RGBA16F render targets in Tiled+UBWC mode.
   7: 3. [COLOR] R11G11B10_FLOAT Half-Precision fix in tu_clear_blit.cc: sets .half_precision when dst_format OR src_format is PIPE_FORMAT_R11G11B10_FLOAT.
   8: 4. [COLOR] A8XX Category-4 (SFU: log2, exp2, rsq, sqrt) repeat latency guard in ir3_legalize.c: prevents broken sRGB gamma and ACES tonemapping curves.
   9: 5. [PERF] A8XX UBO Push Range Coalescing in freedreno_devices.py / ir3: enables coalesce_ubo_push_ranges across Adreno 825 (0x44030000) and A8xx family.
  10: 6. [STABILITY] UE4 Split/Resumed RenderPass Flush in tu_cmd_buffer.cc: ensures pending cache flushes are preserved across suspending/resuming dynamic render passes.
  11: """
  12: 
  13: import pathlib
  14: import re
  15: import sys
  16: 
  17: NAME = "65-nepo-hl-mk1-color-and-perf"
  18: 
  19: 
  20: def fix_1_sample_shading_gate(mesa_root: pathlib.Path) -> str:
  21:     p = mesa_root / "src/freedreno/vulkan/tu_pipeline.cc"
  22:     if not p.exists():
  23:         return "ERROR: tu_pipeline.cc not found"
  24:     txt = p.read_text(encoding="utf-8")
  25:     if "/* NEPO_65_SAMPLE_GATE */" in txt:
  26:         return "ALREADY"
  27: 
  28:     old = (
  29:         "      keys[MESA_SHADER_FRAGMENT].force_sample_interp =\n"
  30:         "         !builder->rasterizer_discard && msaa_info && msaa_info->sampleShadingEnable;"
  31:     )
  32:     new = (
  33:         "      /* NEPO_65_SAMPLE_GATE */\n"
  34:         "      keys[MESA_SHADER_FRAGMENT].force_sample_interp =\n"
  35:         "         !builder->rasterizer_discard && msaa_info && msaa_info->sampleShadingEnable &&\n"
  36:         "         (msaa_info->minSampleShading > 0.5f ||\n"
  37:         "          (nir[MESA_SHADER_FRAGMENT] &&\n"
  38:         "           nir[MESA_SHADER_FRAGMENT]->info.fs.uses_sample_shading));"
  39:     )
  40:     if old in txt:
  41:         p.write_text(txt.replace(old, new, 1), encoding="utf-8")
  42:         return "OK"
  43:     return "SKIP"
  44: 
  45: 
  46: def fix_2_mutable_format_ubwc_and_bgra_fastpath(mesa_root: pathlib.Path) -> str:
  47:     p = mesa_root / "src/freedreno/vulkan/tu_image.cc"
  48:     if not p.exists():
  49:         return "ERROR: tu_image.cc not found"
  50:     txt = p.read_text(encoding="utf-8")
  51:     if "/* NEPO_65_MUTABLE_UBWC" in txt:
  52:         return "ALREADY"
  53: 
  54:     # Parte A: BGRA8 HIC Tiled fast-path (linha ~576)
  55:     old_hic = (
  56:         "   if ((pCreateInfo->usage & VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT) &&\n"
  57:         "       fd6_color_swap(vk_format_to_pipe_format(image->vk.format),\n"
  58:         "                                               TILE6_LINEAR, false) != WZYX)\n"
  59:         "      force_linear_tile = true;"
  60:     )
  61:     new_hic = (
  62:         "   /* NEPO_65_BGRA_TILED_FASTPATH: Allow BGRA8 UNORM/SRGB to stay tiled */\n"
  63:         "   if ((pCreateInfo->usage & VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT) &&\n"
  64:         "       image->vk.format != VK_FORMAT_B8G8R8A8_UNORM &&\n"
  65:         "       image->vk.format != VK_FORMAT_B8G8R8A8_SRGB &&\n"
  66:         "       fd6_color_swap(vk_format_to_pipe_format(image->vk.format),\n"
  67:         "                                               TILE6_LINEAR, false) != WZYX)\n"
  68:         "      force_linear_tile = true;"
  69:     )
  70:     if old_hic in txt:
  71:         txt = txt.replace(old_hic, new_hic, 1)
  72: 
  73:     # Parte B: Mutable format UBWC preservation (linha ~612)
  74:     old_mut = "         bool mutable_ubwc_fc = device->physical_device->info->props.ubwc_all_formats_compatible;"
  75:     new_mut = (
  76:         "         /* NEPO_65_MUTABLE_UBWC: Keep UE4/Switch R11G11B10, RGBA8, BGRA8, RGB10A2 and RGBA16F\n"
  77:         "          * mutable render targets in Tiled+UBWC mode to preserve color LUT & SceneColor precision.\n"
  78:         "          */\n"
  79:         "         bool mutable_ubwc_fc = device->physical_device->info->props.ubwc_all_formats_compatible ||\n"
  80:         "            ((!fmt_list || fmt_list->viewFormatCount <= 2) &&\n"
  81:         "             (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||\n"
  82:         "              image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||\n"
  83:         "              image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||\n"
  84:         "              image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||\n"
  85:         "              image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||\n"
  86:         "              image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||\n"
  87:         "              image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));"
  88:     )
  89:     if old_mut in txt:
  90:         txt = txt.replace(old_mut, new_mut, 1)
  91:         p.write_text(txt, encoding="utf-8")
  92:         return "OK"
  93:     return "ERROR: anchor not found in tu_image.cc"
  94: 
  95: 
  96: def fix_3_r11g11b10_half_precision(mesa_root: pathlib.Path) -> str:
  97:     p = mesa_root / "src/freedreno/vulkan/tu_clear_blit.cc"
  98:     if not p.exists():
  99:         return "ERROR: tu_clear_blit.cc not found"
 100:     txt = p.read_text(encoding="utf-8")
 101:     if "/* NEPO_65_R11G11B10_PREC */" in txt:
 102:         return "ALREADY"
 103: 
 104:     old = "         .half_precision = util_format_is_float16(src_format) || src_format == PIPE_FORMAT_R11G11B10_FLOAT,"
 105:     new = (
 106:         "         /* NEPO_65_R11G11B10_PREC */\n"
 107:         "         .half_precision = util_format_is_float16(src_format) ||\n"
 108:         "                           src_format == PIPE_FORMAT_R11G11B10_FLOAT ||\n"
 109:         "                           dst_format == PIPE_FORMAT_R11G11B10_FLOAT,"
 110:     )
 111:     if old in txt:
 112:         p.write_text(txt.replace(old, new, 1), encoding="utf-8")
 113:         return "OK"
 114:     return "ERROR: anchor not found in tu_clear_blit.cc"
 115: 
 116: 
 117: def fix_4_cat4_sfu_repeat_delay(mesa_root: pathlib.Path) -> str:
 118:     p = mesa_root / "src/freedreno/ir3/ir3_legalize.c"
 119:     if not p.exists():
 120:         return "ERROR: ir3_legalize.c not found"
 121:     txt = p.read_text(encoding="utf-8")
 122:     if "/* NEPO_65_CAT4_SFU_RPT" in txt:
 123:         return "ALREADY"
 124: 
 125:     old = "         if (instr->repeat && !(dst->flags & IR3_REG_RELATIV))\n            dst_cycle++;"
 126:     new = (
 127:         "         /* NEPO_65_CAT4_SFU_RPT: Ensure full SFU (cat4) latency on A8xx repeated instructions */\n"
 128:         "         if (instr->repeat && !(dst->flags & IR3_REG_RELATIV))\n"
 129:         "            dst_cycle += (opc_cat(instr->opc) == 4 && compiler->gen >= 8) ? 2 : 1;"
 130:     )
 131:     if old in txt:
 132:         p.write_text(txt.replace(old, new, 1), encoding="utf-8")
 133:         return "OK"
 134:     return "ERROR: anchor not found in ir3_legalize.c"
 135: 
 136: 
 137: def fix_5_ubo_push_range_coalescing_a8xx(mesa_root: pathlib.Path) -> str:
 138:     """Enable UBO push range neighbor coalescing (up to 64B / 4 vec4 gap) in ir3_nir_analyze_ubo_ranges.c."""
 139:     p = mesa_root / "src/freedreno/ir3/ir3_nir_analyze_ubo_ranges.c"
 140:     if not p.exists():
 141:         return "ERROR: ir3_nir_analyze_ubo_ranges.c not found"
 142:     txt = p.read_text(encoding="utf-8")
 143:     if "/* NEPO_65_UBO_COALESCE */" in txt:
 144:         return "ALREADY"
 145: 
 146:     old = "      if (a->start > b->end || a->end < b->start)\n         continue;"
 147:     new = (
 148:         "      /* NEPO_65_UBO_COALESCE: Coalesce neighboring UBO ranges within 64B (4 vec4s) to reduce ldc.k count */\n"
 149:         "      if (a->start > b->end + 64 || a->end + 64 < b->start)\n"
 150:         "         continue;"
 151:     )
 152:     if old in txt:
 153:         p.write_text(txt.replace(old, new, 1), encoding="utf-8")
 154:         return "OK"
 155:     return "ERROR: anchor not found in ir3_nir_analyze_ubo_ranges.c"
 156: 
 157: 
 158: def fix_6_split_renderpass_flush(mesa_root: pathlib.Path) -> str:
 159:     p = mesa_root / "src/freedreno/vulkan/tu_cmd_buffer.cc"
 160:     if not p.exists():
 161:         return "ERROR: tu_cmd_buffer.cc not found"
 162:     txt = p.read_text(encoding="utf-8")
 163:     if "/* NEPO_65_RESUMING_FLUSH" in txt:
 164:         return "ALREADY"
 165: 
 166:     old = (
 167:         "   bool resuming = pRenderingInfo->flags & VK_RENDERING_RESUMING_BIT;\n"
 168:         "   bool suspending = pRenderingInfo->flags & VK_RENDERING_SUSPENDING_BIT;"
 169:     )
 170:     new = (
 171:         "   /* NEPO_65_RESUMING_FLUSH: Ensure compute-to-indirect/render barriers flush across split UE4 passes */\n"
 172:         "   bool resuming = pRenderingInfo->flags & VK_RENDERING_RESUMING_BIT;\n"
 173:         "   bool suspending = pRenderingInfo->flags & VK_RENDERING_SUSPENDING_BIT;\n"
 174:         "   if (resuming) {\n"
 175:         "      cmd->state.cache.pending_flush_bits |=\n"
 176:         "         TU_CMD_FLAG_WAIT_FOR_IDLE | TU_CMD_FLAG_CACHE_INVALIDATE;\n"
 177:         "   }"
 178:     )
 179:     if old in txt:
 180:         p.write_text(txt.replace(old, new, 1), encoding="utf-8")
 181:         return "OK"
 182:     return "SKIP"
 183: 
 184: 
 185: def main() -> int:
 186:     mesa_root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd()
 187:     r1 = fix_1_sample_shading_gate(mesa_root)
 188:     r2 = fix_2_mutable_format_ubwc_and_bgra_fastpath(mesa_root)
 189:     r3 = fix_3_r11g11b10_half_precision(mesa_root)
 190:     r4 = fix_4_cat4_sfu_repeat_delay(mesa_root)
 191:     r5 = fix_5_ubo_push_range_coalescing_a8xx(mesa_root)
 192:     r6 = fix_6_split_renderpass_flush(mesa_root)
 193: 
 194:     results = (r1, r2, r3, r4, r5, r6)
 195:     summary = f"sample_gate={r1} mutable_ubwc={r2} r11g11b10={r3} cat4_sfu={r4} ubo_coalesce={r5} rp_flush={r6}"
 196:     if any(r.startswith("ERROR") for r in results):
 197:         print(f"{NAME}: ERROR ({summary})", file=sys.stderr)
 198:         return 1
 199:     if all(r in ("ALREADY", "SKIP") for r in results) and any(r == "ALREADY" for r in results):
 200:         print(f"{NAME}: already applied ({summary})")
 201:         return 0
 202:     print(f"{NAME}: applied ({summary})")
 203:     return 0
 204: 
 205: 
 206: if __name__ == "__main__":
 207:     sys.exit(main())
```

## PASSO 2 - Ancoras no Mesa pos-patch (maxperf)

```text

==================== TU_DEVICE_SUBALLOC_FULL (src/freedreno/vulkan/tu_device.cc:3155-3185) ====================
 3155:    }
 3156: 
 3157:    if (device->vk.enabled_features.customBorderColors)
 3158:       global_size += TU_BORDER_COLOR_COUNT * sizeof(struct bcolor_entry);
 3159: 
 3160:    tu_bo_suballocator_init(
 3161:       &device->pipeline_suballoc, device, 128 * 1024,
 3162:       static_cast<enum tu_bo_alloc_flags>(TU_BO_ALLOC_GPU_READ_ONLY |
 3163:                                           TU_BO_ALLOC_ALLOW_DUMP |
 3164:                                           TU_BO_ALLOC_INTERNAL_RESOURCE |
 3165:                                           tu_bo_ib_flags(device)),
 3166:       "pipeline_suballoc");
 3167:    if (is_kgsl(physical_device->instance)) {
 3168:       tu_bo_suballocator_init(&device->kgsl_profiling_suballoc, device,
 3169:                               128 * 1024, TU_BO_ALLOC_INTERNAL_RESOURCE,
 3170:                               "kgsl_profiling_suballoc");
 3171:    }
 3172: 
 3173:    tu_bo_suballocator_init(&device->event_suballoc, device,
 3174:       getpagesize(), TU_BO_ALLOC_INTERNAL_RESOURCE,
 3175:       "event_suballoc");
 3176: 
 3177:    tu_bo_suballocator_init(
 3178:       &device->vis_stream_suballocator, device,
 3179:       getpagesize(),
 3180:       static_cast<enum tu_bo_alloc_flags>(TU_BO_ALLOC_INTERNAL_RESOURCE |
 3181:                                           TU_BO_ALLOC_ALLOW_DUMP),
 3182:       "vis_stream_suballoc");
 3183: 
 3184:    result = tu_bo_init_new(
 3185:       device, NULL, &device->global_bo, global_size,

==================== TU_IMAGE_MUTABLE_FULL (src/freedreno/vulkan/tu_image.cc:610-665) ====================
  610:    if ((pCreateInfo->flags & VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT) &&
  611:        !vk_format_is_depth_or_stencil(image->vk.format)) {
  612:       const VkImageFormatListCreateInfo *fmt_list =
  613:          vk_find_struct_const(pCreateInfo->pNext, IMAGE_FORMAT_LIST_CREATE_INFO);
  614:       if (!tu6_mutable_format_list_ubwc_compatible(device->physical_device->info,
  615:                                                    fmt_list)) {
  616:          /* NEPO_65_MUTABLE_UBWC: Keep UE4/Switch R11G11B10, RGBA8, BGRA8, RGB10A2 and RGBA16F
  617:           * mutable render targets in Tiled+UBWC mode to preserve color LUT & SceneColor precision.
  618:           */
  619:          bool mutable_ubwc_fc = device->physical_device->info->props.ubwc_all_formats_compatible ||
  620:             ((!fmt_list || fmt_list->viewFormatCount <= 2) &&
  621:              (image->vk.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32 ||
  622:               image->vk.format == VK_FORMAT_R8G8B8A8_UNORM ||
  623:               image->vk.format == VK_FORMAT_R8G8B8A8_SRGB ||
  624:               image->vk.format == VK_FORMAT_B8G8R8A8_UNORM ||
  625:               image->vk.format == VK_FORMAT_B8G8R8A8_SRGB ||
  626:               image->vk.format == VK_FORMAT_R16G16B16A16_SFLOAT ||
  627:               image->vk.format == VK_FORMAT_A2B10G10R10_UNORM_PACK32));
  628: 
  629:          /* NV12 uses a special compression scheme for the Y channel which
  630:           * doesn't support reinterpretation. We have to fall back to linear
  631:           * always.
  632:           */
  633:          if (pCreateInfo->format == VK_FORMAT_G8_B8R8_2PLANE_420_UNORM) {
  634:             if (ubwc_enabled) {
  635:                perf_debug(
  636:                   device,
  637:                   "Disabling UBWC and tiling on %dx%d %s resource due to mutable formats "
  638:                   "(fmt list %s)",
  639:                   image->vk.extent.width, image->vk.extent.height,
  640:                   util_format_name(vk_format_to_pipe_format(image->vk.format)),
  641:                   fmt_list ? "present" : "missing");
  642:             }
  643:             ubwc_enabled = false;
  644:             force_linear_tile = true;
  645:          } else if (!mutable_ubwc_fc) {
  646:             if (ubwc_enabled) {
  647:                if (fmt_list && fmt_list->viewFormatCount == 2) {
  648:                   perf_debug(
  649:                      device,
  650:                      "Disabling UBWC on %dx%d %s resource due to mutable formats "
  651:                      "(fmt list %s, %s)",
  652:                      image->vk.extent.width, image->vk.extent.height,
  653:                      util_format_name(vk_format_to_pipe_format(image->vk.format)),
  654:                      util_format_name(vk_format_to_pipe_format(fmt_list->pViewFormats[0])),
  655:                      util_format_name(vk_format_to_pipe_format(fmt_list->pViewFormats[1])));
  656:                } else {
  657:                   perf_debug(
  658:                      device,
  659:                      "Disabling UBWC on %dx%d %s resource due to mutable formats "
  660:                      "(fmt list %s)",
  661:                      image->vk.extent.width, image->vk.extent.height,
  662:                      util_format_name(vk_format_to_pipe_format(image->vk.format)),
  663:                      fmt_list ? "present" : "missing");
  664:                }
  665:                ubwc_enabled = false;

==================== REAL_USE_SYSMEM_RENDERING (src/freedreno/vulkan/tu_cmd_buffer.cc | regex: ^use_sysmem_rendering\() ====================
 1427: }
 1428: 
 1429: static bool
 1430: use_sysmem_rendering(struct tu_cmd_buffer *cmd,
 1431:                      tu_autotune::rp_ctx_t *rp_ctx,
 1432:                      tu_autotune::rp_key_opt rp_key)
 1433: {
 1434:    if (TU_DEBUG(SYSMEM)) {
 1435:       cmd->state.rp.force_render_mode_reason = "TU_DEBUG(SYSMEM)";
 1436:       return true;
 1437:    }
 1438: 
 1439:    /* can't fit attachments into gmem */
 1440:    if (!cmd->state.tiling->possible) {
 1441:       cmd->state.rp.force_render_mode_reason = "Can't fit attachments into gmem";
 1442:       return true;
 1443:    }
 1444: 
 1445:    /* Use sysmem for empty render areas */
 1446:    if (cmd->state.per_layer_render_area) {
 1447:       for (unsigned i = 0; i < tu_fdm_num_layers(cmd); i++) {
 1448:          if (cmd->state.render_areas[i].extent.width == 0 ||
 1449:              cmd->state.render_areas[i].extent.height == 0) {
 1450:             cmd->state.rp.force_render_mode_reason = "Render area is empty";
 1451:             return true;
 1452:          }
 1453:       }
 1454:    } else if (cmd->state.render_areas[0].extent.width == 0 ||
 1455:               cmd->state.render_areas[0].extent.height == 0) {
 1456:       cmd->state.rp.force_render_mode_reason = "Render area is empty";
 1457:       return true;
 1458:    }
 1459: 
 1460:    if (cmd->state.rp.has_tess) {
 1461:       cmd->state.rp.force_render_mode_reason = "Uses tessellation shaders";
 1462:       return true;
 1463:    }
 1464: 
 1465:    if (cmd->state.rp.has_mesh) {
 1466:       cmd->state.rp.force_render_mode_reason = "Uses mesh shaders";
 1467:       return true;
 1468:    }
 1469: 
 1470:    if (cmd->state.rp.disable_gmem) {
 1471:       /* force_render_mode_reason is set where disable_gmem is set. */
 1472:       return true;
 1473:    }
 1474: 
 1475:    const struct tu_vsc_config *vsc = tu_vsc_config(cmd, cmd->state.tiling);
 1476: 
 1477:    /* XFB is incompatible with non-hw binning GMEM rendering, see use_hw_binning */
 1478:    if (cmd->state.rp.xfb_used && !vsc->binning_possible) {
 1479:       cmd->state.rp.force_render_mode_reason =
 1480:          "XFB is incompatible with non-hw binning GMEM rendering";
 1481:       return true;
 1482:    }
 1483: 
 1484:    /* QUERY_TYPE_PRIMITIVES_GENERATED is incompatible with non-hw binning
 1485:     * GMEM rendering, see use_hw_binning.
 1486:     */
 1487:    if ((cmd->state.rp.has_prim_generated_query_in_rp ||
 1488:         cmd->state.prim_generated_query_running_before_rp) &&
 1489:        !vsc->binning_possible) {
 1490:       cmd->state.rp.force_render_mode_reason =
 1491:          "QUERY_TYPE_PRIMITIVES_GENERATED is incompatible with non-hw binning GMEM rendering";
 1492:       return true;
 1493:    }
 1494: 
------------------------------------------------------------

==================== TU_LRZ_INVALIDATIONS (src/freedreno/vulkan/tu_lrz.cc | regex: lrz\.valid\s*=\s*false|lrz->valid\s*=\s*false|DISABLE|DONT_CARE|LOAD) ====================
   24:  *                  v
   25:  *               Early Stencil Test -> Stencil Write
   26:  *                  v
   27:  *               Early Depth Test -> Depth Write + LRZ feedback
   28:  *                                 + Stencil depthFailOp
   29:  *                  v
   30:  * (!FS_DISABLE) Fragment Shader
   31:  *                  v
   32:  * (!FS_DISABLE) Late Stencil Test -> Stencil Write
   33:  *                  v
   34:  * (!FS_DISABLE) Late Depth Test -> Depth Write + LRZ feedback
   35:  *                                + Stencil depthFailOp
   36:  *
   37:  * Keep the above in mind, when LRZ test fails, no other operations
   38:  * are performed. Especially important with stencil.
   39:  *
   40:  * LRZ is DISABLED until depth attachment is cleared when:
   41:  *   - Depth Write + changing direction of depth test
   42:  *      e.g. from OP_GREATER to OP_LESS;
   43:  *   - Depth Write + OP_ALWAYS or OP_NOT_EQUAL;
------------------------------------------------------------
   26:  *                  v
   27:  *               Early Depth Test -> Depth Write + LRZ feedback
   28:  *                                 + Stencil depthFailOp
   29:  *                  v
   30:  * (!FS_DISABLE) Fragment Shader
   31:  *                  v
   32:  * (!FS_DISABLE) Late Stencil Test -> Stencil Write
   33:  *                  v
   34:  * (!FS_DISABLE) Late Depth Test -> Depth Write + LRZ feedback
   35:  *                                + Stencil depthFailOp
   36:  *
   37:  * Keep the above in mind, when LRZ test fails, no other operations
   38:  * are performed. Especially important with stencil.
   39:  *
   40:  * LRZ is DISABLED until depth attachment is cleared when:
   41:  *   - Depth Write + changing direction of depth test
   42:  *      e.g. from OP_GREATER to OP_LESS;
   43:  *   - Depth Write + OP_ALWAYS or OP_NOT_EQUAL;
   44:  *   - Clearing depth with vkCmdClearAttachments;
   45:  *   - Depth image is a target of blit commands.
------------------------------------------------------------
   28:  *                                 + Stencil depthFailOp
   29:  *                  v
   30:  * (!FS_DISABLE) Fragment Shader
   31:  *                  v
   32:  * (!FS_DISABLE) Late Stencil Test -> Stencil Write
   33:  *                  v
   34:  * (!FS_DISABLE) Late Depth Test -> Depth Write + LRZ feedback
   35:  *                                + Stencil depthFailOp
   36:  *
   37:  * Keep the above in mind, when LRZ test fails, no other operations
   38:  * are performed. Especially important with stencil.
   39:  *
   40:  * LRZ is DISABLED until depth attachment is cleared when:
   41:  *   - Depth Write + changing direction of depth test
   42:  *      e.g. from OP_GREATER to OP_LESS;
   43:  *   - Depth Write + OP_ALWAYS or OP_NOT_EQUAL;
   44:  *   - Clearing depth with vkCmdClearAttachments;
   45:  *   - Depth image is a target of blit commands.
   46:  *   - (pre-a650) Not clearing depth attachment with LOAD_OP_CLEAR;
   47:  *   - (pre-a650) Using secondary command buffers;
------------------------------------------------------------
   34:  * (!FS_DISABLE) Late Depth Test -> Depth Write + LRZ feedback
   35:  *                                + Stencil depthFailOp
   36:  *
   37:  * Keep the above in mind, when LRZ test fails, no other operations
   38:  * are performed. Especially important with stencil.
   39:  *
   40:  * LRZ is DISABLED until depth attachment is cleared when:
   41:  *   - Depth Write + changing direction of depth test
   42:  *      e.g. from OP_GREATER to OP_LESS;
   43:  *   - Depth Write + OP_ALWAYS or OP_NOT_EQUAL;
   44:  *   - Clearing depth with vkCmdClearAttachments;
   45:  *   - Depth image is a target of blit commands.
   46:  *   - (pre-a650) Not clearing depth attachment with LOAD_OP_CLEAR;
   47:  *   - (pre-a650) Using secondary command buffers;
   48:  * LRZ WRITE is DISABLED until depth attachment is cleared when:
   49:  *   - Depth Write + blending (color blend, logic ops, partial color mask, etc.);
   50:  *   - Fragment may be killed by stencil;
   51:  * LRZ is disabled for CURRENT draw when:
   52:  *   - Fragment shader side-effects (writing to SSBOs, atomic operations, etc);
   53:  *   - Fragment shader writes depth or stencil;
------------------------------------------------------------
   40:  * LRZ is DISABLED until depth attachment is cleared when:
   41:  *   - Depth Write + changing direction of depth test
   42:  *      e.g. from OP_GREATER to OP_LESS;
   43:  *   - Depth Write + OP_ALWAYS or OP_NOT_EQUAL;
   44:  *   - Clearing depth with vkCmdClearAttachments;
   45:  *   - Depth image is a target of blit commands.
   46:  *   - (pre-a650) Not clearing depth attachment with LOAD_OP_CLEAR;
   47:  *   - (pre-a650) Using secondary command buffers;
   48:  * LRZ WRITE is DISABLED until depth attachment is cleared when:
   49:  *   - Depth Write + blending (color blend, logic ops, partial color mask, etc.);
   50:  *   - Fragment may be killed by stencil;
   51:  * LRZ is disabled for CURRENT draw when:
   52:  *   - Fragment shader side-effects (writing to SSBOs, atomic operations, etc);
   53:  *   - Fragment shader writes depth or stencil;
   54:  * LRZ WRITE is DISABLED (via LATE_Z) for CURRENT draw when:
   55:  *   - Fragment may be via killed alpha-to-coverage, discard, sample coverage;
   56:  *
   57:  * There is a documentation on LRZ rules in QCOM's driver:
   58:  *  https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/best_practices.html?product=1601111740035277#lrz-do-not-disable
   59:  *
------------------------------------------------------------
   42:  *      e.g. from OP_GREATER to OP_LESS;
   43:  *   - Depth Write + OP_ALWAYS or OP_NOT_EQUAL;
   44:  *   - Clearing depth with vkCmdClearAttachments;
   45:  *   - Depth image is a target of blit commands.
   46:  *   - (pre-a650) Not clearing depth attachment with LOAD_OP_CLEAR;
   47:  *   - (pre-a650) Using secondary command buffers;
   48:  * LRZ WRITE is DISABLED until depth attachment is cleared when:
   49:  *   - Depth Write + blending (color blend, logic ops, partial color mask, etc.);
   50:  *   - Fragment may be killed by stencil;
   51:  * LRZ is disabled for CURRENT draw when:
   52:  *   - Fragment shader side-effects (writing to SSBOs, atomic operations, etc);
   53:  *   - Fragment shader writes depth or stencil;
   54:  * LRZ WRITE is DISABLED (via LATE_Z) for CURRENT draw when:
   55:  *   - Fragment may be via killed alpha-to-coverage, discard, sample coverage;
   56:  *
   57:  * There is a documentation on LRZ rules in QCOM's driver:
   58:  *  https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/best_practices.html?product=1601111740035277#lrz-do-not-disable
   59:  *
   60:  * A650+ (gen3+)
   61:  * =============
------------------------------------------------------------
   48:  * LRZ WRITE is DISABLED until depth attachment is cleared when:
   49:  *   - Depth Write + blending (color blend, logic ops, partial color mask, etc.);
   50:  *   - Fragment may be killed by stencil;
   51:  * LRZ is disabled for CURRENT draw when:
   52:  *   - Fragment shader side-effects (writing to SSBOs, atomic operations, etc);
   53:  *   - Fragment shader writes depth or stencil;
   54:  * LRZ WRITE is DISABLED (via LATE_Z) for CURRENT draw when:
   55:  *   - Fragment may be via killed alpha-to-coverage, discard, sample coverage;
   56:  *
   57:  * There is a documentation on LRZ rules in QCOM's driver:
   58:  *  https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/best_practices.html?product=1601111740035277#lrz-do-not-disable
   59:  *
   60:  * A650+ (gen3+)
   61:  * =============
   62:  *
   63:  * While LRZ could be reused between renderpasses LRZ, it is disabled when
   64:  * underlying depth buffer is changed.
   65:  * The following commands could change a depth image:
   66:  * - vkCmdBlitImage*
   67:  * - vkCmdCopyBufferToImage*
------------------------------------------------------------
   83:  * before using LRZ.
   84:  */
   85: 
   86: static inline void
   87: tu_lrz_invalidate(struct tu_cmd_buffer *cmd, const char *reason)
   88: {
   89:    cmd->state.lrz.valid = false;
   90:    cmd->state.rp.lrz_disable_for_next_rp = true;
   91:    cmd->state.rp.lrz_disable_reason = reason;
   92:    cmd->state.rp.lrz_disabled_at_draw = cmd->state.rp.drawcall_count;
   93:    perf_debug(cmd->device, "Disabling LRZ because '%s' at draw %u", reason,
   94:               cmd->state.rp.lrz_disabled_at_draw);
   95:    trace_warning_lrz_disabled(&cmd->rp_trace, &cmd->draw_cs, cmd, reason);
   96: }
   97: 
   98: void
   99: tu_lrz_disable_write_for_rp(struct tu_cmd_buffer *cmd, const char *reason)
  100: {
  101:    assert(reason);
  102:    if (cmd->state.rp.lrz_write_disabled)
------------------------------------------------------------

==================== IR3_SCHED_HEURISTIC (src/freedreno/ir3/ir3_sched.c | regex: live_effect|choose_instr) ====================
  606:       regs += reg_elems(dst);
  607:    }
  608: 
  609:    return regs;
  610: }
  611: 
  612: /* find net change to live values if instruction were scheduled: */
  613: static int
  614: live_effect(struct ir3_instruction *instr)
  615: {
  616:    struct ir3_sched_node *n = instr->data;
  617:    int new_live =
  618:       (n->partially_live || !instr->uses || instr->uses->entries == 0)
  619:          ? 0
  620:          : new_regs(instr);
  621:    int freed_live = 0;
  622: 
  623:    /* if we schedule something that causes a vecN to be live,
  624:     * then count all it's other components too:
  625:     */
  626:    if (n->collect)
  627:       new_live *= n->collect->srcs_count;
  628: 
  629:    foreach_ssa_src_n (src, n, instr) {
  630:       if (__is_false_dep(instr, n))
  631:          continue;
  632: 
  633:       if (instr->block != src->block)
  634:          continue;
  635: 
  636:       if (is_only_nonscheduled_use(src, instr))
  637:          freed_live += new_regs(src);
  638:    }
  639: 
  640:    return new_live - freed_live;
  641: }
  642: 
  643: /* Determine if this is an instruction that we'd prefer not to schedule
  644:  * yet, in order to avoid an (ss)/(sy) sync.  This is limited by the
  645:  * ss_delay/sy_delay counters, ie. the more cycles it has been since
  646:  * the last SFU/tex, the less costly a sync would be, and the number of
  647:  * outstanding SFU/tex instructions to prevent a blowup in register pressure.
  648:  */
------------------------------------------------------------
  674:       return true;
  675: 
  676:    if (ctx->ss_index - ctx->first_outstanding_ss_index >= 8 && is_ss_producer(instr))
  677:       return true;
  678: 
  679:    return false;
  680: }
  681: 
  682: static struct ir3_sched_node *choose_instr_inc(struct ir3_sched_ctx *ctx,
  683:                                                struct ir3_sched_notes *notes,
  684:                                                bool defer, bool avoid_output);
  685: 
  686: enum choose_instr_dec_rank {
  687:    DEC_NEUTRAL,
  688:    DEC_NEUTRAL_READY,
  689:    DEC_FREED,
  690:    DEC_FREED_READY,
  691: };
  692: 
  693: static const char *
  694: dec_rank_name(enum choose_instr_dec_rank rank)
  695: {
  696:    switch (rank) {
  697:    case DEC_NEUTRAL:
  698:       return "neutral";
  699:    case DEC_NEUTRAL_READY:
  700:       return "neutral+ready";
  701:    case DEC_FREED:
  702:       return "freed";
  703:    case DEC_FREED_READY:
  704:       return "freed+ready";
  705:    default:
  706:       return NULL;
  707:    }
  708: }
  709: 
  710: static unsigned
  711: node_delay(struct ir3_sched_ctx *ctx, struct ir3_sched_node *n)
  712: {
  713:    return MAX2(n->earliest_ip, ctx->ip) - ctx->ip;
  714: }
  715: 
  716: /**
------------------------------------------------------------
  678: 
  679:    return false;
  680: }
  681: 
  682: static struct ir3_sched_node *choose_instr_inc(struct ir3_sched_ctx *ctx,
  683:                                                struct ir3_sched_notes *notes,
  684:                                                bool defer, bool avoid_output);
  685: 
  686: enum choose_instr_dec_rank {
  687:    DEC_NEUTRAL,
  688:    DEC_NEUTRAL_READY,
  689:    DEC_FREED,
  690:    DEC_FREED_READY,
  691: };
  692: 
  693: static const char *
  694: dec_rank_name(enum choose_instr_dec_rank rank)
  695: {
  696:    switch (rank) {
  697:    case DEC_NEUTRAL:
  698:       return "neutral";
  699:    case DEC_NEUTRAL_READY:
  700:       return "neutral+ready";
  701:    case DEC_FREED:
  702:       return "freed";
  703:    case DEC_FREED_READY:
  704:       return "freed+ready";
  705:    default:
  706:       return NULL;
  707:    }
  708: }
  709: 
  710: static unsigned
  711: node_delay(struct ir3_sched_ctx *ctx, struct ir3_sched_node *n)
  712: {
  713:    return MAX2(n->earliest_ip, ctx->ip) - ctx->ip;
  714: }
  715: 
  716: /**
  717:  * Chooses an instruction to schedule using the Goodman/Hsu (1988) CSR (Code
  718:  * Scheduling for Register pressure) heuristic.
  719:  *
  720:  * Only handles the case of choosing instructions that reduce register pressure
------------------------------------------------------------

==================== TU_AUTOTUNE_FUNCS (src/freedreno/vulkan/tu_autotune.cc | regex: ^tu_autotune_) ====================
NENHUM MATCH
```
