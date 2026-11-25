"""Refresh public GitHub statistics and license links without changing descriptions."""
import argparse
from datetime import datetime

from scripts.build_resource_index import REGISTRY, read_registry
from scripts.common import Client, FetchError, ROOT, SHANGHAI, write_json


def refresh(row, client, date):
    base = "https://api.github.com/repos/" + row["url"].removeprefix("https://github.com/")
    public = client.json(base)
    license = (public.get("license") or {}).get("spdx_id")
    url = None
    try:
        url = client.json(base + "/license").get("html_url")
    except FetchError as error:
        if str(error) != "HTTP 404":
            raise
    known = bool(license and license != "NOASSERTION" and url)
    updated = {**row, "checked_at": date, "github": {
        "stars": public["stargazers_count"], "forks": public["forks_count"], "pushed_at": public["pushed_at"],
        "archived": public["archived"], "license": license if known else "unknown", "license_url": url,
    }}
    if not known:
        updated.update(editorial_grade="license-unclear", use_mode="reference-only")
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = read_registry()
    client, date = Client(), datetime.now(SHANGHAI).date().isoformat()
    updated = []
    for row in rows:
        try:
            updated.append(refresh(row, client, date) if row["github"] else row)
        except FetchError as error:
            raise SystemExit(f"{row['id']}: {error}; registry preserved") from None
    if args.apply:
        write_json(ROOT / REGISTRY, updated)
    print(f"{sum(row['github'] is not None for row in updated)} GitHub records verified; applied={args.apply}")


if __name__ == "__main__":
    main()
