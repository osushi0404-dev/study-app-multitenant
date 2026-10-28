# I209 計画書: ハーネスの古いイシューを棚卸しし、今の流れで不要なものを閉じる

## 基本情報
- **計画書ID**: plan_I209
- **関連イシュー**: #349
- **Draft PR**: #355
- **作成根拠資料**: docs/issues/open/I209.md（起点イシュー・設計確認メモあり）
- **実装後評価**: docs/reviews/open/I209_review.md
- **判定の一覧**: docs/reviews/open/I209_triage.md（この計画の調査結果の本体。計画レビューはこの一覧も見る）
- **作成日**: 2026-10-28

## 1. 背景/目的
- 背景: 開いている `track:harness` のイシューの多くは、I193・I197 で流れを組み直す前に起票され、廃止した自作コマンド（/code-review・/test・/plan-issue-review など）を前提にしている。どれが今も意味があるか分からず、同じ穴を扱うイシューが重なっている
- 目的: 1 件ずつ判定し（閉じる／残す／統合）、閉じるものは理由をコメントして閉じ、残すものは本文の先頭に「今の流れでの読み替え」を足す。閉じるものの中のまだ使える小さな指摘は、残すイシューか軽い指摘の一覧（`docs/reviews/backlog/`）に移す

### 調査結果
- 対象（ツールの実行で確定・2026-10-28）: `gh issue list --state open --label track:harness --limit 200 --json number` で 53 件。I209（#349）を除く 52 件を判定した（起票時の「56 件」は誤り。grill-me で数え直して訂正済み）
- 判定の作り方: 4 つのサブエージェントが 13 件ずつ、本文（`gh issue view`）と今のファイル（workflow.md・review-rules.md・plan-writing-rules.md・`.claude/skills/`・`scripts/claude/`・`.claude/agents/`・閉じたイシューの記録）を照らして案を出した。案が割れた件・迷いがあった件・根拠の要の件は Claude が確かめて決めた（`docs/reviews/open/I209_triage.md`「Claude が決めた点」）
- Claude が自分で確かめた根拠:
  - #172: `scripts/claude/hooks/pretooluse_guard.py:2553,2557` は貪欲な `re.search` のまま（不具合が残る → 統合して残す側へ）
  - #154: サブエージェントが挙げた「問題の作成で他組織の科目を受け付けるかもしれない」は、`backend/problems/views.py:256-259`（作成）・`:309-312`（更新）で拒否済み（I103）。アプリ側の後続は無い
  - #191: `git ls-files docs/issues/open` に I031〜I034・I036・I040〜I044・I047 が残っている
  - I188（#319）・I192（#325）: ユーザー決定（2026-10-24・`docs/issues/closed/I193.md:9,15,70`）は「I193 が終わったら残作業を確かめ、無ければ取り下げ」。項目ごとに確かめた結果、どちらも残る作業は無い（一覧の該当行）
- 結果（`docs/reviews/open/I209_triage.md`）: 閉じる 37 件（I188・I192 を含む）・統合 4 件（#172→#335・#189→#180・#226→#268・#279→#250）・残す 11 件（#180・#191・#237・#250・#268・#278・#316・#321・#324・#335・#337）
- 操作の前提（スパイク・2026-10-28）:
  - `gh` 2.88.1。`gh issue close` は `--reason {completed|not planned|duplicate}`・`--duplicate-of <番号>`・`--comment` を持つ（`gh issue close --help`）
  - 承認画面: `bash scripts/claude/check-permission-prompt.sh bash 'gh issue view 349 --json number'` → 「承認なしで実行された」。`.claude/settings.json:52` の `Bash(gh issue *)` に当たるので、`gh issue close`・`gh issue edit` も同じ規則で承認画面は出ない。見張り（`pretooluse_guard.py`）に `gh issue` の判定は無い（grep で 0 件）
- イシューのローカルのファイル: 判定対象のイシューのファイルは、このリポジトリに追跡済みのものが無い。他のワークツリーの未追跡ファイルはトラック境界のため触らない（設計確認メモ）
- 参照先の実在（棚卸し系の決まり）: 一覧の根拠に書いたファイル（`gate-check.sh`・`flow-stage.sh`・`pr-base-sync.sh`・`check-manual-test-executor.sh`・`check-permission-prompt.sh`・`next-issue-num.sh`・`wt-ports.sh`・`wt-remove.sh`・`docs/runbooks/worktree.md`・`docs/runbooks/frontend-verify.md`・`docs/runbooks/dependency-audit.md`・`.claude/agents/*.md`）は実在する（`ls scripts/claude/`・`ls docs/runbooks/` で確認）。TC-01 が機械で確かめるのは一覧の番号 52 件がそろうことだけで、根拠のファイルの実在は計画レビューと review-gate が読んで確かめた（台帳 F2・retro で訂正）

## 2. 受け入れ条件
イシューの AC と同じ（番号を振る）。
- AC1: 開いている `track:harness` のイシュー（I209 を除く 52 件）のすべてに、閉じる／残す／統合のどれかの判定と理由が記録されている（`docs/reviews/open/I209_triage.md`）
- AC2: 閉じる・統合する一覧（41 件）をユーザーが全件確認して OK を出してから閉じている
- AC3: 閉じたイシューには理由のコメントがあり、残したイシューの本文の先頭に「今の流れでの読み替え」（今のスキル名・段階名との対応と、まだ残っている作業）がある
- AC4: 閉じたイシューの中のまだ使える小さな指摘が、残すイシューへの同梱か `docs/reviews/backlog/` への移動で残っている
- AC5: I188（#319）・I192（#325）の取り下げ判断が記録されている

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: GitHub のイシュー（`track:harness` の 52 件。閉じる 41 件・本文の先頭の追記 11 件）
- 記録: `docs/reviews/open/I209_triage.md`（新規）・`docs/reviews/open/I209_original_bodies/<番号>.md`（新規・残す 11 件の追記前の本文）・`docs/reviews/backlog/I209.md`（新規）・`docs/reviews/open/I209_review.md`・`docs/tests/open/I209_*.md`
- コード（`scripts/`・`.claude/`・`backend/`・`frontend/`）は変えない。`path_risk_trigger()` の集合にも触れない

## 4. 変更点一覧（具体）

### 4.1 判定の一覧（AC1・AC5）
- `docs/reviews/open/I209_triage.md` に 52 件の判定・基準・理由・小さな指摘の行き先を書く（計画の段階で作成済み。計画レビューで判定も見てもらう）
- 実装で反映した後、同じファイルの「## 反映の結果」に、番号ごとの反映の日時と結果（`CLOSED` / 本文追記済み）を書く

### 4.2 ユーザーの確認（AC2・implement の最初で止まる）
- 修正方針: 設計確認メモ（2026-10-28 ユーザー決定）どおり、閉じる・統合する 41 件の一覧を全件見せて、まとめて OK をもらってから閉じる
- implement の最初に、一覧（番号・タイトルの要約・判定・理由の 1 行）を平易な言葉でユーザーに出して止まる（STAGE_DONE は書かない）。ユーザーが OK（または一部を外す指示）を返したら、`docs/reviews/open/I209_review.md` の「## 自律判断の記録」に `- [implement] ユーザー確認: 閉じる・統合する一覧 41 件に OK（YYYY-MM-DD HH:MM・外した番号: なし）` を書いて commit/push してから 4.3 へ進む。ユーザーが返信を `/proceed I209` で送ってきたときも同じ（最後の STAGE_DONE は plan-review なので implement に戻り、この行があれば一覧を出し直さない）
- 一部を外す指示があれば、その番号は「残す」に変えて一覧を直し（計画変更記録に書く）、読み替えを足す側に回す

### 4.3 GitHub への反映（AC2・AC3）
順番（途中で失敗しても、反映した分が一覧の「反映の結果」で分かるようにする）:
1. 残す 11 件の本文の先頭に「今の流れでの読み替え」を足す。1 件ずつ、次の単体のコマンドを順に流す（D = `docs/reviews/open/I209_original_bodies`）:
   1. `gh issue view <番号> --json body --template "{{.body}}" > D/<番号>.md`（追記の前の本文の記録。手動 No.2 の比べる相手・ロールバックの元。commit する）。本文が既に「## 今の流れでの読み替え（I209」で始まっていれば、この件は足さずに飛ばす（やり直しで二重にしない）
   2. Write で `D/<番号>.header.md` を作る（中身は読み替えの節〔一覧の『残すイシューの先頭に足す』の表の行から作る〕と、最後の行に `---` と空行。commit する）
   3. `cat D/<番号>.header.md D/<番号>.md > D/<番号>.new.md`（元の本文を書き写さず、そのままつなげる）
   4. `gh issue edit <番号> --body-file D/<番号>.new.md`
   5. `gh issue view <番号> --json body --template "{{.body}}" > D/<番号>.after.md` → `cmp D/<番号>.new.md D/<番号>.after.md` が exit 0（送った本文が 1 字も違わず GitHub に入った）。合えば `.new.md`・`.after.md` を消す（`.md` と `.header.md` から作り直せる）
   - スパイク（2026-10-28・計画レビューの Warning 2 への対応）: `--jq .body` は末尾に改行を 1 つ足すので比べると食い違う。`--template "{{.body}}"` は足さず、#349 で `gh issue edit --body-file` で送ったファイルと `cmp` が exit 0。リポジトリの中へのリダイレクト（`> docs/...`）と `cat a b > docs/...` は `check-permission-prompt.sh` で承認なしを確認（スクラッチ〔`/tmp`〕へのリダイレクトは承認画面が出る）
2. 統合 4 件: `gh issue close <番号> --duplicate-of <統合先> --comment "<コメント>"`。統合先の本文には 1. で中身を同梱済み
3. 閉じる 37 件: `gh issue close <番号> --reason "<completed|not planned>" --comment "<コメント>"`（② → completed、① ④ → not planned。②と①④の両方に当たるものは completed）
- コメントの形（1 件ずつ一覧の行から作る）:
  ```
  I209（#349）の棚卸しで閉じます。
  - 判定: 閉じる（基準 ②: 既に解決済み）
  - 理由: <一覧の理由>
  - 小さな指摘の行き先: <docs/reviews/backlog/I209.md の F# ／ #番号 ／ なし>
  - 一覧: docs/reviews/open/I209_triage.md（I209 の close 後は docs/reviews/closed/I209_triage.md）
  ```
  統合は「判定: 統合（#統合先 に同梱。中身は #統合先 の本文の先頭『今の流れでの読み替え』にある）」
- 1 コマンド 1 件で流す（`&&`・ループで束ねない）。各コマンドの後に一覧の「反映の結果」に 1 行書く
- 状態が既に CLOSED のもの（並行で誰かが閉じた）は飛ばし、その旨を反映の結果に書く

### 4.4 小さな指摘の一覧（AC4）
新規 `docs/reviews/backlog/I209.md`（見出しは `docs/reviews/backlog/I207.md` と同じ形。行は `test_i202_ledger_cleanup.sh` の `BL_FORM` の形）:
```
# I209 の台帳の残り（軽い指摘の一覧）

- 記録: `docs/reviews/open/I209_triage.md`（棚卸しで閉じたイシューの中の、まだ使える小さな指摘）
- 一覧に回した決まり: I209 の設計確認メモ（閉じるイシューの小さな指摘で、残すイシューに行き先がないもの）
- 見る場所: `.claude/skills/plan-issue/SKILL.md`「台帳の残りの一覧」（実装対象のファイルに当たる行を、同梱するか残すか決める。同梱して直した行は消し、行が無くなったらこのファイルを消す）

- F1 SEV=Low REPRO=no KIND=harness FILE=docs/runbooks/plan-writing-rules.md | 保存の後に表示へ反映される受け入れ条件は、読み取りの API（キャッシュを含む）を通るテストで確かめる（#153 I075） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F2 SEV=Low REPRO=no KIND=harness FILE=.claude/skills/grill-me/SKILL.md | 種別がバグのイシューでは、同じ原因・同じ書き方の兄弟の箇所が他に残っていないかを grep で全件挙げる（#252 I141・#197 I105） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F3 SEV=Low REPRO=no KIND=harness FILE=.claude/skills/implement/SKILL.md | 計画レビューが高リスクのとき、implement の最初に計画書の「## セキュリティレビュー結果」節があることを確かめる（#258 I144） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F4 SEV=Low REPRO=no KIND=harness FILE=scripts/claude/check-manual-test-executor.sh | Human の行の手順に、完全な URL・具体の入力値・使うアカウントが書かれているかを確かめる（#259 I145・#208 I110） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F5 SEV=Low REPRO=no KIND=harness FILE=.claude/skills/fix-loop/SKILL.md | 直し方が計画書の記述を変えるなら、同じ修正の中で計画書も直す（#283 I165） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F6 SEV=Low REPRO=no KIND=harness FILE=scripts/claude/fix-review-lib.sh | 診断レビューの SKIP が exit 0 で素通りし、時間切れか失敗かの原因も記録に残らない（#291 I173） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F7 SEV=Low REPRO=no KIND=harness FILE=.claude/skills/issue-bootstrap/SKILL.md | track:harness の例に `.github/` を足し、どちらの例にも当たらないときの扱いを 1 行書く（#207 I112） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F8 SEV=Low REPRO=no KIND=app FILE=rules/ultimate_django_coding_standards.md | get_permissions を上書きすると @action の permission_classes が効かなくなる注意を書く（#214 I116） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
- F9 SEV=Low REPRO=no KIND=harness FILE=.claude/skills/grill-me/SKILL.md | grill-me の質問の出し方に「何の話か・背景・推奨と理由・答え方」を入れる（#233 I128） | 一覧に回した理由: 棚卸しで閉じたイシューの小さな指摘
```
- 残すイシューへの同梱（#180 に #189・#289・#294・#230、#250 に #279、#268 に #226、#335 に #172）は 4.3 の 1. の読み替えの節に書く

## 5. 実装手順（ステップ）
1. 4.2: 閉じる・統合する 41 件の一覧をユーザーに出して止まる（ユーザーの OK が来るまで 2 以降に進まない）
2. 4.4: `docs/reviews/backlog/I209.md` を作って commit/push する（GitHub を触る前に、行き先を先に残す）→ TC-01
3. 4.3 の 1.（残す 11 件の本文）→ 2.（統合 4 件）→ 3.（閉じる 37 件）。各件の後に一覧の「反映の結果」を書き、最後に commit/push → TC-02・TC-03（手動 No.1〜No.4 は test-gate）
4. implement の通常の手順（/simplify は記録だけの変更なので変更が無いことを確かめる・3.5 の反映検証・結線）
- 依存: 2 以降は 1 の後。3 の中は 1.→2.→3. の順（統合先に中身を同梱してから統合元を閉じる）

## 6. テスト計画
### 自動（docs/tests/open/I209_auto_test.md）
- テストのレベル: 記録ファイルの形の決定論の確かめ（一覧の番号が 52 件そろう・小さな指摘の一覧の行の形）。アプリのテスト（pytest・Jest・E2E）は非該当（コードを変えない）
- 一覧の行の形は CI の Harness Tests（`scripts/claude/tests/test_i202_ledger_cleanup.sh` の D3 が `docs/reviews/backlog/*.md` のすべての行を `BL_FORM` で確かめる）でも固定される
### 手動（docs/tests/open/I209_manual_test.md・実施者はすべて Claude）
- GitHub の状態は CI から見られないので、test-gate で Claude が `gh` で確かめる（閉じた 41 件の状態とコメント・残す 11 件の本文の先頭・ユーザー確認の時刻が閉じる操作より前）

## 7. ロールバック
- 閉じたイシュー: `gh issue reopen <番号>`（コメントは残る。誤りなら「I209 の判定の誤りで開き直す」とコメントする）
- 本文の追記: `gh issue edit <番号> --body-file docs/reviews/open/I209_original_bodies/<番号>.md` で元の本文に戻す
- 記録のファイル: PR を revert する

## 8. Risk & 回避策
- 判定の誤りでまだ要るイシューを閉じる → 計画レビューが一覧を見る・ユーザーが全件を見て OK を出す（AC2）・開き直せる（7）
- 本文の追記で元の本文を壊す → 元の本文は `gh issue view --json body --template "{{.body}}"` で取ったもの（4.3 の 1.。`--jq .body` は末尾に改行を足すので使わない・台帳 F1 で訂正）をそのまま後ろに付ける。追記の前の本文を `docs/reviews/open/I209_original_bodies/` に残し、手動 No.2 で「元の本文が後ろにそのまま残っている」を確かめる
- 途中で失敗して半端に残る → 一覧の「反映の結果」に 1 件ずつ書く。やり直しは状態を見て飛ばす（4.3。二重の追記・二重のコメントを作らない）
- 小さな指摘が消える → 先に `docs/reviews/backlog/I209.md` を commit/push してから閉じる（5 の 2）

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・解決方針・スコープ）:
- 判定基準 ①〜④ と「どれにも当たらなければ残す」
- 判定は Claude が全件決め、閉じる・統合する一覧を全件ユーザーに見せてまとめて OK をもらってから閉じる（4.2）
- 残すイシューは本文の先頭に「今の流れでの読み替え」を足し、元の本文はそのまま残す
- 閉じるイシューの小さな指摘は残すイシューに同梱し、行き先がなければ `docs/reviews/backlog/` に移す
- I188・I192 は残作業を確かめ、無ければ取り下げ（閉じる一覧に入れてユーザー確認を通す）
- 他のワークツリーの未追跡のイシューファイルは触らない
- `track:app` の棚卸し・残したイシューの中身の実装は含まない

Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は無い）:
- 判定の一覧の置き場所は `docs/reviews/open/I209_triage.md`（仮定で決めた）。理由: イシューに「置き場所は計画で決める」とある。レビューの記録と同じ場所に置けば close で closed へ一緒に移る。計画書に 52 行を直接書くより、計画書が短く保てる
- 判定は 4 つのサブエージェントで案を出し、割れた件は Claude が決めた（仮定で決めた）。理由: 52 件の本文は合わせて約 23 万字で、1 つの文脈で読むと前の件の中身を落とす
- 個々の件の判定（一覧の「Claude が決めた点」）（仮定で決めた）。理由: 基準 ①〜④ の当てはめで、要件の価値判断ではない。最終の閉じる判断はユーザーが一覧で確認する
- 閉じる理由の種類（② → completed、① ④ → not planned、③ → `--duplicate-of`）（仮定で決めた）。理由: GitHub の一覧で「済んだから閉じた」と「やらないと決めた」が区別でき、統合は統合先へのリンクが付く
- 統合先には別のコメントを足さず、本文の先頭の読み替えの節に中身を書く（仮定で決めた）。理由: 統合先で読む人が最初に目にする場所にまとまる。コメントに分けると読み替えの節と二重になる
- 小さな指摘の一覧は起点ごとに 1 ファイル（`docs/reviews/backlog/I209.md`）（仮定で決めた）。理由: retro の決まり（起点のイシューごとに 1 ファイル）にそろえる。SEV は Low・REPRO は no（観点・手順の小さな追加で、再現する不具合ではない）
- ユーザーの確認は implement の最初で止まって取る（仮定で決めた）。理由: 計画レビューが一覧を見た後の確定版をユーザーに見せる。計画の段階で見せると、計画レビューで判定が変わったときに見せ直しになる
- GitHub の状態の確かめは手動テスト（実施者 Claude）にする（仮定で決めた）。理由: CI は GitHub のイシューの状態を見る権限・前提を持たず、決定論のゲート（review-gate が流すコマンド）に `gh` は許可されていない。test-gate で 1 件ずつ確かめる
- 一覧 該当なし（`grep -rnF -e "FILE=docs/reviews/open/I209_triage.md |" -e "FILE=docs/reviews/backlog/I209.md |" -e "FILE=- |" docs/reviews/backlog/` が 0 件。2026-10-28）

要件適合性: 受け入れ条件の範囲を超えた仕様の追加は無い。マルチテナント・ステータス遷移は非該当

セキュリティ・ベストプラクティス:
- セキュリティ影響なし（コード・認証認可・個人情報・依存ライブラリを変えない。bandit・npm audit の対象の変更なし）
- イシューのコメント・本文に秘密情報を書かない（書くのは判定・理由・ファイルのパスだけ）

P3/P5/P8 影響なし（DB・外部 API の追加・非同期処理・インフラの追加なし。GitHub の操作は既存の `gh` の許可の範囲）。P6 影響なし（UI なし）。P9 影響なし（個人情報・未成年データ・テナントデータを扱わない）

設計品質: コードの変更なし。判定の基準・コメントの形は一覧と 4.3 の 1 か所に書く

高リスク判定: コード・安全装置（`path_risk_trigger()` の集合）を変えず、アプリの高リスクの条件にも当たらない。GitHub のイシューを閉じるのは開き直せる操作（Danger Ops ではない）→ No の見立て（判定は plan-review）

Danger Ops（有無/手順/ロールバック）:
- 無（イシューを閉じるのは開き直せる。本文の追記は元の本文を残す。ロールバックは 7）

## 必ず確かめる項目
（高リスク判定が Yes になったときに敵対的レビューが使う。No なら使わない）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 一覧の 52 件が、2026-10-28 時点の開いている `track:harness`（#349 を除く）とちょうど一致する |
| V2 | 1 | 読んで可 | 「残す」以外の各件に、基準 ①〜④ のどれかと、根拠（ファイルか閉じたイシュー）が書かれている |
| V3 | 2 | 実験必須 | 閉じた 41 件がすべて CLOSED で、I209 の理由のコメントがある。残す 11 件の本文の先頭に読み替えの節があり、元の本文が後ろに残る |

## 計画変更記録
（実装中に計画と違うことをするときに書く）
- 1（計画レビュー 20261028_1922 の Warning 対応・2026-10-28）: Warning 1 は一覧（`I209_triage.md`）の「反映の仕方」と「行き先」の列を計画書 4.3 の「統合先の本文の読み替えに同梱・別のコメントは足さない」にそろえた。Warning 2 は 4.3 の 1. を単体のコマンドの列（`--template "{{.body}}"` で取る・`cat` でつなげる・送った後に `cmp` で確かめる）に書き直し、手動 No.2 も `cmp` の形にした（スパイクで完全一致と承認画面なしを確認）。Warning 3 は TC-03 の失敗注入を実装のときに流して結果欄に書く。方式・範囲・受け入れ条件は変えないので再レビューはしない
- 2（implement・2026-10-28）: 計画書の記載「4.3 の 1.：`gh issue view … > D/<番号>.md`（commit する）→ Write で `.header.md` → `cat` でつなげる」。採った方法: `.md` と `.header.md` を先に commit して、pre-commit の整形（最後の改行・行末の空白）を済ませてから `cat` でつなげた（`.header.md` は整形で末尾の空行が 1 つ消えた。`.md` は変わらなかった）。理由: 整形の前のファイルからつなげると、記録に残るファイルと GitHub の本文がずれ、手動 No.2 の `cmp` が崩れる。あわせて #335 に計画にないコメントを 1 件足した（#172 の誤ブロックの再現の実例。`I209_triage.md`「計画と違ったこと」）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261028_1922 判定: ✅ 完了](../../reviews/closed/I209_plan_review_20261028_1922.md)
