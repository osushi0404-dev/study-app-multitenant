# I178 自動テスト: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

対象: `.github/CODEOWNERS`・`docs/runbooks/branch-protection-setup.md`・`.claude/skills/close/SKILL.md`・`scripts/claude/pr-base-sync.sh`（無改変の確認）

**合否判定インターフェース**: すべて exit code に統一する（合格 = exit 0 / 不合格 = 非ゼロ）。出力値の目視比較は合否基準にしない。不在判定は `! grep -q ...` の形で書き、合格時に exit 0 を返す。

**実行環境**: ホスト（ワークツリー `/mnt/c/app/wt-harness`）。gh 2.88.1。GitHub API を使う TC（TC-03・TC-04・TC-17）は bot アカウント（write 権限）で実行できることを確認済み。

---

## 決定論ゲート（自動実走）
<!--
  /code-review（code-review.sh）がこのブロックを 1 行 1 コマンドで実走し、実 exit code を VERDICT に注入する。
  コマンド置換を含む検証（TC-02b・TC-03・TC-04・TC-17）は allowlist 外のため /test で実施する。
-->
```bash
test -f .github/CODEOWNERS
grep -qxF '* @oshui0404' .github/CODEOWNERS
grep -q "Require review from Code Owners" docs/runbooks/branch-protection-setup.md
grep -q "Restrict who can push to matching branches" docs/runbooks/branch-protection-setup.md
! grep -qE "自己 approve|セルフ approve" docs/runbooks/branch-protection-setup.md
! grep -q "承認不要" docs/runbooks/branch-protection-setup.md
grep -q "承認者の限定（I178）" docs/runbooks/branch-protection-setup.md
grep -q "main には CODEOWNERS が無い" docs/runbooks/branch-protection-setup.md
grep -q "PR は必ず bot（Claude）が作成する" docs/runbooks/branch-protection-setup.md
grep -q "承認が取り消される" docs/runbooks/branch-protection-setup.md
grep -qF 'Code Owners（`oshui0404`）の承認が必須' .claude/skills/close/SKILL.md
grep -q "再承認を依頼する" .claude/skills/close/SKILL.md
git diff --quiet origin/develop -- scripts/claude/pr-base-sync.sh
bash scripts/claude/tests/test_pr_base_sync.sh
! grep -qF "| Required approvals | 0 |" docs/runbooks/branch-protection-setup.md
! grep -qF "Require approvals（サブオプション）" docs/runbooks/branch-protection-setup.md
```

---

## 計画時ベースライン（Red・失敗注入・2026-10-17 実測）

実装前の状態で全 TC を実行した結果。追加内容を確かめる TC がすべて非ゼロで終わることが、そのまま失敗注入（対象が無い・壊れている状態で NG を返すこと）の確認になる。無改変・既存状態を確かめる TC（TC-03・TC-15・TC-16）は、別途注入版で非ゼロを確認した。

| TC | 実測 exit | 判定 |
|---|---|---|
| TC-01 | 1 | ✅ Red（CODEOWNERS 不在） |
| TC-02a / TC-02b | 2 / 2 | ✅ Red |
| TC-03 | 0 | 既存状態（`oshui0404`=admin）。**注入版**（bot `osushi0404-bot` で照会）= **1** ✅ |
| TC-04 | 2 | ✅ Red（CODEOWNERS を含まないブランチでは API が 404 → 非ゼロ） |
| TC-05〜TC-14 | すべて 1 | ✅ Red（TC-07・TC-08 は現行 runbook に誤記・旧記述があるため不合格＝否定判定が実際に NG を返す） |
| TC-15 | 0 | 無改変。**注入版**（比較先を変更前の develop `85a0b9c` にして差分がある状態）= **1** ✅ |
| TC-16 | 0 | 既存テスト `RESULT: OK (21/21 cases, 30 assertions)`（回帰の基準） |
| TC-17 | 2 | ✅ Red（develop に CODEOWNERS が無いため 404 → 非ゼロ） |
| TC-18a / TC-18b | 1 / 1 | ✅ Red（旧差異表・旧 develop 表の行が残っているため不合格＝否定判定が実際に NG を返す） |

---

## TC-01: CODEOWNERS が存在する（AC-1）
- コマンド: 決定論ゲート 1 行目
- 期待: exit 0

## TC-02: CODEOWNERS の中身が `* @oshui0404` の 1 行だけ（AC-1）
- TC-02a（決定論ゲート 2 行目）: `* @oshui0404` と完全一致する行がある → exit 0
- TC-02b（/test で実行）: コメント・空行以外の行がちょうど 1 行
  ```bash
  [ "$(grep -cvE '^[[:space:]]*(#|$)' .github/CODEOWNERS)" -eq 1 ]
  ```
- 期待: どちらも exit 0

## TC-03: CODEOWNERS の所有者がリポジトリの管理者である（AC-1・R1）
- /test で実行:
  ```bash
  [ "$(gh api repos/osushi0404-dev/study-app-multitenant/collaborators/oshui0404/permission --jq .permission)" = admin ]
  ```
- 期待: exit 0（`oshui0404` の権限が `admin`）

## TC-04: GitHub の CODEOWNERS 検査で問題が 0 件（AC-1・ステップ 1 のゲート）
- ステップ 1 の push 後に /test で実行（後続ステップへ進む条件）。ref はカレントブランチから取る（ブランチ名の書き間違いで「ブランチ不在の 404」と「検査エラー」が混ざらないようにする・plan-review 20261017_1916 Info 対応）:
  ```bash
  [ "$(gh api "repos/osushi0404-dev/study-app-multitenant/codeowners/errors?ref=$(git rev-parse --abbrev-ref HEAD)" --jq '.errors | length')" -eq 0 ]
  ```
- 期待: exit 0（`errors` が空配列。所有者名の誤り・権限不足・構文エラーがあると 1 件以上になる）。CODEOWNERS を含まないブランチでは API が 404 を返し、空文字との比較で非ゼロになる（計画時ベースラインで確認済み）

## TC-05: runbook に「Require review from Code Owners」がある（AC-6）
- コマンド: 決定論ゲート 3 行目 / 期待: exit 0

## TC-06: runbook に「Restrict who can push to matching branches」がある（AC-6）
- コマンド: 決定論ゲート 4 行目 / 期待: exit 0

## TC-07: runbook に「自己 approve」「セルフ approve」の誤記が無い（AC-6）
- コマンド: 決定論ゲート 5 行目 / 期待: exit 0

## TC-08: runbook に develop を「承認不要」とする記述が無い（AC-6）
- コマンド: 決定論ゲート 6 行目 / 期待: exit 0

## TC-09: runbook に新設セクション「承認者の限定（I178）」がある（AC-6）
- コマンド: 決定論ゲート 7 行目 / 期待: exit 0

## TC-10: runbook に main の制約（CODEOWNERS が届かない）が書かれている（AC-6・R3）
- コマンド: 決定論ゲート 8 行目 / 期待: exit 0

## TC-11: runbook に「PR は必ず bot（Claude）が作成する」運用が書かれている（AC-6・R4）
- コマンド: 決定論ゲート 9 行目 / 期待: exit 0

## TC-12: runbook に、承認後のコミットで承認が取り消される旨が書かれている（AC-6・R6）
- コマンド: 決定論ゲート 10 行目 / 期待: exit 0

## TC-13: close スキル step 5.5 の前提が「Code Owners の承認が必須」になっている（AC-7）
- コマンド: 決定論ゲート 11 行目 / 期待: exit 0

## TC-14: close スキル step 6 に再承認の依頼が書かれている（AC-7・R6）
- コマンド: 決定論ゲート 12 行目 / 期待: exit 0

## TC-15: `pr-base-sync.sh` を変更していない（AC-7）
- コマンド: 決定論ゲート 13 行目 / 期待: exit 0

## TC-16: `pr-base-sync.sh` の既存テストが合格する（AC-7・回帰）
- コマンド: 決定論ゲート 14 行目
- 期待: exit 0（`RESULT: OK (21/21 cases, 30 assertions)`）

## TC-17: マージ後、develop の CODEOWNERS 検査で問題が 0 件（AC-1・マージ後）
- PR #298 のマージ後に実行:
  ```bash
  [ "$(gh api 'repos/osushi0404-dev/study-app-multitenant/codeowners/errors?ref=develop' --jq '.errors | length')" -eq 0 ]
  ```
- 期待: exit 0

## TC-18: runbook から旧設定の表の行が消えている（AC-6）
- plan-review 20261017_1916→1921 Warning 対応。TC-07・TC-08 は日本語の文言しか見ないため、英語の表の行が残っても検知できない穴を塞ぐ。
- TC-18a（決定論ゲート 15 行目）: 旧「develop と main の差異」表の `| Required approvals | 0 |` 行が無い
- TC-18b（決定論ゲート 16 行目）: 旧 develop 表の `Require approvals（サブオプション）` 行が無い
- 期待: どちらも exit 0

---

## 実行結果

| TC | 実行日 | 結果 | 備考 |
|---|---|---|---|
| TC-04 | 2026-10-17 | ✅ exit 0 | /implement ステップ 1 のゲート。CODEOWNERS push 直後（3d6f029）に `{"errors":[]}` を確認してから後続へ進んだ |
| TC-01〜TC-16・TC-18 | 2026-10-17 | ✅ 全件 exit 0 | /implement 完了時（ステップ 1〜3 反映後）。TC-16 は `RESULT: OK (21/21 cases, 30 assertions)`。/test で再実行する |
| TC-17 | | 未実施（マージ後） | |
