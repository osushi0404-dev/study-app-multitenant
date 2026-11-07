# I224 レビュー: GitHub への書き込み（イシューの書き換え・コメント・push）の回数を絞り、短い間に集中しないようにする

## 変更概要
- push を要る 3 時点（下書き PR の作成・review-gate の CI 待ちの前・close の最後の確認の前）にまとめ、ほかの段階は手元のコミットだけにする
- イシュー本文の同期を grill-me の終わりの 1 回だけにする
- 同時に複数のセッションで書き込まない決まりを `workflow.md` に書く
- 押し戻しを決定論のテスト（`test_i224_push_points.sh`）で止める

## 変更点
- `docs/runbooks/workflow.md`: 新しい節「## GitHub への書き込みの時点（I224）」（push の 3 時点・ほかはコミットだけ・イシュー本文の書き換えは grill-me だけ・目安 4 回以内と測り方・同時に複数のセッションで書き込まない）。25・50 行目を合わせた
- スキル 10 本: 「commit/push」を「commit（push しない・正への参照）」に。`review-gate` の最初に `git push`。`close` は手順 3 のコミットに `STAGE_DONE: close NEXT: merge` を入れ、手順 6 はコミット・push しない。`proceed` の `merge` は依頼の前に `pr-base-sync.sh final` を流す
- `docs/runbooks/worktree.md`（82・251 行）・`docs/runbooks/plan-writing-rules.md`（230 行・同梱で 90 行の重複を整理）
- `scripts/claude/tests/test_i224_push_points.sh`（新規・P1〜P4 と FG）・`scripts/claude/tests/fixtures/i185/` の固定ファイル 2 つを作り直し
- `docs/reviews/backlog/I226.md`: 同梱した F2 の行を消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/` の 10 本・`docs/runbooks/workflow.md`・`docs/runbooks/worktree.md`・`docs/runbooks/plan-writing-rules.md`・`scripts/claude/tests/test_i224_push_points.sh`・`scripts/claude/tests/fixtures/i185/`・`docs/reviews/backlog/I226.md`

## テスト結果
- 自動: （test-gate で記入）
- 手動: （test-gate で記入）

## 計画との差分
- 振る舞いの差分なし。節の置き場所・固定ファイルの作り直し・言い回しの整理は計画変更記録 2 のとおり

## ロールバック
- PR を revert する

## 自律判断の記録
- [plan] 決まりの正を `workflow.md` の 1 節にし、スキルは参照だけにした — 写しを増やさない（I195）
- [plan] `STAGE_DONE: close NEXT: merge` を close の手順 3 のコミットに入れる — 結線のためだけの 4 回目の push を無くす
- [plan] PR へのレビューの記録のコメントは変えない — grill-me で決めた範囲（push・イシュー本文）の外で、PR でレビューを読む導線を変えるのは別の判断
- [plan] この I224 の plan-issue〜implement は古いスキルのまま進め、push は手順が許す範囲でまとめる（docs と STAGE_DONE を 1 回で送る）— 計画レビューを通す前に新しい決まりで動かない
- [plan-review] PLAN_VERDICT: OK（20261107_2215）。Warning 3 件・Info 1 件を計画書・テスト文書に反映し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけ（計画変更記録 1）
- [plan-review] 結線は commit だけで送らなかった（古いスキルは commit/push だが、次の review-gate の前に送ればよく、計画レビューを通った新しい決まりの先取り。中身の変更は無い）
- [implement] テストを先に書き、本体を直す前に落ちることを確かめてから直した — 新しいテストが false-green でないことを示すため
- [implement] `workflow.md` の新しい節を、`test_i185_harness_docs.sh` の固定範囲の外に置いた。固定している `plan-issue`・`fix-loop` の 2 か所はこのテストの決まりどおり `--update` で固定ファイルを作り直した — 意図した変更で、差分はレビューで見る
- [implement] /simplify の指摘のうち、スキルの言い直しの統一・close と proceed の説明の短縮・テストの写す範囲（primary で全ワークツリーを写さない）・テストの引数と判定の整理は直した。`code-review.sh` に自分で push させる案（範囲の外・今も決定論で止まる）・P4 を消す案（計画で残すと決めた）・同梱の重複の整理を外す案（計画の同梱）は見送った
- [implement] 手元では、変えたスキル・手順書を読むテスト 17 本だけを流した（全体は CI）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
