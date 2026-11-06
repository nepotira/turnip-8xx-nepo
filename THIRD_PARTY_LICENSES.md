# Licenças de Terceiros (Third-Party Licenses)

Todo código, patch e dependência de terceiros integrado ou referenciado por este projeto respeita a licença `MIT` do Mesa 3D:

| Componente / Autor | Versão / Commit | Licença (SPDX) | Fonte | Uso / Alterações |
| :--- | :--- | :--- | :--- | :--- |
| **Mesa 3D (`freedreno` / `turnip`)** — Rob Clark, Danylo Piliaiev, Connor Abbott, Igalia, Google | `27.0.0-devel` (`main >= d520ae90` + MRs `!45937`, `!45973`) | `MIT` | `https://gitlab.freedesktop.org/mesa/mesa` | Árvore-mãe compilada pelo pipeline CI |
| **`WinNative-Emu/Drivers` & `Leb-Sun/Drivers`** — MaxsTechReview (`maxjivi05`), Leb-Sun | `main` (Nov 2026) | `MIT` | `https://github.com/WinNative-Emu/Drivers` | Patches `0001..0005` + `08` (Mesh Shader compute, Half-Wave Subgroup 32, Cube NaN sanitize, Bindless invalidate, KGSL VBO alias + IB cache, `u_gralloc_aimapper.c`, UBWC swapchain) |
| **`Vauzi-17/710` & `sherft2607/turnip-adreno722-duo`** — Vauzi-17, sherft2607 | `main` (Nov 2026) | `MIT` | `https://github.com/Vauzi-17/710` | Patches `52`, `54`, `55`, `61`, `62` e `01` (`RB_RESOLVE_CR_CNTL`, `SP_*_HYSTERESIS`, `FORCE_BI_DIR_LRZ_DISABLE`, `GRAS_LRZ_COLOR_COMP_MASK`, UBWC fallback seguro) |
| **`Droid-VM/turnip`** — HuJK | `gen8` (`486c973`, `b43c434`, `bf2112c`) | `MIT` | `https://github.com/Droid-VM/turnip` | Correções KGSL (`poll_timestamp` para `timeout=0`, `tu_dump_bo_init` em `kgsl_sparse_vma_init`, tolerância a `VK_KHR_display`) |
| **`WinterMist010/AdrenoToolsDriversA810` & `faux123/turnip-faux123-driver`** — WinterMist010, faux123, Hugo223 | `main` (Nov 2026) | `MIT` | `https://github.com/WinterMist010/AdrenoToolsDriversA810` | Correção `kgsl-syncobj-merge-ts-fd.patch` e `0006-tu-sample-shading-gate.patch` |
| **`AlexSanz0902/turnip-sd865-z`** — AlexSanz0902 | `main` (`30-tu-z-mutable.py`) | `MIT` | `https://github.com/AlexSanz0902/turnip-sd865-z` | Guarda `DRM_FORMAT_MOD_QCOM_COMPRESSED` (`TILE6_3`) em `tu_image.cc` |
