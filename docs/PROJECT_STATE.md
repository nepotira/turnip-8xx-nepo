# Estado do Projeto — Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) Patch Stack

- **Versão atual:** `v0.1.0`
- **Repositório público:** `https://github.com/nepotira/turnip-8xx-nepo`
- **Fase atual:** Implementação das 4 camadas de patches + Compilação remota via GitHub Actions (`Run 42168099249`) concluídas com sucesso (`Mesa 26.2.0-devel @ 71d0f611`).
- **Ramo ativo:** `main`
- **Status de verificação:**
  - `python3 scripts/verify_patch_stack.py` (validação sintática e matemática de offsets GMEM/CCU para 1 MB na `Adreno 825` e `Adreno 829`): **VERIFICADO (PASS)**.
  - Compilação completa via GitHub Actions (`build-turnip.yml`, Run `42168099249` com Android NDK r29 sobre `Mesa 26.2.0-devel @ 71d0f611`): **VERIFICADO (PASS — 3 pacotes `.zip` gerados e validados)**.
  - Testes em hardware físico (`SM8735` / `POCO F7` / `Redmi Turbo 4 Pro`): `not tested` (aguardando execução dos pacotes `.zip` no dispositivo).

## Entregáveis Concluídos
1. [RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md) — Auditoria completa de engenharia reversa da arquitetura `Adreno 8xx` (Gen 8 Sliced), do `Snapdragon 8s Gen 4` (`SM8735` / `Adreno 825`) e de mais de 25 forks modificados do Turnip.
2. [PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](file:///home/nepo/Downloads/TURNIP/PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md) — Plano de implementação das 4 camadas de correção, matriz de triagem de patches e definição das 3 variantes de compilação.
3. Stack de patches curada em `patches/` e orquestrador idempotente em [scripts/apply_all_patches.py](file:///home/nepo/Downloads/TURNIP/scripts/apply_all_patches.py).
4. Workflow de compilação automatizada no GitHub Actions em [.github/workflows/build-turnip.yml](file:///home/nepo/Downloads/TURNIP/.github/workflows/build-turnip.yml).
5. Pacotes AdrenoTools `.zip` compilados e baixados em `dist/`:
   - `Turnip-A8xx-8sGen4-Sustained-v0.1.0-71d0f611.zip` (`SHA256: bd20e5303f985b198f496174f894b4f8646a51b9603a0930716772b75df2289c`)
   - `Turnip-A8xx-8sGen4-BigGMEM-v0.1.0-71d0f611.zip` (`SHA256: 9abb1dc27e008b7b94657996ac5e893f9626870a06b0972297e1a2c8f369a243`)
   - `Turnip-A8xx-8sGen4-MaxPerf-v0.1.0-71d0f611.zip` (`SHA256: bef77c7cb06676e0d84725d817faf93bcd0a1914688f5387799cbfd13439ad0b`)
