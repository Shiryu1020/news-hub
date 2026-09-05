"""汎用RSSソース。

sources.yaml に feeds(RSS URLのリスト)を指定するだけで、新しいカテゴリを追加できる。
label はカテゴリ名(トピック軸)。feeds の各項目に name を指定すると、
記事ごとに発行元(publisher)として表示される(カテゴリ自体はまとめたまま)。

例:
    biz_strategy:
      enabled: true
      module: sources.rss
      label: "経営・戦略"
      feeds:
        - url: http://feeds.hbr.org/harvardbusiness
          name: "Harvard Business Review"
        - url: https://www.mckinsey.com/insights/rss
          name: "McKinsey Insights"
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import feedparser

from .ai_summary import generate_insight
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
    category_label = config.get("label", "")
    items: list[Item] = []
    for feed_cfg in config.get("feeds", []):
        # 文字列(URLのみ)でも、{url, name}形式でも受け付ける
        if isinstance(feed_cfg, str):
            feed_url, publisher_name = feed_cfg, None
        else:
            feed_url, publisher_name = feed_cfg["url"], feed_cfg.get("name")

        feed = feedparser.parse(feed_url)
        publisher = publisher_name or feed.feed.get("title", "")

        for entry in feed.entries[:limit_per_feed]:
            title = entry.get("title", "(無題)")
            summary = _clean_summary(entry)
            items.append(
                Item(
                    source="",  # base.fetch_all が source / source_label を設定する
                    title=title,
                    url=entry.get("link", ""),
                    published_at=_parse_published(entry),
                    summary=summary,
                    insight=generate_insight(title, summary, category_label) or "",
                    image_url=_extract_image(entry),
                    publisher=publisher,
                )
            )
    return items
