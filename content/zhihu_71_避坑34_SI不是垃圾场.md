# 知乎 #71 避坑系列#34：SI不是垃圾场——如何把Supplementary Information变成"审稿人沉默器"

**标签**：#计算化学 #DFT #论文写作 #SI #避坑系列
**字数**：~3200字

---

如果你觉得SI（Supplementary Information）只是"正文放不下的东西扔进去的地方"，那么你已经输了。

一个好的SI不是垃圾场——它是**审稿人的沉默器**。审稿人打开你的SI → 发现每个可能质疑的角度都已经被提前回答了 → 无话可说 → "The SI is comprehensive" → Accept。

今天这篇避坑指南，把SI的5个致命错误和正确做法讲透。

---

## 错误1：把SI当作"正文的垃圾桶"

**症状**：SI里堆满了正文放不下的图、表、文字。没有结构、没有逻辑、没有叙事线。审稿人打开后：滚动5秒→找不到想验证的东西→关闭→开始写质疑。

**正确做法**：SI应该有独立的叙事结构。

**SI的黄金三段式**：
1. **验证段**（前20%）：收敛测试/精度验证/方法辩护
2. **补充段**（中60%）：正文没放的构型/数据/测试
3. **文档段**（后20%）：INCAR完整参数/所用赝势/软件版本

**格式上**：SI的每个Figure/Table都应该有"一句话总结"——正文中提到"see Fig. S3"时，审稿人不用读完整个SI才理解S3在说什么。

**一句话**："See Fig. S3 for the ENCUT convergence test, which confirms that 520 eV converges total energies to <1 meV/atom."

---

## 错误2：收敛测试放在正文——SI里却没有原始数据

**症状**：正文里一句"ENCUT was set to 520 eV based on convergence tests (see SI)"。SI里只有一个图，但**没有原始数据表**。审稿人想验证你的收敛判据（<1 meV/atom）→无法核实→质疑。

**正确做法**：收敛测试图 + 原始数据表 = 标配。

| ENCUT (eV) | E_total (eV) | ΔE vs 550eV (meV/atom) | Max Force (eV/Å) |
|------------|-------------|------------------------|-------------------|
| 400 | -456.782 | 3.2 | 0.032 |
| 450 | -456.791 | 1.8 | 0.028 |
| 500 | -456.798 | 0.6 | 0.024 |
| 520 | -456.800 | 0.2 | 0.023 |
| 550 | -456.801 | 0.0 | 0.022 |

**关键**：ΔE列不能用"meV/cell"（审稿人立刻问"cell里有几个原子？"），必须用meV/atom。这一个小细节体现了你的专业度。

---

## 错误3：关键信息放在正文——SI里没有

**症状**：正文只报告了能量最低的吸附构型。审稿人问"你测试过其他位点吗？"→你回答"当然测试过"→审稿人"那为什么不在SI里放？"

这是最冤的——你做了工作但没写，审稿人以为你没做。

**正确做法**：任何正文中省略的信息，只要审稿人可能问的，全放SI。

**必放SI的内容清单**：
- [ ] 所有测试过的位点/构型+能量对比表
- [ ] 所有磁构型(FM/AFM/AFM2)的对比
- [ ] 完整INCAR参数（不是"similar to Ref X"，是完整文件）
- [ ] 赝势精确列表（每个元素的POTCAR名称）
- [ ] 软件版本号（精确到小版本，如VASP 6.5.1）
- [ ] 残余应力张量（结构优化后）
- [ ] 声子谱（如果做了）或结构稳定性证明

---

## 错误4：SI的图表没有"独立可读性"

**症状**：SI里的Figure S5标题是"Fig. S5. Results of calculations." 审稿人：？？？

**正确做法**：SI中每个图表必须有完整自解释的标题。审稿人不需要翻回正文就能理解。

**好标题 vs 坏标题**：

| 坏 | 好 |
|----|-----|
| "Fig. S1. Convergence tests." | "Fig. S1. ENCUT convergence: total energy difference per atom (meV) vs. plane-wave cutoff (eV) for Co3O4 bulk. The 520 eV cutoff converges energies to <1 meV/atom." |
| "Table S2. Adsorption energies." | "Table S2. CO2 adsorption energies (eV) on all 12 tested sites of Co3O4(110), including both FM and AFM magnetic configurations. The 3 most stable sites are discussed in the main text." |

---

## 错误5：SI太长——审稿人不看

**症状**：SI有40页PDF，审稿人打开→"too long"→不看了→直接提问→你被迫在response里重新解释SI已经有的内容。

**正确做法**：SI的第一页有一个"导航页"。

**SI导航页模板**：

```
Supplementary Information: [论文标题]

Contents:
  S1. Computational Details (p.2-3)
    - Complete INCAR parameters (Table S1)
    - Pseudopotential list (Table S2)
  S2. Convergence Tests (p.4-6)
    - ENCUT convergence (Fig. S1, Table S3)
    - K-point convergence (Fig. S2)
    - Vacuum layer convergence (Fig. S3)
  S3. Structure Search (p.7-10)
    - All tested adsorption sites (Table S4)
    - Magnetic configuration comparison (Fig. S4, Table S5)
    - Layer-fixing convergence test (Table S6)
  S4. Supplementary Analysis (p.11-14)
    - DDEC6 charge cross-validation (Table S7)
    - PDOS for all configurations (Fig. S5-S8)
    - Stress tensor after relaxation (Table S8)
```

审稿人看到这个导航→定位自己想验证的部分→2分钟验证完→"SI is complete and well-organized"。

---

## 终极SI质量自检

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 独立可读 | 不看正文能理解SI的每个图表 |
| 2 | 收敛原始数据 | 收敛图+原始数据表=标配 |
| 3 | 所有测试构型 | 位点搜索表+磁构型对比 |
| 4 | 完整INCAR | 不是"similar to Ref"，是完整文件 |
| 5 | 精确赝势 | 每个元素的具体POTCAR名称 |
| 6 | 导航页 | SI第一页有目录+页码 |
| 7 | meV/atom | 所有能量差用per atom，不是per cell |
| 8 | 版本号 | VASP 6.x.y（精确到小版本） |
| 9 | 应力张量 | 结构优化后的残余应力<1 kBar |
| 10 | SI正文双向引用 | 正文每个"see SI"→SI中有对应；SI中每个图表→正文有引用 |

---

## 总结

SI不是论文的附属品——它是审稿人验证你科研严谨性的主要窗口。正文说服编辑，SI说服审稿人。

**核心公式**：好的SI = 审稿人想问的所有问题 × 提前回答 × 结构化呈现 = 审稿人沉默 = 顺利通过。

---

**预告**：下一期避坑#35：**过渡态搜索的10个致命陷阱——为什么你找到的TS可能不是真正的TS**

---

*本文由Bija辅助生成，经人工深度审核。避坑系列34/50完成（68%）。*
*70篇知乎文章草稿就绪·笔名bija*
