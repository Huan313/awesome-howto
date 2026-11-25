# 分类与已知误判复查

有文本证据时优先使用 README、发布方简介和主题。仓库名、路径与父集合提供补充。查询主题只保留为发现出处。没有明确证据或出现同权冲突时使用 unclassified。

| 样本 | V2.1 归类 | 本轮主题 | 本轮风险 | 证据 |
| --- | --- | --- | --- | --- |
| hamidhirsi/mlops-case-study | health-safety | ai-engineering | medium | Repository description → ai-engineering (5) / Repository name → ai-engineering (3) |
| qhyai-bit/farmsource | health-safety | professional | unknown | Repository description → health-safety (5) / Repository description → learning-study (5) / Repository description → professional (5) / Repository name → professional (3) |
| studybuddydevelopers/study-buddy-v2 | finance-law-consumer | learning-study | unknown | Repository name → learning-study (3) |
| decade-qiu/openai-prompt-packs | health-safety | ai-everyone | low | Repository description → ai-everyone (5) / Repository name → ai-everyone (3) |
| alishahryar1/free-claude-code | finance-law-consumer | ai-engineering | low | Repository description → ai-engineering (5) / Repository name → ai-engineering (3) |
| larsmt35/haushaltsbuch-web-version | finance-law-consumer | finance-law-consumer | low | Repository name → finance-law-consumer (3) / Search query supports finance-law-consumer; zero classification weight |
| chrisryugj/korean-law-mcp | ai-engineering | ai-engineering | low | Repository description → finance-law-consumer (5) / Repository description → ai-engineering (5) / Repository description → MCP integration function (3) / Topics → finance-law-consumer (4) / Topics → ai-engineering (4) / Repository name → finance-law-consumer (3) / Repository name → ai-engineering (3) |

分类状态 classified 909、cross-domain 122、needs-review 61、unclassified 2545。主题分布 ai-engineering 410、ai-everyone 46、career-work 104、creative-hobby 22、digital-life 122、finance-law-consumer 47、health-safety 33、learning-study 107、life 121、professional 19、unclassified 2606。

主题词模型用于排序和查阅。混合领域、只有通用 README 的仓库及搜索结果标题仍需人工判读。
