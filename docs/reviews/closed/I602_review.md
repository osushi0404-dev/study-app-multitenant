# I602 レビュー: I590 のレビューの残り（テストの守りの抜け・0027 の戻し方・補助の集約）

## 変更概要
- I590 のレビューの残りを片付けた（テストと手順書だけ）: 配信の見出しを全項目で比べる・移行の判定の相対の読み込みを数える・マイグレーションのテストの補助を 1 か所にまとめる・0027 が止まったときの戻し方を手順書に書く

## 変更点
- `backend/problems/tests/migration_helpers.py`（新規）・`test_I590_review_leftovers.py`・`test_I587_media_migration.py`・`studylogs/tests/test_I492_remove_legacy_study_logs.py`・`docs/runbooks/backend-check.md`

## 影響範囲
- Backend/Frontend/DB/Config: Backend のテストだけ。Frontend・DB・Config なし。手順書 1 本

## テスト結果
- 自動: CI run 44710229604（HEAD 90312b25） で backend 818 passed・frontend 150 passed（3 ファイル 30 件すべて通過）。決定論ゲート 9 行 exit 0
- 手動: Claude の 2 項目とも OK（Human の項目なし）

## 計画との差分
- あり（軽微）: 計画レビューの Info で、手順書の確かめのコマンドを `dbshell -- -c` にした（計画変更記録に記載・方式と範囲は同じ）

## ロールバック
- PR を revert する（テストと手順書だけ）

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 補助の置き場を `backend/problems/tests/migration_helpers.py`、0027 の戻り方の置き場を `docs/runbooks/backend-check.md` の新しい節にした — 前例（`i466_data.py`）と同じ置き方・止まった人が最初に開くマイグレーションの診断の手順書（計画書 9）
- [plan-review] 計画レビュー OK。Info 2 件（確かめのコマンドを `dbshell -- -c` に・0026 の判定と合わせる）を計画書に反映し、Warning 2 件（TC-03 の語を説明文に書かない・SQL の一致は手動テスト No.2）は実装で留意 — 方式・範囲を変えないので再レビューしない
- [implement] 計画どおり実装。手元で 3 ファイル 30 件 passed・TC-03 の 9 行は exit 0 — 正は CI
- [implement] `/simplify`（4 観点）の反映: `app_imports` を「集めてから 1 回だけ絞る」形に戻した・`_subject_columns` の包みを消して `column_names("problems_subject")` を直に呼ぶ（計画書 4-(3) の記載どおり）・`run_migration` の説明の誤解しやすい書き方を直した — 振る舞いは変えない
- [implement] `/simplify` の見送り: `test_I587_media_in_db.py` の見出しの固定の値の確かめを補助に寄せる案（計画の範囲外。固定の値の確かめは辞書と応答が一緒に変わる弱点〔計画 R2〕を補っているので残す）・`Cache-Control` の文字を `MEDIA_CACHE_CONTROL` に置き換える案（計画で残すと決めた行・値そのものを固定する意図）・`load_migrations` をセッションで 1 回にする案（DB の状態に左右され古い状態を読むおそれ）
- [review-gate] コードレビュー OK（CI OK・RISK NO・敵対的レビュー不要）。Low 3 件（F1 は計画 R2 で受け入れ済み・F2 0026 の手順の粒度・F3 補助が制約を即時にしたまま戻さない）は止めない指摘なので直さず retro へ — 台帳の決まり（I197）
- [test-gate] 手動テストの No.1 は、CI の pytest が -q の形で PASSED の文字を出さないので、ファイルごとの `.` の数と全体の passed で判定した — 期待結果（失敗・エラー 0）の趣旨は同じ
- [retro] 台帳の残り: F1・F3（アプリ本体の Low・再現なし）→ #580 に同梱（I492 のレビューの残り。F5 と同じ「テストの守りの範囲」の種類で、`migration_helpers.py` は I492 のテストも使う）・F2（ハーネスの Low）→ `docs/reviews/backlog/I602.md`。判定の仕組み・SECURITY の理由の行は無いので「最優先」は付けない
- [retro] 改善案 3 件はどれも見送り（下の「## 振り返り」）— その場で捕まり手戻りが出ていない・既存の決まりで足りる

## 振り返り

### かんたんなまとめ
**良かった点**
- 計画レビュー・コードレビュー・テストが、どれも 1 回で通りました（理由: 写しを探す確かめを、補助の名前ではなく中身の目印で書き、実装の前に「今の写しなら落ちる」ことまで確かめておいたため）
- 補助をまとめるときに、写しが 3 つだけであることを先に検索で確かめたので、取りこぼしがありませんでした

**今回の問題への直接の対処**
- レビューで残った軽い指摘のうち、テストの守りの範囲の 2 件（見出しの比べ方の弱点・補助が制約の設定を戻さない）は、同じ種類の残りを扱う #580 に入れました。手順書の書き方の 1 件は、軽い指摘の一覧に入れました

**同じ問題を次回から防ぐ改善**
- 新しく足す決まりはありません。途中で起きたつまずき（コマンドの書き方でサンドボックスの中に入り GitHub を読めなかった・一括の置き換えで関数名を 1 か所壊した・不要な包みの関数を残した）は、どれもその場で気づいて直し、手戻りは出ませんでした。前の 2 つは手順書（危険操作の手順書の「外に出すコマンドの書き方」）に既に書いてあり、最後の 1 つは整理の工程（/simplify）で捕まりました

### 詳細
**良かった点**
- 決定論ゲート（TC-03）を名前ではなく中身の目印で書き、実装前の写しで 9 行とも exit 1 を確かめた（FG）。直書きの写し（I492）も捕まえる
- 補助の写しの全件を grep で列挙してから計画した（3 ファイルだけ）

**是正処置（Corrective）**
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ベストプラクティス | テストの比べ方・補助の副作用の想定が無い（台帳 F1・F3） | #580 に同梱（コメント） |

**予防処置（Preventive）**: なし

**見送り（2.7 の 4 問）**
- Bash の 1 回目に `cd … &&`・`; echo` を付けて issue-source.sh がサンドボックスの中で動き gh が失敗 — 実害なし（次の呼び出しで直した）・決まりは `docs/runbooks/danger-ops.md`「外に出すコマンドの書き方」に既にある
- `str.replace` の一括置換で `_columns(` が関数名の一部（`removes_columns(`）にも当たった — 差分の確認でその場で捕まり、テストの前に直した。手順を足すほどの損失が無い
- `_subject_columns` の包みを残した — /simplify が捕まえた（既存の工程で足りる）
- 残余リスク処遇・設計ルール昇格: security-review（設計・組み込み）は動いていない（RISK NO）のでスキップ
- [close] 記録を closed へ移すときに 1 回すべてを `docs/reviews/closed/` に入れてしまい、すぐにそれぞれの closed へ移し直した（コミット前で影響なし）。一覧（backlog/I602.md）の記録のパスも closed に直した — 1 つの呼び出しで git を組み合わせる形が拒否されたため、単体の git mv に分けた

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
