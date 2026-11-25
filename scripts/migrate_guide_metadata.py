"""Migrate V1 frontmatter with per-guide, reviewed annotations."""
import argparse
import json
from pathlib import Path

from scripts.common import ROOT, parse_yaml, read_yaml, write_text
from scripts.validate_guides import split_frontmatter, validate_guide

STATUS_MAP = {"draft": "draft", "review-required": "expert-review",
              "stable": "editorial-review", "published": "editorial-review", "retired": "retired"}
REVIEWED_FIELDS = {"category", "subcategory", "personas", "age_groups", "occupations", "life_stages",
                   "scenarios", "region", "prerequisites", "last_verified_at", "claim_evidence", "version",
                   "execution_status"}


def migrate(metadata, annotation):
    if REVIEWED_FIELDS - annotation.keys():
        raise ValueError("a guide requires its own reviewed annotations")
    return {**metadata, "status": STATUS_MAP[metadata["status"]], **annotation}


def markdown(metadata, body):
    header = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items())
    return f"---\n{header}\n---\n\n{body.strip()}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    annotations = read_yaml(args.annotations)
    pending = []
    for path in sorted((args.root / "guides").glob("*/*.md")):
        header, body = split_frontmatter(path)
        metadata = parse_yaml(header)
        if "claim_evidence" in metadata:
            continue
        annotation = annotations.get(metadata["id"], {})
        migrated = migrate(metadata, annotation)
        validate_guide(migrated, args.root)
        pending.append((path, markdown(migrated, body)))
    if args.apply:
        for path, value in pending:
            write_text(path, value)
    print(f"{len(pending)} V1 guide(s) validated for migration.")


if __name__ == "__main__":
    main()
