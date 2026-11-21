# I610 レビュー: フックの起動役の無視されるファイル・gate-check のリンクの見逃し・run-all の中のキャッシュ

## 変更概要
- フックの起動役は「変更があるか」を `unreviewed.py dirty` で判定し、フックを `python3 -I` で起こす（F24）
- `gate-check.sh` は `/dev/null` を指すリンクを汚れとして数える（F30）・G9b の向きを直す（F31）
- `run-all.sh` はキャッシュに書けないときだけ一時フォルダを使う
- 手順書に外と中の境目を動かすときの確かめを足す

## 変更点
- `.claude/hooks/reviewed-hook.sh`: 「変更が無ければ作業ツリー」の近道を消し、いつも BASE の写しで動かす（作業ツリーは基準なし・写しを作れないときだけ）。フックを起こす `python3` 4 か所に `-I`
- `scripts/claude/gate-check.sh`: ふさぎの印として数えないのを、リンクでない文字デバイスに絞る
- `scripts/claude/tests/run-all.sh`: `UV_CACHE_DIR` が無く既定の置き場に書けないときだけ `$TMPDIR/uv-cache`（無ければ `mktemp -d`）
- `scripts/claude/tests/i599_cases.py`: TC-12 を「変更なしも写し」に直し、TC-12b〜d と FG を足した。写しの場所・結果の確かめ・起動役の写しを壊す処理を関数（`snap_of`・`ran_in`・`launcher_variant`）にまとめた
- `scripts/claude/tests/test_i193_official_flow.sh`: G9b をリンクは汚れ（→ 1）の向きに直し、G9c（判定の差し替えで印の道）と FG を足した
- `docs/runbooks/plan-writing-rules.md`: 節「外と中の境目を動かす計画」

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
- [implement] 計画レビューのやり直しは、実装の途中の変更が「レビュー前の中身」として起動役に止められたので、`git stash push -u -m` で退避（SHA 9c58f2ee を控えた）→ レビュー → `git stash apply <SHA>` → タグで探し直して drop、で流した — 計画レビューは計画書しか読まないため。この先の review-gate はスクリプトをコミットした状態なので、ユーザーに `!` で流してもらう（I599 の決まり）
- [implement] /simplify で直したもの: 起動役の方式（上の行）・テストの写しの場所と結果の確かめの式を関数にまとめた・G9c と FG-G9b の同じ確かめを 1 本にした。見送ったもの: `gate-check.sh` で `/dev/null` と同じデバイス番号（1:3）かまで見る案（今の `! -L` で事故は止まる・任意）・`unreviewed.py` の git の呼び出しをまとめる案（起動役から呼ばなくなったので、毎回の手間ではなくなった）・中へ移るスクリプトをテストで中で流す仕組み（手順書の追記で今回は足りる・retro で要否を決める）・`run-all.sh` の書けるかの確かめを `[ -w ]` に簡単にする案（読み取り専用の bind での確かさを優先）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
