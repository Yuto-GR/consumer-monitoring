#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gov_policy_news_scraper.py  rev-2.5  (2025-06-28)

■ 指定キーワードで Google News RSS を検索し、
  省庁・自治体が関与する各種政策・消費者保護関連ニュースを抽出。
  ソースが指定リスト外、または4日より古い記事を除外。
  タイトル・本文にキーワードの実在をチェック。
"""

# ───────── Imports ──────────────────────────────────────────
import re, sys, html, time, hashlib, requests, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# ───────── 検索キーワード ────────────────────────────────
KEYWORDS = [
    # 知的財産・模倣品
    "知的財産", "模倣品", "著作権侵害", "商標権侵害", "IP claim", "クレーム",
    # 消費者保護・製品安全・ダークパターン
    "消費者問題", "製品安全", "product safety", "ダークパターン", "一般社団法人ダークパターン対策協会",
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

# ───────── フィルタ対象ニュースソース ────────────────────
FILTER_SOURCES = {
    "日経新聞", "共同", "時事", "朝日新聞", "読売新聞", "毎日新聞", "産経新聞",
    "ブルームバーグ", "東京新聞", "中日新聞", "ITmedia", "impress", "BBC", "CNN"
}
# 地方紙：末尾が「新聞」で主要紙リストに含まれないもの
def is_local_paper(source_name: str) -> bool:
    return source_name.endswith("新聞") and source_name not in {
        "日経新聞", "朝日新聞", "読売新聞", "毎日新聞", "産経新聞", "東京新聞", "中日新聞"
    }

# ───────── 行政主体フィルタ ───────────────────────────
MINISTRIES = [
    "総務省","経済産業省","デジタル庁","文部科学省","経産省","厚生労働省",
    "農林水産省","国土交通省","財務省","金融庁","環境省","外務省","防衛省",
    "内閣府","内閣官房","警察庁","消防庁","復興庁","公正取引委員会","公取委",
    "国交省","厚労省","農水省","デジ庁","文科省"
]
PREF_SUFFIX = ("県","府","都","市","町","村")

# ───────── 検索設定 ────────────────────────────────────
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36")
JST = timezone(timedelta(hours=9))
SINCE_DAYS = 4
RSS_URL = "https://news.google.com/rss/search?hl=ja&gl=JP&ceid=JP:ja&q={}%20when:4d"

# ───────── ユーティリティ ──────────────────────────────
def is_gov_related(text: str) -> bool:
    if any(w in text for w in MINISTRIES):
        return True
    if re.search(r"(政府|内閣|自治体|国が|国は)", text):
        return True
    for suf in PREF_SUFFIX:
        if re.search(rf"[^\w]{{1,4}}{suf}", text):
            return True
    return False


def strip_html(raw: str) -> str:
    return BeautifulSoup(html.unescape(raw), "html.parser").get_text(" ", strip=True)

# ───────── RSS 取得 & 解析 ────────────────────────────
def fetch_hits(keyword: str):
    url     = RSS_URL.format(quote_plus(keyword))
    headers = {"User-Agent": UA}
    xml_data = requests.get(url, headers=headers, timeout=30).content

    root = ET.fromstring(xml_data)
    for item in root.iterfind(".//item"):
        raw_title = strip_html(item.findtext("title", default=""))
        descr     = strip_html(item.findtext("description", default=""))

        link        = item.findtext("link", default="")
        source_elem = item.find("source")
        source_name = source_elem.text if source_elem is not None else ""

        if not (source_name in FILTER_SOURCES or is_local_paper(source_name)):
            continue

        low_kw  = keyword.lower()
        low_txt = (raw_title + descr).lower()
        if low_kw not in low_txt:
            continue

        title = raw_title
        if "印刷画面" in raw_title:
            try:
                page = requests.get(link, headers=headers, timeout=30).text
                soup2 = BeautifulSoup(page, "html.parser")
                meta_og = soup2.find("meta", property="og:title")
                if meta_og and meta_og.get("content"):
                    title = meta_og["content"]
                else:
                    h1 = soup2.find("h1")
                    title = h1.get_text(strip=True) if h1 else raw_title
            except Exception:
                title = raw_title.replace("印刷画面", "").strip()
        else:
            if source_name:
                title = re.sub(rf"\s*-\s*{re.escape(source_name)}$", "", title)
            title = title.replace("印刷画面", "").strip()

        try:
            dt = parsedate_to_datetime(item.findtext("pubDate", ""))
            dt = dt.astimezone(JST)
        except Exception:
            continue
        if dt < datetime.now(JST) - timedelta(days=SINCE_DAYS):
            continue

        yield {
            "dt":     dt,
            "date":   f"{dt.month}月{dt.day}日",
            "source": source_name,
            "title":  title,
            "url":    link
        }

# ───────── メイン ──────────────────────────────────────
def main():
    news, seen = [], set()
    for kw in KEYWORDS:
        try:
            for hit in fetch_hits(kw):
                uid = hashlib.md5(hit["url"].encode()).hexdigest()
                if uid in seen:
                    continue
                seen.add(uid)
                news.append(hit)
        except Exception as e:
            print(f"[WARN] {kw}: {e}", file=sys.stderr)
        time.sleep(0.6)

    news.sort(key=lambda x: x["dt"])

    print("【ニュース】")
    if not news:
        print("該当記事なし")
        return
    for n in news:
        print(f"○{n['date']} {n['title']} {n['source']}  ")
        print(f"  {n['url']}\n")

if __name__ == "__main__":
    main()
