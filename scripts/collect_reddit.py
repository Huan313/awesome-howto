"""Optional Reddit API integration for previously approved external clients."""
import os
import re
from datetime import datetime, timezone

from scripts.common import stamp


def units(config, end):
    if os.getenv(config["enabled_by"]) != "true":
        return
    token = os.getenv("REDDIT_ACCESS_TOKEN")
    if not token:
        return
    for community in config["communities"]:
        yield community, lambda client, community=community: collect(client, community, token, end)


def collect(client, community, token, end):
    if not token:
        from scripts.common import FetchError
        raise FetchError("enabled without approved OAuth token")
    if not re.fullmatch(r"[A-Za-z0-9_]{2,25}", community):
        raise ValueError("invalid subreddit name")
    response = client.json(f"https://oauth.reddit.com/r/{community}/hot?limit=20",
                           {"Authorization": f"Bearer {token}"})
    for item in response["data"]["children"]:
        post = item["data"]
        if post.get("over_18") or not post["permalink"].startswith("/r/"):
            continue
        yield dict(platform="reddit", title=post["title"],
                   url="https://www.reddit.com" + post["permalink"], query=community,
                   method="authorized-api", observed_at=stamp(end),
                   event_at=datetime.fromtimestamp(post["created_utc"], timezone.utc),
                   event_basis="published", metrics={"points": post.get("score"),
                                                    "comments": post.get("num_comments")})
