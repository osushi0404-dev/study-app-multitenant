# I609 レビュー: 問題の解説を任意にし、出典の欄を足す

## 変更概要
- （実装後に書く）

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: （実装後に書く）

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし / あり（理由）

## ロールバック
- PR を revert し、`docker compose exec backend python manage.py migrate problems 0027` で戻す（出典の値は失われる・解説は残る）

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] `import_problems` の `points=10` を消し、組織を科目の組織にそろえることを範囲に入れた — 今は 1 問も登録できず、受け入れ条件を満たせないため（plan 調査結果 4）
- [plan] 画面の見せ方の 2 点と出典の上限をユーザーに確かめた（止める条件 1）— 出典の上限を 200→2000 文字（URL を入れる場合）・URL はただの文字で折り返す・プレビューの解説の画像だけの問題はクイズにそろえる
- [plan] E2E は足さず、Jest と Claude の画面確認で確かめる — 種のデータを変えるとほかの E2E に響き、表示は部品のテストで値まで確かめられるため
- [plan] 範囲外の `_save_ai_problem_to_db` の不具合は直さない — 受け入れ条件と関係しない。retro で扱いを決める

- [plan-review] Warning 3・Info 2 のうち、上限の定数化・計画変更記録・空白だけの出典の TC-30 を入れた。イシュー本文（GitHub）は直さない — 写しは同期しない決まりで、変更の正は計画書の計画変更記録と 9 にある
- [implement] 出典の欄の入力例が押す前から見えるよう `InputLabelProps.shrink` を足した — 画面確認で、MUI の既定では AC3 の「入力例が出る」を満たさないと分かったため（計画変更記録）
- [implement] 既存の Jest「解説文が空なら解説画像を出さない」を消し、逆の TC-29 に置き換えた — ユーザーが計画のときに「クイズにそろえる（画像は出す）」を選んだため
- [implement] 問題管理の Jest に `jest.setTimeout(20000)` を足した — 全部を並べて流したときに 1 回 5 秒を超えた（単独では 8 秒以内で通る）
- [implement] 科目の選択欄にはラベルの結び付けが無いので、テストではダイアログの最初の選択欄として探す。結び付けの直しは範囲外 — 既存の作りで、今回の受け入れ条件と関係しない
- [implement] `/simplify` の指摘のうち、改行コード（2 ファイルが CRLF→LF になっていた）を元に戻し、`organization_id` で渡し、古いコメントを直した。見送り: テストの補助 `precedes` の共通化（共通の置き場が無く既存の Dashboard のテストまで触る）・`ProblemSource` 単体のテストへの寄せ（AC は画面ごと）・import を `ProblemService` 経由にする／解説の表示を共通の部品に切り出す（計画の範囲を超える作り直し・retro の候補）・`full_clean`（試し実行の段階で弾く意図）
- [implement] 画面確認で、最後の問題に答えた後に上部の「正解 / 総回答」が増えないのを見た — 数え方の表示は今回変えておらず #333 の範囲。test-gate の手動テスト No.5 の期待はこれに合わせて扱う

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
