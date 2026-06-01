# 知乎 #70 避坑系列#33：VASP计算的"暗数据"——那些你算对了但没报告的参数

**标签**：#计算化学 #DFT #VASP #科研方法 #避坑系列
**字数**：~3500字

---

## 什么是"暗数据"？

在DFT计算中，"暗数据"（Dark Data）是指那些**你算了、用了、但没在方法段报告的参数和决策**。

举个例子：你的方法段写了`ENCUT=520, KPOINTS=4×4×4`，看起来很完整。但审稿人不知道的是——你试过ENCUT=400发现能量差0.03eV→改成了520→发现和500差不多→最终用了520。你做了收敛测试但没报告。

"暗数据"的存在让审稿人无法判断：
- 你的参数选择是"经过验证的最优值"还是"师兄给的默认值"？
- 你的结果在其他参数下是否稳健？
- 别人能不能独立复现你的计算？

本文列出VASP计算中**最常见的7类暗数据**——以及如何让它们变成"明数据"。

---

## 暗数据1：你试过但放弃的初始构型

**场景**：你测试了CO₂在Co₃O₄(110)表面的12个吸附位点，论文中只报告了能量最低的3个。那9个"失败"的位点去哪了？

**为什么重要**：审稿人不知道你搜全了。如果最低能量位点恰好不在你测试的12个里→你的全部结论建立在不完整的位点搜索上。

**明数据转换**：在SI中放一个表：

| 位点 | 吸附能(eV) | 最终Co-O距离(Å) | 备注 |
|------|-----------|-----------------|------|
| Top-Co | -0.52 | 1.89 | 本文讨论 |
| Bridge-Co-Co | -0.48 | 1.94 | 亚稳态 |
| Hollow-O3 | -0.35 | 2.15 | - |
| Top-O | 不吸附 | - | CO₂脱附 |
| ... | ... | ... | ... |

**一句话堵死审稿人**："All 12 possible adsorption sites were systematically sampled (Table S1), with only the 3 most stable reported in the main text."

---

## 暗数据2：你做过但没报告的收敛测试

**场景**：你做了ENCUT收敛测试（400→450→500→520→550），发现520以后能量变化<1 meV/atom。但论文中只写了"ENCUT=520"。

**为什么重要**：审稿人不知道520是"经过收敛测试的最优值"还是"随便选的"。没有收敛测试=没有精度辩护。

**明数据转换**：在SI中放收敛曲线图：

- ENCUT: 1.0×ENMAX → 1.8×ENMAX（至少4个点）
- KPOINTS: KSPACING 0.04→0.03→0.02→0.015
- 真空层: 12→15→18→20Å（表面计算）
- SMEAR: SIGMA 0.01→0.05→0.10→0.20

**一句话堵死审稿人**："Convergence tests (Fig. S1-S3) confirm that ENCUT=520, KSPACING=0.03, and vacuum=15Å yield energies converged to <1 meV/atom."

---

## 暗数据3：你选了的磁性构型但没解释为什么

**场景**：你的体系含Co（d⁷），你测试了FM和AFM两种磁构型，FM低了0.15eV，所以你用了FM。但论文中只写了"spin-polarized calculations were performed"。

**为什么重要**：没有显式声明磁性构型测试→审稿人可能发现AFM其实更稳定→你的结构不是基态→结论被推翻。

**明数据转换**：方法段写清楚：

"Ferromagnetic (FM) and three antiferromagnetic (AFM) configurations were tested (Fig. S4). The FM configuration was 0.15 eV lower in energy than the most stable AFM configuration and was therefore used for all subsequent calculations. The converged magnetic moment on Co is 2.7 μB."

---

## 暗数据4：你用了但没说明的默认值

**场景**：VASP有几十个有默认值的参数。你没有在INCAR里显式设置它们→它们用了默认值→但默认值可能在不同VASP版本中不同。

**常见的"静默默认值"陷阱**：

| 参数 | 默认值 | 风险 |
|------|--------|------|
| ISMEAR | 1 | 半导体应该用0！默认1是金属的 |
| LREAL | .FALSE. | 大体系该用Auto但默认关闭→慢3-5× |
| GGA_COMPAT | .TRUE. (旧版) | VASP 6.x已改默认→不同版本结果差 |
| LASPH | .FALSE. | 默认关闭但几乎所有计算都该开 |
| LMAXMIX | 2 | d电子体系该用4, f电子该用6 |
| ISYM | 2 (默认) | 声子计算该用0→否则对称性错误 |

**明数据转换**：在SI中放完整的INCAR文件（包含所有显式设置的参数），并标注版本号。

---

## 暗数据5：你固定了但没有辩护的原子坐标

**场景**：做表面吸附计算时，你固定了底下3层原子（"bottom 3 layers were fixed"）。但你没有解释为什么是3层，不是2层也不是4层。

**为什么重要**：固定层数影响吸附能。固定太少→虚 relax；固定太多→人工约束。审稿人需要看到你测试过。

**明数据转换**：做一个固定层数收敛测试：

| 固定层数 | 吸附能(eV) | 备注 |
|---------|-----------|------|
| 2层固定 | -0.52 | - |
| 3层固定 | -0.50 | 本文采用 |
| 4层固定 | -0.50 | 与3层无差异 |

**一句话**："Test calculations with 2, 3, and 4 fixed bottom layers showed that adsorption energies are converged within 0.02 eV with 3 fixed layers."

---

## 暗数据6：你用过的AELAS/应力张量信息

**场景**：你做ISIF=3优化→得到了晶格参数→论文中报告了a,b,c值。但你没有报告应力张量→审稿人无法判断优化是否充分收敛。

**为什么重要**：晶格参数收敛≠应力收敛。残余应力>1 kBar→晶格还没优化完→后续所有性质计算基于未收敛的结构。

**明数据转换**：在SI中报告：
- 优化后的晶格参数（实验值对比）
- 残余应力张量（所有分量<1 kBar）
- 总能量vs离子步数的收敛曲线

---

## 暗数据7：你换了但没说的赝势

**场景**：你用Co的`Co_pv`赝势做优化，但做Bader电荷时发现芯电子不够→悄悄换成`Co_sv_GW`→Bader结果变了0.3e。文章中只写了"PAW pseudopotentials were used"。

**为什么重要**：不同赝势给出不同的电荷密度→Bader/ELF/COHP等分析结果不同。审稿人自己跑一遍发现用的是普通赝势不是GW→结果不可复现。

**明数据转换**：在方法段精确列出每个元素的赝势：

"PAW pseudopotentials were used with the following valence configurations: Co (3p⁶3d⁷4s², Co_pv), O (2s²2p⁴, O), C (2s²2p², C). The Co_pv potential includes semi-core 3p states to improve Bader charge analysis accuracy."

---

## 终极方法段模板（堵死所有"暗数据"质疑）

```
Computational Methods:

DFT calculations were performed using VASP 6.5.1 with the PBE 
functional. PAW pseudopotentials with explicit valence configurations 
are listed in Table S1. 

Convergence tests (Fig. S1-S3) established ENCUT=520 eV 
(1.3 x ENMAX) and Γ-centered k-point mesh with KSPACING=0.03 as 
sufficient to converge total energies to <1 meV/atom.

All 12 possible CO2 adsorption sites on Co3O4(110) were systematically 
sampled (Table S2). FM and 3 AFM magnetic configurations were tested 
(Fig. S4); FM was energetically most favorable. The bottom 3 atomic 
layers were fixed based on convergence tests (Table S3).

Post-processing: Bader charges were calculated using the Henkelman 
algorithm with FFT grids converged to 2x default (Fig. S5). DDEC6 
charges (Chargemol) serve as cross-validation (Table S4).

Complete INCAR files for all calculation types are provided in the SI.
```

---

## 暗数据转换清单

| # | 暗数据 | 明数据转换 | 放哪 |
|---|--------|-----------|------|
| 1 | 试过的位点 | 全部位点吸附能表 | SI Table |
| 2 | ENCUT/K点收敛 | 收敛曲线图 | SI Figure |
| 3 | 磁构型测试 | FM/AFM能量对比 | SI Figure |
| 4 | 默认值依赖 | 完整INCAR文件 | SI Text |
| 5 | 固定层数 | 层数收敛测试表 | SI Table |
| 6 | 残余应力 | 应力张量报告 | SI Table |
| 7 | 赝势选择 | 精确赝势列表 | 方法段 |

---

## 总结

暗数据不是造假——它们是你做了但没报告的工作。问题是：**审稿人不知道你做了**。

每一条暗数据都是一个潜在的审稿意见。转换成明数据≈提前回复了审稿人还没提出的问题。

**投Nano-XX/Nature XX的秘诀**：不是计算结果比别人好，是你的SI比别人完整3倍。审稿人看完你的SI→找不到可以质疑的角度→Accept with minor revision。

---

**预告**：下一期避坑#34：**SI不是垃圾场——如何把你的Supplementary Information从"形式要求"变成"审稿人沉默器"**

---

*本文由Bija辅助生成，经人工深度审核。避坑系列33/50完成（66%）。*
*69篇知乎文章草稿就绪·笔名bija | 待宿主发布*
