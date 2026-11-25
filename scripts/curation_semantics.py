"""Classify curation evidence and assess the function of high-impact resources."""
import re
from collections import Counter

from scripts.resource_catalog import DOMAIN_LABELS
from scripts.score_resources import COLLECTIONS

DOMAINS = {**DOMAIN_LABELS, "unclassified": "主题未核定"}
GUIDES = {"practical_guide", "handbook", "manual", "cookbook", "playbook", "field_guide", "cheatsheet"}
LEARNING = {"learning_path", "curriculum", "course", "book"}
AUXILIARY = {"tool", "community", "dataset"}
ROOT_TYPES = COLLECTIONS | LEARNING | {"howto_series", "cookbook", "handbook", "manual"}

SEMANTICS = {
    "life": r"cook(?:ing|book)|recipes?|household|adulting|home repair|pet care|菜谱|食谱|做饭|家居|生活指南|家务|レシピ|cocina",
    "health-safety": r"medic(?:al|ine)|clinical|public.health|first.aid|nutrition|sleep hygiene|health literacy|health care|healthcare|longevity|live.?longer|emergency preparedness|食品安全|急救|健康|医疗|寿命",
    "finance-law-consumer": r"haushaltsbuch|finance|budget(?:ing)?|expense.track|investment|tax(?:es|ation)?\b|insurance|legal|consumer.rights|law\b|财务|消费[者权]|法律|劳动权益|预算|税务|投资",
    "learning-study": r"study.buddy|study.skills|language.learn|critical.thinking|academic.writ|note.tak|learning.path|open.course|pedagog|spaced.repetition|free.?programming.?books|学习|课程体系|学习路线|写作|rédaction.scientifique",
    "digital-life": r"backup|recovery.manual|digital.literacy|android|smartphone|linux|mac.?os|windows|office.software|command.line|privacy.guide|datenschutz|电脑|备份|办公软件",
    "career-work": r"interview|career|job.search|workplace|teacher.handbook|freelanc|resume|professional.development|求职|简历|面试|职场",
    "ai-everyone": r"prompt.pack|ai.literacy|generative.ai.for.beginners|ai.for.beginners|ai.for.teachers|chatgpt.for|prompt.engineer|artificial.intelligence.literacy|人工智能入门|AI入门",
    "ai-engineering": r"\bmlops\b|model.deployment|llm|claude.code|vision.language.model|machine.learning|large.language.model|\brag\b|\bmcp\b|agent.skills|ai.engineer|model.fine.tun|inference|大模型|智能体",
    "creative-hobby": r"photo(?:graphy)?|graphic.design|typograph|gardening|jardinage|blender|audacity|craft|video.edit|摄影|园艺|手工|绘画",
    "professional": r"agricultur|farm.source|farmsource|farming|engineering.handbook|engineering.workflow|scientific.research|manufactur|reporting.guidelines|research.methods|科研|农业|工程手册",
}
SIGNALS = {domain: re.compile(pattern, re.I) for domain, pattern in SEMANTICS.items()}

SOFTWARE = re.compile(r"\b(?:app(?:lication)?|software|plugin|extension|api|server|bot|tracker|dashboard|cli|sdk|library|parser|calculator|toolkit)\b|软件|工具|应用", re.I)
BUDGET_LOG = re.compile(r"expense.track|budget.track|haushaltsbuch|spending.track|记录支出|记账", re.I)
INFORMATION = re.compile(r"\b(?:index|catalog|database|reference|bibliography|papers?|literature|directory|search|retrieval|statutes?|citations?|educational|guidelines?|guidance|public information)\b|索引|资料|官方说明|指南|判例|법령", re.I)
IMPACT_CONTEXT = re.compile(
    r"\b(?:clinical|patient|disease|treatment|medical|medicine|symptoms?|prescription|first aid|health|"
    r"law|legal|tax\b|investment|insurance|financial advice|personal finance|consumer rights|safety|nutrition|"
    r"hospital readmission)\b|诊疗|诊断|临床|用药|医疗|症状|法律|广告法|财务|消费者权益|税务|投资|保险|急救|安全|健康", re.I,
)
ADVICE = (
    ("clinical_decision", re.compile(
        r"clinical.decision.support|diagnos(?:is|e|tic).{0,32}(?:recommend|assistant|chatbot|treatment|tool|predict)|"
        r"(?:predict|diagnos|prescrib|recommend).{0,30}(?:a.disease|your.symptoms|medicat|treatment.for|patients?|disease.from)|"
        r"genetic reports?.{0,32}(?:actionabil|personal)|处方推荐|个性化诊断|临床决策|根据症状.{0,8}(?:诊断|用药)", re.I)),
    ("legal_advice", re.compile(
        r"personali[sz]ed.legal.(?:advice|recommend)|(?:give|provides?|offers?|generates?).{0,35}legal.advice|"
        r"个性化法律意见|针对.{0,10}个案.{0,12}法律建议|生成法律意见|自动识别.{0,14}违规.{0,24}生成投诉材料", re.I)),
    ("financial_recommendation", re.compile(
        r"personali[sz]ed.(?:invest(?:ment|ing)|financial).(?:advice|recommend)|(?:generates?|provides?|offers?).{0,35}"
        r"(?:investment|portfolio|stock).recommend|buy.and.sell.signals|个性化投资|荐股|生成投资建议", re.I)),
)
ACTION = re.compile(r"(?:recommend|triage|predict|assess|suggest).{0,25}(?:health|symptoms?|legal|invest|treatment)|"
                    r"(?:health|legal|investment).{0,20}(?:assistant|chatbot|advisor|scor)|"
                    r"hospital readmission prediction|personal finance.{0,20}(?:assistant|agents?|ai)|"
                    r"风险评估|问诊|法律咨询|法律顾问|合规审核引擎", re.I)


def classify_sources(*, sources, query_domains=(), asserted=None, parent=None):
    """Require descriptive evidence. Query categories are retained in provenance."""
    if asserted:
        domain, source = asserted
        return domain, [domain], "high", "classified", [f"{source} → {domain}"], []
    score, evidence = Counter(), []
    query_domains = set(query_domains)
    for label, value, weight in sources:
        if not value:
            continue
        cleaned = value.replace("_", " ").replace("-", " ")
        for domain, pattern in SIGNALS.items():
            if pattern.search(cleaned):
                score[domain] += weight
                evidence.append(f"{label} → {domain} ({weight})")
        if label == "Repository description" and re.search(r"\bmcp (?:server|connector|integration)\b", cleaned, re.I):
            score["ai-engineering"] += 3
            evidence.append("Repository description → MCP integration function (3)")
    if parent in DOMAINS and parent != "unclassified":
        score[parent] += 2
        evidence.append(f"parent-collection → {parent} (2)")
    matches = sorted((domain for domain in score if score[domain] >= 3),
                     key=lambda domain: (-score[domain], domain))
    if not matches:
        return "unclassified", ["unclassified"], "low", "unclassified", evidence or ["No supported topic signal"], []
    if len(matches) > 1 and score[matches[0]] == score[matches[1]]:
        tied = [domain for domain in matches if score[domain] == score[matches[0]]]
        evidence.append("Equal descriptive evidence. Query provenance does not resolve the tie.")
        return "unclassified", ["unclassified", *tied], "low", "needs-review", evidence, matches
    primary = matches[0]
    if primary in query_domains:
        evidence.append(f"Search query supports {primary}; zero classification weight")
    confident = "high" if score[primary] >= 7 else "medium"
    return primary, matches, confident, "cross-domain" if len(matches) > 1 else "classified", evidence, matches[1:]


def assess_risk(*, title, description="", headings="", kind="unknown", official=False, outline=False):
    """Impact is inferred from function and source evidence, independently of the topic label."""
    text = " ".join((description, headings)).replace("-", " ")
    context = " ".join((title, text))
    for scope, signal in ADVICE:
        if signal.search(text):
            return "high", scope, ["Functional evidence in description or inspected outline"], "medium", True
    if BUDGET_LOG.search(context) and not ACTION.search(text):
        return "low", "software_tool", ["Expense or budget recording function"], "medium", False
    if IMPACT_CONTEXT.search(context):
        if ACTION.search(text):
            return "medium", "decision_support", ["Potential high-impact decision support; output scope needs review"], "medium", True
        if INFORMATION.search(context) or official or outline:
            level = "medium" if official or outline else "low"
            requires = bool(official or outline)
            return level, "reference", ["Reference or outline evidence; verify applicability and freshness"], "medium", requires
        return "unknown", "other", ["High-impact terms present; scope could not be established"], "low", True
    if kind in AUXILIARY or SOFTWARE.search(text):
        return "low", "software_tool", ["Software or auxiliary function evidenced in metadata"], "medium", False
    if official or kind in ROOT_TYPES | GUIDES | {"tutorial", "official_reference"}:
        return "low", "informational", ["Available source describes general instructional or reference material"], "medium", False
    return "unknown", "other", ["Available metadata is insufficient to assess function"], "low", False


def verification_level(row):
    if row["quality_assessment"]["review_status"] == "human-approved":
        return "content_reviewed"
    method = row["link_check"]["method"]
    if row["structure"]["headings"] or row["structure"]["local_items"]:
        return "structure_inspected"
    if method == "git-tree":
        return "structure_inspected" if row["resource_scope"] == "section" else "document_exists"
    if method in {"github-api", "gitlab-api"}:
        return "repository_exists"
    if method == "https" and row["status"] in {"active", "redirected"}:
        return "public_page_reachable"
    return "metadata_only"
