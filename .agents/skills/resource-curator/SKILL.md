---
name: resource-curator
description: 检索公开 GitHub 与官方 HowTo 资源，核验许可证、维护状态、适用人群和复用限制。
---

# resource-curator

## 触发条件

补目录、核对许可或刷新公开 GitHub 元数据时使用。个体化推荐需要另核验。

## 输入与目标

公开 URL、分类和 `resources/resource-registry.yaml`。刷新统计需要网络访问权限。

## 流程与输出

先读发布者页面和许可文件。运行 `python -m scripts.update_resource_metadata` 预检，有权更新时加 `--apply`。填写说明、受众和限制，运行 `python -m scripts.build_resource_index` 生成目录。

## 失败与安全

元数据查询失败保留旧快照。许可不明时仅收录链接。Stars 只说明公开参与度。第三方脚本须先检查许可和行为。

## 示例与验收

用未知 SPDX 资源验证 reference-only。执行 `python -m unittest discover -s tests -p test_v2_contract.py` 和 `python -m scripts.build_resource_index --check`。
