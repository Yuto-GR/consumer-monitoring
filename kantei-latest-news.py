#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re

def fetch_news(keywords):
    url = 'https://www.kantei.go.jp/jp/news/index.html'
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')

    results = []

    # 元々の <dl class="newsList"> 構造で探す
    dl = soup.find('dl', class_='newsList')
    if dl:
        for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
            date_text = dt.get_text(strip=True)
            a = dd.find('a')
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a['href']
            link = href if href.startswith('http') else f'https://www.kantei.go.jp{href}'
            for kw in keywords:
                if kw.lower() in title.lower():
                    results.append((date_text, title, link))
                    break
        return results

    # フォールバック：ページ内の「更新日：」テキストからたどる
    for text_node in soup.find_all(string=re.compile(r'更新日：')):
        # テキストから日付部分を抽出
        m = re.search(r'更新日：\s*([^\s<]+)', text_node)
        if not m:
            continue
        date_text = m.group(1).strip()  # 例: '令和7年6月27日'

        # 日付テキストの親要素から次の <a> を探す
        parent = text_node.parent
        a = parent.find_next('a')
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get('href', '')
        if not href:
            continue
        link = href if href.startswith('http') else f'https://www.kantei.go.jp{href}'

        # キーワードフィルタ
        for kw in keywords:
            if kw.lower() in title.lower():
                results.append((date_text, title, link))
                break

    return results

if __name__ == '__main__':
    keywords = [
        # 英語キーワード
        "IP", "foreign EC", "Consumer protection", "Product safety",
        "Customs", "de minimus", "Fair competition", "Digital platforms",
        "Child safety", "Fashion", "textile", "Uniqlo", "Fast Fashion",
        "Sustainability",
        # 日本語キーワード
        "知的財産", "模倣品", "消費者問題", "製品安全", "ダークパターン",
        "ダークパターン対策協会", "デジタルプラットフォーム", "オンラインモール",
        "ファッション", "繊維", "子供の安全", "ユニクロ", "ファーストリテイリング",
        "公正取引", "競争", "関税", "少額輸入貨物", "消費税免除"
    ]

    matches = fetch_news(keywords)
    print("【首相官邸】")
    if matches:
        for date, title, link in matches:
            print(f"○{date} 「{title}」")
            print(f"　{link}\n")
    else:
        print("指定したキーワードを含む新着情報は見つかりませんでした。\n")
