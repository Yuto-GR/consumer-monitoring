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

#-----------------自民党ーーーーーーーーーーーーーーーーー
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
    #print(f"\n===== {today.strftime('%-m月%-d日')} データ取得開始 =====\n")
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
#-------経済産業省ーーーーーー
print("!!!!!!!!!!!!自分で調べてください！！！！！！！")

#------------首相官邸ーーーーーーーーーー
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

#--------内閣府==========

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
#dbg = lambda *m: print("[DBG]", *m, file=sys.stderr, flush=True)

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
    #dbg(f"[REQ] Fetching RSS {url}")
    resp = requests.get(url, timeout=(10, 30))
    resp.raise_for_status()
    #dbg("     length:", len(resp.content))
    return resp.text

# ───────── Parse and filter ─────────────────────────────
def scrape_cao_rss():
    xml = fetch_rss(RSS_URL)
    root = ET.fromstring(xml)

    # debug root and namespaces
    #dbg("root.tag =", root.tag)
    #dbg("children tags:", [child.tag for child in root[:3]])

    # define namespaces
    ns = {
        'rss': 'http://purl.org/rss/1.0/',
        'dc':  'http://purl.org/dc/elements/1.1/'
    }

    # find all <rss:item>
    items = root.findall('rss:item', ns)
    #dbg("namespaced <item> count:", len(items))

    results = []
    for itm in items:
        title_el = itm.find('rss:title', ns)
        link_el  = itm.find('rss:link', ns)
        date_el  = itm.find('dc:date', ns)
        if title_el is None or link_el is None or date_el is None:
            #dbg(" skip (missing element)")
            continue

        title = title_el.text.strip()
        link  = link_el.text.strip()
        #dbg(" candidate title:", title[:40])

        date_text = date_el.text.strip()
        # parse RFC822 or ISO8601
        dt = None
        try:
            dt = parsedate_to_datetime(date_text)
        except Exception:
            try:
                dt = datetime.fromisoformat(date_text)
            except Exception as e:
                #dbg("    date parse failed:", e, date_text)
                continue
        # ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        dt_jst = dt.astimezone(JST)
        dt0    = dt_jst.replace(hour=0, minute=0, second=0, microsecond=0)

        # date window
        if not (WIN_FROM <= dt0 <= TODAY):
            #dbg("    out of window:", dt0.date())
            continue

        # keyword filter
        if not kw_hit(title):
            #dbg("    no keyword match")
            continue

        #dbg("  HIT:", dt0.date(), title[:40])
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
            #dbg(" duplicate skip:", key)
            continue
        seen.add(key)
        out.append(r)

    #dbg("total hits:", len(out))
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

#-------------消費者安全委員会ーーーーーーーーー
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

#--------------内閣府経済社会ーーーーーーーー
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
    print("【経済社会のデジタル化への対応と納税環境整備に関する専門家会合】")
    if not events:
        print("該当データなし\n")
    else:
        for date_obj, num, theme in sorted(events, key=lambda x: x[0], reverse=True):
            print(f"○{date_obj.month}月{date_obj.day}日　第{num}回　{theme}\n")

if __name__ == "__main__":
    fetch_events_last30_days()

