# I610 レビュー: フックの起動役の無視されるファイル・gate-check のリンクの見逃し・run-all の中のキャッシュ

## 変更概要
- フックの起動役は「変更があるか」を `unreviewed.py dirty` で判定し、フックを `python3 -I` で起こす（F24）
- `gate-check.sh` は `/dev/null` を指すリンクを汚れとして数える（F30）・G9b の向きを直す（F31）
- `run-all.sh` はキャッシュに書けないときだけ一時フォルダを使う
- 手順書に外と中の境目を動かすときの確かめを足す

## 変更点
- （implement 後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- フック: `.claude/hooks/reviewed-hook.sh`
- 関所・テスト: `scripts/claude/gate-check.sh`・`scripts/claude/tests/run-all.sh`・`scripts/claude/tests/i599_cases.py`・`scripts/claude/tests/test_i193_official_flow.sh`
- 文書: `docs/runbooks/plan-writing-rules.md`

## テスト結果
- 自動: （未実施）
- 手動: （未実施）

## 計画との差分
- なし

## ロールバック
- PR を revert する（データの変更なし）

## 自律判断の記録
- [plan] 起動役の「変更があるか」は `unreviewed.py dirty` を呼ぶ（シェルに git の確かめを写さない）— 定義を 1 か所にそろえるため
- [plan] `run-all.sh` のキャッシュは決定論テストにせず手動テストで確かめる — 壊れると手元のテストがすぐ落ちて気づけるため
- [plan-review] 計画レビュー（20261121_1727）は OK・高リスク判定 No。Warning 4 件・Info 1 件は計画とテスト文書で対応し、再レビューは省いた — TC の追加と前提の訂正だけで、方式・範囲・受け入れ条件は変えていないため。`-I` は保ち（`-P` にしない）、yaml が利用者の site にだけある環境で YAML のチェックが外れる点は R3 で受け入れた（この環境は共有の場所にあり外れないことを実測）
- [implement] /simplify の無駄・直す深さの観点の指摘で、フックの起動役の方式を「変更を判定して無ければ作業ツリー」から「いつも写し（作業ツリーは基準なし・写しを作れないときだけ）」に変えた — 毎回のツール呼び出しでの判定の手間（WSL で 1 回 0.2〜0.5 秒）が無くなり、定義の食い違いも判定ごと消えるため。方式の変更なので計画書を先に直し、計画レビューをやり直す

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
