# I134 手動テスト（issue_template 背景/目的プレースホルダ追加＋open イシュー形式統一 sweep）

- 関連: docs/issues/open/I134.md / docs/plans/open/plan_I134.md / GitHub #242 / Draft PR #249

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `git status --short` と `git diff --stat origin/develop...HEAD` で変更ファイル一覧を確認する | tracked の変更が計画 変更点一覧のみ（`issue_template.md`・`check-issue-background.sh`・旧 12 件・I134 関連 docs）で、計画外ファイルの変更が無い。untracked の変更が 13 件（計画 調査結果 (A) の未追跡リスト）のみ | Claude | | |
| 2 | `gh issue view 220 --json body --jq .body` と `gh issue view 10 --json body --jq .body` の冒頭 15 行を表示する | どちらも本文冒頭（タイトル直後）に `## 背景/目的` 見出しとラベル 2 行が入り、既存本文がその下に無傷で続いている（見出し無し本文への挿入位置の代表確認） | Claude | | |
| 3 | Draft PR #249 の CI チェックを `gh pr checks 249` で確認する | 全チェック PASS（docs＋shellcheck 対象スクリプトのみの差分で赤が無い） | Claude | | |
| 4 | 書き起こした背景・目的の内容妥当性をサンプル 3 件で目視確認する: ① https://github.com/osushi0404-dev/study-app-multitenant/issues/191 （I101・現行テンプレ型） ② https://github.com/osushi0404-dev/study-app-multitenant/issues/42 （I020・旧形式） ③ wt-harness の `docs/issues/open/013.md`（ローカル旧形式） | 追記された **背景**/**目的** の要約が各イシューの既存記述と矛盾せず、経緯（どこから生まれたか）と達成状態（何がどうなれば成功か）が読み取れる | Human | | 要約の質の感覚的確認のため Human |
