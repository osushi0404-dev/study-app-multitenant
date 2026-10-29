# I200 レビュー: 見張りの確認を「本当に危ない操作」だけに絞る

## 変更概要
（実装後に記入）

## 変更点
（計画書 `docs/plans/open/plan_I200.md` の 4・5 と対応。実装後に記入）

## 影響範囲
- アプリのコードの変更なし。ハーネスの見張り・許可の設定・セッションの開始のフック・テスト・runbook

## テスト結果
（test-gate で記入）

## 計画との差分
（計画変更記録があれば要約）

## ロールバック
- PR を revert する（データの変更なし）。revert の後、primary を手で develop にそろえ直す

## 自律判断の記録
- [plan] 最初のコミットで I213 のマージ後の手動テスト No.6〜8 の結果を書き足した（イシューの「引き継ぎ」の節。I213 の記録は develop に入っていて書き足す PR が無いため）— あわせて確かめた 2 点: セキュリティの修正が 1 件ずつ届いた理由は Dependabot の仕様（I215 #394 に同梱）／react-scripts 由来で直せない 7 件に本番に影響する重いものは無い（I214 の優先度は上げない）
- [plan] イシューで「計画の最初に確定」としていた、確認を出している層を実測した（check-permission-prompt.sh と見張りの単体の判定）。見張りを直すだけでは足りず、許可の設定に `docker compose exec|run|cp` を足す必要があると分かったので範囲に入れた — 受け入れ条件（I166 の操作が通常モードで確認なしで通る）を満たすのに必要。`git push *` と同じ「allow＋見張りが判定」の形
- [plan] `docker compose cp` のホスト→コンテナを「取り出し」と判定する誤りを見つけ、範囲に入れた — 同じく受け入れ条件に必要
- [plan-review] 計画レビュー 1 は BLOCKER（Edit の allow 不足・Edit を確かめる道具が無い）。範囲を足して直し（計画変更記録 1）、2 回目は HIGHRISK。2 回目の Warning 4 件は方式を変えずに直した（計画変更記録 2）— 再レビューは不要と判断
- [design-security-review] Blocker・High は 0 件。Medium 5 件（ワークフローの `secrets` の書き方の取りこぼし・例外の経路での `down -v`・`docker compose cp` の `/app/` への上書き・pre-commit の `files:`／`types`・確かめの道具の上書き）は、方式を変えずに計画の細部とテストに入れた（計画変更記録 3）— 計画レビューのやり直しは不要と判断（語と条件の細部だけ）。Low 3 件（コンテナ内の `pip install`・`github.token`・git の hook）は受け入れ、retro で残余リスクとして扱う

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement
