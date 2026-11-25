"""Project legacy, search and collection evidence into one versioned resource graph."""
import re
from collections import Counter, defaultdict
from urllib.parse import quote, urlsplit

from scripts.common import read_yaml
from scripts.deduplicate_resources import canonical_url, normalized_title, stable_id
from scripts.discover_github import CONFIG
from scripts.extract_collection_items import suitable
from scripts.score_resources import assess, eligible

LEGACY_DOMAIN = {
    "cooking-household": "life", "life-howto": "life", "health-safety": "health-safety",
    "digital-security": "digital-life", "career-work": "career-work", "ai-everyone": "ai-everyone",
    "ai-engineering": "ai-engineering", "agent-skills": "ai-engineering", "learning-study": "learning-study",
    "research-productivity": "professional", "official-documentation": "ai-everyone",
}
DOMAIN_HINTS = {
    "life": r"recipe|cookbook|cooking|household|home maintenance|食谱|菜谱|家务",
    "health-safety": r"first aid|health literacy|food safety|sleep hygiene|clinical|急救|食品安全|睡眠",
    "finance-law-consumer": r"budget|consumer rights|personal finance|money|tax|insurance|财务|财税|预算|劳动权益|诈骗",
    "learning-study": r"study skill|language learning|learning path|research methods|读写|学习路线|课程",
    "digital-life": r"digital literacy|backup|macos|smartphone|spreadsheet|office productivity|电脑|备份|办公",
    "career-work": r"resume|interview|job search|career|workplace|面试|求职|简历|职场",
    "ai-everyone": r"ai literacy|generative ai for beginners|chatgpt|人工智能入门",
    "ai-engineering": r"llm|agents?|mcp|prompt engineering|rag|大模型",
    "creative-hobby": r"gardening|photography|blender|typography|craft|font|摄影|园艺|手工",
    "professional": r"engineering handbook|research workflow|agriculture|manufacturing|设计手册|科研",
}
TYPES = [
    (r"\b(?:mobile app|desktop app|recipe notebook|browser extension|software utility|web application)\b", "tool"),
    (r"awesome[- ]|awesome_", "awesome_list"),
    (r"cheat[- ]?sheet|速查", "cheatsheet"),
    (r"learning[- ]path|roadmap|学习路线", "learning_path"),
    (r"curriculum|课程体系", "curriculum"),
    (r"cookbook|recipes|菜谱|食谱", "cookbook"),
    (r"handbook|手册", "handbook"),
    (r"field guide", "field_guide"),
    (r"playbook", "playbook"),
    (r"manual|操作手册", "manual"),
    (r"course|课程", "course"),
    (r"wiki|知识库", "wiki"),
    (r"tutorial|from scratch|教程|从零开始", "tutorial"),
    (r"how.?to|指南|how to", "practical_guide"),
    (r"bibliography|reading list", "bibliography"),
    (r"resource|资源合集|directory", "resource_directory"),
    (r"dataset|数据集", "dataset"),
    (r"guide|checklist|清单", "practical_guide"),
    (r"documentation|reference|文档", "manual"),
    (r"community|论坛", "community"),
    (r"^tool |软件工具", "tool"),
]
REGULATION = re.compile(r"\b(?:clinical|first aid|health|financial|investment|insurance|tax|legal|law|"
                         r"workplace safety|scam|phishing|medical|sleep hygiene|cybersecurity)\b|"
                         r"急救|食品安全|用药|金融|投资|报税|劳动权益|健康|反诈|医疗", re.I)
REF_GROUP = {"resource_directory": "目录入口", "awesome_list": "索引集合", "cookbook": "食谱或实践集合",
             "tutorial": "教程入口", "course": "课程入口", "handbook": "手册入口",
             "curriculum": "课程体系入口", "learning_path": "学习路径", "practical_guide": "指南入口",
             "official_reference": "参考入口", "unknown": "候选入口"}
DOMAIN_LABELS = {
    "life": "生活与家庭", "health-safety": "健康素养与安全", "finance-law-consumer": "财务、法律与消费",
    "learning-study": "学习与研究", "digital-life": "数字生活", "career-work": "职业与工作",
    "ai-everyone": "大众 AI", "ai-engineering": "AI 工程", "creative-hobby": "创作与兴趣",
    "professional": "专业手册",
}
OPEN_LICENSE = re.compile(r"^(?:MIT|BSD-\d-Clause|Apache-\d\.\d|MPL-\d\.\d|GPL-.+|LGPL-.+|AGPL-.+|"
                          r"CC0-1\.0|CC-BY(?:-SA|-NC|-NC-SA|-ND|-NC-ND)?-\d\.\d|Unlicense|ISC)$")


def classify(text, hint):
    # GitHub search group is provenance. Confirm semantic hints separately.
    matches = [domain for domain, pattern in DOMAIN_HINTS.items() if re.search(pattern, text, re.I)]
    ordered = list(dict.fromkeys([matches[0], *matches, hint])) if matches else [hint]
    return ordered[0], ordered


def resource_type(text):
    for pattern, kind in TYPES:
        if re.search(pattern, text, re.I):
            return kind
    return "unknown"


def item_type(item, parent_type):
    if item["mode"] == "external":
        return resource_type(item["title"] + " " + item["url"])
    if item.get("translation"):
        return parent_type
    if item["mode"] == "heading":
        return "collection"
    kind = resource_type(item["title"] + " " + item["path"])
    if kind != "unknown":
        return kind
    if parent_type in {"course", "curriculum", "learning_path", "tutorial"}:
        return "tutorial"
    return "practical_guide" if parent_type in {"cookbook", "howto_series"} else "unknown"


def safe_url(value, **options):
    try:
        normalized = canonical_url(value, **options)
    except (ValueError, UnicodeError):
        return None
    return normalized if suitable(normalized) else None


def legal_record(spdx=None, url=None, *, http=None, files=()):
    if len(files) > 1 and any(re.search("content|code|data|doc", name, re.I) for name in files):
        status = "mixed"
    elif spdx and OPEN_LICENSE.fullmatch(spdx) and url:
        status = "verified"
    elif http == 404 and not spdx and not files:
        status = "no_license_found"
    elif spdx or url or files:
        status = "unclear"
    else:
        status = "unknown"
    note = "Link and metadata only; verify scope before any reuse."
    if spdx and "-NC" in spdx:
        note += " SPDX identifies a non-commercial restriction."
    if spdx and "-ND" in spdx:
        note += " SPDX identifies a no-derivatives restriction."
    return {"spdx_id": spdx if spdx not in {None, "NOASSERTION", "unknown"} else None,
            "license_url": safe_url(url) if url else None, "status": status,
            "content_reuse_allowed": False, "limitations": note, "observed_files": list(files)}


def health(status, date, method, *, http=None, reason="", redirect=None):
    return {"status": status, "checked_at": date, "method": method, "http": http,
            "reason": reason, "redirect_target": redirect}


def record(url, title, domain, kind, date, *, method, link, description, meta=None,
           aliases=(), language="unknown", region="unknown", publisher=None, audience=(),
           path=None, commit=None, source_url=None, parent=None, license=None, structure=None,
           refs=(), legacy=None, skill_level="unknown"):
    repository_id = meta["repository_id"] if meta else None
    row = {
        "schema_version": "2.1", "resource_id": legacy["id"] if legacy else stable_id(url, repository_id),
        "title": title, "alternative_titles": [], "canonical_url": url,
        "aliases": sorted(set(aliases) - {url}), "source_platform": (
            "github" if urlsplit(url).hostname == "github.com" else "gitlab" if
            urlsplit(url).hostname == "gitlab.com" else "web"),
        "source_repository": meta["full_name"] if meta else None, "publisher": publisher,
        "resource_type": kind, "primary_domain": domain, "domains": [domain],
        "topics": meta["topics"] if meta else [], "language": language, "region": region,
        "jurisdiction": region if domain == "finance-law-consumer" and region not in {"unknown", "global"} else "unknown",
        "audience": list(audience), "life_stage": [], "skill_level": skill_level, "format": (
            ["reference"] if kind == "official_reference" else ["course"] if kind in {"course", "curriculum"}
            else ["book"] if kind in {"book", "manual", "handbook"} else []),
        "parent_resource_id": parent, "child_resource_ids": [], "child_item_count": 0,
        "description": description, "prerequisites": [], "cost_model": "unknown",
        "license": license or legal_record(), "github_metrics": None,
        "provenance": {"method": method, "discovered_at": date, "last_checked_at": link["checked_at"],
                       "source_url": source_url or url, "source_file_path": path, "source_commit_sha": commit,
                       "query_refs": list(refs)},
        "structure": structure or {"headings": 0, "local_items": 0, "fingerprint": None},
        "link_check": link, "status": link["status"], "legacy_v2": legacy,
        "risk_level": "high" if domain in {"health-safety", "finance-law-consumer"} or REGULATION.search(title) else "low",
        "screening": "catalogued" if legacy else "needs_review",
    }
    if meta:
        row["github_metrics"] = {key: meta[key] for key in (
            "repository_id", "full_name", "stars", "forks", "open_issues", "created_at", "pushed_at",
            "updated_at", "archived", "default_branch", "fork")}
        row["github_metrics"]["metadata_checked_at"] = date
    row["quality_assessment"] = assess(row)
    if legacy:
        row["quality_assessment"].update(review_status="legacy_v2", recommendation="reference-only")
    return row


def legacy_projection(old):
    domain = LEGACY_DOMAIN[old["category"]]
    url = canonical_url(old["url"])
    metadata = old["github"]
    date = old["checked_at"]
    region_match = re.search(r"范围 ([\w-]+)", old["limitations"])
    region = {"united-states": "US", "united-kingdom": "GB", "china-mainland": "CN",
              "global": "global", "singapore": "SG"}.get(region_match[1] if region_match else "", "unknown")
    kind = resource_type(old["title"] + " " + old["description"]) if metadata else "official_reference"
    verification = health("archived" if metadata and metadata["archived"] else "needs_review",
                          date, "legacy-registry", reason="historical V2 snapshot")
    return record(url, old["title"], domain, kind, date, method="legacy-registry", link=verification,
                  language="unknown", region=region, description=old["description"], legacy=old,
                  license=legal_record(metadata["license"], metadata["license_url"]) if metadata else None)


class Catalog:
    def __init__(self, pages_aliases):
        self.pages_aliases = pages_aliases
        self.rows = {}
        self.by_url = {}
        self.by_repo = {}
        self.events = []
        self.edges = {}
        self.rejected = Counter()
        self.raw_count = 0

    def add(self, candidate):
        self.raw_count += 1
        url = candidate["canonical_url"]
        meta = candidate["github_metrics"]
        repo_id = meta["repository_id"] if meta else None
        prior_id = self.by_url.get(url) or self.by_repo.get(repo_id)
        if not prior_id:
            key = candidate["resource_id"]
            self.rows[key] = candidate
            self.by_url[url] = key
            if repo_id:
                self.by_repo[repo_id] = key
            return key
        prior = self.rows[prior_id]
        self.events.append({"kept_id": prior_id, "repeated_url": url, "method": candidate["provenance"]["method"],
                            "basis": "canonical-url" if url in self.by_url else "github-repository-id"})
        self.by_url[url] = prior_id
        prior["aliases"] = sorted((set(prior["aliases"]) | set(candidate["aliases"]) | {url}) - {prior["canonical_url"]})
        candidates = candidate["provenance"]["query_refs"]
        prior["provenance"]["query_refs"] = sorted(set(prior["provenance"]["query_refs"] + candidates))
        if prior["title"] != candidate["title"]:
            prior["alternative_titles"] = sorted(set(prior["alternative_titles"] + [candidate["title"]]))
        prior["domains"] = sorted(set(prior["domains"] + candidate["domains"]))
        if meta:
            self.by_repo[repo_id] = prior_id
            if not prior["github_metrics"] or candidate["provenance"]["method"] == "github-seed":
                for field in ("github_metrics", "publisher", "source_repository", "link_check", "status", "structure", "license"):
                    prior[field] = candidate[field]
                prior["provenance"]["last_checked_at"] = candidate["provenance"]["last_checked_at"]
                prior["provenance"]["source_commit_sha"] = candidate["provenance"]["source_commit_sha"]
                if candidate["language"] != "unknown":
                    prior["language"] = candidate["language"]
                if candidate["resource_type"] != "unknown":
                    prior["resource_type"] = candidate["resource_type"]
                assessment = prior["quality_assessment"]
                prior["quality_assessment"] = assess(prior)
                if assessment["review_status"] == "human-approved":
                    prior["quality_assessment"] = assessment
                elif candidate["screening"] == "catalogued":
                    prior["screening"] = "catalogued"
                    prior["quality_assessment"].update(review_status="source_verified", recommendation="reference-only")
                if prior["legacy_v2"]:
                    prior["quality_assessment"].update(review_status="legacy_v2", recommendation="reference-only")
        return prior_id

    def edge(self, source, kind, target, evidence, *, verified=True):
        if source and target and source != target:
            self.edges[(source, kind, target)] = {"from_id": source, "type": kind, "to_id": target,
                                                   "evidence": evidence, "verified": verified}

    def parent(self, child, parent, evidence):
        if child == parent:
            return
        self.edge(child, "child_of", parent, evidence)
        row = self.rows[child]
        if not row["parent_resource_id"]:
            row["parent_resource_id"] = parent
        children = self.rows[parent]["child_resource_ids"]
        if child not in children:
            children.append(child)
            children.sort()
        self.rows[parent]["child_item_count"] = len(children)


def github_record(meta, domain, kind, checked, *, origin, root=None, refs=()):
    root = root or {}
    canonical = canonical_url(meta["url"], default_branch=meta["default_branch"])
    evidence = root.get("structure", {})
    local = sum(item["mode"] != "external" for item in root.get("items", []))
    license = root.get("license_check") or {}
    return record(canonical, meta["full_name"], domain, kind, checked, method=origin,
                  link=health("archived" if meta["archived"] else "active", checked, "github-api", http=200,
                              reason="public repository metadata"),
                  description=DOMAIN_LABELS[domain] + " · " + REF_GROUP.get(kind, "资料入口") + "，适用范围见原发布方。",
                  meta=meta, aliases=[canonical_url("https://github.com/" + root.get("repository", meta["full_name"]))],
                  publisher=meta["full_name"].split("/")[0],
                  language=root.get("language") or "unknown", commit=evidence.get("commit_sha"),
                  license=legal_record(license.get("spdx_id") or meta.get("license_spdx"),
                                       license.get("url"), http=root.get("license_http"),
                                       files=evidence.get("license_files", [])),
                  structure={"headings": len(root.get("headings", [])), "local_items": local,
                             "fingerprint": root.get("fingerprint")}, refs=refs)


def official_record(item):
    probe = item["probe"]
    evidence = item.get("source_evidence")
    if probe["status"] not in {"active", "redirected", "archived"} and not evidence:
        return None
    url = safe_url(item["url"] if evidence else probe["redirect_target"] or item["url"])
    if url is None:
        return None
    method = "gitlab-project" if item.get("platform") == "gitlab" else "official-entry"
    return record(url, item["title"], item["domain"], item["resource_type"], probe["checked_at"],
                  method=method, link=probe, language=item["language"], publisher=item["publisher"],
                  region=item["region"], description=item["description"], audience=item["audience"],
                  skill_level=item.get("skill_level", "unknown"), source_url=canonical_url(evidence or item["url"]),
                  aliases=[canonical_url(item["url"])])


def select_candidates(catalog, limit):
    pools = defaultdict(list)
    for row in catalog.rows.values():
        if row["screening"] == "needs_review" and eligible(row):
            pools[row["primary_domain"]].append(row)
    for pool in pools.values():
        pool.sort(key=lambda row: (-row["quality_assessment"]["automated_score"], row["resource_id"]))
    screened = 0
    for index in range(max((len(items) for items in pools.values()), default=0)):
        for domain in DOMAIN_LABELS:
            items = pools[domain]
            if index >= len(items):
                continue
            row = items[index]
            row["screening"] = "screened"
            screened += 1
            if screened >= limit:
                return


def suggest_relations(catalog, roots, search_about):
    fingerprints, titles = {}, {}
    for seed in roots:
        if seed["fetch_status"] != "ok":
            continue
        meta = seed["metadata"]
        url = canonical_url(meta["url"])
        key = catalog.by_url.get(url)
        if not key:
            continue
        parent_url = safe_url(meta["parent_url"]) if meta.get("parent_url") else None
        catalog.edge(key, "fork_of", catalog.by_url.get(parent_url), "GitHub parent repository metadata")
        fingerprint = seed.get("fingerprint")
        if fingerprint:
            prior = fingerprints.setdefault(fingerprint, key)
            is_mirror = bool(re.search(r"\bmirror\b|镜像", meta["about"], re.I))
            catalog.edge(key, "mirror_of" if is_mirror else "duplicate", prior,
                         "Matching structural heading fingerprint. Verify upstream and scope.", verified=False)
    from difflib import SequenceMatcher

    for row in catalog.rows.values():
        if not row["github_metrics"] or not row["source_repository"]:
            continue
        key = row["resource_id"]
        title = normalized_title(row["source_repository"].split("/")[-1])
        if len(title) < 9:
            continue
        existing = titles.setdefault(title, key)
        left, right = search_about.get(key, ""), search_about.get(existing, "")
        if existing != key and len(left) > 20 and len(right) > 20 and (
            SequenceMatcher(None, left, right, autojunk=False).ratio() >= .9
        ):
            catalog.edge(key, "duplicate", existing, "Same normalized repository name and similar metadata description. Kept separately.",
                         verified=False)


def declared_mirrors(catalog, roots, entries):
    for item in entries:
        if not item.get("mirror_repository") or not item.get("source_evidence"):
            continue
        mirror, upstream = canonical_url(item["mirror_repository"]), canonical_url(item["url"])
        metadata = next((root["metadata"] for root in roots if root["fetch_status"] == "ok"
                         and canonical_url(root["metadata"]["url"]) == mirror), None)
        if metadata and re.search(r"\bmirror\b", metadata["about"], re.I):
            catalog.edge(catalog.by_url.get(mirror), "mirror_of", catalog.by_url.get(upstream),
                         "Publisher lists both endpoints and GitHub identifies the mirror: " + item["source_evidence"])


def assemble(legacy, searches, expansion, official, limit, screen_limit):
    pages_aliases = {}
    roots = expansion["roots"]
    metas = [root["metadata"] for root in roots if root["fetch_status"] == "ok"]
    for meta in metas:
        if not meta.get("homepage"):
            continue
        homepage = safe_url(meta["homepage"])
        owner, repo = meta["full_name"].casefold().split("/")
        expected_path = f"/{repo}" if repo != f"{owner}.github.io" else "/"
        if homepage and urlsplit(homepage).hostname == f"{owner}.github.io" and urlsplit(homepage).path == expected_path:
            pages_aliases[homepage] = canonical_url(meta["url"])
    catalog = Catalog(pages_aliases)
    for old in legacy:
        catalog.add(legacy_projection(old))
    for item in official["entries"]:
        row = official_record(item)
        if row:
            if (item["probe"]["status"] in {"active", "redirected"} and item.get("platform") != "gitlab"
                    and not item.get("source_evidence")):
                row["screening"] = "catalogued"
                row["quality_assessment"].update(review_status="source_verified", recommendation="reference-only")
            catalog.add(row)
        else:
            catalog.rejected["official-source-unverified"] += 1
    for seed in roots:
        if seed["fetch_status"] != "ok":
            catalog.rejected["seed-fetch-failed"] += 1
            continue
        meta = seed["metadata"]
        if not suitable(meta["full_name"] + " " + meta["about"]):
            catalog.rejected["scope-or-safety-filter"] += 1
            continue
        root = github_record(meta, seed["domain"], seed["resource_type"], seed["checked_at"],
                             origin="github-seed", root=seed)
        if (seed.get("structure", {}).get("status") == "ok" and root["risk_level"] != "high"
                and seed["group"] in {"requested-index", "added-index", "requested-series"}
                and root["status"] == "active" and not meta["fork"]):
            root["screening"] = "catalogued"
            root["quality_assessment"].update(review_status="source_verified", recommendation="reference-only")
        catalog.add(root)
    for seed in roots:
        if seed["fetch_status"] != "ok":
            continue
        meta = seed["metadata"]
        root_url = canonical_url(meta["url"])
        parent = catalog.by_url.get(root_url)
        if not parent:
            continue
        if seed.get("via"):
            catalog.edge(parent, "related_to", catalog.by_url.get(canonical_url(seed["via"])), "Collection index link")
        for item in seed["items"]:
            if len(catalog.rows) >= limit:
                catalog.rejected["candidate-ceiling"] += 1
                continue
            url = safe_url(item["url"], pages_aliases=pages_aliases)
            if not url:
                catalog.rejected["unsafe-or-invalid-url"] += 1
                continue
            external = item["mode"] == "external"
            known = catalog.by_url.get(url)
            kind = item_type(item, seed["resource_type"])
            date = seed["checked_at"]
            domain, _ = classify(item["title"] + " " + str(item["path"]), seed["domain"])
            ref = ref_commit(seed, item["path"])
            if not known:
                description = ("原集合目录列出的外部入口，需独立核验发布者与适用范围。" if external else
                               "原集合在固定提交中列出的章节或文件，可从父目录定位。")
                row = record(url, item["title"], domain, kind, date, method="github-collection-link" if external else "github-collection-item",
                             link=health("needs_review" if external else "active", date,
                                         "collection-link" if external else "git-tree",
                                         reason="link requires verification" if external else "commit-pinned document or parsed heading"),
                             language=item.get("translation") or ("unknown" if external else seed.get("language") or "unknown"),
                             description=description, source_url=ref, path=item["path"], publisher=None if external else meta["full_name"],
                             commit=seed.get("structure", {}).get("commit_sha"))
                if not external:
                    row["source_repository"] = meta["full_name"]
                known = catalog.add(row)
            else:
                catalog.raw_count += 1
                catalog.events.append({"kept_id": known, "repeated_url": url, "method": "collection-link",
                                       "basis": "canonical-url"})
            if item.get("translation"):
                evidence = "Explicit translation section" if external else "Language label and repository document path"
                catalog.edge(known, "translation_of", parent, evidence)
            if external:
                catalog.edge(known, "related_to", parent, ref)
            else:
                catalog.parent(known, parent, ref)
    about = {}
    for page in searches["pages"]:
        for meta in (page["data"] or {}).get("items", []):
            if not suitable(meta["full_name"] + " " + meta["about"]):
                catalog.rejected["scope-or-safety-filter"] += 1
                continue
            canonical = canonical_url(meta["url"])
            if len(catalog.rows) >= limit and canonical not in catalog.by_url and meta["repository_id"] not in catalog.by_repo:
                catalog.rejected["candidate-ceiling"] += 1
                continue
            evidence = meta["full_name"] + " " + meta["about"] + " " + " ".join(meta["topics"])
            domain, domains = classify(evidence, page["domain"])
            kind = resource_type(evidence)
            row = github_record(meta, domain, kind, page["checked_at"], origin="github-search",
                                refs=[f"{page['id']}:{page['page']}"])
            row["domains"] = domains
            key = catalog.add(row)
            about[key] = meta["about"]
    suggest_relations(catalog, roots, about)
    declared_mirrors(catalog, roots, official["entries"])
    select_candidates(catalog, screen_limit)
    return catalog


def ref_commit(seed, path):
    repo = canonical_url(seed["metadata"]["url"])
    commit = seed.get("structure", {}).get("commit_sha")
    return (repo + "/blob/" + commit + "/" + quote(path, safe="/")) if commit and path else repo
