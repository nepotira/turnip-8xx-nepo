# Estratégia de Testes e Verificação (`TESTING.md`)

## 1. Verificação Estática Automatizada (`scripts/verify_patch_stack.py`)
O script `scripts/verify_patch_stack.py` executa testes determinísticos antes de qualquer compilação:
1. **Validação da Aritmética de GMEM e CCU (`Adreno 825` e `Adreno 829` — $2.048\text{ KB}$):**
   - Verifica que em modo `sysmem` a soma dos buffers VPC e caches CCU é exatamente $1.888\text{ KB} \le 2.048\text{ KB}$ (`depth_ccu_offset = 160 KB = 0x28000`), sem *unsigned underflow*.
   - Verifica que em modo `gmem` a variante `sustained` / `maxperf` reserva $992\text{ KB}$ e libera exatamente **`1.056 KB` (`66 blocos` de $16\text{ KB}$)** para tiles, e que a variante `biggmem` reserva $736\text{ KB}$ e libera **`1.312 KB` (`82 blocos` de $16\text{ KB}$)**.
   - Verifica que `tile_align_w = 64` e `tile_max_w = 16384` são divisíveis por $64$ ($2\text{ fatias} \times 32$).
2. **Validação de Sintaxe Python e Presença de Todos os Patches:**
   - Compila a AST de `scripts/apply_all_patches.py` e confere a existência e não-vacuidade de todos os arquivos `.patch` em `patches/`.

## 2. Verificação em Dispositivo Real (`Snapdragon 8s Gen 4 / Adreno 825`)
- Status atual: `not tested` em hardware físico até a conclusão do primeiro build via GitHub Actions.
- Ao testar no Winlator / GameHub / MiceWine / Eden:
  - **Não usar** `TU_DEBUG=sysmem` nem `TU_DEBUG=nolrz`.
  - Coletar log com `TU_DEBUG=startup,gmem` para confirmar `Adreno (TM) 825 (chip_id = 0x44030000)` e `usable_gmem = 1081344` (`Sustained`) ou `1343488` (`BigGMEM`).
