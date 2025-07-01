#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
import unicodedata
import re
from datetime import date, timedelta

# 取得対象期間（日数）
DAYS_RANGE = 15

def normalize(text: str) -> str:
    """全角→半角、前後の空白を削除"""
    return unicodedata.normalize('NFKC', text).strip()

def fetch_with_playwright(keywords):
    url = 'https://www.kantei.go.jp/jp/news/index.html'
    today = date.today()
    threshold = today - timedelta(days=DAYS_RANGE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        # まずはネットワークアイドルを待つ
        page.wait_for_load_state('networkidle')
        # さらに少し余裕を持たせて
        page.wait_for_timeout(1000)

        # できれば selector も待つ
        try:
            page.wait_for_selector('dl.newsList', timeout=10000)
        except TimeoutError:
            print("[WARN] dl.newsList が見つからなかったため、先に進みます。")

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one('dl.newsList')
    if not container:
        print("[ERROR] ニュースリスト（dl.newsList）が見つかりませんでした。")
        return []

    results = []
    for dt, dd in zip(container.find_all('dt'), container.find_all('dd')):
        raw_date = normalize(dt.get_text())
        m = re.search(r'(\d+)月\s*(\d+)日', raw_date)
        if not m:
            continue
        month, day = map(int, m.groups())
        article_date = date(today.year, month, day)
        if not (threshold <= article_date <= today):
            continue

        a = dd.find('a')
        if not a or not a.get('href'):
            continue
        title = normalize(a.get_text())
        href  = a['href']
        link  = href if href.startswith('http') else f'https://www.kantei.go.jp{href}'

        for kw in keywords:
            if kw.lower() in title.lower():
                date_str = f"{month}月{day}日"
                results.append((date_str, title, link))
                break

    return results

if __name__ == '__main__':
    keywords = [
        "知的財産", "消費者問題", "公正取引", "ユニクロ",
        "IP", "Product safety", "Fair competition",
    ]

    matches = fetch_with_playwright(keywords)
    if matches:
        print(f"◎ 過去{DAYS_RANGE}日間の記事件数: {len(matches)} 件")
        for date_str, title, link in matches:
            print(f"○{date_str} 「{title}」")
            print(f"　{link}")
    else:
        print(f"過去{DAYS_RANGE}日間で指定キーワードを含む記事は見つかりませんでした。")
