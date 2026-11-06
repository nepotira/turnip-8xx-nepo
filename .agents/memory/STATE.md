# Memory: Project State Summary
> Short pointer to authoritative documents per Constitution Section 12.

- **Current Version:** v0.2.6 (SemVer 2.0.0)
- **Status:** Implemented verified fixes for DT_SONAME decoupling (vulkan.nepo.so preventing Android linker collision), Depth Blit Scaling (patch 64 adding BLIT_DST_BIT for D32_SFLOAT/D24S8/D16 in tu_formats.cc resolving 64,910 BlitScaleHelper errors at 2160p), and universal driconf profile covering all Switch emulators (Nyushu, Eden Nepo, Citron, Yuzu, Sudachi, Suyu, Ryujinx, Uzuy). Fully verified via verify_patch_stack.py.
- **Authoritative Docs:** [docs/PROJECT_STATE.md](file:///home/nepo/Downloads/TURNIP/docs/PROJECT_STATE.md), [docs/JOURNAL.md](file:///home/nepo/Downloads/TURNIP/docs/JOURNAL.md), [docs/RELATORIO_FORENSE_ARQUITETURAL_FALHAS_2160P_E_ESBRANQUECIMENTO.md](file:///home/nepo/Downloads/TURNIP/docs/RELATORIO_FORENSE_ARQUITETURAL_FALHAS_2160P_E_ESBRANQUECIMENTO.md), and [PLANO_IMPLEMENTACAO_V026_SWITCH_E_DEPTH_BLIT.md](file:///home/nepo/.gemini/antigravity/brain/d97a42e5-2e38-416d-8987-4f02d636fca3/PLANO_IMPLEMENTACAO_V026_SWITCH_E_DEPTH_BLIT.md).
