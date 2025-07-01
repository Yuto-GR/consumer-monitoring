#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import datetime
import re

# 新着情報一覧ページ
BASE_URL = "https://www.cao.go.jp/consumer/shinchaku/index.html"

def fetch_shinchaku_last7_days():
    # DEBUG: 今日と７日前を表示
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    #print(f"[DEBUG] today = {today}, week_ago = {week_ago}")

    # ページ取得・パース
    resp = requests.get(BASE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    #print("[DEBUG] Page fetched and parsed")

    entries = []

    # 年月見出しを検出
    header_tags = soup.find_all(
        lambda tag: tag.name in ["h2", "h3"]
        and re.match(r"\d{4}年\d{1,2}月$", tag.get_text(strip=True))
    )
    #print(f"[DEBUG] Found {len(header_tags)} header_tags: {[tag.get_text(strip=True) for tag in header_tags]}")

    for header in header_tags:
        ym_text = header.get_text(strip=True)
        year, month = map(int, re.match(r"(\d{4})年(\d{1,2})月", ym_text).groups())
        #print(f"[DEBUG] Processing section: {year}年{month}月")

        # この見出しの直後にある <dl> を取得
        dl = header.find_next_sibling("dl")
        if not dl:
            #print("[DEBUG] No <dl> found after header, skipping")
            continue

        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        #print(f"[DEBUG] Found {len(dts)} dt/dd pairs")

        for dt, dd in zip(dts, dds):
            date_text = dt.get_text(strip=True)
            #print(f"[DEBUG] dt text: '{date_text}'")

            # 「YYYY年M月D日」をパース
            m_date = re.match(rf"{year}年{month}月(\d{{1,2}})日", date_text)
            if not m_date:
                #print("[DEBUG] dt text does not match date pattern, skipping")
                continue

            day = int(m_date.group(1))
            date_obj = datetime.date(year, month, day)
            #print(f"[DEBUG] Parsed date: {date_obj}")

            # 範囲チェック
            if not (week_ago <= date_obj <= today):
                #print(f"[DEBUG] {date_obj} out of range, skipping")
                continue

            # <dd> 内のリンクを取得
            a = dd.find("a", href=True)
            if not a:
                #print("[DEBUG] No <a> in dd, skipping")
                continue

            href = a["href"].strip()
            #print(f"[DEBUG] Found link href: '{href}'")

            # ページ内リンク除外
            if href.startswith("#"):
                #print("[DEBUG] href starts with '#', skipping")
                continue

            title = a.get_text(strip=True)
            url = urljoin(BASE_URL, href)
            #print(f"[DEBUG] Title: '{title}', URL: {url}")

            entries.append((date_obj, title, url))
            #print(f"[DEBUG] Appended entry for {date_obj}")

    #print(f"[DEBUG] Total entries collected: {len(entries)}")

    # 出力
    print("【消費者委員会】")
    if not entries:
        print("該当データなし\n")
    else:
        for date_obj, title, url in sorted(entries, key=lambda x: x[0], reverse=True):
            print(f"○{date_obj.month}月{date_obj.day}日\t{title}")
            print(f"　{url}\n")

if __name__ == "__main__":
    fetch_shinchaku_last7_days()
