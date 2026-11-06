# Arquitetura do Sistema de Patches (`ARCHITECTURE.md`)

A especificação arquitetural completa, incluindo o diagrama Mermaid de rastreabilidade entre os 11 problemas evidenciados e as 4 Camadas de intervenção sobre o `mesa/main >= d520ae90`, encontra-se em [PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md](../PLANO_IMPLEMENTACAO_CORRECAO_ADRENO_8XX.md).

## Estrutura de Diretórios do Repositório
- `patches/`: Arquivos `.patch` curados e auditados (série `0001..0006`, `08`, MRs `!45937`/`!45973`, correções de sincronização KGSL e UBWC).
- `scripts/apply_all_patches.py`: Orquestrador Python idempotente que aplica as 4 Camadas de patches e seleciona a variante (`sustained`, `biggmem`, `maxperf`).
- `scripts/verify_patch_stack.py`: Verificador estático das invariantes matemáticas de GMEM/CCU (`Adreno 825` e `829`) e integridade dos patches.
- `.github/workflows/build-turnip.yml`: Pipeline GitHub Actions que compila as 3 variantes com Android NDK r29 e gera pacotes `.zip` AdrenoTools.
