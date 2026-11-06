# Relatório Técnico: Instabilidade, Desempenho e Engenharia dos Drivers Adreno Série 8xx (Gen 8) com Foco no Snapdragon 8s Gen 4

**Data de Elaboração:** Novembro de 2026  
**Ambiente de Análise:** Linux / Android Subsystem / Mesa 3D Graphics Library / Emulação Mobile  
**Alvos Principais:** Arquitetura Qualcomm Adreno 8xx (Adreno 825 / Adreno 830 / Adreno 840), SoC Qualcomm Snapdragon 8s Gen 4 (SM8735), Driver Open-Source Mesa Turnip (Freedreno Vulkan), Builds Turnip Gen8 V38 (StevenMXZ / whitebelyash) e Unified Turnip (MrPurple666).

---

## Sumário Executivo

A comunidade de emulação de alto desempenho no Android (Winlator, Mobox, Cassia, Eden, Yuzu, Vita3K, FEX-Emu, Box64) deparou-se com um paradoxo técnico expressivo com a chegada da família de processadores Snapdragon baseados na arquitetura gráfica **Adreno 8xx (Gen 8)**. Enquanto o hardware bruto apresenta avanços teóricos gigantescos em poder computacional (TFLOPS), suporte a Ray Tracing por hardware e novos nós de litografia (3nm e 4nm), **a experiência real em camadas de compatibilidade e emuladores é frequentemente inferior, instável e propensa a falhas graves quando comparada a SoCs de gerações anteriores e maduras, como o Snapdragon 8 Gen 2 (Adreno 740) e até mesmo o lendário Snapdragon 870/865 (Adreno 650)**.

O objetivo deste relatório é dissecar as razões técnicas, arquiteturais e de engenharia de software que causam essa disparidade, com foco minucioso no **Snapdragon 8s Gen 4 (SM8735 / Adreno 825)**. Este documento expõe, de forma explícita e sem atenuantes, os gargalos, quebras de abstração no código dos drivers e deficiências de hardware/chassi que explicam por que o chip entrega desempenho truncado e inconsistente nos drivers atuais.

---

## 1. O Salto Arquitetural Adreno 7xx $\rightarrow$ Adreno 8xx: A Ruptura de Engenharia

Para compreender a quebra dos drivers, é necessário decodificar como a Qualcomm alterou a microarquitetura dos seus processadores gráficos.

### 1.1 Da Arquitetura Monolítica para a "Sliced Architecture" (Arquitetura Fatiada)

Nas gerações Adreno 5xx, 6xx e 7xx, a Qualcomm adotou uma abordagem predominantemente monolítica ou de blocos centralizados:
* Um Command Processor (CP) centralizado recebia os indirect buffers (`ib1`, `ib2`).
* Um conjunto coeso de Shader Processors (SPs) e Texture Processors (TPs) comunicava-se com um bloco unificado de memória local on-chip (**GMEM** - Graphics Memory / Tile Buffer).
* O agendamento de ondas de shaders (wavefronts/fibers) e a rasterização de primitivas operavam sobre coordenadas globais simples.

Na arquitetura **Adreno 8xx (Gen 8 - codinomes Kaanapali para dispositivos móveis e Glymur para computação Windows/X2)**, a Qualcomm reformulou radicalmente o chip, adotando uma **Arquitetura Fatiada (Sliced Architecture)**:
1. **Particionamento em Slices:** O chip é segmentado fisicamente em fatias autônomas (por exemplo, 3 fatias no Adreno 830, ou 2 fatias em modelos derivados como o Adreno 825).
2. **Subunidades Dedicadas por Fatia:** Cada slice abriga seus próprios clusters de ALUs de sombreamento, unidades de textura, hardware dedicado para aceleração de BVH (Bounding Volume Hierarchy para Ray Tracing) e uma partição local do cache L2 / GMEM.
3. **Crossbar e Interconexão de Fatias:** A distribuição de primitivas e a fusão de saídas de fragmentos passaram a exigir um crossbar de alta largura de banda para sincronizar as fatias.

#### A Consequência para os Drivers:
Drivers maduros desenvolvidos pela comunidade por engenharia reversa (como o **Mesa Turnip**) assumiam premissas fundamentadas em anos de documentação e traces de Adreno 6xx/7xx:
* Registradores de controle de rasterização, binning e buffers de profundidade eram mapeados globalmente.
* Na Adreno 8xx, muitos desses registradores tornaram-se duplicados ou indexados por fatia. O envio de comandos legados afeta apenas uma fatia ou causa falha catastrófica de decodificação no Command Processor.

---

### 1.2 O Subsistema de Memória On-Chip (GMEM) e Tile-Based Deferred Rendering (TBDR)

As GPUs Adreno são projetadas com base em **Tile-Based Deferred Rendering (TBDR)**: a tela é dividida em pequenas grades (*bins* ou *tiles*), renderizadas diretamente dentro da memória estática ultrarrápida on-chip (**GMEM**, que atua como um buffer SRAM integrado ao die, operando com latência ínfima e altíssima largura de banda). Uma vez concluído o processamento de um tile, os dados de cores e profundidade são resolvidos (*resolved*) para a memória DRAM principal (LPDDR5/LPDDR5X).

#### O Problema no Adreno 8xx:
* No Adreno 6xx e 7xx, o cálculo de coordenadas de binning no Turnip (`src/freedreno/vulkan/tu_gmem.c`) e o controle do **Visibility Stream Coordinator (VSC)** seguiam fórmulas lineares bem conhecidas de largura, altura e alinhamento de tiles em relação ao tamanho total da GMEM.
* No Adreno 8xx, a GMEM foi fracionada entre as fatias de hardware. O particionamento exige sequências inteiramente novas de pacotes PM4 para calibrar os limites dos tiles em cada slice.
* **Sintoma Real:** Se o driver Turnip tenta executar o passe de binning em GMEM sem o novo protocolo de registradores de corte de tiles, a GPU gera **Write Page Faults** instantâneos no kernel (`kgsl` ou `msm`), corrompendo a memória de vídeo e disparando um *GPU Reset* imediato.

#### A Solução Paliativa Comunitária e seu Custo Brutal:
Para impedir o encerramento forçado do jogo, os desenvolvedores de forks e usuários são forçados a injetar a variável de ambiente:
```bash
TU_DEBUG=sysmem
```
* **O que faz:** Desativa integralmente o motor de TBDR e a memória GMEM, forçando o driver a trabalhar em modo de renderização direta na memória de sistema (Direct System Memory Rendering), operando como se fosse uma GPU de desktop dedicada.
* **O desastre de desempenho:** O chip passa a escrever e ler cada fragmento, mistura de transparência (*alpha blending*) e teste de profundidade diretamente na DRAM externa (LPDDR5X). A largura de banda da memória — que já é compartilhada com a CPU executando retranspilação pesada (Box64/FEX/emulador) — é completamente afogada. A GPU consome muito mais energia, opera com latência dezenas de vezes maior e tem seu frame rate destruído.

---

### 1.3 O Mecanismo de Oclusão e Profundidade: Low Resolution Z (LRZ)

O **Low Resolution Z (LRZ)** é a implementação proprietária da Adreno para aceleração de *Early-Z Rejection* e *Fast Depth Clear*. O hardware constrói uma representação de baixa resolução do buffer de profundidade e descarta fragmentos invisíveis/ocultos antes mesmo que os caros *pixel/fragment shaders* sejam executados.

#### O Problema no Adreno 8xx:
* No código do Turnip (`src/freedreno/vulkan/tu_lrz.c`), a lógica de invalidação, troca de direção de profundidade (`GREATER` $\leftrightarrow$ `LESS`) e alinhamento de buffers de LRZ foi lapidada ao longo de 4 anos para funcionar perfeitamente até o Adreno 750 (Snapdragon 8 Gen 3).
* No Adreno 8xx, a Qualcomm modificou a representação binária e a semântica dos registradores de controle do LRZ, além de introduzir requisitos de barreiras explícitas de cache de profundidade ao término de cada sub-passo.
* **Sintoma Real:** Quando o LRZ está ativo em builds preliminares no Adreno 8xx, ocorrem anomalias visuais graves:
  * Paredes e terrenos renderizam por cima do personagem principal (*Z-fighting* invertido).
  * Geometrias inteiras piscam ou desaparecem dependendo do ângulo da câmera.
  * O pipeline de profundidade tenta escrever em páginas inválidas, travando o contexto.
* **A Consequência:** A recomendação padrão na comunidade para o Adreno 8xx é executar:
```bash
TU_DEBUG=nolrz
```
* Desativar o LRZ força o processador de sombreamento a calcular as cores e iluminação de **todos os pixels**, inclusive os que estão completamente escondidos atrás de outros objetos. Em jogos 3D modernos traduzidos via DXVK (DirectX 11 $\rightarrow$ Vulkan), isso quase **duplica a carga sobre as ALUs**, gerando quedas de quadros drásticas e micro-travamentos contínuos.

---

### 1.4 A Mudança no Conjunto de Instruções (ISA) e no Compilador `ir3`

Os shaders originados de jogos de PC ou consoles vêm em formato HLSL/GLSL, são compilados para o bytecode intermediário **SPIR-V** (pelo DXVK, VKD3D ou emulador) e, em seguida, o driver Vulkan precisa traduzir esse SPIR-V para o código de máquina nativo da GPU Adreno. Essa tarefa é executada pelo compilador de backend do Freedreno: o **`ir3`** (`src/freedreno/ir3/`).

#### O Abismo no Adreno 8xx:
1. **Novos Opcodes e Modificadores:** A Qualcomm alterou campos de bits de instruções de controle de fluxo, saltos condicionais (*branches*), sincronização entre threads e instruções de empacotamento vetorial (FP16 / FP32).
2. **Instruções de Ray Tracing:** A inclusão de instruções específicas para aceleração de árvores BVH alterou a tabela de codificação de certas instruções de amostragem de textura e leitura de buffers de memória (`ldl`, `stl`, `ldg`).
3. **Erros no Compilador:** Como a especificação oficial da ISA do Adreno 8xx nunca foi liberada pela Qualcomm, a equipe do Freedreno (liderada por desenvolvedores como Rob Clark) depende de engenharia reversa a partir da desmontagem de binários proprietários.
4. **Sintoma Real:** Shaders complexos contendo laços dinâmicos, arrays de texturas dinâmicos (*bindless textures*) ou cálculos com inteiros de 64 bits (`shaderInt64`) frequentemente disparam falhas internas no `ir3` ou emitem sequências de bytes que a GPU Adreno 8xx rejeita como instruções ilegais, resultando em:
   * Falhas de compilação durante telas de carregamento (*Pipeline Creation Stalls*).
   * Travamentos do Shader Processor (SP Hang / CP Interrupt Timeout).

---

## 2. Radiografia do Snapdragon 8s Gen 4 (SM8735 / Adreno 825)

Se o chip topo de linha Snapdragon 8 Elite (Adreno 830) já sofre com a falta de maturidade dos drivers, o **Snapdragon 8s Gen 4 (SM8735)** encontra-se em uma situação ainda mais crítica. A análise da sua engenharia revela por que esse SoC se torna uma armadilha para usuários que esperam dele a estabilidade de processadores consolidados.

```
+-----------------------------------------------------------------------------------------+
|                  QUALCOMM SNAPDRAGON 8s Gen 4 (SM8735) - ADRENO 825                     |
+-----------------------------------------------------------------------------------------+
|  CPU Cores:               1x Cortex-X4 + 4x Cortex-A720 + 3x Cortex-A520 (sem Oryon)    |
|  GPU Architecture:        Adreno Gen 8 (Sliced Architecture - Variante Podada)          |
|  GPU Model:               Adreno 825 (Fatias reduzidas, contagem de ALUs inferior)      |
|  On-Chip Cache / GMEM:    Capacidade de GMEM reduzida frente ao Adreno 830/840          |
|  Memory Subsystem:        Interface LPDDR5X mais estreita / menor largura de banda      |
|  Target Devices:          Smartphones intermediários-premium (Poco, Redmi, Realme)      |
|  Cooling Profile:         Chassis com dissipação passiva modesta (Throttling agressivo) |
+-----------------------------------------------------------------------------------------+
```

### 2.1 A Natureza da Linha "s": O Flagship de Custo Reduzido

A linha "8s" da Qualcomm (como visto anteriormente no 8s Gen 3 / Adreno 735 e reiterado no 8s Gen 4 / Adreno 825) **não é o processador carro-chefe de geração pura**:
* **Arquitetura de CPU Diferente:** O verdadeiro topo de linha (Snapdragon 8 Elite / 8 Gen 4) estreou os núcleos de CPU customizados **Qualcomm Oryon**. O 8s Gen 4 utiliza a arquitetura ARM padrão (Cortex-X4 e Cortex-A720). Em emuladores de PC que dependem do tradutor dinâmico de binários (JIT / dynarec como Box64 ou FEX-Emu), o perfil de IPC e a latência de troca de contexto entre threads de x86 para ARM divergem substancialmente.
* **A GPU Adreno 825:** Trata-se de uma versão "capada" da microarquitetura Gen 8. Em vez das fatias completas e dos 12MB de cache L2 dedicados da Adreno 830, a Adreno 825 sofre reduções drásticas:
  * Menor contagem de Shader Processors / ALUs de computação.
  * Menor bloco de memória GMEM física disponível.
  * Possível redução no número de fatias ativas de processamento.

---

### 2.2 O Fenômeno da "Orfandade" de Otimização e Mapeamento de Registradores

No desenvolvimento open-source do Mesa Freedreno/Turnip, o esforço da comunidade e dos engenheiros concentra-se primariamente em dois alvos:
1. O SoC flagship móvel comercial de maior visibilidade (Snapdragon 8 Elite / Adreno 830).
2. O processador para laptops Linux/Windows em ARM (Snapdragon X Elite / X2 Elite / Adreno X1-85 / X2-85).

O arquivo de definição de dispositivos do driver (`src/freedreno/common/freedreno_devices.py`) mapeia o hardware por seu código de identificação de chip (`chip_id`):
```python
# Trecho representativo da abstração no Mesa freedreno_devices.py
# Cada variante exige constantes exatas de gmem_size, num_slices e num_sp_cores:
"a830": DeviceInfo(
    chip_id=0x08030000,
    gmem_size=...,
    num_slices=3,
    ...
)
```
Quando um chip derivado como o **Adreno 825** é lançado:
* **Incompatibilidade de Constantes:** Se o driver Turnip tentar inicializar o Adreno 825 assumindo os limites e buffers de memória do Adreno 830, o driver alocará offsets de GMEM e limites de binning que ultrapassam a memória estática real do Adreno 825. O resultado é a corrupção imediata da VRAM e o encerramento do processo.
* **Falta de Tuning Específico:** Enquanto a comunidade ajusta magic numbers de registradores para o Adreno 830, o Adreno 825 permanece em um limbo de compatibilidade, apresentando falhas exclusivas que não ocorrem sequer no seu irmão maior.

---

### 2.3 O Gargalo Crítico de Largura de Banda de Memória (Memory Bandwidth Starvation)

A linha "8s" costuma ser equipada pelas fabricantes de aparelhos com barramentos de memória LPDDR5X mais estreitos ou frequências de operação mais conservadoras em comparação aos chips topo de linha.

Quando se soma:
$$\text{Box64/FEX (Emulação de CPU x86)} + \text{DXVK (Tradução D3D11 } \rightarrow \text{ Vulkan)} + \text{Turnip operando com TU\_DEBUG=sysmem}$$
Ocorre uma catástrofe de fluxo de dados:
1. O emulador de CPU satura a memória lendo e traduzindo instruções do jogo.
2. A GPU, privada de sua GMEM rápida devido a bugs de driver, tenta ler e escrever todos os buffers de cor, stencil e profundidade na mesma memória RAM LPDDR5X.
3. O barramento atinge $100\%$ de saturação de largura de banda.
4. **O Efeito no Jogo:** Mesmo com o chip operando em clock alto, a GPU passa a maior parte do tempo ociosa esperando que os dados cheguem da DRAM (*Memory Stalls*). O jogo apresenta congelamentos constantes (*micro-stutters* severos), e o frame time oscila descontroladamente entre 16ms e 120ms.

---

### 2.4 Fator Térmico e Throttling Desenfreado no Chassi Intermediário

O Snapdragon 8s Gen 4 é comercializado para alimentar smartphones da categoria "flagship killer" (como linhas Redmi Turbo, Poco F, Realme GT Neo, Motorola Edge). Essas carcaças compartilham um traço em comum:
* **Soluções de Arrefecimento Econômicas:** Ao contrário de aparelhos gamers dedicados (RedMagic, ROG Phone) ou flagships de mais de mil dólares (Galaxy S Ultra), que contam com grandes câmaras de vapor multicamadas, placas de grafite espessas ou ventoinhas integradas, os aparelhos com chips "8s" possuem dissipação térmica modesta e limites rígidos de aquecimento na superfície plástica/fina de vidro.
* **A Curva de Queda Térmica:**
  * **Minuto 0 ao Minuto 2:** O processador inicia o jogo entregando picos de 50 a 60 FPS (força bruta momentânea).
  * **Minuto 3:** A carga conjugada de DRAM saturada, ALUs sem Early-Z e CPU ARM retranspilando código faz a junção do silício atingir o teto de corte térmico ($80^\circ\text{C} - 85^\circ\text{C}$).
  * **Minuto 4 em diante:** O regulador térmico do kernel (*thermal engine governor*) reduz abruptamente a frequência da GPU de cerca de $900-1000\text{ MHz}$ para patamares irrisórios de $300-400\text{ MHz}$.
  * **Resultado:** O desempenho despenca para 15 a 20 FPS com engasgos crônicos, tornando a experiência intolerável.

---

## 3. O Driver Proprietário da Qualcomm (`vulkan.adreno.so`): Por Que Não Salva a Emulação?

Muitos usuários se perguntam: *"Se o driver comunitário Turnip ainda não está pronto para o Adreno 8xx, por que não usar simplesmente o driver oficial da Qualcomm fornecido no sistema Android?"*

A resposta reside no abismo de padrões de engenharia entre jogos nativos do Android e camadas de tradução de jogos de PC/Console:

```
+-----------------------------------------------------------------------------------------------+
|                       PERFIL DE DEMANDA GRÁFICA: MOBILE vs. TRADUÇÃO                          |
+------------------------------------+----------------------------------------------------------+
| Jogos Nativos Android (Genshin)    | Camadas de Tradução Desktop (DXVK / VKD3D / Winlator)    |
+------------------------------------+----------------------------------------------------------+
| Pipelines Vulkan estáticos         | Criação dinâmica contínua de pipelines em tempo real     |
| Render Passes pré-definidos        | Dynamic Rendering com múltiplas trocas de layout         |
| Descritores estáticos simples      | Unbounded Descriptor Indexing (milhares de texturas)     |
| Samplers e filtros convencionais   | VK_EXT_custom_border_color (específico do DirectX)       |
| Transformações simples             | VK_EXT_transform_feedback (Stream Output do D3D10/11)    |
| Tipos de dados padrão (FP32/FP16)  | Operações inteiras de 64 bits (shaderInt64 para D3D12)   |
| Ausência de geometrias complexas   | Shaders de geometria e tesselação arbitrários            |
+------------------------------------+----------------------------------------------------------+
```

### 3.1 Violações de Conformidade com Extensões de Desktop
O driver proprietário da Qualcomm é altamente ajustado e otimizado para um propósito específico: **pontuar alto em benchmarks sintéticos (3DMark, Geekbench) e rodar uma dúzia de jogos populares da Google Play Store (Genshin Impact, Honkai Star Rail, PUBG Mobile, Call of Duty)**. Esses jogos utilizam pipelines gráficos padronizados para plataformas móveis.

No entanto, quando o DXVK ou o emulador submete instruções que emulam chamadas do DirectX de PC, o driver proprietário falha nos seguintes pontos:
1. **`VK_EXT_custom_border_color` Ausente ou Quebrada:** Jogos de DirectX de PC frequentemente utilizam cores de borda personalizadas para texturas (para controlar limites de mapas de sombras e efeitos visuais). O driver da Qualcomm ignora essa extensão ou a implementa com falhas que causam artefatos negros em sombras e água.
2. **`VK_EXT_transform_feedback` Inexistente:** O recurso de *Stream Output* das APIs DirectX 10 e 11 depende do suporte a Transform Feedback no Vulkan. Como os jogos nativos do Android praticamente não usam essa extensão, a Qualcomm não se preocupa em refiná-la para SoCs recém-lançados. Sem ela, objetos dinâmicos (como grama se movimentando, peles e roupas de personagens) não são renderizados.
3. **Indexação Ilimitada de Descritores (`descriptorIndexing`):** Jogos modernos de PC utilizam o conceito de arquitetura *Bindless*, onde centenas ou milhares de texturas ficam mapeadas simultaneamente em uma tabela massiva na VRAM. O compilador de shaders da Qualcomm frequentemente entra em *stack overflow* ou emite código inválido ao lidar com esses índices em tempo de execução.
4. **Vazamento e Fragmentação de Memória no Kernel `kgsl`:** O driver de sistema fecha e abre instâncias de memória em alocações de tamanho fixo. Camadas como DXVK alocam e desalocam buffers de geometria a cada frame, gerando esgotamento de *file descriptors* no `/dev/kgsl-3d0` e encerrando o jogo com erro `VK_ERROR_OUT_OF_DEVICE_MEMORY`.

---

## 4. Mapeamento Exaustivo e Auditoria de Código de Todos os Turnips Modificados (Forks Comunitários)

Para compreender o estado real do ecossistema além do Mesa Upstream (`gitlab.freedesktop.org/mesa/mesa`), foram rastreados, clonados e auditados linha a linha **mais de 25 repositórios de forks e builders de Turnip modificados** — abrangendo tanto os forks dedicados ao Adreno 8xx (Gen 8) quanto os forks históricos e universais de A6xx/A7xx/A8xx distribuídos em hubs como `AdrenoToolsDrivers`, `EmuHub-APP` e `GameNative`.

### 4.1 Catálogo Geral e Genealogia dos Repositórios de Turnip Modificados

| Categoria | Repositório / Autor | Variante / Nome Comercial | Base de Código & Escopo | Relação com Adreno 8xx / Snapdragon 8s Gen 4 (`Adreno 825`) |
| :--- | :--- | :--- | :--- | :--- |
| **Hubs e Indexadores** | `K11MCH1/AdrenoToolsDrivers` (★5.168) | Kimchi / AdrenoTools | Agregador histórico (`Weab-chan`, `MrPurple`, `Qualcomm`) | Focado em A6xx/A7xx; pacotes para 8xx são redirecionados para `StevenMXZ` e `whitebelyash`. |
| **Hubs e Indexadores** | `StevenMXZ/Adreno-Tools-Drivers` (★1.149) | `Turnip v26` / `Turnip Gen8 V36–V38 (v27.0.0-R1)` | Empacota builds de `whitebelyash/mesa-unified` (`turnip/gen8`) | Principal distribuidor público da linha `Turnip Gen8 V38`. |
| **Hubs e Indexadores** | `Rodrig02005/EmuHub-APP` & `GameNative/mesa-turnip` | `sources.json` / `variants/matrix.yml` | Índices vivos de CI (`stevenmxz`, `whitebelyash`, `mrpurple`, `banner`, `s1mptom`, `wintermist010`, `diskdvd`, `vauzi17`, `winnative`) | Mapeiam todas as variantes ativas usadas por Winlator, MiceWine, GameHub e Eden. |
| **Fork Base Gen 8** | `whitebelyash/mesa-unified` (`turnip/gen8`), `whitebelyash/mesa-tu8` & `whitebelyash/AdrenoToolsDrivers` | `Turnip Gen8` / `mesa-tu8` | Rebase do MR `!38450` (Rob Clark) + `tu8_kgsl.patch` + `DECK_EMU` (`FD810/825/829`) | **Árvore-mãe da maioria dos forks Gen 8.** Introduziu o suporte inicial ao KGSL no A8xx, mas também injetou regressões graves (`reg_size_vec4=96` em `a8xx_gen1`, `offset -= 0x78000` e `supports_double_threadsize=True`). |
| **Forks Gen 8 (A8xx)** | `WinNative-Emu/Drivers` (`maxjivi05` / MaxsTechReview) & `Leb-Sun/Drivers` | `WinNative A8xx` (`main`, `eco-variant`, `Redmagic-11-Pro-fixes`) | `mesa/main` dinâmico + série `0001..0005` + scripts Python (`apply_a8xx_gpus.py`, `add_aimapper_gralloc.py`, variantes `-b`, `-p`, `-e`) | Autores dos patches mais avançados de hardware A8xx (Mesh Shader em compute, Wave32 em meia-onda, Cube NaN sanitize, VBO alias no KGSL e `AIMapper5`), porém com erro de `tile_align_w=96` e colisão de CCU cache no `Adreno 825`. |
| **Forks Gen 8 (A8xx)** | `The412Banner/Banners-Turnip` (★227, branch `A8xx`) | `Banner's Turnip A8xx` | Combina `mesa/main` + `tu_gen8_clean.patch` (`whitebelyash`) + `0001..0005` (`MaxsTechReview`) + `tune_a830.py` + `a8xx_no_double_threadsize.py` | Corrige `supports_double_threadsize=False`, mas herda `offset -= 0x78000` (que causa underflow no `Adreno 825/829`) e configura `127 * 1024` desalinhado na GMEM do `Adreno 825`. |
| **Forks Gen 8 (A8xx)** | `DiskDVD/TurniptoolsA8XX` & `DiskDVD/MesaA8XX` | `Turnip A8XX-Y` | Fork entusiasta sobre `whitebelyash/mesa-unified` | Autor dos commits `70e2d6f3`/`136323c4` (config de GMEM do `Adreno 825`), `bc16322d` (código morto gerado por LLM em `ir3_compiler.c`) e `d854a454` (booleano C++ quebrado `|| 0x44050001`). |
| **Forks Gen 8 (A8xx)** | `WinterMist010/AdrenoToolsDriversA810` & `WinterMist010/mist-mesa-unified` | `WinterMist -N` (fork) & `WinterMist -U` (upstream + `patches/base` + `patches/sync2`) | Mantém duas trilhas: `-N` (`mist-mesa-unified`) e `-U` (`mesa/main` + 35 patches curados de `Vauzi-17`, `Hugo223`, `MaxsTechReview` e `DiskDVD`) | A trilha `-U` agrega excelentes correções de sincronização KGSL (`patches/sync2`) e registradores A8xx, mas aplica `0000-a8xx.patch` do `DiskDVD` que corrompe os offsets de GMEM do `Adreno 825`. |
| **Forks Gen 8 (A8xx)** | `Droid-VM/turnip` (branch `gen8` — `HuJK`) | `Droid-VM Turnip Gen8` | Fork de `whitebelyash/mesa-tu8` com 3 commits cirúrgicos no backend `tu_knl_kgsl.cc` | **Descoberta valiosa:** resolveu o travamento de `wait_timestamp_safe(timeout=0)` no KGSL (+35% FPS no Minecraft) e o crash de `kgsl_sparse_vma_init` ao liberar memória sparse (`dump_bo_list_idx`). |
| **Forks Gen 8 (A8xx)** | `faux123/turnip-faux123-driver` & `turnip-faux123-droiddeck` | `faux123 Turnip` | `mesa/main` testado nas 115 cenas do Khronos Vulkan-Samples no AYN Odin 3 (`Adreno 830`) | Identificou e corrigiu o crash `SIGSEGV` por ponteiro nulo / FD inválido em `kgsl_syncobj_merge` (`tu_knl_kgsl.cc`). |
| **Forks Gen 8 (A8xx)** | `s1mptom/freedreno_turnip-CI` | `s1mptom Turnip` (Eden) | Builder CI focado no emulador Eden (`fix_devices.py`, `fix_timeline_sync.py`, `filter_patch.py`) | Compila para `A830/A840/A825/A829/A810`, mas reduz `reg_size_vec4` de `128` para `96` e força `prefer_sysmem`. |
| **Forks Gen 8 (A8xx)** | `Frane12/Testturnip` (`Drnas Turnip`), `Ghael-V/Turnip-Lemon-Ade` & `Killdos26/turnip-a8xx` | `Drnas V12–V18 / S Ultimate`, `Lemon-Ade` | Forks experimentais com scripts Python de mutação sobre o Mesa | `Frane12` (`patches/v13_a830.py`) foi o primeiro a detectar e corrigir o bug `|| 0x44050001` do `DiskDVD` e restaurar a checagem de limites `numInts >= 2` em `u_gralloc_fallback.c`. |
| **Forks Cross-Gen (A7xx + A8xx)** | `Vauzi-17/710` & `sherft2607/turnip-adreno722-duo` (★48) | `Turnip A710/A722/A8xx` | Engenharia reversa baseada em **116 capturas `.rd` (`cffdump`)** do driver proprietário Qualcomm + patches WSI glibc do Winlator (`brunodev85/mesa3d-custom`) | **Fonte de ouro em engenharia reversa:** criou os patches `51..62` para A8xx baseados em traces reais do blob da Qualcomm (`SP_*_HYSTERESIS`, `RB_RESOLVE_CR_CNTL`, `FORCE_BI_DIR_LRZ_DISABLE` e `GRAS_LRZ_COLOR_COMP_MASK`). |
| **Forks Cross-Gen / A6xx / A7xx** | `MrPurple666/purple-turnip` & `MrPurple666/freedreno-CI` | `Purple Turnip T26–T30-toasted` | Base `26.3.0-devel` com ajustes de `fd_dev_info` e `force_sample_interp = false` (reconstruído em `patch_t30_a722_sysmem.py` do `sherft2607`) | Excelente em A6xx/A7xx, mas no A8xx usa tabelas estáticas de Agosto/2026 sem suporte real ao `Adreno 825` no KGSL. |
| **Forks Cross-Gen / A6xx / A7xx** | `AlexSanz0902/turnip-sd865-z` (★85) | `TurnipZ` | Criador da família de patches `tu-z-*` (`30-tu-z-mutable.py`, `33-tu-z-lrz-clear.py`, `34-tu-z-texfast.py`, `35/36-sysmem`, `38-bgra-swap.py`) | O patch `30-tu-z-mutable.py` contém uma correção vital para `VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT` com `DRM_FORMAT_MOD_QCOM_COMPRESSED` em `CHIP >= A8XX` (`TILE6_3`). |
| **Forks Cross-Gen / A6xx / A7xx** | `Balemuni/Balemunis-Aurora` (★267) | `Apex Universal V2` | Otimizações agressivas de subalocação (`pipeline_suballoc` 512 KB, shader cache 4 GB, `gcm=1` no `ir3`) e Driconf para TOTK/BOTW | Focado em A6xx/A7xx; ajustes de subalocação de BO e Driconf são portáveis. |
| **Forks Cross-Gen / CI** | `Weab-chan/freedreno_turnip-CI`, `ilhan-athn7/freedreno_turnip-CI` (★166), `v3kt0r-87/Mesa-Turnip-Builder` (★222), `JustCallMeJade`, `VanezZa-Driver`, `zachspartofaday` | Builders CI e patches pontuais | Automação de builds Android NDK + patches de LOD (`mesa-turnip-min-lod-fix`) e WSI | Fornecem infraestrutura de empacotamento `.adpkg` e flags de compilação LTO/PGO. |

---

### 4.2 O Que os Turnips Modificados Já Descobriram e Acertaram (Patches Valiosos que Faltam no Mesa Oficial)

A auditoria do código-fonte de todos esses repositórios revelou **10 correções e implementações de altíssimo valor técnico** que já existem espalhadas nos forks comunitários, mas que **ainda não estão no Mesa Upstream (`mesa/main`)**:

#### 1. Crash `SIGSEGV` e Uso de File Descriptor Não Inicializado em `kgsl_syncobj_merge()` (`patches/sync2/kgsl-syncobj-merge-ts-fd.patch` & `faux123`)
Ao inspecionar `src/freedreno/vulkan/tu_knl_kgsl.cc:1136-1169` no Mesa Upstream atual (`d520ae90`), confirma-se que a função `kgsl_syncobj_merge()` possui **dois bugs fatais de memória/descritor de arquivo** quando mescla um `syncobj` baseado em Timestamp (`KGSL_SYNCOBJ_STATE_TS`) com outro `TS` ou `FD`:
* **Bug A (Linhas 1139–1147):** Quando `ret.state == KGSL_SYNCOBJ_STATE_TS` e `sync->state == KGSL_SYNCOBJ_STATE_TS` pertencem a filas diferentes (`ret.queue != sync->queue`), o código upstream faz `ret.state = KGSL_SYNCOBJ_STATE_FD;` e na linha seguinte passa `ret.fd` (que contém o valor lixo da union/struct de quando `ret` era um `TS`!) diretamente para `sync_merge_close("tu_sync", ret.fd, sync_fd, true)`, sem converter `ret` para FD via `kgsl_syncobj_ts_to_fd(&ret)`!
* **Bug B (Linhas 1159–1163):** No bloco `case KGSL_SYNCOBJ_STATE_FD:`, quando `ret.state == KGSL_SYNCOBJ_STATE_TS`, o código upstream chama `int sync_fd = kgsl_syncobj_ts_to_fd(sync);` passando `sync` (que já é `FD`, logo `sync->queue` é `NULL`!) em vez de `&ret`! Dentro de `kgsl_syncobj_ts_to_fd()`, a desreferenciação `syncobj->queue->device->fd` causa **`SIGSEGV` imediato**!
* O patch `kgsl-syncobj-merge-ts-fd.patch` (presente em `WinterMist010` e `faux123`) corrige ambos os ramos convertendo `int ret_fd = kgsl_syncobj_ts_to_fd(&ret);`.

#### 2. Travamento de Thread por `timeout = 0` ("Wait Forever") em `wait_timestamp_safe()` (`Droid-VM/turnip@486c973` & `patches/sync2/kgsl-zero-timeout-poll.patch`)
No driver de kernel KGSL da Qualcomm (`adreno_drawctxt_wait()` em `drivers/gpu/msm/adreno_drawctxt.c`), passar `timeout = 0` no `IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID` **não significa "retornar imediatamente"**, e sim **"esperar infinitamente (`wait_event` sem timeout)"**!
* Em `src/freedreno/vulkan/tu_knl_kgsl.cc:833-862`, sempre que `get_relative_ms(abs_timeout_ns)` retorna `0` (como quando o coletor de lixo de `vk_sync_timeline` sonda pontos pendentes com `abs_timeout_ns = 0`, ou quando restam menos de $1\text{ ms}$ para o prazo expirar), `wait_timestamp_safe()` chama o `ioctl` com `wait.timeout = 0`.
* Isso bloqueia a thread chamadora no kernel até a GPU concluir o frame inteiro **enquanto segura o `timeline->mutex`**, travando todas as outras threads do jogo em `vkWaitSemaphores` / `vkQueueSubmit`!
* O commit `486c973` de `HuJK` (`Droid-VM/turnip`) substitui a chamada com `timeout == 0` por uma leitura não-bloqueante via `IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID` (`KGSL_TIMESTAMP_RETIRED`) comparada com `timestamp_cmp()`, reduzindo o tempo bloqueado em `vkWaitSemaphores` de **$250\text{ ms/s}$ para $5\text{ ms/s}$** e elevando a taxa de quadros em **+35% (de 93 para 126 FPS)**.

#### 3. Crash na Desalocação de Memória Sparse por Falta de `tu_dump_bo_init()` (`Droid-VM/turnip@b43c434`)
Em `src/freedreno/vulkan/tu_knl_kgsl.cc`, a função `kgsl_sparse_vma_init()` (usada por jogos DirectX 12 no VKD3D-Proton e emuladores com *Sparse Binding*) inicializa um `struct tu_bo` sintético para rastrear a VMA no `dump-bo`, mas **esquece de chamar `tu_dump_bo_init(dev, bo)`**.
* Como a struct é zerada com `memset`, `bo->dump_bo_list_idx` fica com o valor `0` em vez da sentinela `~0` (`UINT32_MAX`).
* Quando a VMA sparse é liberada em `kgsl_bo_finish()` $\rightarrow$ `tu_dump_bo_del(dev, bo)`, o driver vê `dump_bo_list_idx (0) != ~0`, tenta remover o índice `0` de uma `dump_bo_list` vazia (quando `TU_DEBUG=dump` não está ativo) e sofre **corrupção de heap / `SIGSEGV`**!

#### 4. Rejeição da Extensão `VK_KHR_display` na Inicialização do KGSL (`Droid-VM/turnip@bf2112c`)
Em `src/freedreno/vulkan/tu_knl_kgsl.cc`, `tu_knl_kgsl_load()` aborta `vkCreateInstance` / inicialização do dispositivo com `VK_ERROR_INITIALIZATION_FAILED ("I can't KHR_display")` se a aplicação habilitar a extensão de instância `VK_KHR_display` (comportamento padrão do Zink, compositores Wayland/Weston e camadas de contêiner). Remover esse bloqueio artificial (reportando 0 displays físicos) evita falhas de inicialização.

#### 5. Inicialização de `SP_*_HYSTERESIS` no Adreno 8xx (`54-a8xx-sp-hysteresis.py` & `55-a8xx-sp-hysteresis-gs-hs-ds.py` de `Vauzi-17`)
A engenharia reversa de `Vauzi-17` sobre 116 capturas `.rd` (`cffdump`) do driver proprietário da Qualcomm descobriu uma omissão importante em `src/freedreno/vulkan/tu_cmd_buffer.cc`:
* No Adreno 7xx (`has_rt_workaround = True`), os registradores `SP_PS_HYSTERESIS`, `SP_VS_HYSTERESIS` e `SP_CS_HYSTERESIS` são programados indiretamente dentro de `tu_emit_rt_workaround()`.
* No Adreno 8xx, como `has_rt_workaround = False` em `a8xx_base`, `tu_emit_rt_workaround()` nunca é executado! Como resultado, todos os 6 registradores (`SP_VS_HYSTERESIS`, `SP_HS_HYSTERESIS`, `SP_DS_HYSTERESIS`, `SP_GS_HYSTERESIS`, `SP_PS_HYSTERESIS` e `SP_CS_HYSTERESIS`) permanecem em `0x0`, fazendo o Shader Processor desligar as fatias de ALU prematuramente (*power-gating* agressivo sem histerese) entre draw calls consecutivos e causando micro-engasgos constantes de reativação de clock!
* O driver oficial da Qualcomm grava `SP_PS_HYSTERESIS = 0x00000c00` e `SP_VS/HS/DS/GS/CS_HYSTERESIS = 0x00000400` logo após `SP_ALPHA_TEST_CNTL` em `tu6_init_hw<A8XX>`.

#### 6. Emissão de `REG_A8XX_RB_RESOLVE_CR_CNTL = 1` no Preamble (`52-a8xx-resolve-cr-cntl.py` de `Vauzi-17`)
Nos traces de hardware A8xx do blob da Qualcomm, o registrador `REG_A8XX_RB_RESOLVE_CR_CNTL` (`0x8816`) é invariavelmente inicializado com `0x00000001` no preamble estático (`a8xx_base_raw_magic_regs`) para habilitar o controle de *Color/Clear Resolve* das unidades RB nas fatias do Gen 8 — registrador ausente no `freedreno_devices.py` upstream.

#### 7. Bits de Coerência de Hardware do LRZ no Adreno 8xx: `FORCE_BI_DIR_LRZ_DISABLE` e `GRAS_LRZ_COLOR_COMP_MASK` (`61` e `62` de `Vauzi-17`)
Além dos commits `2ce86eed` e `e1852a33` do Mesa Upstream, os patches `61-a8xx-lrz-bidir-disable.py` e `62-a8xx-lrz-color-comp-mask.py` identificaram duas exigências físicas do bloco GRAS no Adreno 8xx:
* **`GRAS_SC_BIN_CNTL.FORCE_BI_DIR_LRZ_DISABLE` (bit 14 em `CHIP >= A8XX`):** No Adreno 8xx, o hardware possui atualização bidirecional de LRZ. Durante o modo `sysmem` (`tu6_sysmem_render_begin`) e quando o LRZ é desabilitado no bin (`tu6_emit_bin_size` com `disable_lrz = true`), o blob da Qualcomm seta `.force_bi_dir_lrz_disable = true` para impedir que as fatias atualizem o buffer LRZ em direções conflitantes entre draws — resolvendo a causa raiz do *flickering* de profundidade em jogos como *Red Dead Redemption 2* sem precisar de `TU_DEBUG=nolrz`!
* **`GRAS_LRZ_COLOR_COMP_MASK` (`0x810c` em `CHIP >= A8XX`):** No Adreno 8xx, o bloco LRZ exige que a máscara de componentes de cor dos MRTs (`mrt_comp_mask`) seja espelhada no registrador `GRAS_LRZ_COLOR_COMP_MASK` dentro de `tu6_emit_mrt_blend_state()` (`tu_pipeline.cc`).

#### 8. Bloqueio de Falso-Positivo de `sampleShadingEnable` no VKD3D-Proton (`0006-tu-sample-shading-gate.patch` de `Hugo223`)
O tradutor DirectX 12 `vkd3d-proton` ativa `VkPipelineMultisampleStateCreateInfo::sampleShadingEnable = VK_TRUE` (`minSampleShading = 1.0f`) no pipeline inteiro sempre que um módulo DXIL declara a flag global `SampleRateShading`, mesmo quando o fragment shader atual não interpola nada por amostra (`nir->info.fs.uses_sample_shading == false`).
* Em `src/freedreno/vulkan/tu_shader.cc` (`tu_lower_nir`), o Turnip upstream verifica apenas `if (key->force_sample_interp)` e força `nir_lower_single_sampled` em todos os inputs do FS, multiplicando a execução do Fragment Shader por $4\times$ (em MSAA 4x) e desativando otimizações de Early-Z.
* Exigir `if (key->force_sample_interp && nir->info.fs.uses_sample_shading)` restaura a execução *per-pixel* quando o shader não usa interpolação por amostra, gerando um ganho documentado de **+37,5% de FPS no Adreno 8xx** (ex.: *Teardown* subindo de 40 FPS para 55 FPS).

#### 9. Cache de Buffers de Comando (`IB`) Retirados no KGSL + VBO Alias (`0005` + `08-tu-kgsl-cache-retired-a8xx-ib-storage.patch` de `MaxsTechReview`)
Além de mapear os command streams (`TU_BO_ALLOC_CMD_STREAM`) através de um alias virtual `KGSL_MEMFLAGS_VBO` (evitando o *GPU hang* ao chamar `IOCTL_KGSL_GPUMEM_FREE_ID`), o patch `08-tu-kgsl-cache-retired-a8xx-ib-storage.patch` recicla os BOs de command stream já aposentados (`check_timestamp >= max_point`) em uma lista livre por dispositivo (`a8xx_ib_bo_cache`, limitada a $256\text{ MB}$), eliminando o overhead de dezenas de chamadas de sistema `IOCTL_KGSL_GPUOBJ_ALLOC` / `BIND_RANGES` por segundo.

#### 10. Proteção de `TILE6_3` em Imagens `MUTABLE_FORMAT` Comprimidas no A8xx (`30-tu-z-mutable.py` de `AlexSanz0902`)
Em `src/freedreno/vulkan/tu_image.cc` (`tu_image_init`), quando uma imagem com `VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT` usa modificador explícito `DRM_FORMAT_MOD_QCOM_COMPRESSED` e formatos que variam em *block width/height*, o código upstream faz `layout->tile_mode = TILE6_LINEAR` se `CHIP < A8XX` não for respeitado, criando um estado ilegal (`UBWC = true` + `TILE6_LINEAR`) que corrompe o display. O guarda `if (image->vk.drm_format_mod != DRM_FORMAT_MOD_QCOM_COMPRESSED && CHIP < A8XX)` preserva `TILE6_3` no Adreno 8xx.

---

### 4.3 Onde os Turnips Modificados Erram e Sabotam o Snapdragon 8s Gen 4 (`Adreno 825`)

Se por um lado os forks comunitários trouxeram as descobertas acima, por outro lado a auditoria expôs **erros gravíssimos de engenharia, matemática de registradores quebrada e até código morto gerado por IA (LLM)** dentro dos próprios patches que tentam dar suporte ao `Snapdragon 8s Gen 4` (`Adreno 825`):

```
+----------------------------------------------------------------------------------------------------+
|            RADIOGRAFIA DOS ERROS NOS FORKS COMUNITÁRIOS PARA O ADRENO 825 (2.048 KB GMEM)          |
+--------------------------+-----------------------------------+-------------------------------------+
| Fork / Patch             | Configuração Aplicada no Código   | Consequência Física no Adreno 825   |
+--------------------------+-----------------------------------+-------------------------------------+
| whitebelyash / V38 /     | sysmem_ccu_depth = THREE_QUARTER  | Hardware reserva 4x192KB = 768KB,   |
| WinNative / Banners      | (768KB HW) vs 96KB*4 (384KB SW)   | mas software subtrai só 384KB:      |
| (apply_a8xx_gpus.py)     |                                   | Depth CCU atropela 384KB do Color!  |
+--------------------------+-----------------------------------+-------------------------------------+
| DiskDVD / WinterMist010  | gmem_ccu_color = HALF (4x128KB)   | Só os caches CCU consomem 1.024 KB  |
| (0000-a8xx.patch)        | gmem_ccu_depth = HALF (4x128KB)   | (50% da GMEM inteira!), restando    |
|                          | + sysmem 128KB+96KB desalinhado   | apenas 608 KB para tiles TBDR!      |
+--------------------------+-----------------------------------+-------------------------------------+
| Banners-Turnip           | gmem_ccu_depth = FULL (1.024KB)   | Depth CCU de 1 MB invade 516 KB da  |
| (apply_a8xx_gpus.py +    | vs 127KB*4 (508KB) + aplica       | região de tiles GMEM, e o desconto  |
| tu_gen8_clean.patch)     | offset -= 0x78000 (480 KB)        | 0x78000 causa UNDERFLOW (-224 KB)!  |
+--------------------------+-----------------------------------+-------------------------------------+
| DiskDVD / whitebelyash   | const bool is_a830 = chip_id ==   | 0x44050001 é sempre TRUE em C++!    |
| (commit d854a454 /       | 0x44050000 || 0x44050001;         | Desativa fdm_per_layer e MSAA       |
| 6a415c50)                |                                   | sample shading em TODAS as GPUs!    |
+--------------------------+-----------------------------------+-------------------------------------+
| DiskDVD / WinterMist010  | Commit bc16322d ("Known to be     | ~100 linhas de funções (ir3_get_    |
| (0000-a8xx.patch)        | generated with an LLM")           | gpu_profile) NUNCA chamadas (0 uso)!|
+--------------------------+-----------------------------------+-------------------------------------+
| whitebelyash / s1mptom / | a8xx_gen1.reg_size_vec4 = 128->96 | Corta 25% dos registradores (GPRs)  |
| Banners (tu_gen8_clean)  | e supports_double_threadsize=True | do A830 e quebra 660/660 subgroups! |
+--------------------------+-----------------------------------+-------------------------------------+
| whitebelyash             | Comenta if (numInts >= 2 && ...)  | Leitura fora dos limites (OOB read) |
| (commit 742f5776)        | em u_gralloc_fallback.c           | em handles nativos com numInts < 2! |
+--------------------------+-----------------------------------+-------------------------------------+
```

1. **A Catástrofe Matemática do `0000-a8xx.patch` (`DiskDVD` / `WinterMist010`):**
   * No commit `70e2d6f3` / `136323c4`, `DiskDVD` tentou configurar o `Adreno 825` definindo `gmem_ccu_color_cache_fraction = HALF` ($128\text{ KB}$ por CCU — quando o máximo físico do Color Cache é $128\text{ KB}$, logo `HALF` na verdade programa $64\text{ KB}$ no hardware enquanto o software subtrai $128\text{ KB} \times 4 = 512\text{ KB}$!) e `gmem_ccu_depth_cache_fraction = HALF` ($128\text{ KB} \times 4 = 512\text{ KB}$). Com isso, $1.024\text{ KB}$ mais $416\text{ KB}$ de buffers VPC consomem **$1.440\text{ KB}$ dos $2.048\text{ KB}$ de GMEM**, deixando míseros **$608\text{ KB}$** para renderização em tiles! E no modo `sysmem`, manteve `THREE_QUARTER` ($192\text{ KB}$ no hardware) com `96 * 1024` no software, perpetuando a sobreposição de $384\text{ KB}$ entre Depth e Color CCU.
2. **Alucinação de IA (Código 100% Morto) em `src/freedreno/ir3/ir3_compiler.c` (`DiskDVD` / `WinterMist010` commit `bc16322d`):**
   * O próprio commit no repositório `WinterMist010/AdrenoToolsDriversA810` (`0000-a8xx.patch`, linhas 273–460) traz o aviso explícito: *"Known to be generated with an LLM"*. Ele adiciona a struct `ir3_gpu_profile` e as funções `ir3_get_gpu_profile()`, `ir3_effective_reg_size()`, `ir3_force_double_threadsize()` e `ir3_get_alu_to_alu_delay()` em `ir3_compiler.c` e `ir3_compiler.h` (inclusive com `chip_id` errados da geração A7xx como `0x43050a31` para GPUs A8xx!), mas **nenhuma dessas funções é chamada em lugar algum do compilador `ir3` ou do Turnip**. É peso morto puro.
3. **Underflow de Inteiro Sem Sinal no `Adreno 825` e `829` via `fd6_gmem_cache.h` (`whitebelyash` / `Banners-Turnip`):**
   * O patch `tu_gen8_clean.patch` (`PATCH 9/9`) reinsere `if (info->chip >= 8 && info->num_slices > 1) offset -= 0x78000;` ($480\text{ KB}$) em `__calc_gmem_cache_offsets()`. Esse desconto foi criado originalmente apenas para o `Adreno 830` ($3\text{ fatias}$, $3.072\text{ KB}$ de GMEM). Como o `Adreno 825` e o `Adreno 829` possuem `num_slices = 2` (`> 1`), mas apenas **$2.048\text{ KB}$ de GMEM**, subtrair $480\text{ KB}$ extras faz o `unsigned offset` sofrer *underflow* para **`0xFFFC8000` ($-224\text{ KB}$)**, programando um endereço inválido no registrador `RB_CCU_DEPTH_BUFFER_BASE` e causando *GPU Page Fault* instantâneo!
4. **Leitura Fora de Limites (*Out-of-Bounds Read*) em `u_gralloc_fallback.c` (`whitebelyash` commit `742f5776`):**
   * Para remover a checagem do magic `'gmsm'`, `whitebelyash` comentou a linha inteira `// if (hnd->handle->numInts >= 2 && hnd->handle->data[hnd->handle->numFds] == 'gmsm')`, fazendo o código ler `hnd->handle->data[hnd->handle->numFds + 1]` mesmo quando `numInts < 2` (corrigido posteriormente por `Vauzi-17` em `01-u_gralloc-always-use-ubwc-detection.patch` e `Frane12` mantendo `if (hnd->handle->numInts >= 2)`).

---

## 5. Matriz Comparativa: Por Que Gerações Mais Antigas São Tão Superiores Hoje?

A tabela a seguir evidencia detalhadamente por que processadores antigos superam o Snapdragon 8s Gen 4 na prática em camadas de compatibilidade:

| Parâmetro Técnico | Adreno 650 (Snapdragon 870 / 865) | Adreno 740 (Snapdragon 8 Gen 2) | Adreno 825 (Snapdragon 8s Gen 4) |
| :--- | :--- | :--- | :--- |
| **Tempo de Engenharia Reversa** | Mais de 5 anos (extremamente maduro) | Cerca de 2,5 anos (estado da arte) | Menos de 1 ano (preliminar / experimental) |
| **Arquitetura da GPU** | Monolítica clássica | Monolítica aprimorada | Fatiada (*Sliced Architecture*) podada |
| **Suporte a GMEM (TBDR) no Turnip** | $\mathbf{100\%}$ Funcional e ultra-otimizado | $\mathbf{100\%}$ Funcional e ultra-otimizado | **Quebrado / Incompleto** (exige `sysmem`) |
| **Suporte a LRZ (Early-Z)** | Totalmente funcional | Totalmente funcional | **Instável / Quebrado** (exige `nolrz`) |
| **Compilador `ir3` (Shaders)** | Praticamente todos os opcodes mapeados | Excelente cobertura de instruções | Instruções novas e modificadas sem mapeamento |
| **Largura de Banda de Memória** | Adequada, sem estresse (usa GMEM) | Muito alta (LPDDR5X) + GMEM funcional | **Estrangulada** (LPDDR5X saturada por `sysmem`) |
| **Comportamento Térmico** | Estável em 60 FPS com TDP moderado | Altíssima eficiência energética (TSMC 4nm) | **Throttling agressivo** em carcaças intermediárias |
| **Compatibilidade DXVK / Winlator** | Altíssima (jogos abrem e rodam lisos) | Padrão ouro da emulação no Android | **Crítica** (Crashes, artefatos e micro-stutters) |
| **Consistência de Frame Pacing** | Linha de frame time plana | Linha de frame time extremamente lisa | Picos caóticos de latência de renderização |

> [!NOTE]
> **O Paradoxo da Força Bruta:** Em benchmarks sintéticos que usam APIs estáticas de demonstração (como o 3DMark Wildlife), o Snapdragon 8s Gen 4 pode pontuar até três vezes mais que o Snapdragon 870. No entanto, ao iniciar um jogo de PC traduzido em tempo real (como *Fallout 4* ou *Bioshock Infinite*), o Snapdragon 870 sustenta 45-60 FPS fluidos e sem erros gráficos, enquanto o 8s Gen 4 frequentemente não consegue passar da tela de introdução, ou opera a 20 FPS com falhas geométricas graves devido à ausência de drivers otimizados.

---

## 6. Evidenciação Explícita de Todos os Problemas a Serem Resolvidos

Esta seção consolida e elenca de forma objetiva, direta e explícita todos os problemas técnicos existentes na pilha de hardware e software do Snapdragon Adreno 8xx / 8s Gen 4 (tanto no Mesa Upstream quanto nos forks comunitários) que impedem seu funcionamento ideal. **Conforme diretriz, esta listagem expõe e evidencia as falhas sem tentar implementar soluções provisórias.**

### 6.1 Problemas na Camada de Microarquitetura e Kernel
1. **Falta de Abstração para a Arquitetura Fatiada no Espaço de Usuário:** Os drivers open-source ainda não orquestram de forma completa a subdivisão de tarefas, histerese de energia dos Shader Processors (`SP_*_HYSTERESIS = 0`) e registradores de resolução (`REG_A8XX_RB_RESOLVE_CR_CNTL = 1`) entre as fatias de hardware independentes da GPU Adreno 8xx.
2. **Bugs Críticos de Sincronização, Timestamps e Sparse VMA no Backend `tu_knl_kgsl.cc` (Presentes no Mesa Upstream):**
   * **Crash `SIGSEGV` e FD não inicializado em `kgsl_syncobj_merge()` (`tu_knl_kgsl.cc:1136-1169`):** Passa `ret.fd` não inicializado quando `ret` e `sync` são `TS` de filas distintas, e chama `kgsl_syncobj_ts_to_fd(sync)` em um `sync` que já é `FD` (`sync->queue == NULL`, causando `SIGSEGV`) quando `ret` é `TS`.
   * **Bloqueio Infinito por `timeout = 0` em `wait_timestamp_safe()` (`tu_knl_kgsl.cc:833-862`):** No kernel KGSL da Qualcomm (`adreno_drawctxt_wait`), `timeout = 0` significa esperar infinitamente. Quando `get_relative_ms(abs_timeout_ns) == 0`, o Turnip bloqueia a thread chamadora no kernel segurando `timeline->mutex`, causando até $250\text{ ms/s}$ de travamento de CPU em `vkWaitSemaphores`.
   * **Crash ao Liberar Memória Sparse (`kgsl_sparse_vma_init()`):** Não chama `tu_dump_bo_init(dev, bo)`, deixando `bo->dump_bo_list_idx = 0` em vez de `~0`, o que provoca `SIGSEGV` em `tu_dump_bo_del()` ao destruir recursos sparse (DX12 / VKD3D-Proton).
   * **Rejeição de `VK_KHR_display` em `tu_knl_kgsl_load()`:** Aborta a criação de dispositivo quando camadas como Zink ou compositores ativam `VK_KHR_display`.
3. **Throttling Térmico Descompassado:** O perfil de controle de energia das OEMs em SoCs intermediários (linha "s") estrangula o clock da GPU de forma desproporcional sob cargas contínuas de emulação combinada (CPU + GPU + DRAM), agravado em forks que forçam `KGSL_CONSTRAINT_PWR_MAX` sem controle térmico.

### 6.2 Problemas no Driver Turnip (Mesa Freedreno Vulkan e Forks Modificados)
4. **Instabilidade Fatal no Modo GMEM (Tiling) e Dessincronia Matemática dos Caches CCU:** O cálculo de offsets da GMEM em `src/freedreno/common/fd6_gmem_cache.h` combinado com definições incorretas de `freedreno_devices.py` nos forks comunitários (`V38`, `WinNative`, `Banners-Turnip`, `DiskDVD`, `WinterMist010`) dessincroniza o enum de hardware `RB_CCU_CACHE_CNTL` do tamanho em bytes subtraído nos offsets (`THREE_QUARTER` = $768\text{ KB}$ no hardware vs. $384\text{ KB}$ no software em `sysmem`, ou `FULL` = $1.024\text{ KB}$ vs. $508\text{ KB}$ desalinhados em `gmem`, ou `HALF + HALF` = $1.024\text{ KB}$ no `DiskDVD`), além de usar `tile_align_w = 96` (3 fatias) em uma GPU de 2 fatias (`num_slices = 2`) ou reintroduzir o desconto legado `offset -= 0x78000` ($480\text{ KB}$) que provoca *unsigned integer underflow* (`-224 KB` / `0xFFFC8000`) nos $2\text{ MB}$ do Adreno 825 e 829.
5. **Corrupção no Sub-passo de Profundidade (LRZ) tanto em GMEM quanto em SYSMEM:**
   * No modo GMEM, forks anteriores a 04/11/2026 carecem do `lrz_fc_slice_pitch` por fatia (commit `2ce86eed`) e do alinhamento de `lrz_pitch` a 32 (commit `e1852a33`).
   * **No `mesa/main` atual (`tu_lrz.cc:852-876`):** A função `tu_lrz_before_sysmem_br<CHIP>()` contém um hardcode explícito `fd_lrzfc_layout<A7XX>` (`// FIXME hard-coding A7XX here and below is wrong!`). No Adreno 8xx (`fd_lrzfc_layout<A8XX>`), o bloco `fc2` ($4.096\text{ B}$) antecede `buffer[2]` e cada `buffer[i]` ocupa $1.024\text{ B}$, deslocando `buffer[0].depth_clear_val` de `0x838` para `0x2038`, `buffer[1].depth_clear_val` de `0x878` para `0x2438`, e `br_cur_buffer` de `0x8C0` para `0x2C00`. Como resultado, no modo `SYSMEM` com reuso de estado LRZ, o Adreno 8xx lê bits da máscara de *fast-clear* (`fc1_b`) achando que são o float `depth_clear_val` e grava lixo (`0xffffffff` = `NaN`) no registrador `GRAS_LRZ_DEPTH_CLEAR`!
   * **Falta de Emissão de `FORCE_BI_DIR_LRZ_DISABLE` e `GRAS_LRZ_COLOR_COMP_MASK` no `mesa/main`:** O Turnip oficial não seta `.force_bi_dir_lrz_disable = true` em `GRAS_SC_BIN_CNTL` durante renderização `sysmem` ou quando `disable_lrz` está ativo, nem emite `GRAS_LRZ_COLOR_COMP_MASK` (`0x810c`) em `tu6_emit_mrt_blend_state()`, causando conflitos bidirecionais de LRZ entre fatias.
6. **Sabotagem Silenciosa do Autotuner via `00-turnip-defaults.conf` (`prefer_sysmem` em DXVK/VKD3D), Falso-Positivo de `sampleShadingEnable` e Condicionais `<A7XX>` Residuais:**
   * A linha 48 de `src/freedreno/vulkan/00-turnip-defaults.conf` define `<option name="tu_autotune_algorithm" value="prefer_sysmem" />` para `DXVK|vkd3d`. Em `tu_autotune::get_optimal_mode()` (`src/freedreno/vulkan/tu_autotune.cc:1882-1894`), `PREFER_SYSMEM` aciona um `early_return_mode` que força `render_mode::SYSMEM` em **100% dos render passes normais** de jogos Windows (Winlator/GameHub/MiceWine), ignorando completamente a GMEM mesmo quando habilitada e empurrando todos os frames diretamente para os bugs de `SYSMEM`.
   * Em `src/freedreno/vulkan/tu_shader.cc` (`tu_lower_nir`), `if (key->force_sample_interp)` não verifica `nir->info.fs.uses_sample_shading`, fazendo com que o falso-positivo de `sampleShadingEnable` do `vkd3d-proton` escale todos os Fragment Shaders para execução por amostra (derrubando o FPS em mais de 25% e desativando Early-Z).
   * Funções críticas do driver no `mesa/main` ainda possuem checagens `CHIP == A7XX` ou chamadas template `<A7XX>` hardcoded quando executam em `A8XX`:
     * `tu_binning_conservative_rast<CHIP>` (`src/freedreno/vulkan/tu_pipeline.cc:3479`) checa `CHIP == A7XX` em vez de `CHIP >= A7XX`.
     * `tu_CmdWriteAccelerationStructuresPropertiesKHR` (`src/freedreno/vulkan/tu_query_pool.cc:2178`) chama `tu_emit_cache_flush<A7XX>(cmd)` em vez de `TU_CALLX(cmd->device, tu_emit_cache_flush)(cmd)`.
     * `tu_emit_subpass_fsr<CHIP>` (`src/freedreno/vulkan/tu_cmd_buffer.cc:6967, 6991`) e `tu_emit_rt_workaround<CHIP>` (`tu_cmd_buffer.cc:345-351, 438`) invocam `<A7XX>` hardcoded, e `tu_image_init` (`tu_image.cc`) rebaixa `TILE6_3` para `TILE6_LINEAR` em imagens `MUTABLE_FORMAT` comprimidas (`DRM_FORMAT_MOD_QCOM_COMPRESSED`).
7. **Lacunas e Bugs no Compilador `ir3`, Código Morto de LLM e Descritores A8xx:**
   * `supports_double_threadsize = True` ativado indevidamente no `whitebelyash/mesa-unified` (`031918ec` / Turnip V38) e `reg_size_vec4` reduzido de `128` para `96` em `a8xx_gen1` quebram 660/660 testes de subgrupo e mutilam o banco de registradores; o hardware A8xx exige `supports_double_threadsize = False` combinado com particionamento de meia-onda (`HALF_SUBGROUP_SIZE 32`) no `ir3_lower_subgroups.c`.
   * Expressão booleana quebrada `const bool is_a830 = chip_id == 0xffff44050000 || 0x44050001;` em `tu_pipeline.cc` (`DiskDVD` / `whitebelyash` / Turnip V38) e ~100 linhas de código morto gerado por LLM (`ir3_get_gpu_profile`) em `ir3_compiler.c` (`DiskDVD` / `WinterMist010` commit `bc16322d`).
   * Falta de `NUM_ELEMENTS` nos descritores de buffer A8xx antes do commit `5b2db4b8` (`fd6_view.cc`), falta de divisão de `vkCmdDrawIndirect` grandes (`max_fetch_size = ((1 << 20) - 1) * 4`, commits `14656cee`/`7638039f`), falta de `WFI` antes de leitura de registradores no CP (MR `!45937`), perda de precisão alfa de 2 bits em `A2B10G10R10_UNORM` no KGSL (MR `!45973`), falta de sanitização de coordenadas de Cube Map (`0,0,0` / `NaN`) e invalidação bindless incompleta.
8. **Ausência de Mapeamento Específico para o Adreno 825 no Upstream:** O arquivo `freedreno_devices.py` no Mesa oficial ainda não possui a entrada `0x44030000` (Adreno 825), e a entrada `0x44030a20` (Adreno 829, também de $2\text{ MB}$ de GMEM) herda `sysmem_per_ccu_depth_cache_size = 192 * 1024` do `a8xx_gen2`, estourando os $2.048\text{ KB}$ de GMEM ($2.144\text{ KB}$) com underflow de $-96\text{ KB}$ (`0xFFE80000`).

### 6.3 Problemas no Driver Proprietário da Qualcomm (`vulkan.adreno.so`) e Integração Android KGSL
9. **Hang Fatal na Desalocação de Command Streams no KGSL (`IOCTL_KGSL_GPUMEM_FREE_ID`):** No Adreno 8xx, liberar buffers de comando (`ib1`/`ib2`) diretamente sem desmapear antes um alias virtual (`KGSL_MEMFLAGS_VBO`) e sem reciclar IBs retirados trava a GPU devido ao pré-buscador especulativo do Command Processor.
10. **Remoção do Header `'gmsm'` no Gralloc do Android 15/16, `UBWC_5`/`UBWC_6` e OOB Read em `u_gralloc_fallback.c`:** O fallback do Turnip falha em detectar buffers comprimidos UBWC sem o backend `u_gralloc_aimapper.c` (AIMapper5 SP-HAL) e sem os `case 5:`/`case 6:` em `tu_knl_kgsl.cc`, enquanto o patch de fallback do `whitebelyash` (`742f5776`) removeu a checagem `numInts >= 2`, causando leitura fora dos limites em handles pequenos.
11. **Inconformidade com Especificações de Desktop do Vulkan no Driver Proprietário:** O driver proprietário não oferece suporte confiável a extensões vitais para tradutores DirectX (`VK_EXT_custom_border_color`, `VK_EXT_transform_feedback`) e sofre com estouro de alocações dinâmicas em DXVK/VKD3D.

---

## Conclusão do Relatório

O desempenho decepcionante e instável da linha Adreno 8xx — e de modo particular do **Snapdragon 8s Gen 4** — em cenários de emulação e camadas gráficas avançadas não é decorrente de falta de transistores ou capacidade teórica de silício, mas sim de uma **profunda defasagem na camada de software e drivers gerada por uma reformulação disruptiva da microarquitetura de hardware**, somada a patches comunitários que, ao tentarem contornar o problema empiricamente, introduziram colisões matemáticas de GMEM/CCU e regressões de subgrupos.

Enquanto plataformas como o Snapdragon 8 Gen 2 e Snapdragon 870 colhem os frutos de um ecossistema de engenharia reversa quase perfeito (onde cada registrador, pipeline de GMEM e instrução `ir3` é dominado), o Adreno 8xx encontra-se na transição crítica para a maturidade. No caso específico do Snapdragon 8s Gen 4, reunir as correções cirúrgicas validadas por traces de hardware (`Vauzi-17`, `Droid-VM`, `faux123`, `MaxsTechReview`, `Hugo223` e `Danylo Piliaiev`) com uma aritmética impecável dos $2\text{ MB}$ de GMEM e 2 fatias é a chave exata para destravar todo o potencial da GPU `Adreno 825`.
