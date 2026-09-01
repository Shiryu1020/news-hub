"""株価ソース。

定量データ(終値・前日比)を yfinance (無料・APIキー不要) で取得し、
関連ニュース見出しを Google News RSS (無料・APIキー不要) から取得したうえで、
Claude API (Haiku) を使って「なぜ動いたか」を2〜3文の日本語サマリに要約する。

ANTHROPIC_API_KEY が未設定の場合は、AI要約をスキップして一番関連度の高い
見出しをそのままサマリとして使う(フォールバック)。
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import yfinance as yf

from .ai_summary import summarize_price_move
from .base import Item, RelatedLink

SOURCE_NAME = "株価"

_CHART_WIDTH = 100
_CHART_HEIGHT = 32


def _sparkline_points(closes: list[float]) -> str:
    """3ヶ月分の終値を SVG viewBox (0 0 100 32) 上の折れ線座標に変換する。"""
    if len(closes) < 2:
        return ""
    lo, hi = min(closes), max(closes)
    span = hi - lo or 1.0
    n = len(closes)
    points = []
    for i, c in enumerate(closes):
        x = i / (n - 1) * _CHART_WIDTH
        y = _CHART_HEIGHT - (c - lo) / span * _CHART_HEIGHT
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _fetch_related_news(query: str, limit: int = 5) -> list[RelatedLink]:
    rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ja&gl=JP&ceid=JP:ja"
    feed = feedparser.parse(rss_url)
    links = []
    for entry in feed.entries[:limit]:
        links.append(RelatedLink(title=entry.title, url=entry.link))
    return links


def fetch(config: dict) -> list[Item]:
    items: list[Item] = []
    for ticker_cfg in config.get("tickers", []):
        symbol = ticker_cfg["symbol"]
        label = ticker_cfg.get("label", symbol)
        news_query = ticker_cfg.get("news_query", label)

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d").dropna(subset=["Close"])
        if hist.empty:
            continue

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        change_pct = (
            (latest["Close"] - prev["Close"]) / prev["Close"] * 100
            if prev["Close"]
            else 0.0
        )

        hist_3mo = ticker.history(period="3mo").dropna(subset=["Close"])
        closes_3mo = [float(c) for c in hist_3mo["Close"].tolist()]
        chart_points = _sparkline_points(closes_3mo)
        chart_trend = "up" if (closes_3mo and closes_3mo[-1] >= closes_3mo[0]) else "down"

        related_links = _fetch_related_news(news_query)
        headlines = [l.title for l in related_links]
        summary = summarize_price_move(label, change_pct, headlines) or (
            headlines[0] if headlines else ""
        )

        items.append(
            Item(
                source="stock",
                title=label,
                url=f"https://finance.yahoo.com/quote/{symbol}",
                published_at=hist.index[-1].to_pydatetime().astimezone(timezone.utc),
                summary=summary,
                metrics={
                    "close": round(float(latest["Close"]), 2),
                    "change_pct": round(float(change_pct), 2),
                    "volume": int(latest["Volume"]),
                    "chart_points": chart_points,
                    "chart_trend": chart_trend,
                },
                related_links=related_links,
            )
        )
    return items
