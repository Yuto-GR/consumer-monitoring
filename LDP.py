#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ldp_watcher.py  rev-4.7-LDP-r4  (2025-06-28)

■ 自民党サイト（/activity）を巡回し，
   過去 4 日＋当日＋未来 10 日の 15 日分から
   消費者関連イベントのみ抽出して表示。
   ─ 重複タイトルは「本文が詳しい方」を優先して 1 行に集約。
"""

# ───────── Imports ──────────────────────────────────────────
import re, time, sys, requests
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ───────── Global settings ─────────────────────────────────
LOOKBACK          = 15           # 過去 4 日
AHEAD             = 10          # 未来 10 日
WAIT_SEC          = 1
DEBUG             = True
DEBUG_SOU         = True
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

# ───────── キーワード ────────────────────────────────────
KEYWORDS = [
    "消費者問題調査会",
    "税制調査会",
    "知的財産戦略調査会",
]

# ───────── 正規化 & ヒット判定 ─────────────────────────
norm = lambda s: re.sub(r"\s+", "", s).lower()
def kw_hit(text: str) -> bool:
    t = norm(text)
    for k in KEYWORDS:
        if k.lower() in t:
            return True
    return False

# ───────── 日付ユーティリティ ─────────────────────────
JST   = timezone(timedelta(hours=9))
# 当日を午前0時に揃え
today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
# 過去 LOOKBACK 日 ～ 当日 ～ 未来 AHEAD 日
DATES = [today - timedelta(days=delta) for delta in range(-AHEAD, LOOKBACK + 1)]

EXCLUDE_LDP = re.compile(r"^記者会見$")      # 除外ワード

# デバッグ出力用
dbg  = lambda *m: print(*m, file=sys.stderr, flush=True) if DEBUG else None
sdbg = lambda *m: print("[SOU]", *m, file=sys.stderr, flush=True) if DEBUG_SOU else None


def better(record_new, record_old):
    """どちらを残すか判定（本文がタイトルと同じなら劣る）"""
    body_n, body_o = record_new["body"], record_old["body"]
    ttl = record_new["title"]
    score_n = len(body_n) if body_n and body_n != ttl else 0
    score_o = len(body_o) if body_o and body_o != ttl else 0
    return record_new if score_n > score_o else record_old


def scrape_ldp():
    # key=(日付, タイトル) で最良レコードを保持
    best = {}
    with sync_playwright() as p:
        ctx = (p.chromium
               .launch(headless=True,
                       args=["--disable-blink-features=AutomationControlled"])
               .new_context(user_agent=UA))
        page = ctx.new_page()
        for d in DATES:
            url = f"https://www.jimin.jp/activity/?day={d.year}.{d.month}.{d.day}"
            #dbg("[LDP] goto", url)
            try:
                page.goto(url, wait_until="networkidle", timeout=25000)
            except Exception:
                continue
            soup = BeautifulSoup(page.content(), "html.parser")
            for tag in soup.find_all(("dt","h1","h2","h3","h4","li")):
                ttl = tag.get_text(" ", strip=True)
                if not ttl or EXCLUDE_LDP.match(ttl):
                    continue
                if not kw_hit(ttl):
                    continue
                sib = tag.find_next_sibling() or tag
                body = sib.get_text(" ", strip=True)
                if body.startswith("今日の 自民党"):
                    body = ""
                rec = {
                    "date": f"{d.month}月{d.day}日",
                    "title": ttl,
                    "body": body.replace("Google Calenderに予定を追加", "").strip()
                }
                key = (rec["date"], rec["title"])
                best[key] = better(rec, best[key]) if key in best else rec
                #dbg(" 🔹LDP-HIT", ttl[:60])
            time.sleep(WAIT_SEC)
    return list(best.values())


def main():
    ldp = scrape_ldp()
    print(f"\n===== {today.strftime('%-m月%-d日')} データ取得開始 =====\n")
    print("【自由民主党】")
    if ldp:
        def dt_key(r):
            m, d = map(int, r["date"].rstrip("日").split("月"))
            return (m, d)
        for r in sorted(ldp, key=dt_key):
            print(f"○{r['date']}　{r['title']}")
            if r['body'] and r['body'] != r['title']:
                print(f"　{r['body']}\n")
            else:
                print()
    else:
        print("該当データなし\n")

if __name__ == "__main__":
    main()
