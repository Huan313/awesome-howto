"""Read dated RSS/Atom entries without persisting full feed content."""
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from defusedxml.ElementTree import fromstring

from scripts.common import stamp, timestamp


def units(config, end):
    for feed in config["feeds"]:
        yield feed["name"], lambda client, feed=feed: collect(client, feed, end)


def collect(client, feed, end):
    root = fromstring(client.get(feed["url"]))
    entries = [node for node in root.iter()
               if node.tag.rsplit("}", 1)[-1] in {"item", "entry"}]
    for node in entries[:60]:
        fields = {child.tag.rsplit("}", 1)[-1]: child for child in node}
        title = fields.get("title")
        link = next((child for child in node if child.tag.rsplit("}", 1)[-1] == "link"
                     and child.get("rel", "alternate") == "alternate"), None)
        date = next((fields[key].text for key in ("pubDate", "published", "updated", "date")
                     if key in fields and fields[key].text), None)
        if title is None or link is None or date is None:
            continue
        try:
            published = timestamp(date)
        except ValueError:
            try:
                published = timestamp(parsedate_to_datetime(date))
            except (TypeError, ValueError):
                continue
        yield dict(platform="rss", kind=feed["kind"], title="".join(title.itertext()),
                   url=urljoin(feed["url"], link.get("href") or link.text or ""),
                   query=feed["name"], method="rss", observed_at=stamp(end),
                   event_at=published, event_basis="published")
