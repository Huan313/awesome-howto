# 贡献指南

1. 查[问题索引](howto/README.md)和[历史目录](archive/legacy-v3-0/README.md)，把需求写成能看到完成结果的问题。
2. 按[指南模板](templates/howto-template.md)先写基础方法，并在[研究](templates/research-template.md)和[验证记录](templates/verification-template.md)中写清证据与实际测试。
3. 标出地区、版本、费用与风险。涉及医疗、法律、财税或可能造成数据损失的操作，按[安全政策](docs/safety-policy.md)送人工复核。
4. 运行 `python -m scripts.validate_catalog` 和 `python -m scripts.check_links`。在 PR 说明来源、试验范围及剩余风险。

修订旧指南时用[旧模板](archive/legacy-v3-0/howto-template.md)。版权参见 [MIT](LICENSE) 和 [CC BY 4.0](LICENSE-CONTENT)。
