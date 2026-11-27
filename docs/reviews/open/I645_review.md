# I645 レビュー: 選択肢の記号（ア・イ・ウ・エ）と選んだ誤答の印

## 変更概要
- 選択肢に順番から「ア・イ・ウ・エ」の記号を本文と分けて出す（クイズの画面・問題管理のプレビュー・AI の問題作成の画面）
- 答えた後、選んだ誤答に赤い×の印と赤い文字を付け、正解・誤答の文字の色が disabled の灰色に負けないようにする

## 変更点
-

## 影響範囲
- Backend/Frontend/DB/Config: Frontend だけ（計画書 3）

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし

## ロールバック
- この PR を revert する（画面だけの変更）

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 記号の表は五十音の 46 字で、超えたら数字 — 選択肢の数に上限が無いため
- [plan] 選択肢の塊を `QuizChoices` に切り出す — `QuizSession.tsx` が 721 行で、React 規約 §4 に照らして書き直す部分だけを分ける
- [plan] 色は `.Mui-disabled` のセレクタにも書く（`!important` なし） — MUI 5 の disabled の指定（クラス 3 つ）と同じ強さで勝つため
- [plan] 入力に `aria-label`（記号＋本文）を付ける — 読み上げで記号を分けて伝え、テストの名前を表示の形に頼らせないため
- [plan] 色の勝ち負けは E2E（TC-08）で確かめる — jsdom はセレクタの強さによる上書きを正しく計算しないため
- [plan-review] Warning 4 件・Info 2 件を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけのため
- [implement] 単一選択でラジオの文字の値から元の id の選択肢を探して渡す — E2E で、API の数字の id と比べられず誤答の印も色も出ないと分かった（計画書の調査結果 10・TC-04b）
- [implement] ダークモードの誤答の赤は `error.light` — `error.main` はダークモードのカードの背景に 3.94:1 で、決まりの 4.5:1 に届かなかった（調査結果 11）
- [implement] 色はラベルの中の自前の要素に直接書き、行の組み立てを 1 つにまとめる — /simplify の点検。MUI の内部のセレクタの強さに頼らない
- [implement] /simplify の指摘のうち、`Choice.id` の型を `number` にそろえる直し（frontend の型と API の食い違い・約 13 か所）はこのイシューでは見送る — 受け入れ条件の外で範囲が広い。retro で起票を判断する
- [implement] /simplify の指摘のうち、問題の編集画面の入力欄のラベル「選択肢 A」（`QuizManagement.tsx:842`）は直さない — 入力欄の名前で、E2E（`auth.spec.ts:96`）が使っている。イシューの範囲（表示の記号）の外
- [implement] 私の書き換えで CRLF から LF に変わった `ProblemPreview.tsx` の改行コードを CRLF に戻した — /simplify の指摘。差分を実際の変更の 3 行にするため
- [implement] ダークモードの「解説」の枠が明るい灰色のままで文字が読みにくいのを画面確認で見つけた — 変更前からあり、このイシューの範囲外。retro で扱う
- [implement] 記号の表を文字列にして `charAt` で取り出す — ビルドの ESLint のセキュリティの規則に当たったため。無効化のコメントは足さない
- [implement] 複数選択の行にも `data-testid="choice-option"` を付け、部品のテストは行を分割代入で受け取る — pre-commit の ESLint（`no-node-access`・`detect-object-injection`）に当たったため。無効化のコメントは足さない。書き換えた後も、×の印を外した版で TC-04・TC-06 が落ちることを確かめ直した
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
