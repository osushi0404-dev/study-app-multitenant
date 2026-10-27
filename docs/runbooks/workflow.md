# Vibe Coding 運用フロー（公式の道具を土台にした自律の流れ・I193）

## 使うスキル（ユーザーが / で打つもの）
- /issue-bootstrap [title] : 採番、イシューファイル作成、issue-review による自己完結度レビュー（ソフト）、GitHub Issue 作成。要件・基本設計・UI/UX で決めてもらうことがあるときだけ質問して止まる（ブランチ作成は /plan-issue で行う）
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
1. /issue-bootstrap → issue-review で自己完結度レビュー（ソフト）。要件・基本設計・UI/UX の質問があればそこで止まる
1.5. /grill-me I###（任意）→ 要件・基本設計・UI/UX の疑問点を解消
2. /plan-issue I### → 計画書・テスト文書・レビュー文書 → 以下を Claude が順に進める（`proceed` が `scripts/claude/flow-stage.sh` で次の段階を決める）
   1. plan-review: 自作の計画レビュー（`plan-issue-review.sh`・`.claude/agents/plan-reviewer.md`）。Blocker は自分で直して再レビュー。高リスク判定 Yes → design-security-review、No → implement
   2. design-security-review（高リスクのときだけ）: 実装前の設計レビュー＋攻撃シナリオ。Blocker は計画を直して plan-review からやり直す
   3. implement: 実装・TDD → 組み込みの `/simplify` で整理 → push
   4. review-gate: CI 待ち（失敗・時間切れで止まる）＋組み込みの `/code-review`（パスの判定が YES のときは `/security-review` も。どちらも読み取り専用の plan モード）＋自作のレビュー役（受け入れ条件・計画・文書の照合）＋決定論ゲートの実走。高リスクなら敵対的レビュー（別プロセス・読むだけ・1 周 10 分・確かめる項目の一覧で判定。`scripts/claude/adversarial-review.sh`）。NG → fix-loop
   5. fix-loop: 診断レビューを通した案で直し、実装・テストのレビューを通して、**必ず review-gate に戻る**（戻り先は 1 か所）
   6. test-gate: `gate-check.sh`（最新のレビューが今の HEAD を見て OK か）→ 計画書が指定した重いテスト・Claude 担当の手動テスト（pytest・Jest・E2E は CI が正で、手元では流し直さない）→ 人の手動テストがあれば**ここで止まる**
3. ユーザーが人の手動テストの結果を返信（OK、または NG と内容）→ Claude が記録して続ける（会話が切れたら /proceed I###）
   - OK → retro → close
   - NG → fix-loop → review-gate → test-gate → もう一度人の手動テストを依頼して止まる
4. retro: 改善案の採否を Claude が決め、直す（記録の場所だけ）・既存イシューに同梱・起票（`issue-bootstrap`）まで行う
5. close: base 追従 → `gate-check.sh`（取り込んだ後の HEAD を見る）→ 記録を closed へ → PR 説明 → Ready → 追従と CI の最終確認 → **Approve & Merge を依頼して止まる**（自律判断の記録と振り返りの結果をまとめて報告する）
6. ユーザーが GitHub で Approve & Merge

詳細なイシューフローは docs/runbooks/issue-flow.md を参照。設計の根拠は docs/proposals/I193_official_base_flow.md。
フロントの画面確認（Claude が Playwright MCP で起動・ログイン・操作・画面キャプチャ・コンソール確認をする手順と、test-gate 段階の判定）は docs/runbooks/frontend-verify.md を参照。

## 止めて聞く条件（この 3 つだけ・各スキルはここを参照する）

ユーザーの確認は「人がやる手動テスト」と「マージ」に加えて、次のどれかに当たるときだけ。

1. **要件・基本設計・UI/UX の価値判断が要るとき**: 受け入れ条件・仕様・画面の配置/文言/操作の流れを変えないと進めないとき。複数の案のどれを選ぶかで仕様や画面が変わるとき
2. **取り消せない操作・安全装置そのものを変える操作**: CLAUDE.md の危険操作（Danger Ops・`DANGER_OK=1`）・秘密情報が push されうる操作・GitHub Actions の変更、および安全装置そのものを変える操作。安全装置の集合は `scripts/claude/code-review.sh` の `path_risk_trigger` と同じ: `.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json`（安全装置は人の承認を外した流れで最後に残る守りなので、Claude が自分で緩めない）
3. **周回の上限に達し、安全側の選択肢も取れないとき**: レビュー・修正の周回が上限に達したら、まず安全側の選択肢（確認を厳しめに倒す・範囲を狭める・別イシューに切り出す）を選んで記録して進む。それも取れないときだけ止める。セキュリティの Blocker・敵対的レビューで残った Critical/High を「受け入れて進む」判断は Claude だけではしない

それ以外（技術的な設計の選択・直せる指摘の直し方・CI の失敗の直し方・develop との食い違いの解決など）は Claude が決め、`docs/reviews/open/I###_review.md` の「## 自律判断の記録」に `- [段階] 決めたこと — 理由` で書く。止まったとき（人の手動テストの手前・マージ依頼）に、その要点を平易にまとめて報告する。

## 記録とつなぎ（決定論）
- 各段階は、終わりに `docs/reviews/open/I###_review.md`（close の後は closed）の末尾へ `STAGE_DONE: <段階> NEXT: <次の段階>` を 1 行足して commit/push する。止める条件で止まるときは書かない
- `scripts/claude/flow-stage.sh I###` が最後の `STAGE_DONE:` 行から次の段階を返す（`STAGE_DONE:` が無い・読めないときは exit 2 で止める）
- `scripts/claude/gate-check.sh I###` が、test-gate・close の最初に「最新のコードレビュー記録（高リスク時は敵対的レビュー記録も）が VERDICT OK で、その `REVIEWED_COMMIT` から HEAD まで・作業ツリーに、記録の場所（`docs/reviews/`・`docs/tests/`・`docs/issues/`・`docs/plans/`）の外の変更が無い」ことを確かめる。直した後は必ずレビューを通り直す
- 段階のスキルのうち test-gate・retro・close が書いてよいのは記録の場所だけ。それ以外を直す必要が出たら fix-loop・review-gate を通す

## ゲート
- 計画レビュー（plan-review）を通す前にコード変更を開始しない
- Danger Ops は明示承認（danger-approved + DANGER_OK=1）なしに実行しない（止める条件 2）
- develop/main への直 push を禁止（PR経由）
- イシューのスコープ・受け入れ条件が変更された場合は、docs/issues/open/[番号].md も必ず更新する
- 計画の方式・範囲・受け入れ条件を変えたら plan-review を通り直す（findings への対応を計画変更記録に足しただけなら通り直さない。どちらに当たるかは計画変更記録に 1 行で書く）

## スキル呼び出しルール

- **ユーザーが打つスキル**（`/issue-bootstrap`・`/grill-me`・`/plan-issue`・`/proceed`）は、ユーザーがスラッシュコマンドを入力したときに使う。Claude が自分から呼んでよいのは次だけ:
  - `proceed`: `/plan-issue` の最後と、ユーザーが人の手動テストの結果を返信したとき
  - `issue-bootstrap`: retro 段階が改善案を起票するとき
- **段階のスキル**は、`/plan-issue`・`/proceed` の流れの中でだけ Claude が呼ぶ。会話の流れで単独に呼ばない（呼んでも `flow-stage.sh` と `gate-check.sh` が順番を外れた進行を止める）
- `/plan-issue`・`/grill-me` は `disable-model-invocation: true`（Claude からは呼べない）

### 各段階で止まったときの案内

| 止まったところ | Claude がやること |
|-----------|-----------------|
| イシュー作成依頼を受けた後 | 「`/issue-bootstrap [タイトル]` を入力してください」と案内 |
| イシュー作成後 | 要件・基本設計・UI/UX の質問があればそれを聞く。無ければ「`/plan-issue I###` を入力してください」と案内（設計を詰めたいときは `/grill-me I###`） |
| 人の手動テストの手前 | Human の項目と、ここまでの自律判断の要点を平易に提示し、「結果（OK、または NG と内容）を返信してください」と案内 |
| マージ依頼 | 変更の概要・自律判断の要点・振り返りの結果をまとめて報告し、GitHub での Approve & Merge を依頼 |
| 止める条件に当たったとき | どの条件に当たったか・選択肢と推奨を平易に示して聞く。回答の後は「`/proceed I###`」で続ける（同じ会話なら Claude がそのまま続けてよい） |
| 会話が切れた・新しいセッション | 「`/proceed I###` を入力してください」と案内 |

## 移行（I193 のマージ前に着手したイシュー）
- I193 のマージ前に着手したイシューは、古い流れのまま最後まで進める。スキルは各ワークツリーで checkout しているブランチから読み込まれるため、そのブランチが develop を取り込むまでは古いスキル（`/implement`・`/code-review`・`/test`・`/retro`・`/close`）が動く
- 古い流れのイシューで `/proceed` を打つと、`STAGE_DONE:` が無いので止まる（新しい流れで誤って進めない）
- I193 のマージ後に /plan-issue するイシューから新しい流れにする。新しい流れの最初のイシューを実地の通しとし、その振り返り（retro）で「`/plan-issue` だけで人の手動テストの手前まで進んだか」を確かめる

---

## Claude Code実行ルール

- **コマンド実行前に必ず説明する**: 実行するコマンドが何をするものか、なぜ実行するのかを日本語で説明してから実行すること
- 例: 「PostgreSQLのデータベース一覧を確認するため、docker compose exec db psql -U postgres -c "\l"を実行します」

- **ロジック修正提案時に必ず説明する**: フロント・バックエンド問わず、ロジック修正を提案する際は以下を必ず説明すること
  1. **修正の意図**: なぜこの修正が必要なのか
  2. **修正前の問題点**: 現状どういう問題があるのか（具体的に）
  3. **修正後の改善内容**: 修正するとどう改善されるのか（具体的に）
  - 例: 「現在のコードでは科目が1件のみでも科目選択UIが表示されてしまい、ユーザーが余計な操作を強いられています。科目が1件の場合は自動遷移させることで、ユーザーは『クイズを始める』ボタンを1回押すだけで即座にクイズを開始できるようになります」

---

## 作業実行前の確認ルール

指示を受けた際は、次の順で進める（ユーザーの承認は待たない。止めるのは「止めて聞く条件」に当たるときだけ）:

1. **調査・分析**: 問題特定とログ確認
2. **対応方針検討**: 調査結果に基づいて具体的な対応方針を検討
3. **計画書作成**: `docs/plans/open/plan_I###.md`（再作成時は `plan_I###_2.md`…）に詳細記録
4. **計画レビュー**: plan-review 段階（Blocker は自分で直す）
5. **修正実施**: 実際の修正・テスト・検証（段階のスキルに沿う）

### 修正ツール使用前チェック（必須）
Edit/Write/MultiEdit等の実行前に必ず確認：
- 計画書作成済み？（計画書・テスト文書・レビュー文書そのものの作成は除く）
- 計画レビュー（plan-review）を通した？
- 変更が計画書に書いてある？（無ければ計画書を先に直す）

---

## ブランチ戦略

### 基本方針: 3ブランチ戦略（本番環境対応版）

**ブランチ構成**:
- **main**: 本番環境（AWS）デプロイ用、常に安定版のみ、リリース済みコードのみ
- **develop**: 開発統合・ステージング環境用、機能開発の統合ブランチ
- **feature/Ixxx-xxx**: 各イシュー開発用の作業ブランチ
- **hotfix/xxx**: 本番環境の緊急修正用ブランチ

**ブランチの役割**:
```
main (本番環境 - AWS) ← リリース時のみマージ
  ↑
develop (開発統合・ステージング) ← 日常的な開発はここに集約
  ↑
feature/Ixxx-xxx (各イシュー開発) ← イシューごとに作成
```

**ブランチ命名規則**:
- フォーマット: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`
- 例: `feature/I030-media-asset-models`

### 現在のブランチ確認
作業開始前に必ず現在のブランチを確認：
```bash
git branch --show-current
```
適切なブランチで作業していない場合は警告を出す。

### イシュー完了時のマージフロー

**詳細は「イシューフロー（統合ルール）」セクションを参照**

マージはイシューフローのステップ25で実行する。
- 全てのドキュメント更新（テストケース、エラー管理、計画書、イシューファイル）完了後にマージ
- マージ後にレビューファイルをclosedに移動してクローズ完了

### 本番リリースフロー（重要）

**developの複数機能を本番環境（main）にリリースする場合のみ実行**:

```bash
# 1. bot が develop → main の PR を作る
gh pr create --base main --head develop --title "Release: vX.X.X" --body-file <リリースノートのファイル>
# 2. oshui0404 が GitHub の PR 画面で承認・マージする
# 3. マージ後、main の先頭にタグを付ける
git fetch origin main
git tag -a vX.X.X origin/main -m "バージョンX.X.Xリリース"
git push origin vX.X.X
```

**重要な注意事項**:
- mainへのマージは慎重に行う（十分なテスト完了後のみ）
- 必ずバージョンタグを付ける
- リリースノートを残す
- developからmainへは定期的（週1回、月1回等）にまとめてマージ

### 緊急修正（hotfix）のブランチ運用

本番環境で緊急のバグ修正が必要な場合：

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

**main がまだ初期コミットだけの間は、main への hotfix はマージできない**（main から作ったブランチには CI のワークフローが無く、必須チェックが報告されないため。docs/runbooks/branch-protection-setup.md §1.5「main の制約」）。最初のリリース（develop → main）より前は、緊急の修正も develop 宛ての PR で行い、リリースで main に入れる。

**hotfixの重要ポイント**: mainとdevelop**両方**にマージすること。
- mainとdevelop**両方**にマージすること（忘れると修正が失われる）
- 本番環境への影響を最小限にするため、修正は最小限に
- テストは迅速だが確実に実施

### ブランチ作成例外ルール
以下の場合はブランチ作成を省略可能：
1. **ドキュメントのみの修正**: README更新、typo修正等
2. **緊急の1行修正**: 明らかな設定ミス等
3. **ユーザーが明示的に指示**: 「ブランチ作成不要」等の指示がある場合

ただし、**イシューファイル作成依頼の場合は必ずブランチを作成**すること。

## 外部（fork）からの PR の扱い

public リポジトリのため、第三者（自律 AI エージェントを含む）から fork 経由の PR が届くことがある。
外部からのコード寄稿は受け付けない（`CONTRIBUTING.md`）。届いた場合は次の手順で処理する。

1. head リポジトリを確認する: `gh pr view <PR番号> --json isCrossRepository -q .isCrossRepository` → `true` なら外部 PR。
2. **Actions の実行を承認しない**（fork PR には repository secrets が渡らず、E2E は原理的に失敗する）。
3. **base 追従・CI 対応・レビューをしない**（マージしない PR に投じる意味がない）。
   **手元に checkout しない**（`.claude/` と hook 本体が相手の版に置き換わり、次の操作でそのコードが実行されるため）。中身は `gh pr diff <PR番号>` / `gh pr view <PR番号>` で確認する。
   `gh pr checkout` と既定エイリアス `gh co` は PreToolUse ガードで block されるが、`git fetch origin pull/<N>/head` → `git checkout`・`gh pr diff <N> | git apply` などの別経路はガードの対象外なので、手順として行わないこと。
4. 方針コメントを付けて close する: `gh pr comment <PR番号> --body-file <file>` → `gh pr close <PR番号>`。
5. 対象のイシューは OPEN のまま残し、必要なら通常のハーネス手順（/plan-issue 以降）で自前実装する。

判定は `scripts/claude/pr-base-sync.sh`（close 段階の最初）と PreToolUse ガード
（`scripts/claude/hooks/pretooluse_guard.py`）でも自動検知されるが、上記は人が最初に見たときの手順である。
ガードは外部 PR への `gh pr merge` / `gh pr checkout`（`gh co`）と MCP の `merge_pull_request` を block、
`gh pr ready` / `edit` / `update-branch` / `review --approve` と MCP の `update_pull_request_branch` /
`create_pull_request_review`（APPROVE）を ask にする。読み取りと `close` / `comment` は断るために必要なので素通しする。
実行されるコマンドの中に `gh pr merge` 等があるのに判定しきれない場合は、block ではなく ask になる。
引用符の中の文字列やヒアドキュメントの本文（コミットメッセージ・文書・テスト用の文字列）には反応しない。
