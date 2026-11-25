"""Extract Markdown headings and link metadata without retaining third-party prose."""
import base64
import re
from collections import Counter
from html import unescape
from urllib.parse import urljoin

from markdown_it import MarkdownIt

from scripts.check_links import slug
from scripts.normalize_topics import clean_text

PARSER = MarkdownIt("commonmark").enable("table")
SKIP_TITLE = re.compile(r"^(contents|table of contents|license|licence|contributors|sponsors|"
                        r"目录|许可证|贡献者|赞助|致谢)\b", re.I)
EXCLUDE = re.compile(
    r"\b(?:exploit(?:s|ation)?|malware|payloads?|pentest(?:ing)?|offensive|osint|"
    r"credential dumping|jailbreak(?:s|ing)?|red team(?:ing)?|weapons?|bomb making|"
    r"phishing kit|dark web|pirat(?:e|ed|ing)|cracked|hitman|ddos|surveillance|automated.{0,24}censorship)\b"
    r"|wargame|渗透测试|漏洞利用|攻击载荷|武器|炸弹|恶意软件|勒索软件|破解软件|绕过验证码|暗网",
    re.I,
)
LANGUAGES = {"中文": "zh", "简体中文": "zh-CN", "简体中文版": "zh-CN", "繁體中文": "zh-TW",
             "繁體中文版": "zh-TW", "日本語": "ja", "한국어": "ko", "english": "en", "español": "es",
             "français": "fr", "deutsch": "de", "čeština": "cs", "ελληνικά": "el", "русский": "ru",
             "italiano": "it", "português": "pt", "bahasa indonesia": "id", "türkçe": "tr"}
TRANSLATIONS = re.compile(r"(translations?|language versions?|翻译|翻譯|多语言|言語|번역)", re.I)
LOCALE_README = re.compile(r"(?:^|/)readme[-_.]([a-z]{2,3}(?:[-_][a-z]{2,4})?)\.(?:md|rst)$", re.I)


def translation_language(link, path=None):
    """Accept an explicit translation section or a matching local README locale."""
    language = LANGUAGES.get(link["label"].casefold())
    if language and TRANSLATIONS.search(link["heading"]):
        return language
    locale = LOCALE_README.search(path) if path else None
    if language and locale:
        path_language = locale[1].casefold().replace("_", "-")
        if path_language in {language.casefold(), language.split("-")[0]}:
            return language
    return None


def suitable(text):
    return bool(text and not EXCLUDE.search(text))


def link_labels(children):
    href, current = "", []
    for token in children:
        if token.type == "link_open":
            href, current = token.attrGet("href") or "", []
        elif token.type == "link_close":
            yield href, clean_text(" ".join(current), 100)
            href = ""
        elif href and token.type in {"text", "code_inline"}:
            current.append(token.content)


def plain_heading(value):
    text = re.sub(r":(?:[a-z0-9_+-]+):", "", unescape(value.casefold()))
    return text.strip(" \u00a0·:–—")


def parse_document(payload, root_url, safe_outline=()):
    path = payload["path"]
    if payload["encoding"] != "base64" or payload.get("size", 0) > 220_000:
        return {"path": path, "headings": [], "links": [], "status": "oversize-or-unsupported"}
    markdown = base64.b64decode(payload["content"]).decode("utf-8", errors="replace")
    tokens = PARSER.parse(markdown)
    headings, links = [], []
    used = Counter()
    current = ""
    title = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            heading = tokens[index + 1]
            current = clean_text(" ".join(part.content for part in heading.children or []
                                          if part.type in {"text", "code_inline"}), 100)
            anchor = slug(current)
            if title is None and token.tag == "h1" and suitable(current):
                title = current
            count = used[anchor]
            used[anchor] += 1
            if count:
                anchor += f"-{count}"
            if (token.tag in {"h2", "h3", "h4"} and anchor and suitable(current) and not SKIP_TITLE.search(current)
                    and (not safe_outline or plain_heading(current) in safe_outline)):
                headings.append({"title": current, "anchor": anchor})
        if token.type != "inline" or not suitable(current or "top"):
            continue
        for href, label in link_labels(token.children or []):
            if safe_outline:
                if href.startswith("#") and plain_heading(label) in safe_outline and suitable(label):
                    item = {"title": plain_heading(label), "anchor": href[1:]}
                    if item not in headings:
                        headings.append(item)
                continue
            target = urljoin(root_url, href)
            if (len(links) < 650 and href and not href.startswith("#") and len(href) < 500
                    and len(label) > 2 and suitable(label + " " + target)):
                links.append({"href": href, "label": label, "heading": current,
                              "translation": LANGUAGES.get(label.casefold()) if TRANSLATIONS.search(current) else None})
    # Short titles and link destinations are the only textual content retained.
    return {"path": path, "title": title, "headings": headings[:100], "links": links, "status": "parsed"}
