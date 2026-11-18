# I569 レビュー: イシューの番号の検査が 3 桁固定で、I1000 から流れ全体が止まる

## 変更概要
- 番号を受け付ける判定 8 か所（bash 5 本・見張り・開始時のフック・close のスキル）を「I＋数字 3 つ以上」にそろえ、3 桁固定の書き方を CI で止める走査のテストを足す

## 変更点
-（実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: ハーネスのスクリプト・フック・スキル・ハーネスのテスト

## テスト結果
- 自動:（review-gate で記入）
- 手動:（test-gate で記入）

## 計画との差分
-（実装後に記入）

## ロールバック
- この PR を revert する

## 自律判断の記録
- [plan] 再発を断つ仕組みは「8 か所を直す＋3 桁固定の書き方の走査を CI で毎回流す」にした。判定を共通の関数に寄せる案は、bash・Python・スキルの 3 種にまたがり覆えないため採らない — 言語によらず新しいファイルも止められる
- [plan] 走査の範囲から記録の場所（`docs/`）を外した — 記録は古い形を説明として書くもので、判定は無い（イシューの AC 3 の「closed の記録を除く」の読み替え）
- [plan] `.claude/skills/plan-issue/SKILL.md` のブランチ名の「イシュー番号3桁」を同梱した — イシューは I546 で直すとしていたが残っていた。同じ食い違いの 1 行
- [plan] 一覧（台帳の残り）は `I221.md` の F7 だけ同梱し、ほかは別の話なので残す（計画書 9）
- [plan-review] 計画レビューは Info 3 件だけで HIGHRISK（見張りの変更）。Info は計画書に理由が書いてあり直しは不要 — 方式・範囲を変えない
- [design-security-review] Blocker・High なし（Low 3 件・シナリオ Low 4 件はどれも計画の TC で覆う）。番号の確かめに上限の桁数は付けない — 数字だけでパスの外へ出られず、長い列はファイルが無いだけで害が無い

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement
