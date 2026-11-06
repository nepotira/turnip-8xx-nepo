# Memory: Latest Handoff
> Short pointer to authoritative handoffs per Constitution Section 12.

- **Last Session:** 2026-11-06 (v0.2.4)
- **Delivered:**
  - Resolved 2160p (4K) rendering failure by restoring BANDWIDTH autotuning (eliminating 4,000-bin VSC buffer overflow on 1 MB GMEM).
  - Fixed whitish graphics by activating `tu_fix_a2_alpha_precision = true` for Switch emulators (fixing A8XX KGSL hardware bug on A2B10G10R10 deferred G-buffers) and extending NIR sanitization to compute shader image stores.
  - Bumped version to `0.2.4` and verified with all static, syntactic, and math test suites.
- **Full History:** [docs/handoffs/](file:///home/nepo/Downloads/TURNIP/docs/handoffs/)
