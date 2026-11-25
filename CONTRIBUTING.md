# 贡献资源

1. 从[主题入口](README.md#按主题浏览)查重。每条资源在一个最合适的主题页保留可点击原始地址。
2. 打开原发布方页面，核对维护者、可进入的正文或目录、适用地区与版本。写一句具体用途，标注类型和语言。系列、手册／课程和 Awesome Lists 放在各自的集合页。
3. 高风险操作须给出中国大陆当前主管部门或专业机构的具体来源、核验日期和人工审核记录。人工复核完成后再标注 `高风险`、`已人工复核`、`中国大陆`、`核验 YYYY-MM-DD` 和 `审核记录 #编号`。只指向中国大陆官方查询或服务位置的条目使用 `官方入口`，标注地区及入口核验日期。
4. 在 PR 说明核验页面、适用限制和待复核事项。运行 `python -m scripts.validate_catalog` 和 `python -m scripts.check_links`。

[来源规则](data/source-policy.yml) · [分类词表](data/taxonomy.yml) · [本地质量检查](docs/automation-guide.md#本地运行)

目录只保存原始链接和原创简介。脚本、正文或图表的使用权由发布方许可决定。403、429 和超时保留复核状态。候选证据存于本地忽略目录或 Actions artifact。需求线索记录在[选题素材库](content-bank/README.md)，采用可公开核验的信息。

修订旧指南时，沿用[研究记录模板](templates/research-record-template.md)和[指南模板](templates/howto-template.md)。[旧版资产](archive/legacy-v1/README.md)保留历史路径和审核状态。

原创代码以 MIT 提交，原创文字以 CC BY 4.0 提交。第三方资料保留原许可。
