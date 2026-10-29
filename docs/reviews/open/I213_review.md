# I213 レビュー: Dependabot を点検し、動いて役に立つ形に直す

## 変更概要
（実装後に記入）

## 変更点
（実装後に記入。計画書 docs/plans/open/plan_I213.md の 4 と対応させる）

## 影響範囲
（実装後に記入）

## テスト結果
（test-gate 段階で記入）

## 計画との差分
（実装後に記入）

## ロールバック
- PR を revert する（設定・ワークフロー・Dockerfile の書き方・文書の変更だけ。データの変更なし）。secrets `E2E_TEST_PASSWORD` は残すので戻せる。閉じた Dependabot の PR は開き直せる

## 自律判断の記録
- [plan] ハーネスの uv を Dependabot で見張らない（AC の読み替え） — Dependabot の uv 0.13.5 と I211 の「uv は 0.13.6 ぴったり」がぶつかり、ロックファイルの作り直しが毎回失敗する（スパイクで exit 2 を確認）。範囲にすると I211 の手元と CI の一致が崩れる
- [plan] 土台イメージを指紋で固定する（AC の追加） — Q4「同じ版の中の更新だけ Dependabot に任せる」は、タグだけでは Dependabot が PR にできない。指紋を併記すれば `--pull` も要らなくなる
- [plan] Playwright の 2 つの版を同じ PR で上げる設定は使わず、e2e のコンテナの起動時にブラウザを入れる — 公式の種類をまたぐまとめ方は動きが文書化されておらず試せない。起動時に入れる形は CI と同じ方法で、版がずれても動くことを確かめた
- [plan] `target-branch` を消す — 書くとセキュリティの修正の PR に設定が効かない（公式）。既定のブランチが develop なので宛先は同じ
- [plan] 書き間違いの検証に公式の `check-dependabot`（0.38.2）を使う — 誤りを 4 種とも止めた。0.39.0 は出て 3 日なので待つ日数に合わせて 1 つ前
- [plan-review] Warning 3 件（手動 No.4 の数・W2 の GITHUB_TOKEN・No.1 のテーブル名）は直し、計画レビューはやり直さない — 方式・範囲・受け入れ条件を変えない
- [design-security-review] 土台イメージの指紋固定で OS の修正の取り込みが最大で週 1＋7 日遅れるのを受け入れる — 再現性とタグの付け替えへの耐性を優先（OpenSSF の Pinned-Dependencies と同じ考え）。急ぐときは手で上げてよいと runbook に書く
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
