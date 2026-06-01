# X轮笔记 — 型男日课#30 (2026-06-01)

## X74: COHP/ICOHP分析常见误区文献搜索
- COHP vs -COHP vs COOP三重符号陷阱：原始COHP负=成键，-COHP正=成键（与COOP对齐）
- 论文未标注绘制的是COHP还是-COHP → 审稿人直接拒稿风险
- ICOHP跨元素对不可比：C-C vs C-H天然标度不同，过渡金属-非金属vs主族共价键值域完全不同

### Charge Spilling投影质量（Scientific Data 2023基准）
- <2% 优秀，2-5% 可接受，>5% 不可靠
- 极端案例：BaO₂缺少5d基函数→spilling 46.7%
- Lowdin正交化恢复Hilbert空间但不保证化学可解释性
- bandOverlaps.lobster：任何k点偏离>0.1→数据存疑

### 费米能级陷阱
- GGA带隙偏小30-50%→半导体ICOHP可能包含不应占据的态
- 金属体系smearing→ICOHP从"占据态积分"变为"态密度加权积分"
- 需报告E_F附近±1eV的-pCOHP细节

### 自旋极化
- 磁性体系必须分α/β通道
- 反铁磁体系不同子晶格COHP可能反相→混合后相互抵消→"没有成键"误判
- LOBSTER自动输出spin-resolved COHP

### 基组
- 过渡金属需d/f极化函数
- β-Be默认基组spilling 19%→加极化→1.7%
- Ba/La/Ce等碱土/稀土需空轨道

## 核心收获（C步骤）
ICOHP排序仅在"同类型键"间有效——跨元素对比较是审稿人固定靶。charge spilling<5%是准入门槛，不达标的数据不配进入键分析。
