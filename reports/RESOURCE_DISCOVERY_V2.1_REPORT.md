# V2.1 全球资源发现记录

运行窗口 2026-11-25T11:23:41+08:00 至 2026-11-25T13:48:03+08:00（UTC+08）。改进基线 a315fd7c52238bc6b54b0f8c6fad40fdb54f253a。脚本版本摘要见 [运行清单](../data/discovery-runs/2026-11-25/manifest.json)。

来源包括 GitHub REST Repository Search、GitHub Contents / Git Trees 和官方站点核验。GitLab 项目核验见链接报告。

补充平台探测 GitLab 公开项目搜索 HTTP 200，前五条样本与主题不符，后续定向核验 3 个公开项目、Codeberg 公开仓库搜索 HTTP 429、Codex 网页检索 抽查官方目录页和镜像声明，未计入 GitHub 分页命中。

GitHub 查询组 29，执行 58 个分页请求，返回 1160 条命中。成功 58 页，标记 incomplete_results 0 页。
配置种子 44，API 核验成功 44。其中索引种子成功 26，补充索引种子成功 11。
BFS 深度上限 3，实际最深 3。抽取 983 个目录观察，建立 658 条父子边。
纳入规范化的原始观察 2270 条，含旧注册表和补充入口。合并 128 条重复观察，唯一记录 2142 条。其中目录 95 条、候选 2047 条，自动初筛 200 条。人工新评分 0 条。

## 类型、主题与语言

目录类型分布：awesome_list 13、bibliography 1、book 1、cheatsheet 1、cookbook 2、course 2、curriculum 5、handbook 4、howto_series 2、learning_path 2、manual 3、official_reference 39、practical_guide 3、resource_directory 8、tutorial 2、unknown 7。
候选类型分布：awesome_list 205、bibliography 1、cheatsheet 5、collection 348、community 8、cookbook 47、course 66、curriculum 75、dataset 10、handbook 38、learning_path 47、manual 11、practical_guide 164、resource_directory 27、tool 10、tutorial 126、unknown 846、wiki 13。
初筛类型分布：awesome_list 91、cheatsheet 2、collection 1、cookbook 6、course 4、curriculum 6、handbook 15、learning_path 12、manual 5、practical_guide 24、resource_directory 12、tutorial 22。
初筛主题分布：ai-engineering 26、ai-everyone 26、career-work 26、creative-hobby 19、digital-life 26、learning-study 26、life 26、professional 25。
目录地域分布：CA 1、CN 1、GB 3、SG 1、US 9、global 33、unknown 47。
候选语言分布：cs 1、de 1、el 1、en 296、es 1、fr 1、it 1、ja 2、ko 2、mul 87、pt 1、ru 1、unknown 1559、zh 73、zh-CN 3、zh-TW 17。

## 本轮新增并核验的入口

- [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning)。按编程语言组织项目练习，外链保留来源集合。
- [EbookFoundation/free-programming-books](https://github.com/ebookfoundation/free-programming-books)。多语书目入口，可分别核对语言版本及原始资源。
- [Managing your money](https://www.moneysense.gov.sg/managing-your-money)。可明确定位到新加坡的公共财务教育入口。
- [Live Well](https://www.nhs.uk/live-well)。按健康生活主题查找英国公共医疗机构的原始资料。
- [Web Accessibility Tutorials](https://www.w3.org/WAI/tutorials)。按无障碍任务查找标准机构的教程。
- [Interview primer](https://capd.mit.edu/resources/interview-primer)。大学职业中心的面试资料，区分常见面试场景。
- [Blender Manual](https://docs.blender.org/manual/en/latest)。按版本、工具和工作环节浏览的官方手册。
- [OpenCourseWare](https://ocw.mit.edu/)。按学科查找大学开放课程，便于逐门核对版本和许可。
- [Systems Engineering Handbook](https://www.nasa.gov/reference/systems-engineering-handbook)。工程机构的原始手册入口，可按术语和流程查阅。
- [microsoft/AI-For-Beginners](https://github.com/microsoft/ai-for-beginners)。按单元组织 AI 基础课程及习题，便于核对受众。

## 低 Stars 待审样本

- [awesome-german/websites](https://github.com/awesome-german/websites) · 3 Stars。采集 2026-11-25T03:24:28Z。按语言程度整理德语学习网站，补充非英语学习入口。
- [AdamXweb/awesome-aussie](https://github.com/adamxweb/awesome-aussie) · 49 Stars。采集 2026-11-25T03:24:49Z。按澳大利亚开发的软件和服务整理，可复查区域数字生态。
- [AutoGeoAI4Sci/awesome-autonomous-geoai](https://github.com/autogeoai4sci/awesome-autonomous-geoai) · 22 Stars。采集 2026-11-25T03:25:41Z。集中索引自主地理空间 AI 资料，便于查找专业候选。

## 排除及后续

排除观察：official-source-unverified 10、scope-or-safety-filter 13。
下一轮优先补非英语生活资源、按司法辖区的消费与劳动公开目录，以及无需账号即可查阅的低星行业手册。

[覆盖与种子](RESOURCE_COVERAGE_GAP_REPORT.md) · [自动初筛](RESOURCE_QUALITY_REPORT.md) · [关系与去重](RESOURCE_DUPLICATION_REPORT.md) · [许可证](LICENSE_AND_COMPLIANCE_REPORT.md) · [链接核验](LINK_HEALTH_REPORT.md)
