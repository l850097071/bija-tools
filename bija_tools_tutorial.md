# bija-tools v0.1 详细教程

> 计算化学科研工具链：从文献调研到计算报告，一条命令搞定。

---

## 目录

1. [安装](#1-安装)
2. [快速体验：5分钟全管线](#2-快速体验5分钟全管线)
3. [工具详解](#3-工具详解)
   - [3.1 vaspgen — VASP输入文件生成器](#31-vaspgen--vasp输入文件生成器)
   - [3.2 gate — HPC提交前门控验证](#32-gate--hpc提交前门控验证)
   - [3.3 litsearch — 文献深度搜索](#33-litsearch--文献深度搜索)
   - [3.4 outcarp — OUTCAR解析+计算报告](#34-outcarp--outcar解析计算报告)
4. [配方库](#4-配方库)
5. [常见问题](#5-常见问题)

---

## 1. 安装

### 前提条件
- Python 3.9 或更高版本
- pip（Python包管理器）

### 安装步骤

```bash
# 进入bija-tools目录
cd bija-tools

# 安装（开发模式，修改代码后无需重新安装）
pip install -e .

# 验证安装
bija-tools --help
```

安装成功后，你会看到四个子命令：

```
usage: bija-tools [-h] {vaspgen,gate,litsearch,outcarp} ...

positional arguments:
  {vaspgen,gate,litsearch,outcarp}
    vaspgen             Generate VASP input files
    gate                Validate HPC job before submission
    litsearch           Deep literature search
    outcarp             Parse OUTCAR + generate report
```

### 依赖
- Flask（仅Web UI需要）：`pip install flask`
- 其余工具零额外依赖——纯Python标准库。

---

## 2. 快速体验：5分钟全管线

假设你要计算Co₃O₄的催化性质。完整流程：

```bash
# Step 1: 文献调研——了解Co₃O₄催化CO₂还原的研究现状
bija-tools litsearch "Co3O4 CO2 reduction DFT catalyst" --years 2023-2026 --limit 10

# Step 2: 生成VASP输入文件——从化学式一键生成INCAR/POSCAR/KPOINTS
bija-tools vaspgen --formula "Co3O4" -o co3o4_job

# Step 3: 提交前验证——10道门控检查，防止GPU小时浪费
bija-tools gate co3o4_job --preset vasp

# Step 4: （在HPC上提交作业 sbatch run_vasp.job）

# Step 5: 计算完成后——解析OUTCAR，生成可读报告
bija-tools outcarp OUTCAR
```

这就是完整的研究→生成→验证→解析管线。

---

## 3. 工具详解

### 3.1 vaspgen — VASP输入文件生成器

**功能**：从CIF文件或化学式生成INCAR、POSCAR、KPOINTS、POTCAR推荐和作业脚本。

**为什么用它**：手工写INCAR容易漏参数。vaspgen自动检测金属/磁性/溶剂，给出合理默认值，并附带注释说明哪些参数需要你确认。

#### 3.1.1 基础用法

```bash
# 从化学式生成（快速测试用）
bija-tools vaspgen --formula "Co3O4" -o my_job

# 从CIF文件生成（生产用——有真实结构）
bija-tools vaspgen --cif structure.cif -o my_job

# 指定计算类型
bija-tools vaspgen --formula "H2O" --calc singlepoint -o sp_job
```

#### 3.1.2 生成的文件

```
my_job/
├── INCAR           # 主输入参数文件
├── POSCAR          # 原子结构文件
├── KPOINTS         # k点网格文件
├── POTCAR_INFO.txt  # POTCAR构建命令
├── run_vasp.job    # SLURM作业脚本
└── VASPGEN_NOTES.txt # 注意事项（必读！）
```

#### 3.1.3 INCAR自动检测规则

| 检测条件 | INCAR设置 | 原因 |
|---------|----------|------|
| 含Fe/Co/Ni/Mn/Cr/V/Cu/Ti | `ISMEAR=1 SIGMA=0.2` | 金属体系，用Methfessel-Paxton |
| 不含过渡金属 | `ISMEAR=0 SIGMA=0.05` | 半导体/绝缘体 |
| 含Fe/Co/Ni/Mn/Cr | `ISPIN=2 MAGMOM=...` | 自动设初始磁矩 |
| 结构优化 | `IBRION=2 NSW=100 ISIF=3` | 共轭梯度+优化晶格 |
| 单点能 | `NSW=0 IBRION=-1` | 不做离子移动 |
| 所有体系 | `IVDW=12` | DFT-D3色散修正 |

#### 3.1.4 POTCAR构建

vaspgen不生成POTCAR文件（受VASP版权保护），但告诉你构建命令：

```bash
# vaspgen输出的构建命令（在POTCAR_INFO.txt中）
cat POTCAR_PBE/Co POTCAR_PBE/O > POTCAR
```

#### 3.1.5 KPOINTS自动计算

```
K点密度规则：
  金属体系 → 0.04/Å (更密)
  半导体   → 0.05/Å
  真空方向 → 固定为1
```

#### 3.1.6 支持的59种元素

H, Li, C, N, O, F, Na, Mg, Al, Si, P, S, Cl, K, Ca, Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, Ga, Ge, As, Se, Br, Rb, Sr, Y, Zr, Nb, Mo, Ru, Rh, Pd, Ag, In, Sn, Sb, Te, I, Cs, Ba, La, Ce, Hf, Ta, W, Re, Os, Ir, Pt, Au, Hg, Pb, Bi

#### 3.1.7 注意事项（VASPGEN_NOTES.txt）

每次生成后务必阅读此文件。典型提示：
- "WARNING: Simple cubic guess. Use --cif for real structure."（从化学式生成时）
- "MAGMOM auto-set. Verify initial magnetic moments for your system."（含磁性元素时）
- "ISIF=3 (cell+ions). For surface slabs, change to ISIF=2."（做表面计算时）

---

### 3.2 gate — HPC提交前门控验证

**功能**：在`sbatch`之前运行10道门控检查。任一未通过=禁止提交。防止GPU小时浪费在错误输入上。

**为什么用它**：78%的科研人员每周在计算流程管理上花10+小时。最常见的错误——POTCAR不匹配、忘记偶极修正、K点不够——全部可被自动检测。

#### 3.2.1 支持的预设

| 预设 | 适用软件 | 门控数 | 检查内容 |
|------|---------|--------|---------|
| `vasp` | VASP | 5 | 四文件、POTCAR元素、INCAR合理性、重复检测、作业脚本 |
| `pwmat` | PWmat | 10 | etot.input、NPROC、结构、赝势、关键参数、溶剂、层级、重复、模板、脚本 |
| `gaussian` | Gaussian | 6 | 输入文件、Route段、电荷/自旋、坐标、重复检测、脚本 |
| `quick` | 通用 | 3 | 输入文件、结构文件、脚本语法 |

#### 3.2.2 CLI用法

```bash
# 验证VASP作业目录
bija-tools gate my_job --preset vasp

# 验证PWmat作业
bija-tools gate pwmat_job --preset pwmat

# 快速检查（仅3道门控）
bija-tools gate my_job --preset quick

# 启动Web界面（拖拽上传文件）
bija-tools gate --web
```

#### 3.2.3 CLI输出解读

```
==================================================
sbatch_gate — VASP preset
Workdir: co3o4_job
==================================================
  [OK] GATE V1: VASP四文件 — All 4 files present
  [OK] GATE V2: POTCAR元素 — Elements: Co, O
  [OK] GATE V3: INCAR合理性 — INCAR looks reasonable
  [OK] GATE V4: 重复检测 — No converged REPORT — OK to submit
  [OK] GATE V5: 脚本语法 — run_vasp.job OK
==================================================
Result: 5/5 gates passed
ALL CLEAR — safe to submit
==================================================
```

失败示例：
```
  [FAIL] GATE V1: VASP四文件 — Missing: KPOINTS
  [FAIL] GATE V2: POTCAR元素 — POTCAR has 2 elements, POSCAR line6 has 3
==================================================
Result: 3/5 gates passed
BLOCKED — 2 gate(s) failed
==================================================
```

#### 3.2.4 Web界面

```bash
bija-tools gate --web
# → 打开浏览器访问 http://localhost:8765
```

功能：拖拽上传VASP/PWmat/Gaussian输入文件 → 一键验证 → 显示每道门控的通过/失败详情。

#### 3.2.5 VASP门控详解

| 门控 | 检查内容 | 常见失败原因 |
|------|---------|------------|
| V1 | INCAR/POSCAR/POTCAR/KPOINTS存在 | 忘记复制KPOINTS |
| V2 | POTCAR元素顺序与POSCAR一致 | POTCAR元素顺序搞反 |
| V3 | INCAR参数合理性 | ISMEAR=-5用于金属/NSW=0以为在做优化/ISPIN=2但没设MAGMOM |
| V4 | 重复提交检测 | REPORT文件显示已收敛 |
| V5 | 作业脚本语法 | 缺shebang/缺#SBATCH指令/缺mpirun |

#### 3.2.6 退出码（CI/CD集成）

```bash
bija-tools gate my_job --preset vasp
echo $?  # 0=全部通过, 1=有门控失败
```

可在SLURM提交脚本中集成：
```bash
#!/bin/bash
bija-tools gate . --preset vasp || exit 1
sbatch run_vasp.job
```

---

### 3.3 litsearch — 文献深度搜索

**功能**：输入研究问题→自动搜索Semantic Scholar→主题聚类→生成结构化综述报告。

**为什么用它**：传统文献检索：打开Google Scholar→一个关键词一个关键词试→手动整理→花2-3小时。litsearch：一行命令，30秒出综述框架。

#### 3.3.1 基础用法

```bash
# 基础搜索
bija-tools litsearch "CO2 reduction on single atom catalysts"

# 限定年份
bija-tools litsearch "DFT free energy calculation method" --years 2024-2026

# 限定数量
bija-tools litsearch "VASP machine learning potential" --limit 30

# 保存到文件
bija-tools litsearch "electrochemical CO2 reduction Cu" -o review.md
```

#### 3.3.2 输出解读

```
Literature Search Report
============================================================
Query: CO2 reduction on single atom catalysts
Date: 2026-06-01
Papers found: 20

Year range: 2023-2026
Total citations: 1,234
Top venue: Nature Communications

## Thematic Breakdown
  Catalysis: 8 papers (40%)
  DFT: 6 papers (30%)
  Machine Learning: 3 papers (15%)
  Review: 2 papers (10%)
  Experiment: 1 papers (5%)

## Top Cited Papers
  1. [234] Single-atom catalysis for CO2 conversion
     Wang et al. (2023) — Nature Communications
     Recent advances in single-atom catalysts...

## Priority Reading List
  1. ... (2026, 45 cites)
  2. ... (2025, 89 cites)
  3. ... (2024, 156 cites)
```

#### 3.3.3 主题聚类

litsearch自动将论文按主题分组。聚类关键词：

| 主题 | 匹配关键词 |
|------|----------|
| DFT | dft, density functional, first-principles, vasp, ab initio |
| Machine Learning | machine learning, neural network, deep learning, ml, ai |
| Catalysis | catalysis, catalyst, catalytic, reaction mechanism |
| CO2 Reduction | co2, carbon dioxide, co2rr, electroreduction |
| Experiment | experimental, synthesis, characterization, xrd, tem, xps |
| Review | review, perspective, roadmap, progress |

#### 3.3.4 API限速

Semantic Scholar免费API有速率限制。遇到限速会自动重试3次（间隔5秒/10秒）。如果持续失败，等待几分钟再试。

---

### 3.4 outcarp — OUTCAR解析+计算报告

**功能**：解析VASP的OUTCAR文件，提取关键数据，生成人类可读的计算报告。

**为什么用它**：OUTCAR动辄几百MB，手动`grep`找数据效率极低。outcarp自动提取所有关键信息并标出问题。

#### 3.4.1 基础用法

```bash
# 生成可读报告（默认）
bija-tools outcarp OUTCAR

# JSON输出（用于脚本/数据库）
bija-tools outcarp OUTCAR --json

# 提取能量收敛曲线
bija-tools outcarp OUTCAR --energy
```

#### 3.4.2 报告解读

```
============================================================
  VASP CALCULATION REPORT
  OUTCAR
============================================================
  Status:       CONVERGED              ← 电子步收敛状态
  VASP version: 6.4.3
  Elements:     Co O                   ← 自动识别元素
  Atoms:        48
  ENCUT:        450 eV
  K-points:     16
  NBANDS:       80
  Cell volume:  850.50 A^3

  Ionic steps:  5                       ← 离子步数
  Total SCF:    23 (4 avg/ionic)        ← 总电子步+平均
  Free energy:  -450.123456 eV          ← 最终自由能
  E(sigma->0):  -450.123000 eV          ← 外推到0展宽

  Max force:    0.0235 eV/A             ← 最大残余力
  Force RMS:    0.0157 eV/A
  Forces OK:    Yes                     ← 力收敛状态

  CPU time:     12346s (3.4h)
  Wall time:    6789s  (1.9h)

  SCF history per ionic step: [5, 4, 5, 5, 4]
  (min=4, max=5, avg=4.6)

  All checks passed. Calculation looks good.
============================================================
```

#### 3.4.3 自动问题检测

outcarp会自动标记以下问题：

| 检测条件 | 标记 |
|---------|------|
| `reached required accuracy` 未出现 | SCF not converged |
| Max force > 0.05 eV/Å | 力未收敛 |
| 离子步 ≥ 100 | 可能卡在NSW上限 |
| Max force = 0 但有离子步 | 可能NSW=0（单点能，非优化） |
| OUTCAR中有WARNING | 列出警告内容 |
| `Total CPU time` 缺失 | 未完成或崩溃 |

#### 3.4.4 JSON输出

```json
{
  "converged": true,
  "e_free_ev": -450.123456,
  "e0_ev": -450.123,
  "max_force": 0.0235,
  "force_rms": 0.0157,
  "ionic_steps": 5,
  "total_scf": 23,
  "scf_per_ionic": [5, 4, 5, 5, 4],
  "cpu_time_s": 12346,
  "wall_time_h": 1.89,
  "warnings": 0
}
```

适合批量处理多个计算目录：
```bash
for d in job_*/; do
  bija-tools outcarp "$d/OUTCAR" --json >> all_results.jsonl
done
```

---

## 4. 配方库

`recipes/index.html` — 浏览器直接打开即可使用的静态页面。

### 8个计算配方

| 配方 | 难度 | 核心INCAR参数 |
|------|------|-------------|
| CO₂吸附在金属表面 | 进阶 | `IVDW=11 IDIPOL=3 LDIPOL=.TRUE.` |
| 过渡态搜索(NEB) | 高级 | `IBRION=3 LCLIMB=.TRUE. IMAGES=5 SPRING=-5` |
| 声子频率计算 | 进阶 | `IBRION=5 NFREE=2 EDIFF=1E-8` |
| 隐式溶剂化(VASPsol) | 高级 | `LSOL=.TRUE. EB_K=80 ENCUT≥600` |
| 能带结构+DOS | 入门 | `ICHARG=11 LORBIT=11 NEDOS=2000` |
| Bader电荷分析 | 入门 | `LAECHG=.TRUE. ADDGRID=.TRUE.` |
| 体相结构优化 | 入门 | `ISIF=3 ENCUT≥520 EDIFF=1E-6` |
| DFT+U | 进阶 | `LDAU=.TRUE. LDAUTYPE=2 LASPH=.TRUE.` |

每个配方包含：INCAR参数（优化+静态）、KPOINTS建议、POTCAR注意事项、常见避坑清单。

---

## 5. 常见问题

### Q1: vaspgen生成的INCAR能直接用吗？

**不能直接不经审核使用。** vaspgen给出的是合理默认值，但每个计算体系有特殊性。务必将`VASPGEN_NOTES.txt`中的每条NOTE逐一确认后再提交。

### Q2: gate总是报POTCAR缺失？

POTCAR是VASP授权文件，vaspgen不会生成它。按`POTCAR_INFO.txt`中的命令手动构建POTCAR后再运行gate。

### Q3: litsearch返回"HTTP 429"？

Semantic Scholar API限速。等待几分钟后重试。如需高频使用，到Semantic Scholar申请API key。

### Q4: outcarp报"Max force = 0"？

你的计算可能是NSW=0（单点能），不是结构优化。检查INCAR中的NSW参数。

### Q5: 怎么添加自定义门控？

修改`gate/gate_engine.py`中的PRESETS字典，或创建自定义门控列表传入`run_gates(workdir, custom_gates=my_gates)`。

### Q6: 支持Gaussian/Quantum ESPRESSO吗？

gate已支持Gaussian预设。QE预设未实现——欢迎贡献。vaspgen专门为VASP设计，但INCAR生成逻辑可适配其他软件。

### Q7: 怎么部署到实验室服务器？

```bash
# 在服务器上
git clone <repo-url> bija-tools
cd bija-tools
pip install -e .

# 启动Web界面（实验室共享）
bija-tools gate --web --port 80
```

### Q8: 和pymatgen/ASE的关系？

互补，非竞争。pymatgen/ASE是大而全的材料科学库。bija-tools是轻量级管线——零依赖（除Flask），专注"生成→验证→解析"这一高频工作流。
