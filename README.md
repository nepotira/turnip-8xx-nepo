# Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) — Hybrid Patch Stack

Repositório de engenharia reversa, auditoria forense e compilação automatizada do driver Vulkan open-source **Mesa Turnip (Freedreno)** para GPUs **Qualcomm Adreno Série 8xx (Gen 8)**, com calibração matemática dedicada para o **Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`, `chip_id = 0x44030000`)** e suporte completo a `Adreno 810`, `Adreno 829`, `Adreno 830` e `Adreno 840`.

## Documentação Técnica Principal
- **[RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md):** Radiografia completa da arquitetura fatiada (*Sliced Architecture*) do Adreno 8xx, gargalos do Snapdragon 8s Gen 4 e auditoria de código de mais de 25 forks comunitários de Turnip.
- **[PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md):** Matriz de triagem (Adotar / Adaptar / Rejeitar) e especificação das 4 Camadas de patches sobre o `mesa/main >= d520ae90`.

## As 3 Variantes Compiladas Automaticamente (`.zip` AdrenoTools)
1. **`Turnip-A8xx-8sGen4-Sustained` (`-b` Balanced / Padrão Recomendada):**
   - `1.056 KB` (`66 blocos`) de GMEM útil para tiles no Adreno 825, `tile_align_w = 64`, `tile_max_w = 16384`, autotuner em `"bandwidth"` (GMEM-First) e governador DCVS livre para evitar *thermal throttling* sem cooler externo.
2. **`Turnip-A8xx-8sGen4-BigGMEM` (`-e` Eco-CCU / Max Tile):**
   - Reduz sincronizadamente o Depth CCU em modo GMEM para `QUARTER` ($256\text{ KB}$) em GPUs de $2\text{ MB}$ (`Adreno 825/829`), liberando **`1.312 KB` (`82 blocos` — 64% da SRAM física)** exclusivamente para tiles em jogos DirectX 12 / Unreal Engine 5 pesados.
3. **`Turnip-A8xx-8sGen4-MaxPerf` (`-p` Performance `PWR_MAX`):**
   - Mantém `KGSL_CONSTRAINT_PWR_MAX` ativo com refresh de $40\text{ ms}$ para desempenho máximo em aparelhos com cooler Peltier externo ou ventoinha integrada.

## Como Aplicar os Patches e Verificar Localmente
```bash
# 1. Verificar a integridade da pilha de patches e scripts:
python3 scripts/verify_patch_stack.py

# 2. Aplicar todas as 4 camadas sobre uma árvore do Mesa (branch main):
python3 scripts/apply_all_patches.py --mesa-dir /caminho/para/mesa --variant sustained
```

## Como Disparar a Compilação via GitHub CLI (`gh`)
```bash
gh workflow run build-turnip.yml --ref main -f variant=all
```

## Licença
Distribuído sob a licença **MIT** ([LICENSE](LICENSE)). Veja créditos e atribuições em [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) e [NOTICE](NOTICE).
