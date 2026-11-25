"""Repository discovery via GitHub's public Search API."""
import os
from urllib.parse import urlencode

from scripts.common import FetchError, stamp


def units(config, start, end):
    for keyword in config["queries"]:
        yield keyword, lambda client, keyword=keyword: collect(client, keyword, start, end)


def collect(client, keyword, start, end):
    params = urlencode({
        "q": f"{keyword} is:public archived:false pushed:>={start.date().isoformat()}",
        "sort": "updated", "order": "desc", "per_page": 12,
    })
    url = "https://api.github.com/search/repositories?" + params
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("HOWTO_GITHUB_TOKEN")
    if token:
        try:
            body = client.json(url, {**headers, "Authorization": f"Bearer {token}"})
        except FetchError as error:
            if str(error) not in {"HTTP 401", "HTTP 403"}:
                raise
            body = client.json(url, headers)
    else:
        body = client.json(url, headers)
    if body.get("incomplete_results"):
        raise FetchError("GitHub search returned incomplete_results")
    for item in body["items"]:
        title = item["name"].replace("-", " ").replace("_", " ")
        if item.get("description"):
            title += " | " + item["description"]
        yield dict(platform="github", title=title, url=item["html_url"], query=keyword,
                   method="public-api", observed_at=stamp(end), event_at=item["pushed_at"],
                   event_basis="pushed", metrics={"stars": item["stargazers_count"],
                                                 "forks": item["forks_count"]})
