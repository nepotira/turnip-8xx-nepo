# Turnip Adreno 8xx & Snapdragon 8s Gen 4 (`Adreno 825`) — Hybrid Patch Stack

Repositório de engenharia reversa, auditoria forense e compilação automatizada do driver Vulkan open-source **Mesa Turnip (Freedreno)** para GPUs **Qualcomm Adreno Série 8xx (Gen 8)**, com calibração matemática dedicada para o **Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`, `chip_id = 0x44030000`)** e suporte completo a `Adreno 810`, `Adreno 829`, `Adreno 830` e `Adreno 840`.

## Documentação Técnica Principal
- **[RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md](RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md):** Radiografia completa da arquitetura fatiada (*Sliced Architecture*) do Adreno 8xx, gargalos do Snapdragon 8s Gen 4 e auditoria de código de mais de 25 forks comunitários de Turnip.
- **[PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md):** Matriz de triagem (Adotar / Adaptar / Rejeitar) e especificação das 4 Camadas de patches sobre o `mesa/main >= d520ae90`.

## As 4 Variantes Compiladas Automaticamente (`.zip` AdrenoTools)
1. **`Turnip-A8xx-8sGen4-Sustained` (`-b` Balanced / Padrão Recomendada):**
   - `total_reserved = 496 KB`, `usable_gmem = 528 KB` no Adreno 825, `tile_align_w = 64`, `tile_max_w = 16384`, autotuner em `"bandwidth"`.
   - `gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value`, `gmem_per_ccu_color_cache_size = 16 * 1024`, `gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.QUARTER.value`, `gmem_per_ccu_depth_cache_size = 64 * 1024`.
2. **`Turnip-A8xx-8sGen4-BigGMEM` (`-e` Eco-CCU / Max Tile):**
   - `total_reserved = 368 KB`, `usable_gmem = 656 KB` no Adreno 825.
   - `gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value`, `gmem_per_ccu_color_cache_size = 16 * 1024`, `gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.EIGHTH.value`, `gmem_per_ccu_depth_cache_size = 32 * 1024`.
3. **`Turnip-A8xx-8sGen4-MaxPerf` (`-p` Performance `PWR_MAX`):**
   - `total_reserved = 496 KB`, `usable_gmem = 528 KB` no Adreno 825, mantendo `KGSL_CONSTRAINT_PWR_MAX` ativo com refresh de 40 ms para desempenho máximo em aparelhos com cooler Peltier externo ou ventoinha integrada.
   - `gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value`, `gmem_per_ccu_color_cache_size = 16 * 1024`, `gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.QUARTER.value`, `gmem_per_ccu_depth_cache_size = 64 * 1024`.
4. **`Turnip-A8xx-8sGen4-Switch2` (`-s2` Switch 2 / DLSS-like):**
   - Specialized for Nintendo Switch 2 (T239/NVN2), DLSS 5 / Cooperative Matrix, Mesh Shaders & Zero-Stutter Shader Delivery.
   - `total_reserved = 368 KB`, `usable_gmem = 656 KB` no Adreno 825.
   - `gmem_ccu_color_cache_fraction = CCUColorCacheFraction.EIGHTH.value`, `gmem_per_ccu_color_cache_size = 16 * 1024`, `gmem_ccu_depth_cache_fraction = CCUColorCacheFraction.EIGHTH.value`, `gmem_per_ccu_depth_cache_size = 32 * 1024`.

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
