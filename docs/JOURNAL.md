# Diário do Projeto (`JOURNAL.md`)

## 2026-11-06 — Adoção de regras, estruturação da stack v0.1.0 e compilação no GitHub Actions
- **Contexto:** Após concluir a auditoria técnica exaustiva da arquitetura `Adreno 8xx` (com foco no `Snapdragon 8s Gen 4` / `SM8735` / `Adreno 825`) e de 25+ forks comunitários do Turnip, o projeto passou pelo fluxo `/adotar-regras` (`adocao-retroativa`) e publicação no GitHub (`nepotira/turnip-8xx-nepo`).
- **Decisões tomadas:**
  - Manter `GEMINI.md` exclusivamente na pasta local do workspace (`/home/nepo/Downloads/TURNIP/GEMINI.md`) e ignorado no `.gitignore` para nunca ser publicado no GitHub.
  - Adotar a licença `MIT` (compatível com Mesa 3D) e documentar todos os créditos de terceiros em `THIRD_PARTY_LICENSES.md` e `NOTICE` (ADR-0001).
  - Estruturar a stack de patches em 4 camadas idempotentes (`scripts/apply_all_patches.py`) e 3 variantes de compilação (`Sustained -b`, `BigGMEM -e`, `MaxPerf -p`).
- **Evidências de verificação:**
  - `python3 scripts/verify_patch_stack.py` executado localmente e no CI com sucesso (`PASS`), comprovando matematicamente a ausência de underflow em 1 MB de GMEM na `Adreno 825` (`0 B` de underflow em sysmem; `688 KB` úteis em `Sustained`/`MaxPerf` e `752 KB` úteis em `BigGMEM`) e os offsets de `fd_lrzfc_layout<A8XX>` (`br_cur_buffer = 11264`).
  - Workflow `build-turnip.yml` executado no GitHub Actions (`Run 42168099249` sobre `Mesa 26.2.0-devel @ 71d0f611` com Android NDK r29): todas as 3 variantes compilaram `libvulkan_freedreno.so` (`vulkan.adreno.so`, `8.714.321 bytes`) e geraram os pacotes `.zip` em `dist/`.
  - Testes em hardware físico (`SM8735` / `Adreno 825`): `not tested`.
