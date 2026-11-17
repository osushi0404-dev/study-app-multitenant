# I546 計画書: 進め方の決まり（docs/runbooks・CLAUDE.md・記憶）をベストプラクティスのあるべき状態に見直す（最新化・漏れ・最適化）

## 基本情報
- **計画書ID**: plan_I546
- **関連イシュー**: #546
- **Draft PR**: #565
- **作成根拠資料**: docs/issues/open/I546.md（起点イシュー）
- **点検の結果の表**: docs/reviews/open/I546_rules_audit.md（節ごとの判定・根拠・正の置き場所。§0 が確定）
- **実装後評価**: docs/reviews/open/I546_review.md
- **作成日**: 2026-11-17

## 1. 背景/目的
- 進め方の決まりは振り返りのたびに手順書と Claude の手元の記憶の 2 か所に継ぎ足され、全体を通して見直していない。決まりは Claude が毎回読んで従うので、古さ・重複・矛盾はそのまま作業の誤りと手戻りになる
- 目的: `docs/runbooks/`（`ux-rules.md`・`backend-check.md` は I545。`ux-rules.md` §5 の 1 項目だけ扱う）・`CLAUDE.md`・記憶の feedback を、ループエンジニアリング・ハーネスエンジニアリングの BP と開発効率の物差しで「あるべき状態」にする（最新化・漏れ・最適化）

### 調査結果
**原因の概要**: 決まりを足すときに、同じ決まりがすでにどこにあるか・今の流れと合っているかを確かめず、足す場所もばらばらだったので、古い流れの手順・同じ決まりの写し・食い違いが積み重なった。

**詳細**（点検の結果の表 `docs/reviews/open/I546_rules_audit.md` に節ごとの全件。ここは要点）:
1. 今の流れと矛盾する古い手順: `docs/runbooks/issue-flow.md`「イシューフロー（統合ルール）」（約 285 行）は close 段階と逆の順（マージ → レビューを closed へ・手で `gh issue close`・完了情報の echo）。`docs/runbooks/workflow.md`「イシュー完了時のマージフロー」も同じ。`workflow.md`「ブランチ作成例外ルール」は直 commit を許し、`CLAUDE.md` 絶対ルール 3 と矛盾
2. 同じ決まりの写し（3〜4 重）: 計画外の実装をしない（`CLAUDE.md`・`workflow.md`・`plan-writing-rules.md` の中で 3〜4 回）・イシューの置き場所（3 か所）・トラックのラベル（4 か所で `.github/` の有無が食い違う）・外部 PR（3 か所）・計画書のヘッダー（2 つの手順書。テンプレートに無い）
3. ファイル間の矛盾: ローカル E2E のレート制限の外し方が `common-commands.md` と `frontend-verify.md` §8 で正反対／`common-commands.md` が案内する `docker compose config` は見張りの承認画面に当たる／`plan-writing-rules.md` が計画の前に手元で pytest を流せと言い、test-gate は「手元で流し直さない」／「大規模 rebase」が危険操作の例と「見張りは判定しない」の両方にある／`review-rules.md` のスキル点検の項目 2・4 が今のスキルの設計と公式の上限と合わない
4. 公式の今の挙動と合わない記載: `common-commands.md`「Bash 実行作法」の理由（束ねると許可に当たらない）は今の公式（部分ごとに判定）と違い、本当の理由はサンドボックスの外に出るかどうか（公式 sandboxing）／`review-rules.md` の「裏のサブエージェントは承認待ちに親が気づけない」は今の公式（承認画面は親に出る）と違う／`mcp-usage.md` の WebSearch の使える環境・モデル名が古い／`worktree.md` §2 の片付け・ロックの説明が公式と違う
5. 使われていない・古い記載: 計画書の `_2` 連番（実績 0 件）・「最低 5 分」の検討と時間の記録（0 件）・完了情報の echo（close の手順に無い）・flake8（今は ruff）・`template-sync.md`（ひな形が 5 本に固定）・`docs/runbooks/legacy/CLAUDE.md.20260302`（`docs/migration/CLAUDE_original.md` とバイト単位で同じ）・`CLAUDE.md:8`「Cursor 経由」・`README.md` の段階のスキルをユーザーが打つ流れ
6. 漏れ: 記憶の feedback 38 件のうち 9 件は手順書に無い決まり（規約と依存を開いてから自作を決める・公式の機能を土台にする・同梱の前に前提と広がりを確かめる・候補は分けて起票する など）。サンドボックスの外に出る条件（前置き・パイプ・振り向け）・`Closes #N` が既定ブランチ宛てでだけ効く・ワークツリーで許した許可が全ワークツリーに効く、も無い
7. 文書の文字を見るテスト: `scripts/claude/tests/` の 21 本が手順書の文字を読む。消す・移す節のうち i107・i179・i181・i185・i193・i202 の項目と `fixtures/i185/` の 2 本が当たる（点検の表の各「表5」）
8. 基準のテスト（2026-11-17・このワークツリー）: 上の 21 本を流し、20 本が合格。`test_i193_official_flow.sh` だけ F9 の 3 項目（`run-all.sh` の動き）が got=2 で不合格。手順書と関係の無い項目で、手元の環境（サンドボックス）の都合と見る（develop の CI は緑）
9. 番号の検査: `flow-stage.sh`・`gate-check.sh` など 6 か所が `^I[0-9]{3}$` で、I1000 で流れ全体が止まる。#563 まで来ていて、今の速さなら約 1 か月で届く（推測）。スクリプトの直しなので本イシューの範囲外 → 新しいイシューに起票する
10. スパイク（外部の挙動）: 公式の文書をネットから読めるか → 点検役が `code.claude.com/docs/en/` の memory・worktrees・skills・sandboxing・permissions・sub-agents・mcp・tools-reference と GitHub の文書を WebFetch で読めた（成立）
11. 環境前提: 文書とテストの文字の変更だけで、使う道具は git・gh・grep・bash・WebFetch。どれも使えることを確認済み（このセッションで実行）

## 2. 受け入れ条件
イシューの受け入れ条件と同じ（AC1〜AC9）。
- [ ] AC1: 対象の全部のファイル・節について、点検の結果（そのまま／直す／消す／足す）と根拠（公式の文書の出典と照らした日付）が表で残っている
- [ ] AC2: 同じ決まりを違う内容で書いた箇所が、ファイルをまたいでも無い（点検の表で、決まりごとに正の置き場所が 1 つに決まっている）
- [ ] AC3: 今の公式の機能・手順と合わない古い記載が残っていない（置き換えが要るものは #427 に、設定との食い違いは #520 に、点検の表の行を添えてコメントしてある）
- [ ] AC4: 漏れの点検の結果（足した決まりと、足さなかったものとその理由）が残っている
- [ ] AC5: 記憶の feedback_*.md の全件について、移した／残した（個人の好み）／消した（古い）とその理由が表で残り、移したものが記憶と手順書の両方に残っていない
- [ ] AC6: `CLAUDE.md`・`worktree.md` に、特定の道具（Cursor）を前提にした記載が無い
- [ ] AC7: 「絶対ルール」「止めて聞く条件」「危険操作の承認」の中身を変えたときは、実装の前にユーザーが確認した記録がある（変えていなければその旨）
- [ ] AC8: `ux-rules.md` §5 に「流れの途中の空の状態」の決まりがある
- [ ] AC9: 書き換えで切れた参照（ファイル名・節の名前）が無い（変えた名前を `.claude/`・`docs/`・`scripts/claude/`・`CLAUDE.md` で検索して確かめる）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: なし（`.claude/settings.json`・`.github/`・`.secrets.baseline` は触らない）
- ハーネス: Claude・レビュー役が読む手順書・テンプレートが変わる。手順書の文字を見るテスト（`scripts/claude/tests/`）の期待を合わせる（仕組みは変えない）。Claude の手元の記憶（リポジトリの外）から手順書に移した決まりを消す

## 4. 変更点一覧（具体）

### 修正アプローチ
点検の結果の表（`docs/reviews/open/I546_rules_audit.md`）の §0 の確定と、§1 以降の各表の「判定・変更内容」のとおりに書き換える。表が節ごとの正で、ここはファイルごとの要約。決まりは 1 か所に置き、ほかはファイル名と節名で参照する。足すのは「気づきにくく被害が大きい」ものだけ。

### 4.1 ファイルごとの変更
| ファイル | 変更内容（詳細は点検の表の該当の行） |
|---|---|
| `CLAUDE.md` | 冒頭の定型文を消す・「Cursor 経由」→「端末・IDE の拡張のどちらでも」・§2 を §0 の索引の 1 行に・§3 を「権限と守り」にして 3 層（サンドボックス・見張り・GitHub の保護）を書く・索引から `template-sync.md` を消し `issue-flow.md` の説明を直す・U6 の結果で絶対ルール 4 の言い回し |
| `docs/runbooks/workflow.md` | 題を直す・「イシューの置き場所」を `issue-flow.md` へ・「外部（fork）からの PR の扱い」を `danger-ops.md` へ・「移行」「Claude Code実行ルール」「作業実行前の確認ルール」「修正ツール使用前チェック」「現在のブランチ確認」「イシュー完了時のマージフロー」「ブランチ作成例外ルール」を消す・「ゲート」に計画のゲートを 1 行で・ブランチ名を「I＋GitHub の番号」に・本番（まだ無い）・hotfix の重複を消す・起票の節を U2 の結果で直す・`Closes #N` は既定ブランチ（develop）宛てでだけ効く 1 行・記憶から移す 3 行（根治で比べて 1 案に決める／AC の文言を目的に合わせて狭める／整理済みの小さな追加に /simplify を回し直さない） |
| `docs/runbooks/issue-flow.md` | 題を「イシューの扱い（番号・置き場所・起票・ラベル）」に・置き場所の正にする・「イシューフロー（統合ルール）」「イシュー対応中のブランチ運用」を消す・起票の手順はスキルを正にしてラベルの決まり（`.github/` を含む版）だけ残す・U1・U3 の結果を反映・記憶から移す 2 項目（候補は分けて起票／同梱の前に前提と広がりを確かめ、目的を崩す指摘は一覧に回さない） |
| `docs/runbooks/worktree.md` | §2 の確認 2・版の注記・I179 前の注意を消し、片付け・ロックの説明を公式に合わせる・Cursor の記載を「IDE（VS Code・Cursor など）」に一般化・§4 の判定の説明を縮める・§6 の例のコマンドを分ける・§7 に「ワークツリーで許した許可は全ワークツリーに効く」・§8 を `issue-flow.md` へ（番号は詰めない）・§9 を縮め公式の分離を 1 行・§10 の表を参照 1 行に・§11 を消す |
| `docs/runbooks/plan-writing-rules.md` | 494 行 → 約 200 行。1)〜9) は形をテンプレートに任せ書く中身だけ・事前の 3 節（既存テスト・lint・検査ツール）を 1 節に（ベースラインは develop の CI の結果・flake8 を消す）・観測手段の一覧を 1 か所に（「プレーン default」→「通常モード（Manual）の新しいセッション」）・「見張りに判定を足す計画」を `danger-ops.md` の参照 1 行に・一致性保証ルールを基本原則・計画変更記録の形・例外の 3 つに（「最低 5 分」・cat・echo・5 つの質問・`_2` 連番・完了情報・`completed/` を消す）・「test-gate 段階の運用」を 1 行に・`template-sync.md` の決まり 2 行を受け取る・記憶から移す 4 行（規約と依存を開いてから自作を決める／公式の機能を土台にする／テストの差し替えより設計を直す／AC は結果で書く）。「実施者の区別」の名前と、テストが見る 4 語は残す |
| `docs/runbooks/review-rules.md` | 187 行 → 約 100 行。ヘッダーの写し・状態管理の経緯・「レビュー内容の必須要素 A〜D」「レビュー活用方法」「レビュー実施タイミング」を消す・命名の表に `I###_fix_diagnosis_<ts>.md` と `docs/reviews/backlog/I###.md` を足す・「検証の全体設計」の裏のサブエージェントの理由を公式に合わせて書き直す（方式は変えない・見出しは変えない）・敵対的レビューの節の重複 2 行を消し、計画のやり直しの文は `workflow.md` の参照に（`test_i181` D10 を直す）・スキル点検の項目 2（`disable-model-invocation` と `user-invocable: false` の使い分け）・項目 4（公式の 1,536 文字）を直す・記憶から移す 1 行（工程を減らすときは漏れの種類と上流の原因で判断） |
| `docs/runbooks/danger-ops.md` | 冒頭の条件を「強制されるもの／人の約束」で書き分け U6 の結果を反映・U5 の結果を反映・サンドボックスの節に外に出る条件（呼び出しの中のコマンドが全部当たるときだけ・前置き／パイプ／振り向け／`$(…)`／`cd` で中に戻る・中の `gh` は鍵が読めない）を足し `common-commands.md`「Bash 実行作法」を吸収・見張りの判定の順の実装の細部を縮めて正を見張りとテストに・新しい秘密の deny の説明を公式に合わせる・「未コミット変更の取り消し」を例の Git 行へ・「実行テンプレ」をテンプレートへ・外部 PR の手順を受け取る。テストが見る語（`--no-verify`・`20 秒`・`512MB`・`volume rm / prune`・`wt-remove.sh` など）は残す |
| `docs/runbooks/common-commands.md` | 201 行 → 約 95 行。ログ・`analyze_logs`・テストのコマンドをコンテナで動く形に（テストは関係するファイルだけ・全体は CI の 1 行）・ポート分離を 1 行と参照に（確認は `docker compose port`）・「Bash 実行作法」「未コミット変更の取り消し」「API エンドポイント」「ディレクトリ構造」「注意事項」「修正済みの問題」を消す・E2E の節を `frontend-verify.md` §8 の参照 1 行に・webpack の節を縮める・Bash ツールの終了コードの読み方 1 行（記憶から） |
| `docs/runbooks/pre-commit.md` | セットアップを `onboarding.md` へ（detect-secrets の版を `.pre-commit-config.yaml` に合わせる）・フック一覧に `check-dependabot`、対象の範囲を実物に・JWT の節を baseline の節にまとめる・誤検知の対処で `audit` は人が行う／Claude は pragma・「ロールバック」を消す・ESLint のフックはサンドボックスの中では Docker に届かない 1 行（一覧 I468 R1） |
| `docs/runbooks/dependency-audit.md` | 見張るものの一覧を `.github/dependabot.yml` を正にして写さない・`tools/api-types` の抜け・同じ注意の重複・起動コマンドを参照に・Dependabot の PR を計画の流れに通さない例外と供給網の残余のリスクを 1 行ずつ（一覧 I213 F7・F10） |
| `docs/runbooks/harness-audit.md` | 点検の範囲に「Claude の手元の記憶」「利用者の設定（`~/.claude/`）」「`.worktreeinclude`」を足す・`gh auth status` を `--json` なしで流すと鍵が出る注記 |
| `docs/runbooks/template-sync.md` | 消す（決まり 2 行を `plan-writing-rules.md` へ） |
| `docs/runbooks/onboarding.md` | 193 行 → 約 105 行。冒頭を今の形に・流れ・ブランチ・構成・参照先・止める条件・CI の中身の写しを参照に（`test_i185` TC-14⑦ の行は残す）・`pre-commit.md` のセットアップを受け取る・版を上げる手順の例を今の版に（一覧 I211 F7・A3・A1）・U7 の結果で「全部 pass しないとマージ不可」を事実に |
| `docs/runbooks/branch-protection-setup.md` | 2 つの表を 1 つに・件数（5／7）を書かず §2 の一覧を参照・移行期の節と廃止の確認 5 を消す・I430 で push・外部 PR のマージの守りがこの設定にあることを 1 行・U7 の結果で §2 に E2E |
| `docs/runbooks/github-app-setup.md` | §1 の起動行の写しを参照に・§5 の説明を縮める・§7 を時点に依らない書き方に・§9 を短く（番号は変えない）・設定を変える API は権限不足を 404 で返す 1 行（記憶から） |
| `docs/runbooks/mcp-usage.md` | WebSearch の節を公式に合わせて 3 行に・§3 を §1 の表へ（見張りに MCP 向けの部分が残っているという誤りを消す）・§4 のモデル名と起動確認を消す・§5 に `claude -p` は project の MCP を承認なしで読む／新しい MCP は見張りの matcher と allow を決める、の 2 行 |
| `docs/runbooks/frontend-verify.md` | §2 の版は `e2e/package.json` を参照・番号なしの 2 節を `###` に（語「画面確認」は残す）・§8 を E2E を流す手順の正にする（安全なコンテキスト・オーバーレイ）・§10 の待つ日数を `dependency-audit.md` の基準に・§11 を縮める・§12 に `/mcp reconnect all`。§9・§12 の番号と名前は変えない |
| `docs/runbooks/ux-rules.md` | §5 に 1 項目だけ: 「初めて使う人の流れ（作る → 中身を足す → 使う）では、各段の途中の状態（親はあるが中身が 0 など）ごとに、①次にやること 1 つを目立つボタンで示す ②その状態で押せる操作はエラーの通知で戻されない（押せないか、案内に置き換える）を決める」（#546 のコメント） |
| `docs/runbooks/legacy/`（`CLAUDE.md.20260302`・`.gitkeep`） | 消す（同じ内容が `docs/migration/CLAUDE_original.md` にある） |
| `docs/plans/templates/plan_template.md` | `## 基本情報`・`### 調査結果`・`### 修正アプローチ`・`## 計画変更記録`、条件付きの 10〜15 の 1 行、Danger Ops の 4 項目（影響範囲・代替案・ロールバック・実行コマンド）を足す |
| `docs/reviews/templates/review_template.md` | `## 自律判断の記録` を足す |
| `docs/claude-code-structure.md` | 今回の書き換えで食い違う行だけ直す（legacy・template-sync・旧いレビューの命名・「9 承認ポイント」・計画書の節の説明） |
| `docs/migration/MANIFEST.md` | legacy の 3 行に「I546 で削除・同じ内容は `docs/migration/CLAUDE_original.md`」と注記（移行の記録なので消さない） |
| `README.md` | 「バイブコーディング運用（Claude Code）」の 11 行を `CLAUDE.md`・`docs/runbooks/workflow.md` への参照 2 行に |
| `scripts/claude/tests/`（i107・i179・i181・i185・i193・i202 と `fixtures/i185/` の 2 本） | 消す・移す節の文字を見る項目を合わせる。消した節の文字だけを固定する項目は項目ごと消す。仕組みを確かめる項目は変えない |
| `~/.claude/projects/-mnt-c-app-study-app-multitenant/memory/`（`feedback_*.md`・`reference_*.md`・`MEMORY.md`） | 点検の表 E のとおり: 移したもの（記載済みを含む）と消すものを消し、残すもの 6 件（`always_japanese`・`count_all_transcripts`・`plain_language_user_facing`・`timebox_review_agents`・`warn_before_approval_prompt`・`reference_clipboard_powershell_utf8`）は古い部分を直す。`MEMORY.md` の索引を直す（リポジトリの外。PR には入らない） |
| `docs/reviews/backlog/`（I211・I213・I220・I224・I226・I468） | §9 で同梱とした行を、直した後に消す |
| `docs/reviews/open/I546_rules_audit.md` | 点検の結果の表（作成済み）。実装で確定した結果・起票とコメントの番号を足す |

### 4.2 起票とコメント（AC3）
- 新しいイシュー（issue-bootstrap を Claude が呼ぶ）: イシューの番号の検査が 3 桁固定で I1000 から流れが止まる（調査結果 9）。トラックは harness・最優先
- #520 にコメント: `workflow.md`「スキル呼び出しルール」の「順番を外れた進行を止める」が一部実際と合わない／`dependency-audit-issue.sh` の本文が手順書と逆／定期監査に `tools/api-types` が無い／開発でメールを送らない仕組みが確かめられない（被害が大きいので優先）／`test_guard_corpus_diff.sh` のコメントの本数／`harness-audit.md` の点検コマンドがサンドボックスの中で正しく動くか／E2E の必須チェックと文書（U7 の結果）／`npm ci` がサンドボックスの中で通るか
- #427 にコメント: `worktree.baseRef: "fresh"` と set-head／公式のロックの掃除と `wt-remove.sh`／公式のワークツリーの分離と見張り／`/doctor prompt-audit` で決まりの矛盾の点検／head ブランチの自動削除の設定／Actions の SHA 固定を GitHub の設定で強制・lockfile／Dependabot alerts と自作の定期監査／pre-commit 本体の入れ方の一本化／ブランチ保護を rulesets へ移し設定を決定論で確かめる／`.mcp.json` の版を Dependabot に乗せる／`lint_skills.py` を CI で流す
- #547 にコメント: 本イシューで名前・中身を変えた節を参照しているスキル・レビュー役の行（close の「完了情報追記」の語・implement のテストのコマンド・plan-reviewer のスキル点検の写し・同梱のコメントを `issue-source.sh` が読まない〔一覧 I221 F9〕）

## 5. 実装手順（ステップ）
0. **（計画レビューの後・実装の前）ユーザーに 1 度だけ確かめる**: 点検の表 §0.3 の U1〜U7 をまとめて聞き、答えを §9 と点検の表 §0.3 に書く。答えが「残す」のものはその節を変えない（止めて聞く条件 2・設計確認メモ）
1. **流れの手順書**（`CLAUDE.md`・`workflow.md`・`issue-flow.md`・`worktree.md`）を書き換え、当たるテスト（i107・i179・i185・i193・i202 と fixtures）を合わせる。ステップ 0 の後（→ TC-01）
2. **計画とレビューの手順書**（`plan-writing-rules.md`・`review-rules.md`・2 つのテンプレート・`template-sync.md` の削除）と当たるテスト（i181・i193）。ステップ 1 と並行してよい（→ TC-01）
3. **安全と依存の手順書**（`danger-ops.md`・`common-commands.md`・`pre-commit.md`・`dependency-audit.md`・`harness-audit.md`）。ステップ 1 の後（外部 PR の手順を受け取るため）（→ TC-01）
4. **準備と環境の手順書**（`onboarding.md`・`branch-protection-setup.md`・`github-app-setup.md`・`mcp-usage.md`・`frontend-verify.md`）と `ux-rules.md` §5・legacy の削除・`README.md`・`docs/claude-code-structure.md`・`docs/migration/MANIFEST.md`。ステップ 3 の後（E2E の正の置き場所を決めてから）（→ TC-01〜TC-03）
5. **記憶**: まず消す・直す対象のファイルを、記憶のフォルダの中の `archive_I546/` に元の全文のまま移す（索引 `MEMORY.md` からは外れ、元に戻すときはそこから戻す）。次に点検の表 E の「移す」の各行に、移す先で確かめる固有の語（確認語）を 1 つずつ足し、移す先にその語があることを確かめてから、記憶を消し・直し、`MEMORY.md` を直す。ステップ 1〜4 の後（→ 手動 No.3）
6. **参照と食い違いの全件の確かめ**: 手順書・テンプレート・スキル・レビュー役・スクリプトの中のパス・節名の参照を抜き出して実在を確かめる（→ 手動 No.2）
7. **起票とコメント**: 4.2 のとおり（→ 手動 No.4）
8. **一覧と記録**: 同梱した一覧の行を消し、点検の表に確定した結果を足し、計画変更記録・自律判断の記録を整える

## 6. テスト計画
### 自動
- 決定論ゲート（`docs/tests/open/I546_auto_test.md`）: 手順書の文字を読む既存のテスト 21 本（直した後も合格すること）＋「Cursor 経由」が無いこと・`ux-rules.md` §5 の決まりがあること。新しいテストのスクリプトは足さない（今回の変更はどれも意図的な変更でしか戻らない・`plan-writing-rules.md`「決定論テストの対象の選び方」）
- pytest・Jest・E2E: 変更なし（文書だけ）。CI に任せる
### 手動（すべて Claude）
- No.1 点検の結果の表が、元の全部の見出しを覆っているか（元の見出しの一覧と表の照合）
- No.2 書き換えた文書のパス・節名の参照が全部あるか（抜き出して `test -e`・見出しの grep）
- No.3 記憶の全件が表のとおりに処理され、移したものが記憶と手順書の両方に無いか（表 E の確認語で grep）
- No.4 起票・コメントが 4.2 の全項目について GitHub にあるか
- No.5 消した節の決まりのうち残すべきものが、正の置き場所に残っているか（点検の表の「消す」の行ごとに正の置き場所を grep）。あわせて `worktree.md` に Cursor を前提にした記載が無いこと（「IDE（VS Code・Cursor など）」の例示だけは許す）と、`ux-rules.md` §5 に ①次にやること 1 つ ②エラーの通知で戻されない、の 2 点があることを読んで確かめる

## 7. ロールバック
- 文書とテストの文字だけなので、PR を revert すれば戻る。消した legacy・template-sync は git の履歴から戻せる
- 記憶は消す前に元の全文を記憶のフォルダの `archive_I546/` に移しておく。戻すときはそこから元の場所へ移し、`MEMORY.md` の行を戻す
- 起票したイシューは閉じれば戻る（コメントは消せる）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 書き換えで、今の手順書にあった大事な決まりを落とす | 点検の表で元の全部の節に結果と正の置き場所を付け、手動 No.1・No.5 で確かめる | 回避 |
| R2: 文書の文字を見るテストを壊し、CI が落ちる | 点検の表の「表5」で当たる項目を全件挙げ、決定論ゲートで 21 本を流す | 回避 |
| R3: 公式の文書の読み違いで古い・誤った記載にする | 出典の URL と照らした日を表に残す。推測と書いた行（`worktree.baseRef` など）は書き換えず #427 で確かめる | 回避 |
| R4: 中身の変更（U1〜U7）を確認なしで入れる | 実装のステップ 0 で聞き、答えを記録してから書き換える（手動 No.1 の中で確かめる） | 回避 |
| R5: 記憶を消して、手順書に移っていない決まりを失う | 消す前に全文を `archive_I546/` に移し、表 E の確認語で移す先を grep で確かめる（手動 No.3） | 回避 |
| R6: 1 つの PR が大きい | 文書だけで戻しやすく、ファイル間の正の置き場所を同時に決める必要がある（分けると途中で写しと参照が食い違う） | 受け入れ |
| R7: legacy を消すときに commit の前のフックが `.secrets.baseline` を書き換え、高リスクのファイルが範囲に入る | 書き換わったら計画変更記録に書き、必ず確かめる項目を足して計画レビューをやり直す（I545 と同じ） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 範囲は `docs/runbooks/` の 16 本・`CLAUDE.md`・記憶・`ux-rules.md` §5 の 1 項目。スクリプト・設定・CI の仕組みは #520・#427
- 物差しはあるべき姿・ループとハーネスエンジニアリングの BP・開発効率
- Cursor の前提は道具を問わない書き方に
- 絶対ルール・止めて聞く条件・危険操作の承認の中身を変える案は、計画レビューの後・実装の前に 1 度だけユーザーに確かめる（U1〜U7。案が無ければ止まらない）
- 記憶のプロジェクトの決まりは手順書に移して記憶から消す。個人の好みは残す

Claude が決めた（技術的な選択と理由）:
- 点検は実装の前に済ませ、点検の結果の表を計画の変更点の正にする — 中身の変更案を実装の前に聞くには点検が先に要り、計画に書いていない書き換えをしないため
- 点検の結果の表は `docs/reviews/open/I546_rules_audit.md` — 計画書を太らせず、close の移動の対象に入る（I545 と同じ）
- 正の置き場所の決め方は点検の表 §0.1、点検役の案から変えたものは §0.2（`worktree.md` の set-head を残す・`docs/claude-code-structure.md` は消さず食い違う行だけ直す・`README.md` を範囲に入れる・テストの文字を合わせる）
- 手順書の文字を見るテストを同じ PR で直す — 直さないと CI が落ちる。仕組みは変えないので #520・#427 の範囲（仕組みの変更）に当たらない。消した節の文字だけを固定する項目は項目ごと消す
- テンプレート 2 本を範囲に入れる — 手順書から形の写しを消す先（形の正）として要る
- 1 つの PR にする（R6）
- ファイル名は変えない（`template-sync.md` と legacy は消す）・`worktree.md` と `frontend-verify.md`・`github-app-setup.md` の § 番号は変えない — スクリプト・スキル・テストが番号で参照するため
- 番号の検査の 3 桁固定は新しいイシューに起票する — 手順書の直しでは足りず、I1000 で流れが止まる（#520 の食い違いの話より急ぐ）
- `.secrets.baseline` の legacy の項目は触らない — 安全装置で、残っても害が無い
- 一覧 `docs/reviews/backlog/I211.md` F7・A3・A1（`onboarding.md` の版を上げる手順）: 同梱 — 対象のファイルの古い例の直し
- 一覧 `docs/reviews/backlog/I213.md` F7・F10（`dependency-audit.md`）: 同梱 — Dependabot の PR の例外と残余のリスクを 1 行ずつ。F11（例外の範囲の機械の確かめ）: 残す — スクリプトの話
- 一覧 `docs/reviews/backlog/I220.md` F2・F7・F8（`workflow.md`）: 同梱 — 起票の節と止めて聞く条件の関係を直すので一緒に解ける。F4（`onboarding.md` の流れ図）: 同梱 — 図を消す
- 一覧 `docs/reviews/backlog/I224.md` F5（`workflow.md`・`NOT_PUSHED` の安全網の範囲）: 同梱 — 書き方を事実に合わせる。F9（`FILE=-`）: 残す — 計測の話
- 一覧 `docs/reviews/backlog/I221.md` F9（同梱のコメントを `issue-source.sh` が読まない）: 残す — スクリプトとスキルの話。#547 のコメントに入れる
- 一覧 `docs/reviews/backlog/I226.md` F5（`CLAUDE.md` §3）: 同梱 — §3 を書き直すので解ける
- 一覧 `docs/reviews/backlog/I468.md` R1（`pre-commit.md` の ESLint とサンドボックス）: 同梱 — 1 行
- 一覧 `docs/reviews/backlog/I209.md` F1（`plan-writing-rules.md`・保存の後の表示の AC は読み取りの API で確かめる）: 残す — テストの書き方の決まりで、置き場所は `rules/`（I545 は閉じた）
- 一覧 `docs/reviews/backlog/I545.md` F5（`ux-rules.md` の 44×44px）: 残す — `ux-rules.md` は §5 の 1 項目だけ扱う
- 一覧 `FILE=-` の行（`docs/reviews/backlog/I223.md` B1〜B4）: 残す — GitHub の bot の話で、このイシューの対象と関係が無い

要件適合性・業務ロジック: 受け入れ条件の範囲を超えた仕様の追加は無い（`README.md`・テンプレート・テストの文字は、受け入れ条件 AC2・AC9 と CI を保つための付随の直し）。アプリの動き・テナントの範囲は変えない
セキュリティ: セキュリティ影響なし（コード変更なし）。安全の手順書（`danger-ops.md`・`pre-commit.md`・`github-app-setup.md`）は、守りを緩めない向きでだけ直す。秘密の検査を外す手順（`pre-commit.md`「ロールバック」）は消す。承認の対象を減らす案（U5・U6）はユーザーの確認を通す。依存の追加なし
P3/P5/P8 影響なし（DB・外部 API・非同期処理・インフラの変更なし）
P6 影響なし（画面の変更なし。`ux-rules.md` に決まりを 1 項目足すだけ）
P9 影響なし（個人情報・未成年データを扱わない）
設計品質: 決まりを 1 か所に置き、ほかは参照にする（写しを作らない）。強調の繰り返しを消し、守らせる仕組み（レビュー・ゲート）を正にする
設計判断の区別: 上の「Claude が決めた」はすべて技術的な仮定。要件・UI/UX の価値判断の仮定は無い（中身の変更 U1〜U7 は実装の前にユーザーに確かめる）

Danger Ops（有無/手順/ロールバック）:
- 無（文書の削除はあるが git で戻せる。記憶の削除は表 E から書き戻せる）

## 計画変更記録
- 2026-11-17 計画レビュー（`docs/reviews/I546_plan_review_20261117_1544.md`・OK）の Warning 4 件への対応: 手動 No.5 に `worktree.md` の Cursor の確認と `ux-rules.md` §5 の 2 点の確認を足した・記憶は消す前に全文を `archive_I546/` に移す（ロールバックの手段）・表 E の「移す」の行に確認語を足してから grep する。Info の i193（F9 以外の項目が手元で合格すること）は TC-01 の記録に書く。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない findings への対応の追記だけ）

## レビュー結果
- [20261117_1544 判定: ✅ 完了](../../reviews/I546_plan_review_20261117_1544.md)
