


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cao_press_watcher_rss_etree.py  rev-1.6  (2025-06-19)

■ 内閣府「報道発表新着情報」RSSフィードを標準ライブラリだけで取得・解析し、
  過去 4 日間に掲載された “DX／デジタル関連＋食品・環境” の
  リリースを抽出して一覧表示します。

・requests で RSS(XML) を取得
・xml.etree.ElementTree でパース
・email.utils.parsedate_to_datetime + datetime.fromisoformat で日付変換
・デバッグログは標準エラー出力
依存:
    pip install requests
"""

import re
import sys
import unicodedata
import requests

from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime

# ───────── Settings ──────────────────────────────────────
RSS_URL       = "https://www.cao.go.jp/rss/news.rdf"
LOOKBACK_DAYS = 4
dbg = lambda *m: print("[DBG]", *m, file=sys.stderr, flush=True)

# ───────── Date window ───────────────────────────────────
JST      = timezone(timedelta(hours=9))
NOW      = datetime.now(JST)
TODAY    = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
WIN_FROM = TODAY - timedelta(days=LOOKBACK_DAYS)

# ───────── Keywords ─────────────────────────────────────
KEYWORDS = [
    # 知的財産・模倣品
    "知的財産", "模倣品", "著作権侵害", "商標権侵害", "IP claim", "クレーム",
    # 消費者保護・製品安全・ダークパターン
    "消費者問題", "製品安全", "product safety", "ダークパターン", "一般社団法人ダークパターン対策協会","食品"
    # 関税・少額輸入貨物の免税
    "関税", "少額輸入貨物", "de minimis", "customs" 
    # 公正取引・競争
    ,"公正取引", "競争", "fair competition"
    # デジタルプラットフォーム・オンラインモール
    ,"デジタルプラットフォーム", "オンラインモール", "digital platform"
    # 子供のインターネット安全
    ,"子供の安全", "child safety"
    # ファッション・繊維・ユニクロ・ファーストリテイリング
    ,"ファッション", "繊維", "fashion textile", "fast fashion", "ユニクロ", "ファーストリテイリング"
    # 持続可能性
    ,"サステナビリティ", "持続可能", "sustainability"
]
SHORT_ASCII = {"ai", "it", "dx"}
norm = lambda s: unicodedata.normalize("NFKC", s).lower()

def kw_hit(text: str) -> bool:
    t = norm(text)
    for kw in KEYWORDS:
        k = norm(kw)
        if k in SHORT_ASCII:
            if re.search(rf"(?:^|[^a-z0-9]){k}(?:[^a-z0-9]|$)", t):
                return True
        elif k in t:
            return True
    return False

# ───────── Fetch RSS ─────────────────────────────────────
def fetch_rss(url: str) -> str:
    dbg(f"[REQ] Fetching RSS {url}")
    resp = requests.get(url, timeout=(10, 30))
    resp.raise_for_status()
    dbg("     length:", len(resp.content))
    return resp.text

# ───────── Parse and filter ─────────────────────────────
def scrape_cao_rss():
    xml = fetch_rss(RSS_URL)
    root = ET.fromstring(xml)

    # debug root and namespaces
    dbg("root.tag =", root.tag)
    dbg("children tags:", [child.tag for child in root[:3]])

    # define namespaces
    ns = {
        'rss': 'http://purl.org/rss/1.0/',
        'dc':  'http://purl.org/dc/elements/1.1/'
    }

    # find all <rss:item>
    items = root.findall('rss:item', ns)
    dbg("namespaced <item> count:", len(items))

    results = []
    for itm in items:
        title_el = itm.find('rss:title', ns)
        link_el  = itm.find('rss:link', ns)
        date_el  = itm.find('dc:date', ns)
        if title_el is None or link_el is None or date_el is None:
            dbg(" skip (missing element)")
            continue

        title = title_el.text.strip()
        link  = link_el.text.strip()
        dbg(" candidate title:", title[:40])

        date_text = date_el.text.strip()
        # parse RFC822 or ISO8601
        dt = None
        try:
            dt = parsedate_to_datetime(date_text)
        except Exception:
            try:
                dt = datetime.fromisoformat(date_text)
            except Exception as e:
                dbg("    date parse failed:", e, date_text)
                continue
        # ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        dt_jst = dt.astimezone(JST)
        dt0    = dt_jst.replace(hour=0, minute=0, second=0, microsecond=0)

        # date window
        if not (WIN_FROM <= dt0 <= TODAY):
            dbg("    out of window:", dt0.date())
            continue

        # keyword filter
        if not kw_hit(title):
            dbg("    no keyword match")
            continue

        dbg("  HIT:", dt0.date(), title[:40])
        results.append({
            'dt':   dt0,
            'date': dt0.strftime('%-m月%-d日'),
            'title': title,
            'url':   link
        })

    # dedupe & sort desc
    seen, out = set(), []
    for r in sorted(results, key=lambda x: x['dt'], reverse=True):
        key = (r['date'], r['title'])
        if key in seen:
            dbg(" duplicate skip:", key)
            continue
        seen.add(key)
        out.append(r)

    dbg("total hits:", len(out))
    return out

# ───────── CLI ─────────────────────────────────────────
def main():
    recs = scrape_cao_rss()
    print("【内閣府】")
    if not recs:
        print("該当データなし")
        return
    for r in recs:
        print(f"○{r['date']}　{r['title']}")
        print(f"　{r['url']}\n")

if __name__ == "__main__":
    main()


