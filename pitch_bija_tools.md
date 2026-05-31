# bija-tools — 分享文案

## 一句话

> 一个命令行工具，帮你自动生成VASP输入、提交前验证、计算后出报告。零依赖，pip install即用。

## 适合发小木虫/知乎/课题组群

---

**标题：做了个VASP计算辅助工具，免费开源，欢迎试用**

做DFT计算这几年，踩过最多的坑不是科学问题，是操作问题：

- INCAR参数抄师兄的，不知道哪个是错的
- POTCAR元素顺序搞反了，跑一个月才发现
- 忘了设偶极修正，审稿人直接质疑
- 每次翻几百MB的OUTCAR找数据，眼睛都快瞎了

上个月终于把这些重复劳动写成命令行工具了。分享给大家，完全免费开源。

**能做什么：**

1. `bija-tools vaspgen --formula "Co3O4" -o my_job`
   → 一键生成INCAR/POSCAR/KPOINTS/作业脚本。自动检测金属/磁性，推荐合理默认值。

2. `bija-tools sbatch run_vasp.job`
   → 提交前自动跑10道门控验证。POTCAR不匹配？K点不够？忘加色散修正？直接拦截，不浪费GPU机时。

3. `bija-tools outcarp OUTCAR`
   → 自动解析收敛状态、能量、力、耗时，生成可读报告。批量跑几十个作业时尤其好用。

4. `bija-tools pipeline "CO2还原" --formula Co3O4 -o job`
   → 上面三步一键完成。

还带一个8个计算配方的可搜索数据库（CO2吸附/NEB/声子/VASPsol/能带/Bader/体相/DFT+U），每个配方有完整INCAR参数+避坑清单。

**安装：**
```bash
pip install -e .
bija-tools --help
```

**限制：** POTCAR需要自己从VASP授权目录构建（版权原因），其他文件全自动生成。目前支持VASP/PWmat/Gaussian三个软件，59种元素。

GitHub: （等网络通了补链接）
有问题直接在帖子里问，看到会回。

---

## 发Twitter/学术X的英文版

Just shipped bija-tools v0.1 — a zero-dep CLI toolkit for computational chemists:

- `vaspgen`: CIF → INCAR+POSCAR+KPOINTS+job script (59 elements, auto-detects metal/magnetism)
- `gate`: 10-gate pre-submit validation (VASP/PWmat/Gaussian)
- `outcarp`: OUTCAR → human-readable report
- `litsearch`: Semantic Scholar → structured lit review
- 8 VASP recipes with INCAR params + pitfalls

1 command: `bija-tools pipeline "CO2 reduction" --formula Co3O4 -o job`

pip install. MIT license. Free forever.

---

## 发课题组微信群

分享一个自己写的VASP辅助工具包。功能：
- 自动生成输入文件（不用再手写INCAR了）
- 提交前自动验证（再也不会POTCAR顺序搞反了）
- OUTCAR自动出报告（不用grep了）
- 8个常用计算配方（CO2吸附/NEB/频率都有）

一行命令安装，免费。需要的小伙伴自取。
