"""Normalize approved, minimized observation exports from social platforms."""
import argparse
from pathlib import Path

from scripts.common import ROOT, read_json, read_yaml, write_json
from scripts.normalize_topics import normalize


def read_records(path, platform):
    records = read_json(path)
    if not isinstance(records, list) or len(records) > 200:
        raise ValueError("expected an array of up to 200 observations")
    for index, raw in enumerate(records, 1):
        try:
            if not isinstance(raw, dict) or raw.get("platform", platform) != platform:
                raise ValueError("observation belongs to a different platform")
            method = raw.get("method", "manual")
            if method not in {"manual", "authorized-export"}:
                raise ValueError("manual input requires a manual or authorized-export method")
            yield normalize({**raw, "platform": platform, "kind": "social", "method": method})
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
