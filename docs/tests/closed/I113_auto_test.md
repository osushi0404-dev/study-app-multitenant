# I113 自動テスト: /close の base 追従チェック（pr-base-sync.sh）

実行コマンドは末尾の「決定論ゲート（自動実走）」セクションに宣言（テストスクリプト＋統合 grep＋構文検証）。

結果:
- backend: 非該当（アプリコード変更なし・pytest 不要）
- frontend: 非該当（アプリコード変更なし・Jest 不要）
- E2E: 非該当（アプリ挙動変更なし）
- 決定論ゲート: **実行済み（実装時 2026-07-16）**。TDD Red（スクリプト不在で全ケース NG=exit 127）→ Green（**`RESULT: OK (16/16 cases, 23 assertions)`・exit 0**）を確認。TC-02 注入 3 件（DIRTY→exit 0 改変・SKILL.md sync 行欠落・final 行欠落）すべて NG/NO-HIT 検知。TC-03 統合 grep 5 件＋`bash -n` 2 件すべて OK
- 決定論ゲート再実行（/test 時 2026-07-17・develop 取り込み 67bef93 後）: test_pr_base_sync.sh → **`RESULT: OK (16/16 cases, 23 assertions)`・exit 0**。統合 grep 5 件（sync/final/合格条件/`gh pr ready`/staged ガード）＋`bash -n` すべて exit 0。CI（PR #219）も全6項目 pass 確認済み

## テストケース

### TC-01: pr-base-sync.sh の分岐網羅（test_pr_base_sync.sh・T1〜T16）
方式: 一時ディレクトリに gh / git のスタブを置き `PATH` 先頭に挿して実行（実 GitHub・実 git 非依存）。スタブは呼び出し引数をログ記録し、mergeStateStatus はケースごとのキューから返す。`PBS_RETRY_INTERVAL=0` `PBS_CI_INTERVAL=0` 等で高速実行。テスト対象は `TARGET_SCRIPT`（既定 scripts/claude/pr-base-sync.sh）で差し替え可能。

| # | モード | 状態系列（スタブ） | 期待値 |
|---|--------|-------------------|--------|
| T1 | sync | CLEAN | exit 0・git 呼び出しなし |
| T2 | sync | BEHIND | exit 0・ログに `fetch origin develop` と `merge origin/develop --no-edit` あり・`push` なし |
| T3 | sync | DIRTY | exit 1 |
| T4 | sync | DRAFT | exit 0（リトライせず即続行） |
| T5 | sync | UNKNOWN 継続 | exit 2 |
| T6 | sync | UNKNOWN→BEHIND | exit 0・merge あり（リトライ動作） |
| T7 | final | CLEAN | exit 0 |
| T8 | final | BLOCKED＋checks 全緑 | exit 0（Approve 待ちの正常） |
| T9 | final | UNSTABLE＋checks fail | exit 1 |
| T10 | final | BEHIND（merge 成功）→BLOCKED＋checks 全緑 | exit 0・ログに `push` あり |
| T11 | final | BEHIND＋merge 失敗（スタブ注入） | exit 1・ログに `merge --abort` あり |
| T12 | final | DRAFT 継続 | exit 1 |
| T13 | final | BEHIND 連続（`PBS_LOOP_MAX=1`） | exit 1（追従上限 STOP） |
| T14 | final | HOGE（未知値） | exit 1（fail-closed） |
| T15 | sync | gh pr view 失敗（スタブが exit 1） | exit 1（取得失敗で「✅ 追従不要」に落ちない＝fail-open 防止・plan review Blocker の再発防止） |
| T16 | final | gh pr view 失敗（同上） | exit 1（同上） |
| — | 合計判定 | test_pr_base_sync.sh 全体 | **exit 0・`RESULT: OK (16/16)`** |

AC との対応: T2/T11=AC1（照会・fetch/merge・コンフリクト STOP）、T2＋T10=AC2（2モード）、T7/T8=AC3（合格条件・CLEAN 非要求）、T1〜T14=AC4（全8値分岐＋確定数値）、スクリプト全体=AC7（決定論ゲート）。T15/T16 は plan review Blocker（取得失敗時の fail-open）の再発防止。

### TC-02: false-green 注入検証（実装ステップ2 で実施・実ファイル無改変）
| 手順 | 期待値 |
|------|--------|
| pr-base-sync.sh の一時コピーを作り DIRTY 分岐を `exit 0` に改変、`TARGET_SCRIPT=<コピー>` で差し替えて test_pr_base_sync.sh を実行 | **T3 が NG を出力し exit 非ゼロ**（テストは壊れた実装を確実に不合格にする） |
| SKILL.md の一時コピーから呼び出し行を削除し、TC-03 の grep を当てる | **NO-HIT（exit 1）**（統合 grep は欠落を検知する） |

実施記録（実装ステップ2・2026-07-16・実ファイル無改変・scratchpad/i113/ 上のコピーで実施）:
- 注入1: pr-base-sync.sh のコピーの sync DIRTY 分岐を `exit 0` に改変し `TARGET_SCRIPT` で差し替え → `NG: T3 sync DIRTY=STOP (expect=1 actual=0)`・`RESULT: NG (1 件 / pass 22)`・**exit 1**（検知 OK）
- 注入2: SKILL.md のコピーから `pr-base-sync.sh` 行を削除し grep → sync 行・final 行とも **NO-HIT（exit 1）**（欠落を検知 OK）
- 判定: 本ゲートは false-green ではない（壊れた状態を確実に不合格にする）

### TC-03: SKILL.md 統合＋構文検証
| 検証項目 | 判定方法 | 期待値 |
|---------|---------|--------|
| step 0 の sync 呼び出し | `grep -qF "pr-base-sync.sh sync" .claude/skills/close/SKILL.md` | ヒット（exit 0） |
| step 5.5 の final 呼び出し | `grep -qF "pr-base-sync.sh final" .claude/skills/close/SKILL.md` | ヒット（exit 0） |
| 合格条件の明記 | `grep -qF "BEHIND / DIRTY でない" .claude/skills/close/SKILL.md` | ヒット（exit 0） |
| 既存 step 5（Ready 化）の維持 | `grep -qF "gh pr ready" .claude/skills/close/SKILL.md` | ヒット（exit 0・無改変検証） |
| 既存 staged スコープガードの維持 | `grep -qF "以外が staged されています" .claude/skills/close/SKILL.md` | ヒット（exit 0・無改変検証） |
| スクリプト構文 | `bash -n scripts/claude/pr-base-sync.sh` | exit 0 |

計画時ベースライン（2026-07-16・TDD Red）: `pr-base-sync` は SKILL.md に NO-HIT・スクリプト2ファイル不在（ls exit 2）・維持系2件（`gh pr ready`／staged ガード文言）は現状 HIT を確認済み。

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_pr_base_sync.sh
grep -qF "pr-base-sync.sh sync" .claude/skills/close/SKILL.md
grep -qF "pr-base-sync.sh final" .claude/skills/close/SKILL.md
grep -qF "BEHIND / DIRTY でない" .claude/skills/close/SKILL.md
grep -qF "gh pr ready" .claude/skills/close/SKILL.md
bash -n scripts/claude/pr-base-sync.sh
```
