# TEST_SPEC.md — jikenbo-atlas

<!-- scaffold template v1.12.0 から展開(2026-08-24) -->

## 実行規約

- `pytest -x -q` を stage 3–5 の判定に使用。マーカー: `unit` / `integration` / `validation`
- `validation` は取得済みコーパス(`data/raw/`)を前提とする。未取得環境では skip
- フィクスチャ更新は専用コミット(`test: update fixtures`)で行い、理由をループログに記す

## 期待値の出所(HC-016)

| 出所 | 書き方 |
|---|---|
| SPEC の条項 | 条項 ID を書く |
| 外部権威 | 出典 URL と取得日をフィクスチャの先頭に書く |
| 実測 | 実測日と実測値をコメントに残す |

件数・行数は定数で書かず、**集合の一致・取りこぼしの不在**という不変量で書く。

## オラクルの出所

| フィクスチャ | 出所 | 性格 |
|---|---|---|
| `tests/fixtures/akage_excerpt.txt` | 青空文庫 card8「赤毛連盟」ルビあり zip(https://www.aozora.gr.jp/cards/000009/files/8_ruby_31219.zip、2026-08-24 実測)からの抜粋 | 実データ抜粋。改変禁止 |
| `tests/fixtures/person9.html` | 青空文庫ドイル作家ページ(https://www.aozora.gr.jp/index_pages/person9.html、2026-08-24 取得) | 実データ全文。改変禁止 |
| 往復検査(T-101) | パーサー自身の逆写像。原文が正解であり外部正解不要 | 自己完結オラクル |
| 正典構成(T-201/202) | シャーロック・ホームズ正典の確立した書誌(短編集構成・初出年)。en.wikipedia.org/wiki/Canon_of_Sherlock_Holmes ほか(2026-08-24 参照) | 外部権威の定数 |
| 対応付け(T-204/205) | 取得テキストのヘッダ原題(実測)・本文キーワード(実測) | 実測 |

## ケース一覧

| ID | 対応要求 | ケース | 期待 |
|---|---|---|---|
| T-001 | F-03 | 実抜粋のヘッダ/本文/フッタ分離 | 罫線 2 本目までがヘッダ、`［＃本文終わり］` 以降がフッタ |
| T-002 | F-03 | ルビ自動ベース(漢字連続・カタカナ) | `弁慶格子《シェパド・チェック》`→base=弁慶格子 ほか(実測 2026-08-24) |
| T-003 | F-03 | `｜` 明示ベース | base を正しく取り、再直列化で `｜` が復元される |
| T-004 | F-03 | 入力者注 `［＃…］` | verbatim 保存(挿絵注含む) |
| T-005 | F-04 | 抜粋フィクスチャの往復 | serialize(parse(x)) == x(全文一致) |
| T-006 | F-01 | person9.html の作品リスト抽出 | 公開中 `<ol>` の li と抽出結果が全単射(取りこぼし・重複なし)。各entryに訳者≥1 |
| T-101 | F-04 | 【validation】全取得テキストの往復 | 不一致 0 件(100%) |
| T-201 | F-05 | 正典の構成 | 全 60 件・id 一意・短編 56/長編 4。短編集別件数は外部権威の定数(冒険 12・回想 11・生還 13・最後の挨拶 8=ボール箱含む英国流・事件簿 12。出典: Canon of Sherlock Holmes、2026-08-24 参照) |
| T-202 | F-05 | 発表年の整合 | 各作品の pub_year が短編集の刊行範囲内(冒険 1891–92 / 回想 1892–93 / 生還 1903–04 / 挨拶 1892–1917 / 事件簿 1921–27、長編は各初出年) |
| T-203 | F-05 | 語彙・必須欄 | case_type / region が統制語彙内、必須欄(題・依頼人・動機等)非空、deaths は bool |
| T-204 | F-05 | コーパス対応の全単射 | canon 側の work_id 集合 == aozora_works の {holmes==true ∪ external_host} 集合。1 つの work_id は 1 事件にのみ属す |
| T-205 | F-05 | 対応の証拠 | evidence が header: のものは、引用行が当該ファイル先頭 6 行に実在する(実測の再現)。それ以外は 本文実測: / 題名対応(取得不能) のいずれか |
| T-206 | F-05 | 主訳の選好 | corpus ありの事件の primary_work_id は、大久保訳が存在すればそれを指す |
| T-301 | F-06 | 【validation】本文 JSON の網羅 | web/data/stories/ に holmes==true 全作品の JSON が存在し、余剰がない(集合一致) |
| T-302 | F-06 | 【validation】本文 JSON の可逆性 | 各 story JSON のセグメントから青空記法本文を再構成すると、パーサーの serialize 本文と一致(表示層まで無損失) |
| T-303 | F-07 | 【validation】索引の整合 | index.json の事件数・work 参照が canon/aozora と一致。reading_minutes > 0。stats の合計が全数と一致 |
| T-304 | F-06/07 | web 骨格 | index.html / reader.html が存在し、必須マウント要素とデータパス参照を含む |
| T-401 | F-08 | 座標の全数付与 | 全 60 事件に site(lat/lon/label/approx)がある。approx は bool、label 非空 |
| T-402 | F-08 | 座標境界ゲート | 海外=英国 bbox 外 / ロンドン=大ロンドン bbox 内 / 近郊=チャリング・クロスから 60km 以内 / 地方=英国内かつ 25km 超。bbox・基準点は公知の地理定数(2026-08-24 記載) |
| T-403 | F-08 | 地図ページ骨格 | map.html が存在し Leaflet とデータ参照を含む。index.json の全事件に site が伝搬 |
| T-102 | F-01 | 【validation】ホームズ判定の解消 | 全 work の holmes フラグが本文実測 evidence 付きで確定、needs_review 残 0 |
| T-103 | F-02 | 【validation】provenance | 全取得ファイルに取得元 URL・取得日が記録されている |
