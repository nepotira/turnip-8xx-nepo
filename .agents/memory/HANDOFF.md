# Memory: Latest Handoff
> Short pointer to authoritative handoffs per Constitution Section 12.

- **Last Session:** 2026-11-06 (Implementation of A825 CCU Math Invariant and 2160p Viewport Fix - v0.2.5)
- **Delivered:**
  - Implemented exact mathematical CCU cache fraction and size invariants for Adreno 825 (`0x44030000`) in `scripts/apply_all_patches.py` and `scripts/verify_patch_stack.py` with 100% register alignment and zero underflow.
  - Implemented `patches/63-tu-framebuffer-attachment-extent-guard.py` guarding `tu_CreateFramebuffer` and `tu6_sysmem_render_begin` window scissors against presentation attachment mismatches (eliminates 65% black cutoff in 2160p/Nyushu).
  - Validated static and mathematical invariants via `scripts/verify_patch_stack.py` and tested real patch application on Mesa 3D source tree across all 4 variants (`biggmem`, `sustained`, `maxperf`, `switch2`).
  - Bumped version to `v0.2.5` and updated documentation.
- **Full History:** [docs/handoffs/](file:///home/nepo/Downloads/TURNIP/docs/handoffs/)
