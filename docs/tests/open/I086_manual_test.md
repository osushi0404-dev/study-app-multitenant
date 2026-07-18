# I086 手動テスト: 高リスク変更の敵対的レビューステージ自動化

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実装後の `/code-review I086` で生成された `docs/reviews/I086_code_review_<ts>.md` の注入セクション（決定論ゲート実行結果）を Read で開く | 「高リスク判定: YES（LLM=… / path=YES）」の証跡行が存在する（本イシューは `.claude/skills/` 等の変更を含むためパス決定論トリガで強制 YES になる） | Claude | | |
| 2 | 同じ `/code-review I086` 実行で敵対的レビューステージが**ユーザー操作なしに自動起動**したことを確認する: `docs/reviews/I086_adversarial_review_<ts>.md` が生成・commit されていることを Bash（git log）と Read で確認する | 記録に周回数・観点（固定 3 観点を含む）・エージェント数・findings・最終行 `VERDICT: <BLOCKER\|HIGH\|OK>` が含まれ、新規 Critical/High が 0 の周回で終了している（本イシュー自身によるドッグフード） | Claude | | |
| 3 | I080 逆引き検出（AC6）: `git log` で I083 修正**前**の push ガード（`scripts/claude/hooks/pretooluse_guard.py` の当時版）を特定し temp repo（scratchpad 配下）へ展開。adversarial-reviewer.md のマンデート＋観点①（ロジック回避・実機 repro）で Agent を 1 体起動し、当時のガードをレビューさせる | R5 相当（コマンド置換・変数展開等で宛先が静的確定できない `git push` がガードを素通りする）が Critical/High として検出され、検出結果が記録される（ステージが load-bearing であることの裏取り） | Claude | | |
| 4 | 非高リスク経路の無回帰（AC5）: SKILL.md の分岐記述を Read で確認し、`ADVERSARIAL_STAGE: NOT_REQUIRED` の場合に従来どおりスクリプトの案内のみで終了する（敵対ステージに触れない）ことを確認する。あわせて TC-01 の path_risk_trigger 非対象系（app のみの変更 → NO）の結果を参照する | NOT_REQUIRED 分岐が「従来どおり終了（無回帰）」と明記され、非対象パスで NO を返すことがテスト済みである | Claude | | |
| 5 | 追記・新規作成した文言（SKILL.md の敵対ステージフロー・adversarial-reviewer.md・review-rules.md の非権威化規定・code-reviewer.md の条件リスト/RISK 行仕様）を通読する | 運用者（レビュー実施者・計画作成者）が誤解なく読める文言になっている（分かりにくい表現があれば NG として指摘） | Human | | |

結論: （/test 時に記録）
