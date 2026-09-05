"""Gemini API (無料枠) を使った短い要約・示唆生成。

GEMINI_API_KEY が環境変数に無い場合は None を返す。
呼び出し側は None のとき、見出しをそのまま使うなどのフォールバックをすること。

無料キーの取得方法: https://aistudio.google.com/apikey (Googleアカウントのみ、
クレジットカード登録不要)
"""
from __future__ import annotations

import os
import time

import requests

_MODEL = "gemini-flash-lite-latest"  # 無料枠のクォータに余裕がある軽量モデル
_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"

# 無料枠のレート制限(RPM)に収まるよう、呼び出し間隔を空ける(記事数が多いRSSソースが
# 増えても429で失敗しないようにするための簡易スロットリング)。
_MIN_INTERVAL_SEC = 4.5
_last_call_at: float = 0.0


def _throttle() -> None:
    global _last_call_at
    wait = _MIN_INTERVAL_SEC - (time.monotonic() - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def _call_gemini(prompt: str) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    last_error: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            time.sleep(15 * attempt)  # 429(レート制限)は数秒待つだけでは解消しないため長めに待つ
        _throttle()
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

    print(f"[WARN] Gemini call failed after retries: {last_error}")
    return None


def summarize_price_move(label: str, change_pct: float, headlines: list[str]) -> str | None:
    """指数・銘柄の値動きの理由を、関連見出しから2〜3文で要約する。取得できなければNoneを返す。"""
    if not headlines:
        return None

    direction = "上昇" if change_pct >= 0 else "下落"
    headline_block = "\n".join(f"- {h}" for h in headlines)
    prompt = (
        f"{label}が本日 {change_pct:+.2f}% ({direction}) でした。"
        f"以下は関連ニュースの見出しです。\n\n{headline_block}\n\n"
        "これらの見出しから読み取れる値動きの背景を、日本語の自然な文章で2〜3文にまとめてください。"
        "見出しの単純な繰り返しは避け、要因を整理して説明してください。前置きや箇条書きは不要です。"
    )
    return _call_gemini(prompt)


def generate_insight(title: str, summary: str, category_label: str) -> str | None:
    """記事の見出し・要約から「何が言えるか」の示唆を1〜2文で生成する。取得できなければNoneを返す。"""
    if not title:
        return None

    prompt = (
        "以下は経済・ビジネス系ニュースの記事情報です。\n\n"
        f"カテゴリ: {category_label}\n"
        f"タイトル: {title}\n"
        f"要約: {summary or '(要約なし)'}\n\n"
        "この記事の内容を単に繰り返すのではなく、そこから読み取れる「示唆」"
        "(これが意味すること、今後注目すべき点、鵜呑みにせず確認すべき点があればそれも含む)"
        "を、日本語で1〜2文にまとめてください。前置き・見出しの繰り返しは不要です。"
    )
    return _call_gemini(prompt)
