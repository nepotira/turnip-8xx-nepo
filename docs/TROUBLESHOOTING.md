# Resolução de Problemas Conhecidos (`TROUBLESHOOTING.md`)

## 1. Queda de Desempenho Após 3 Minutos em Aparelhos Sem Cooler (`Thermal Throttling`)
- **Causa:** Uso da variante `MaxPerf` (`-p`, que força `KGSL_CONSTRAINT_PWR_MAX`) em smartphones sem cooler ativo.
- **Solução:** Use a variante padrão **`Turnip-A8xx-8sGen4-Sustained` (`-b`)** ou **`Turnip-A8xx-8sGen4-BigGMEM` (`-e`)**, que mantêm o governador DCVS livre e priorizam a GMEM on-chip.

## 2. Jogo DirectX 12 / Unreal Engine 5 Caindo para `sysmem` em Cenas Pesadas
- **Causa:** Excesso de Render Targets simultâneos (*Deferred Shading*) ultrapassando $1.056\text{ KB}$ de GMEM nos $2\text{ MB}$ do Adreno 825.
- **Solução:** Instale a variante **`Turnip-A8xx-8sGen4-BigGMEM` (`-e`)**, que reduz sincronizadamente o Depth CCU para `QUARTER` ($256\text{ KB}$) e libera **$1.312\text{ KB}$ (`82 blocos`)** para tiles.
