"""Transparent heuristic scores kept separate from editorial evidence claims."""
import re
from collections import Counter, defaultdict
from urllib.parse import urlsplit

from scripts.common import ROOT, read_yaml, timestamp, validate
from scripts.deduplicate_topics import similar, topic_id
from scripts.evidence import matching_package

WEIGHTS = dict(demand=0.25, momentum=0.20, evidence=0.25, actionability=0.20, novelty=0.10)
RISK = re.compile(
    r"\b(?:medical|first aid|suicide|medication|investments?|loans?|tax|fraud|phishing|weapons?|exploits?|minor|child|diagnosis|attacks?|financial)\b"
    r"|医疗|急救|自杀|处方|投资|贷款|保险|法律|诈骗|未成年|武器|攻击|漏洞利用|隐私|税务",
    flags=re.I,
)
ACTION = re.compile(
    r"\b(?:how to|tutorials?|learn|guide|build|set up|backup|verify|verification|practice|automate"
    r"|automation|cook|organize|evaluate|evaluating|evaluation|testing|detecting|debugging|release notes)\b"
    r"|如何|怎么|教程|步骤|备份|核验|整理|复习|搭建|配置|自动化|调试|评估",
    flags=re.I,
)
EXCLUDE = re.compile(
    r"\b(?:bypass captcha|doxx?ing|credential theft|weapon manufacturing|exploit chain)\b"
    r"|绕过验证码|人肉搜索|窃取账号|制造武器|漏洞利用链",
    flags=re.I,
)


def weighted_score(signals):
    return round(sum(signals[key] * weight for key, weight in WEIGHTS.items()), 1)


def decision(score, *, high_risk, evidence, social_only, existing=False, prohibited=False):
    if prohibited or (high_risk and evidence < 70):
        return "blocked", "风险门槛拦截，需补证据或改为安全教育"
    if high_risk:
        return "observe", "高风险，须由编辑进行专业审查"
    if social_only:
        return "observe", "仅有单一社交平台线索，需独立需求和证据"
    if existing:
        return "update-existing", "已有相近指南，优先核对并更新"
    for limit, status, reason in (
        (80, "research", "优先深研"), (65, "candidate", "纳入候选池"),
        (50, "observe", "收集更多独立观测"), (0, "deferred", "暂缓"),
    ):
        if score >= limit:
            return status, reason
    raise ValueError("score is outside its expected range")


def metric_growth(observations):
    series = defaultdict(dict)
    for item in observations:
        for unit, value in item["metrics"].items():
            key = item["platform"], item["url"], item["query"], unit
            series[key][timestamp(item["observed_at"])] = value
    results = []
    for key, values in sorted(series.items()):
        if len(values) < 2:
            continue
        times = sorted(values)
        baseline = values[times[0]]
        if baseline:
            results.append((*key, round((values[times[-1]] - baseline) / baseline * 100, 1)))
    return results


def score_group(group, guides, taxonomy=None):
    taxonomy = taxonomy or read_yaml(ROOT / "data/topic-taxonomy.yaml")
    latest = max(group, key=lambda item: (timestamp(item["observed_at"]), item["source_id"]))
    title = latest["title"]
    labels = {name: sum(keyword.casefold() in title.casefold() for keyword in data["keywords"])
              for name, data in taxonomy.items()}
    category = max(labels, key=labels.get)
    if not labels[category]:
        category = "unclassified"
    action = bool(ACTION.search(title))
    platforms = {item["platform"] for item in group}
    events = {item["event_at"][:10] for item in group}
    distinct = {(item["platform"], item["url"]) for item in group}
    evidence = max({"official": 80, "research": 65, "community": 15, "social": 0}[item["kind"]]
                   for item in group)
    existing = next((guide for guide in guides if similar(title, guide["title"])
                     or group[0].get("topic_key") == guide["id"].removeprefix("howto-")), None)
    signals = {
        "demand": min(100, 20 + 35 * action + 12 * (len(distinct) - 1) + 10 * (category != "unclassified")),
        "momentum": min(100, 25 + 20 * (len(platforms) - 1) + 10 * (len(events) - 1)),
        "evidence": evidence,
        "actionability": 80 if action else 45 if category != "unclassified" else 20,
        "novelty": 10 if existing else 55,
    }
    score = weighted_score(signals)
    risk_text = " ".join(item["title"] for item in group)
    high_risk = bool(RISK.search(risk_text))
    status, reason = decision(score, high_risk=high_risk, evidence=evidence,
                              social_only=len(platforms) == 1 and all(item["kind"] == "social" for item in group),
                              existing=existing is not None, prohibited=bool(EXCLUDE.search(risk_text)))
    personas = {"learning": ["student"], "ai": ["office-worker", "software-engineer"],
                "work": ["office-worker"], "life": ["general-public"], "digital": ["general-public"]}
    result = {
        "topic_id": topic_id(group), "title": title, "category": category,
        "personas": existing["personas"] if existing else personas.get(category, ["general-public"]),
        "scenarios": existing["scenarios"] if existing else taxonomy.get(category, {}).get("scenarios", []),
        "source_refs": sorted({item["source_id"] for item in group}),
        "first_seen": min(item["observed_at"] for item in group), "last_seen": latest["observed_at"],
        "score": score, "signals": signals, "risk": "high" if high_risk else "low",
        "status": status, "decision_reason": reason,
        "existing_guide": existing["id"] if existing else "none",
    }
    validate("topic", result)
    return result


V2_WEIGHTS = {"demand": .30, "trend": .15, "persona_confidence": .10,
              "evidence_readiness": .25, "actionability": .15, "novelty": .05}


def score_group_v2(group, guides, taxonomy=None, packages=None):
    """Keep baseline results alongside independently observable V2 signals."""
    taxonomy = taxonomy or read_yaml(ROOT / "data/topic-taxonomy.yaml")
    baseline = score_group(group, guides, taxonomy)
    staged = matching_package(baseline, group, packages or {})
    distinct = {(row["platform"], row["url"]): row for row in group}
    labels = {name: 0 for name in taxonomy}
    for row in distinct.values():
        text = " ".join(row.get(field, "") for field in ("title", "task", "summary")).casefold()
        for name, rule in taxonomy.items():
            labels[name] += sum(keyword.casefold() in text for keyword in rule["keywords"])
    ranked = sorted(labels, key=lambda label: (-labels[label], label))
    category = ranked[0] if labels[ranked[0]] > labels[ranked[1]] else "unclassified"
    if staged:
        category = staged["category"]
    signals = []
    for row in distinct.values():
        if row.get("signal_type") == "demand":
            signals.append(row)
    demand = min(100, 18 * len(signals) + 15 * sum(bool(row.get("task")) for row in signals)) if signals else "unknown"
    personas = sorted({tag for row in signals if row.get("audience_basis") in {"self-described", "documented-sample"}
                       for tag in row.get("audience", []) if tag != "unknown"})
    valid_personas = read_yaml(ROOT / "data/personas.yaml")["personas"]
    personas = [tag for tag in personas if tag in valid_personas]
    scoped = {row["region"] for row in signals if row.get("region") not in {None, "unknown"}}
    region = next(iter(scoped)) if len(scoped) == 1 else "unknown"
    if staged:
        personas, region = staged["personas"], staged["region"]
    coverage_dates = sorted({row["observed_at"][:10] for row in group})
    domains = sorted({urlsplit(row["url"]).hostname for row in group if urlsplit(row["url"]).hostname})
    growth = [dict(platform=p, url=url, query=q, unit=u, percent=g) for p, url, q, u, g in metric_growth(group)]
    trend = min(100, round(max(item["percent"] for item in growth), 1)) if growth else "unknown"
    if trend != "unknown":
        trend = max(0, trend)
    existing = next((guide for guide in guides if (staged and guide["id"] == staged["guide_id"])
                     or (category == guide["category"] and any(similar(row["title"], guide["title"]) for row in group)
                         and region in {guide["region"], "unknown"})), None)
    risk_text = " ".join(row["title"] + " " + row.get("task", "") for row in distinct.values())
    prohibited = bool(EXCLUDE.search(risk_text))
    risk = "high" if prohibited or RISK.search(risk_text) else "medium" if re.search(
        r"delete|erase|data loss|恢复|删除|迁移", risk_text, re.I) else "low"
    levels = ("low", "medium", "high")
    if staged and levels.index(staged["risk_level"]) > levels.index(risk):
        risk = staged["risk_level"]
    reasons = {"low": "标题和任务暂未提示高风险，需要编辑复核",
               "medium": "可能改动数据或账户，需要验证与回退",
               "high": "命中高风险主题，需专业审核或拒绝"}
    if staged and staged["risk_level"] == risk and not prohibited:
        reasons[risk] = staged["risk_reason"]
    direct_ids = sorted({item for c in staged["claims"] if c["support_level"] == "direct"
                         for item in c["supporting_source_ids"]}) if staged else []
    scores = {
        "demand": demand, "trend": trend,
        "persona_confidence": min(100, 30 + 15 * len(signals)) if personas and personas != ["unknown"] else "unknown",
        "evidence_readiness": min(100, 55 + 10 * len(direct_ids)) if direct_ids else "unknown",
        "actionability": min(100, 40 + 10 * len(staged["steps"])) if staged else (
            35 if any(row.get("task") or ACTION.search(row["title"]) for row in distinct.values()) else "unknown"),
        "novelty": 10 if existing else 60 if staged and region != "unknown" else "unknown",
    }
    coverage = round(sum(value != "unknown" for value in scores.values()) / len(scores), 3)
    score = round(sum(scores[k] * weight for k, weight in V2_WEIGHTS.items() if scores[k] != "unknown"), 1)
    social_only = bool(signals) and all(row["kind"] == "social" for row in signals) and len(
        {row["platform"] for row in signals}) == 1
    if prohibited or (risk == "high" and direct_ids == []):
        status, reason = "blocked", reasons["high"]
    elif risk == "high":
        status, reason = "observe", "需要专业审核，退出自动草稿"
    elif existing:
        status, reason = "update-existing", "匹配现有指南，先核对范围及更新差异"
    elif staged and len(signals) >= 1:
        status, reason = "research", "已审证据包匹配真实观测，可进一步核验草稿"
    elif len(signals) >= 2 and not social_only:
        status, reason = "candidate", "多个问题观测，补独立需求与原始步骤证据"
    elif signals or (category != "unclassified" and scores["actionability"] != "unknown"):
        status, reason = "observe", "保留研究线索，核验样本和解决方案"
    else:
        status, reason = "deferred", "信号不足，保留来源记录"
    result = {
        **baseline, "schema_version": 2, "baseline": {"score": baseline["score"], "status": baseline["status"]},
        "category": category, "personas": personas or ["unknown"],
        "scenarios": staged["scenarios"] if staged else existing["scenarios"] if existing else ["unknown"],
        "score": score, "risk": risk, "risk_reason": reasons[risk], "region": region,
        "status": status, "decision_reason": reason, "existing_guide": existing["id"] if existing else "none",
        "signals_v2": scores, "growth": growth or "unknown", "coverage": coverage,
        "confidence": "high" if staged and coverage >= .8 and len(domains) >= 2 else (
            "medium" if staged or len(signals) >= 2 else "low"),
        "sample_count": len(distinct), "unique_domains": domains, "unique_dates": coverage_dates,
        "source_types": dict(sorted(Counter(row["kind"] for row in distinct.values()).items())),
        "demand_refs": sorted({row["source_id"] for row in signals}), "evidence_source_ids": direct_ids,
    }
    validate("topic", result)
    return result
