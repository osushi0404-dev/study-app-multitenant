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
- 自動: OK — review-gate がゲート 4 本を実走し全 exit 0・CI 全緑。test-gate に回された重いゲートは無い
- 手動: OK — M-01（push の回数: test-gate の時点で計 3 回・implement より後は 1 回）・M-02（新しいスキルの要所）を Claude が実施（Human の項目なし）

## 計画との差分
- 振る舞いの差分なし。節の置き場所・固定ファイルの作り直し・言い回しの整理は計画変更記録 2 のとおり

## ロールバック
- PR を revert する

## 振り返り

### かんたんなまとめ
良かった点
- 新しい決まりで I224 自身の review-gate から先を進められた（理由: 決まりを作ったその場で使い、push を前提にする確認〔CI 待ち〕が壊れていないことを実際に確かめられた。implement より後の push は review-gate の 1 回だけ）
- 手順書の書き方を戻してしまう事故を、テストで止める形にした（理由: push が増えても CI も画面も気づかないので、人の注意に頼れない）
- 変えた手順書を読む既存のテスト 17 本を、コミットの前に手元で流した（理由: 手順の写しを固定しているテストに、新しい節がぶつかるのをその場で見つけ、置き場所を変えて済ませられた）

今回の問題への直接の対処
- なし。レビューの残り 9 件（中くらい 2・軽い 7）は、どれも再現が無いか軽いので、決まりどおり軽い指摘の一覧に入れた。中くらいの 2 件（close の最後の確認の後に直したコミットが送られない・`/proceed` で最後の確認を流し直すと承認が取り消されうる）は、次に close・proceed を直すときに一覧から拾う

同じ問題を次回から防ぐ改善
- 新しい決まりは足さない。固定範囲とのぶつかりは既存のテストがその場で捕まえ、手戻りは置き場所の移動だけだった
- 受け入れ条件の残り（次のイシュー 1 本での push の回数）は、次のイシューの計画で測ることにして、マージ依頼の報告とメモリに残す

### 詳細
良かった点
- 新しいスキルで review-gate〜close を回し、M-01 で push の回数を実測（`docs/tests/open/I224_manual_test.md`）・決定論のテスト P1〜P4 と FG（`test_i224_push_points.sh`）・関係テスト 17 本の手元実行で固定範囲（`test_i185_harness_docs.sh`）とのぶつかりを実装中に発見

是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| （なし） | | | |

予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| （なし） | | | | |

見送り
- 「手順書に節を足すときは、固定しているテストの範囲を先に確かめる」を計画の決まりに足す: 見送り — 既存のテストがその場で捕まえ、手戻りは置き場所の移動だけ（2.7 の問 2）

5 Whys: 新しい節が手順の写しの固定範囲に入った
- Why 1: なぜ固定のテストが落ちたか → 新しい節を「## 記録とつなぎ」の直前に置き、そこが「## 止めて聞く条件」からの固定範囲の中だった
- Why 2: なぜその場所に置いたか → 内容が近い節の隣を選び、固定の範囲を見ていなかった
- Why 3: なぜ見ていなかったか → 固定の範囲はテストの中にだけ書かれていて、手順書の側からは見えない
- 根本原因: 手順書の一部をテストで固定していることが、手順書の側から見えない。ただし変えた手順書を読むテストを流す手順でその場で捕まり、手戻りは小さいので、新しい手順は足さない

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
- [review-gate] 新しい手順どおり最初に `git push` してから `code-review.sh` を流した（CI_WAIT: OK＝push を前提にする確認は壊れていない）。FINAL_VERDICT: OK・ADVERSARIAL_STAGE: NOT_REQUIRED（20261107_2228・ゲート 4 本 exit 0）。台帳の F1〜F9 は止める指摘でないので直さず retro へ — fix-loop が直すのは止める指摘だけ（I197）
- [test-gate] gate-check OK。M-01・M-02 を自分で行い OK。M-01 の最終の数（close の ③ の後）は close の報告に書く — close の後は記録に足さない決まり（新しい close の手順 6）
- [retro] 台帳の残りの振り分け: 後続イシューに回す行は 0 件。F1〜F9 → `docs/reviews/backlog/I224.md` — `code-review.sh --route` の結果に従った（F1・F2 は Medium だが再現なし）
- [retro] 予防処置は足さない — 固定範囲とのぶつかりは既存のテストがその場で捕まえた（2.7 の問 2）。受け入れ条件 3 の残り（次のイシュー 1 本での push の回数）は、マージ依頼の報告とメモリに残し、次のイシューの計画で測る

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
