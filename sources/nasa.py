"""NASA APOD (Astronomy Picture of the Day) ソース。
無料・無登録の DEMO_KEY で動作するので、最初の動作確認用に使う。
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from .base import Item

SOURCE_NAME = "NASA 今日の天体写真"
API_URL = "https://api.nasa.gov/planetary/apod"


def fetch(config: dict) -> list[Item]:
    api_key = config.get("api_key", "DEMO_KEY")
    resp = requests.get(API_URL, params={"api_key": api_key}, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    published = datetime.fromisoformat(data["date"]).replace(tzinfo=timezone.utc)
    return [
        Item(
            source="nasa_apod",
            title=data.get("title", "NASA APOD"),
            url=data.get("hdurl") or data.get("url", "https://apod.nasa.gov/"),
            published_at=published,
            summary=data.get("explanation", ""),
            image_url=data.get("url") if data.get("media_type") == "image" else None,
        )
    ]
