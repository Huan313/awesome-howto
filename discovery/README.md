# 资源发现与复核

从官方来源、公开索引和项目原始目录收集入口。请提供资源地址、类型、适用范围、原始来源和可核验的许可。记录法律和财务资料的辖区，明确标出需要专业复核的内容。避免提交第三方正文、附件、个人资料和访问凭据。

## 查看结果

- [按主题浏览](../resources/discovery-index.md)和[按类型、受众、难度浏览](../resources/discovery-by-type.md)
- [规范目录 JSONL](../data/resource-catalog/resources.jsonl)、[候选 JSONL](../data/resource-catalog/candidates.jsonl)和[资源关系 JSONL](../data/resource-catalog/resource-relations.jsonl)
- [人工复核](../data/reviews/manual-review-queue.csv)、[许可证](../data/reviews/license-review.csv)、[高风险主题](../data/reviews/high-risk-review.csv)和[疑似重复](../data/reviews/duplicate-review.csv)
- [最近一轮发现记录](../reports/RESOURCE_DISCOVERY_V2.1_REPORT.md)

规范目录保留 V2 数据，并纳入已核验的参考入口。自动初筛用于安排复核次序。编辑推荐等级需要逐项记录人工审核。许可未明时保留链接和必要元数据，禁止据此重用正文。课程版本、翻译、Fork 和不同辖区保留独立记录。

## 执行采集

使用 Python 3.12、项目依赖和已认证的 GitHub CLI。从仓库根目录运行，默认写入 `out/resource-discovery/`。

```sh
python -m pip install -r requirements.txt
python -m scripts.discover_github --resume
python -m scripts.expand_awesome_indexes --resume --max-depth 3
python -m scripts.check_resource_links --resume
python -m scripts.build_resource_catalog
```

`--dry-run` 查看范围。搜索支持 `--domains`、`--languages` 和 `--since YYYY-MM-DD`。递归和官方入口脚本支持主题、语言和 `--output`。用统一的输出目录收集同一轮证据。`--resume` 复用成功的 API 响应和链接核验记录。`--refresh-cache` 发起重新检查，GitHub API 在可用时使用条件请求。构建时 `--limit` 控制规范化规模，旧记录始终带入。响应缓存保存经筛选的元数据、目录标题和链接。

检查输出中的覆盖和失败项。确认可以更新规范目录后再发布到工作树。

```sh
python -m scripts.build_resource_catalog --publish
python -m scripts.validate_catalog
python -m scripts.build_resource_catalog --check
python -m scripts.check_links
```

采集预算、种子和查询由本目录下的配置维护。受限站点、尚未独立核验的集合外链及不可访问入口保留状态或缺口记录。短期 API 限流、超时和 403 进入复核。提交前检查生成差异和审核字段，保存相关日期的运行记录。
