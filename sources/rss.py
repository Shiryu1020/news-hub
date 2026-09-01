"""汎用RSSソース。

sources.yaml に feeds(RSS URLのリスト)を指定するだけで、新しいカテゴリを追加できる。
label をあわせて指定すると、そのカテゴリ名でタブ表示される。

例:
    biz_strategy:
      enabled: true
      module: sources.rss
      label: "経営・戦略"
      feeds:
        - http://feeds.hbr.org/harvardbusiness
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import feedparser

from .base import Item

_TAG_RE = re.compile(r"<[^>]+>")


def _parse_published(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _clean_summary(entry, max_len: int = 160) -> str:
    text = entry.get("summary") or entry.get("description") or ""
    text = _TAG_RE.sub("", text).strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _extract_image(entry) -> str | None:
    """フィードにサムネイル画像があれば拾う(無ければ None、見出しのみでOK)。"""
    for thumb in entry.get("media_thumbnail", []) or []:
        if thumb.get("url"):
            return thumb["url"]
    for media in entry.get("media_content", []) or []:
        medium = media.get("medium", "")
        mtype = media.get("type", "")
        if media.get("url") and (medium == "image" or mtype.startswith("image")):
            return media["url"]
    for link in entry.get("links", []) or []:
        if link.get("type", "").startswith("image") and link.get("href"):
            return link["href"]
    html = entry.get("summary", "") or entry.get("description", "") or ""
    m = re.search(r'<img[^>]+src="([^"]+)"', html)
    return m.group(1) if m else None


def fetch(config: dict) -> list[Item]:
    limit_per_feed = config.get("limit_per_feed", 5)
    items: list[Item] = []
    for feed_url in config.get("feeds", []):
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit_per_feed]:
            items.append(
                Item(
                    source="",  # base.fetch_all が source / source_label を設定する
                    title=entry.get("title", "(無題)"),
                    url=entry.get("link", ""),
                    published_at=_parse_published(entry),
                    summary=_clean_summary(entry),
                    image_url=_extract_image(entry),
                )
            )
    return items
