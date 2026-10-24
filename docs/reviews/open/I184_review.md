# I184 レビュー: I179 のワークツリー運用を既存の環境に適用する

## 基本情報
- **関連イシュー**: #312（docs/issues/open/I184.md）
- **計画書**: docs/plans/open/plan_I184.md
- **Draft PR**: #313
- **テスト文書**: docs/tests/open/I184_auto_test.md・docs/tests/open/I184_manual_test.md

## レビュー対象
| 計画 | 対象 | 内容 |
|------|------|------|
| 4-1 | primary `refs/remotes/origin/HEAD` | `origin/develop` に合わせる |
| 4-2 | harness-1・harness-2 | 公式 `claude --worktree` で作成 |
| 4-3 | primary の `docs/issues/open/`・`docs/reviews/` | wt-harness から 37 件をコピー（未コミット） |
| 4-5〜4-7 | wt-harness・Docker volume 4 つ・I181 ブランチ | untracked の削除 → volume の削除（危険操作・バックアップなし＝D4）→ 撤去 |
| 4-8 | ラベル `track:harness`・`track:app` | 説明文からワークツリー名を外す |
| 4-11 | ラベル `danger-approved`（新規）・PR #313 | 危険操作の承認の印として作成・付与 |
| 4-9・4-10 | `docs/runbooks/worktree.md` | §7 反映のタイミング・§11 手順 4 の注意・手順の不足の修正 |

## コピーの一覧（ステップ 3・2026-10-24）
wt-harness の `??` 39 件のうち 37 件を primary へ `cp`（コピー前に primary に同じパスが無いことを確認）。TC-4a（全件 `cmp` 一致、または closed 済みイシューファイル）は exit 0。primary 側は未コミットのまま。

<!-- copied-begin -->
docs/issues/open/I093.md
docs/issues/open/I094.md
docs/issues/open/I099.md
docs/issues/open/I101.md
docs/issues/open/I110.md
docs/issues/open/I112.md
docs/issues/open/I118.md
docs/issues/open/I125.md
docs/issues/open/I128.md
docs/issues/open/I130.md
docs/issues/open/I135.md
docs/issues/open/I136.md
docs/issues/open/I139.md
docs/issues/open/I152.md
docs/issues/open/I175.md
docs/issues/open/I176.md
docs/issues/open/I177.md
docs/reviews/I093_issue_review_20260702_1416.md
docs/reviews/I094_issue_review_20260702_1418.md
docs/reviews/I099_issue_review_20260705_0238.md
docs/reviews/I100_issue_review_20260705_0241.md
docs/reviews/I101_issue_review_20260705_0246.md
docs/reviews/I110_issue_review_20260715_1156.md
docs/reviews/I112_issue_review_20260715_1308.md
docs/reviews/I118_issue_review_20260715_2116.md
docs/reviews/I121_issue_review_20260716_1731.md
docs/reviews/I125_issue_review_20260718_0115.md
docs/reviews/I128_issue_review_20260718_1211.md
docs/reviews/I130_issue_review_20260719_0129.md
docs/reviews/I135_issue_review_20260719_1453.md
docs/reviews/I136_issue_review_20260719_1501.md
docs/reviews/I139_issue_review_20260719_2231.md
docs/reviews/I151_issue_review_20260815_1636.md
docs/reviews/I152_issue_review_20260815_1639.md
docs/reviews/I175_issue_review_20261017_1221.md
docs/reviews/I176_issue_review_20261017_1226.md
docs/reviews/I177_issue_review_20261017_1232.md
<!-- copied-end -->

| コピーしなかったもの | 理由 |
|--------------------|------|
| `docs/issues/open/I121.md` | develop に closed 版あり（§11 コピーしないもの）＝`docs/issues/closed/I121.md` |
| `docs/issues/open/I151.md` | develop に closed 版あり（§11 コピーしないもの）＝`docs/issues/closed/I151.md` |
| gitignore 済み（`.claude/settings.local.json`・`.env`・`backend/.env`・キャッシュ・ログ・`celerybeat-schedule`） | 計画書 調査結果のとおり反映不要（`settings.local.json` は primary が上位集合） |

## 危険操作の承認（ステップ 4・2026-10-24）
- 対象: wt-harness の Docker volume 4 つ（`wt-harness_postgres_data`・`wt-harness_redis_data`・`wt-harness_backend_logs`・`wt-harness_backend_static`）の削除（`DANGER_OK=1 bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness` 内の `docker compose -p wt-harness down -v`）。バックアップなし（D4）
- ユーザーの明示承認: 「データは削除してよい」（/plan-issue-review 中・2026-10-24）。前段で「古いデータはたぶん削除してよいかと」
- 使用箇所の確認（承認時にユーザーの依頼で実施）: 4 つの volume を使うコンテナは停止中を含めて 0 件（`docker ps -a --filter volume=…`）。稼働中は primary（`study-app-multitenant`）のコンテナだけで別の volume を使う。tracked ファイルでの名前の出現は計画書の説明とガードのテスト文字列（`scripts/claude/tests/test_pretooluse_worktree_guard.sh:121`）だけ。primary の `.env`・`e2e/.env.e2e` は秘密情報を含むため読めず未確認（wt-harness のポートは wt-harness の `.env` にだけ書かれる）
- `danger-approved` ラベルを新規作成し PR #313 に付与（TC-9 exit 0）

## 撤去（ステップ 5・2026-10-24）
- ユーザーが wt-harness の untracked 39 件を削除（`git status --porcelain` が空）→ primary で `DANGER_OK=1 bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness`（承認画面でユーザーが許可）→ volume 4 つ Removed・「撤去完了」→ `git branch -d feature/I181-slim-review-process`（26d06ec・マージ済み）

## 手順の不足（ステップ 6・2026-10-24）
- §11 手順 4 の「作った直後は終了で消える」注意の欠け（計画時に発見・4-10 で追記済み）
- それ以外は無し（§2 確認 1〜2・§11 手順 1〜3・§4 の volume だけ残っている場合の停止と `DANGER_OK=1` の再実行は、書かれたとおりに進んだ）

## 実装（2026-10-24・/implement）
- ステップ 1〜6 を計画どおり実施。計画外の変更なし。自動テストの結果は `docs/tests/open/I184_auto_test.md`「実装時」
- /retro の材料: wt-harness 側の 39 件の削除をユーザーに依頼したが、ユーザーから「あなた自身で実施できなかったか」と指摘。§11 手順 3・§9 の「別のワークツリーの中身を消さない」に従ったためで、技術的には primary から消せた（I179 で削除のガードは廃止済み）。コピーの一致（TC-4a）を確かめた後の削除なので、実害の無い手間を人に回していた可能性がある
