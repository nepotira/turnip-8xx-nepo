# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.
O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e este projeto segue [SemVer 2.0.0](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.2.0] - 2026-11-06
### Added
- Variante especializada **`Turnip-A8xx-8sGen4-Switch2` (`-s2`)** focada em emulação de Nintendo Switch e Switch 2 (T239/NVN2), com 752 KB de GMEM, `has_attachment_shading_rate` (VRS), `VK_EXT_mesh_shader` acelerado e calibração de histerese de SP balanceada.
- Perfis de aplicativo dedicados em `00-turnip-defaults.conf` para emuladores de Switch (`Eden`, `Citron`, `Sudachi`, `Yuzu`, `Ryujinx`), `Hogwarts Legacy` e `Mortal Kombat 11`.
- Relatório técnico aprofundado `RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md` com análise forense dos commits de `nepotira/eden-android-optimizations`, causa raiz do glitch esbranquiçado de *Super Mario Odyssey*, engenharia de stutters de shader e inovações disruptivas.
- Relatório técnico aprofundado `RELATORIO_HOGWARTS_MK11_ADRENO8XX.md` com diagnóstico e guia de mitigação para falhas gráficas em *Hogwarts Legacy* (DX12) e *Mortal Kombat 11* (DX11) via Winlator / GameHub.

### Changed
- `scripts/apply_all_patches.py` atualizado para orquestrar as 4 variantes (`sustained`, `biggmem`, `maxperf`, `switch2`) e injetar perfis driconf dinamicamente.
- `.github/workflows/build-turnip.yml` atualizado com a 4ª variante na matriz de compilação.
- `scripts/verify_patch_stack.py` atualizado para validar os invariantes matemáticos da variante `Switch2`.

## [0.1.0] - 2026-11-06
### Added
- Relatório técnico completo (`RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md`) dissecando a arquitetura Adreno 8xx (Gen 8), o gargalo do Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`) e a auditoria de código de mais de 25 forks comunitários de Turnip.
- Plano de implementação (`PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md`) com matriz de triagem de patches e arquitetura em 4 camadas sobre o `mesa/main >= d520ae90`.
- Stack modular de patches e scripts Python (`patches/` e `scripts/apply_all_patches.py`) cobrindo as 4 camadas de correção (GMEM/CCU do Adreno 825/829, LRZ fatiado em GMEM e SYSMEM + coerência bidirecional, `SP_*_HYSTERESIS`, `RB_RESOLVE_CR_CNTL`, MRs `!45937`/`!45973`, série `0001..0006` + `08` IB cache, correções de `kgsl_syncobj_merge`, `wait_timestamp_safe` `poll_timestamp`, `kgsl_sparse_vma_init` e `u_gralloc_aimapper.c`).
- Workflow GitHub Actions (`.github/workflows/build-turnip.yml`) para compilação das 3 variantes (`Sustained`, `BigGMEM` e `MaxPerf`) com Android NDK r29.
