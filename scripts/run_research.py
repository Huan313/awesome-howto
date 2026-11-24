"""Collect public signals, update the candidate queue and render research reports."""
import argparse
import html
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException

from scripts import collect_douyin, collect_github, collect_hackernews, collect_reddit, collect_rss
from scripts.common import Client, FetchError, ROOT, SHANGHAI, read_json, read_yaml, stamp, timestamp
from scripts.common import write_json, write_text
from scripts.deduplicate_topics import cluster
from scripts.ingest_manual_social_sources import read_records
from scripts.normalize_topics import normalize
from scripts.score_topics import metric_growth, score_group
from scripts.validate_guides import validate_repository

COLLECTION_ERRORS = (FetchError, ValueError, KeyError, TypeError, OSError, ParseError, DefusedXmlException)
RESEARCH_STATUS = {"research", "candidate", "observe", "update-existing"}


def during_window(row, start, end):
    return all(start <= timestamp(row[field]) <= end for field in ("observed_at", "event_at"))


def collect_observations(start, end, config, root=ROOT):
    observations, statuses = {}, []
    client = Client()

    def fetch(platform, name, getter, *, issues=None, normalized=False):
        count, skipped = 0, 0
        status = {"platform": platform, "query": name, "status": "ok", "observations": 0}
        try:
            for raw in getter(client):
                try:
                    record = raw if normalized else normalize(raw)
                    if during_window(record, start, end):
                        observations[record["source_id"]] = record
                        count += 1
                except (KeyError, ValueError, TypeError):
                    skipped += 1
        except COLLECTION_ERRORS as error:
            status.update(status="partial" if count else "failed",
                          reason=str(error) if isinstance(error, FetchError) else type(error).__name__)
        if skipped or issues:
            status["status"] = "partial" if count else "failed"
            status["reason"] = f"{skipped + len(issues or [])} unavailable or invalid records"
        status["observations"] = count
        statuses.append(status)
        if status["status"] in {"failed", "partial"}:
            print(f"{platform} {name}: {status['status']} ({status['reason']})", file=sys.stderr)

    if config["github"]["enabled"]:
        for name, getter in collect_github.units(config["github"], start, end):
            fetch("github", name, getter)
    if config["hackernews"]["enabled"]:
        issues = []
        fetch("hackernews", "topstories",
              lambda conn: collect_hackernews.collect(conn, config["hackernews"]["limit"], end, issues),
              issues=issues)
    if config["rss"]["enabled"]:
        for name, getter in collect_rss.units(config["rss"], end):
            fetch("rss", name, getter)
    for platform, units in (
        ("reddit", list(collect_reddit.units(config["reddit"], end))),
        ("douyin", list(collect_douyin.units(config["douyin"], end))),
    ):
        if units:
            for name, getter in units:
                fetch(platform, name, getter)
        else:
            statuses.append({"platform": platform, "query": "authorized API", "status": "skipped",
                             "observations": 0, "reason": "not enabled"})
    for platform in config["manual"]["platforms"]:
        path = root / "data/source-cache" / platform / "observations.json"
        if path.is_file():
            fetch(platform, "manual input", lambda _: read_records(path, platform), normalized=True)
        else:
            statuses.append({"platform": platform, "query": "manual input", "status": "skipped",
                             "observations": 0, "reason": "no approved observations file"})
    return list(observations.values()), statuses


def load_history(paths, start, end):
    observations, used = {}, 0
    for path in sorted(set(paths)):
        try:
            if path.stat().st_size > 2_000_000:
                raise ValueError("history size exceeded")
            batch = read_json(path)
            # Recompute IDs, canonical URLs and risk inputs when reading artifacts.
            if not isinstance(batch, list) or len(batch) > 1200:
                raise ValueError("history does not contain an observation array")
            records = [normalize(record) for record in batch]
            retained = [row for row in records if during_window(row, start, end)]
            if retained:
                used += 1
                observations.update({row["source_id"]: row for row in retained})
        except (KeyError, TypeError, OSError, ValueError):
            print("Ignored invalid or unavailable history file", file=sys.stderr)
    return list(observations.values()), used


def escape(text):
    return re.sub(r"([\\\x60*_\[\]#~])", r"\\\1", html.escape(str(text)))


def md_url(url):
    return url.replace("(", "%28").replace(")", "%29")


def write_report(output, mode, start, end, statuses, observations, guides, history_count):
    candidates = [(score_group(group, guides), group) for group in cluster(observations)]
    candidates.sort(key=lambda item: (-item[0]["score"], item[0]["topic_id"]))
    decisions = Counter(topic["status"] for topic, _ in candidates)
    queue = [item for item in candidates if item[0]["status"] != "blocked"]
    max_count = 20 if mode == "weekly" else 5
    target = 10 if mode == "weekly" else 3
    if mode == "monthly":
        selected = [(topic, group) for topic, group in queue if (
            topic["risk"] == "low" and topic["status"] in RESEARCH_STATUS
            and (topic["signals"]["evidence"] >= 65 or len({row["platform"] for row in group}) >= 2)
            and topic["category"] != "unclassified"
        )][:max_count]
    else:
        selected = queue[:max_count]
    label = "周度候选话题" if mode == "weekly" else "月度专题研究计划"
    date = end.astimezone(SHANGHAI).date().isoformat()
    directory = "weekly" if mode == "weekly" else "monthly"
    report = [
        f"# {label} · {date}", "",
        f"采集时间（UTC） {stamp(end)}。观测和事件窗口 {stamp(start)} 至 {stamp(end)}。",
        f"来源观测 {len(observations)} 条，候选聚类 {len(candidates)} 个，"
        f"风险门槛拦截 {decisions['blocked']} 个。复用周报快照 {history_count} 份。",
        "", "本报告用于选题。公开讨论和聚合指标仅代表样本，评分需由编辑核对。"
        "参考来源类型用于识别潜在证据，核心事实仍需回到原文逐项验证。", "",
        "## 来源状态", "",
    ]
    for row in statuses:
        reason = f"。{escape(row['reason'])}" if row.get("reason") else ""
        report.append(f"- {escape(row['platform'])} · {escape(row['query'])} · "
                      f"{row['status']} · {row['observations']} 条{reason}")
    report.extend(["", "## 候选与依据", ""])
    if len(selected) < target:
        report.append(f"本期符合条件 {len(selected)} 项，少于目标 {target} 项。")
    for topic, group in selected:
        report.extend([
            "", f"### {escape(topic['title'])}", "",
            f"- {topic['topic_id']} · {topic['category']} · {topic['score']}/100 · "
            f"{topic['status']}。{topic['decision_reason']}。",
            "- 分项　" + " / ".join(f"{key} {value}" for key, value in topic["signals"].items()) + "。",
            f"- 标签　{', '.join(topic['personas'])}。场景 {', '.join(topic['scenarios']) or '待核对'}。",
            f"- 首次与最近观测　{topic['first_seen']} → {topic['last_seen']}。",
        ])
        if topic["existing_guide"] != "none":
            report.append(f"- 已有指南　{topic['existing_guide']}。")
        metrics = metric_growth(group)
        if metrics:
            report.append("- 同平台可比增长　" + "、".join(
                f"{platform} {escape(query)} {unit} {growth:+.1f}%"
                for platform, _, query, unit, growth in metrics[:5]
            ) + "。")
        else:
            report.append("- 缺少可比历史值，无法计算趋势增长。")
        for item in sorted(group, key=lambda row: row["observed_at"], reverse=True)[:5]:
            report.append(f"- 来源　[{escape(item['platform'])} · {escape(item['query'])}]"
                          f"({md_url(item['url'])}) · {item['kind']} · {item['event_basis']} {item['event_at']}。")
        if mode == "monthly":
            sustained = len({row["observed_at"][:10] for row in group}) > 1
            report.extend([
                f"- 持续性　{'多个日期有观测，需核对同类样本' if sustained else '单日观测，持续性待核对'}。",
                "- 证据缺口　确认典型读者、任务频率、原始材料实际支持的步骤，以及地区或版本限制。",
                "- 研究计划　定位官方文档或原始论文，抽样核对读者问题，用虚构输入实测关键操作。",
                "- HowTo 提纲　任务与受众 → 前置条件 → 操作与验收 → 故障与停止条件 → 可复查证据。",
            ])
    source_ids = {source_id for topic, _ in queue for source_id in topic["source_refs"]}
    write_json(output / "source-cache" / "observations.json",
               sorted((row for row in observations if row["source_id"] in source_ids),
                      key=lambda row: row["source_id"]))
    write_json(output / "source-cache" / "source-status.json", statuses)
    write_json(output / "topic-queue" / f"{mode}-{date}.json", [topic for topic, _ in queue])
    write_json(output / "selection.json", {"categories": sorted({topic["category"] for topic, _ in selected})})
    write_text(output / directory / f"{date}.md", "\n".join(report) + "\n")
    print(f"{mode}: {len(selected)} selected, {len(queue)} in queue, {decisions['blocked']} blocked.")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["weekly", "monthly"])
    parser.add_argument("--output", default=ROOT / "out" / "research", type=Path)
    parser.add_argument("--history", action="append", default=[], type=Path,
                        help="directory with previously reviewed or trusted weekly artifacts")
    args = parser.parse_args()
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=7 if args.mode == "weekly" else 30)
    records, statuses = collect_observations(start, end, read_yaml(ROOT / "data/sources.yaml"))
    historical_files = (list((ROOT / "data/weekly").rglob("observations.json"))
                        + [path for folder in args.history for path in folder.rglob("observations.json")])
    history, count = load_history(historical_files, start, end)
    seen = {row["source_id"]: row for row in history + records}
    guides, _ = validate_repository()
    write_report(args.output, args.mode, start, end, statuses, list(seen.values()),
                 [item for _, item in guides], count)
    if not any(item["status"] in {"ok", "partial"} and
               item["platform"] in {"github", "hackernews", "rss"} for item in statuses):
        raise SystemExit("No public collectors succeeded. Read source-cache/source-status.json.")


if __name__ == "__main__":
    main()
