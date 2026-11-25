# 稳定资源身份与快照

保留了 2142 条基线记录的身份或映射。共输出 1011 条旧 ID 到稳定 ID 的迁移记录，其中 658 条来自基线。有 0 条固定提交记录无法确认默认分支映射，保留原记录并排入复核。

稳定子项身份由 GitHub 仓库、默认分支、路径和片段组成。根仓库既有 ID 保留，新增根记录优先使用 GitHub repository ID。
固定提交的 snapshot_url 与 source_url 保存证据定位。snapshots 保留此前来源 URL 和提交。旧 ID 还可在 identity_aliases 查询。
翻译、不同路径与片段、发布版本、辖区和 Fork 维持独立身份。迁移记录的 supersedes 指向退役旧 ID。

[旧 ID 映射](../data/curation-runs/v2.1.1/id-migrations.jsonl) · [疑似重复复核](../data/reviews/duplicate-review.csv)
