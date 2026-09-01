"""Gemini API (無料枠) を使った短い要約生成。

GEMINI_API_KEY が環境変数に無い場合は None を返す。
呼び出し側は None のとき、見出しをそのまま使うなどのフォールバックをすること。

無料キーの取得方法: https://aistudio.google.com/apikey (Googleアカウントのみ、
クレジットカード登録不要)
"""
from __future__ import annotations

import os
import time

import requests

_MODEL = "gemini-3.6-flash"
_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"


def summarize_price_move(label: str, change_pct: float, headlines: list[str]) -> str | None:
    """指数・銘柄の値動きの理由を、関連見出しから2〜3文で要約する。取得できなければNoneを返す。"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not headlines:
        return None

    direction = "上昇" if change_pct >= 0 else "下落"
    headline_block = "\n".join(f"- {h}" for h in headlines)
    prompt = (
        f"{label}が本日 {change_pct:+.2f}% ({direction}) でした。"
        f"以下は関連ニュースの見出しです。\n\n{headline_block}\n\n"
        "これらの見出しから読み取れる値動きの背景を、日本語の自然な文章で2〜3文にまとめてください。"
        "見出しの単純な繰り返しは避け、要因を整理して説明してください。前置きや箇条書きは不要です。"
    )

    last_error: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            time.sleep(2 * attempt)  # 一時的なサーバーエラー(503等)向けの簡易リトライ
        try:
            resp = requests.post(
                _API_URL,
                params={"key": api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:  # noqa: BLE001
            last_error = e

    print(f"[WARN] AI summary failed after retries: {last_error}")
    return None
