---
name: cross-verify-web-search-numbers
description: Web搜索引用的数字须经≥2独立来源验证，单一来源不引用
metadata:
  type: T2
  scope: mechanism-level
---

**Why:** Bija-外部化在R3→R4发现：SER/ELG Star数被百度文章夸大，GitHub无验证。单一来源的数字（市场规模、定价、增长率）极易被SEO文章污染。引用未经验证的数字 → 下游决策建立在虚假信息上 → 假进展。

**How to apply:**
1. WebSearch获得数字后 → 搜索第二个独立来源确认
2. 两个来源必须是独立机构（不能是同一篇文章被不同网站转载）
3. 无法交叉验证的数字 → 标注"单一来源，未验证" → 不用于决策
4. 来源URL随x_daily笔记保存

**Boundary:**
- 适用于所有可量化声明（市场规模、定价、增长率、用户数）
- 不适用于定性判断（"市场拥挤""竞品众多"——这些不需要验证）
- 公开数据优先（公司财报/官方定价页），第三方估算次之

**关联:** [[domain-boundary-filter]] [[t1_5_execution_tier]]
