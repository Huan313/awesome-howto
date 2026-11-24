"""Cluster exact URLs, explicit topic keys and highly similar titles."""
import re
import unicodedata
from difflib import SequenceMatcher

from scripts.normalize_topics import fingerprint


def normalized_title(title):
    title = unicodedata.normalize("NFKC", title).casefold()
    title = re.sub(r"^\s*(?:how to\b|如何|怎样)\s*", "", title)
    return " ".join(re.findall(r"[a-z0-9]+|[\u3400-\u9fff]", title))


def similar(left, right):
    left, right = normalized_title(left), normalized_title(right)
    if not left or not right:
        return False
    if left == right:
        return True
    if min(len(left), len(right)) < 14:
        return False
    left_words, right_words = set(left.split()), set(right.split())
    overlap = len(left_words & right_words) / len(left_words | right_words)
    return overlap >= 0.70 and SequenceMatcher(None, left, right, autojunk=False).ratio() >= 0.83


def same_topic(left, right):
    key = left.get("topic_key")
    shared_feed = left.get("platform") == "douyin" or right.get("platform") == "douyin"
    shared_url = left.get("url") and left.get("url") == right.get("url") and not shared_feed
    return (bool(key and key == right.get("topic_key"))
            or bool(shared_url)
            or similar(left["title"], right["title"]))


def cluster(observations):
    groups = []
    for item in sorted(observations, key=lambda row: (row.get("observed_at", ""), row["source_id"])):
        for group in groups:
            if same_topic(item, group[0]) or (
                item.get("topic_key") and any(item["topic_key"] == other.get("topic_key") for other in group)
            ):
                group.append(item)
                break
        else:
            groups.append([item])
    return groups


def topic_id(group):
    key = next((item["topic_key"] for item in group if "topic_key" in item), None)
    return fingerprint("topic", key or normalized_title(group[0]["title"]) or group[0]["title"])
