# 资源发现与复核

从官方来源、公开索引和项目原始目录收集入口。请提供资源地址、类型、适用范围、原始来源和可核验的许可。记录法律和财务资料的辖区，明确标出需要专业复核的内容。避免提交第三方正文、附件、个人资料和访问凭据。

## 查看结果

- [按主题浏览](../resources/discovery-index.md)和[按类型、受众、难度浏览](../resources/discovery-by-type.md)
- [规范目录 JSONL](../data/resource-catalog/resources.jsonl)、[候选 JSONL](../data/resource-catalog/candidates.jsonl)和[资源关系 JSONL](../data/resource-catalog/resource-relations.jsonl)
- [优先复核](../data/reviews/priority-review.csv)、[候选积压](../data/reviews/candidate-backlog.csv)、[仓库许可](../data/reviews/license-root-review.csv)、[专业复核](../data/reviews/high-risk-review.csv)、[元数据](../data/reviews/metadata-review.csv)和[疑似重复](../data/reviews/duplicate-review.csv)
- [V2.1.1 策展与风险复核](../reports/RESOURCE_CURATION_V2.1.1_REPORT.md) · [历史 V2.1 发现记录](../reports/RESOURCE_DISCOVERY_V2.1_REPORT.md)

规范目录保留 V2 数据，并纳入已核验的参考入口。自动初筛用于安排复核次序。编辑推荐等级需要逐项记录人工审核。许可未明时保留链接和必要元数据，禁止据此重用正文。课程版本、翻译、Fork 和不同辖区保留独立记录。

## 执行采集

使用 Python 3.12、项目依赖和已认证的 GitHub CLI。从仓库根目录运行。将同轮证据保存在同一输出路径。

```sh
python -m pip install -r requirements.txt
python -m scripts.discover_github --resume --output out/resource-curation
python -m scripts.expand_awesome_indexes --resume --max-depth 3 --output out/resource-curation
python -m scripts.check_resource_links --resume --output out/resource-curation
python -m scripts.refine_resource_catalog
```

`--dry-run` 查看采集范围。搜索支持 `--domains`、`--languages` 和 `--since YYYY-MM-DD`。`--resume` 复用已缓存证据。`--refresh-cache` 发起重新检查，GitHub API 在可用时使用条件请求。精修从已发布目录保留已知资源和审核字段，首次发布需要明确 V2.1 基准提交。

检查输出中的覆盖和失败项。确认可以更新规范目录后再发布到工作树。

```sh
python -m scripts.refine_resource_catalog --publish
python -m scripts.validate_catalog
python -m scripts.build_resource_catalog --check
python -m scripts.check_links
```

采集预算、种子和查询由本目录下的配置维护。目录子节点使用默认分支路径作为稳定身份，并保存不可变提交链接和旧 ID 映射。子文件独立核对许可。受限入口保留核验状态，403、429 和超时进入复核。

发布前按抽样规则逐条审阅风险样本，并记录能支持判断的来源和复核动作。历史 V2.1 的原始运行目录及旧复核 CSV 可通过历史报告追溯。
