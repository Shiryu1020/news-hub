"""共通のデータ型とソースの読み込みロジック。

新しいソースを追加するときは sources/ に1ファイル追加し、
- SOURCE_NAME: str
- fetch(config: dict) -> list[Item]
の2つを定義するだけでよい。sources.yaml に登録すれば自動的に取り込まれる。
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RelatedLink:
    title: str
    url: str


@dataclass
class Item:
    source: str                     # ソースID (例: "nasa_apod", "stock")
    title: str
    url: str
    published_at: datetime
    summary: str = ""
    image_url: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)       # 定量データ (例: {"price": 2700, "change_pct": -1.8})
    related_links: list[RelatedLink] = field(default_factory=list)  # 定性的な補足情報(関連ニュース見出し等)
    source_label: str = ""          # 表示用ソース名 (例: "株価")。fetch_all が自動で埋める
    icon: str = ""                  # 表示用アイコン絵文字 (例: "📈")。fetch_all が自動で埋める

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_label": self.source_label,
            "icon": self.icon,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "summary": self.summary,
            "image_url": self.image_url,
            "metrics": self.metrics,
            "related_links": [vars(l) for l in self.related_links],
        }


def load_source_module(module_path: str):
    return importlib.import_module(module_path)


def fetch_all(sources_config: dict) -> list[Item]:
    items: list[Item] = []
    for source_id, cfg in sources_config.get("sources", {}).items():
        if not cfg.get("enabled", False):
            continue
        module = load_source_module(cfg["module"])
        label = cfg.get("label") or getattr(module, "SOURCE_NAME", source_id)
        icon = cfg.get("icon", "")
        try:
            fetched = module.fetch(cfg)
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] source '{source_id}' failed: {e}")
            continue
        for item in fetched:
            item.source = source_id
            item.source_label = label
            item.icon = icon
        items.extend(fetched)
    items.sort(key=lambda i: i.published_at, reverse=True)
    return items
