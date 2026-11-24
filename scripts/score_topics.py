"""Transparent heuristic scores kept separate from editorial evidence claims."""
import re
from collections import defaultdict

from scripts.common import ROOT, read_yaml, timestamp, validate
from scripts.deduplicate_topics import similar, topic_id

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
