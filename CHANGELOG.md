# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.
O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e este projeto segue [SemVer 2.0.0](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.1.0] - 2026-11-06
### Added
- Relatório técnico completo (`RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md`) dissecando a arquitetura Adreno 8xx (Gen 8), o gargalo do Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`) e a auditoria de código de mais de 25 forks comunitários de Turnip.
- Plano de implementação (`PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md`) com matriz de triagem de patches e arquitetura em 4 camadas sobre o `mesa/main >= d520ae90`.
- Stack modular de patches e scripts Python (`patches/` e `scripts/apply_all_patches.py`) cobrindo as 4 camadas de correção (GMEM/CCU do Adreno 825/829, LRZ fatiado em GMEM e SYSMEM + coerência bidirecional, `SP_*_HYSTERESIS`, `RB_RESOLVE_CR_CNTL`, MRs `!45937`/`!45973`, série `0001..0006` + `08` IB cache, correções de `kgsl_syncobj_merge`, `wait_timestamp_safe` `poll_timestamp`, `kgsl_sparse_vma_init` e `u_gralloc_aimapper.c`).
- Workflow GitHub Actions (`.github/workflows/build-turnip.yml`) para compilação das 3 variantes (`Sustained`, `BigGMEM` e `MaxPerf`) com Android NDK r29.
