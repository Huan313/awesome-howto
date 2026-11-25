# 风险筛查审计

基线风险分布 high 168、low 1974。本轮风险分布 high 2、low 2192、medium 11、unknown 1432。专业核验队列 65 条，含高影响决策、潜在决策支持和证据不足的入口。

风险判断采用产品功能和来源证据，主题用于导航。记账软件与资料目录可列为低风险或参考。来源显示临床决策、个性化法律意见或投资建议功能时触发专业复核。

## 可复现的抽查

按 SHA256(awesome-howto-v2.1.1-risk-audit|resource_id) 排序。抽取基线高风险 50 条与当前非高风险 50 条。非高风险样本分别从已进入专家队列及其他资源各选 25 条。复查本轮高风险记录，当前数量少于 50 时全查。抽查限于公开元数据与结构，无法判定时记为 uncertain。

| 样本层 | 抽查结果 |
| --- | --- |
| baseline-high | decision 3、ordinary 8、reference 11、software 14、uncertain 14 |
| current-non-high | decision 5、ordinary 12、reference 17、software 5、uncertain 11 |
| current-high | decision 2 |

基线 50 条样本中有 33 条依据可见用途属于旧版高风险误报。当前非高风险样本中有 5 条值得复核为决策支持，其中 0 条尚未进入专业队列。

旧高风险层中的 ordinary、software 或 reference 为元数据可见的旧误报。非高风险层中的 decision 为潜在漏报，仍需按原始输出和部署情境核对。

[逐条抽查](../data/curation-runs/v2.1.1/risk-sample.csv) · [专业复核队列](../data/reviews/high-risk-review.csv)
