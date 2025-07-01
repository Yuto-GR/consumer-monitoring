#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import datetime
import re

# 対象ページ
BASE_URL = "https://www.cao.go.jp/zei-cho/gijiroku/digital-noukan/index.html"

def fetch_events_last30_days():
    # DEBUG: 今日と30日前の日付
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=30)
    #print(f"[DEBUG] today = {today}, start_date = {start_date}")

    # ページ取得・パース
    resp = requests.get(BASE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    #print("[DEBUG] Page fetched and parsed")

    # テキストを改行で取得し、空行を除去
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    #print(f"[DEBUG] Total lines extracted: {len(lines)}")

    events = []
    year = None

    for idx, line in enumerate(lines):
        #print(f"[DEBUG] Processing line {idx}: '{line}'")
        # ページ先頭へのリンクで終了
        if line == "このページの先頭へ":
            #print("[DEBUG] Reached sentinel, breaking")
            break

        # 年の行（例: "2025年"）
        m_year = re.match(r"^(\d{4})年$", line)
        if m_year:
            year = int(m_year.group(1))
            #print(f"[DEBUG] Set year = {year}")
            continue

        # 日付行（例: "6月11日"）
        m_date = re.match(r"^(\d{1,2})月(\d{1,2})日$", line)
        if m_date and year:
            month, day = map(int, m_date.groups())
            date_obj = datetime.date(year, month, day)
            #print(f"[DEBUG] Found date: {date_obj}")

            # 次の２行で「第n回」「・テーマ」を期待
            iter_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            theme_line = lines[idx + 2] if idx + 2 < len(lines) else ""
            #print(f"[DEBUG] Next lines: iter_line='{iter_line}', theme_line='{theme_line}'")

            m_iter = re.match(r"^第(\d{1,2})回$", iter_line)
            m_theme = re.match(r"^・(.+)$", theme_line)
            if m_iter and m_theme:
                num = int(m_iter.group(1))
                theme = m_theme.group(1).strip()
                #print(f"[DEBUG] Parsed iteration: {num}, theme: '{theme}'")

                # 範囲内かチェック
                if start_date <= date_obj <= today:
                    events.append((date_obj, num, theme))
                    #print("[DEBUG] Appended event")
                #else:
                    #print("[DEBUG] Date out of range, skipping")
            #else:
                #print("[DEBUG] Iteration or theme pattern not matched, skipping")

    #print(f"[DEBUG] Total events collected: {len(events)}")

    # 出力
    if not events:
        print("該当データなし\n")
    else:
        for date_obj, num, theme in sorted(events, key=lambda x: x[0], reverse=True):
            print(f"○{date_obj.month}月{date_obj.day}日　第{num}回　{theme}\n")

if __name__ == "__main__":
    fetch_events_last30_days()
