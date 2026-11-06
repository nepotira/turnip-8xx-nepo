# Manual de Operação (`RUNBOOK.md`)

## 1. Verificar a Pilha de Patches e Invariantes Matemáticas Localmente
```bash
python3 scripts/verify_patch_stack.py
```

## 2. Aplicar os Patches Sobre uma Árvore do Mesa 3D (`main`)
```bash
python3 scripts/apply_all_patches.py --mesa-dir /caminho/para/mesa --variant sustained
# Ou para as variantes biggmem / maxperf:
python3 scripts/apply_all_patches.py --mesa-dir /caminho/para/mesa --variant biggmem
python3 scripts/apply_all_patches.py --mesa-dir /caminho/para/mesa --variant maxperf
```

## 3. Disparar e Monitorar a Compilação das 3 Variantes via GitHub CLI (`gh`)
```bash
git push -u origin main
gh workflow run build-turnip.yml --ref main -f variant=all
sleep 8
RUN=$(gh run list --workflow build-turnip.yml --branch main --limit 1 --json databaseId -q '.[0].databaseId')
echo "Execução iniciada: $RUN"
gh run watch "$RUN" --exit-status --interval 20
```

## 4. Baixar os Pacotes `.zip` AdrenoTools Compilados
```bash
mkdir -p artefatos
gh run download "$RUN" -D artefatos/
sha256sum artefatos/*/*.zip | tee artefatos/SHA256SUMS
```
