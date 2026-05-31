---
name: domain-boundary-filter
description: X轮搜索前自动对照域边界关键词过滤——防止域漂移
metadata:
  type: T2
  scope: mechanism-level
---

**Why:** Bija_SuperIndividual在R1-R160期间20%的X轮搜索漂移到非域领域。宿主纠正后手动零复发500+轮——证明自动化即可。Bija-变现域边界明确（不碰DFT/HPC/论文论证/Bija架构），适合自动化过滤。

**How to apply:**
1. X轮搜索前 → 加载DOMAIN_IDENTITY.md non_output关键词
2. 对照本轮搜索词 → 匹配禁止词 → 替换为域内替代词
3. 例如: "DFT计算CRO" → 匹配"DFT"禁止词 → "计算化学CRO"(域内替代)

**Boundary:**
- 依赖DOMAIN_IDENTITY.md的正确定义
- 仅过滤关键词级别——不保证语义级别不漂移
- 替代词池需维护

**关联:** [[cross-verify-web-search-numbers]]
