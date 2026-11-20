# I602 レビュー: I590 のレビューの残り（テストの守りの抜け・0027 の戻し方・補助の集約）

## 変更概要
-

## 変更点
-

## 影響範囲
- Backend/Frontend/DB/Config:

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし / あり（理由）

## ロールバック
-

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 補助の置き場を `backend/problems/tests/migration_helpers.py`、0027 の戻り方の置き場を `docs/runbooks/backend-check.md` の新しい節にした — 前例（`i466_data.py`）と同じ置き方・止まった人が最初に開くマイグレーションの診断の手順書（計画書 9）
- [plan-review] 計画レビュー OK。Info 2 件（確かめのコマンドを `dbshell -- -c` に・0026 の判定と合わせる）を計画書に反映し、Warning 2 件（TC-03 の語を説明文に書かない・SQL の一致は手動テスト No.2）は実装で留意 — 方式・範囲を変えないので再レビューしない
- [implement] 計画どおり実装。手元で 3 ファイル 30 件 passed・TC-03 の 9 行は exit 0 — 正は CI
- [implement] `/simplify`（4 観点）の反映: `app_imports` を「集めてから 1 回だけ絞る」形に戻した・`_subject_columns` の包みを消して `column_names("problems_subject")` を直に呼ぶ（計画書 4-(3) の記載どおり）・`run_migration` の説明の誤解しやすい書き方を直した — 振る舞いは変えない
- [implement] `/simplify` の見送り: `test_I587_media_in_db.py` の見出しの固定の値の確かめを補助に寄せる案（計画の範囲外。固定の値の確かめは辞書と応答が一緒に変わる弱点〔計画 R2〕を補っているので残す）・`Cache-Control` の文字を `MEDIA_CACHE_CONTROL` に置き換える案（計画で残すと決めた行・値そのものを固定する意図）・`load_migrations` をセッションで 1 回にする案（DB の状態に左右され古い状態を読むおそれ）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
