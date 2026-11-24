"""Hacker News stories from the official read-only Firebase API."""
from datetime import datetime, timezone

from scripts.common import FetchError, stamp

API = "https://hacker-news.firebaseio.com/v0"


def collect(client, limit, end, issues):
    for item_id in client.json(f"{API}/topstories.json")[:limit]:
        if type(item_id) is not int:
            continue
        try:
            item = client.json(f"{API}/item/{item_id}.json")
            if not item or item.get("deleted") or item.get("dead"):
                continue
            if item.get("type") != "story":
                continue
            yield dict(platform="hackernews", title=item["title"],
                       url=f"https://news.ycombinator.com/item?id={item_id}",
                       query="topstories", method="public-api", observed_at=stamp(end),
                       event_at=datetime.fromtimestamp(item["time"], timezone.utc),
                       event_basis="published", metrics={"points": item.get("score"),
                                                        "comments": item.get("descendants")})
        except (FetchError, KeyError, TypeError, ValueError) as error:
            issues.append(str(error) if isinstance(error, FetchError) else type(error).__name__)
