---
github_issue_number: 8
created_at: 2026-03-08
---

# 手動テスト — Issue #8: docs/work ディレクトリ再構成

## MT01: `/issue-bootstrap` Mode A（新規 GH Issue）の動作確認

**手順:**
1. `feature/test-bootstrap-mode-a` ブランチを作成（テスト用）
2. `/issue-bootstrap テスト用イシュー` を実行
3. GitHub に新しいイシューが作成されることを確認
4. `docs/work/open/{新しい番号}/00_issue.md` が作成されることを確認
5. ブランチ `feature/I{番号}-{slug}` が作成されることを確認
6. Draft PR が作成されることを確認
7. テスト用ブランチ・イシュー・PR を削除してクリーンアップ

**期待結果:**
- GH Issue 番号が主キーになっている
- ローカル採番（001, 002...）が使われていない
- `docs/work/open/` 配下にフォルダが作成されている

**実施記録:**
- 実施日: -
- 結果: -
- 備考: -

---

## MT02: `/issue-bootstrap` Mode B（既存 GH Issue）の動作確認

**手順:**
1. GH Issue 番号（例: 8）を指定して `/issue-bootstrap 8` を実行
   （ただし Issue #8 のフォルダが既に存在する場合はスキップ or 別の番号で確認）
2. `docs/work/open/{番号}/00_issue.md` が GH Issue の内容で作成されることを確認
3. ブランチが作成されることを確認
4. Draft PR が作成されることを確認

**期待結果:**
- `gh issue view` で取得した内容が `00_issue.md` に反映されている
- 既存フォルダがある場合は上書きせずエラーを出す（または確認を求める）

**実施記録:**
- 実施日: -
- 結果: -
- 備考: -

---

## MT03: `/plan` の新パス動作確認

**手順:**
1. テスト用 Work Item フォルダ（例: `docs/work/open/999/`）を作成
2. `00_issue.md` に最低限の内容を記載
3. `/plan 999` を実行
4. 以下のファイルが生成されることを確認:
   - `docs/work/open/999/10_plan.md`
   - `docs/work/open/999/20_test_auto.md`
   - `docs/work/open/999/21_test_manual.md`
   - `docs/work/open/999/30_review_R?????.md`
5. `docs/indices/review_seq.json` の `next` がインクリメントされていることを確認
6. テスト用フォルダを削除してクリーンアップ

**期待結果:**
- 旧パス（`docs/plans/`, `docs/tests/`, `docs/reviews/`）に何も作成されない

**実施記録:**
- 実施日: -
- 結果: -
- 備考: -

---

## MT04: `/close` のフォルダ移動確認

**手順:**
1. テスト用 Work Item フォルダ（例: `docs/work/open/998/`）を作成し必須ファイルを用意
2. `/close 998` を実行
3. `docs/work/open/998/` が `docs/work/closed/998/` に移動していることを確認
4. `90_closeout.md` が作成されていることを確認
5. `docs/indices/WORK_INDEX.md` が更新されていることを確認
6. テスト用フォルダを削除してクリーンアップ

**期待結果:**
- `open/998/` が存在しない
- `closed/998/` が存在する
- `90_closeout.md` が完成している

**実施記録:**
- 実施日: -
- 結果: -
- 備考: -

---

## MT05: 旧ディレクトリへの誤操作防止確認

**手順:**
1. `docs/issues/DEPRECATED.md` を開き内容が表示されることを確認
2. 旧テンプレートファイルが旧ディレクトリに残っていないことを確認
3. 新テンプレートが `docs/work/templates/` に存在することを確認

**期待結果:**
- 旧テンプレートが `docs/work/templates/` に移管済み
- 旧ディレクトリには `DEPRECATED.md` のみ存在

**実施記録:**
- 実施日: -
- 結果: -
- 備考: -
