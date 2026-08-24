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
| T-102 | F-01 | 【validation】ホームズ判定の解消 | 全 work の holmes フラグが本文実測 evidence 付きで確定、needs_review 残 0 |
| T-103 | F-02 | 【validation】provenance | 全取得ファイルに取得元 URL・取得日が記録されている |
