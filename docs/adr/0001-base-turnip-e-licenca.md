# ADR 0001: Escolha da Base Mesa Upstream (`main`) com Patch Stack Híbrida e Licença MIT

- **Status:** Aceita
- **Data:** 2026-11-06

## Contexto
As GPUs Qualcomm Adreno 8xx (especialmente o Snapdragon 8s Gen 4 / `Adreno 825`, `chip_id = 0x44030000`) sofrem de severa instabilidade e perda de desempenho tanto no Mesa Upstream puro (que ainda não mapeia `0x44030000` e possui bugs em `tu_knl_kgsl.cc` e `tu_lrz.cc`) quanto nos forks estáticos comunitários (`Turnip Gen8 V38 / whitebelyash`, `DiskDVD`, `Banners`), que introduziram regressões graves (`supports_double_threadsize = True`, `offset -= 0x78000` causando underflow nos $2\text{ MB}$ de GMEM e colisões de cache CCU).

## Decisão
1. Adotar o **Mesa Upstream (`gitlab.freedesktop.org/mesa/mesa`, branch `main >= d520ae90`)** como árvore-mãe dinâmica.
2. Aplicar um **Patch Stack Modular em 4 Camadas** gerenciado por scripts Python idempotentes (`scripts/apply_all_patches.py`) e patches `.patch` auditados (`patches/`), gerando **3 variantes especializadas** (`Sustained -b`, `BigGMEM -e` e `MaxPerf -p`).
3. Adotar a licença **MIT** (`SPDX-License-Identifier: MIT`) para manter compatibilidade direta com o Mesa 3D, e usar inglês para commits/código e português do Brasil para documentação do projeto.

## Consequências
- Incorpora imediatamente os commits oficiais de Nov/2026 (`2ce86eed`, `e1852a33`, `5b2db4b8`, `14656cee`) sem herdar código morto ou regressões de subgrupo dos forks estáticos.
- Permite compilar as 3 variantes automaticamente via GitHub Actions (`gh`).
