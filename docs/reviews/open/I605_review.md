# I605 レビュー: ほかのワークツリーの画像の移行と片付け

## 変更概要
- primary・harness-1・harness-2・study に残っていた、画像の移行の前の DB と画像ファイルを片付ける（primary は移して確かめてから消す・harness は DB を捨てる・study はファイルを消す）
- 手順書 `docs/runbooks/backend-check.md` §4 を、backend が起動の途中で止まった後でも動くコマンドに直す

## 変更点
- `docs/runbooks/backend-check.md` §4（計画書 4-1）
- 運用: 計画書 4-2（primary）・4-3（harness-1・harness-2・study）

## 影響範囲
- Backend/Frontend: なし（コードを変えない）
- DB: primary の開発の DB（移行 0024〜0027）・harness-1・harness-2 の開発の DB（保存領域ごと削除）
- Config: 各ワークツリーの `backend/media`（git の外）の削除

## テスト結果
- 自動:
- 手動:

## 計画との差分
-

## ロールバック
- 計画書 7 のとおり

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] harness-1・harness-2・study の削除は app-1 で人が `!` を付けて流す（各ワークツリーで Claude を起動しない）— 消すだけで人の承認が要り、Claude の `DANGER_OK=1 docker …` はサンドボックスの中に入って docker に届かないため（計画書 9）
- [plan] primary の結果は GitHub #605 のコメントで受け渡す — primary のセッションは app-1 のファイルに書けず、チャットでの受け渡しは禁止のため（計画書 9）
- [plan] 片付けは implement の段階で済ませ、人の承認のところで止まって `/proceed` で戻る — 危険操作は人の承認が要り、test-gate で終わった状態を確かめるため（計画書 9）
- [plan] 手順書 §4 を直し、一覧の I602 F2 を同梱する — 起動の途中で止まった後に今のコマンドが動かないため（計画書の調査結果 2）

### 承認の記録
<!-- 危険操作の承認の言葉と日付（P4・P9 は #605 の primary のコメントから写す・A2 は app-1 の会話から） -->
-

STAGE_DONE: plan NEXT: plan-review
