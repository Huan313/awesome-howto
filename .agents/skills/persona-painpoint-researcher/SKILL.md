---
name: persona-painpoint-researcher
description: "查证特定人群在具体场景中的痛点，产出读者、问题、场景与独立证据矩阵。"
---

# persona-painpoint-researcher

## 触发条件

核验特定读者在某任务的困难时触发。年龄和职业猜测保留 unknown。

## 输入与目标

读者群、地区、使用场景以及一组明示需求或可追溯样本。先确定研究问题和纳入标准。

## 流程与输出

查阅 `docs/persona-taxonomy.md` 和 `templates/research-record-template.md`。拆成读者、任务、卡住的步骤。优先核对调查、官方统计、公开问题及调查方法。输出 persona × 痛点 × 场景矩阵，每行注明来源 URL、访问日期、样本与限制。将确认需求和研究假设标记出来。

## 失败与安全

避免把年龄、职业或性别当作痛点证据。内容缺少独立样本时保留假设。不得推断身份敏感属性，禁止保留个人账号或私信。

## 示例与验收

输入 `$persona-painpoint-researcher 研究换手机时成年人遇到的验证器转移问题`。只有一条公开讨论的虚构试例必须标为待验证，并指出独立样本缺口。

## V2 文件、权限和验收

读 `data/personas.yaml`、`data/occupations.yaml`、`data/life-stages.yaml`。从事实样本出发，收集读者自述或有出处的调查。

将脱敏记录写入 `data/research/`，每一行注明样本和地区。禁止保存个人账号或推断敏感身份。

回归命令 `python -m unittest discover -s tests -p test_v2_contract.py`。
