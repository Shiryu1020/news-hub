"""ニュースを各ソースから取得し、docs/index.html を生成するビルドスクリプト。

使い方:
    python build.py

GitHub Actions から定期実行され、生成された docs/ が GitHub Pages で公開される。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from sources.base import fetch_all

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

load_dotenv(ROOT / ".env")


def time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    seconds = (now - dt).total_seconds()
    if seconds < 60:
        return "たった今"
    if seconds < 3600:
        return f"{int(seconds // 60)}分前"
    if seconds < 86400:
        return f"{int(seconds // 3600)}時間前"
    return f"{int(seconds // 86400)}日前"


def main() -> None:
    config = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    items = fetch_all(config)

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "items.json").write_text(
        json.dumps([i.to_dict() for i in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 表示順: 画像つきの最新記事をヒーローに、残りをグリッドへ
    hero = next((i for i in items if i.image_url), items[0] if items else None)
    grid_items = [i for i in items if i is not hero]

    categories = []
    seen = set()
    for i in items:
        if i.source not in seen:
            seen.add(i.source)
            categories.append({"id": i.source, "label": i.source_label})

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    env.filters["time_ago"] = time_ago
    template = env.get_template("index.html.j2")
    html = template.render(
        hero=hero,
        items=grid_items,
        categories=categories,
        generated_at=datetime.now(timezone.utc),
    )

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")

    static_src = ROOT / "static" / "style.css"
    static_dst = DOCS_DIR / "style.css"
    static_dst.write_text(static_src.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Generated {len(items)} items -> {DOCS_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
