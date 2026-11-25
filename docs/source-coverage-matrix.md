# 来源覆盖矩阵

| 领域 | 公开采集 | 原始来源 | 边界 |
| --- | --- | --- | --- |
| 生活与消费 | GitHub 查询、脱敏小红书和抖音记录 | FTC、SAMR、WHO、Apple、Android | FTC Feed 403，保留人工访问入口 |
| 学习研究 | GitHub、arXiv 及授权数据 | 教育部、UNESCO、OECD、Crossref | 摘要及元数据仅用于标记原文入口 |
| AI | HN、GitHub、GitHub Changelog、arXiv cs.AI | OpenAI、Anthropic、Google、Microsoft、Hugging Face | Hugging Face Feed 本地连接失败 |
| 数字技能 | GitHub、Python Insider、NIST RSS | Apple、Android、Microsoft、NIST、网信办、工信部 | RSS 是发布事件，步骤需要原文核验 |
| 职场 | GitHub、HN、获批 Reddit | 人社部、DOL、CareerOneStop | DOL RSS 本地 403，保留人工入口 |

[NIST Feed](https://www.nist.gov/blogs/cybersecurity-insights/rss.xml) 用项目解析器读到 40 条，正式报告另套用日期窗口。采集状态逐次记录。来源详见 [注册表](../data/source-registry.yaml) 与 [官方目录](../resources/official-resources.md)。
