# Diário do Projeto (`JOURNAL.md`)

## 2026-11-06 — Implementação da Variante Switch 2, Relatórios Forenses e Otimização para Shaders e Jogos Pesados (v0.2.0)
- **Contexto:** Após os testes em hardware real no Snapdragon 8s Gen 4 confirmarem que a nossa build superou com folga o Turnip v38 e o MrPurple v30 (com `BigGMEM` em 1º lugar, `Sustained` em 2º e `Performance` em 3º), o usuário solicitou:
  1. Análise forense de `nepotira/eden-android-optimizations` para explicar o fim do glitch esbranquiçado de Super Mario Odyssey.
  2. Diagnóstico das quedas abruptas de FPS na compilação/renderização de shaders.
  3. Adição de camada de compatibilidade e desempenho para emulação de Switch e do futuro Switch 2 (T239/NVN2).
  4. Suporte nativo/arquitetura para DLSS 5 / IA upscaling via `VK_KHR_cooperative_matrix`.
  5. Relatórios técnicos aprofundados sobre a engenharia do Eden + Turnip e as correções para Hogwarts Legacy e Mortal Kombat 11.
- **Decisões tomadas:**
  - Criação da variante `Turnip-A8xx-8sGen4-Switch2` (`-s2`) com 752 KB de GMEM, suporte a VRS (`has_attachment_shading_rate`), Mesh Shaders via compute e histerese balanceada de SP.
  - Injeção de perfis de otimização em `00-turnip-defaults.conf` para emuladores de Switch (`eden`, `yuzu`, `citron`, `sudachi`, `suyu`, `ryujinx`), Hogwarts Legacy (forçando `prefer_sysmem` e OOB UBO) e Mortal Kombat 11 (ativando emulação de alpha-to-coverage para eliminar grid lines).
  - Elaboração dos relatórios `RELATORIO_EDEN_TURNIP_SWITCH2_SHADERS.md` e `RELATORIO_HOGWARTS_MK11_ADRENO8XX.md`.
- **Evidências de verificação:**
  - `python3 scripts/verify_patch_stack.py` executado com sucesso validando todas as 4 variantes.
  - Testes do usuário em hardware real: BigGMEM #1, Sustained #2, Performance #3.

## 2026-11-06 — Adoção de regras, estruturação da stack v0.1.0 e compilação no GitHub Actions
- **Contexto:** Adoção de regras e publicação no GitHub (`nepotira/turnip-8xx-nepo`).
- **Evidências:** Compilação das variantes `Sustained`, `BigGMEM` e `MaxPerf` no GitHub Actions (`Run 42168099249`) concluída com 100% de sucesso.
