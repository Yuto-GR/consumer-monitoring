#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tokyo_seiji_monitoring.py  rev-3.0  (2026-08-07)

■ 小池百合子・東京都知事、東京都議会、自民党東京都連（都連）、
  都議会自民党の動向を監視するレポートを生成する。
"""

# ───────── Imports ──────────────────────────────────────────
import re, sys, html, time, hashlib, requests, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

# ───────── 検索キーワード ────────────────────────────────
KEYWORDS = [
    "小池百合子", "小池知事", "小池都知事", "東京都知事", "都知事",
    "東京都議会", "都議会",
    "自民党東京都連", "東京都連", "都議会自民党",
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

# ───────── 検索設定 ────────────────────────────────────
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36")
JST = timezone(timedelta(hours=9))
SINCE_DAYS = 4
RSS_URL = "https://news.google.com/rss/search?hl=ja&gl=JP&ceid=JP:ja&q={}%20when:4d"

# ───────── ユーティリティ ──────────────────────────────
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
        print(f"○{n['date']} [{n['title']}]({n['url']}) {n['source']}\n")

if __name__ == "__main__":
    main()

#-----------------東京都知事（小池百合子）ーーーーーーーーーーーーーーーーー
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tokyo_governor_watcher.py  rev-1.0  (2026-08-07)

■ 東京都公式サイトのRSS（報道発表・トピックス等）を取得し、
  知事（小池百合子）関連のキーワードにヒットする記事のみ抽出。
"""

RSS_URL       = "https://www.metro.tokyo.lg.jp/rss/index.rdf"
LOOKBACK_DAYS = 4
JST           = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36")

KEYWORDS = ["知事", "小池", "記者会見"]

def local_tag(elem) -> str:
    return elem.tag.rsplit("}", 1)[-1]

def find_child(elem, name):
    for child in elem:
        if local_tag(child) == name:
            return child
    return None

def parse_date(text: str):
    if not text:
        return None
    try:
        return parsedate_to_datetime(text)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(text.strip())
    except Exception:
        return None

def scrape_governor_rss():
    resp = requests.get(RSS_URL, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    since = datetime.now(JST) - timedelta(days=LOOKBACK_DAYS)
    results = []
    for item in root.iter():
        if local_tag(item) != "item":
            continue
        title_el = find_child(item, "title")
        link_el  = find_child(item, "link")
        date_el  = find_child(item, "date") or find_child(item, "pubDate")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link  = (link_el.text or "").strip()
        if not title or not link:
            continue

        dt = parse_date(date_el.text if date_el is not None else "")
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        dt = dt.astimezone(JST)
        if dt < since:
            continue

        if not any(kw in title for kw in KEYWORDS):
            continue

        results.append({"dt": dt, "date": f"{dt.month}月{dt.day}日", "title": title, "url": link})

    seen, out = set(), []
    for r in sorted(results, key=lambda x: x["dt"], reverse=True):
        key = (r["date"], r["title"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def main():
    print("【東京都知事（小池百合子）】")
    try:
        recs = scrape_governor_rss()
    except Exception as e:
        print(f"[WARN] 取得失敗: {e}", file=sys.stderr)
        print("該当データなし\n")
        return
    if not recs:
        print("該当データなし\n")
        return
    for r in recs:
        print(f"○{r['date']}　[{r['title']}]({r['url']})\n")

if __name__ == "__main__":
    main()

#-----------------東京都議会ーーーーーーーーーーーーーーーーー
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tokyo_gikai_watcher.py  rev-1.0  (2026-08-07)

■ 東京都議会サイトの「会議の予定」ページを巡回し、
   過去4日＋当日＋今後14日の日程を抽出して表示。
"""

GIKAI_URL     = "https://www.gikai.metro.tokyo.lg.jp/schedule/"
GIKAI_LOOKBACK = 4
GIKAI_AHEAD    = 14
DATE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")

def scrape_gikai_schedule():
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    win_from = today - timedelta(days=GIKAI_LOOKBACK)
    win_to   = today + timedelta(days=GIKAI_AHEAD)

    resp = requests.get(GIKAI_URL, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    results = []
    for row in soup.find_all(("tr", "li", "dt")):
        text = row.get_text(" ", strip=True)
        m = DATE_RE.search(text)
        if not m:
            continue
        month, day = map(int, m.groups())
        for year in (today.year, today.year - 1, today.year + 1):
            try:
                date_obj = datetime(year, month, day, tzinfo=JST)
            except ValueError:
                continue
            if win_from <= date_obj <= win_to:
                break
        else:
            continue

        a = row.find("a", href=True)
        link = urljoin(GIKAI_URL, a["href"]) if a else GIKAI_URL
        title = text if len(text) < 120 else text[:120] + "…"

        results.append({"dt": date_obj, "date": f"{month}月{day}日", "title": title, "url": link})

    seen, out = set(), []
    for r in sorted(results, key=lambda x: x["dt"]):
        key = (r["date"], r["title"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def main():
    print("【東京都議会】")
    try:
        recs = scrape_gikai_schedule()
    except Exception as e:
        print(f"[WARN] 取得失敗: {e}", file=sys.stderr)
        print("該当データなし\n")
        return
    if not recs:
        print("該当データなし\n")
        return
    for r in recs:
        print(f"○{r['date']}　[{r['title']}]({r['url']})\n")

if __name__ == "__main__":
    main()

#-----------------自民党東京都連ーーーーーーーーーーーーーーーーー
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tokyo_jimin_watcher.py  rev-1.0  (2026-08-07)

■ 自民党東京都支部連合会（都連）サイトを巡回し、
   投稿URL（/YYYY/MM/DD/...形式）から直近の記事のみ抽出。
"""

TOKYO_JIMIN_URL   = "https://www.tokyo-jimin.jp/"
TOKYO_JIMIN_DAYS  = 7
POST_URL_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")

def scrape_tokyo_jimin():
    since = datetime.now(JST) - timedelta(days=TOKYO_JIMIN_DAYS)

    resp = requests.get(TOKYO_JIMIN_URL, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    seen, results = set(), []
    for a in soup.find_all("a", href=True):
        href = urljoin(TOKYO_JIMIN_URL, a["href"])
        m = POST_URL_RE.search(href)
        if not m:
            continue
        year, month, day = map(int, m.groups())
        try:
            dt = datetime(year, month, day, tzinfo=JST)
        except ValueError:
            continue
        if dt < since:
            continue

        title = a.get_text(" ", strip=True)
        if not title or href in seen:
            continue
        seen.add(href)
        results.append({"dt": dt, "date": f"{month}月{day}日", "title": title, "url": href})

    results.sort(key=lambda x: x["dt"], reverse=True)
    return results

def main():
    print("【自民党東京都連（TOKYO自民党）】")
    try:
        recs = scrape_tokyo_jimin()
    except Exception as e:
        print(f"[WARN] 取得失敗: {e}", file=sys.stderr)
        print("該当データなし\n")
        return
    if not recs:
        print("該当データなし\n")
        return
    for r in recs:
        print(f"○{r['date']}　[{r['title']}]({r['url']})\n")

if __name__ == "__main__":
    main()

#-----------------都議会自民党ーーーーーーーーーーーーーーーーー
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
togikai_jimin_watcher.py  rev-1.0  (2026-08-07)

■ 都議会自民党サイトを巡回し、日付表記を含む新着項目のみ抽出。
"""

TOGIKAI_JIMIN_URL  = "https://www.togikai-jimin.jimusho.jp/"
TOGIKAI_JIMIN_DAYS = 14
TOGIKAI_DATE_RE = re.compile(r"(\d{4})[./年](\d{1,2})[./月](\d{1,2})")

def scrape_togikai_jimin():
    since = datetime.now(JST) - timedelta(days=TOGIKAI_JIMIN_DAYS)

    resp = requests.get(TOGIKAI_JIMIN_URL, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    seen, results = set(), []
    for tag in soup.find_all(("li", "tr", "p", "dt")):
        text = tag.get_text(" ", strip=True)
        m = TOGIKAI_DATE_RE.search(text)
        if not m:
            continue
        year, month, day = map(int, m.groups())
        try:
            dt = datetime(year, month, day, tzinfo=JST)
        except ValueError:
            continue
        if dt < since:
            continue

        a = tag.find("a", href=True)
        if not a:
            continue
        href = urljoin(TOGIKAI_JIMIN_URL, a["href"])
        if href in seen:
            continue
        seen.add(href)

        title = a.get_text(" ", strip=True) or text
        results.append({"dt": dt, "date": f"{month}月{day}日", "title": title, "url": href})

    results.sort(key=lambda x: x["dt"], reverse=True)
    return results

def main():
    print("【都議会自民党】")
    try:
        recs = scrape_togikai_jimin()
    except Exception as e:
        print(f"[WARN] 取得失敗: {e}", file=sys.stderr)
        print("該当データなし\n")
        return
    if not recs:
        print("該当データなし\n")
        return
    for r in recs:
        print(f"○{r['date']}　[{r['title']}]({r['url']})\n")

if __name__ == "__main__":
    main()
