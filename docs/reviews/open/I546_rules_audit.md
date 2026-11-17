# I546 点検の結果の表（進め方の決まり: docs/runbooks・CLAUDE.md・記憶）

- 点検した日: 2026-11-17（公式の文書を照らした日も同じ）。点検した版: `feature/I546-process-rules-bp-review`（53436302）
- 作り方: 対象を 5 つに分け（A 流れ・B 計画とレビュー・C 安全と依存・D 準備と環境・E 記憶）、点検役が節ごとに判定と根拠（公式の文書の URL・照らした日、または「内部: 理由」）を出した。下の「§0 確定」は、点検役の案を Claude が突き合わせて決めた結果で、§1 以降の各表より優先する（食い違うところは §0 が正）
- 公式の文書の置き場所: Claude Code の文書は `docs.anthropic.com/en/docs/claude-code/` から `code.claude.com/docs/en/` に移っている（点検 A の注）

## §0 確定（点検役の案との違いと、案どうしの食い違いの決め方）

### 0.1 正の置き場所の決定（案どうしで分かれたもの）
| 決まり | 決めた置き場所 | 理由 |
|---|---|---|
| ローカルで E2E を流す手順（レート制限の外し方を含む） | `docs/runbooks/frontend-verify.md` §8（`common-commands.md` は 1 行の参照） | 中身が I187 で確かめた正しい方で、スキル・テストが frontend-verify.md を参照している（点検 C の案。点検 D の「common-commands を正に」は採らない） |
| Bash の書き方（束ねない理由・サンドボックスの外に出る条件） | `docs/runbooks/danger-ops.md`「サンドボックス（第 1 層・I430）」（`common-commands.md`「Bash 実行作法」は消す） | 理由が今はサンドボックスの外に出るかどうかで、公式の文書（sandboxing・permissions）と合う形で 1 か所に書ける（点検 C・E） |
| イシューの番号・置き場所 | `docs/runbooks/issue-flow.md`「イシューの番号と置き場所（I221）」 | 原則「issue-flow.md=イシューの扱い」（点検 A） |
| 外部（fork）の PR の扱い | `docs/runbooks/danger-ops.md` | 安全の話（点検 A） |
| 計画を変えたら plan-review を通り直す | `docs/runbooks/workflow.md`「ゲート」。`review-rules.md` の文は `test_i181` D10 が見るので参照の文に直してテストも直す | 流れのゲートの決まり（点検 B・E） |
| 計画書・レビュー文書の形（基本情報・調査結果・修正アプローチ・計画変更記録・自律判断の記録・Danger Ops の 4 項目） | `docs/plans/templates/plan_template.md`・`docs/reviews/templates/review_template.md` | 毎回手で足している節の形の正をテンプレートに（点検 B・C） |
| 記憶から移す決まり | 点検 E の表の「移す先」。ただし点検 E が `plan-writing-rules.md`「より良い方法の検討」に置くとした 2 件（テストの差し替えより設計・公式の機能を土台に）は、その節を消すので「計画書作成前の事前調査」と「6) テスト計画」の行に置く | 消す節に足さない |

### 0.2 点検役の案から変えたもの
- `worktree.md` §2 の確認 1（`git remote set-head origin --auto`）は残す。公式の `worktree.baseRef: "fresh"` で要らなくなるかは推測で、#427 で確かめてから消す（確認 2 と版の注記だけ消す）
- `docs/claude-code-structure.md` は消さない（テスト 2 本が読み、I545・I430 でも直している）。今回の書き換えで食い違う行（legacy・template-sync・旧いレビューの命名・「9 承認ポイント」・計画書の節の説明）だけ直す
- `README.md` の「バイブコーディング運用（Claude Code）」の 11 行は、段階のスキルをユーザーが打つ古い流れを書いていて害がある。`CLAUDE.md` と `docs/runbooks/workflow.md` への参照 2 行にする（範囲を広げる自律判断。AC2 の「ファイルをまたいで違う内容で書いた箇所が無い」のため）
- 文書の文字を見ているテスト（`scripts/claude/tests/` の i107・i179・i181・i185・i193・i202 と fixtures）は、消す節・移す節に合わせて同じ PR で直す。消した節の文字だけを固定している項目は、期待値を書き換えるより項目ごと消す（`plan-writing-rules.md`「決定論テストの対象の選び方」: 意図的な変更でしか消えない文言はテストにしない）。仕組み（スクリプトの動き）は変えない
- `.secrets.baseline` の legacy の項目は触らない（止めて聞く条件 2 の安全装置。項目が残っても害は無い）。commit の前のフックが自動で書き換えた場合は計画変更記録に書き、高リスクの扱い（必ず確かめる項目・計画レビューのやり直し）にする

### 0.3 実装の前にユーザーに 1 度だけ確かめる中身の変更（設計確認メモ・解決方針 9）
| 番号 | 変更 | 確認の場面・承認の対象 | 推奨 | 理由 |
|---|---|---|---|---|
| U1 | ラベルで迷ったらユーザーに確認、を消す（`issue-flow.md`）。代わりに「主目的の側に付け、理由を報告に 1 行」 | 減る | 消す | ラベルはいつでも付け直せ、止めて聞く条件のどれにも当たらない（「この 3 つだけ」と食い違う） |
| U2 | 起票の前に聞く 3 つ（`workflow.md`「Claude が会話の中で起票するとき」）のうち「価値が低いか迷う」を消す。残り 2 つは止めて聞く条件 1 の場面として参照を付ける | 減る | 消す | 記憶の「価値の低いもの以外は確認なしで起票」と同じ。条件 1 と食い違わない形にする |
| U3 | ブランチ作成に失敗したらユーザーに報告・提案、を消す（`issue-flow.md`） | 減る | 消す | 直せるものは Claude が直して記録する（止めて聞く条件 3 の扱いに寄せる） |
| U4 | ブランチ作成の例外（文書だけ・1 行の修正・指示があれば直 commit 可）を消す（`workflow.md`） | 変わらない（守りは厳しくなる側） | 消す | 絶対ルール 3 と矛盾し、GitHub の保護で実際にもできない |
| U5 | 「大規模 rebase」を危険操作の例から外し、「rebase の前に commit しておく（reflog・GitHub から戻せる）」にする（`danger-ops.md`） | 減る | 外す | 同じファイルで「見張りは判定しない・戻せる」と書いていて食い違う。戻せる操作に承認を重ねない（GitHub が最後の守り）。強制 push は危険操作のまま |
| U6 | 危険操作の条件から「PR に `danger-approved` のラベル」を外し、「計画書の Danger Ops 欄＋ユーザーの明示の承認（記録に残す）＋実行時の `DANGER_OK=1`（見張りが承認画面を出す）」の 3 つにする（`danger-ops.md`・`workflow.md`・`CLAUDE.md`） | 減る（人の承認そのものは残る） | 外す | ラベルを確かめる仕組みがどこにも無い（ワークフロー・スクリプトに 0 件）。誰も確かめない手順は守られているか分からない |
| U7 | `E2E Tests (Playwright)` を develop・main の必須チェックに足す（GitHub の設定画面・ユーザーの操作）。足さないなら `onboarding.md` の「全部 pass しないとマージ不可」を事実（E2E は Claude の review-gate が待つ）に直すだけ | 増える（E2E が赤だとマージボタンが押せない） | 足す | review-gate はもともと E2E を待つので運用は変わらず、人が赤いままマージする事故だけを止める。E2E が不安定なときは止まるのが欠点 |

**ユーザーの答え（2026-11-17）**: U1〜U7 すべて推奨どおり（返答「はい」）。U7 の GitHub の設定はユーザーが画面で行う（マージ依頼で依頼する）

### 0.4 一覧（`docs/reviews/backlog/`）の扱い
計画書 §9 に 1 行ずつ書く。

---

以下は点検役の結果（A〜E）そのまま。

# I546 点検 A: CLAUDE.md・workflow.md・issue-flow.md・worktree.md

- 点検日: 2026-11-17（公式の文書を照らした日付も同じ）
- 点検した版: ブランチ `feature/I546-process-rules-bp-review`（HEAD 53436302）
- 照らした公式の文書（すべて 2026-11-17 に取得）:
  - [M] https://code.claude.com/docs/en/memory （CLAUDE.md の大きさ・矛盾・`/doctor prompt-audit`・「CLAUDE.md は強制ではない」）
  - [W] https://code.claude.com/docs/en/worktrees （`--worktree`・終了時の片付け・ロック・掃除・`worktree.baseRef`・分離の仕組み）
  - [S] https://code.claude.com/docs/en/skills （`user-invocable`・`disable-model-invocation`）
  - [B] https://code.claude.com/docs/en/best-practices （CLAUDE.md は短く・コードから分かることは書かない・例外の無い決まりは hook/deny へ・強制の数は少なく）
  - [G] https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue （closing keyword は既定ブランチ宛ての PR だけで効く）
  - 注: 依頼文の docs.anthropic.com/en/docs/claude-code/ は今は code.claude.com/docs/en/ に移っている（取得したのは移った先）
- 確かめた設定・スクリプト: `.claude/settings.json`（hooks・sandbox・deny）・`scripts/claude/hooks/pretooluse_guard.py`・`posttooluse_check.py`・`sessionstart_context.py`・`code-review.sh`（`path_risk_trigger`・`CI_WAIT: NOT_PUSHED`）・`pr-base-sync.sh`・`flow-stage.sh`・`gate-check.sh`・`.claude/skills/*/SKILL.md` の frontmatter・`close/SKILL.md`・`refs/remotes/origin/HEAD`（= origin/develop）
- 記号: 「推測」と書いたものは確かめていない

---

## 表1 節ごとの判定

### CLAUDE.md（57 行）

| ファイル | 節（見出しの文字のまま） | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| CLAUDE.md | （1 行目の前置き） | 消す | `This file provides guidance to Claude Code (claude.ai/code) …` を消す（`/init` の定型文。中身が無い）。-2 行 | [B]「コードから分からないことだけ書く」 | - | - |
| CLAUDE.md | # Claude Code 運用（プロジェクト憲法） | そのまま | - | - | - | - |
| CLAUDE.md | ## プロジェクト概要 | 直す | 8 行目「Claude Code（Cursor 経由）に実装を委任します。」→「Claude Code（端末・IDE の拡張のどちらでも）に実装を委任します。」（設計確認メモで確定の方針）。9 行目の流れの 1 文は残す（いつも読み込まれる唯一の場所なので要約として価値がある）。行数は同じ | 内部: 今は WSL・tmux の端末でも動かしている（I546 背景） | CLAUDE.md | - |
| CLAUDE.md | ## 0. 参照先（このファイルは短く保つ） | 直す | 一覧は残す。①「イシューフロー」の説明を「イシューの扱い（番号・置き場所・起票・ラベル）」に変える（issue-flow.md を下の提案どおり絞った場合）②`docs/runbooks/legacy/` の扱いが決まったら触れない（今も触れていない）。③`/doctor prompt-audit` の存在は書かない（#427 へ回す）。±0 行 | [M]「矛盾は定期的に見直す」 | CLAUDE.md | #427（`/doctor prompt-audit` で定期点検を置き換えられるか） |
| CLAUDE.md | ## 1. 絶対ルール（破ったら中断） | そのまま（中身）／言い回しだけ直す | 2) の括弧の 3 条件の要約は残す（CLAUDE.md だけが毎回読み込まれ、workflow.md は読み込まれないため。テスト D5 も「止めて聞く条件」の文字を見る）。4) の例の列挙は danger-ops.md が正なので「（例と承認の手順は docs/runbooks/danger-ops.md）」を足すだけ。見出しの「破ったら中断」は残す（下の注）。+0〜1 行 | [B]「例外の無い決まりは hook・deny・managed settings へ。CLAUDE.md は guideline」→ 3) は GitHub の保護・4) は見張り（DANGER_OK）で強制済み。1) 計画外の実装をしない は強制が無い（gate-check は test-gate・close でだけ見る）。文書は「自動で止める」とは書いていないので食い違いではない | CLAUDE.md（要約）＋ workflow.md（3 条件の本体）＋ danger-ops.md（危険操作の本体） | - |
| CLAUDE.md | ## 2. 使うスキル（/ で実行） | 直す | 見出しと 1 行を「## 0. 参照先」の運用・ルールの一覧の 1 行（「使うスキルと呼び方: workflow.md「使うスキル」」）にまとめて節を消す。-3 行 | 最適化（1 行のための節） | workflow.md | - |
| CLAUDE.md | ## 3. 権限と二重ガード | 直す | 見出しを「## 3. 権限と守り」に（今はサンドボックス・見張り・GitHub の保護の 3 層で「二重」が古い）。4 行目に「最後の守りは GitHub のブランチ保護（docs/runbooks/branch-protection-setup.md）」を 1 行足す。中身は settings.json と一致を確認済み（PreToolUse: Edit/Write/MultiEdit/NotebookEdit・Bash・playwright、PostToolUse: Edit/Write、sandbox enabled）。+1 行 | 内部: I430 でサンドボックスを第 1 層にした。[B]「強制は hook・deny・sandbox」 | CLAUDE.md（索引）・danger-ops.md（本体） | - |

### docs/runbooks/workflow.md（256 行）

| ファイル | 節（見出しの文字のまま） | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| workflow.md | # Vibe Coding 運用フロー（公式の道具を土台にした自律の流れ・I193） | 直す | 「# 運用フロー（イシューの流れ・段階・止めて聞く条件）」に。「Vibe Coding」は中身を表さない。±0 | 最適化 | - | - |
| workflow.md | ## 使うスキル（ユーザーが / で打つもの） | 直す | 4 行目（/issue-bootstrap の説明・約 300 字）を 1 文に縮める（下書き→issue-review→登録、詳細は issue-bootstrap スキルと issue-flow.md）。9・11 行目はそのまま（公式と一致: `user-invocable: false` は `/` に出ず Claude は呼べる [S]）。-0（行は同じで字数が半分） | [S] 表「user-invocable: false → You: No / Claude: Yes」と一致 | workflow.md | - |
| workflow.md | ## ディレクトリ規約 | そのまま | - | - | workflow.md | - |
| workflow.md | ## フロー | そのまま（正の置き場所にする） | 段階の流れの正をここ 1 か所にする（issue-flow.md の「イシューフロー（統合ルール）」を消す前提）。36 行目「詳細なイシューフローは issue-flow.md」を「イシューの番号・置き場所・起票は issue-flow.md」に直す。28 行目の「（pytest・Jest・E2E は CI が正で、手元では流し直さない）」は記憶 feedback_no_local_full_tests の正としてここを使う。±0 | 最適化（同じ流れが issue-flow.md の 70 行の図と 2 か所にあり、そちらは古い） | workflow.md | - |
| workflow.md | ## 止めて聞く条件（この 3 つだけ・各スキルはここを参照する） | そのまま（中身）／重複の整理は下 | 条件 2 の安全装置の集合は `code-review.sh` の `path_risk_trigger` と一致を確認済み（テスト S12 もある）。中身の変更案は表4（起票の節・ラベルの節などに「3 つだけ」と合わない確認の場面が別にある） | 内部: テスト S12・D4 | workflow.md | - |
| workflow.md | ## 記録とつなぎ（決定論） | そのまま | 見出しは test_i185 の抜き出しの終わりの目印なので変えない | - | workflow.md | - |
| workflow.md | ## イシューの置き場所（I221） | 消す（移す） | 本文 7 行をそのまま issue-flow.md の「## イシューの番号と置き場所」へ移し、ここは 1 行の参照にする（原則: issue-flow.md=イシューの扱い）。参照している 9 行を直す（表5）。-6 行 | 最適化（3 か所に書かれている: ここ・issue-flow.md:7・worktree.md §8） | issue-flow.md | - |
| workflow.md | ## GitHub への書き込みの時点（I224） | そのまま | 見出しは test_i224 が見る。72 行目の「目安 4 回以内」は残す | - | workflow.md | - |
| workflow.md | ## ゲート | 直す | 78・79 行目（Danger Ops・直 push）は CLAUDE.md 絶対ルール 3・4 と同じなので消す。80 行目（スコープ変更時に写しを直す）は issue-flow.md へ移す節と重なるので消す。77・81 行目だけ残し、下の「修正ツール使用前チェック」をここに吸収（「実装の前に: 計画書がある・plan-review を通った・変更が計画書に書いてある」1 行）。-2 行 | 最適化（CLAUDE.md・plan-writing-rules.md:265 と三重） | workflow.md（計画レビューの関所）・CLAUDE.md（直 push・危険操作） | - |
| workflow.md | ## スキル呼び出しルール | そのまま | 88 行目「呼んでも `flow-stage.sh` と `gate-check.sh` が順番を外れた進行を止める」は実際と一部合わない（下の #520）。文言は #520 の結論で直す | [S] `user-invocable: false` でも Claude は呼べる＝強制ではない | workflow.md | #520 |
| workflow.md | ### Claude が会話の中で起票するとき（I220） | 直す | 95〜98 行目の「起票する前に聞く 3 つ」は「止めて聞く条件（この 3 つだけ）」と食い違う（1 つ目・2 つ目は 3 条件に無い）。中身の変更なので表4。言い回しは表4の結論に合わせる。100 行目は残す | 内部: 同じファイルの中の矛盾 | workflow.md | - |
| workflow.md | ### 各段階で止まったときの案内 | そのまま | 見出しは test_i185 のフィクスチャの始まりの目印 | - | workflow.md | - |
| workflow.md | ## 移行（I193 のマージ前に着手したイシュー） | 消す | 節ごと消す。I193 のマージ（2026-10 下旬）より前に着手して進行中のイシューは無い（推測: develop の docs/plans/open に I031〜I047 の古い計画が残るが、これらは放置されたもので、もし `/proceed` しても `flow-stage.sh` が STAGE_DONE 無しで exit 2 で止める＝文書が無くても安全）。-5 行。**test_i193 D6 と test_i185 の抜き出しの終わりの目印「## 移行」が壊れる**（表5） | 最適化（役目を終えた移行の記録） | -（git の履歴） | - |
| workflow.md | ## Claude Code実行ルール | 消す | 「コマンド実行前に必ず説明する」は公式の Bash ツールが `description` を必須にしており、auto モードで自律に進める今の流れでは毎回の日本語の前置きは冗長。「ロジック修正提案時に必ず説明する（意図・問題点・改善内容）」は、自律の流れでは提案ではなく「自律判断の記録」と計画書の背景に書くので、計画書の書き方（plan-writing-rules.md の背景/目的）に既にある。-11 行 | [B]「Claude がもう正しくやることは書かない」「every line takes attention」 | plan-writing-rules.md（背景/目的）・workflow.md（自律判断の記録） | - |
| workflow.md | ## 作業実行前の確認ルール | 消す | 1〜5 の手順は「## フロー」の言い換え。計画書の名前（`plan_I###_2.md`）は plan-writing-rules.md:233・review-rules.md:12 にある。-9 行 | 最適化（重複） | workflow.md「フロー」・plan-writing-rules.md | - |
| workflow.md | ### 修正ツール使用前チェック（必須） | 消す | 「ゲート」に 1 行で吸収（上）。`MultiEdit` の語は消す（今の公式の文書の worktrees の分離の説明は Edit・Write・NotebookEdit だけを挙げる [W]。推測: MultiEdit は今の版に無い。settings.json の matcher に残るのは害が無いので触らない）。-6 行 | CLAUDE.md 絶対ルール 1・plan-writing-rules.md:265 と三重 | CLAUDE.md・plan-writing-rules.md | - |
| workflow.md | ## ブランチ戦略 | 直す | 下の小節を整理して約 90 行→約 30 行 | 下 | workflow.md | - |
| workflow.md | ### 基本方針: 3ブランチ戦略（本番環境対応版） | 直す | 「本番環境（AWS）」→「本番（まだ無い。用意したらリリースに使う）」。hotfix は「本番ができてから」。命名規則の「イシュー番号3桁」→「イシュー番号（I546 なら I546）」（GitHub の番号は 1000 を越える。表3）。-3 行 | 内部: 本番環境はまだ無い（記憶 project_no_production_env・11-17） | workflow.md | - |
| workflow.md | ### 現在のブランチ確認 | 消す | `git branch --show-current` の確認と「警告を出す」は、ブランチは /plan-issue が作り gate-check が HEAD を見るので不要。-6 行 | [B]「Claude がもう正しくやることは書かない」 | - | - |
| workflow.md | ### イシュー完了時のマージフロー | 消す | 「ステップ25 でマージ」「マージ後にレビューファイルを closed に移動」は今の close 段階（記録を closed へ移してから Ready・マージ依頼）と**逆の順**で矛盾。-7 行 | 内部: close/SKILL.md step 1→5 の順 | workflow.md「フロー」5・close スキル | - |
| workflow.md | ### 本番リリースフロー（重要） | 直す | コマンド 3 つは残す。「重要な注意事項」4 行のうち「週1回、月1回等」は本番が無い今は根拠が無いので消す。onboarding.md:173 がこの見出しを参照しているので見出しの文字は変えない。-3 行 | 内部 | workflow.md | - |
| workflow.md | ### 緊急修正（hotfix）のブランチ運用 | 直す | 227・228 行目が同じ文の繰り返し（「mainとdevelop**両方**にマージすること」）→ 1 つに。「テストは迅速だが確実に実施」など中身の無い行を消す。手順 3「GitHub の PR 画面の Delete branch でブランチを消す」は GitHub の設定「Automatically delete head branches」で置き換えられる（#427）。-4 行 | 最適化 | workflow.md | #427（head ブランチの自動削除の設定） |
| workflow.md | ### ブランチ作成例外ルール | 消す | 「ドキュメントのみ・1 行修正・ユーザーの指示ならブランチを省略可」は CLAUDE.md 絶対ルール 3（直 push 禁止・イシューごとにブランチ）と矛盾し、GitHub の保護で実際にもできない。「イシューファイル作成依頼の場合は必ずブランチ」は I221 で手元にイシューファイルを作らなくなったので古い。-7 行。中身（例外を無くす）に当たるので表4にも載せる | 内部: 絶対ルール 3・branch-protection-setup.md | CLAUDE.md 絶対ルール 3 | - |
| workflow.md | ## 外部（fork）からの PR の扱い | 消す（移す） | 手順 1〜5 を danger-ops.md へ移す（外部の PR の扱いは安全の話で、danger-ops.md:34・39 に既に半分ある）。254〜256 行目は danger-ops.md:34 と同じ内容なので移す先で 1 つにする。close/SKILL.md:22 の参照を直す（表5）。ここは 1 行の参照に。-16 行 | 最適化（danger-ops.md:34・branch-protection-setup.md:67 と三重） | danger-ops.md | - |

### docs/runbooks/issue-flow.md（356 行）

| ファイル | 節（見出しの文字のまま） | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| issue-flow.md | # イシューフロー | 直す | 「# イシューの扱い（番号・置き場所・起票・ラベル）」に。3〜4 行目は「段階の流れは workflow.md「フロー」が正」の 1 行に。-1 行 | 原則: issue-flow.md=イシューの扱い | - | - |
| issue-flow.md | ## イシューの番号と置き場所（I221） | 直す（正の置き場所にする） | workflow.md「イシューの置き場所」の 7 行を移して、ここを正にする。7 行目の「workflow.md が正」の文は消す。worktree.md §8 の 2 行もここへ（I426 以下のファイルは起票したワークツリーで扱う）。+6 行 | 最適化 | issue-flow.md | - |
| issue-flow.md | ## イシュー作成時の自動実行フロー（必須） | 直す | 手順 1〜4（コマンドと報告の雛形 ✅🔗⚠️）は issue-bootstrap スキルの写しなので消す（スキルが手順の正）。残すのは決まりだけ: ①起票は issue-bootstrap スキルで行う ②**ラベル 2 軸の決まり（ここを正にする）**: 種別 4 つ・トラック（`.github/` を含む今の 20 行目の版を正にする）。「判断に迷う場合はユーザーに確認」は表4。-15 行 | 最適化（issue-bootstrap/SKILL.md:18〜・64〜65 と二重） | issue-flow.md（ラベル）・issue-bootstrap スキル（手順） | - |
| issue-flow.md | ## イシューフロー（統合ルール） | 消す | 節ごと（38〜323 行・約 285 行）消す。理由: ①段階の流れは workflow.md「フロー」と各スキルが正で、ここは古い写し（番号が 1・1.5・2・3・5・6…と飛ぶ）②**フェーズ4 が close 段階と矛盾**: マージ（25）の後にレビューを closed へ（26）・`mv`（close は `git mv`）・`gh issue close` を手で（close は PR 本文の `Closes #N` で、既定ブランチが develop なので自動で閉じる [G]）・「完了情報」を echo で足す・`error_IXXX.md`（どのスキルも作らない）③ステップ8 の「実装結果評価セクション」は今のレビューのテンプレートに無い（`git grep 実装結果評価` は issue-flow.md だけ）。残す価値のある 1 行だけ移す: 「元の計画書を上書きしない（計画変更記録に追記か `_2`）」→ plan-writing-rules.md:233 に既にあるので移すものは無い。**tests の i107・i179 D6・i185（フィクスチャ 2 本）・i202 N13 が壊れる**（表5）。-285 行 | [G]「closing keywords は既定ブランチ宛ての PR だけで効く」・`git symbolic-ref refs/remotes/origin/HEAD` = develop・close/SKILL.md:107 `Closes #...` | workflow.md「フロー」・各段階のスキル | - |
| issue-flow.md | ### フロー図 | 消す | 上に含む | 同上 | 同上 | - |
| issue-flow.md | ### 各ステップの詳細（#### フェーズ1〜4・ステップ15-18 を含む） | 消す | 上に含む | 同上 | 同上 | - |
| issue-flow.md | ### 重要な注意事項 | 消す | 上に含む（1・2 はテンプレートに無い節の話・5・6 はエラー管理ファイル・7・8 は close と逆の順） | 同上 | 同上 | - |
| issue-flow.md | ## イシュー対応中のブランチ運用 | 消す | 下の 3 小節を消す。-30 行 | 下 | - | - |
| issue-flow.md | ### コミット時のルール | 消す | 例の「イシュー#XXX」は実際の形（`docs(I545): …`・`close(I545): …`・`fix(I545): …`）と違う。Claude は git log から形を読むので書かない（または 1 行「コミットの題は `<種類>(I###): 内容`」だけ残す。残すなら workflow.md「ブランチ戦略」へ） | [B]「コードから分かることは書かない」・`git log origin/develop` | workflow.md（残すなら 1 行） | - |
| issue-flow.md | ### イシュー対応時の必須ルール | 消す | 1（本文を読む）は plan-issue スキルがする。2・3（コーディング規約）は CLAUDE.md「コーディング規約（必読）」と同じ。4 は plan-writing-rules.md 13) と同じ。6 は workflow.md「止めて聞く条件」と同じ | 最適化（三重） | CLAUDE.md・plan-writing-rules.md・workflow.md | - |
| issue-flow.md | ### ブランチ作成失敗時の対処 | 消す | 「ユーザーに報告・原因を説明・対処を提案」は自律の流れ（直せるものは Claude が直す）と合わない。表4 | 内部: 止めて聞く条件 | workflow.md「止めて聞く条件」 | - |

### docs/runbooks/worktree.md（282 行）

| ファイル | 節（見出しの文字のまま） | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| worktree.md | # worktree ベースの並行作業運用（前置き 3〜7 行） | そのまま | 7 行目の公式の URL は今も有効（取得できた） | [W] | worktree.md | - |
| worktree.md | ## 1. 用語 | そのまま | - | - | worktree.md | - |
| worktree.md | ## 2. ワークツリーの作り方（公式 `claude --worktree`） | 直す | ①確認 2（`.worktreeinclude`・`_owning_root` の grep）と 47 行目後半の「I179 より前に作られたブランチを primary で使っている間は…」を消す（I179 は 10 月にマージ済み・primary は開始時に develop へ自動で早送りされる）。-4 行 ②確認 1（`git remote set-head origin --auto`）は公式が「fresh のときは 24 時間ごとに既定ブランチを fetch して origin/HEAD を新しく保つ」と書くので要らなくなった可能性がある（推測。set-head までするかは文書から読み切れない）→ #427 で確かめる。test_i179 D3 がこの文字を見る ③51 行目「変更が無いワークツリーは確認なしで自動的に片付けられる」→公式は「名前の無いセッションは自動で消す・名前付きのセッションは聞く・自分以外のブランチにコミットがあれば聞く」。/plan-issue の後は feature ブランチにコミットがあるので聞かれる。言い換え: 「変更もコミットも無いときだけ自動で消える（名前付きのセッションでは確認が出る）」④52〜53 行目のロック: 公式は「`-p` のロックは、後のセッションの古いロックの掃除が外す」「終了したプロセスのロックは掃除が外す」。「ロックが残る場合がある」を「後のセッションが自動で外す。待てないときは wt-remove.sh」に ⑤54 行目「サブエージェントの入れ子は…ロックは付かない」→公式は「動いている間はロック・終われば外す・変更のあるものは `cleanupPeriodDays` を過ぎて作業が無くなれば掃除で消える」⑥57〜59 行目の Cursor の記載を一般化: 「IDE（VS Code・Cursor など）では、ワークツリーごとに新しいウィンドウで開く（例: `code -n <パス>`。既に開いているフォルダを開き直しても新しいウィンドウにならない）」の 2 行に。-2 行 ⑦50 行目の信頼の確認は公式と一致（「`-p` は信頼の確認を飛ばす」を足すと正確） ⑧「（2.1.304 で確認）」などの版の注記は消す（公式の文書が正・版は古くなる）。計 -8 行 | [W]「Clean up worktrees」「Worktree locks and manual removal」「Choose the base branch」「Start Claude in a worktree」 | worktree.md | #427（確認 1 の set-head と、wt-remove.sh のロックの扱いを公式の掃除で置き換えられるか） |
| worktree.md | ## 3. 次のイシューへ移る（同じワークツリーで続ける） | そのまま | 見出しの番号は plan-issue/SKILL.md:25・issue-flow.md:138 が「§3」で参照 | - | worktree.md | - |
| worktree.md | ## 4. 撤去 | 直す | 105〜114 行目（wt-remove.sh の中の判定の説明・約 10 行の長い段落）を「止まったときはスクリプトの出力に従う。止まる理由: 未コミット・未 push・中の入れ子・使用中のロック・消す相手が決まらない・docker が使えない」の 3〜4 行に縮める（スクリプトの出力が手順を出す・wt-remove.sh:73・157・191・196・204 で確認）。107 行目の「登録の無い .git」の手当ては残す（気づきにくくデータが消える）。「止まったときの片付け」「取り残しの発見と削除」は残す（人が手で消す手順で、他のワークツリーのデータを消す事故を防ぐ）。-12 行 | [B]「コードから分かることは書かない」・スクリプトの停止メッセージ | worktree.md（手で消す手順）・wt-remove.sh（判定） | - |
| worktree.md | ## 5. Docker を使う場合のセットアップ | 直す | (D) は §4 と同じなので 1 行に。(B)(C) は残す（静かに壊れる・気づきにくい）。-1 行 | 最適化 | worktree.md | - |
| worktree.md | ## 6. 並行実行のポート分離（同時起動可能・I097） | 直す | 188・189 行目の例の `wt-ports.sh && docker compose up …` を 2 つのコマンドに分けて書く（記憶 feedback_atomic_allowlisted_commands・danger-ops.md:26「git は他のコマンドとつながない」と同じ方向。束ねると許可の一致・サンドボックスの外に出る判定が崩れる）。±0〜+2 行 | 内部: danger-ops.md:26 | worktree.md | - |
| worktree.md | ## 7. 共有されるもの / されないもの | 直す | ①226 行目「Windows 側エクスプローラや Cursor のパス表示」→「Windows 側のエクスプローラーや IDE のパス表示」②211 行目の git stash の決まりは残す（Claude Code 本体のシステムの指示にも同じものがあるが、人と他の道具にも効かせるため）③公式の「Permission approvals: worktree で "don't ask again" を選ぶと main checkout の `.claude/settings.local.json` に保存され全ワークツリーに効く」を「共有される」に 1 行足す（記憶 reference_worktree_permissions_from_main の正をここに）。+1 行 | [W]「What worktrees share with the main checkout」 | worktree.md | - |
| worktree.md | ## 8. イシューの番号（I221） | 消す（移す） | 2 項目を issue-flow.md「イシューの番号と置き場所」へ移す。番号を詰めると §9 を参照するスクリプト（pretooluse_guard.py:710「worktree.md §9」）などが切れるので、**見出しの番号は詰めない**（「## 8. （issue-flow.md へ移した）」の 1 行を残すか、欠番にする）。217 行目「→ §8」は「→ §9」に。-3 行 | 最適化（workflow.md・issue-flow.md と三重） | issue-flow.md | - |
| worktree.md | ## 9. セッション間の引き継ぎ原則（自己完結） | 直す | 原則（239〜241 行）は残す。「憲法5」→「CLAUDE.md 絶対ルール 5」。242〜245 行（primary の早送りの実装の詳細: ロック・SIGTERM・GIT_OPTIONAL_LOCKS 等）は sessionstart_context.py の説明なので「例外: 開始時のフックが primary を develop へ早送りする（何も消さない。結果は開始時の文脈の 1 行）」の 2 行に縮める。246〜248 行（技術強制）は danger-ops.md「サンドボックス（第 1 層）」と表 32 行と重なるので、Edit 系の見張り（入れ子の所有者の判定）だけ 2 行残し、Bash の書き込みは参照に。249〜252 行（削除・破棄）は「こまめに commit・別のワークツリーを消さない・撤去は wt-remove.sh」の 3 行に。253 行（既知の限界）は残す（気づきにくい）。公式の分離の仕組み（ワークツリーのセッションから main checkout への Edit・git の向け直しを公式が止める [W]）を 1 行足す。-12 行 | [W]「How Claude Code enforces isolation」（公式は main checkout だけを守り、兄弟・primary→入れ子は守らない＝見張りは今も要る） | worktree.md（原則）・danger-ops.md（強制の仕組み） | #427（Edit 系の見張りのうち公式の分離と重なる部分の記録） |
| worktree.md | ## 10. 現在の構成の確認とトラック⇔ラベル対応 | 直す | トラックとラベルの対応表は issue-flow.md のラベルの決まりと重複（しかも `.github/` が抜けて食い違う）。表を消して「トラック=ラベル `track:harness`／`track:app`（決まりは issue-flow.md）」の 1 行に（test_i107 は worktree.md に両ラベルの文字が 1 行以上あれば通る）。1 行目と最後の行は残す。-5 行 | 最適化・食い違いの解消 | issue-flow.md | - |
| worktree.md | ## 11. 旧方式からの移行 | 消す | 「I184（2026-10-24）で完了した。手順の記録として残す」と自分で書いている。git の履歴に残る。-14 行。**test_i179 D3 が「旧方式からの移行」の文字を必須にしている**（表5） | 最適化 | -（git の履歴） | - |

---

## 表2 ファイルをまたぐ重複・矛盾

| 決まり | 書いてある場所（ファイル:行） | 食い違いの有無 | 正の置き場所の案 |
|---|---|---|---|
| イシューの番号・置き場所（I221） | workflow.md:55-61・issue-flow.md:7・worktree.md:230-233・（参照）issue-bootstrap/SKILL.md:9・grill-me/SKILL.md:20・plan-issue/SKILL.md:11・dependency-audit.md:16・issue-source.sh:11 | 無し（内容は同じ・三重） | issue-flow.md「イシューの番号と置き場所」 |
| トラックラベルの決まり | issue-flow.md:19-22・issue-flow.md:124-127・worktree.md:261-264・issue-bootstrap/SKILL.md:64-65 | **有り**: issue-flow.md:20・SKILL:65 は `.github/` を含む／issue-flow.md:125・worktree.md:263 は含まない | issue-flow.md（1 か所。`.github/` を含む版） |
| 起票の手順（下書き→issue-review→gh issue create→報告） | issue-flow.md:9-34・issue-flow.md:110-131・issue-bootstrap/SKILL.md:18〜・workflow.md:4・workflow.md:20 | 有り（軽い）: issue-flow.md の報告の雛形とスキルの報告の形が別 | issue-bootstrap スキル（手順）。決まりは issue-flow.md |
| 段階の流れ（plan-review→…→close） | workflow.md:19-34・issue-flow.md:42-106・issue-flow.md:133-310・CLAUDE.md:9・各段階のスキル | **有り**: issue-flow.md のフェーズ4（マージ→レビューを closed→`gh issue close`）が close スキル（closed へ移す→Ready→マージ依頼・`Closes #N`）と逆の順。workflow.md:181-187「マージ後にレビューファイルを closed」も同じ矛盾 | workflow.md「フロー」 |
| 計画外の実装をしない | CLAUDE.md:44・workflow.md:77・workflow.md:143-147・plan-writing-rules.md:265・issue-flow.md:187 | 無し（四重） | CLAUDE.md（要約）＋plan-writing-rules.md:265（本体）。workflow.md は「ゲート」1 行 |
| 計画を変えたら plan-review を通り直す | workflow.md:81・issue-flow.md:187・issue-flow.md:212・plan-writing-rules.md:265・記憶 feedback_plan_change_needs_plan_review | 無し | workflow.md「ゲート」（plan-writing-rules.md は参照）。記憶は消してよい |
| 直 push の禁止 | CLAUDE.md:46・workflow.md:79・issue-flow.md:281・branch-protection-setup.md:15 | **有り**: workflow.md:232-238「ブランチ作成例外ルール」が直 commit を許す | CLAUDE.md 絶対ルール 3（強制は GitHub） |
| Danger Ops の承認 | CLAUDE.md:47・workflow.md:44・workflow.md:78・danger-ops.md 全体 | 無し | danger-ops.md（CLAUDE.md・workflow.md 条件 2 は要約） |
| 外部（fork）の PR | workflow.md:240-256・danger-ops.md:34・danger-ops.md:39・branch-protection-setup.md:67〜・close/SKILL.md:20-22・pr-base-sync.sh:24-36 | 無し（三重） | danger-ops.md |
| 止めて聞く条件 | workflow.md:39-47（正）・CLAUDE.md:45（要約）・各スキル（参照）・issue-flow.md:22・127（「迷えばユーザーに確認」）・workflow.md:95-98（起票前に聞く 3 つ）・issue-flow.md:352-356（ブランチ作成失敗で報告・提案） | **有り**: 3 条件に無い確認の場面が issue-flow.md と workflow.md の起票の節にある（表4） | workflow.md「止めて聞く条件」 |
| ブランチの命名（「イシュー番号3桁」） | workflow.md:171・issue-flow.md:137・issue-flow.md:173・onboarding.md:94・plan-issue/SKILL.md:29・close/SKILL.md:44-47・scripts の `^I[0-9]{3}$`（flow-stage.sh:11・gate-check.sh:17・adversarial-review.sh:490・check-frontend-evidence.sh:15・check-manual-test-executor.sh:18） | **有り**: 番号は「I＋GitHub の番号」（上限なし）なのに、命名と 6 か所の検査が 3 桁固定（表3） | workflow.md「ブランチ戦略」（文書）。スクリプトは #520 か新しいイシュー |
| ブランチ戦略（main/develop/feature・hotfix） | workflow.md:151-238・onboarding.md:84-96 | 有り（軽い）: workflow.md は「本番環境（AWS）」、本番はまだ無い（記憶 project_no_production_env） | workflow.md（onboarding.md は 3 行の要約と参照に。onboarding.md は別の担当） |
| ワークツリー間の書き込みの守り | worktree.md:246-252・danger-ops.md:13・danger-ops.md:19・danger-ops.md:32・danger-ops.md:47 | 無し（二重） | danger-ops.md（仕組み）・worktree.md §9（原則と人の手順） |
| git stash を素で使わない | worktree.md:211・（Claude Code 本体のシステムの指示にも同じ文） | 無し | worktree.md §7 |
| コミットの題の形 | issue-flow.md:329-341（「イシュー#XXX」）・実際の git log（`<種類>(I###): …`） | **有り** | 書かない（消す）。残すなら workflow.md に 1 行 |
| 手元で全テストを流し直さない | workflow.md:28・test-gate スキルの description・記憶 feedback_no_local_full_tests_duplicating_ci | 無し | workflow.md「フロー」（記憶は消してよい） |
| レビューのファイルの書く時期（実装結果評価など） | issue-flow.md:174-181・issue-flow.md:314-315 | **有り**: 「実装結果評価」節は今のテンプレートに無い | 書かない（テンプレートとスキルが正） |

---

## 表3 漏れの候補

| 足す決まり | 足す理由（気づきにくく被害が大きい根拠） | 置き場所 | 足す/足さない |
|---|---|---|---|
| イシュー番号が 1000 を越えたときの名前と検査 | 番号は GitHub が振り（I221）、#563 まで来ている（11-08 の #427 から 9 日で約 136 番＝1 日約 15 番。推測: 今の速さなら約 1 か月で #1000）。flow-stage.sh・gate-check.sh・adversarial-review.sh ほか 6 か所が `^I[0-9]{3}$` で、I1000 では流れ全体が止まる。止まり方は大きいが、文書（「3桁」）の直しだけでは足りない | 文書: workflow.md「ブランチ戦略」の命名を「I＋GitHub の番号（桁数は問わない）」に。スクリプトは本イシューの範囲外 | **足す**（文書）。スクリプトは #520 へ（食い違い）か、急ぐなら新しいイシュー（推奨: 新しいイシュー・ハーネス最優先） |
| `Closes #N` が効く前提（既定ブランチが develop） | GitHub の closing keyword は既定ブランチ宛ての PR だけで効く [G]。今の既定は develop（I109 で変更）。I109 は「本番リリース後に既定を main に戻す」可能性を書いており、戻すと**イシューが黙って閉じなくなる**（気づきにくい）。issue-flow.md の手の `gh issue close` を消すならなおさら前提を 1 行残す | issue-flow.md（閉じ方の 1 行）＋ branch-protection-setup.md（既定ブランチを変えるときの注意。別の担当） | **足す**（1 行） |
| ワークツリーのセッションで「don't ask again」を選ぶと main checkout の `settings.local.json` に入り全ワークツリーに効く | 公式の仕様 [W]。片方のワークツリーで許した許可がほかでも黙って効く。記憶にだけある（reference_worktree_permissions_from_main） | worktree.md §7 | **足す**（1 行） |
| 相互依存のイシューは単体 PR の既知の CI 失敗で止まらない | 記憶 feedback_coupled_issues_proceed_autonomously。止めて聞く条件の「それ以外」の例に入る話 | workflow.md「止めて聞く条件」の最後の段落の例に 1 句 | 足す（記憶から移す。中身は「止めない」の確認で、確認の場面は変えない） |
| 起票は触る場所・失敗の影響・戻し方がそろう単位に分ける | 記憶 feedback_split_many_candidates_into_issues。1 イシューにまとめると PR が大きくなりレビューが収束しない（I197・I179 の周回） | issue-flow.md（起票の決まり） | 足す（記憶から移す・1 行） |
| 一覧に回す前に目的を崩すかを見る | 記憶 feedback_backlog_purpose_check（I486 で close 後に戻した＝手戻り大） | retro の決まり（review-rules.md か plan-writing-rules.md。私の担当外）。issue-flow.md ではない | 足す候補（置き場所は別の担当で決める） |
| 承認画面が出うる操作は呼ぶ前に予告 | 記憶 feedback_warn_before_approval_prompt。ユーザー個人とのやり取りの好みに近い | - | **足さない**: 個人の好み寄り・手順書に無くても事故にならない（記憶に残す） |
| コマンド実行前の日本語の説明（今の workflow.md「Claude Code実行ルール」） | - | - | **足さない（消す）**: Bash ツールの description が公式で必須・[B] |
| 「現在のブランチを確認して警告」 | - | - | **足さない（消す）**: /plan-issue が作り gate-check が HEAD を見る。その場で捕まる |
| `/doctor prompt-audit` で決まりの矛盾を定期に点検 | [M]・[B] の公式の機能。今回のような総点検を軽くできる | - | **足さない**（公式の機能への置き換えなので #427 へ） |
| サブエージェントを `isolation: worktree` で動かすと、そのワークツリーの CLAUDE.md を読まない | 公式 [W]。今の流れでは別プロセスの `claude -p --agent` でレビュー役を動かし、`isolation: worktree` を使わない | - | **足さない**: 今の流れで踏まない |
| worktree の名前を使い回すとサンドボックス有効時は古い先端で開き直す | 公式 [W]。/plan-issue が origin/develop からブランチを作るので影響が無い | - | **足さない**: 今の流れで踏まない |

---

## 表4 中身の変更案（安全装置: CLAUDE.md「1. 絶対ルール」・workflow.md「止めて聞く条件」と、それと同じ働きの確認の場面）

| 案 | 今の中身（ファイル:行） | 変えた後 | 確認の場面の増減 | 理由 |
|---|---|---|---|---|
| 4-1 ラベルで迷ったらユーザーに確認、を消す | issue-flow.md:22・127「判断に迷う場合はユーザーに確認」 | 「主目的の側に 1 つ付け、迷ったら決めた理由を報告に 1 行」 | **減る** | 3 条件のどれにも当たらない（ラベルはいつでも付け直せる・要件でも UI でもない）。「この 3 つだけ」と食い違う |
| 4-2 起票の前に聞く 3 つを 3 条件に合わせる | workflow.md:95-98（①価値が低いか迷う ②別イシューが先に要り範囲・順番が変わる ③要件・UI の判断が残る） | ①は聞かずに Claude が決めて報告（記憶 feedback_propose_issue_title_on_separate_issue「価値の低いもの以外は確認なしで起票」と同じ）②は「止めて聞く条件 1（受け入れ条件・範囲が変わる）」に当たるものとして残し、文に条件 1 の参照を付ける ③はそのまま（もともと条件 1） | **減る**（①が無くなる） | 「止めて聞く条件（この 3 つだけ）」との矛盾の解消。②を条件 1 の言い換えと読めるか（「進める順番」は条件 1 に無い）はユーザーの判断。代案: 条件 1 に「対応中のイシューの範囲・順番を変えるとき」を足す（その場合は**増える**ではなく今の運用を明文化するだけ） |
| 4-3 ブランチ作成の失敗でユーザーに報告・提案、を消す | issue-flow.md:352-356 | 消す（直せるものは Claude が直して自律判断の記録へ。直せなければ条件 3 の扱い） | **減る** | 3 条件に無い |
| 4-4 ブランチ作成の例外（直 commit 可）を消す | workflow.md:232-238 | 消す（例外なし） | 承認の対象は変わらない（直 push は GitHub がもともと止める）。**守りは厳しくなる側** | CLAUDE.md 絶対ルール 3 と矛盾。実際にもできない |
| 4-5（検討して見送り）安全装置の集合を広げる | workflow.md:44（`.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`pretooluse_guard.py`・`settings.json`・`settings.local.json`） | 変えない。候補だった `posttooluse_check.py`・`sessionstart_context.py`・`.claude/agents/*`・`gate-check.sh` は足さない | 無し | 足すと「止めて聞く」が増える。これらは構文の検査・早送り・レビュー役・ゲートで、緩めても GitHub の保護と CI のテストが最後に残る（記憶 feedback_local_guard_github_last_line）。足さない理由をユーザーに見せるだけ |

（4-1〜4-4 は「止めて聞く条件 2」の安全装置そのものではないが、ユーザーの関わり方を変えるので、方針どおり plan-review の後・実装の前に 1 度だけユーザーに確認する対象に入れた）

---

## 表5 名前・置き場所を変える節を参照している行

（`git grep` で `.claude/`・`docs/runbooks/`・`docs/*/templates`・`scripts/claude/`・`CLAUDE.md` を検索。closed の記録・legacy は除く。**テストが文書の文字を見ているもの**は「テスト」と書いた。テストは「スクリプト」なので I546 の範囲外とした場合、文書を変える PR で一緒に直さないと CI が落ちる。直し方の案: 消した節を見るテストは、記憶 feedback_tests_guard_only_hard_to_notice に従い期待値を直すより項目ごと消す方がよい）

| 変える節 | 参照している行 |
|---|---|
| workflow.md「イシューの置き場所」→ issue-flow.md へ移す | .claude/skills/grill-me/SKILL.md:20・.claude/skills/issue-bootstrap/SKILL.md:9・.claude/skills/plan-issue/SKILL.md:11・docs/runbooks/dependency-audit.md:16・docs/runbooks/issue-flow.md:7・docs/runbooks/workflow.md:4・docs/runbooks/workflow.md:80・docs/runbooks/worktree.md:232・scripts/claude/issue-source.sh:11（コメント） |
| workflow.md「外部（fork）からの PR の扱い」→ danger-ops.md へ移す | .claude/skills/close/SKILL.md:22 |
| workflow.md「移行（I193 のマージ前に着手したイシュー）」を消す | テスト: scripts/claude/tests/test_i193_official_flow.sh:543（d6）・:551（D6）／テスト: scripts/claude/tests/test_i185_harness_docs.sh:62（フィクスチャ workflow_stop_guidance の抜き出しの終わりの目印が「## 移行」。次の見出し「## Claude Code実行ルール」も消すので、終わりの目印を「---」か「## ブランチ戦略」に変える必要） |
| workflow.md「Claude Code実行ルール」「作業実行前の確認ルール」「修正ツール使用前チェック」を消す | 参照なし |
| workflow.md「イシュー完了時のマージフロー」「ブランチ作成例外ルール」「現在のブランチ確認」を消す | 参照なし |
| workflow.md「本番リリースフロー（重要）」（見出しは変えない） | docs/runbooks/onboarding.md:173 |
| workflow.md の題（「Vibe Coding 運用フロー…」） | 参照なし（onboarding.md:7・13 の「Vibe Coding」は別の文） |
| issue-flow.md「イシュー作成時の自動実行フロー（必須）」を縮める | テスト: scripts/claude/tests/test_i107_track_label_docs.sh:8・15・32-33（issue-flow.md に `track:app`・`track:harness` が各 **2 行以上**。1 か所にまとめると 1 行になり落ちる） |
| issue-flow.md「イシューフロー（統合ルール）」を消す | docs/runbooks/workflow.md:36（「詳細なイシューフローは」）・.claude/skills/issue-bootstrap/SKILL.md:100-101（「イシュー作成フロー・ブランチ戦略・クローズ手順は issue-flow.md」）・docs/runbooks/onboarding.md:183（ファイル単位）／テスト: scripts/claude/tests/test_i179_worktree_docs.sh:28・36・72-77・170（D6 ステップ5 の範囲）・:131（FILES）／テスト: scripts/claude/tests/test_i185_harness_docs.sh:63-64（フィクスチャ issue_flow_8_5・issue_flow_step_8_5）と scripts/claude/tests/fixtures/i185/issue_flow_8_5.txt・issue_flow_step_8_5.txt／テスト: scripts/claude/tests/test_i202_ledger_cleanup.sh:551（N13: issue-flow.md に「パスの判定が YES のときは」が要る） |
| issue-flow.md の題（「イシューフロー」→「イシューの扱い…」） | CLAUDE.md:20（説明の文）・docs/runbooks/onboarding.md:183 |
| worktree.md §2 の確認 2（`_owning_root` の grep）を消す・確認 1 を #427 で外す場合 | テスト: scripts/claude/tests/test_i179_worktree_docs.sh:53（D3 が 'git remote set-head origin --auto'・'refs/remotes/origin/HEAD' を必須） |
| worktree.md §8 を移す（番号は詰めない） | docs/runbooks/worktree.md:217（「→ §8」） |
| worktree.md §10 の表を消す（番号は残す） | docs/runbooks/worktree.md:15（「→ §10」）／テスト: scripts/claude/tests/test_i107_track_label_docs.sh:9・16・34-35（worktree.md に両ラベルが 1 行以上。1 行の参照に両方書けば通る） |
| worktree.md §11「旧方式からの移行」を消す | テスト: scripts/claude/tests/test_i179_worktree_docs.sh:53（D3 が '旧方式からの移行' を必須） |
| worktree.md の § 番号（参照: 番号を詰めると切れるので詰めない前提） | .claude/skills/plan-issue/SKILL.md:25（§3）・docs/runbooks/issue-flow.md:138（§3）・docs/runbooks/common-commands.md:20（§6）・docs/runbooks/danger-ops.md:11（§4）・:13（§9）・docs/runbooks/pre-commit.md:73（§5）・scripts/claude/adversarial-review.sh:427（§6）・scripts/claude/hooks/pretooluse_guard.py:710（§9）・scripts/claude/lint-frontend.sh:2（§5）・scripts/claude/wt-ports.sh:11（§5/§6）・scripts/claude/wt-remove.sh:14・73・157・191・196・204（§4・§4 の小見出し「止まったときの片付け」「取り残しの発見と削除」）・scripts/claude/tests/test_pretooluse_worktree_guard.sh:84（§4） |
| 変えない見出し（テストの目印） | workflow.md「## 止めて聞く条件」「## 記録とつなぎ」（test_i185:61）・「### 各段階で止まったときの案内」（test_i185:62）・「## GitHub への書き込みの時点」（test_i224:43・78）・「5. close: base 追従 → `gate-check.sh`」の文（test_i193:156）・「- /issue-bootstrap」等 4 行と「ユーザーは打たない」（test_i193 D7）・条件 2 の集合の文（test_i193 S12） |

---

## #427・#520 へ回すもの（まとめ）

| 回す先 | 内容 | 根拠 |
|---|---|---|
| #427 | worktree.md §2 確認 1（`git remote set-head origin --auto`）: 公式の `worktree.baseRef: "fresh"` が既定ブランチを 24 時間ごとに fetch して origin/HEAD を新しく保つ。手の確認が要らなくなったかを実地で確かめる（推測: set-head までするかは文書から読み切れない） | [W]「Choose the base branch」 |
| #427 | worktree.md §2・§4 のロックの扱い: 公式の古いロックの掃除（終了したプロセスのロックを外す）で、wt-remove.sh のロック外しの一部が要らなくなるか | [W]「Worktree locks and manual removal」 |
| #427 | worktree.md §9 の Edit 系の見張り: 公式の分離（ワークツリーのセッションから main checkout への Edit・git の向け直しを止める）と重なる部分。primary→入れ子・兄弟の間は公式に無いので見張りは残る（置き換えは一部だけ） | [W]「How Claude Code enforces isolation」 |
| #427 | 決まりの矛盾の定期点検: 公式の `/doctor prompt-audit`（CLAUDE.md・skills・agents・rules の矛盾と古さを点検）を harness-audit.md の手の総点検に使えるか（#441 とも近い） | [M]「Consistency」・[B] |
| #427 | hotfix の後のブランチ削除: GitHub の「Automatically delete head branches」 | GitHub の設定（ユーザーの画面の操作） |
| #520 | workflow.md:88「（段階のスキルを単独に）呼んでも `flow-stage.sh` と `gate-check.sh` が順番を外れた進行を止める」: 段階のスキルは自分で flow-stage.sh を呼ばない（proceed だけが呼ぶ・proceed/SKILL.md:21）。gate-check.sh は test-gate・close の最初だけ。implement・review-gate を単独で呼んだときは止まらない（推測: review-gate は CI 待ちとレビュー記録で事実上害は小さい） | `git grep flow-stage .claude/skills` |
| #520（または新しいイシュー・急ぎ） | 番号の検査 `^I[0-9]{3}$`（flow-stage.sh:11・gate-check.sh:17・adversarial-review.sh:490・check-frontend-evidence.sh:15・check-manual-test-executor.sh:18・close/SKILL.md:47）と、文書の「I＋GitHub の番号」の食い違い。I1000 で流れが止まる | 表3 の 1 行目 |

食い違いが無いと確かめたもの（#520 に回さない）: CLAUDE.md §3 の hooks の説明（settings.json と一致）・workflow.md:44 の集合（path_risk_trigger と一致）・workflow.md:70 `CI_WAIT: NOT_PUSHED`（code-review.sh:250）・workflow.md:249 の deny（settings.json:124-125）・workflow.md:253 の外部 PR の検知（pr-base-sync.sh:24-36）・worktree.md:247 のサンドボックスの `denyWrite: [".claude/worktrees"]` と外に出すコマンド（settings.json:206-214）・worktree.md:248 の Edit 系の見張り（matcher Edit|Write|MultiEdit|NotebookEdit・onFailure block）・worktree.md:252 の `rm -r`・`git clean -f`・`git reset --hard` の停止（pretooluse_guard.py:1947-1952・2000-2041）・worktree.md:242 の `--sync-primary`（sessionstart_context.py:170・200）

---

## 行数（今 → 提案どおりにしたときの見込み）

| ファイル | 今 | 見込み | 主な減り |
|---|---|---|---|
| CLAUDE.md | 57 | 約 53 | 前置き・§2 を索引へ |
| docs/runbooks/workflow.md | 256 | 約 135 | 移行・実行ルール・作業前の確認・ブランチ戦略の古い小節・外部 PR とイシューの置き場所を移す |
| docs/runbooks/issue-flow.md | 356 | 約 40 | 統合ルール（約 285 行）・ブランチ運用（約 30 行）を消し、置き場所（+7）を受け取る |
| docs/runbooks/worktree.md | 282 | 約 225 | §11 を消す・§4・§9 を縮める・§8・§10 を参照に |
| 合計 | 951 | 約 453 | 約 52% 減 |

（見込みは手で数えた概算。移す先の danger-ops.md は外部 PR の手順で約 +10 行）
# 点検 B: `docs/runbooks/plan-writing-rules.md`・`docs/runbooks/review-rules.md`（I546・2026-11-17）

照らした公式の文書（すべて 2026-11-17 に参照）:
- [S1] https://code.claude.com/docs/en/skills （frontmatter・description の上限 1,536 文字・SKILL.md 500 行）
- [S2] https://code.claude.com/docs/en/cli-reference （`--permission-mode` の値・`manual` は `default` の別名で UI 表示は Manual・`--permission-prompts none`）
- [S3] https://code.claude.com/docs/en/sub-agents （裏のサブエージェントの承認画面は親のセッションに出る）
- [S4] https://code.claude.com/docs/en/best-practices （決定論/非決定論の指示・「多くの場合 Claude に決めさせる」・強調を足しても守られない行はフックへ・`/code-review` は新しいサブエージェントで見る・「skip style」）
- [S5] https://code.claude.com/docs/en/memory （「Write effective instructions」: 短く・矛盾させない／`/doctor prompt-audit <path>` が古い指示・存在しないファイル・矛盾を見つける）
- [S6] https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions （`pull_request_target`・GITHUB_TOKEN の最小権限・SHA 固定／lockfile が SHA 固定に代わる記載）

凡例: 「内部:」= リポジトリの中の事実（スクリプト・スキル・テンプレート・過去の記録）だけを根拠にした判定。行番号は今の develop（このワークツリーの HEAD 53436302）。

---

## 表1 節ごとの判定

### plan-writing-rules.md（494 行）

| ファイル | 節（見出しの文字のまま） | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| plan-writing-rules.md | `# 計画書の書き方（安全寄り）`（L1〜25 の 1)〜9) の一覧） | 直す | 1)〜9) は `docs/plans/templates/plan_template.md` の `## 1.`〜`## 9.` と同じ並び。一覧は「形の正はテンプレート。各節に何を書くか」に絞る。5) の下位原則（垂直スライス・未知リスク先行・依存関係・セキュリティ制御を分けない・検証コマンドを書かない）は残す。「（各原則は…読み替える）」L20 は 1 行に縮める。9) の UI 確認の文（L25）は「`docs/runbooks/workflow.md`「止めて聞く条件」1」への参照だけにする（中身は同じ）。テンプレートに無い `## 基本情報`・`### 調査結果`（1 の下）・`### 修正アプローチ`（4 の下）・`## 計画変更記録` を「テンプレートに足す」と書く（下の「計画書作成ルール」節の吸収先）。−5 行程度 | 内部: 最近の計画（plan_I539・I545・I530・I524・I525）はすべて `## 基本情報`・`### 調査結果`・`## 計画変更記録` を持つが、テンプレートには無い（手で毎回足している）。[S5] 同じことを 2 か所に書かない | 形 = `docs/plans/templates/plan_template.md`、書く中身 = 本節 | - |
| plan-writing-rules.md | `### 条件付きセクション（該当する場合のみ含める）`（10〜15） | そのまま | 番号 10〜15 は変えない（`ux-rules.md:6`・`issue-flow.md:348`・`plan-issue/SKILL.md:149〜165` が「セクション10〜15」「13)」で参照）。テンプレートに条件付き節の見出しが無いので、テンプレートに「`## 10.`〜`## 15.`（該当時のみ）」の 1 行コメントを足す案だけ | 内部: 参照の番号依存 | 本節 | - |
| plan-writing-rules.md | `重要:`（L66〜68） | 直す | L67（計画書に書いていない実装は禁止…）は CLAUDE.md 絶対ルール 1・`workflow.md`「ゲート」・本ファイル「計画書と実装の一致性保証ルール」と 4 重。1 行の参照に縮める。L68（関連文書の同時更新）は本ファイルにしか無い決まりなので残すが、「例: スキルの実装形態…」の括弧書きは消す。−2 行 | 内部: 重複 | 絶対ルール = CLAUDE.md、計画を直す手順 = 本ファイルの一致性の節 | - |
| plan-writing-rules.md | `## 計画書作成前の事前調査（必須）` | 直す | 見出しの「（必須）」を消し、各小節に「いつ要るか」を書く形にそろえる（今は「全イシュー必須」と「該当時必須」が混在） | [S4]「多くの場合 Claude に決めさせる。ほとんどの指針には例外がある」 | 本節 | - |
| plan-writing-rules.md | `### 環境前提確認（全イシュー必須）` | 直す | 「全イシュー必須」→「手順が新しい道具・サービス・コマンドに頼るときだけ」。例の 3 行は残し、ハーネスのテストの道具は `bash scripts/claude/tests/check-tools.sh`（`required-tools.txt`）で確かめる、を 1 行足す。−3 行 | 内部: 文書だけのイシュー（本イシューなど）で毎回は不要。`check-tools.sh` が既にある | 本節 | - |
| plan-writing-rules.md | `### 外部/ハーネス挙動依存のスパイク実証（計画が「未知リスク」と認識する場合・必須）` | 直す | (2) の 1 文（L90・約 600 字）に、観測手段（`claude -p`・`test-session.sh`・`check-permission-prompt.sh`・`tui-capture.sh`・`--strict-mcp-config`・`PATH`）が詰め込まれ、同じ一覧が「実施者の区別」の表と「ハーネス挙動テストの実施環境」の表にもある（ファイル内で 3 重）。観測手段の一覧を 1 か所（下の「ハーネス挙動テストの実施環境」を「Claude が観測できる手段」に改める）に置き、(2) はそこを参照する。`--strict-mcp-config`・`PATH`・G6/G7 の話はスクリプトの作り方の決まりで計画書の書き方ではない → `github-app-setup.md`（鍵の決まり）へ移すか、テストが止めているので消す。「プレーン default の新規セッション」→「通常モード（Manual）の新しいセッション」。−4 行 | [S2] `--permission-mode` の `manual` は `default` の別名で UI 表示は Manual（v2.1.200〜）。内部: `test_i223_gh_app.sh` の G6・G7 が付け忘れを止める（文書は重ねて言わなくてよい） | 観測手段 = 本ファイルの 1 か所、鍵の扱い = `github-app-setup.md` | - |
| plan-writing-rules.md | `### 参照先実在性の全件機械検証（ドキュメント整合・棚卸し系イシュー）` | 直す | 残す（文書のイシューで後から切れた参照が見つかる事故は実際にあった）。公式の `/doctor prompt-audit <path>` が「存在しないファイル・コマンドへの参照、矛盾」を見るので、`test -f` の全件確認に加えて使えるかを #427 で確かめる、と 1 行。−1 行 | [S5]「Audit your instruction files」: 既定は CLAUDE.md・`.claude/` の rules・skills・agents。パスを渡せば任意のファイル（推測: `docs/runbooks/` も渡せば見られる。未実証） | 本節 | #427 |
| plan-writing-rules.md | `### 規約是正時の消費箇所の全件列挙（命名・フォーマット・規約の是正イシュー）` | 直す | 残す。L108 の「イシュー本文では…`check-memo-body-paths.sh`（grill-me が実行）が…決定論的インスタンスである」は grill-me の手順の説明なので消す（`grill-me/SKILL.md:73` に既にある）。−2 行 | 内部: 重複（`plan-reviewer.md:72,110`・`code-reviewer.md:78` も同じ観点を持つがレビュー役の観点なので I547） | 本節 | - |
| plan-writing-rules.md | `### 指示ファイルへの条件分岐追加時のコマンド粒度パリティ` | 直す | 残すが 3 行に縮める（理由の段落と確認手順は 1 文に）。「計画書の書き方」ではなく「指示ファイルを書くとき」の決まりなので、#538（手順の書き方）で置き場所を決めるまで本ファイルに置く。−4 行 | 内部: `plan-reviewer.md:109`・`code-reviewer.md:79` と同趣旨 | 本節（#538 の結果で移す） | - |
| plan-writing-rules.md | 区切り後の前置き「CI・lint・テスト・コード品質に関わるイシューでは、以下も実施すること。」（L119） | 直す | 下の 3 節を 1 節にまとめるので前置きも 1 行に | 内部 | 本節 | - |
| plan-writing-rules.md | `### 既存テストの事前実行` | 消す（下にまとめる） | `cd backend && python -m pytest … \| tail` を計画前に手元で流す指示は、test-gate の「pytest・Jest・E2E の手元での流し直しはしない（CI が正）」と矛盾。ベースラインは「develop の最新の CI の結果（`gh run list --branch develop`）で見る」に置き換え、下の 1 節に 1 行で入れる。コマンドも `cd … && … \| tail` の複合形で、サンドボックス・許可ルールに当たりにくい書き方（記憶の「Bash は複合化せず単体で」と食い違う）。−14 行 | 内部: `test-gate/SKILL.md:3,30`・記憶 feedback_no_local_full_tests_duplicating_ci・feedback_atomic_allowlisted_commands。backend のテストはホストでなくコンテナ（`docker compose exec backend …`・`common-commands.md`） | 本節（まとめた 1 節） | - |
| plan-writing-rules.md | `### lint エラー数の事前計測` | 消す（下にまとめる） | `flake8` は使っていない（pre-commit は `ruff`）。古いコマンド。「検査ツールを入れる・強めるときは計画前に流して件数と直す対象を調査結果に書く」1 行に吸収。−13 行 | 内部: `pre-commit.md:44`（ruff が flake8 相当） | 本節（まとめた 1 節） | - |
| plan-writing-rules.md | `### lint/audit/scan 系ツール導入時の副作用事前調査（必須）` | 直す | 上の 2 節を吸収して「検査ツール（lint・audit・scan・型）を入れる・強めるときの事前の実行」1 節（6 行程度）にする。−4 行 | 内部 | 本節 | - |
| plan-writing-rules.md | `### 否定・回帰系の決定論テストの自己検証（false-green 禁止）` | 直す | 中身は残す（気づきにくく被害が大きい）。L166「これは…品質保証であり…」の 1 行は消す。`plan-issue/SKILL.md:190〜191` の文書品質ゲートと `plan-reviewer.md:118,120` が同文を持つ → 決まりの本体はここ、スキル・レビュー役は参照に（I547）。−1 行 | 内部 | 本節 | - |
| plan-writing-rules.md | `### 決定論テストの対象の選び方（写しのテストを作らない）` | そのまま | I213 の最新の決まり。[S4] の「強制する集合は小さく保つ」と合う。例の「action を SHA で固定」は GitHub が lockfile を SHA 固定の代わりに挙げているので、lockfile を採るかは #427 で見る（本節は変えない） | [S4]「keep the enforced set small」・[S6]「a lockfile supersedes SHA pinning」 | 本節 | #427（lockfile） |
| plan-writing-rules.md | `### 高リスクの計画の「必ず確かめる項目」（I228）` | そのまま | 書き方の決まりで、`review-rules.md:73` が参照。L186 の `carry_items` の説明はスクリプトの動きの説明なので 1 文に縮めてよい（−1 行） | 内部: `adversarial-review.sh:369` に `carry_items` あり（一致） | 本節 | - |
| plan-writing-rules.md | `### 見張り（`pretooluse_guard.py`）に判定を足す計画（I430）` | 消す（参照 1 行に） | 本文は `danger-ops.md:60〜63`「見張りに判定を足すときの決まり」とほぼ同文（本節自身が「ここは要約」と書く）。条件付きの事前調査の一覧に「見張りに判定を足す計画は `danger-ops.md`「見張りに判定を足すときの決まり」の 3 点を計画に書く」の 1 行だけ残す。**`danger-ops.md:60` が本節の名前を参照しているので、その参照も直す（表5）**。−7 行 | 内部: 重複 | `danger-ops.md` | - |
| plan-writing-rules.md | `## 計画書作成ルール（詳細）` / `### 計画書作成ルール` | 直す | 「計画書の内容」（L202〜218）は 1)〜9) の一覧と重複（DB 変更→10、リスク→8、完了条件→2、ロールバック→7）。残すのは「1 の下に `### 調査結果`（原因の概要を平易に 1〜2 文 → 詳細な原因〔流れ・技術的な背景・問題の箇所 ファイル:行〕）」「4 の下に `### 修正アプローチ` と項目ごとの修正方針（コード例の前に言葉で）」の 2 点だけ（テンプレートのコメントに入れればここは 3 行）。「作成タイミング」は 1 行。−25 行 | 内部: 最近の計画はこの形（plan_I539・I530 など） | 形 = テンプレート、中身 = 本節 | - |
| plan-writing-rules.md | 同節内「計画書ファイル名ルール」「ファイル名生成手順」（L230〜246） | 直す | 再作成時の `plan_I010_2.md` 連番と bash の連番生成は使われていない（`docs/plans/closed` に `_2` は 0 件・`plan-issue` は `plan_$ARGUMENTS.md` だけを作る）。計画を変えるときは計画変更記録に足す、に一本化して連番と bash を消す。`workflow.md:139`・`issue-flow.md:157,317`・`review-rules.md:12` の `_2`/`_N` も同時に直す。−15 行 | 内部: 実績 0 件。記憶「Read ツールで読む」とも合わない手作りのコード | 名前 = `plan-issue/SKILL.md`（生成物）、変えるとき = 本ファイルの計画変更記録 | - |
| plan-writing-rules.md | 同節内「計画書作成後」（L247） | そのまま | I193 の流れ（承認を待たない）と一致 | 内部: `plan-issue/SKILL.md:194〜201` | 手順 = `plan-issue/SKILL.md`、本節は 1 行 | - |
| plan-writing-rules.md | `### 計画書ヘッダー（文書間の関係性）` | 直す（テンプレートへ移す） | `## 基本情報` の形はテンプレートに入れ、本節は消す。項目「実装後評価: docs/reviews/open/IXXX_review.md（または未作成）」は plan-issue が同時に作るので「（未作成）」の場合分けは不要。`review-rules.md:9〜16` の写しも消す（表2）。**節の名前を `review-rules.md:10` が参照（表5）**。−10 行 | 内部: テンプレートに無く毎回手で書いている | `docs/plans/templates/plan_template.md` | - |
| plan-writing-rules.md | `## 計画書と実装の一致性保証ルール（絶対遵守）` / `### 基本原則` | 直す | 「（絶対遵守）」の強調を外し、基本原則（L265）の 1 段落を残す。CLAUDE.md 絶対ルール 1 と `workflow.md`「ゲート」が要約を持つので、ここが正（計画を直す手順の本体）だと明記 | [S4]「強調を足しても守られない行は hook へ。逆に好みの強制はやめて Claude に決めさせる」 | 本節 | - |
| plan-writing-rules.md | `### 実装開始前の必須確認（3ステップチェック）` / `#### ステップ1: 計画書の再確認` | 消す | `cat docs/plans/open/plan_….md` は Read ツールで読む方針・implement の「必読」と食い違う。計画書を読むのは `implement/SKILL.md:10〜14` の必読で既に決まっている。−5 行 | 内部: implement の必読・記憶 feedback_use_read_tool_not_bash_for_files | `implement/SKILL.md` | - |
| plan-writing-rules.md | `#### ステップ2: 実装内容の事前確認と改善` | 消す（基本原則に 3 行で吸収） | チェックリスト・4 つの自問・「あってはならない例」は下の「より良い方法の検討」「徹底のための自己チェック質問」と同じ主張の繰り返し（ファイル内で 3〜4 回）。残すのは「計画にない変更・名前の違い・より良い方法は、実装の前に計画書を直す（計画変更記録）」の 1 文と、あってはならない例 2 行（`list` 修正 → 新メソッド追加など）。−20 行 | 内部: 重複。[S4] | 本節（基本原則） | - |
| plan-writing-rules.md | `#### ステップ3: 逸脱検知時の強制停止` | 直す | 4 つの場合と「中断後の手順」（計画変更記録に書く → 方式・範囲・AC を変えるなら plan-review → 要件・設計・UI だけユーザー）は残す本体。下の「改善の記録フォーマット」と記録の形が 2 つある（L311〜317 と L396〜401）→ 1 つにまとめる（4 項目＋「計画レビューのやり直し: 要/不要」）。「強制停止」「修正ツールは使用しない」の強調は外す。−6 行 | 内部: 同じ記録の形が 2 つ。`workflow.md:81`・`review-rules.md:88`・`plan-review/SKILL.md:31` が「要/不要を 1 行」と言う | 本節 | - |
| plan-writing-rules.md | `### より良い方法の検討（必須プロセス）` | 消す（1 行に） | 7 観点（性能・保守性…）と「直すべきケース」は一般論で、`implement/SKILL.md:85〜86`（「最適な実装を採用・より良い方法は計画書を直す」）と、組み込み `/simplify`・`/code-review` が受け持つ。「見つけたら計画書を直す。承認待ちはしない」1 行だけ基本原則へ。−20 行 | [S4] 現行のモデルは目の前のコードで指針の当てはまりを判断できる。内部: implement 1)・1.5) | 本節（基本原則の 1 行） | - |
| plan-writing-rules.md | `### 厳守しなければならない実装フロー（必須手順）` | 消す | 「最低5分」の検討・「検討時間: ___分」の記録・ステップ 1〜7 の遵守チェックは、実際の記録に 1 件も無い（`docs/reviews/closed`・`docs/plans/closed` に「検討時間」0 件）。流れは implement の手順 0)〜4) が正。−30 行 | 内部: 実績 0 件・implement の手順と二重 | `implement/SKILL.md` | - |
| plan-writing-rules.md | `### 実装完了後の一致性検証` | 消す | `echo "❓…"` と `grep -A 20 "修正対象" docs/plans/open/plan_*.md`（他イシューの計画まで拾う）は手作りで、実質は `implement/SKILL.md` 3.5)（`git diff origin/develop...HEAD --name-only` で反映を確かめる）と review-gate の code-reviewer の「計画との照合」が受け持つ。−19 行 | 内部: implement 3.5)・`review-rules.md`「検証の全体設計」層 2 | `implement/SKILL.md` 3.5)・review-gate | - |
| plan-writing-rules.md | `### 改善の記録フォーマット` | 直す（ステップ3 と 1 つに） | 上のステップ3 の形と統合して 1 つの「計画変更記録の形」にする。−4 行 | 内部 | 本節 | - |
| plan-writing-rules.md | `### 徹底のための自己チェック質問` | 消す | 5 つの質問は ステップ2・ステップ3 の再掲。「1文字でも違えば中断」「すべてYESで答えられない限り修正ツールは使用禁止」は強調だけで決定論の止め方が無い（止めるのは plan-review 前の `flow-stage.sh`・`gate-check.sh` とレビュー）。`workflow.md:143〜148`「修正ツール使用前チェック（必須）」も同じ質問の写し（表2）。−9 行 | [S4]「強調を足しても守られないなら hook に。強制が要るなら決定論で」。内部: 実際の守りは計画レビュー前のコード変更禁止（plan-issue の禁止）とレビューの計画照合 | 本節（基本原則） | -（「文書は止めると言うが仕組みが無い」に当たるかは、文書が「使用禁止」と書くだけで「自動で止める」とは書いていないので #520 には回さない） |
| plan-writing-rules.md | `### 例外ルール（極めて限定的）` | そのまま（縮める） | タイポ・import・整形の 3 つは残す。「極めて限定的」「のみ」の強調を外す。−2 行 | 内部 | 本節 | - |
| plan-writing-rules.md | `## 計画書作成例外の禁止ルール` | 直す（一致性の節に 2 行で吸収） | 3 つの禁止のうち 1 は fix-loop の手順（計画を変えるなら plan-review）と、2・3 は基本原則と同じ。「#### 違反時の対処法」は「計画変更記録に事後で書き、plan-review を呼ぶ・再発防止は retro」1 行。見出しのレベルも `##` の下に `####`（`###` 飛ばし）で崩れている。−11 行 | 内部: `fix-loop/SKILL.md`・`review-rules.md:88` | 本節（基本原則） | - |
| plan-writing-rules.md | `## 計画書完了時のルール` | 消す | open → closed の移動は `close/SKILL.md` step 1 が正。`echo "## 完了情報" >> "$PLAN_FILE"` は close の手順に無く（close は staging のコメントで「完了情報追記など」と触れるだけ）、実際の計画の 61/163 件だけが持つ（揺れている）。完了の日時・対応者・結果は PR のマージと git の履歴に残る。`completed/` の注意も、`docs/plans/` に `completed/` が無いので不要。`issue-flow.md:232〜266` の同じ echo も同時に消す（表2）。−15 行 | 内部: `ls docs/plans` = closed/open/templates。close SKILL に完了情報の手順なし | `close/SKILL.md`（close の staging コメントの「完了情報」の語は I547 で消す） | - |
| plan-writing-rules.md | `## 手動テスト文書のフォーマットルール` | 直す | 列の形（`| No | 手順 | …`）は `manual_test_template.md` と同じ → 形はテンプレートを正にし、ここは「実施者」列が必須であることだけ。−6 行 | 内部: テンプレートが同じ表を持つ | 形 = `docs/tests/templates/manual_test_template.md`、基準 = 本節 | - |
| plan-writing-rules.md | `**実施者の区別**`（表・「この基準の正はこの節」） | 直す（名前は変えない） | 表の `Claude` の行の観測手段の長い括弧書きを、上の「観測手段の一覧」1 か所への参照にする。`Human` の行の「試した手段:」の決まりは残す。**`この基準の正はこの節`・`tui-capture.sh`・`試した手段:`・`実施者の区別` の 4 語は `test_i193_official_flow.sh` S21 が grep するので消さない（表5）**。漏れ（表3）: Human の行は使うアカウント・URL・手順を具体的に書く、を 1 行足す。±0 行 | 内部: test_i193 の文言依存。記憶 feedback_manual_test_concrete_accounts | 本節 | - |
| plan-writing-rules.md | `**test-gate 段階の運用**`（L478〜481） | 消す（1 行残す） | Claude/Human の進め方は `test-gate/SKILL.md:41〜71` が正（手順はスキル）。L481 の `check-manual-test-executor.sh` の判定の説明は「`bash scripts/claude/check-manual-test-executor.sh I###` が Human の行の形を止める（中身の正しさは計画レビュー役）」1 行に。−3 行 | 内部: 重複 | `test-gate/SKILL.md`・`plan-issue/SKILL.md:102〜105` | - |
| plan-writing-rules.md | `### ハーネス挙動テストの実施環境（条件付き列）` | 直す | 「Claude が観測できる手段」の 1 か所として作り直す（`claude -p` の判定・`check-permission-prompt.sh`・`test-session.sh`・`tui-capture.sh`・Playwright MCP〔`frontend-verify.md`〕）。スパイク (2) と実施者の区別はここを参照。値「プレーン default 新規セッション」→「通常モード（Manual）の新しい対話セッション」。L494「既存の手動テスト文書の遡及改修は不要」は導入時の移行の注記なので消す。−3 行 | [S2]（manual = default の別名・UI 表示 Manual）。内部: 3 重の観測手段の一覧 | 本節 | - |
| plan-writing-rules.md | （足す）`## 計画変更記録の形` | 足す（統合） | 上の 2 つの記録の形を 1 つにした小節（5 行）。`## 計画変更記録` の見出しをテンプレートに足す | 内部 | 本節＋テンプレート | - |

### review-rules.md（187 行）

| ファイル | 節（見出しの文字のまま） | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| review-rules.md | `# レビュールール` / `## 参照（レビューの前提となる基準）` | そのまま | 2 つの参照先は実在 | 内部: `docs/proposals/learning_app_quality_criteria.md`・`review_perspective_framework.md` 実在 | 本節 | - |
| review-rules.md | `## 文書間の関係性記載ルール` | 直す（ほぼ消す） | 下 2 節を消し、「`I###_review.md` は計画書と同時に plan-issue が作り、計画書の `## 基本情報` が相互に指す（形はテンプレート）」1 行に。−10 行 | 内部 | テンプレート | - |
| review-rules.md | `### 計画書ヘッダの必須記載（初期作成）` | 消す | plan-writing-rules「計画書ヘッダー」の写し（自分で「要点のみ再掲」と書く）。`（再作成時 plan_I###_N）` は使われていない。−7 行 | 内部: 写し | `docs/plans/templates/plan_template.md` | - |
| review-rules.md | `### 実装後評価の記録先（新系統）` | 直す | 「旧来の通し番号付き別ファイル方式は廃止」など移行の経緯を消し、「実装後の評価は `I###_review.md` の「テスト結果」「計画との差分」「振り返り」「自律判断の記録」に書く」1 行に。−1 行 | 内部: 最近の `I545_review.md` の節 | 本節 | - |
| review-rules.md | `## レビューファイルの命名・状態管理（正準規約）` / `### 命名規則（新系統・issue 単位で一意）` | 直す | 表に今ある記録を足す: `I###_fix_diagnosis_<ts>.md`（`fix-diagnosis-review.sh`・`docs/reviews/` に 31 件）・軽い指摘の一覧 `docs/reviews/backlog/I###.md`（retro の `code-review.sh --route`）。敵対的の生成者を「review-gate 段階（敵対ステージ）」→ `scripts/claude/adversarial-review.sh` に。`<timestamp>` に同時刻の `_<n>` が付くことも 1 語。L37 の旧形式 `review001〜003` の注記は消す。（新系統）（正準規約）の語も消す。±0 行 | 内部: `adversarial-review.sh:599〜600`・`fix-diagnosis-review.sh:13`・`ls docs/reviews` | 本節 | - |
| review-rules.md | `### 状態管理（open / closed の2系統）` | 直す（表に吸収） | 表の「保存先・ライフサイクル」列と同じことを 2 行で言い直している。「旧来の3状態管理は廃止」も経緯。表に吸収して節を消す。−6 行 | 内部 | 本節の表 | - |
| review-rules.md | `## 検証の全体設計（I197）` | 直す（見出しは変えない） | 中身は今のスクリプトと一致（`blocking()`・`path_risk_trigger()`・`--route`・`ACCEPTED=R`）。直すのは L58 の理由: 「親の会話の中で裏で動くサブエージェントに検証を任せない（確認待ちになっても親から気づけない。I166）」→ 公式は今、裏のサブエージェントの承認画面を親のセッションに出す。理由を「別プロセスの `claude -p --permission-prompts none` なら判定・時間・拒否が記録に残り決定論で合否を出せる・実装した会話の文脈を持ち込まない」に差し替える（方式は変えない）。**見出し `## 検証の全体設計（I197）` は `test_i197` S4 が `grep -qxF` で完全一致を見るので変えない（表5）**。±0 行 | [S3]「Background subagents surface every permission prompt in your main session」。[S4] `/code-review` は会話を見ていない新しいサブエージェント。内部: `code-review.sh:186〜188` | 本節 | - |
| review-rules.md | 同節「止める基準は変更の種類で分ける（I205）」の表と下の箇条 | そのまま | L70 の振り分けの 1 文（約 450 字）は読みにくいが、`test_i202` D3（`code-review.sh --route`・`guard`・`docs/reviews/backlog/`）・`test_i205` D5（`関所の穴`・`最後の安全網`）が語を見るので、箇条に割るなら語を保つ。割るのは任意（−0〜+3 行） | 内部: `code-review.sh:840`（guard の Medium 以上）と一致 | 本節 | - |
| review-rules.md | 同節「review-gate ⇄ fix-loop の回数の上限（5 回目で止める）」 | そのまま | 数え方は `review-gate/SKILL.md:44`（手順）、ここは決まり。スクリプトで数えていない（スキルの指示だけ）が、文書は「自動で止める」とは書いていないので食い違いではない | 内部 | 本節（数え方の手順はスキル） | - |
| review-rules.md | `## 高リスク変更の敵対的レビューステージ（自己認証の非権威化・I086／対象と上限・I181）` | 直す（見出しの頭は変えない） | (b) の例外ファイルの集合は `path_risk_trigger()`・`workflow.md` 止めて聞く条件 2・`danger-ops.md`・`code-reviewer.md`・`plan-reviewer.md` と 6 か所にあるが、`test_i181` D6 が 3 か所の一致を、D5 がこの節の語を見る → 集合の正は `path_risk_trigger()` のまま、文書の写しはテストが守る分（ここ・workflow）だけに。L84「実装者が書く自己レビューは判定根拠にしない」と L74（検証の全体設計）が同じ主張 → L84 を消す。L85「通常の変更は従来の単発 code-review のまま（比例性）」は「検証の全体設計」層 2 と同じ → 消す。L88（計画レビューのやり直しの条件）は `workflow.md:81` が正（流れのゲート）だが、`test_i181` D10 がこの節に文を求めるので、消すならテストも直す（表5）。案: 残す。−2 行 | 内部: `test_i181_review_slim.sh:88〜127` | 本節（集合の正は `code-review.sh`） | - |
| review-rules.md | `## GitHub から復旧できない変更のレビュー観点（I182）` | そのまま | GitHub 公式の推奨（`pull_request_target` を避ける・GITHUB_TOKEN を読み取りだけに）と一致。**見出しは `test_i182_docs.sh` H4 が使う（表5）** | [S6] | 本節（一覧と理由は `danger-ops.md`） | - |
| review-rules.md | `## レビュー作成の必須ルール` / `### 基本方針` | 直す | 「品質向上と継続的改善を実現する」の標語を消し、「`I###_review.md` に評価を書き、各段階の監査記録と合わせて完了の証跡にする」1 行に。−1 行 | 内部 | 本節 | - |
| review-rules.md | `### レビュー実施タイミング` | 消す | 「アドホック修正完了後」「定期レビュー」は旧命名（`reviewXXX_AD_…`・`_PR_…`）の名残で、今の流れ（イシュー → 段階）に当たる手順が無い。イシュー対応は上の 1 行で足りる。−4 行 | 内部: 今の命名表にアドホック・定期の行が無い。`docs/claude-code-structure.md:430〜438` に旧命名が残る（表2） | - | - |
| review-rules.md | `### 記載の必須要件` | 直す | 「対象計画書へのリンク」→ テンプレートの `## 基本情報` で足りる。「重複記載の回避」は 1 行残す。「イシューとの相互参照（イシュー側の `## 対応履歴` にレビューリンク）」は使われていない（`docs/issues/closed/I4*・I5*` に 0 件）→ 消す。−10 行 | 内部: 実績 0 件 | 本節 | - |
| review-rules.md | `### レビュー内容の必須要素`（`#### A.`〜`#### D.`） | 消す | A〜D の 16 観点は `review_template.md`（変更概要・変更点・影響範囲・テスト結果・計画との差分・ロールバック）にも、実際の `I###_review.md` にも無い。評価は review-gate の code-reviewer（P1〜P9）・retro の「振り返り」が受け持つ。−24 行 | 内部: `docs/reviews/closed/I545_review.md` の節。[S4]「問題を探せと言われたレビューは必ず何か見つける。skip style」 | `review_template.md`・retro | - |
| review-rules.md | `## レビュー活用方法`（`### 継続的改善`・`### 知識共有`・`### 重要な注意事項`） | 消す | 標語だけで、決まり・手順・確かめ方が無い（「定期的なアクションアイテム確認」「品質指標の継続的モニタリング」など、当たる仕組みが無い）。後続の扱いは retro（`code-review.sh --route`・起票）が正。−19 行 | [S5]「具体的で確かめられる指示を書く」 | retro | - |
| review-rules.md | `## スキルファイル変更時の Claude Code ベストプラクティス準拠（必須）` / `### チェックリスト` | 直す | 2: 「副作用のある操作（commit・push）に `disable-model-invocation: true`」は今の流れと矛盾: 段階のスキル（implement は commit、close は push）は Skill ツールで Claude が呼ぶので `user-invocable: false` を使っている（`disable-model-invocation: true` にすると呼べない）。→「ユーザーだけが始めるスキル（/plan-issue・/grill-me）は `disable-model-invocation: true`、流れの中でだけ Claude が呼ぶ段階のスキルは `user-invocable: false`」に。4: 「250文字以内」→ 公式は `description` と `when_to_use` の合計 1,536 文字で切る・使い道を先頭に。7: 500 行は公式と一致。1: 公式と一致（**行の文言は `test_i185` TC-14⑧a が `has_line` で完全一致を見る・変えない**）。L187「このチェックは計画レビューに組み込まれている」→ `plan-reviewer.md:100〜108` が同じ 7 項目の写し（2・4 も同じ古さ）。本体をここに置き、plan-reviewer は参照に（I547）。形の検査（frontmatter のキー・description の長さ・行数）は `scripts/migration_verify/lint_skills.py` があるが CI で流れていない → 機械で止めるなら #427（公式に skills の検査機能があるかは未確認・推測）。−1 行 | [S1]（`disallowed-tools`「Tools removed…while this skill is active」・`allowed-tools`「does not restrict」・description 1,536 文字・「Keep SKILL.md under 500 lines」）。内部: `.claude/skills/*/SKILL.md` の frontmatter | 本節（plan-reviewer は参照） | #427（形の検査の自動化） |

---

## 表2 ファイルをまたぐ重複・矛盾

| 決まり | 書いてある場所（ファイル:行） | 食い違いの有無 | 正の置き場所の案 |
|---|---|---|---|
| 計画書に書いていない実装はしない／より良い方法は計画を先に直す | `CLAUDE.md:42`・`plan-writing-rules.md:67,265,276〜419`・`workflow.md:76〜81,133〜148`・`implement/SKILL.md:19,86` | 中身は同じ。`workflow.md:143〜148`「修正ツール使用前チェック（必須）」と `plan-writing-rules.md:403〜411` は同じ自問の写し。`workflow.md:144` は `MultiEdit` を挙げる（推測: 今の Claude Code の道具の一覧に MultiEdit は無い。未確認） | 絶対ルール = CLAUDE.md、流れのゲート = `workflow.md`「ゲート」、計画を直す手順・記録の形 = `plan-writing-rules.md`「計画書と実装の一致性保証ルール」。`workflow.md`「作業実行前の確認ルール」「修正ツール使用前チェック」は消す（workflow 担当の点検と合わせる） |
| 計画レビューのやり直しは方式・範囲・AC を変えたときだけ（要否を計画変更記録に 1 行） | `workflow.md:81`・`review-rules.md:88`・`plan-writing-rules.md:400`・`plan-review/SKILL.md:31`・記憶 feedback_plan_change_needs_plan_review | 食い違いなし | 決まり = `workflow.md`「ゲート」、記録の形 = `plan-writing-rules.md`。`review-rules.md:88` は `test_i181` D10 が文を求めるので残すか、テストと一緒に参照に変える。記憶は消してよい（手順書に全部ある） |
| 計画書の再作成の連番 `plan_I###_2.md` | `plan-writing-rules.md:230〜246`・`review-rules.md:12`・`workflow.md:139`・`issue-flow.md:157,317` | 実際は使われていない（closed に 0 件・plan-issue は作らない）。`issue-flow.md:317` は「計画変更記録に追記するか新規計画書（_2）」と 2 通りを許す | 計画変更記録に一本化。4 か所から連番を消す |
| 計画書の完了時の移動と「完了情報」の echo | `plan-writing-rules.md:441〜455`・`issue-flow.md:232〜266`・`close/SKILL.md:47〜`（移動）・`close/SKILL.md:127,129`（「完了情報追記」の語だけ） | 食い違いあり: close の手順に完了情報の追記が無いのに、2 つの runbook が echo で足せと言う。実績は 61/163 件で揺れ | 移動 = `close/SKILL.md`。完了情報は廃止（2 つの runbook から消す。close の語は I547） |
| 計画書の `## 基本情報`（ヘッダー） | `plan-writing-rules.md:249〜258`・`review-rules.md:9〜16`・テンプレートには無い | 食い違いあり: review-rules は「作成根拠資料」「実装後評価（未作成）」の書き方を追加で持つ。テンプレートに無いので毎回手で書く | `docs/plans/templates/plan_template.md` に入れ、2 つの runbook は消す |
| 手動テスト・実施者の基準 | `plan-writing-rules.md:459〜494`（正と明記）・`plan-issue/SKILL.md:100`・`test-gate/SKILL.md:41〜71`・`manual_test_template.md:7`・`plan-reviewer.md:190`・`check-manual-test-executor.sh:13,76,84` | 食い違いなし（I195 で整理済み）。`plan-writing-rules.md:478〜481` の「test-gate 段階の運用」は test-gate の手順の写し | 基準 = `plan-writing-rules.md`「実施者の区別」、手順 = test-gate。478〜480 を消す |
| Claude が観測できる手段（`claude -p`・`check-permission-prompt.sh`・`test-session.sh`・`tui-capture.sh`・Playwright MCP） | `plan-writing-rules.md:90,473,489〜491`（ファイル内 3 回）・`frontend-verify.md`・`github-app-setup.md:11` | 中身は同じ。「プレーン default」の呼び名だけ古い（公式は Manual） | `plan-writing-rules.md` の 1 か所（「ハーネス挙動テストの実施環境」を作り直す） |
| 見張りに判定を足す計画の 3 点 | `plan-writing-rules.md:188〜194`・`danger-ops.md:60〜63` | ほぼ同文（相互に参照し合っている） | `danger-ops.md`。plan-writing-rules は 1 行の参照 |
| 決定論テストの false-green 禁止・exit 0 で合否 | `plan-writing-rules.md:159〜166`・`plan-issue/SKILL.md:190〜191`・`plan-reviewer.md:118,120`・`code-reviewer.md:115`・`implement/SKILL.md:32` | 食い違いなし | 本体 = `plan-writing-rules.md`、スキル・レビュー役は参照（I547） |
| 決定論テストの対象の選び方（写しを作らない） | `plan-writing-rules.md:168〜177`・`plan-reviewer.md:119`・`code-reviewer.md:116`・記憶 feedback_tests_guard_only_hard_to_notice | 食い違いなし。レビュー役は参照している | `plan-writing-rules.md`。記憶は消してよい |
| 消費箇所の全件列挙・分岐のパリティ | `plan-writing-rules.md:101〜115`・`plan-reviewer.md:72,109,110`・`code-reviewer.md:78,79`・`grill-me/SKILL.md:70,73` | 食い違いなし | 本体 = `plan-writing-rules.md`（パリティは #538 の結果で移す可能性） |
| 手元で全テストを流し直さない／計画前の既存テストの実行 | `plan-writing-rules.md:121〜133`（計画前に pytest・npm test を流す）・`test-gate/SKILL.md:3,30`（手元で流し直さない）・記憶 feedback_no_local_full_tests_duplicating_ci | **矛盾あり** | 「CI が正。ベースラインは develop の CI の結果で見る」を `plan-writing-rules.md` に。記憶は移して消す |
| lint のコマンド | `plan-writing-rules.md:139〜144`（flake8・`npx eslint`）・`pre-commit.md:44,47`（ruff・`lint-frontend.sh`） | **矛盾あり**（flake8 は使っていない） | 道具とコマンド = `pre-commit.md`。plan-writing-rules からコマンドを消す |
| スキルの BP チェックリスト（7 項目） | `review-rules.md:170〜187`・`plan-reviewer.md:100〜108`・`scripts/migration_verify/lint_skills.py`（CI 外） | 2 か所とも「副作用は `disable-model-invocation`」「description 250 文字」が古い（今の段階のスキルの設計・公式の 1,536 文字と食い違う） | 本体 = `review-rules.md`、plan-reviewer は参照（I547） |
| 例外のファイルの集合（GitHub から復旧できない） | `code-review.sh:309〜317`（正）・`review-rules.md:82`・`workflow.md:44`・`danger-ops.md:66〜80`・`code-reviewer.md:171`・`plan-reviewer.md:220` | 今は一致（`test_i181` D6 が 3 か所を照合） | 正 = `path_risk_trigger()`。文書は参照＋テストが守る写しだけ |
| 裏のサブエージェントに検証を任せない理由 | `review-rules.md:58`（「確認待ちになっても親から気づけない」）・記憶 feedback_review_with_subagent_adversarial（「Agent ツールで独立レビュアーを起動」） | **矛盾あり**: 記憶は Agent ツール（裏のサブエージェント）でのレビューを勧め、review-rules は禁じる。review-rules の理由も公式の今の挙動と合わない（[S3]） | 決まり = `review-rules.md`（理由を直す）。記憶は古いので消す（独立・反証のマンデートは review-rules と adversarial-review.sh にある） |
| レビュー役の時間・攻め筋の上限 | `review-rules.md:86`（1 周 10 分・攻め筋 3 本）・`adversarial-review.sh:30〜31`・記憶 feedback_timebox_review_agents | 食い違いなし（スクリプトが締め切る） | `review-rules.md`。記憶は「手で起こすサブエージェント（この点検のような）にも時間・攻め筋の上限を書く」部分だけ残すか `review-rules.md` に 1 行（表3） |
| レビューファイルの命名（旧 `reviewXXX_IYYY.md`・AD・PR） | `docs/claude-code-structure.md:426〜440`・`review-rules.md:37`（廃止の注記） | **矛盾あり**: `docs/claude-code-structure.md` は旧命名・「9 承認ポイント」（`:350`）など I193 前の内容のまま（runbooks の外。I546 の対象に入れるかは計画で決める） | `review-rules.md`。`claude-code-structure.md` は消すか索引だけにする案（計画で決める） |
| テンプレートの節と I###_review.md の節 | `review_template.md`（6 節）・`plan-issue/SKILL.md:107`（「自律判断の記録」節を作る）・retro（「振り返り」節） | テンプレートに `## 自律判断の記録` が無く、スキルの指示で毎回足す | `review_template.md` に足す（本イシューで直せる文書） |

---

## 表3 漏れの候補（足す／足さない）

| 足す決まり | 足す理由 | 置き場所 |
|---|---|---|
| **足す**: 計画の「確定事項と自律判断」で技術を選ぶとき・仕組みを自作すると決める前に、`rules/` の当たる節と依存のファイル（`frontend/package.json`・`backend/requirements*.txt`）を開き、確かめた事実（ファイル:行）を添える | 4 回起きた（I487・I513・I524・I494）・マージ依頼の後に作り直し＝気づきにくく手戻りが大きい。記憶 feedback_check_rules_and_deps_before_building にだけある | `plan-writing-rules.md` 事前調査（2 行） |
| **足す**: 受け入れ条件は手段（見る範囲・ファイル）でなく結果（どの周でも〜しない等）で書く | I486 で close 後に戻した。レビュー役が「AC の文言どおり」で止めず目的の穴が通る＝気づきにくい。記憶 feedback_backlog_purpose_check にだけある | `plan-writing-rules.md` の 2) 受け入れ条件（1 行） |
| **足す**: テストのために monkeypatch・一時の差し替えが要るなら、まず本番の設計を直してその差し替えを不要にできないかを計画の案の第一候補にする | 記憶 feedback_design_for_testability にだけある。レビューで捕まりにくい（テストは通る） | `plan-writing-rules.md` の 6) テスト計画（1 行） |
| **足す**: 人の手動テストの行は、使うアカウント（無ければ作る手順）・URL・手順を具体的に書く | 記憶 feedback_manual_test_concrete_accounts にだけある。人が手を止める往復が出る。ただし人の行は少なく、その場で人が気づく → 1 行だけ（テンプレートのコメント） | `manual_test_template.md` のコメント（`plan-writing-rules.md`「実施者の区別」の Human の行に 1 語でも可） |
| **足す**: 計画書・レビュー文書のテンプレートに、実際に毎回書いている節（`## 基本情報`・`### 調査結果`・`### 修正アプローチ`・`## 計画変更記録`・`## 自律判断の記録`）を入れる | 決まりは書き方を求めるのに形の正が無い（毎回手で足す）。読む量も減る | `docs/plans/templates/plan_template.md`・`docs/reviews/templates/review_template.md` |
| **足す**: レビューの命名の表に `I###_fix_diagnosis_<ts>.md` と `docs/reviews/backlog/I###.md` | 実在する記録が規約に無い（close の回収の対象か分からない） | `review-rules.md` 命名の表 |
| **足す（任意）**: 手で起こすレビュー・点検のサブエージェントにも時間と攻め筋の上限を書く | 記憶 feedback_timebox_review_agents（4 時間超）。スクリプト経由のレビューは締め切りがあるが、手で起こす分には決まりが無い。ただし発生は手動起動のときだけ | `review-rules.md`「検証の全体設計」の箇条 1 行 |
| 足さない: 計画で SKILL.md・agents の書き方の観点を増やす | I547 の範囲 | - |
| 足さない: 計画の各節の分量の上限 | その場で読む人（計画レビュー役）が気づける。手順を足さない原則 | - |
| 足さない: 「Bash を束ねない」を plan-writing-rules に | 計画書の書き方ではなく実行時の決まり。計画書のコマンド例を単体形に直せば足りる（本表1 で例のコマンドを消す）。置き場所は `common-commands.md` か `danger-ops.md`（サンドボックス）で他担当の点検が決める | - |
| 足さない: `/simplify` の範囲外れの確認 | implement 1.5) にあり、review-gate で捕まる | - |
| 足さない: レビューの「skip style」 | 公式が勧める（[S4]）が、止める基準は既にスクリプト（`blocking()`）が種類別に決め、Low は止めない＝同じ効果がある | - |

---

## 表4 中身の変更案

| 案 | 今の決まり | 変える中身 | 理由 | 推奨 |
|---|---|---|---|---|
| C1（境目の確認用） | `plan-writing-rules.md:403〜411`「1文字でも違えば中断」「5 つの質問にすべて YES でなければ修正ツールは使用禁止」 | この強調の文を消し、「計画にない変更・より良い方法は実装の前に計画書を直す（計画変更記録）」の基本原則 1 文に寄せる。ユーザーへの確認の場面（要件・基本設計・UI/UX のときだけ）・plan-review を通す条件は**変えない** | 同じ主張の 3〜4 重の繰り返しで、守らせる仕組みは計画レビュー前のコード変更禁止とレビューの計画照合（決定論の守りは変わらない）。[S4] 強調を足すのは守らせる手段にならない | ユーザーの関わり方は変わらないので、本来は「言い回し・重複の整理」。CLAUDE.md 絶対ルール 1 の説明部分に触れるので、念のため一覧に出す |

ほかに、確認の場面を増やす・減らす・承認の対象を変える案は無し（`plan-writing-rules.md:25` の UI の確認・`review-rules.md:87` の上限到達の扱いは `workflow.md`「止めて聞く条件」1・3 と一致しており変えない）。

---

## 表5 名前・置き場所を変える節を参照している行（スクリプト・テストの文言依存を含む）

closed/・legacy/・`docs/migration/`（移行の記録）・`docs/reviews/I###_*` の監査記録は除く。

| 変える節（案） | 参照している行 | 文言依存のテスト |
|---|---|---|
| plan-writing-rules「見張り（`pretooluse_guard.py`）に判定を足す計画（I430）」→ 消して 1 行の参照に | `docs/runbooks/danger-ops.md:60`（節の名前を括弧で参照） | なし |
| plan-writing-rules「計画書ヘッダー（文書間の関係性）」→ テンプレートへ | `docs/runbooks/review-rules.md:10`（この行自体も消す案） | なし |
| plan-writing-rules「計画書ファイル名ルール」（`_2` 連番）→ 消す | `docs/runbooks/workflow.md:139`・`docs/runbooks/issue-flow.md:157,317`・`docs/runbooks/review-rules.md:12` | なし |
| plan-writing-rules「計画書完了時のルール」→ 消す | `docs/runbooks/issue-flow.md:232〜266`（同じ echo）・`.claude/skills/close/SKILL.md:127,129`（「完了情報追記」の語。I547） | なし |
| plan-writing-rules「既存テストの事前実行」「lint エラー数の事前計測」→ まとめる | 名前の参照なし | なし |
| plan-writing-rules「計画書と実装の一致性保証ルール（絶対遵守）」→ 見出しから「（絶対遵守）」を外す | `docs/claude-code-structure.md:37,352`（古い説明。表2） | なし |
| plan-writing-rules「ハーネス挙動テストの実施環境（条件付き列）」→ 「Claude が観測できる手段」に作り直す | `.claude/agents/plan-reviewer.md`（「実施環境」の語。名前の参照はなし・I547 で確認）・`docs/tests/closed/*`（過去記録・除外） | なし |
| plan-writing-rules「実施者の区別」（**名前は変えない**。中を縮める） | `scripts/claude/check-manual-test-executor.sh:13,76,84`・`.claude/skills/plan-issue/SKILL.md:100`・`.claude/agents/plan-reviewer.md:190`・`docs/tests/templates/manual_test_template.md:7` | **あり**: `scripts/claude/tests/test_i193_official_flow.sh:441`（S21 `s21_rules_pw`: `tui-capture.sh`・`試した手段:`・`実施者の区別`・`この基準の正はこの節` の 4 語を plan-writing-rules に求める）・`:446`（plan-issue に `` plan-writing-rules.md`「実施者の区別」 `` を求める） |
| plan-writing-rules 10〜15 の番号（**変えない**） | `docs/runbooks/ux-rules.md:6`・`docs/runbooks/issue-flow.md:348`・`.claude/skills/plan-issue/SKILL.md:149〜165` | なし |
| plan-writing-rules「決定論テストの対象の選び方」（**変えない**） | `.claude/agents/plan-reviewer.md:119`・`.claude/agents/code-reviewer.md:116` | なし |
| plan-writing-rules「高リスクの計画の「必ず確かめる項目」（I228）」（**変えない**） | `docs/runbooks/review-rules.md:73` | なし |
| review-rules「文書間の関係性記載ルール」「計画書ヘッダの必須記載」→ 消す | 名前の参照は `docs/runbooks/template-sync.md:86`（「文書間の関係性ルールの変更」一般名。直接の参照ではない） | なし |
| review-rules「レビュー作成の必須ルール」「レビュー活用方法」→ 縮める・消す | 参照なし | なし |
| review-rules「検証の全体設計（I197）」（**見出しは変えない**） | `.claude/agents/code-reviewer.md:185` | **あり**: `test_i197_adversarial_process.sh:444`（S4 `grep -qxF '## 検証の全体設計（I197）'` 完全一致）・`test_i202_ledger_cleanup.sh:446,657,665`（`台帳の目印`・`code-review.sh --route`・`guard`・`docs/reviews/backlog/`）・`test_i205_stop_criteria.sh:268,273,280`（`関所の穴`・`最後の安全網`、`止めるのは High 以上だけ` が無いこと） |
| review-rules「高リスク変更の敵対的レビューステージ（…）」（**見出しの頭は変えない**。L84・L85 を消す） | `.claude/skills/review-gate/SKILL.md:50` | **あり**: `test_i181_review_slim.sh:88,111〜127`（`H_RR="## 高リスク変更の敵対的レビューステージ"` の前方一致。D3 `種類ごと`・`止める場所・方式の見直し`、D5 `GitHub が最後の守り`・`danger-ops.md`・`path_risk_trigger`・6 つの例外パス、D8 節の中のパスの実在、D10 `計画レビューのやり直しは、計画の方式・範囲・受け入れ条件を変えたときだけ`、D2 旧上限の語が無いこと）。L88 を移すなら D10 も直す |
| review-rules「GitHub から復旧できない変更のレビュー観点（I182）」（**変えない**） | `docs/runbooks/danger-ops.md:75`（`review-rules.md` をファイル名で参照） | **あり**: `test_i182_docs.sh:59,63,67`（H4 の見出し完全一致・`pull_request_target`・`.secrets.baseline`・節の中のパスの実在） |
| review-rules「スキルファイル変更時の Claude Code ベストプラクティス準拠（必須）」チェックリスト 2・4 を直す | `.claude/agents/plan-reviewer.md:100〜108`（同じ 7 項目の写し・I547）・`docs/proposals/automation_over_manual_checks_proposal.md:65,164,169`（提案書） | **あり**: `test_i185_harness_docs.sh:148`（TC-14⑧a 項目 1 の行を `has_line` で完全一致。1 は変えない）。項目 2・4 には文言依存なし |
| review-rules（ファイル名で参照するだけ） | `scripts/claude/code-review.sh:307`（コメント）・`scripts/claude/tests/test_adversarial_trigger.sh:89`（パスが NO になること）・`CLAUDE.md:24`・`docs/runbooks/onboarding.md:185` | ファイル名を変えない限り影響なし |
| plan-writing-rules（ファイル名で参照するだけ） | `CLAUDE.md:17`・`.claude/skills/plan-issue/SKILL.md:12`・`docs/runbooks/onboarding.md:184`・`docs/claude-code-structure.md:37,110,227,334,454,641` | ファイル名を変えない限り影響なし |

---

## 行数の見込み

| ファイル | 今 | 提案どおりにしたとき（見込み） | 主な減り |
|---|---|---|---|
| `docs/runbooks/plan-writing-rules.md` | 494 | 約 190〜210 | 一致性保証ルールの繰り返し（約 160 → 約 25）・完了時ルール（15 → 0）・計画書作成ルール詳細とヘッダー（約 60 → 約 15）・事前のテスト/lint 3 節（約 40 → 約 8）・観測手段の 3 重（−約 10）。テンプレートに約 +10 行移る |
| `docs/runbooks/review-rules.md` | 187 | 約 95〜105 | レビュー内容の必須要素 A〜D・活用方法（約 43 → 0）・ヘッダーの写しと命名の経緯（約 25 → 約 12） |

注: 見込みは節ごとの目安の合計で、まとめ直しの書き方で ±15 行ほど揺れる（推測）。
# I546 点検 C: danger-ops.md・pre-commit.md・dependency-audit.md・harness-audit.md・template-sync.md・common-commands.md

点検日: 2026-11-17。作業ツリー: harness-1（feature/I546-process-rules-bp-review）。Claude Code 2.1.326。
「推測」と書いたものは実物・公式で確かめきれていないもの。

照らした公式の文書（いずれも 2026-11-17 に参照）:
- [S1] https://code.claude.com/docs/en/sandboxing.md （excludedCommands は「呼び出しの中のコマンドが全部当たるときだけ外」・リダイレクト・`cd`・`$(...)` が入ると全体が中・設定ファイル〔.claude の settings・.mcp.json〕の書き込みは自動で拒否・`FOO=bar cmd` 形は通常の許可の流れ）
- [S2] https://code.claude.com/docs/en/permissions.md （複合コマンドは `&& || ; | |& &` と改行で分け、**部分コマンドがそれぞれ allow に当たれば確認なし**。deny／ask はどれか 1 つに当たれば効く。Read／Edit の deny は Bash の `cat`・`head`・`tail`・`sed`・`tee`・リダイレクトにも効く。`Edit(...)` は Write・MultiEdit にも効く）
- [S3] https://code.claude.com/docs/en/hooks.md （`onFailure: "block"`〔v2.1.295 以降〕・`timeout`。未設定だと PreToolUse の時間切れ・exit 0/2 以外は止めない）
- [S4] https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference （cooldown の `semver-*-days` は pip・npm 等だけで docker・docker-compose・github-actions・pre-commit は不可。cooldown はセキュリティの修正には効かない）
- [S5] https://docs.github.com/en/code-security/secret-scanning/working-with-secret-scanning-and-push-protection/working-with-push-protection-from-the-command-line （拒否されたら秘密を消して amend／rebase して push し直す。bypass の手順がある）
- [S6] https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository （Settings > Actions > General「Require actions to be pinned to a full-length commit SHA」がある）
- 実物: `.claude/settings.json`・`.pre-commit-config.yaml`・`.github/dependabot.yml`・`.github/workflows/{ci,dependency-audit,e2e}.yml`・`docker-compose.yml`・`frontend/package.json`・`backend/Dockerfile`・`backend/core/settings.py`・`scripts/claude/*`・`type grep`（Claude Code の対話シェルの grep は今も ugrep の関数に置き換わっている）

---

## 表1 節ごとの判定

| ファイル | 節 | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| danger-ops.md | 冒頭（4 条件「計画書に明記＋ユーザー明示承認＋PR に danger-approved＋DANGER_OK=1」） | 直す（言い回し） | 4 条件を「何が強制され、何が人の約束か」で書き分ける（DANGER_OK=1 → 見張りが承認画面を出す＝強制／計画書の Danger Ops 欄・ユーザー承認＝人の約束／danger-approved＝ラベルを確かめる仕組みが無い）。中身（danger-approved をやめる等）は表4 | 内部: `danger-approved` を読むワークフロー・スクリプトが無い（`grep -rn danger-approved .github scripts` が 0 件） | danger-ops.md 冒頭 | - |
| danger-ops.md | 例（DB／Git／Docker／Files／ワークツリー） | 直す | ①Git 行の「未コミット変更があるファイルへの checkout/restore」注記を下の節と 1 か所にまとめる ②「大規模 rebase」は下の「見張りが判定しないもの」と食い違う（表2・表4） ③ワークツリー行（13 行目）の後半「Bash の書き込みはサンドボックスが止め…」はサンドボックス節と worktree.md §9 の写し → 1 文の参照に ④Files「secrets 操作」は曖昧 → 「秘密ファイルの表示・送信（下の見張り 3.）」 −3 行・文字数 −30% | 内部: 同じ決まりが 3 か所（例・未コミット節・common-commands 72 行） | danger-ops.md「例」 | - |
| danger-ops.md | サンドボックス（第 1 層・I430） | 直す＋足す | ①公式の挙動に合わせ「外に出るのは呼び出しの中のコマンドが**全部**一覧に当たるときだけ。リダイレクト・`cd`・`$(...)`・前置きの代入（`X=1 cmd`）が入ると全体が中」と書く（今は git＋非 git の例だけ。記憶 reference_sandbox_prefix_pipe_breaks_exclusion の中身を移す）②`gh` を中で動かすと App の鍵が読めず失敗、と 1 行（気づきにくい）③common-commands.md「Bash 実行作法」をここに吸収（表2）④19 行目「settings.json は Claude Code が読み取り専用にする」→ 公式どおり「設定ファイル（.claude の settings・.mcp.json）」に ⑤26 行目の復旧手順（settings.json だけ古く残ったとき）は残す ±0 行 | S1・S2、記憶 reference_sandbox_prefix_pipe_breaks_exclusion | danger-ops.md「サンドボックス」 | - |
| danger-ops.md | 公式・GitHub に任せて消した判定（表） | そのまま | — | 内部: 実物の deny・sandbox と一致 | danger-ops.md | - |
| danger-ops.md | 見張りの扱い「確認を出す基準（A）〜（C）」 | そのまま（言い回しのみ） | 承認の範囲を決める核なので中身は変えない。43 行目「語の一覧の正は `_RISKY_WORDS`」の方式は良い | 内部 | danger-ops.md | - |
| danger-ops.md | 見張りの扱い 判定の順 1.〜5.（45〜51 行） | 直す（大幅に縮める） | 2.（48 行・1 行で約 1,500 字）の cd の読み方・`GIT_DIR=`・外のリポジトリの設定などの**実装の仕様**と、4.（50 行）の `_container_safe`・`/tmp/` 書き込みの細部は、Claude が作業中に要らない。「何を止める／確認するか」の 1 行ずつに縮め、細部は「正は `pretooluse_guard.py` の docstring とテスト（`guard_must_stop_cases.txt`）」と参照にする。文字数 −70%（行数は −0〜2） | 内部: 見張りの仕様を文書に写すと、見張りを直すたびに文書がずれる（I200 の fix_diagnosis で写しの点検が要った）。記憶 feedback_local_guard_github_last_line | `pretooluse_guard.py`（仕様）／danger-ops.md（方針） | -（docstring 側に足すのは #520） |
| danger-ops.md | 見張りが失敗したとき | 直す（縮める） | 公式の `timeout: 20`・`onFailure: "block"` は公式の文言どおりで正しい。512MB・語の判定の部分を 1 文に。`! git restore …` の復旧手順は残す（気づきにくく、Claude が自分で直せない） −0 行・文字 −40% | S3（onFailure・timeout・既定では時間切れで止まらない） | danger-ops.md | - |
| danger-ops.md | 編集の確認（I200） | 直す（縮める） | 語の一覧（`secrets`・`write`…・`exclude`…）は見張りの写し → 「増えたときだけ確認（語の正は見張り）」に。「確認なしの一覧（Dockerfile…）」は残す | 内部: 写しの削減 | `pretooluse_guard.py` | - |
| danger-ops.md | 見張りを直したら 4 つのテスト | 直す（軽微） | 4 本のうち `test_guard_must_stop_cases.sh` は CI でも流れる旨は残す。説明を各 1 句に | 内部: `scripts/claude/tests/test_guard_corpus_diff.sh:5` のコメントは「3 つのテスト」で文書（4 つ）と食い違い | danger-ops.md | #520（スクリプトのコメント側） |
| danger-ops.md | 新しい秘密を置くとき（denyRead・deny の 2 項目、56〜57 行） | 直す（最新化） | ①57 行「名前を足さないと Read／Edit ツールでの読み書きが確認なしで通る（Bash での読み出しは見張りが確認に回す）」→ 公式では Read／Edit の deny は Bash の `cat` 等とリダイレクトにも効く。「deny に足せば Read・Edit・Bash の代表的な読み書きの両方に効く。スクリプト経由の読み取りはサンドボックスの denyRead が止める」に ②2 項目を 1 項目にまとめる −1 行 | S2（Read and Edit deny rules apply to … `cat`, `head`…）。この session の sandbox 設定に `**/.env` 等が denyRead として入っていることを観測（Read の deny がサンドボックスへ反映される。リポジトリの外に効くかは推測） | danger-ops.md | - |
| danger-ops.md | DANGER_OK=1 を付けても人の承認 | そのまま（位置を冒頭へ） | 冒頭の 4 条件の「強制される部分」として冒頭に寄せる（100 行の重複を消せる） | 内部 | danger-ops.md 冒頭 | - |
| danger-ops.md | 見張りが判定しないもの | 直す | 「大規模 rebase」は冒頭の例と食い違う（表2・表4）。ほかはそのまま | 内部 | danger-ops.md | - |
| danger-ops.md | 見張りに判定を足すときの決まり（I430） | そのまま | plan-writing-rules.md:190 は「要約」と明記して正をここに置いている。良い形 | 内部 | danger-ops.md | - |
| danger-ops.md | 見張りを避ける書き方を使わない | そのまま | — | 内部 | danger-ops.md | - |
| danger-ops.md | GitHub から復旧できる範囲（I182） | そのまま（1 か所直す） | 多くのスキル・レビュー役・テストが見出しで参照。中身は今も正しい。75 行目の対策「見張りが…語が増えたときだけ確認」は上の「編集の確認」の写し → 「上の『編集の確認』」と参照に | 内部: 参照 7 か所（表5） | danger-ops.md | - |
| danger-ops.md | 秘密情報を push してしまったとき（I182） | 直す（軽微） | ①4. の `GH013` は「`GH013`／`GH009`・`push protection`・`Push cannot contain secrets`」のように文言で探す形に（エラーコードは推測: ルールセット経由は GH013、旧来は GH009 と記憶。公式 S5 はコードを書いていない）②3. の手順は公式どおり（直近なら `--amend`、それより前は対話の rebase だが、このハーネスでは対話の rebase が使えないので「計画書と承認で」と書く今の形でよい）③2. の「本番の設定」は本番がまだ無い（記憶 project_no_production_env）が、将来も通るので残す | S5 | danger-ops.md | - |
| danger-ops.md | 未コミット変更の取り消し | 消す（例の Git 行に吸収） | 「一時変更は Edit で戻す」の 1 文だけ例の Git 行の注記に残す −7 行 | 内部: 例の Git 行・common-commands.md 72 行と 3 重 | danger-ops.md「例」 | - |
| danger-ops.md | 実行テンプレ | 消す | 計画書のひな形 `docs/plans/templates/plan_template.md:47`「Danger Ops（有無/手順/ロールバック）」が同じ役。4 項目（影響範囲・代替案・ロールバック・実行コマンド）はひな形の側に寄せる −5 行 | 内部: 重複 | `docs/plans/templates/plan_template.md` | - |
| pre-commit.md | 概要 | そのまま | — | — | pre-commit.md | - |
| pre-commit.md | セットアップ（pipx・pre-commit・detect-secrets・install） | 直す | ①onboarding.md の初回の準備へ移し、ここは参照にする（初回の手順は onboarding に集める）②`pipx install detect-secrets` は版が固定されていない。フックは `.pre-commit-config.yaml` の `rev: v1.5.0`、baseline も `"version": "1.5.0"` → `pipx install detect-secrets==1.5.0`（または pre-commit 経由の実行）に。版が違うと baseline の再生成で差分が出る ③pre-commit 本体はハーネスのテストでは `scripts/claude/tests/uv.lock` で固定されている（onboarding.md:133）のに、git のフックは pipx の無固定。どちらかに寄せる案は #427（推測: `uv run --project scripts/claude/tests pre-commit install` で足りるかは未確認） −15 行 | 内部: `.pre-commit-config.yaml`・`.secrets.baseline` の版。pre-commit 公式（https://pre-commit.com/ ・照合は記憶ベースで未取得）| onboarding.md | #427（pre-commit 本体の入れ方の一本化） |
| pre-commit.md | フック一覧 | 直す（最新化） | ①`check-dependabot`（check-jsonschema）が表に無い → 足す ②shellcheck の対象「`scripts/` 等」→ 実物は `files: ^scripts/` だけ ③detect-secrets の対象「全体」→ `package-lock.json` を除く ④ruff・bandit の説明は実物どおり。表は「正は `.pre-commit-config.yaml`」と 1 行添え、細かい引数は写さない ±1 行 | 実物 `.pre-commit-config.yaml` | `.pre-commit-config.yaml` | - |
| pre-commit.md | detect-secrets JWT 検出について | 消す（下の baseline 節に統合） | 再生成コマンドが 53 行と 127 行に 2 回。`e2e/.auth/` の 1 文だけ残す −4 行 | 内部: 重複 | pre-commit.md「baseline の更新」 | - |
| pre-commit.md | 日常的な使い方 | 直す（縮める） | 2 小節を 3 行に。「merge・cherry-pick・rebase で作るコミットではフックが動かない」は danger-ops.md の表にあるので参照だけ −6 行 | 内部 | pre-commit.md | - |
| pre-commit.md | ESLint のフックの流し方（I468） | そのまま | `lint-frontend.sh` がこの見出しを案内文に出している（見出し名を変えない）。`docker image prune`（任意）は danger-ops の「volume prune」と違いデータを消さないことを明記済みで良い | 内部: `scripts/claude/lint-frontend.sh:5,29` | pre-commit.md | - |
| pre-commit.md | detect-secrets の誤検知への対処（方法 1・2） | 直す | ①方法 1 の `detect-secrets audit` は対話式で Claude は使えない（対話の入力不可）→「人が行う」と明記するか、Claude は方法 2（`# pragma: allowlist secret`）を使う、を先に書く ②`.secrets.baseline` の編集は `.claude/settings.json` の `ask`（承認画面が出る）と 1 行 ③コミット例（`git add`・`git commit -m`）は消す −8 行 | 内部: settings の `ask: Edit(.secrets.baseline)` | pre-commit.md | - |
| pre-commit.md | `.secrets.baseline` の更新 | 直す（統合先） | JWT 節を吸収。`--force-use-all-plugins` 必須の注意は気づきにくく被害が大きいので残す。⚠️ の絵文字は外す。コミット例は消す −3 行 | 内部 | pre-commit.md | - |
| pre-commit.md | ロールバック | 消す | `git rm .pre-commit-config.yaml .secrets.baseline` は秘密情報の検査（安全装置・CI の必須チェック・`test_i182_secret_gates.sh` が守る）を丸ごと外す手順で、今の運用ではやってはいけない操作。残すと誤って使われうる −7 行 | 内部: workflow.md「止めて聞く条件」2・danger-ops.md の表 | — | - |
| dependency-audit.md | 冒頭・役割分担 | そのまま | — | — | dependency-audit.md | - |
| dependency-audit.md | 仕組みの概要 | 直す | ①16 行「検知するのは GitHub イシューのみ」→「起票先は GitHub のイシューだけ」②「PR ゲートと同一条件」は backend・frontend については正しいが、CI は `tools/api-types` も `npm audit --audit-level=high` で見ているのに定期監査は見ていない（文書の言う「同一」が成り立たない対象がある）| 実物 `ci.yml:178-179`・`dependency-audit.yml` | dependency-audit.md | #520（定期監査に api-types が無い） |
| dependency-audit.md | 検知時の対応手順 | 直す（軽微） | ①`/grill-me I<番号>` で本文を書き足す、は今のスキル構成（`.claude/skills/grill-me`）と合う ②ただし自動起票の本文（`dependency-audit-issue.sh:30`）は「/issue-bootstrap でローカルイシュー化して対応する」と書いていて、この手順（別のイシューを起票し直さない・GitHub だけで管理）と食い違う | 実物 `scripts/claude/dependency-audit-issue.sh:30` | dependency-audit.md | #520（スクリプトの本文） |
| dependency-audit.md | 手動実行 | そのまま | — | 実物 `simulate_failure` あり | dependency-audit.md | - |
| dependency-audit.md | 検知漏れ・workflow 失敗時の確認 | そのまま | — | — | dependency-audit.md | - |
| dependency-audit.md | 前提・変更時の注意 | 直す（縮める） | 42・43 行は同じこと（ci.yml と同一条件を保つ）→ 1 項目に −1 行 | 内部 | dependency-audit.md | - |
| dependency-audit.md | Dependabot：見張るもの・見張らないもの | 直す（最新化） | 見張る一覧に `tools/api-types` の npm（I493）が無い → 足す。もしくは一覧を書かず「正は `.github/dependabot.yml`」とし、見張らないもの（uv・動かす環境の版上げ）と理由だけ残す（写しを減らす。推奨） −1 行 | 実物 `.github/dependabot.yml`（npm が 3 か所） | `.github/dependabot.yml` | - |
| dependency-audit.md | Dependabot：届き方 | そのまま | cooldown の記述（7 日・pip と npm の major は 14 日・他は版別不可・セキュリティの修正は待たない）は公式と一致。`target-branch` の注意は設定ファイルのコメントと重複しているが、設定ファイル側は「理由の正」なので文書は 1 行参照でも可 | S4 | `.github/dependabot.yml`（コメント） | - |
| dependency-audit.md | Dependabot：届いた PR の通し方 | 直す（軽微） | `/issue-bootstrap で` → 「issue-bootstrap で（Claude が自分で起票）」（記憶 feedback_propose_issue_title_on_separate_issue の決まりに合わせる） | 内部 | dependency-audit.md | - |
| dependency-audit.md | 取り込んだあと手元でやること | 直す | 起動コマンドの説明は common-commands.md の写し → 「common-commands.md『開発環境起動』の 1 コマンドだけ」と 1 行に −1 行 | 内部 | common-commands.md | - |
| dependency-audit.md | 固定の決まり（SHA・指紋・services の例外） | そのまま | 「action を SHA で書く」は GitHub の設定「Require actions to be pinned to a full-length commit SHA」で強制できる（公式の機能） | S6 | dependency-audit.md | #427（SHA 固定を GitHub の設定で強制する） |
| dependency-audit.md | 止まったときに見る場所 | そのまま | 「Settings → Advanced Security」は今の画面名（推測: 2025 年に Code security から改名） | — | dependency-audit.md | - |
| dependency-audit.md | 全体（定期監査そのもの） | そのまま（回す） | 自作の毎日の pip-audit／npm audit → イシュー起票は、GitHub の Dependabot alerts（新しい CVE で通知）＋security updates と役割が重なる。置き換えられるかは「alerts をイシューにする仕組みが要るか・bot が alerts を読めるか」次第（推測） | 内部＋GitHub の Dependabot alerts | — | #427 |
| harness-audit.md | 冒頭・項目の表 | 足す | ①Claude の手元の記憶（`~/.claude/projects/<プロジェクト>/memory/`）を項目に足す（I546 で「プロジェクトの決まりを記憶に置かない」と決めた。点検で記憶に決まりが溜まっていないかを見る）②利用者の設定（`~/.claude/settings.json`・`~/.claude/CLAUDE.md`）と `.worktreeinclude` を見張りと設定の行に足す（どちらもハーネスの挙動を変える。推測: 今の総点検で漏れうる）③`docs/claude-code-structure.md`（全体の構成の説明）を手順書の行に足すか、消す判断を記録（表2） +2 行 | 内部: I546 設計確認メモ・`.worktreeinclude` は worktree.md:49 | harness-audit.md | - |
| harness-audit.md | GitHub の認証・鍵・アカウント | そのまま | — | — | harness-audit.md | - |
| harness-audit.md | 古い鍵の点検コマンド | 直す（要確認） | ①2 行目 `GH_APP_READONLY= GH_APP_DISABLE=1 gh auth status …` は前置きの代入付きなので、公式どおりならサンドボックスの中で動く（S1）。中は通信が無い（`allowedDomains: []`）ので `gh auth status` の鍵の有効性の確認が通信エラーになり、状態の欄が実態と違って出うる（推測・未実行）②1 行目の `grep -c -E` は対話シェルの ugrep に置き換わる（common-commands.md の注意の対象。`-c -E` で誤動作するかは未確認） | S1・`type grep` の結果 | harness-audit.md | #520（コマンドが今の環境で正しく動くかの確認） |
| template-sync.md | ファイル全体（基本方針〜重要な注意事項） | 消す（決まりは 2 行に縮めて移す） | 中身は「決まりを変えたら、対応するひな形（`docs/*/templates/`）も同じ PR で直す」「runbook を足す・名前を変える・消すときは CLAUDE.md の参照先も直す」の 2 つだけ。`ls -la … 2>/dev/null` の確認・`cp … .bak`・チェックリストは、ひな形が 5 本に固定された今は不要（`.bak` はリポジトリに未追跡のファイルを残す悪い手順）。2 つの決まりは plan-writing-rules.md（計画書の「実装対象」にひな形・CLAUDE.md の参照を挙げる）に 2 行で移す。CLAUDE.md の参照先との突き合わせ（`comm -3`）は「気づきにくい」ので、残すなら決定論テストに（#520 の範囲） −93 行 | 内部: ひな形は `docs/{issues,plans,reviews}/templates/` に計 5 本で固定・スキル（issue-bootstrap）はひな形を名指しで読む | plan-writing-rules.md（2 行） | #520（参照先の突き合わせをテストにするなら） |
| common-commands.md | エラー調査手順 | 直す | `python manage.py analyze_logs --last-errors=1` はホストでは動かない（Django はコンテナの中だけ）→ `docker compose exec -T backend python manage.py analyze_logs --last-errors=1` | 実物: `backend/core/management/commands/analyze_logs.py` はある・ホストに Django の環境が無い | common-commands.md | - |
| common-commands.md | 開発環境起動 | そのまま | 起動コマンドの正（frontend-verify.md・worktree.md・dependency-audit.md が参照）。test_i213 の V1 が固定 | 実物 | common-commands.md | - |
| common-commands.md | worktree ごとのポート分離 | 直す | ①説明は worktree.md §6 の写し → コマンド 1 行（`bash scripts/claude/wt-ports.sh`）と参照に ②確認の `docker compose config \| grep -A1 published` は見張りの「秘密情報の表示」（`docker compose config`）で承認画面が出る（danger-ops.md 見張り 3.）。`docker compose ps`（allow 済み）か `docker compose port backend 8000`（allow 済み）に替える −6 行 | 実物 settings の allow・danger-ops.md 49 行（同じ文書群の中の矛盾） | worktree.md §6 | - |
| common-commands.md | ログ確認 | 直す | `tail -f backend/logs/django.log` はホストでは読めない（`backend_logs` は名前付きの保存領域で、ホストの `backend/logs/` は空）。また `-f` は終わらないので Claude が使うと止まる → `docker compose logs --tail=200 backend`、ファイルなら `docker compose exec -T backend tail -n 200 /app/logs/django.log`。下の「注意事項」の「ログファイル: backend/logs/django.log」も同じ誤り | 実物 `docker-compose.yml:52`（`backend_logs:/app/logs`） | common-commands.md | - |
| common-commands.md | フロントエンド・バックエンド再起動 | そのまま | — | — | common-commands.md | - |
| common-commands.md | テスト実行 | 直す（正の置き場所にする） | ①backend は CI と同じ `pytest`（`backend/pytest.ini`・CI は `pytest`）。`manage.py test` は違う走らせ方 ②frontend の `npm test` は `CI=true` が無いと監視モードで終わらない → `docker compose exec -T -e CI=true frontend npm test -- <対象>` ③「関係するテストのファイルだけを流す・全体は CI」（記憶 feedback_no_local_full_tests_duplicating_ci・test-gate の決まり）を 1 行足す ④テストを流すコマンドは implement SKILL（ホストで `python -m pytest`）・plan-writing-rules.md:127-129（ホストで `cd backend && …`）・backend-check.md:13（コンテナ）で形がばらばら → ここを正にし、他は参照（表2） ±0 行 | 実物 `ci.yml:84-85,144-145`・`frontend/package.json:38` | common-commands.md「テスト実行」 | - |
| common-commands.md | シェルスクリプトのロジック検証 | 直す（縮める） | ugrep の置き換えは今も事実（2026-11-17 に `type grep` で確認）。理由の段落を 2 文に −3 行。見出し名は `test_review_verdict.sh` TC-23-do が grep しているので変えない | 実物 `type grep` | common-commands.md | - |
| common-commands.md | Bash 実行作法（allowlist 単体コマンド） | 消す（danger-ops.md のサンドボックス節へ吸収） | 理由が古い: 公式は複合コマンドを部分ごとに判定し、全部が allow（または読み取り専用）なら確認は出ない（S2）。さらにサンドボックスの中は `autoAllowBashIfSandboxed: true` で確認なし。今の本当の制約は「外に出すコマンド（git・gh・docker・`bash scripts/claude/*`）を他のコマンド・リダイレクト・`cd`・前置きの代入とつなぐと中で動き、gh は鍵が読めず、git は settings.json の切り替えで壊れる」（S1）で、これは danger-ops.md 26 行の書きかけと同じ。「ファイル閲覧は Read ツール」は Claude Code 自体の指示にあるので不要 −10 行 | S1・S2・`.claude/settings.json` の sandbox | danger-ops.md「サンドボックス」 | - |
| common-commands.md | 未コミット変更の取り消し（引用） | 消す | danger-ops.md の写し −1 行 | 内部 | danger-ops.md | - |
| common-commands.md | API エンドポイント | 消す | 3 本だけの古い抜粋（実際は多数。正は `backend/openapi.yaml`）。読む人の役に立たない −4 行 | 実物 `backend/openapi.yaml`・`backend/accounts/urls.py` | `backend/openapi.yaml` | - |
| common-commands.md | ディレクトリ構造 | 消す | `e2e/`・`scripts/`・`tools/`・`.claude/` が無く古い。`ls` で分かる −7 行 | 実物 | — | - |
| common-commands.md | 注意事項 | 消す（要確認） | ①「開発環境ではメール送信をスキップ」は `backend/core/settings.py:282` が常に SMTP の設定で、どこで飛ばしているか確認できなかった（推測: コード側で DEBUG 時に飛ばしている可能性）。誤りなら開発中に実メールが出うるので、文書を消すだけでなく実物の確認が要る ②ログファイルは上の誤り ③「URL 変更時はキャッシュクリア」は意味不明（webpack の節と重複か） −4 行 | 実物 `backend/core/settings.py:281-288` | — | #520（メールを飛ばす実装の有無の確認） |
| common-commands.md | モデル変更時の必須手順 | 直す（縮める） | コマンド 2 つ（`makemigrations`・`--check --dry-run`）と「CI の backend-lint が止める」1 行に。`git add`・`git commit` 例と「なぜ重要か」の 5 行は縮める −8 行。見出し名は backend-check.md:18 が参照しているので変えない | 実物 `ci.yml:33-38` | common-commands.md | - |
| common-commands.md | API の形を変えたとき | そのまま | `npm --prefix tools/api-types ci`・`run generate` は実在（`tools/api-types/package.json`）。ホストで npm を使う（ネットワークが要る。サンドボックスの中では通信が無いので失敗しうる・推測）点だけ要確認 | 実物 | common-commands.md | #520（サンドボックスの中で `npm ci` が通るかの確認・推測） |
| common-commands.md | ローカル E2E テスト実行手順 | 消す（frontend-verify.md §8 に一本化） | **矛盾**: 手順 2「`RATELIMIT_ENABLE=false docker compose up -d backend` で起動」は、frontend-verify.md §8 が「この方法は効かない（e2e の実行が backend を作り直して制限ありに戻す・I187 で確認）」と書き、`test_i187_frontend_verify_config.sh` ⑤c もその許可が無いことを確かめている。正は `RATELIMIT_ENABLE=false docker compose --profile e2e run --rm e2e`。手順 3 の `docker compose rm -f e2e-init` は allow に無く承認画面が出る・frontend-verify.md には無い（今も要るかは推測で未確認）。`.env.e2e` の作り方は onboarding へ −44 行 | 実物 `docker-compose.yml`・frontend-verify.md:65-67・test_i187 ⑤c | frontend-verify.md §8 | - |
| common-commands.md | webpack キャッシュトラブル対処 | 直す（縮める） | 自動のキャッシュ消しは実在（`frontend/docker-entrypoint.sh:5`）。症状と `docker compose restart frontend` の 2 行に。手動回避の `rm -rf /app/node_modules/.cache` はコンテナの中で見張りの `rm -r`（危険操作の停止）に当たる → 消す −7 行 | 実物・danger-ops.md 例 Files | common-commands.md | - |
| common-commands.md | 修正済みの問題（履歴） | 消す | 移行時（docs/migration）の古い履歴。今の作業に使わない −8 行 | 内部 | git の履歴 | - |

## 表2 ファイルをまたぐ重複・矛盾

| 種類 | 決まり | 書いてある場所 | 食い違い | 正の置き場所（提案） |
|---|---|---|---|---|
| **矛盾** | ローカル E2E のレート制限を外す方法 | common-commands.md:148-156（`RATELIMIT_ENABLE=false docker compose up -d backend`）／frontend-verify.md:67（それは効かない。実行コマンドに前置きする） | 正反対 | frontend-verify.md §8。common-commands.md の節は消す |
| **矛盾** | `docker compose config` | common-commands.md:31 で「ポートの確認」に案内／danger-ops.md:49 で秘密情報の表示として確認（承認画面）の対象 | 案内したコマンドで承認画面が出る | danger-ops.md（判定）。common-commands.md は `docker compose ps`／`port` に替える |
| **矛盾** | 「大規模 rebase」 | danger-ops.md:10（危険操作の例＝承認制）／danger-ops.md:59（見張りは判定しない・reflog で戻せる・I200 で確認をやめた） | 承認が要るのか不明 | 表4 の案 1 で決める |
| **矛盾** | 複合コマンドの扱い | common-commands.md:63-70（束ねると allow に一致せずプロンプト）／公式 S2（部分ごとに判定）／danger-ops.md:26（git と非 git をつなぐな＝別の理由） | 理由が古く、本当の理由（サンドボックスの外に出ない）が別の場所 | danger-ops.md「サンドボックス」 |
| **矛盾** | テストを流すコマンド | common-commands.md:47,50（`manage.py test`・`npm test`）／implement SKILL:30-31（ホストで `python -m pytest`）／plan-writing-rules.md:127-129（ホストで `cd backend && python -m pytest`）／backend-check.md:13（`docker compose exec -T backend python -m pytest <ファイル>`）／CI（`pytest`・`CI=true npm test`） | 4 通り。ホストには Django・node_modules が無い（worktree.md §5） | common-commands.md「テスト実行」（コンテナ・対象ファイルだけ）。他は参照（implement SKILL は I547、plan-writing-rules は担当の点検へ） |
| **矛盾** | dependency-audit のイシューの扱い | dependency-audit.md:21（別のイシューを起票し直さない・/grill-me で書き足す）／`scripts/claude/dependency-audit-issue.sh:30`（/issue-bootstrap でローカルイシュー化） | 正反対 | dependency-audit.md。スクリプトは #520 |
| **矛盾** | 見張りを直したときのテストの本数 | danger-ops.md:55（4 つ）／`test_guard_corpus_diff.sh:5`（3 つ） | 数 | danger-ops.md。スクリプトのコメントは #520 |
| 矛盾（参照先） | Danger Ops の参照 | workflow.md:44「CLAUDE.md の危険操作（Danger Ops・`DANGER_OK=1`）」 | CLAUDE.md には 1 行の例しか無く、正は danger-ops.md | workflow.md:44 を「danger-ops.md の危険操作」に（workflow.md の担当へ） |
| 重複 | 未コミット変更への checkout/restore の禁止 | danger-ops.md:10・94-100／common-commands.md:72／code-reviewer.md・plan-reviewer.md（観点） | 中身は同じ | danger-ops.md「例」の Git 行（1 か所）。レビュー役は I547 |
| 重複 | Danger Ops の 2 条件（danger-approved＋DANGER_OK=1） | danger-ops.md:3／workflow.md:78／implement SKILL:20／CLAUDE.md 絶対ルール 4 | 中身は同じ（4 条件か 2 条件かの書き方差あり） | danger-ops.md。workflow.md・SKILL は「danger-ops.md の承認」と参照だけ |
| 重複 | 危険操作の実行の記録の形 | danger-ops.md「実行テンプレ」／plan_template.md:47／issue_template.md:47 | 項目名が少し違う | plan_template.md |
| 重複 | 起動コマンドの理由 | common-commands.md:14-17／dependency-audit.md:71／worktree.md:152／frontend-verify.md:20 | 中身は同じ（他は参照の形で良い） | common-commands.md（dependency-audit.md:71 を 1 行の参照に） |
| 重複 | ポート分離の説明 | common-commands.md:19-32／worktree.md §6 | 中身は同じ | worktree.md §6（`test_i179_worktree_docs.sh` DOC1 が common-commands.md に `BACKEND_PORT`・`wt-ports.sh` を求めるので、1 行は残す） |
| 重複 | runbook の一覧 | CLAUDE.md §0／onboarding.md:186-191／`docs/claude-code-structure.md`:39-44,111-117,388-460 | 3 か所に一覧 | CLAUDE.md §0。onboarding.md は参照に。`docs/claude-code-structure.md` は対象外の文書だが、手順書の要約を写していて古くなる（消すか参照だけにするかを計画で決める） |
| 重複 | detect-secrets の baseline の再生成コマンド | pre-commit.md:53・127 | 同じ | pre-commit.md の baseline 節 1 か所 |
| 重複 | Dependabot の設定の説明 | dependency-audit.md「見張るもの」「届き方」／`.github/dependabot.yml` の先頭のコメント | 文書側の一覧が古い（api-types 抜け） | 理由は設定ファイルのコメント、受け取り方は dependency-audit.md |
| 重複 | 「GitHub が最後の守り」の前提 | danger-ops.md:68／review-rules.md:79／worktree.md:249／記憶 feedback_local_guard_github_last_line | 中身は同じ（他は参照の形） | danger-ops.md「GitHub から復旧できる範囲」（記憶は消す） |
| 重複 | 見張りの脅威モデルは「事故」 | danger-ops.md:59・82／adversarial-reviewer.md:54／記憶 feedback_guard_threat_model_accidents | 中身は同じ | danger-ops.md（記憶は消す） |
| 重複 | 見張りに判定を足す決まり | danger-ops.md:60-63／plan-writing-rules.md:190（要約と明記）／plan-reviewer.md:147・fix-loop SKILL:40 | 正が明記されていて良い形 | danger-ops.md（そのまま） |

## 表3 漏れの候補

| 候補 | 足す／足さない | 置き場所 | 理由 |
|---|---|---|---|
| サンドボックスの外に出す条件の全体（リダイレクト・`cd`・`$(...)`・前置きの代入・パイプが入ると中で動く。gh は中では鍵が読めず失敗、git は settings.json だけ古く残る） | **足す** | danger-ops.md「サンドボックス」 | 気づきにくい（失敗の文言が原因を示さない）・毎回の作業で踏む。記憶 reference_sandbox_prefix_pipe_breaks_exclusion にだけある。公式 S1 で裏付けあり |
| 「手元では関係するテストのファイルだけを流す。全体は CI」 | **足す**（1 行） | common-commands.md「テスト実行」 | 記憶 feedback_no_local_full_tests_duplicating_ci にだけあり、テストのコマンドの正の場所に無い。被害は時間（全テストの手元実行）で中程度。test-gate SKILL にはあるが implement 段階でも効かせたい |
| Bash ツールで `test`・`[`・`grep` の終了コード 1 が見えにくい（記憶 reference_bash_tool_test_exit_code） | 足さない（要再確認） | — | 今の Bash ツールは終了コードを表示する（推測: この点検中も `Exit code` 表示を確認していない）。今も起きると確かめられたら common-commands.md「シェルスクリプトのロジック検証」に 1 行 |
| `gh auth status` を `--json` なしで流すと App の鍵が画面に出る（記憶 reference_gh_auth_status_leaks_app_token） | **足す** | harness-audit.md「古い鍵の点検コマンド」の注記（または github-app-setup.md） | 秘密の表示で取り消せない（公開されうる）。harness-audit は `--json` を使う理由を書いているが「無しだと鍵が出る」とは書いていない |
| 本番環境はまだ無い（記憶 project_no_production_env） | 足さない | — | danger-ops.md の「本番の設定」は将来も通る書き方で害が無い。レビューで「本番の確認」を頼まない話は review-rules 側の担当 |
| 手元の記憶をハーネスの総点検の範囲に入れる | **足す**（1 行） | harness-audit.md の表 | I546 で決まりを記憶から移すと決めた。次の総点検で再び溜まっていないかを見る場所が無い |
| 利用者の設定（`~/.claude/settings.json`・`~/.claude/CLAUDE.md`）・`.worktreeinclude` を点検の範囲に | **足す**（表の行に追記） | harness-audit.md | 手元の設定はリポジトリの許可より先に効き、気づきにくい（推測: 今は空かもしれない） |
| Actions の SHA 固定を GitHub の設定で強制 | 足さない（回す） | — | 公式の機能での置き換え → #427 |
| 定期の依存監査で `tools/api-types` を見ていない | 足さない（回す） | — | 設定の変更 → #520 |
| 開発でメールを本当に飛ばさないか（「注意事項」の確認） | 足さない（回す） | — | 実装の確認が要る → #520。被害（実メールの送信）は大きいので優先度を上げて伝える |
| 危険操作の一覧に「秘密の値の入った `docker compose config`」等の表示系を足す | 足さない | — | 既に見張り 3. と (C) にある。一覧に写すと重複 |
| pre-commit を `git commit` 以外（merge・rebase）で動かす | 足さない | — | danger-ops.md の表に「対策しない（push protection と CI で拾う）」と判断済み |

## 表4 中身の変更案（承認の対象を増やす・減らす）

ユーザーの確認が要る（I546 設計確認メモ・解決方針 9）。

| 案 | 今 | 変える内容 | 理由 | 影響 |
|---|---|---|---|---|
| 1. 「大規模 rebase」を危険操作の一覧から外す | danger-ops.md:10 で承認制。一方 59 行で「見張りは判定しない（I200 で確認をやめた）・計画書と人の承認で管理」 | 一覧から外し、「rebase の前に commit しておく（reflog・GitHub から戻せる）」の 1 文にする | 戻せる操作（reflog・push 済みは GitHub）で、記憶 feedback_local_guard_github_last_line の方針（戻せるものに承認を重ねない）と合う。今は一覧と実態が食い違い、承認を取るのか分からない | 承認の対象が 1 つ減る。強制 push（危険操作のまま）は変わらない。**逆案**: 残すなら 59 行の「見張りが判定しないもの」に「ただし計画書とユーザー承認は要る」と明記する（中身は変えず食い違いだけ直す） |
| 2. 「PR に danger-approved」を条件から外す | 4 条件の 1 つ。ラベルを確かめる仕組みが無い（ワークフロー・スクリプトに 0 件） | 条件を「計画書の Danger Ops 欄に明記」＋「ユーザーの明示承認（記録に残す）」＋「実行時の `DANGER_OK=1`（見張りが承認画面を出す）」の 3 つにする | 誰も確かめない手順は守られているか分からず、記録の役は計画書の欄とユーザー承認の記録で足りる。承認画面が実際の強制 | 承認の手順が 1 つ減る（人の承認そのものは残る）。workflow.md:78・implement SKILL:20 の「danger-approved + DANGER_OK=1」も直す（SKILL は I547）。**逆案**: 残すならラベルを PR に付けるのは誰か（bot か人か）を書く |
| （参考）見張りの (A)〜(C) の基準・`DANGER_OK=1` の承認画面・GitHub から復旧できない操作の表 | — | 変えない | 今の公式機能（S1〜S3）と実物に合っている | — |

## 表5 名前・置き場所を変える節を参照している行

（`.claude/`・`docs/`〔closed・reviews の過去記録・legacy を除く〕・`scripts/claude/`・`CLAUDE.md` を grep。2026-11-17）

| 変える節 | 案 | 参照している行 | 文言を grep しているテスト（壊さない条件） |
|---|---|---|---|
| template-sync.md（ファイルごと） | 消す（2 行を plan-writing-rules.md へ） | `CLAUDE.md:25`・`docs/runbooks/onboarding.md:190`・`docs/claude-code-structure.md:44,117,458`（`docs/migration/MANIFEST.md:70`・`migration_map.yml:129`・`apply_summary.md` は移行の過去記録なので直さない） | 無し。ただし CLAUDE.md の参照先から消したら、template-sync.md 自身の「comm -3」の確認と同じことを手で 1 回やる |
| danger-ops.md「未コミット変更の取り消し」 | 消す（例の Git 行へ） | `docs/runbooks/common-commands.md:72`（同時に消す） | 無し（`test_pretooluse_checkout_guard.sh` は見張りを試すだけで文書を読まない） |
| danger-ops.md「実行テンプレ」 | 消す（plan_template.md へ） | `docs/claude-code-structure.md:399` | 無し |
| danger-ops.md「見張り（pretooluse_guard.py）の扱い」 | 中身を縮める（見出しは変えない） | — | `scripts/claude/tests/test_i182_docs.sh` DOC3: 節の中に `--no-verify`・`20 秒`・`512MB` が要る。DOC6: 節の中のバッククォートの `/` 入りパスが実在すること（縮めて参照を足すときも実在のパスだけ書く） |
| danger-ops.md「GitHub から復旧できる範囲（I182）」「秘密情報を push してしまったとき（I182）」 | 見出しは変えない | `.claude/agents/adversarial-reviewer.md:54`・`.claude/agents/plan-reviewer.md:147`・`.claude/skills/fix-loop/SKILL.md:40`・`docs/runbooks/review-rules.md:79,92`・`docs/runbooks/worktree.md:249`・`scripts/claude/code-review.sh:305`・`scripts/claude/tests/test_adversarial_trigger.sh:70` | `test_i182_docs.sh` DOC1（`秘密情報`・`.github/workflows/`・`リモートブランチの削除`・`イシュー・PR への書き込み`）・DOC2（`無効化`・`push protection`）・DOC5（worktree.md が「GitHub から復旧できる範囲」を含む） |
| danger-ops.md「サンドボックス（第 1 層・I430）」 | 見出しは変えず、common-commands.md「Bash 実行作法」を吸収 | `CLAUDE.md:55`・`docs/runbooks/onboarding.md:114`・`docs/runbooks/workflow.md:255`・`docs/runbooks/worktree.md:247`・`docs/claude-code-structure.md:172` | `scripts/claude/tests/test_settings_permissions.sh`（excludedCommands・denyRead は設定を見る。文書の文言は見ない）。`test_i525_skill_sandbox_form.sh` は SKILL を見る |
| danger-ops.md「例」の Docker 行 | 縮める | `scripts/claude/wt-remove.sh:14`（ファイル名だけ） | `scripts/claude/tests/test_i179_worktree_docs.sh` D12: `volume rm / prune` と `wt-remove.sh` の文字列が danger-ops.md に要る |
| danger-ops.md 全体 | ファイル名は変えない | `CLAUDE.md:18`・`scripts/claude/hooks/pretooluse_guard.py:2240,2823,2836`・`scripts/claude/tests/guard_must_stop_cases.txt:5`・`test_guard_corpus_diff.sh:5`・`test_guard_must_stop_cases.sh:4`・`docs/runbooks/plan-writing-rules.md:190` | `test_i181_review_slim.sh` D4_SCOPE・D5・D7: 他の文書（review-rules・SKILL・レビュー役）に `danger-ops.md` の文字列が要る（名前を変えると落ちる） |
| common-commands.md「Bash 実行作法」 | 消す（danger-ops.md へ） | 文書の参照なし（記憶 feedback_atomic_allowlisted_commands・feedback_use_read_tool_not_bash_for_files が指す） | 無し |
| common-commands.md「ローカル E2E テスト実行手順」 | 消す（frontend-verify.md §8 へ） | 参照なし | `test_i187_frontend_verify_config.sh` は settings の allow を見る（`RATELIMIT_ENABLE=false docker compose up` の許可が無いこと）。文書の文言は見ない |
| common-commands.md「worktree ごとのポート分離」 | 1 行＋参照に縮める | `docs/runbooks/worktree.md:152`（common-commands を参照） | `test_i179_worktree_docs.sh` D10（`wt-ports.sh` を含む・廃止スクリプト名を含まない）・DOC1（`BACKEND_PORT` を含む）→ 縮めてもこの 2 語は残す |
| common-commands.md「シェルスクリプトのロジック検証」 | 中身を縮める（見出しは変えない） | — | `scripts/claude/tests/test_review_verdict.sh:121` TC-23-do: 見出しの文字列 `シェルスクリプトのロジック検証` が要る |
| common-commands.md「モデル変更時の必須手順（migration drift 防止）」「API の形を変えたとき（型の作り直し・I493）」「開発環境起動」 | 見出しは変えない | `docs/runbooks/backend-check.md:7,14,18`・`frontend-verify.md:20`・`worktree.md:152`・`dependency-audit.md:71` | `test_i213_dependabot.sh` V1（起動コマンドの `--renew-anon-volumes`） |
| common-commands.md「API エンドポイント」「ディレクトリ構造」「注意事項」「修正済みの問題」 | 消す | `docs/migration/*`（過去記録・直さない） | 無し |
| pre-commit.md「ロールバック」「detect-secrets JWT 検出について」 | 消す・統合 | 参照なし | 無し |
| pre-commit.md「ESLint のフックの流し方（I468）」 | 変えない | `scripts/claude/lint-frontend.sh:5,29`（見出しの文字列を表示する） | `test_i468_lint_frontend.sh` |
| pre-commit.md「セットアップ」 | onboarding.md へ移す | `docs/runbooks/onboarding.md:191`（ファイル名だけ） | 無し |
| dependency-audit.md | ファイル名・見出しは変えない | `scripts/claude/dependency-audit-issue.sh:30`・`.github/dependabot.yml:1`（「Dependabot」節を名指し） | `test_i109_dependency_audit.sh:58-60`（ファイルの実在・CLAUDE.md とスクリプトがパスを含む）・`test_i213_dependabot.sh` |
| harness-audit.md | ファイル名は変えない | `CLAUDE.md:28`・`.claude/agents/plan-reviewer.md:140` | 無し |

## 行数（今 → 見込み）

| ファイル | 今 | 見込み | 主な減り方 |
|---|---:|---:|---|
| docs/runbooks/danger-ops.md | 106 | 約 92（文字数は約 −45%） | 見張りの仕様の細部を見張りの側へ・未コミット節と実行テンプレを消す。サンドボックス節は +3（吸収した決まり） |
| docs/runbooks/pre-commit.md | 141 | 約 75 | セットアップを onboarding へ・JWT 節の統合・コミット例とロールバックを消す |
| docs/runbooks/dependency-audit.md | 81 | 約 74 | 見張る一覧を設定ファイルへ委ねる・重複の注意をまとめる |
| docs/runbooks/harness-audit.md | 40 | 約 43 | 記憶・利用者の設定・鍵が出る注意を足す |
| docs/runbooks/template-sync.md | 93 | 0（消す。plan-writing-rules.md に +2） | 決まり 2 つだけを移す |
| docs/runbooks/common-commands.md | 201 | 約 95 | E2E 節を frontend-verify へ・Bash 作法を danger-ops へ・古い節（API・構造・注意事項・履歴）を消す |
| 計 | 662 | 約 381（＋移す先に約 +8） | |
# I546 点検 D（セットアップ系 5 本＋legacy）

- 点検日: 2026-11-17。作業ディレクトリ: harness-1（`feature/I546-process-rules-bp-review`・53436302）
- 公式の照合（照らした日付はすべて 2026-11-17）:
  - [O1] Claude Code MCP: https://code.claude.com/docs/en/mcp （.mcp.json は対話セッションでは初回承認・`claude -p` は承認なしで読み込む・`--strict-mcp-config` で外せる・`/mcp` の Reconnect／`/mcp reconnect all`・`claude mcp reset-project-choices`）
  - [O2] Claude Code tools reference: https://code.claude.com/docs/en/tools-reference （WebSearch は組み込み。使えないのは提供元次第〔Amazon Bedrock は不可〕。対話セッションは 200 回まで。ページは取らず WebFetch で読む）
  - [O3] Claude Code settings: https://code.claude.com/docs/en/settings （`.claude/settings.json` の allow はワークスペースの信頼の後に効く・deny/ask は即時）
  - [O4] GitHub rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets （「読み取り権限があれば有効な ruleset を見られる」・classic と重ねると厳しい方が効く）
  - [O5] GitHub rulesets の規則: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets （Restrict updates・Code Owners・Dismiss stale・必須チェックの出どころの App 指定）
  - [O6] GitHub App installation token: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app （1 時間で切れる・`permissions`／`repositories` で絞れる）
  - [O7] Playwright MCP: https://github.com/microsoft/playwright-mcp （`--allowed-origins` は「セキュリティの境界ではない」・`--secrets` は「便利機能でセキュリティの機能ではない」・`--isolated`・`--output-dir`）
- 実物と照らしたもの: `.mcp.json`・`.claude/settings.json`（sandbox・hooks の matcher・allow）・`scripts/claude/gh-app/{gh,gh-app-token,install.sh,revoke.sh}`・`docker-compose.yml`・`.github/workflows/{ci,e2e}.yml`・`.github/CODEOWNERS`・`.pre-commit-config.yaml`・`e2e/playwright.config.ts`・`e2e/package.json`・`origin/main`（初期コミットだけ・2ce480ce）

---

## 表1 節ごとの判定

| ファイル | 節 | 判定 | 変更内容 | 根拠 | 正の置き場所 | 回す先 |
|---|---|---|---|---|---|---|
| onboarding.md | 冒頭「このプロジェクトとは」 | 直す | 「人間がゲートキーパーになる安全寄り Vibe Coding」を今の形（Claude が自律で進め、人は価値判断・人の手動テスト・マージだけ）に。2 行に | 内部: workflow.md「止めて聞く条件」と CLAUDE.md §1-2 が今の形。onboarding は旧い説明 | onboarding | - |
| onboarding.md | 一言で言うなら | 消す | 冒頭と同じ内容（-5 行） | 内部: 重複 | onboarding 冒頭 | - |
| onboarding.md | 4つの特徴 §1 スキル駆動のフロー | 直す | スキル表・段階の説明は workflow.md「使うスキル」「フロー」の写し。流れの 1 行（`/issue-bootstrap →（任意で /grill-me）→ /plan-issue`）だけ残し（test_i185 TC-14⑦ が見る）、表と段階の説明は「workflow.md を参照」に。21 行目の「打つのは /plan-issue（と /issue-bootstrap）だけ」は CLAUDE.md（/grill-me・/proceed も）と食い違うので参照に置き換え（-15 行） | 内部: workflow.md:3-11・19-34 と重複／CLAUDE.md:8 と言い方が違う | workflow.md | - |
| onboarding.md | 4つの特徴 §2 止める条件を絞った安全設計 | 直す | 止める条件の言い換え・hooks 2 行は CLAUDE.md §1-2・§3、workflow.md「止めて聞く条件」の写し。「サンドボックス・見張り・GitHub の 3 層で守る（danger-ops.md）」の 1 行と参照に（-4 行）。今の第 1 層（サンドボックス）が書かれておらず古い | 内部: danger-ops.md:15-（I430 で守りの土台がサンドボックスと GitHub に移った） | workflow.md／danger-ops.md／CLAUDE.md §3 | - |
| onboarding.md | 4つの特徴 §3 GitHub が品質ゲート | 直す | CI の中身の列挙が古い: 「`flake8`」→ 実物は pre-commit（Ruff＋bandit）・pip-audit・マイグレーションの差分、Frontend に npm audit、`API Types Up To Date` が無い、E2E（e2e.yml・必須ではない）が無い。列挙をやめ「必須チェックは branch-protection-setup.md §2」の参照に（-6 行） | 内部: `.github/workflows/ci.yml:26-33,127,151`・e2e.yml | branch-protection-setup.md §2（必須チェックの一覧） | #520（onboarding の「全部 pass しないとマージ不可」と、E2E が必須でない設定の食い違い） |
| onboarding.md | 4つの特徴 §4 すべてドキュメントが残る | そのまま | 2 行で短い。ただし「`open`→`closed`」の記録の説明は workflow.md「ディレクトリ規約」と同じなので 1 行に | 内部 | workflow.md | - |
| onboarding.md | 全体の流れ（図） | 消す | §1 の流れと workflow.md「フロー」の 3 つ目の写し（-15 行） | 内部: 重複 | workflow.md「フロー」 | - |
| onboarding.md | ブランチ戦略 | 消す | workflow.md「ブランチ戦略」の写し（命名「3桁」も両方にあり、I427 以降は GitHub の番号なので 4 桁になりうる点は workflow.md 側で直す）。参照 1 行に（-12 行） | 内部: workflow.md:151-172・issue-flow.md:137 | workflow.md「ブランチ戦略」 | - |
| onboarding.md | ドキュメント構成 | 消す | workflow.md「ディレクトリ規約」・docs/claude-code-structure.md の写し（-10 行） | 内部: 重複 | workflow.md「ディレクトリ規約」 | - |
| onboarding.md | 手元の準備（サンドボックスの道具・I430） | そのまま | 人が一度だけ行う手順として正しい置き場所。`failIfUnavailable: true` は settings.json:205 と一致。danger-ops.md:22 から参照されている | 内部: `.claude/settings.json:201-205` | onboarding（入れ方）／danger-ops.md（決まり） | - |
| onboarding.md | 手元の準備（GitHub の名義） | そのまま | 1 行の参照で適切 | 内部 | github-app-setup.md | - |
| onboarding.md | 手元の準備（ハーネスのテスト）・初回 | そのまま | 新しい端末の手順として適切。節名は `run-all.sh:19`・`required-tools.txt:5,8`・`pyproject.toml:3`・`dependency-audit.md:52`・`check-tools.sh:3` が参照しているので変えない | 内部 | onboarding | - |
| onboarding.md | 同・版を上げる手順／片方だけずれたら | そのまま（置き場所は検討の上で据え置き） | 「一度だけ読む」手順ではない保守の手順で、本来の置き場所は dependency-audit.md（版の管理）だが、移すと scripts の 3 か所のコメント（I546 の範囲外）と dependency-audit.md:52 を直す要があり、得が小さい。据え置きを推奨 | 内部: 参照元 6 か所 | onboarding（据え置き） | - |
| onboarding.md | よくある質問 | 直す | 「CI が落ちたら」「main にはどうマージ」は workflow.md の写し → 削除または参照 1 行。「Draft PR を最初に作る理由」「計画書なしに実装できる？」は人向けの説明として残す（-6 行） | 内部: workflow.md「本番リリースフロー」・「フロー」5 | workflow.md | - |
| onboarding.md | 参照先 | 直す | CLAUDE.md §0 の索引の写しで、frontend-verify・worktree・github-app-setup・harness-audit など 5 本が抜けて既に食い違っている。「CLAUDE.md §0 を参照」の 1 行に（-12 行） | 内部: CLAUDE.md:14-41 と比較 | CLAUDE.md §0 | - |
| branch-protection-setup.md | 冒頭のメタ情報（作成日・関連イシュー・改訂） | そのまま | 4 行。設定の由来として最小限 | 内部 | - | - |
| branch-protection-setup.md | 概要 | 直す | 「CI（5ジョブ）」→ 7（同じファイル内で 5／7 が矛盾）。件数を書かず「§2 の必須チェック」に。I430 以降、danger-ops.md が develop/main への push・外部 PR のマージをこの設定に任せている（第 1 層の代わり）ことを 1 行足す（設定を緩める人が影響を知れるように） | 内部: 同ファイル 16 行と 35・101 行の矛盾／danger-ops.md:30-33 | branch-protection-setup.md | - |
| branch-protection-setup.md | §1 設定値一覧（develop・main の 2 表） | 直す | 2 つの表は中身が同じ（「承認 1（本番ゲート）」の注記だけ違う）。「develop・main 共通」の 1 表にする（-16 行）。`Required status checks（7件）` の件数を外す | 内部 | 本節 | - |
| branch-protection-setup.md | §1 の「classic branch protection に合わせている」と §3 ステップ 1 の注意 | 直す | 公式は rulesets を推奨の新方式として案内し、rulesets は**読み取り権限で誰でも見られる**ため、bot（admin 権限なし）でも設定の今の状態を決定論で確かめられる。classic のままでは bot は設定を読めず、確認は人の目視だけ（§4）。この文書では書き換えず、移行は #427 へ | [O4][O5] | - | #427（classic → rulesets 移行と、`gh api repos/{o}/{r}/rules/branches/develop` での設定の決定論の確認） |
| branch-protection-setup.md | §1.5 理由 | そのまま | 4 行。設定の根拠として要る | 内部 | 本節 | - |
| branch-protection-setup.md | §1.5 3 つの設定の役割 | 直す | 3 の「`gh pr edit --base` では承認が取り消されない可能性（未確認）」: 公式は「merge-base の変化で取り消されることがある」と書く。未確認の推測を残さず、「宛先を変えた PR は承認の前に差分を見直す」だけ残す（-1 行） | [O5]（Dismiss stale は diff の変化・merge-base の変化で取り消し） | 本節 | - |
| branch-protection-setup.md | §1.5 main の制約 | そのまま | `origin/main` は初期コミットだけ（2ce480ce）で今も正しい。workflow.md:225・close/SKILL.md:163 が参照 | 内部: `git log origin/main` | 本節 | - |
| branch-protection-setup.md | §1.5 設定変更直後の develop | 消す | CODEOWNERS（#298）は develop に入って久しく、もう起きない移行期の説明（-3 行） | 内部: `.github/CODEOWNERS` が develop にある | - | - |
| branch-protection-setup.md | §1.5 運用 | 直す | 1 行目の「bot」の定義は 3 か所目（§1.5 理由・github-app-setup.md）。1 か所に。自動マージ不許可（2026-10-20 実測）はそのまま | 内部 | 本節 | - |
| branch-protection-setup.md | §2 必須 CI チェック名 | 直す | ジョブ名 7 件は ci.yml と一致（確かめた）。`E2E Tests (Playwright)`（e2e.yml・PR で動く・review-gate は待つ）が必須に入っていない。入れるかは表3・表4。注意書き 3 行は §6 トラブルシューティングと重複 → 片方に（-3 行） | 内部: `ci.yml` の `jobs.*.name`・`e2e.yml:15`・`code-review.sh:221-263` | 本節（一覧の正） | #520（onboarding の「CI 全部 pass しないとマージ不可」との食い違い） |
| branch-protection-setup.md | §3 GitHub Settings 操作手順 | 直す | ステップ 3 の必須チェック 7 件の再掲を「§2 の一覧」の参照に（-7 行）。ステップ 5 は「develop・main 共通の 1 表」に合わせて 1 行に | 内部: §2 と重複 | §2 | - |
| branch-protection-setup.md | §4 確認 1・2（直 push を試さない） | 直す | 経緯（I032 の当初は試していた）を落とし、「試さない・理由 3 つ」を 4 行に（-4 行） | 内部 | 本節 | - |
| branch-protection-setup.md | §4 確認 3・4 | そのまま | 手順として妥当 | 内部 | 本節 | - |
| branch-protection-setup.md | §4 確認 5（廃止） | 消す | 廃止の記録だけ（-4 行）。経緯は I178 の記録にある | 内部 | - | - |
| branch-protection-setup.md | §4 確認 6 | そのまま | bot のマージ API の拒否で push 制限を確かめる唯一の手順。人の了承を得てから（取り消せない操作）と書いてあり正しい | 内部 | 本節 | - |
| branch-protection-setup.md | §5 ロールバック | そのまま | 短い | 内部 | 本節 | - |
| branch-protection-setup.md | §6 トラブルシューティング | 直す | 「status checks の候補が表示されない」は §2 の注意と重複 → ここに 1 つ。「既存の Draft PR への影響」は「Draft はマージできないので影響しない」の 1 行に | 内部 | 本節 | - |
| github-app-setup.md | 冒頭 | そのまま | | 内部 | | - |
| github-app-setup.md | §1 仕組み | 直す | 1・2 点目は実物どおり（鍵 1 時間・残り 10 分〔`exp - 600`〕で取り直し・`gh auth git-credential`）。3 点目（6 行相当の 1 文）は「決まりの正は plan-writing-rules.md」と自分で書いているのに、G6・G7・tmux の PATH まで中身を写している → 「テスト用のセッションには読み取りだけの鍵（`GH_APP_READONLY=1`・`permissions` を read に絞った installation token）。Claude を起こす行の決まりは plan-writing-rules.md」の 2 行に（-3 行）。4 点目の GitHub MCP は mcp-usage.md と重複 → 残してよい（1 行） | [O6]（1 時間・`permissions` で絞れる）・`gh-app-token:12-24`・plan-writing-rules.md:90 | plan-writing-rules.md（Claude を起こす行の決まり） | - |
| github-app-setup.md | §2 App の設定 | そのまま | 権限・番号の上書き（`GH_APP_CLIENT_ID`・`GH_APP_INSTALLATION_ID`）は `gh-app-token:7-8` と一致。harness-audit.md:23 が「2.」を参照 | 内部 | 本節 | - |
| github-app-setup.md | §3 秘密の鍵ファイルを置く | そのまま | `.gitignore:94` の `*.pem`・pre-commit の detect-secrets（CI は pre-commit/action で全フック）と一致。サンドボックスの denyRead（`~/.config/github-app`）も効いている | 内部: `.pre-commit-config.yaml:11-16`・`ci.yml:26-29`・settings.json の sandbox | 本節 | - |
| github-app-setup.md | §4 入れる | そのまま | `install.sh`・`--check` は実在 | 内部 | 本節 | - |
| github-app-setup.md | §5 確かめる | 直す | 名義の確かめのコマンドは残す。2 段目の説明（入口の置き換え・G10）の 4 文を 2 文に（-1 行）。手元の記憶 `reference_gh_auth_status_leaks_app_token.md` は同じ内容 → I546 の記憶の点検で「移し済み・記憶から消す」候補 | 内部: `scripts/claude/gh-app/gh:30` | 本節 | - |
| github-app-setup.md | §5 鍵が画面・記録に出てしまったら | そのまま | `revoke.sh`・`--stdin` は実在。revoke.sh:13・38 が「5.」「7.」「8.」を参照するので番号を変えない | 内部 | 本節 | - |
| github-app-setup.md | §6 テスト用のセッション | そのまま | `test-session.sh` 実在 | 内部 | | - |
| github-app-setup.md | §7 困ったとき | 直す | `GH_APP_DISABLE=1` の「今は停止中の bot アカウントのログインで無効」は時点の記載。「本物の `gh` に有効なログインがあるときだけの退避」と時点に依らない書き方に | 内部: `gh:4-6` | 本節 | - |
| github-app-setup.md | §8 守ること | そのまま | 守りの範囲（ふつうの書き方の事故・最後の守りは GitHub）の明記は必要 | 内部 | 本節 | - |
| github-app-setup.md | §9 前の仕組み | 直す | 経緯の 1 行と「残っていたら消す」1 行に（-1 行）。harness-audit.md:39 が「9.」を参照するので節は残す | 内部 | 本節 | - |
| mcp-usage.md | 冒頭・§1 一覧 | 直す | 表は残す。GitHub MCP の行に §3 の中身（廃止の理由）を寄せる | 内部 | 本節 | - |
| mcp-usage.md | §2 built-in WebSearch | 直す | 「claude.ai/code では使える・CLI は設定・プランで使えない場合あり」は古い。公式は「Claude API などでは使える・Amazon Bedrock は不可・対話セッションは 200 回まで・ページは WebFetch で読む」。利用場面の表と「使い方」の例（自然言語で頼むだけ）は消し、「最新の版・CVE・推奨は WebSearch→WebFetch で公式の文書を読み、計画書に URL と日付を書く」の 3 行に（-22 行） | [O2] | 本節 | - |
| mcp-usage.md | §3 GitHub MCP（I223 で廃止） | 消す（§1 に統合） | 「見張りの MCP 向けの部分（settings.json・pretooluse_guard.py）は残している」は**実物と違う**: `mcp__github` は settings.json・pretooluse_guard.py に 0 件（I430 で消えたと推測）。文書側は削除、食い違いは #520 に記録（-4 行） | 内部: `grep -c mcp__github` = 0 | §1 の表 | #520 |
| mcp-usage.md | §4 Sequential Thinking を入れない理由 | 直す | 「Claude claude-sonnet-4-6（本プロジェクト使用中）」は古いモデル名。モデル名を書かず「今の Claude の推論で足りる」に。起動確認の 5 行は不要。理由 3 点を 3 行に（-12 行） | 内部: 今の会話は Opus 5.5 | 本節 | - |
| mcp-usage.md | §5 評価観点・設定ルール | 直す＋足す | 版の固定の決まりは残す。足す 2 行: ①`.mcp.json` に足すと `claude -p`（レビュー役など）では承認なしで読み込まれる（公式）ため、`scripts/claude/` の起動行は `--strict-mcp-config` を保つ（正は plan-writing-rules.md）②新しい MCP の道具は PreToolUse の見張りの matcher（settings.json は今 `mcp__playwright__.*` だけ）と allow を足すかを決める（`.claude/settings.json` の変更は止めて聞く条件 2） | [O1]・内部: settings.json:188-197 | 本節（手順）／plan-writing-rules.md（起動行）／danger-ops.md（見張り） | - |
| frontend-verify.md | §1 目的と範囲 | そのまま | 実物（check-frontend-evidence.sh・code-reviewer の観点）と一致 | 内部 | 本節 | - |
| frontend-verify.md | §2 初回だけの準備 | 直す | 1 の `playwright@1.59.1` は `e2e/package.json` の `@playwright/test` と同じ版を手で写している → 「`e2e/package.json` の `@playwright/test` の版」と書く（版上げで古くならない）。5 の「初回は確認が出るので許可」は公式どおり（対話セッションのみ） | [O1]・`e2e/package.json:10` | 本節 | - |
| frontend-verify.md | §3 起動と URL・§4 確かめる前に | そのまま | `docker compose port frontend 3000`（compose の `${FRONTEND_PORT:-3000}:3000`）と一致 | 内部: docker-compose.yml:129 | 本節（起動の正は common-commands.md） | - |
| frontend-verify.md | §5 ログイン | そのまま | `seed_e2e`・`seed_dashboard_verify` 実在。`--secrets` は公式でも「セキュリティの機能ではない」→ §9 に既にその旨あり | [O7] | 本節 | - |
| frontend-verify.md | §6 確かめること | そのまま | | 内部 | 本節 | - |
| frontend-verify.md | 「## 画面確認」（番号なし） | 直す | §6 と §7 の間の番号なしの `##`。`### 画面確認の記録` として §6 の下に入れる（名前「画面確認」は test-gate/SKILL.md:44 が「同じ手順書の『画面確認』の書き方」で参照するので語は残す） | 内部 | 本節 | - |
| frontend-verify.md | §7 画像が消えるタイミング | そのまま | `.gitignore:55`・`.evidence/` 一致 | 内部 | 本節 | - |
| frontend-verify.md | §8 E2E の落とし穴と避け方 | 直す | 5 行のうち 3 行（ホストで動かさない・MODULE_NOT_FOUND・レート制限）は「E2E を流す手順」で、画面確認の話ではない。**common-commands.md の E2E 節と矛盾**: common-commands.md:147-155 は「先に `RATELIMIT_ENABLE=false docker compose up -d backend`」を勧め、本節は「その方法は効かない（I187 で確認）・実行コマンドに前置きする」。E2E を流す手順は common-commands.md を正にして本節の 3 行を移し（矛盾は本節の内容で直す）、本節は安全なコンテキスト・オーバーレイの 2 行と参照だけに（-4 行）。手元の記憶 `reference_e2e_local_run.md` も同じ内容 | 内部: common-commands.md:147-160 | common-commands.md「E2E」 | - |
| frontend-verify.md | 「## 公式と自作の分担」（番号なし） | 直す | §8 と §9 の間の番号なし。§1 の末尾の `###` に移す（「なぜ自作か」の説明なので目的の節に） | 内部 | 本節 | - |
| frontend-verify.md | §9 安全上の注意 | そのまま（番号を変えない） | `--allowed-origins` は公式でも「セキュリティの境界ではない」・リダイレクトに効かない、で一致。`browser_network_requests` だけ allow（settings.json:102）も一致。「§9」は implement/SKILL.md:87・test-gate/SKILL.md:44・test_i193 S21 が文字列で見る | [O7]・settings.json:83-102 | 本節 | - |
| frontend-verify.md | §10 MCP のバージョンを上げるとき | 直す | 「公開から 2 週間以上」は Dependabot の cooldown（7 日・major 14 日。`.github/dependabot.yml:4`）と基準が違う。`.mcp.json` は Dependabot の対象外なので手で上げるのは正しいが、待つ日数は dependency-audit.md 側の基準に合わせて参照に。Dependabot・npm audit に乗せる仕組み（例: 版を package.json に持たせる）は #427 候補（推測: 実現できるかは未確認） | 内部: dependabot.yml:4 | dependency-audit.md | #427 |
| frontend-verify.md | §11 確かめ用のデータ | 直す | 20 行。手で流す形・出力の形・毎回入るものの細目は `seed_dashboard_verify` の `--help`／コマンドの docstring が正で十分。起動のたびに作り直す・ログの読み方・見比べ方・`--wait` を使わない、だけ残す（-6 行）。手元の記憶 `project_dashboard_verify_data.md` と重複 | 内部 | 本節 | - |
| frontend-verify.md | §12 MCP が使えないとき | 直す | 公式に `/mcp reconnect all`（v2.1.284 以降）がある。依頼の文例に「`/mcp reconnect all` を打つ（または `/mcp` で playwright → Reconnect）」と足す。番号「12」と節名は implement/SKILL.md:83・test-gate/SKILL.md:44 が参照するので変えない。`~/.cache/claude-cli-nodejs/...` の場所は公式の記載が無い内部の場所（推測: 版で変わりうる）なので「見つからなければこの手順は飛ばす」を 1 句足す | [O1] | 本節 | - |

## 表2 ファイルをまたぐ重複・矛盾

| 内容 | 書いてある場所 | 種類 | 正の置き場所の提案 | 他の扱い |
|---|---|---|---|---|
| ユーザーが打つスキル・段階の流れ | onboarding.md §1・「全体の流れ」、workflow.md「使うスキル」「フロー」、CLAUDE.md 冒頭、**README.md:105-117** | 重複＋矛盾（README は `/implement`・`/fix-loop`・`/close` をユーザーが打つ、`/plan-issue` は「承認待ち」と書く。今は段階のスキルは `user-invocable: false`） | workflow.md | onboarding は 1 行（TC-14⑦ の行）＋参照。README は「Claude Code の運用は CLAUDE.md／docs/runbooks/onboarding.md」の 2 行に（README は I546 の対象の外なので、計画で範囲に入れるか判断。古い記載は害がある） |
| 止める条件・hooks の説明 | onboarding.md §2、CLAUDE.md §1-2・§3、workflow.md「止めて聞く条件」 | 重複（onboarding はサンドボックスが抜けて古い） | workflow.md（条件）・danger-ops.md（守りの層）・CLAUDE.md §3（索引） | onboarding は参照 |
| ブランチ戦略・命名・hotfix | onboarding.md「ブランチ戦略」、workflow.md「ブランチ戦略」、issue-flow.md:137 | 重複 | workflow.md | onboarding・issue-flow は参照 |
| ディレクトリ構成 | onboarding.md「ドキュメント構成」、workflow.md「ディレクトリ規約」、docs/claude-code-structure.md | 重複 | workflow.md | onboarding は消す |
| 手順書の索引 | onboarding.md「参照先」、CLAUDE.md §0 | 重複＋食い違い（onboarding に 5 本の抜け） | CLAUDE.md §0 | onboarding は参照 1 行 |
| CI の中身・必須チェックの一覧 | onboarding.md §3（flake8 と古い）、branch-protection-setup.md 概要（5 ジョブ）・§1 表（7件）・§2・§3 ステップ 3・§4 確認 6（7 件） | 矛盾（5／7、flake8／Ruff）・同じファイル内で 4 回 | branch-protection-setup.md §2 | 他は「§2 の一覧」と書く（件数を書かない） |
| E2E を流すときのレート制限の避け方 | common-commands.md:147-160（先に backend を起動）、frontend-verify.md §8（その方法は効かない・前置き） | **矛盾** | common-commands.md の E2E 節（中身は frontend-verify §8 の I187 で確かめた方） | frontend-verify は参照 |
| 「bot」の定義（Claude の名義） | branch-protection-setup.md §1.5 理由・運用、github-app-setup.md 冒頭 | 重複 | github-app-setup.md 冒頭 | branch-protection は 1 か所で参照 |
| `claude -p` の起動行（`GH_APP_READONLY=1`・`--strict-mcp-config`・tmux の PATH） | github-app-setup.md §1、plan-writing-rules.md:90 | 重複（github-app-setup は「正は plan-writing-rules」と書きつつ中身も写す） | plan-writing-rules.md | github-app-setup は 2 行＋参照 |
| GitHub MCP の廃止 | mcp-usage.md §1・§3、github-app-setup.md §1・§9 | 重複＋mcp-usage §3 は実物と矛盾 | mcp-usage.md §1 の表の行 | github-app-setup は 1 行参照 |
| ブランチ保護が push・外部 PR のマージの守り | danger-ops.md:30-33（I430 で見張りから GitHub に移した）、branch-protection-setup.md（それが書かれていない） | 漏れの片側（設定側の文書に影響が書かれていない） | danger-ops.md（決まり） | branch-protection 概要に 1 行の参照 |
| 版を待つ日数 | frontend-verify.md §10（2 週間）、dependabot.yml（7 日・major 14 日） | 基準の食い違い | dependency-audit.md | frontend-verify は参照 |
| 手元の記憶との重複（I546 の記憶の点検の材料） | `reference_gh_auth_status_leaks_app_token.md` ↔ github-app-setup §5／`reference_e2e_local_run.md` ↔ frontend-verify §8・common-commands／`project_dashboard_verify_data.md` ↔ frontend-verify §11／`reference_bot_account_no_admin.md` ↔ branch-protection §2（「bot には権限が無い」） | 記憶と手順書の 2 重 | 手順書 | 記憶から消す候補（記憶の点検の担当に渡す） |

## 表3 漏れの候補

| 候補 | 足す？ | 理由 | 置き場所 | 回す先 |
|---|---|---|---|---|
| ブランチ保護の設定が今も表どおりかを、決まった時に確かめる手段（今は人の目視だけ。bot は classic の設定を読めない） | 足す（ただし仕組みは #427） | 気づきにくく被害が大きい: I430 で push・外部 PR のマージの守りを GitHub に任せたので、設定が緩むと最後の守りが黙って消える。rulesets にすれば読み取り権限で見られる（公式）ので、harness-audit の点検か CI で決定論にできる | 文書: harness-audit.md の「ブランチの守りの設定」の行に確かめ方を書く（移行後） | #427（rulesets への移行・`gh api …/rules/branches/<b>` での確認） |
| `E2E Tests (Playwright)` を必須チェックにするか | 候補として出す（表4 へ） | review-gate は E2E を待つが、GitHub はマージを止めない。onboarding の「全部 pass しないとマージ不可」と食い違う。人が赤いままマージする事故の余地。ただし設定画面の変更は人の操作で、マージの条件（ユーザーの関わり方）を変える | branch-protection-setup.md §2 | #520（文書と設定の食い違い）・表4 |
| mcp-usage: 新しい MCP を足すときに見張りの matcher・allow を決める | 足す（1 行） | 気づきにくい: 足しても PreToolUse の見張りが掛からず、auto モードでは承認なしで動きうる。`.claude/settings.json` の変更なので止めて聞く条件 2 に当たることも明記 | mcp-usage.md §5 | - |
| mcp-usage: `claude -p` は project の MCP を承認なしで読み込む | 足す（1 行・参照） | 公式の挙動で、レビュー役のセッションが読み取りだけの鍵を迂回しうる。決まり自体は plan-writing-rules.md にあるので参照だけ | mcp-usage.md §5 | - |
| 必須チェックの出どころの App を GitHub Actions に固定（他の App の偽の成功を数えない） | 足さない | App の権限は Commit statuses: read だけで偽の状態を書けない。外部の App も入れていない。その場で被害の筋が無い | - | - |
| 「Require approval of the most recent reviewable push」 | 足さない | 承認できるのは CODEOWNERS の `oshui0404` だけで、bot の push の後の承認は Dismiss stale が既に取り消す。効き目が重なる | - | - |
| gh を `| head` や `$(…)` で使うと鍵が読めない（サンドボックスの外に出ない）| 足さない（github-app-setup には） | その場で認証エラーになり気づける。決まりの置き場所は danger-ops.md「サンドボックス」（別の担当の点検範囲） | - | - |
| Playwright MCP の `--secrets` は「セキュリティの機能ではない」 | 足さない | §9 に「伏せ字は文字の出力だけ・画像には効かない」と既にあり実質同じ | - | - |
| ruleset と classic を併用したときは厳しい方が効く | 足さない（今は） | rulesets へ移すときの #427 の中で書けばよい | - | #427 |

## 表4 中身の変更案（ユーザーの関わり方・承認の場面を変えるもの）

| 案 | 今 | 変えた後 | 影響 | 備考 |
|---|---|---|---|---|
| `E2E Tests (Playwright)` を develop・main の必須チェックに加える | E2E が赤でも GitHub はマージを止めない（Claude の review-gate・close は待つ） | E2E が通らないとマージボタンが押せない | ユーザーの操作: 設定画面で 1 件足す（bot は権限なし）。E2E が不安定だとマージが止まる。外部 fork の PR は secrets が無いが、E2E は secrets を使わない（dependency-audit.md:68）ので影響なし | 安全装置（GitHub の設定）の変更なので I546 の実装前の 1 回の確認の一覧に載せる。設定を変えない判断なら onboarding の記載を事実に合わせる（「ci.yml のジョブが必須・E2E は Claude が待つ」） |
| ブランチ保護を classic から rulesets へ移す | classic（設定は管理者しか読めない） | rulesets（読み取り権限で読める・決定論で確かめられる） | ユーザーの操作: 設定画面での作り直し。承認・マージの場面は同じ | #427 へ回す（I546 では書き換えない）。ここでは記録だけ |

（上の 2 件以外に、この 5 本で「絶対ルール」「止めて聞く条件」「危険操作の承認」の中身を変える案は無し）

## 表5 名前・置き場所を変える節を参照している行

| 変える節 | 参照している行 | 文言を grep しているテスト | 提案 |
|---|---|---|---|
| onboarding.md「全体の流れ」・§1 の表を消す | 無し（節名での参照なし） | `scripts/claude/tests/test_i185_harness_docs.sh:145` TC-14⑦ が `/issue-bootstrap →（任意で /grill-me）→ /plan-issue` の行を onboarding に求める | その 1 行は残す |
| onboarding.md 全体（古い名前を入れない） | - | `test_i179_worktree_docs.sh:132,167`（D2: 廃止したスクリプト名が無いこと） | 書き換えで古い名前を入れなければ影響なし |
| onboarding.md「手元の準備（ハーネスのテスト）」 | `scripts/claude/tests/run-all.sh:19`・`required-tools.txt:5,8`・`pyproject.toml:3`・`check-tools.sh:3`・`docs/runbooks/dependency-audit.md:52`・`danger-ops.md:22`（サンドボックスの節を onboarding で参照） | 無し | **節名を変えない**（変えると scripts の 4 か所＝I546 の範囲外を直す要） |
| onboarding.md「参照先」を消す | 無し | 無し | - |
| branch-protection-setup.md §1.5「main の制約」 | `docs/runbooks/workflow.md:225`・`.claude/skills/close/SKILL.md:163`（ファイル名のみ） | 無し | 節名を変えない |
| branch-protection-setup.md §1.5「設定変更直後の develop」・§4 確認 5 を消す | 無し | 無し | - |
| branch-protection-setup.md 全体 | `docs/runbooks/harness-audit.md:28`・`issue-flow.md:281`・`danger-ops.md`（内容で依存）・CLAUDE.md:32 | 無し | ファイル名は変えない |
| github-app-setup.md の節番号「2.」「5.」「7.」「8.」「9.」 | `harness-audit.md:23`（2.）・`harness-audit.md:39`（9.）・`scripts/claude/gh-app/revoke.sh:13`（5.）・`revoke.sh:38`（7.・8.）・同ファイル内 §5-4（8.）・§8（3.） | `test_i223_gh_app.sh` G10 は「`--json` なしの auth status が無いこと」を見る（書き換えで `gh auth status` を `--json` なしで書かない） | **番号を変えない**（§9 は消さず短くする） |
| mcp-usage.md §3 を §1 に統合（以降の §4・§5 の番号が変わる） | 番号での参照なし（grep で 0 件）。CLAUDE.md:34 はファイル名だけ | 無し | 番号を詰めてよい |
| frontend-verify.md「画面確認」を §6 の下へ・「公式と自作の分担」を §1 の下へ | `test-gate/SKILL.md:44`（「画面確認」の書き方）・`check-frontend-evidence.sh` はテスト記録の `## 画面確認` を見る（この文書の見出しではない） | 無し | 語「画面確認」は残す |
| frontend-verify.md §9・§12・「2.」「8.」「11.」 | `.claude/skills/implement/SKILL.md:83`（「12. MCP が使えないとき」）・`:87`（§9・12）・`.claude/skills/test-gate/SKILL.md:44`（§12・§9）・同ファイル内 9・32・36・65・89・118 行 | `scripts/claude/tests/test_i193_official_flow.sh:428,431`（S21: `docs/runbooks/frontend-verify.md\` の手順（§9 の安全上の注意を含む）` を skills に求める） | **番号と節名を変えない**（番号なしの 2 節を `###` にしても `##` の番号 1〜12 は変わらない） |
| frontend-verify.md §8 の 3 行を common-commands.md へ | 同ファイル 36 行（「8. E2E の落とし穴」でログイン制限を参照） | 無し | 36 行の参照先を common-commands.md に |

### legacy（`docs/runbooks/legacy/CLAUDE.md.20260302`）を消す場合

- 調べた結果: **`docs/migration/CLAUDE_original.md` とバイト単位で同じ**（`cmp` で一致・2147 行）。移行の検証（`scripts/migration_verify/verify.sh`）が読むのは `CLAUDE_original.md` の方で、`match_atomic_lines.py`・`check_references.py` は `docs/runbooks` を `*.md` で集めるので拡張子 `.20260302` の legacy は読まない。→ 消しても失うものは無い（git の履歴にも残る）。推奨: **消す**（`.gitkeep` ごと `legacy/` を消す）
- 直す行:
  - `docs/claude-code-structure.md:45`（`legacy/ ← 旧ルールファイルのアーカイブ` の行を消す）
  - `docs/migration/MANIFEST.md:10`・`:52`・`:65`（移行の時点の記録。消すか「I546 で削除・同じ内容は `docs/migration/CLAUDE_original.md`」と注記。MANIFEST は記録なので注記を推奨）
  - `.secrets.baseline:181-188`（legacy の項目）: 消さなくても害は無い（推測: detect-secrets のフックは渡されたファイルの項目だけを整理するので、無いファイルの項目は残るだけで不合格にならない）。**`.secrets.baseline` は止めて聞く条件 2 の安全装置**なので、I546 では触らず残すのを推奨（直すなら確認が要る）
  - closed/ の過去記録（I060・I064・I178 など）は直さない
- テストの参照: 無し

## 行数（今 → 見込み）

| ファイル | 今 | 見込み | 主な減り |
|---|---|---|---|
| docs/runbooks/onboarding.md | 193 | 約 105 | 流れの図・ブランチ戦略・構成・参照先・特徴の写しを参照に（版を上げる手順は据え置き） |
| docs/runbooks/branch-protection-setup.md | 274 | 約 225 | 2 つの表を 1 つに・必須チェックの再掲・移行期の節・廃止の確認 5 |
| docs/runbooks/github-app-setup.md | 83 | 約 76 | §1 の起動行の写し・§5 の説明・§9 |
| docs/runbooks/mcp-usage.md | 113 | 約 62 | WebSearch の例と古い環境の注意・§3 統合・§4 の起動確認（＋2 行足す） |
| docs/runbooks/frontend-verify.md | 121 | 約 110 | §8 の 3 行を移す・§11 の細目（＋§12 に 1 句） |
| docs/runbooks/legacy/CLAUDE.md.20260302 | 2147 | 0 | 削除（同じ内容が docs/migration/CLAUDE_original.md にある） |
# inspect_E: 記憶（feedback_*.md 38 件・reference_*.md 10 件）の振り分け

- 点検日: 2026-11-17。作業ツリー: harness-1（feature/I546-process-rules-bp-review・develop 0a4b0202 の後）
- 「記載済み」の場所は grep と Read で確かめた行。行番号はこの時点のもの
- 方針: 足すのは「気づきにくく被害が大きい」ものだけ（`plan-writing-rules.md:168-177`・retro SKILL 2.7）。その場で捕まり手戻りの小さいものは足さない
- 「推測」と書いたものは実地で確かめていない

## 記憶の振り分け（feedback_*.md 38 件）

| 記憶のファイル | 判定 | 移す先（ファイル・節） | 足す文、または記載済みの場所 | 理由 |
|---|---|---|---|---|
| feedback_always_japanese.md | 残す | — | — | 返答の言語はユーザー個人の好み。手順書に無くても作業の正しさは変わらない |
| feedback_atomic_allowlisted_commands.md | 移す（記載済み） | common-commands.md「Bash 実行作法（allowlist 単体コマンド）」 | `docs/runbooks/common-commands.md:63-72`（束ねない・`; echo exit` を付けない・Read で読む・例外は検証目的）。git を git 以外とつながない理由は `docs/runbooks/danger-ops.md:26` | 決まりは書いてある。ただし同節の理由「allow に一致せず ask に落ちる」は I430 のサンドボックス導入前の説明で、今はサンドボックスの中の複合コマンドは承認なしで通る一方、`gh`・`git`・`bash scripts/claude/*` に付けると外に出られず失敗する（reference_sandbox_prefix… の実測）。I546 本体で節の理由をサンドボックス基準に書き直す材料（下の reference_sandbox_prefix… の行とまとめる）。記憶の push の ask-shadow の注記（I080）は古い |
| feedback_backlog_purpose_check.md | 移す | ①issue-flow.md 新しい節「retro の振り分け」（下の 2 件と同じ節）②plan-writing-rules.md「計画書作成ルール」 | ①「台帳の振り分けで一覧に出た指摘でも、イシューの目的そのものを崩すものは一覧に回さず、その PR で直す（計画を直して plan-review から）。」②「受け入れ条件は手段（見る範囲・ファイル）でなく結果（どの場合でも〜しない）で書く（手段で書くとレビュー役が『AC の文言どおり』で止めない・I486）。」 | close の後に戻した実害（I486）。台帳の振り分けは機械的に重さで決まるので、目的の穴は気づきにくい。retro SKILL 4-0 には無い（grep で確認） |
| feedback_check_rules_and_deps_before_building.md | 移す | plan-writing-rules.md「計画書作成前の事前調査（必須）」に小節「規約と依存の照合」を新設 | 「仕組み（取得・キャッシュ・状態管理・検証など）を自作すると決める前と、BP の確認に答える前に、`rules/` の該当の節と依存のファイル（`frontend/package.json`・`backend/requirements*.txt`）を開いて照合し、計画の技術選択に節と行を添える。新しいコードは既存ファイルの書き方より規約を優先する。レビュー・/simplify の指摘が計画の決定とぶつかったら『計画どおり』で見送らず、規約と照らして計画を直す。」（3 行） | 4 回再発（I487・I513・I524・I494）、どれもマージ依頼の後に見つかり計画レビューからやり直した＝気づきにくく被害が大きい。スキル・レビュー役側（plan-issue・plan-reviewer に 1 項目ずつ）は #509 で直す予定なので、ここは手順書の正だけ。現状 runbooks に該当なし（`rules/` の参照は `issue-flow.md:346` の「規約を確認する」だけ） |
| feedback_count_all_transcripts.md | 残す | — | — | Claude Code の作業記録（`~/.claude/projects/`）の数え方で、リポジトリの手順書には不自然。頻度も低い（回数で判断する調査のときだけ）。記憶の例のディレクトリ名 `-mnt-c-app-wt-harness` は古い（今は `-mnt-c-app-study-app-multitenant--claude-worktrees-harness-N`）ので、残すときに直す |
| feedback_coupled_issues_proceed_autonomously.md | 消す | — | 一般則は `docs/runbooks/workflow.md:39-47`（CI の失敗の直し方は Claude が決めて記録）・`CLAUDE.md` 絶対ルール 2 | 状況（I151×I159 の相互待ち）が特殊で以後の再発記録なし。書かれた回避手順（旧 `/code-review`・一時ブランチ→ff）は I193 前の流れで古い。一般則で足りるので足さない |
| feedback_design_for_testability.md | 移す | plan-writing-rules.md「より良い方法の検討（必須プロセス）」 | 「テストのために差し替え（monkeypatch・一時的なグローバルの書き換え・テスト専用の差し込み）が要るときは、本番の設計を変えて差し替え自体を不要にする案を第一候補にする。」（1 行） | 設計の歪みを残す対症療法は気づきにくい（I127 では本番の退行も同時に見つかった）。`rules/` には無い（grep で確認）。コードの書き方の決まりとしては `rules/` が本来の置き場所だが I545 の範囲で閉じたため、計画の観点として置く（推測: I547 か次の rules の見直しで `rules/` へ移す方がよい可能性） |
| feedback_evaluate_by_ideal_not_minimal.md | 移す（一部記載済み） | workflow.md「止めて聞く条件」の直後の段落（`workflow.md:47`） | 記載済み: 止める条件（`workflow.md:39-47`・`CLAUDE.md` 絶対ルール 2）。足す文:「案を比べるときは『今の症状を消すか』でなく『同じ壊れ方の再発を断てるか（根治か）・失うものは何か』を基準にし、決めた 1 案を理由とともに示す（選択肢の一覧を出して選ばせない）。Claude が起票時に書いた受け入れ条件の文言がイシューの目的・BP とぶつかるときは、目的に沿う形に狭めて自律判断の記録に書く。」（2 行） | ユーザーに何度も差し戻された（I066・I067/68・I151・I212）。「止める条件」は記載済みだが、判断の基準（根治・決め切る）は runbooks に無い。追記の「スラッシュコマンドはユーザー入力」「I193 マージまで」は古いので消す。「規約はあるべき姿」は I545/I546 の物差しとしてイシューに記載済み |
| feedback_fix_issues_yourself.md | 移す（記載済み）＋一部消す | workflow.md「フロー」2-1 | `docs/runbooks/workflow.md:23`（Blocker は自分で直して再レビュー）・`.claude/skills/plan-review/SKILL.md` | 本体は記載済み。「OK で残った Low は修正前にユーザーへ提示して判断を仰ぐ」は今の流れ（止めない指摘は台帳→retro が振り分け・`review-rules.md:70`）と矛盾するので消す |
| feedback_fixloop_not_excessive.md | 移す（記載済み）＋一部消す | review-rules.md「検証の全体設計」「高リスク変更の敵対的レビューステージ」 | 同種が続いたら止め方を見直す: `review-rules.md:87`・`.claude/skills/review-gate/SKILL.md:84`。止める範囲: `review-rules.md:60-71`。上限: `review-rules.md:86` | 本体は記載済み。記憶の「3 周上限・2 体各 10 分」は I181/I197 前の数字で今の上限（1 周 10 分・2 周）と矛盾するので消す |
| feedback_guard_threat_model_accidents.md | 移す（記載済み） | danger-ops.md・plan-writing-rules.md | `docs/runbooks/danger-ops.md:59`（脅威モデルは事故・意図的な回避は対象外）・`danger-ops.md:60-63`・`docs/runbooks/plan-writing-rules.md:188-195`・`.claude/agents/adversarial-reviewer.md:52-56`・`review-rules.md:86` | 書いてあるので記憶から消すだけ |
| feedback_local_guard_github_last_line.md | 移す（記載済み） | review-rules.md・danger-ops.md | `docs/runbooks/review-rules.md:79`（GitHub が最後の守り）・`docs/runbooks/danger-ops.md:66-82`（復旧できる範囲と例外）・`.claude/skills/fix-loop/SKILL.md:40`・`.claude/agents/plan-reviewer.md:147`。Actions の確認の絞り込みは `danger-ops.md:54` | 書いてあるので記憶から消すだけ。記憶の「I200 に同梱済み・それまでは予告」は完了済みで古い |
| feedback_manual_test_concrete_accounts.md | 移す（記載済み）＋一部消す | frontend-verify.md「5. ログイン」 | `docs/runbooks/frontend-verify.md:26-35`（組織・役割ごとの決まったアカウント・パスワードの渡し方）・`frontend-verify.md:92-`（確かめ用のデータ） | 決まったアカウントの表が正になった。記憶の「専用アカウントを DB に作り check_password で確かめる」は古いやり方（今は seed_e2e・verify_i487）で消す。Human 行の具体化は、ユーザーがその場で気づける（手が止まる）ので手順を足さない |
| feedback_manual_test_executor.md | 移す（記載済み） | plan-writing-rules.md「手動テスト文書のフォーマットルール」 | `docs/runbooks/plan-writing-rules.md:470-482`（実施者の区別・原則 Claude・「試した手段:」必須・`check-manual-test-executor.sh`）・`plan-writing-rules.md:485-491`・`.claude/skills/test-gate/SKILL.md:41-47` | 書いてあり、決定論のチェックもある |
| feedback_no_local_full_tests_duplicating_ci.md | 移す（記載済み） | workflow.md「フロー」2-6 | `docs/runbooks/workflow.md:28`（pytest・Jest・E2E は CI が正で手元では流し直さない）・`docs/runbooks/backend-check.md:12`・`.claude/skills/fix-loop/SKILL.md:51` | 書いてある。ハーネスのテスト（run-all.sh）は workflow.md:28 の列挙に無いが fix-loop SKILL:51 が「関係するテストだけ」を持つ。機械で選ぶ仕組みは #523。workflow.md:28 の列挙に「ハーネスのテスト」を足すかは I546 本体の判断（足すなら 0 行増の言い換え） |
| feedback_no_per_edit_confirmation_during_impl.md | 移す（記載済み） | workflow.md・CLAUDE.md | `docs/runbooks/workflow.md:39-47`（それ以外は Claude が決める）・`CLAUDE.md` 絶対ルール 2・`.claude/settings.json` の allow | 書いてある（設定で強制済み）。記憶の「`/implement` をユーザーが打つ必要はない」も `workflow.md:9` に記載済み |
| feedback_plain_language_user_facing.md | 残す | — | （参考: 手順の中の平易化は `.claude/skills/retro/SKILL.md:14-23`・`workflow.md:108,110`） | 説明の書き方の好み（改行・空行・用語の置き換え）は個人の好み。記録ファイルは詳細のまま、という点は retro SKILL に記載済み |
| feedback_plan_change_needs_plan_review.md | 移す（記載済み） | workflow.md「ゲート」 | `docs/runbooks/workflow.md:81`・`docs/runbooks/review-rules.md:88` | 書いてある。ただし 2 か所に同じ決まりがある（重複）。I546 本体で正を 1 つにする（推奨: workflow.md:81 を正、review-rules.md:88 は参照に） |
| feedback_prefer_official_features.md | 移す（一部記載済み） | plan-writing-rules.md「より良い方法の検討（必須プロセス）」 | 記載済み（領域ごと）: `docs/runbooks/worktree.md:6`・`docs/runbooks/frontend-verify.md:73-75`・`danger-ops.md:61`（見張りの前に公式・GitHub）。足す文:「公式の機能（Claude Code・GitHub）と重なる設計は、公式だけで足りるかを先に確かめ、足りない部分だけを自作で足す。公式の処理を置き換える・無効にする案は、失う公式機能をスパイクで確かめてから推奨する。」（2 行） | 領域ごとには書いてあるが一般則が無い。I179 で設計やり直し・I185 で再発。I546 のイシューの「制約」にも書いてあるのでプロジェクトの決まり |
| feedback_propose_issue_title_on_separate_issue.md | 移す（記載済み） | workflow.md「Claude が会話の中で起票するとき（I220）」 | `docs/runbooks/workflow.md:91-100`・`.claude/skills/issue-bootstrap/SKILL.md` の description | 書いてある（I220 で反映済み）。記憶の「I220 マージまでは記憶を優先」は古い |
| feedback_reduce_step_by_leak_type.md | 移す | review-rules.md「検証の全体設計（I197）」の箇条書き | 「工程（レビュー・チェック・ゲート）を減らす・まとめる案は、その工程が止めている漏れの種類と、回数を押し上げている上流の原因を分けて示してから出す。別々の漏れを止める工程はまとめず、中身を減らす。」（1 行） | 工程の見直し（#441 の定期見直し・ハーネスの棚卸し）で毎回効く判断基準。誤った統合は漏れとして後で気づきにくい（I181 で撤回）。今の runbooks に無い |
| feedback_respect_track_session_boundary.md | 移す（記載済み） | worktree.md「9. セッション間の引き継ぎ原則」 | `docs/runbooks/worktree.md:237-246`（他のワークツリーを直接編集しない・引き継ぎはファイル・サンドボックスとフックで技術強制） | 書いてあり、技術強制もある |
| feedback_retro_do_gate_two_layers.md | 消す | — | 同梱優先は `.claude/skills/retro/SKILL.md:102`（4 問の 4） | 「手順を足すなら対のレビュー観点も足す」は、後の方針（retro SKILL 2.7「手続きより決定論・同じ穴を二重に塞がない」・feedback_retro_no_rule_inflation）と矛盾する（観点を増やす方向）。生きている部分（同梱優先）は記載済み |
| feedback_retro_no_rule_inflation.md | 移す（記載済み） | retro SKILL 2.7・plan-writing-rules.md | `.claude/skills/retro/SKILL.md:91-105`（2 つの基準と 4 問・振り分け）・`docs/runbooks/plan-writing-rules.md:168-177`（テスト側） | 書いてある。I545 の追記「捕まったかでなく捕まえるまでの手戻りの大きさで判断」は 2.7 の問 2「捕まって手戻りも無いなら」で表せている。runbooks 側に retro の判定の正が無い点は I546 本体の点検（issue-flow.md）の材料 |
| feedback_retro_routing_verify_scope.md | 移す | issue-flow.md 新しい節「retro の振り分け」 | 「既存イシューに同梱する前に、指摘の前提が本当かをコードで確かめ、同じ穴がほかにもないかを grep で測る。同梱は同じファイル・同じ原因・同じ直し方のときだけにし、原因・直す場所が違うもの、複数の手順に広がり毎回踏むものは別イシューにする。」（2 行） | マージ依頼の後にユーザーの問いで 2 件の誤った振り分けが見つかった（I491）＝気づきにくい。retro SKILL に無い（grep で確認）。スキル側への反映は I547 |
| feedback_review_must_converge.md | 移す（記載済み） | review-rules.md「検証の全体設計」 | `docs/runbooks/review-rules.md:59`（1 回目だけ全体・台帳・やり直しは差分だけ）・`review-rules.md:60-71`（止める基準） | 書いてある |
| feedback_review_with_subagent_adversarial.md | 移す（記載済み）＋一部消す | review-rules.md「検証の全体設計」「高リスク変更の敵対的レビューステージ」 | `docs/runbooks/review-rules.md:54-55,74,84`（独立した目・自己認証の非権威化）・レビュー後の変更の再レビューは `gate-check.sh`（`workflow.md:52`） | 書いてあり決定論で強制済み。記憶の「Agent ツールで独立レビュアーを起動」は今の決まり（`review-rules.md:58` 親の会話の裏で動くサブエージェントに検証を任せない・別プロセスの claude -p）と矛盾するので消す |
| feedback_self_verify_permission_prompts.md | 移す（記載済み） | plan-writing-rules.md「手動テスト文書のフォーマットルール」 | `docs/runbooks/plan-writing-rules.md:473-474,481,489`・`plan-writing-rules.md:90` | 書いてあり、`check-manual-test-executor.sh` で強制済み |
| feedback_skill_tool_usage.md | 移す（記載済み） | workflow.md「スキル呼び出しルール」 | `docs/runbooks/workflow.md:9,83-89`（段階のスキルと issue-bootstrap・proceed は Claude が Skill ツールで呼ぶ） | 書いてある。「ユーザーが打った /xxx は呼び直さない」は Claude Code 自体の動き（読み込み済み）で手順書に書く必要なし |
| feedback_skip_heavy_steps_for_tiny_changes.md | 移す | workflow.md「フロー」2-3（implement）の続き、または「止めて聞く条件」直後の自律判断の段落 | 「/simplify で整理済みの変更に後から数行を足しただけなら /simplify を回し直さず、自律判断の記録に『前回整理済み・追加は N 行』と 1 行書く。決定論のゲートとレビュー（gate-check が求めるもの）は省かない。」（1 行） | ユーザーの指示（I454「記録しておいて」）で、毎回のイシューの速さに効く。implement・fix-loop SKILL に無い（grep で確認）。レビューは省かない、と書くことで feedback_review_with_subagent_adversarial の「省略しない」と両立させる |
| feedback_split_many_candidates_into_issues.md | 移す | issue-flow.md「イシュー作成時の自動実行フロー（必須）」 | 「改善案・導入候補が 2 つ以上あるときは 1 イシューにまとめず、触る場所・失敗したときの影響・戻し方がそろう単位で分けて起票する。『互いに関係している』はまとめる理由にしない（どちらを先に入れても安全なら分ける）。」（2 行） | 2 回ユーザーに直された（11-10・#501）。まとめるとレビューが収束しにくい（I174・I179）。今の runbooks に無い |
| feedback_target_operating_model.md | 移す（記載済み）＋一部消す | CLAUDE.md・workflow.md・review-rules.md | ユーザーの確認の場面: `CLAUDE.md` 絶対ルール 2・`docs/runbooks/workflow.md:39-47`。検証の層（決定論・独立した目）: `docs/runbooks/review-rules.md:47-56`。承認ポイントを並べない: 計画書の「## 9. 確定事項と自律判断」（`docs/plans/templates/plan_template.md:42`・`plan-writing-rules.md:24`） | 書いてある。「I193 のマージまでは今のルール」「既存の hook 基盤に乗せる」などは古い（I193・I430 完了）。目標そのもの（人がレビューしなくても高品質）は I546 の物差しで、手順書の決まりとしては上の場所で足りる |
| feedback_tests_guard_only_hard_to_notice.md | 移す（記載済み） | plan-writing-rules.md「決定論テストの対象の選び方」 | `docs/runbooks/plan-writing-rules.md:168-177` | 書いてある（I213 で反映済み） |
| feedback_timebox_review_agents.md | 残す（縮める） | — | 流れの中のレビューの上限は `docs/runbooks/review-rules.md:86`（スクリプトが 10 分で締め切る）・報告の無い観点の扱いも同所 | 流れの中の敵対的レビューはスクリプトが時間を強制するので記載済み。残るのは会話の中で Agent ツールを手で起こすとき（点検の手分けなど）で、これは Claude Code 自体の使い方。「全員の報告がそろってから周の記録を書く」はスクリプト化済みで消す |
| feedback_use_read_tool_not_bash_for_files.md | 移す（記載済み） | common-commands.md「Bash 実行作法」 | `docs/runbooks/common-commands.md:70` | 書いてある。理由（未許可の sed が混ざると承認画面）はサンドボックス導入後は変わっている可能性がある（推測。サンドボックスの中の読み取りは承認なしで通るため）。I546 本体で上の atomic の行と一緒に理由を見直す |
| feedback_user_test_before_code_review.md | 消す | — | 今の順番は `docs/runbooks/workflow.md:26-31`（review-gate → test-gate → 人の手動テスト → retro → close） | 今の流れと矛盾（コードレビューが人の手動テストより先）。古い `/test`・`/code-review` 時代の指摘 |
| feedback_wait_for_explicit_command.md | 消す | — | 生きている部分（流れの起動はユーザーの `/plan-issue`）は `docs/runbooks/workflow.md:6,85-89` と plan-issue の `disable-model-invocation: true`（`workflow.md:89`）で強制済み | 「方向の選択だけでは issue-bootstrap も始めない」は、今の決まり（別イシューと決まったら Claude が起票・`workflow.md:91-100`）と矛盾。「/implement 待ち」も古い |
| feedback_warn_before_approval_prompt.md | 残す（縮める） | — | — | 承認画面の予告・会話で重ねて聞かない、はユーザーとのやりとりの好み（サブエージェント・レビュー役には関係しない）。スパイクで見張りに当たらない書き方（`docker compose cp`・`os.environ`・`curl`）は、見張りの判定（`danger-ops.md:48-50`）から分かり、外れても承認画面が 1 回出るだけ（被害が小さい）ので手順書に足さない |

## reference_*.md 10 件

| 記憶のファイル | 判定 | 移す先（ファイル・節） | 足す文、または記載済みの場所 | 理由 |
|---|---|---|---|---|
| reference_bash_tool_test_exit_code.md | 移す | common-commands.md「シェルスクリプトのロジック検証」 | 「Claude Code の Bash ツールは `test`・`[`・`grep` の終了コード 1 をエラーとして表示しない。手で流す決定論の TC・失敗の注入は `bash -c '…'` かスクリプトで包み、終了コードを出させて読む（表示なし＝合格と読まない）。」（1 行） | 偽合格に見える（I209）＝気づきにくく、TC の採否（`plan-writing-rules.md:159-166` の失敗注入）を誤らせる。runbooks に無い。記憶の「/tmp への振り向けは承認画面」はサンドボックス導入前の観測で古い可能性（推測） |
| reference_bot_account_no_admin.md | 移す（記載済み）＋1 行足す | github-app-setup.md 冒頭の「権限」の行（`github-app-setup.md:17`） | 記載済み: App の権限の一覧 `docs/runbooks/github-app-setup.md:17`（Administration なし）・設定は `oshui0404` が画面で行う `docs/runbooks/branch-protection-setup.md`。足す文:「リポジトリの設定を変える API は権限不足を 404（Not Found）で返す。設定の変更が受け入れ条件にあるときは、計画で実施者を Human（`oshui0404`）にして画面の手順を書く。」（1 行） | 名義は bot から GitHub App に替わり（I223）、記憶の bot アカウントの記述は古い。404 が権限不足だと分かりにくい点は今も当てはまる（推測: App も Administration 権限が無いので同じ 404 になる） |
| reference_clipboard_powershell_utf8.md | 残す | — | — | WSL・Windows のクリップボードの使い方で、ユーザーの環境の話。起票ではクリップボードを使わなくなった（`workflow.md:93`）。記憶の「起票コマンドはクリップボードへ」の関連は古いので直す |
| reference_e2e_local_run.md | 移す（記載済み） | common-commands.md「ローカル E2E テスト実行手順」・frontend-verify.md「8. E2E の落とし穴と避け方」 | `docs/runbooks/common-commands.md:137-178`・`docs/runbooks/frontend-verify.md:62-69`（ホストの chromium・レート制限・安全なコンテキスト・オーバーレイ） | 書いてある。記憶の「直接指定は見張りの確認」は I444 の `_container_safe`（テストは通す形）の後で古い可能性（推測） |
| reference_gh_auth_status_leaks_app_token.md | 移す（記載済み） | github-app-setup.md | `docs/runbooks/github-app-setup.md:46-47`（`--json` で欄だけ取る）・同「5.」（出してしまったら revoke.sh） | 書いてある |
| reference_interactive_shell_grep_wrapper.md | 移す（記載済み） | common-commands.md「シェルスクリプトのロジック検証」 | `docs/runbooks/common-commands.md:53-61` | 書いてある |
| reference_sandbox_prefix_pipe_breaks_exclusion.md | 移す（一部記載済み） | common-commands.md「Bash 実行作法」 | 記載済み: 1 回の呼び出しのコマンドがすべて一覧に当たるときだけ外で動く・git を他とつながない `docs/runbooks/danger-ops.md:26`。足す文:「外に出すコマンド（`gh`・`git`・`bash scripts/claude/*`）に値を渡すときは、環境変数の前置き（`X=1 bash …`）でなく引数にする。パイプ・振り向け（`>`）・`$(…)` を付けない（サンドボックスの中で動き、GitHub App の鍵が読めず失敗する・作業ツリーの確かめが DIRTY になる）。」（2 行） | 失敗の原因が分かりにくく（「鍵を受け取れません」・DIRTY）、毎回の作業で踏む。atomic の決まりの今の正しい理由でもあるので、common-commands.md の節の理由の書き直しとまとめる。スキルの手順の書き方そのものは #538 |
| reference_string_token_match_anchoring.md | 消す（足さない） | — | — | 文字列の部分一致の注意は一般的なプログラミングの知識で、2026 年の初め（I062）の 1 回だけ・以後の再発記録なし。手順書に足すと決まりが増えるだけ。レビューの観点に要るなら I547（code-reviewer）で判断 |
| reference_tui_observe_with_tmux.md | 移す（記載済み） | plan-writing-rules.md「手動テスト文書のフォーマットルール」 | `docs/runbooks/plan-writing-rules.md:473,490`（`scripts/claude/tui-capture.sh`）・`.claude/skills/test-gate/SKILL.md:46` | スクリプト化されて書いてある。tmux の生の手順はスクリプトの冒頭が正 |
| reference_worktree_permissions_from_main.md | 移す（記載済み） | worktree.md・plan-writing-rules.md | `docs/runbooks/worktree.md:47,242`（許可の判定の一部は primary）・`docs/runbooks/plan-writing-rules.md:489`（ワークツリーの許可を読ませた新しいセッション・`check-permission-prompt.sh`） | 書いてある |

## 移す先ごとの足す行数

| 移す先 | 足す行数 | 内訳 |
|---|---:|---|
| docs/runbooks/plan-writing-rules.md | 7 | 規約と依存の照合 3・公式の機能を土台に 2・テストの差し替えより設計 1・AC は結果で書く 1 |
| docs/runbooks/issue-flow.md | 5 | 新しい節「retro の振り分け」: 目的を崩す指摘は一覧に回さない 1・同梱の前の確かめ 2／起票: 候補は分けて起票 2 |
| docs/runbooks/workflow.md | 3 | 根治で比べ 1 案を決める・AC の文言を目的に合わせて狭める 2・小さな追加に /simplify を回し直さない 1 |
| docs/runbooks/common-commands.md | 3 | 外に出すコマンドに前置き・パイプを付けない 2（節の理由をサンドボックス基準に書き直すのと一緒に）・Bash ツールの終了コードの表示 1 |
| docs/runbooks/review-rules.md | 1 | 工程を減らすときは漏れの種類と上流の原因で判断 1 |
| docs/runbooks/github-app-setup.md | 1 | 設定を変える API の 404 と実施者 1 |
| CLAUDE.md・danger-ops.md・worktree.md | 0 | — |
| 合計 | 20 | |

## 集計

- feedback 38 件: 移す（新しく書く）9 件（うち一部記載済み 2 件: evaluate_by_ideal・prefer_official）・移す（記載済み）20 件（fix_issues・fixloop・manual_test_concrete・review_with_subagent・target_operating は、今の決まりと矛盾する古い部分も含む＝記憶ごと消して問題なし）・残す 5 件（always_japanese・count_all_transcripts・plain_language・timebox〔縮める〕・warn_before_approval_prompt〔縮める〕）・消す 4 件（coupled_issues・retro_do_gate・user_test_before_code_review・wait_for_explicit_command）
- reference 10 件: 移す 2 件（bash_tool_exit_code・sandbox_prefix）・移す（記載済み）6 件（うち bot_account は 1 行足す）・残す 1 件（clipboard）・消す 1 件（string_token）
- 記憶に残るもの: feedback 5 件＋reference 1 件。`MEMORY.md` の Feedback 節と Reference 節は、残す 6 件以外の行を消す

## 点検中に見つけた、記憶とは別の材料（I546 本体の点検の表へ）

- 重複: 計画を変えたら plan-review を通り直す決まりが `workflow.md:81` と `review-rules.md:88` の 2 か所にある
- 重複（要約と明記済み）: 見張りに判定を足すときの 3 つが `danger-ops.md:60-63` と `plan-writing-rules.md:188-195`
- 古さの疑い（推測）: `common-commands.md:63-72`「Bash 実行作法」の理由（allow に一致せず ask に落ちる）は I430 のサンドボックスの前の説明。今の正しい理由は「外に出すコマンドがサンドボックスの中で動くと鍵が読めない・DIRTY」。`workflow.md:122-129`「Claude Code実行ルール」（コマンドの前に必ず説明）も、自律の流れ（I193）と合うか点検が要る
- 古さ: `workflow.md:181-187`「イシュー完了時のマージフロー」の「ステップ25」「レビューファイルを closed に移動」は今の close 段階と合わない可能性
