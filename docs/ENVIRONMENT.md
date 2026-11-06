# Ambiente de Desenvolvimento e Compilação (`ENVIRONMENT.md`)

## Ambiente Local
- **SO:** Linux (`ubuntu`/`debian` base)
- **Ferramentas instaladas e verificadas:**
  - `git version 2.43.0`
  - `gh version 2.103.3` (autenticado como `nepotira`, escopos `repo`, `workflow`)
  - `python3`

## Ambiente de Compilação Remota (GitHub Actions)
- **Runner:** `ubuntu-latest` (`x86_64`)
- **Toolchain Cross-Compile:** Android NDK `r29` (`aarch64-linux-android36-clang` / `clang++`)
- **Build System:** `meson` (`>= 1.4`), `ninja`, `mako`, `pyyaml`, `glslangValidator`
