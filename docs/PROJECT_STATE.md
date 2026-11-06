# Estado do Projeto (`PROJECT_STATE.md`)

**Última atualização:** 2026-11-06  
**Versão atual:** `0.1.0`  
**Ramo principal:** `main`  

## Resumo Executivo
Projeto de engenharia reversa, auditoria de código e compilação automatizada do driver Vulkan open-source **Mesa Turnip** para GPUs **Qualcomm Adreno 8xx (Gen 8)**, com foco prioritário no **Snapdragon 8s Gen 4 (`SM8735` / `Adreno 825`, `chip_id = 0x44030000`)**.

## O Que Já Está Pronto
1. **Pesquisa e Auditoria Forense Concluídas (`100%`):**
   - `RELATORIO_TECNICO_DRIVERS_ADRENO_8XX.md`: radiografia da arquitetura fatiada (2 fatias / 4 CCUs / $2\text{ MB}$ de GMEM no Adreno 825) e auditoria de código de mais de 25 repositórios de Turnip modificados.
   - `PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md`: matriz de triagem de patches e especificação das 4 camadas e 3 variantes (`Sustained -b`, `BigGMEM -e`, `MaxPerf -p`).
2. **Estrutura de Patches e CI (`100%`):**
   - Scripts modulares de patch em `scripts/` e patches em `patches/`.
   - Workflow de compilação em `.github/workflows/build-turnip.yml`.

## Status de Verificação
- **Verificação estática dos scripts e patches:** verificada localmente (`python3 scripts/verify_patch_stack.py`).
- **Compilação Android NDK r29 via GitHub Actions:** pronta para disparo via `gh workflow run`.
- **Execução em hardware físico (`Snapdragon 8s Gen 4 / Adreno 825`):** `not tested` (aguardando geração do artefato `.zip` no GitHub Actions e teste pelo usuário no aparelho).

## Próximos Passos
1. Subir o repositório para o GitHub via `gh repo create` (ou push para remoto) e disparar o workflow `build-turnip.yml`.
2. Monitorar a compilação das 3 variantes (`Sustained`, `BigGMEM`, `MaxPerf`) até a conclusão e baixar os pacotes `.zip` AdrenoTools.
