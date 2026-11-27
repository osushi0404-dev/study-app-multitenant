# 運用フロー（イシューの流れ・段階・止めて聞く条件）

## 使うスキル（ユーザーが / で打つもの）
- /issue-bootstrap [title] : GitHub にイシューを起票する（決まりは docs/runbooks/issue-flow.md・手順はスキル）。会話の中で別イシューにすると決まったときは Claude が自分で呼ぶ（下の「Claude が会話の中で起票するとき」）
- /grill-me I### : 計画書作成前に、要件・基本設計・UI/UX の曖昧な点だけを聞く（任意。issue-review 判定「十分」ならスキップ可）
- /plan-issue I### : ブランチ・Draft PR・計画書・テスト文書・レビュー文書を作り、そのまま下の段階を順に進めて、人の手動テストの手前（人の分が無ければマージ依頼）で止まる
- /proceed I### : 途中で止まったとき・新しいセッションで、記録の最後の `STAGE_DONE:` から続きを再開する

段階のスキル（`plan-review`・`design-security-review`・`implement`・`review-gate`・`test-gate`・`fix-loop`・`retro`・`close`）は `user-invocable: false` で、ユーザーは打たない（`/` の候補にも出ない）。`/plan-issue` と `/proceed` の中で Claude が Skill ツールで呼ぶ。

組み込み（公式）の `/code-review`・`/security-review`・`/simplify` は、段階の中で Claude が使う（review-gate・implement）。ユーザーが自分で打ってもよい（このプロジェクトのスキルは同じ名前を使わない）。

## ディレクトリ規約
- docs/issues/open, docs/issues/closed
- docs/plans/open, docs/plans/closed
- docs/tests/open, docs/tests/closed
- docs/reviews/open, docs/reviews/closed

## フロー
1. /issue-bootstrap（会話の中で別イシューにすると決まったときは Claude が呼ぶ）→ issue-review で自己完結度レビュー（ソフト）→ GitHub に登録（I＋GitHub の番号）。要件・基本設計・UI/UX の質問があればそこで止まる
1.5. /grill-me I###（任意）→ 要件・基本設計・UI/UX の疑問点を解消
2. /plan-issue I### → 計画書・テスト文書・レビュー文書 → 以下を Claude が順に進める（`proceed` が `scripts/claude/flow-stage.sh` で次の段階を決める）
   1. plan-review: 自作の計画レビュー（`plan-issue-review.sh`・`.claude/agents/plan-reviewer.md`）。Blocker は自分で直して再レビュー。高リスク判定 Yes → design-security-review、No → implement
   2. design-security-review（高リスクのときだけ）: 実装前の設計レビュー＋攻撃シナリオ。Blocker は計画を直して plan-review からやり直す
   3. implement: 実装・TDD → 組み込みの `/simplify` で整理 → commit（push は review-gate の最初・下の「GitHub への書き込みの時点」）。`/simplify` で整理済みの変更に後から数行を足しただけなら `/simplify` を回し直さず、自律判断の記録に「前回整理済み・追加は N 行」と 1 行書く（決定論ゲートとレビューは省かない）
   4. review-gate: CI 待ち（失敗・時間切れで止まる）＋組み込みの `/code-review`（パスの判定が YES のときは `/security-review` も。どちらも読み取り専用の plan モード）＋自作のレビュー役（受け入れ条件・計画・文書の照合）＋決定論ゲートの実走。高リスクなら敵対的レビュー（別プロセス・読むだけ・1 周 10 分・確かめる項目の一覧で判定。`scripts/claude/adversarial-review.sh`）。NG → fix-loop
   5. fix-loop: 診断レビューを通した案で直し、実装・テストのレビューを通して、**必ず review-gate に戻る**（戻り先は 1 か所）
   6. test-gate: `gate-check.sh`（最新のレビューが今の HEAD を見て OK か）→ 計画書が指定した重いテスト・Claude 担当の手動テスト（pytest・Jest・E2E は CI が正で、手元では流し直さない）→ 人の手動テストがあれば**ここで止まる**
3. ユーザーが人の手動テストの結果を返信（OK、または NG と内容）→ Claude が記録して続ける（会話が切れたら /proceed I###）
   - OK → retro → close
   - NG → fix-loop → review-gate → test-gate → もう一度人の手動テストを依頼して止まる
4. retro: 改善案の採否を Claude が決め、直す（記録の場所だけ）・既存イシューに同梱・起票（`issue-bootstrap`）まで行う
5. close: base 追従 → `gate-check.sh`（取り込んだ後の HEAD を見る）→ 記録を closed へ → PR 説明 → Ready → 追従と CI の最終確認 → **Approve & Merge を依頼して止まる**（自律判断の記録と振り返りの結果をまとめて報告する）
6. ユーザーが GitHub で Approve & Merge

イシューの番号・置き場所・起票・ラベルは docs/runbooks/issue-flow.md を参照。設計の根拠は docs/proposals/I193_official_base_flow.md。
フロントの画面確認（Claude が Playwright MCP で起動・ログイン・操作・画面キャプチャ・コンソール確認をする手順と、test-gate 段階の判定）は docs/runbooks/frontend-verify.md を参照。

## 止めて聞く条件（この 3 つだけ・各スキルはここを参照する）

ユーザーの確認は「人がやる手動テスト」と「マージ」に加えて、次のどれかに当たるときだけ。

1. **要件・基本設計・UI/UX の価値判断が要るとき**: 受け入れ条件・仕様・画面の配置/文言/操作の流れを変えないと進めないとき（対応中のイシューの範囲・進める順番が変わるときを含む）。複数の案のどれを選ぶかで仕様や画面が変わるとき
2. **取り消せない操作・安全装置そのものを変える操作**: 危険操作（`docs/runbooks/danger-ops.md`・`DANGER_OK=1`）・秘密情報が push されうる操作・GitHub Actions の変更、および安全装置そのものを変える操作。安全装置の集合は `scripts/claude/code-review.sh` の `guard_path_trigger` と同じ（高リスクの判定はこれに審査の部品を足したもの・I593）: `.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json`。安全装置は人の承認を外した流れで最後に残る守りなので、Claude が自分で緩めない
3. **周回の上限に達し、安全側の選択肢も取れないとき**: レビュー・修正の周回が上限に達したら、まず安全側の選択肢（確認を厳しめに倒す・範囲を狭める・別イシューに切り出す）を選んで記録して進む。それも取れないときだけ止める。セキュリティの Blocker・敵対的レビューで残った Critical/High を「受け入れて進む」判断は Claude だけではしない

それ以外（技術的な設計の選択・直せる指摘の直し方・CI の失敗の直し方・develop との食い違いの解決など）は Claude が決め、`docs/reviews/open/I###_review.md` の「## 自律判断の記録」に `- [段階] 決めたこと — 理由` で書く。止まったとき（人の手動テストの手前・マージ依頼）に、その要点を平易にまとめて報告する。

Claude が決めるときの基準: 案は「今の症状を消すか」ではなく「同じ壊れ方の再発を断てるか（根治か）・失うものは何か」で比べ、決めた 1 案を理由とともに記録する（選択肢の一覧を出して選ばせない）。

## 記録とつなぎ（決定論）
- 各段階は、終わりに `docs/reviews/open/I###_review.md`（close の後は closed）の末尾へ `STAGE_DONE: <段階> NEXT: <次の段階>` を 1 行足して commit する（push は下の「GitHub への書き込みの時点」だけ）。止める条件で止まるときは書かない
- `scripts/claude/flow-stage.sh I###` が最後の `STAGE_DONE:` 行から次の段階を返す（`STAGE_DONE:` が無い・読めないときは exit 2 で止める）
- `scripts/claude/gate-check.sh I###` が、test-gate・close の最初に「最新のコードレビュー記録（高リスク時は敵対的レビュー記録も）が VERDICT OK で、その `REVIEWED_COMMIT` から HEAD まで・作業ツリーに、記録の場所（`docs/reviews/`・`docs/tests/`・`docs/issues/`・`docs/plans/`）の外の変更が無い」ことを確かめる。直した後は必ずレビューを通り直す
- 段階のスキルのうち test-gate・retro・close が書いてよいのは記録の場所だけ。それ以外を直す必要が出たら fix-loop・review-gate を通す

## イシューの置き場所（I221）
正は docs/runbooks/issue-flow.md「イシューの番号と置き場所（I221）」（番号・見分け方・本文の写し・既存イシューへの同梱）。

## GitHub への書き込みの時点（I224）
GitHub に送るのは、GitHub が中身を見る時点だけにする（量の上限には頼らない）。各スキルはこの節を参照する（写しを持たない）。
- **push するのは 3 時点だけ**:
  1. plan-issue の下書き PR の作成（イシューファイルのコミット〔新しいイシューでは本文の写しのコミット〕。既コミット経路では計画の文書のコミット）
  2. review-gate の CI 待ちの前（`code-review.sh` を流す直前。fix-loop の後のやり直しのたびを含む）
  3. close の最後の確認の前（記録を closed へ移すコミット。`STAGE_DONE: close NEXT: merge` もこのコミットに入れる）
  - ほかに `pr-base-sync.sh final` が base を取り込んだとき（BEHIND のときだけ・スクリプトが送る）
- **それ以外の段階は手元でコミットだけ**（STAGE_DONE・自律判断の記録・テスト結果・レビュー記録）。次の時点でまとめて送る。送り忘れを仕組みで止めるのは review-gate の CI 待ち（`CI_WAIT: NOT_PUSHED`・決定論）だけで、close・マージの後の送り忘れは仕組みでは止まらない（close は手順の中で push する）
- **イシュー本文の書き換え（`gh issue edit --body-file`）は grill-me の終わりの 1 回だけ**。plan-issue で足す Draft PR の番号などは手元のファイルにだけ書く。起票（issue-bootstrap）・retro の既存イシューへのコメントはそのまま
- **目安**: 1 本のイシューの push は 4 回以内（fix-loop の後のやり直し 1 回ごとに +1）。測り方: `git reflog show refs/remotes/origin/<ブランチ>` の `update by push` の行数
- **同時に複数のセッションで GitHub に書き込まない**: 書き込む段階（plan-issue・review-gate・retro の起票・close）を、別の作業フォルダ（worktree）のセッションと重ねない。テスト用に起こすセッションは読み取りだけの鍵（I223）なので対象外。仕組みでは止めない（最後の守りは GitHub）
- 決まりの押し戻し（スキルに「commit/push」を書き足すなど）は `scripts/claude/tests/test_i224_push_points.sh` が CI で止める

## ゲート
- 計画レビュー（plan-review）を通す前にコード変更を開始しない。実装の前に、計画書があり・plan-review を通り・変更が計画書に書いてあることを確かめる（無ければ計画書を先に直す。直し方は docs/runbooks/plan-writing-rules.md「計画書と実装の一致性保証ルール」）
- 計画の方式・範囲・受け入れ条件を変えたら plan-review を通り直す（findings への対応を計画変更記録に足しただけなら通り直さない。どちらに当たるかは計画変更記録に 1 行で書く）
- 直 push の禁止・危険操作の承認は CLAUDE.md の絶対ルール 3・4（危険操作の条件は docs/runbooks/danger-ops.md）

## スキル呼び出しルール

- **ユーザーが打つスキル**（`/issue-bootstrap`・`/grill-me`・`/plan-issue`・`/proceed`）は、ユーザーがスラッシュコマンドを入力したときに使う（`issue-bootstrap` は会話の中の起票でも Claude が呼ぶ）。Claude が自分から呼んでよいのは次だけ:
  - `proceed`: `/plan-issue` の最後と、ユーザーが人の手動テストの結果を返信したとき
  - `issue-bootstrap`: retro 段階が改善案を起票するとき／会話の中で別イシューにすると決まったとき（作業中に見つけた後続の不具合・改善を含む。下の「Claude が会話の中で起票するとき」）
- **段階のスキル**は、`/plan-issue`・`/proceed` の流れの中でだけ Claude が呼ぶ。会話の流れで単独に呼ばない（呼んでも `flow-stage.sh` と `gate-check.sh` が順番を外れた進行を止める）
- `/plan-issue`・`/grill-me` は `disable-model-invocation: true`（Claude からは呼べない）

### Claude が会話の中で起票するとき（I220）

- ユーザーにコマンドを渡さず（クリップボードにも入れず）、Claude が Skill ツールで `issue-bootstrap` を呼んで起票する
- 明らかに価値が低いもの（その場で直せる軽い指摘・既存イシューへの同梱で足りるもの）は起票しない。その場で直すか既存イシューに同梱し、そのことを報告する。当たるか迷うものは Claude が決めて、報告に理由を 1 行書く
- それ以外は確認なしで起票する。起票する前にユーザーに聞くのは、「止めて聞く条件」1 に当たる次の 2 つだけ（両方に当たるときは 1 回にまとめて聞く）:
  - 対応中のイシューを進めるのに、別イシューの起票・対応が先に要るもの（今のイシューの範囲や進める順番が変わる）: 起票するか、どの順で進めるかを聞く
  - 要件・基本設計・UI/UX の判断が要る点が残っているもの: GitHub に起票する前に質問をまとめて出して止まり、答えをイシューの本文に入れてから起票する。対応中のイシューの段階の途中（/plan-issue の流れの中）で見つけた後続でも同じ
- 起票した後に、1 件 1 行で `I###（#GitHub の番号）・タイトル・なぜ起票したか` を報告する
- retro 段階からの起票は、この節ではなく retro の手順に従う（質問しない。決まっていない点は「未定」と書いて起票する）

### 各段階で止まったときの案内

| 止まったところ | Claude がやること |
|-----------|-----------------|
| 別イシューにすると決まったとき（イシュー作成の依頼を含む） | Claude が `issue-bootstrap` を呼んで起票し、報告する（上の「Claude が会話の中で起票するとき」） |
| イシュー作成後 | 要件・基本設計・UI/UX の質問があればそれを聞く。無ければ「`/plan-issue I###` を入力してください」と案内（設計を詰めたいときは `/grill-me I###`）。会話の中で Claude が起票したときは、上の節の 1 行の報告で終わる |
| 人の手動テストの手前 | Human の項目と、ここまでの自律判断の要点を平易に提示し、「結果（OK、または NG と内容）を返信してください」と案内 |
| マージ依頼 | 変更の概要・自律判断の要点・振り返りの結果をまとめて報告し、GitHub での Approve & Merge を依頼 |
| 止める条件に当たったとき | どの条件に当たったか・選択肢と推奨を平易に示して聞く。回答の後は「`/proceed I###`」で続ける（同じ会話なら Claude がそのまま続けてよい） |
| 会話が切れた・新しいセッション | 「`/proceed I###` を入力してください」と案内 |

---

## ブランチ戦略

**ブランチ構成**:
- **main**: リリース済みのコードだけを置く（本番環境はまだ無い。用意したらリリースに使う）
- **develop**: 開発の統合ブランチ（GitHub の既定ブランチ）。日常の PR はすべてここ宛て
- **feature/I###-xxx**: イシューごとの作業ブランチ（/plan-issue が `origin/develop` から作る）
- **hotfix/xxx**: リリース済みのコードの緊急修正用（本番ができてから使う）

**ブランチ命名規則**: `feature/I{GitHub の番号}-{概要を英語化してケバブケース}`（番号の桁数は問わない。例: `feature/I546-process-rules-bp-review`）

### 本番リリースフロー

develop の複数の機能を main にリリースするときの手順:

```bash
# 1. bot が develop → main の PR を作る
gh pr create --base main --head develop --title "Release: vX.X.X" --body-file <リリースノートのファイル>
# 2. oshui0404 が GitHub の PR 画面で承認・マージする
# 3. マージ後、main の先頭にタグを付ける
git fetch origin main
git tag -a vX.X.X origin/main -m "バージョンX.X.Xリリース"
git push origin vX.X.X
```

- バージョンタグを付け、リリースノートを残す

### 緊急修正（hotfix）のブランチ運用

リリース済みのコードで緊急のバグ修正が必要な場合：

```bash
git fetch origin
git checkout --no-track -b hotfix/critical-bug-description origin/main
# 修正・コミット
git push -u origin hotfix/critical-bug-description
# 1. bot が main 宛ての PR を作り、oshui0404 が承認・マージする
gh pr create --base main --title "hotfix: ..." --body-file <ファイル>
# 2. develop にも反映する（必須）。bot が develop 宛ての PR を作り、oshui0404 が承認・マージする
gh pr create --base develop --head hotfix/critical-bug-description --title "hotfix: ...（develop へ反映）" --body-file <ファイル>
# 3. 両方のマージ後、GitHub の PR 画面の Delete branch でブランチを消す
```

- main と develop の**両方**にマージする（忘れると修正が失われる）。修正は最小限にする
- **main がまだ初期コミットだけの間は、main への hotfix はマージできない**（main から作ったブランチには CI のワークフローが無く、必須チェックが報告されないため。docs/runbooks/branch-protection-setup.md §1.5「main の制約」）。最初のリリース（develop → main）より前は、緊急の修正も develop 宛ての PR で行い、リリースで main に入れる

## 外部（fork）からの PR の扱い

正は docs/runbooks/danger-ops.md（外部からの PR の判定・取り込まない・閉じる手順）。
