# I069 自動テスト（計画駆動）

- **関連計画書**: docs/plans/open/plan_I069.md
- **正とする自動テスト**: 下記 TC-A1〜A6・TC-B1〜B3・TC-C1〜C3（`scripts/claude/tests/test_review_commit_lifecycle.sh`）
- **既定テスト**: pytest / Jest / Playwright E2E は **非該当**（app コード変更なし）。`/test` 時に「非該当」と記録する。
- 実行者: すべて Claude。TC-A/B は git 一時 fixture（使い捨て repo）、TC-C は shellcheck/bash -n/既存テスト非退行。
- **TDD**: TC-A1〜A6・TC-B1 は implement の Red（`commit_review_artifact` 未定義・close 未修正で失敗）→ Green（実装後 PASS）で実行・記録する。

実行（必ず bash スクリプトとして実行。対話シェルへ貼らない＝grep が ugrep ラッパーに上書きされ -E/-o が誤動作するため）:
```bash
bash scripts/claude/tests/test_review_commit_lifecycle.sh
```

## 案A: commit_review_artifact（ブランチガード・path-scoped・他 index 不可侵）
fixture は一時 git repo（`git init` + ローカル user 設定 + 初期コミット）。`plan-issue-review.sh` / `code-review.sh` から
`REVIEW_LIB_SOURCE_ONLY=1 source` で `commit_review_artifact` を読み込んで検証する。

> **テスト実装上の注意（review W-Info1 反映）**: 対象スクリプト冒頭の `set -euo pipefail` は source 時に
> テストシェルへ伝播する。既存 `test_review_verdict.sh:42` と同様に、source 直後に `set +e +o pipefail` で
> 解除する（または `( source ... )` サブシェルで隔離する）こと。
> **grep 系 TC の決定論性**: コメント行マッチによる偽陽性を避けるため、配線有無を検査する grep は
> コメント行（`^[[:space:]]*#`）を除外したうえで判定する。

| TC | 内容 | 手順（要点） | 期待結果 |
|----|------|------------|---------|
| TC-A1 | source ガードで関数定義（plan-issue-review） | `REVIEW_LIB_SOURCE_ONLY=1 source plan-issue-review.sh` 後に `declare -F commit_review_artifact` | 終了コード 0（関数が定義され、本体は未実行） |
| TC-A1b | source ガードで関数定義（code-review・W3 反映） | `REVIEW_LIB_SOURCE_ONLY=1 source code-review.sh` 後に `declare -F commit_review_artifact` | 終了コード 0（同一ヘルパが code-review 側でも定義され、本体は未実行） |
| TC-A2 | feature ブランチで commit される | fixture を feature ブランチに切替→未追跡 review ファイル作成→`commit_review_artifact` 実行 | `git ls-files` に review ファイルが出る（追跡済み）・新規コミットが1件増える・コミットは当該1ファイルのみ |
| TC-A3 | 他 index 不可侵（path-scoped） | 無関係ファイルを `git add` で staging 済みにしてから `commit_review_artifact` 実行 | 新コミットに含まれるのは review ファイルのみ（`git show --name-only HEAD` に無関係ファイルが**含まれない**）・無関係ファイルは staged のまま残る |
| TC-A4 | develop ではスキップ（未追跡で残す） | fixture を `develop` ブランチに切替→`commit_review_artifact` 実行 | review ファイルは**未追跡のまま**（`git ls-files` に出ない）・新規コミットは増えない・`ℹ️ ...commit しません` を出力・終了コード 0 |
| TC-A4b | main でもスキップ（ブランチガード・main 明示／code-review Low 反映） | fixture を `main` ブランチに切替→`commit_review_artifact` 実行 | 未追跡のまま・新規コミットなし・終了コード 0 |
| TC-A5 | detached HEAD でスキップ | detached HEAD 状態で実行 | 未追跡のまま・新規コミットなし・終了コード 0 |
| TC-A6 | issue-review.sh は commit を配線していない（案A'・W1 反映） | コメント行を除外して配線を検査: `grep -vE '^[[:space:]]*#' scripts/claude/issue-review.sh \| grep -E 'commit_review_artifact\|git commit'` | **マッチ無し**（終了コード 1＝実コードに `commit_review_artifact` 呼び出し・`git commit` が無い＝案A'）。コメント行内の文言は除外され偽陽性しない |
| TC-A6b | issue-review.sh に「commit しない」意図コメントが存在（W2 反映・コメント存在は本 TC で検証） | `grep -qE 'commit しない\|コミットしない\|案A' scripts/claude/issue-review.sh` | マッチあり（終了コード 0＝commit しない旨／案A' の意図が明記されている） |

## 案B: close 回収ループ（未追跡 review を git mv 失敗させない）
close/SKILL.md step 1 の timestamped 回収ループのロジック（`git add -- "$f"` → `git mv "$f" docs/reviews/closed/`）を
一時 git fixture 上で再現し、未追跡 review ファイルが `fatal: not under version control` を起こさず移動できることを検証する。

| TC | 内容 | 手順（要点） | 期待結果 |
|----|------|------------|---------|
| TC-B1 | 未追跡 issue-review を回収（AC1 再発防止） | fixture に**未追跡**の `docs/reviews/I900_issue_review_<ts>.md` を作成→回収ループ（add→mv）実行 | `git mv` が `fatal: not under version control` を起こさず終了コード 0・ファイルが `docs/reviews/closed/` へ移動・`git status` 上 staged（追跡済み） |
| TC-B2 | close/SKILL.md に案B の add が配線されている（アンカー検証） | close/SKILL.md の timestamped 回収ループ内で `git add -- "$f"` が `git mv "$f" docs/reviews/closed/` の**前**に存在することを awk/grep で検証 | 両行が存在し add が mv より前（順序成立） |
| TC-B3 | I067 決定論ゲート（step 3）が非退行 | close/SKILL.md に step 3 の scoped staging（`git add -u`）と決定論ゲート（`grep -vE "I${ISSUE_NUM}`）が残存していることを grep | 両方ヒット（I067 導入分が削除/改変されていない） |

## 静的解析・非退行
| TC | 内容 | コマンド | 期待結果 |
|----|------|---------|---------|
| TC-C1 | shellcheck（変更スクリプト） | `shellcheck scripts/claude/plan-issue-review.sh scripts/claude/code-review.sh scripts/claude/issue-review.sh scripts/claude/tests/test_review_commit_lifecycle.sh`（pre-commit 経由可） | エラーなし（局所 `# shellcheck disable` を除く） |
| TC-C2 | bash -n 構文 | `bash -n` を変更4スクリプトに対して実行 | 全て終了コード 0 |
| TC-C3 | 既存テスト非退行 | `bash scripts/claude/tests/test_review_verdict.sh` | PASS=55 FAIL=0（非退行） |

## 既定テスト（フォールバック）— 非該当
| 種別 | 判定 | 理由 |
|------|------|------|
| pytest / Jest / Playwright E2E | 非該当 | app（Backend/Frontend/DB/UI）変更なし |

## 実行記録（/implement TDD 時・2026-06-19）
Red（実装前）: PASS=16 FAIL=11 SKIP=1（TC-A1/A1b 関数未定義・TC-A2〜A5 commit されず/rc=127・TC-A6b コメント未追加・TC-B2 close 未修正）。
Green（実装後）: **PASS=27 FAIL=0 SKIP=1**。TC-C1 はローカル shellcheck 未インストールのため SKIP だが、pre-commit shellcheck フックで **Passed** を別途確認。
code-review Low 反映後（TC-A4b 追加）: **PASS=30 FAIL=0 SKIP=1**。

| TC | 結果(PASS/FAIL) | 備考 |
|----|------|------|
| TC-A1 | PASS | plan-issue-review.sh の source ガードで commit_review_artifact 定義 |
| TC-A1b | PASS | code-review.sh でも同一ヘルパ定義（非対称解消） |
| TC-A2 | PASS | feature ブランチで review 1ファイルのみ commit・追跡化 |
| TC-A3 | PASS | 事前 staged の無関係ファイルを commit に含めない（path-scoped）・staged のまま残存 |
| TC-A4 | PASS | develop でスキップ・未追跡・新規コミットなし・`commit しません` 出力 |
| TC-A4b | PASS | main でスキップ・未追跡・新規コミットなし（code-review Low 反映） |
| TC-A5 | PASS | detached HEAD でスキップ・未追跡・新規コミットなし |
| TC-A6 | PASS | issue-review.sh は配線なし（コメント除外 grep でマッチ無し＝偽陽性なし） |
| TC-A6b | PASS | issue-review.sh に案A' 意図コメント存在 |
| TC-B1 | PASS | 未追跡 issue-review を add→mv で回収・`fatal: not under version control` 起きず・closed/ へ移動・staged |
| TC-B2 | PASS | close/SKILL.md 回収ループで `git add -- "$f"` が `git mv` の前に配線（awk 順序検証） |
| TC-B3 | PASS | I067 ゲート（`git add -u` / `grep -vE "I${ISSUE_NUM}`）が非退行で残存 |
| TC-C1 | PASS | ローカル shellcheck 未インストールで自動テスト上は SKIP。pre-commit shellcheck フックで Passed を確認（4ファイル） |
| TC-C2 | PASS | bash -n 構文チェック 4スクリプト全 0 |
| TC-C3 | PASS | 既存 test_review_verdict.sh 非退行（PASS=55 FAIL=0） |
