"""Normalize approved, minimized observation exports from social platforms."""
import argparse
from pathlib import Path

from scripts.common import ROOT, read_json, read_yaml, write_json
from scripts.normalize_topics import METRICS, normalize

PLATFORM_UNITS = {"xiaohongshu": {"likes", "saves", "comments", "views"},
                  "douyin": {"likes", "views", "comments", "heat"},
                  "reddit": {"points", "comments"}, "x": {"likes", "views", "comments"},
                  "youtube": {"likes", "views", "comments"}, "tiktok": {"likes", "views", "comments"}}


def normalize_manual(raw, platform):
    metrics = raw.get("metrics", {})
    if not isinstance(metrics, dict) or any(
        unit not in PLATFORM_UNITS.get(platform, METRICS) or type(value) is not int or value < 0
        for unit, value in metrics.items()
    ):
        raise ValueError("invalid platform metric or value")
    audience = raw.get("audience", [])
    if audience:
        valid = read_yaml(ROOT / "data/personas.yaml")["personas"]
        if raw.get("audience_basis") not in {"self-described", "documented-sample"} or any(
            value not in valid or value == "unknown" for value in audience
        ):
            raise ValueError("audience requires observed basis and known vocabulary")
    if raw.get("signal_type") == "demand" and not raw.get("task"):
        raise ValueError("demand requires a concrete task")
    return normalize({"sample_limit": "手工观测，样本限制未提供", **raw,
                      "platform": platform, "kind": "social", "method": raw.get("method", "manual")})


def read_records(path, platform):
    records = read_json(path)
    if not isinstance(records, list) or len(records) > 200:
        raise ValueError("expected an array of up to 200 observations")
    for index, raw in enumerate(records, 1):
        try:
            if not isinstance(raw, dict) or raw.get("platform", platform) != platform:
                raise ValueError("observation belongs to a different platform")
            if raw.get("example") is True:
                continue
            method = raw.get("method", "manual")
            if method not in {"manual", "authorized-export"}:
                raise ValueError("manual input requires a manual or authorized-export method")
            yield normalize_manual(raw, platform)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid manual observation at row {index}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    platforms = read_yaml(ROOT / "data/sources.yaml")["manual"]["platforms"]
    parser.add_argument("platform", choices=platforms)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json(args.output, list(read_records(args.input, args.platform)))


if __name__ == "__main__":
    main()
