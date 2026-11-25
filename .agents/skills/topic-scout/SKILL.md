---
name: topic-scout
description: 核验实际用户问题、来源可达性与现有解法缺口，输出可复核的选题记录。
---

# topic-scout

## 输入与目标

问题、读者、地区、时间窗及已有指南。先查官方更新和公开社区；小红书、抖音、B站、知乎、微博、V2EX、Reddit 和 GitHub 优先使用原始公开页面。

## 流程与输出

输出 topic_id、topic、target_audience、pain_point、discovery_source、source_url、evidence、existing_solution_gap、proposed_solution、priority、evergreen_or_trend、verification_requirements 和 status。将事实、需求和热度分开。

## 失败与安全

页面受限就记 unknown 或受限。官方文档只能证明支持场景。避免登录绕过、个人信息和未经授权的抓取。

## 示例与验收

微信换机样例。可读聚合页支持需求线索，厂商指南支持事实，缺少测试机时实操留待验证。
