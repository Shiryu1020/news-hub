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
                )
            )
    return items
