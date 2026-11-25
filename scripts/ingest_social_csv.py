"""Import minimized public social observations from CSV to the normalized JSON format."""
import argparse
import csv
from pathlib import Path

from scripts.common import ROOT, read_yaml, write_json
from scripts.ingest_manual_social_sources import normalize_manual

REQUIRED = {"platform", "title", "url", "query", "observed_at", "sample_limit"}



def parse_rows(stream, platform):
    reader = csv.DictReader(stream)
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
        raise ValueError("required CSV columns missing")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("duplicate CSV header")
    ids = set()
    for number, row in enumerate(reader, 2):
        if number > 201:
            raise ValueError("CSV import is limited to 200 observations")
        try:
            row = {key: (value or "").strip() for key, value in row.items() if key and isinstance(value, str)}
            if row.get("example", "").lower() in {"1", "true", "yes"}:
                continue
            if row.get("platform") != platform or any(not row.get(key) for key in REQUIRED):
                raise ValueError("missing required input or platform mismatch")
            unit, value = row.get("metric_unit"), row.get("metric_value")
            metrics = {}
            if unit or value:
                if not unit or not value or not value.isdecimal():
                    raise ValueError("metric requires a valid platform-specific unit and integer value")
                metrics[unit] = int(value)
            audience = [item.strip() for item in row.get("audience", "").split("|") if item.strip()]
            basis = row.get("audience_basis") or "unknown"
            signal = row.get("signal_type") or "unknown"
            normalized = normalize_manual({
                **{key: row[key] for key in REQUIRED}, "method": "manual", "metrics": metrics,
                "summary": row.get("summary", ""), "task": row.get("task", ""),
                "signal_type": signal, "audience": audience, "audience_basis": basis,
                "region": row.get("region") or "unknown",
            }, platform)
            if normalized["source_id"] in ids:
                raise ValueError("duplicate observation canonical URL, query and time")
            ids.add(normalized["source_id"])
        except (TypeError, ValueError, KeyError) as error:
            raise ValueError(f"invalid minimized CSV observation at row {number}") from error
        yield normalized


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    allowed = read_yaml(ROOT / "data/sources.yaml")["manual"]["platforms"]
    parser.add_argument("platform", choices=allowed)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig", newline="") as stream:
        records = list(parse_rows(stream, args.platform))
    write_json(args.output, records)
    print(f"{len(records)} public observations imported; examples skipped.")


if __name__ == "__main__":
    main()
