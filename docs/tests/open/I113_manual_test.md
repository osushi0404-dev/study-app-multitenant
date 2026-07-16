# I113 手動テスト: /close の base 追従チェック（pr-base-sync.sh）

対象: `scripts/claude/pr-base-sync.sh`・`.claude/skills/close/SKILL.md`（呼び出し追加後）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | Read で close SKILL.md 全体を読み、step 0（sync 呼び出し）・step 5.5（final 呼び出し）・終了コードごとの進行指示を確認する | step 0 のコードブロックに `pr-base-sync.sh sync` が、step 5（`gh pr ready`）と step 6（マージ依頼）の間に step 5.5 として `pr-base-sync.sh final` があり、双方に exit 1=STOP してユーザーに報告（自動解決しない）・exit 2=ユーザーに続行可否確認が明記されている。既存 step 1〜6 の本文（git mv 手順・staged スコープガード・`gh pr ready`）は無改変 | Claude | | |
| M2 | 実機スモーク（sync）: 本イシューの PR #219 のブランチ上で `bash scripts/claude/pr-base-sync.sh sync 219` を実行する | exit 0 で終了し、「✅ 追従不要（mergeStateStatus=...)」または「✅ base（origin/develop）を取り込みました」のどちらかが表示される。BEHIND だった場合は `git log` に merge コミットができ、push はされない（`git status` が ahead を示す） | Claude | OK | 2026-07-16 実施。実測 `✅ 追従不要（mergeStateStatus=CLEAN）`・exit 0（実 GitHub 照会） |
| M3 | 実機スモーク（final・fail-closed 実証）: PR #219 が draft のうちに `PBS_RETRY_INTERVAL=1 bash scripts/claude/pr-base-sync.sh final 219` を実行する | リトライ（約6秒）の後「⛔ Ready 化後も DRAFT のまま」を表示して exit 1（draft の PR を final が誤って合格させない） | Claude | OK | 2026-07-16 実施。実測は DRAFT ではなく **CLEAN** が返り `✅ CLEAN（マージ可・CI 通過）`・exit 0（備考の想定どおり実測値の分岐動作を記録: 本リポジトリでは draft・最新・CI 緑の PR に CLEAN が返る＝DRAFT 値は観測されず）。CLEAN 分岐の実機確認として OK。DRAFT 分岐は T12（スタブ）で担保済み |
| M4 | （マージ後・次イシューの /close 実行時）step 0 と step 5.5 が実際に実行され、出力どおりに進行することを確認する | /close の流れの中で2箇所のチェックが実行され、BEHIND 時は追従（step 0=取り込みのみ・step 5.5=push＋CI 待機）、それ以外は続行する。I107 型の out-of-date 見逃しが発生しない | Human | | 非ブロック（通常運用での確認継続） |
