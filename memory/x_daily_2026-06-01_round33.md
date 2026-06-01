# X轮笔记 — 型男日课#33 | 2026-06-01

## X79: 知乎2026变现趋势更新
- 致知计划2026.2: 活跃领域与收益解绑——垂直专业仍是加权核心
- 收益计算时限缩短: 仅1年内内容计收益，"想法"周期更短
- 长尾收益改周更(非每日推送)→创作者体感收益下降
- AI赛道被列为2026重点扶持方向(AI办公/AI学术辅助/副业搞钱)
- AI内容隐性限制: 严禁AI拼接洗稿→扣优质分; 知乎直答=事实核查工具
- 政协委员周源建议: 延长收益计算周期、算法透明化(参考X开源)、AI事实核查
- 核心矛盾: 平台推AI内容但审核更严→真实科研经验=护城河(与变现策略一致)
- 创作者应对: 多参与圆桌活动(单次数千盐粒)、"想法"性价比>长回答、避免晚8点后发布

## X80: DFT+U计算10大隐蔽陷阱(2025-2026最新文献)
- **#1 Projector敏感性(最大陷阱)**: 不同投影球大小→不同occupancy→不同电子结构/晶格/磁基态。2026 Raman&Park提出projection-consistent U_eff方案
- **#2 轨道流形错误(混合d-f体系)**: Warda 2026 JCTC——标准DFT+U在强d-f-p杂化中overcorrect→结构扭曲。解: orbital-resolved DFT+U
- **#3 VASP Known Bug(2025.5仍open)**: DFT+U的EOS拟合→晶格常数vs U非物理线性关系。跨验证或等修复
- **#4 NAO框架默认projector崩溃**: Logsdail 2025 Digital Discovery——FHI-aims默认projector对TiO2/CeO2导致SCF不收敛。ML优化projector
- **#5 U值非可迁移性**: LR-cDFT对stoichiometric系统标定的U→缺陷计算失败(LiCoO2掺Mg预测虚假深缺陷态)
- **#6 文献U值陷阱**: U是material/projector/code三重依赖。文献值可能在完全不同的投影设置下标定
- **#7 U_eff vs (U,J)分离**: β-MnO2案例——U_eff简化错误偏好铁磁; 完整(U,J)正确预测反铁磁
- **#8 亚稳态收敛**: 初始磁构型(FM/AFM)可困在金属亚稳态。必须多初始自旋构型测试
- **#9 Tetrahedron vs Gaussian**: 关联绝缘体须用ISMEAR=-5。Gaussian smearing可抹掉绝缘体gap
- **#10 跨代码不可比**: 同一材料+VASP/QE/WIEN2k/FHI-aims→定性不同结果。必须报告code+projector+U确定方法

**关键趋势(2025-2026)**: 社区从"随便选个U值"→严格要求关联子空间定义的可复现性。projector specification已成DFT+U论文必备要素。
