# 東京都政・IR政策モニタリング

小池百合子・東京都知事、東京都議会、自民党東京都連（都連）、都議会自民党の動向、および東京都における統合型リゾート（IR）推進の政策動向を監視するレポートを自動生成する。

## 実行スケジュール

- GitHub Actions（`.github/workflows/consumer-monitoring.yml`）により **毎日 JST 9:00 / 16:00** に自動実行
- `workflow_dispatch` により手動実行も可能
- 実行結果は `docs/index.md` にコミットされ、GitHub Pages（`https://yuto-gr.github.io/consumer-monitoring/`）で閲覧できる

## レポート構成

実行本体は `consumer-monitoring.py`。5つのセクションを順に出力する。

### 1. 【ニュース】

Google News RSS を日本語版・英語版それぞれでキーワード検索する。過去4日以内の記事のみ抽出。

**日本語キーワード**
- 小池百合子、小池知事、小池都知事、東京都知事、都知事
- 東京都議会、都議会
- 自民党東京都連、東京都連、都議会自民党
- IR（統合型リゾート）関連：統合型リゾート、IR誘致、IR推進、特定複合観光施設区域、IR整備法、東京IR、カジノ解禁

**英語キーワード（海外メディア向け）**
- Yuriko Koike、Tokyo Governor、Tokyo Metropolitan Assembly
- Tokyo LDP、Liberal Democratic Party Tokyo
- Tokyo integrated resort、Tokyo casino、Japan IR Tokyo

**対象ニュースソース（日本語）**
日経新聞、共同、時事、朝日新聞、読売新聞、毎日新聞、産経新聞、ブルームバーグ、ロイター、東京新聞、中日新聞、BBC、CNN、および「〇〇新聞」で終わる地方紙全般

**対象ニュースソース（英語）**
Reuters、Bloomberg、BBC、CNN、The Japan Times、Nikkei Asia、Kyodo News、Associated Press（AP News）、The Guardian、Financial Times

### 2. 【東京都知事（小池百合子）】

東京都公式サイトのRSS（`https://www.metro.tokyo.lg.jp/rss/index.rdf`）を取得し、タイトルに「知事」「小池」「記者会見」「IR」「統合型リゾート」「カジノ」のいずれかを含む記事のみ抽出。過去4日以内。

### 3. 【東京都議会】

東京都議会サイトの会議予定ページ（`https://www.gikai.metro.tokyo.lg.jp/schedule/`）を巡回し、過去4日〜今後14日の日程を抽出。

### 4. 【自民党東京都連（TOKYO自民党）】

自民党東京都支部連合会サイト（`https://www.tokyo-jimin.jp/`）を巡回し、過去7日以内に投稿された記事を抽出。

### 5. 【都議会自民党】

都議会自民党サイト（`https://www.togikai-jimin.jimusho.jp/`）を巡回し、過去14日以内の日付表記を含む新着項目を抽出。

## 補足

- 各記事の見出しはクリック可能なリンクとして表示され、生のURLは表示しない
- レポート冒頭に生成日時（JST）を表示
- キーワード・ソースの追加/変更が必要な場合は `consumer-monitoring.py` 内の該当セクションを編集する
