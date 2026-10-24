# I193 設計書: 公式の道具を土台にした開発の流れ

- 作成日: 2026-10-24
- 対象: 計画からクローズまでの全工程（I193 設計確認メモで確定）
- 前提の版: Claude Code 2.1.310
- 出典は各節に記載する。「実証」はこの設計の前に実際に動かして確かめた結果（記録は `docs/plans/open/plan_I193.md` の「調査結果」）

## 1. 進め方（土台は公式）

1. 公式の道具だけで組んだ流れを先に描く（§2）
2. その流れで止まらなくなる漏れを挙げ、GitHub（CI・ブランチ保護）でも止まらないものだけを自作で載せる（§3）
3. 公式の道具ごとに、流れに入れる／入れないを実証つきで決める（§4）
4. ユーザーの確認と、途中で止めて聞く条件を決める（§5）

## 2. 公式の道具だけで組んだ流れ

出典: https://code.claude.com/docs/en/best-practices （「Explore → Plan → Implement → Commit」「Give Claude a way to verify its work」「Add an adversarial review step」「Have Claude show evidence」）

| 工程 | 公式の道具 | 公式の位置づけ |
|---|---|---|
| 調べる・決める | 要件の聞き取り（AskUserQuestion で SPEC を作る）・plan mode | 「Spec interview」「Explore first, then plan, then code」 |
| 実装 | 実装＋テストを書いて流し、失敗を直す | 「write tests ..., run the test suite and fix any failures」 |
| 整理 | `/simplify`（4 観点の並列レビューで重複・無駄を直す。正しさのバグは見ない） | commands.md |
| 確かめ | テスト・ビルド・CI。アプリを動かす確認は `/verify` | 「Give Claude a check it can run」 |
| レビュー | `/code-review`（差分の正しさのバグ）・`/security-review`（差分のセキュリティ）・別の文脈のサブエージェントによる反証 | code-review-local.md・「adversarial review step」 |
| 止める仕組み | フック（PreToolUse・Stop）・permissions の ask/deny・サブエージェントの `tools` 制限 | hooks.md・permissions.md・sub-agents.md |
| 人が見るもの | 証拠（テストの出力・実行したコマンドと結果） | 「Reviewing evidence is faster than re-running the verification yourself」 |
| 最後の守り | GitHub の CI（必須チェック）とブランチ保護（承認・マージはユーザー） | このリポジトリの branch-protection-setup.md |

公式に無いもの: イシュー・計画・テスト文書の置き方、計画のレビュー、受け入れ条件との照合、記録の残し方、振り返り、クローズの手順。

## 3. 公式だけの流れで止まらなくなる漏れと、自作で載せる差分

判断の基準（イシュー解決方針③）: 置き換えると漏れが止まらなくなり、GitHub でも止まらないものだけ自作で載せる。手間・便利さだけでは残さない。

| No | 公式だけでは止まらない漏れ | GitHub で止まるか | 自作で載せるか・形 |
|---|---|---|---|
| L1 | 受け入れ条件・計画どおりかの確認（公式 `/code-review` は計画・受け入れ条件を入力に取らない。実証 S3） | 止まらない（CI はテストだけ） | **載せる**: 自作のレビュー役 `code-reviewer`（公式のサブエージェント定義に移す） |
| L2 | 文書・スキル・スクリプト中心の変更の見落とし（公式 `/code-review` は大きな差分で文書・スキルを読み飛ばした。実証 S1） | 止まらない | **載せる**: L1 と同じ自作レビュー役が文書・スキルも見る |
| L3 | 計画書・テスト文書の欠け（実装前） | 止まらない | **載せる**: 自作の計画レビュー `plan-reviewer`（計画をレビューする公式機能は無い） |
| L4 | 計画書が宣言した決定論ゲートの実走と、その結果での判定の上書き | 一部（ハーネスのテストは CI で動いていない） | **載せる**: `code-review.sh` のゲート実走は残す。加えてハーネスのテスト一式を CI で動かす（§6） |
| L5 | 高リスク変更の判定（パスで決める・GitHub から復旧できない例外） | 止まらない | **載せる**: `code-review.sh` の `path_risk_trigger`／RISK 合成は残す |
| L6 | レビュー記録の保存と、判定（VERDICT）の機械的な読み取り | 止まらない | **載せる**: スクリプト側で保存・解析（公式 `/code-review` は合否の判定を返さない。実証 S3） |
| L7 | レビュー役が書き込みをしないこと | ― | **公式に置き換える**: サブエージェント定義の `tools: Read, Grep, Glob`（実証 S2。`disallowedTools` だけでは GitHub への書き込み道具などが残るため使わない） |
| L8 | レビューの時間切れ | ― | **公式＋差分**: `timeout` で包む（今は fix 系だけ。全レビュー呼び出しにそろえる） |
| L9 | 危険操作・別ワークツリーへの書き込み・fork PR・保護ブランチへの push | 一部（保護ブランチは止まる） | **残す**（I185 §4 で判定済み。公式の隔離はメインの checkout だけ、自動モードは確率で判定） |
| L10 | 採番・base 追従・文書の整合チェック・ワークツリーの後始末 | 止まらない | **残す**（公式に相当なし。I185 §4） |
| L11 | 実装前のセキュリティ設計レビュー（高リスク時） | 止まらない | **載せる**: 名前を `design-security-review` に変え、公式 `/security-review`（実装後）と分ける |
| L12 | 途中で止まったときの再開（長い自律実行は途中で切れうる） | ― | **載せる**: 各段階が記録に `STAGE_DONE:` を書き、`/proceed` が続きから再開する |
| L13 | 自動の修正が、実際の差分を誰もレビューしないまま先へ進む（I185 敵対的レビューの種類 B。人の承認をなくすと人も見なくなる） | 一部（マージはユーザー） | **載せる（決定論）**: レビュー記録に `REVIEWED_COMMIT:` を書き、テスト段階・クローズの前に `gate-check.sh` が「最新のコードレビュー記録（高リスク時は敵対的レビュー記録も）が VERDICT OK で、その `REVIEWED_COMMIT` から今の HEAD までの差分とコミットしていない変更が、記録の場所（`docs/reviews/`・`docs/tests/`・`docs/issues/`・`docs/plans/`）の中だけ」を確かめる（詳細は計画書 §5.3）。修正の後は必ずレビュー段階を通り直さないと先へ進めない（I185 P11 の「close 前の機械確認」も兼ねる） |
| L14 | レビューの判定行（VERDICT）が無い出力が OK 扱いになる（I185 種類 C。`code-review.sh` の `detect_code_verdict` は VERDICT も表の印も無いと OK を返す） | 止まらない | **直す（決定論）**: VERDICT が読めないときは BLOCKER に倒す（`plan-issue-review.sh` は I185 で直し済み） |

## 4. 公式の道具ごとの採否（実証つき）

| 道具 | 採否 | どこで | 理由（実証） |
|---|---|---|---|
| `/code-review`（組み込み） | **入れる** | レビュー段階で、自作レビューの前に `claude -p` で実行し、指摘を自作レビュー役に渡す | 練習用リポジトリで、差分の正しさのバグを 6 件、行番号と失敗シナリオつきで返した（S3）。合否の判定は返さないので、判定は自作レビュー役が指摘ごとに「採用（Blocker/High）／理由つきで不採用」を決めて VERDICT を出す。対象は `origin/develop...HEAD` を明示する（対象を省くと、手元の古い develop と比べて無関係な 113 ファイルを見た。S1）。強さは `medium`（`low` は文書を読み飛ばした。S1）。このリポジトリでは自作の同名スキルが `claude -p "/code-review …"` でも組み込みを隠し、自作が動いた（S7）ので、自作を `review-gate` に改名してから使う |
| `/security-review`（組み込み） | **入れる** | 高リスク判定 YES のとき、レビュー段階で実行 | 既定のブランチ（develop）との差分を見る（`gh repo view` で既定 develop を確認）。自作の同名スキルが組み込みを隠していたので、自作を `design-security-review` に改名して解消する |
| `/simplify`（組み込み） | **入れる** | 実装段階の最後（commit の前） | 練習用リポジトリで重複関数を自動で書き換え、正しさのバグは「`/code-review` の対象」として触らなかった（S4）。役割が自作に無い（整理）ので重ならない |
| `/verify`（組み込み） | **入れない** | ― | 自動実行では許可が無いと何も動かせず、コードを読んだ判断だけになった（S5）。動かすには自動モードと、DB・env・複数サービスの起動手順が要る（skills.md「Inference gets unreliable ... a database, an env file ...」）。画面の確認は I187（Playwright MCP）で整える途中で、人の手動テストも残す（設計確認メモ）。ユーザーが自分で打つのは自由 |
| サブエージェント定義（`.claude/agents/`） | **入れる** | 7 本のレビュー役をここへ移す | `claude -p --agent <name>` でファイル定義を呼べ、`tools` の許可リストで読み取り専用になり、VERDICT の形も保てた（S2・S6） |
| スキルの `user-invocable: false` | **入れる** | 段階のスキル（ユーザーが打たないもの） | ユーザー用スキルから Skill ツールで呼べ、ユーザーが直接打つと動かなかった（S6） |
| フック | **今のまま** | PreToolUse（見張り）・PostToolUse（構文）・SessionStart | Stop フックで「記録を書くまで終わらせない」も検討したが、各段階の記録はスクリプトが決定論で書くので重ねない |
| `/goal` | **入れない** | ― | 条件の判定役はコマンドを動かさず読むだけ（goal.md）。止める条件は段階のスキルとスクリプトの判定で足りる |
| 有料の道具（`/code-review ultra`・GitHub Actions の Claude 連携） | **入れない** | ― | 無料の範囲に限る（設計確認メモ） |

## 5. ユーザーの確認と、止めて聞く条件

### 5.1 ユーザーが打つコマンド

| コマンド | すること | 止まるところ |
|---|---|---|
| `/issue-bootstrap [タイトル]` | 採番・イシュー作成・自己完結度レビュー・GitHub 登録 | 要件・基本設計・UI/UX で決めてもらうことがあれば、その質問だけして止まる |
| `/grill-me I###`（任意） | 要件・基本設計・UI/UX の質問だけをまとめて聞く | 回答待ち |
| `/plan-issue I###` | ブランチ・計画・計画レビュー →（高リスク）実装前のセキュリティ設計レビュー → 実装 → `/simplify` → push → CI 待ち → レビュー（公式 `/code-review`＋自作）→（高リスク）公式 `/security-review`＋敵対的レビュー → 必要なら修正の繰り返し → 計画書の専用テスト → Claude 担当の手動テスト | 人がやる手動テストの手前（人の分が無ければ、振り返り・クローズまで進んでマージ依頼で止まる） |
| 手動テストの結果を返信（OK / NG と内容） | OK: 振り返り → クローズ → マージ依頼。NG: 修正 → レビュー → テスト → もう一度手動テストを依頼 | マージ依頼 |
| `/proceed I###` | 途中で止まったとき・新しいセッションで、記録の `STAGE_DONE:` から続きを再開する | 上と同じ |
| GitHub で Approve & Merge | ユーザーだけが行える（ブランチ保護） | ― |

### 5.2 止めて聞く条件（この 3 つだけ）

1. 要件・基本設計・UI/UX の価値判断が要るとき（受け入れ条件・仕様・画面の配置/文言/操作の流れを変えないと進めないとき）
2. 取り消せない操作（CLAUDE.md の危険操作・秘密情報が push されうる操作・GitHub Actions の変更）と、安全装置そのものを変える操作（集合は `code-review.sh` の `path_risk_trigger` と同じ: `.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json`）。安全装置は人の承認を外した流れで最後に残る守りなので、Claude が自分で緩められないようにする（I193 の security-review で追加。ユーザーが「止める条件はベストプラクティスの観点で Claude が評価して決めてよい」と一任した範囲での追加）
3. レビューや修正の周回が上限に達し、安全側の選択肢（fail-closed に倒す・範囲を狭める・別イシューに切り出す）も取れないとき

それ以外（技術的な設計の選択・上限到達で安全側が取れる場合・直せるセキュリティの Blocker）は Claude が決め、`docs/reviews/open/I###_review.md` の「## 自律判断の記録」に理由を書き、止まったときにまとめて報告する。セキュリティの Blocker を「受け入れて進む」判断は Claude だけではしない。

### 5.3 振り返りの改善案

Claude が採否を決める。小さな直しはそのイシューで直し、起票が要るものはまず既存イシューへの同梱を探し、無理なものだけ新規に起票する（`/issue-bootstrap` を Claude が呼ぶ）。見送りも含めてマージ依頼のときに一覧で報告する。

リポジトリは公開なので、Claude が自動で書くイシューの本文・イシューへのコメントには、コマンドの出力・ログ・環境変数・記録（JSONL）の中身を貼らない。要約と `ファイル:行` の参照だけにする（今の `/issue-bootstrap` と同じ扱いを、人が目を通さない自動の起票でも守る）。

## 6. GitHub を最後の守りにするための追加

ハーネスのテスト（`scripts/claude/tests/test_*.sh` の 33 本）は、CI でも pre-commit でも動いていない（棚卸しで確認）。各イシューの auto_test.md に宣言されたときだけ動く。ユーザーの確認を減らす以上、ハーネスの回帰は CI で止める。

- `scripts/claude/tests/run-all.sh`（全テストを順に流し、1 本でも失敗なら非ゼロで終わる）を足す
- `.github/workflows/ci.yml` に「Harness Tests」ジョブを足す（GitHub Actions の変更なので、計画の承認を取ってから行う＝止める条件 2）
- 今の develop では 33 本中 2 本が失敗している（`test_i181_review_slim.sh` D8: review-rules の節にある `.claude/settings.local.json` がワークツリー・CI に無い／`test_i182_docs.sh` DOC6: danger-ops が `docs/issues/open/I181.md` を指すが closed へ移動済み）。CI に載せる前に直す
- 必須チェックへの追加はブランチ保護の設定で、bot には権限が無い（repo admin 権限なし）。ユーザーが GitHub の画面で行う（手動テストの項目）

## 7. スキルとレビュー役の新しい構成

| 区分 | 名前 | 元 | 主な変更 |
|---|---|---|---|
| ユーザー用 | `issue-bootstrap` | 同じ | 振り返りから Claude も呼べるようにする（`disable-model-invocation` を外す）。要件の質問だけして止まる |
| ユーザー用 | `grill-me` | 同じ | 質問を要件・基本設計・UI/UX に絞る |
| ユーザー用 | `plan-issue` | 同じ | 承認待ちで止まらず、手動テストの手前まで段階のスキルを順に呼ぶ |
| ユーザー用 | `proceed` | 新設 | `STAGE_DONE:` から続きの段階を決めて呼ぶ |
| 段階 | `plan-review` | `plan-issue-review` | 改名・`user-invocable: false`。計画を変えたら Claude が自分で呼ぶ |
| 段階 | `design-security-review` | `security-review` | 改名（組み込みとの重なりを解消）・`user-invocable: false` |
| 段階 | `implement` | 同じ | 最後に `/simplify` を呼ぶ・`user-invocable: false` |
| 段階 | `review-gate` | `code-review` | 改名（組み込みとの重なりを解消）。公式 `/code-review`・（高リスク時）公式 `/security-review`・自作レビュー・敵対的レビュー |
| 段階 | `test-gate` | `test` | 改名。手元での pytest/Jest/E2E の既定の流し直しをやめ（CI が正）、計画書が宣言した重いテスト・Claude 担当の手動テストを行い、人の分で止まる |
| 段階 | `fix-loop` | 同じ | ユーザー承認の待ちをなくし、止める条件 3 つに合わせる。戻り先は `review-gate` 1 か所 |
| 段階 | `retro` | 同じ | 改善案の採否・起票を Claude が行う |
| 段階 | `close` | 同じ | 振り返りを先に呼び、技術的な問題（develop との食い違いなど）は自分で解決し、マージ依頼で止まる |
| レビュー役 | `.claude/agents/*.md`（7 本） | `.claude/review-agents/*.md` | 移動・`tools: Read, Grep, Glob`（敵対的レビュー役だけは temp repo での再現実行のため `Read, Grep, Glob, Bash`）・`model: sonnet`。スクリプトは `claude -p --agent <name> --tools "Read,Grep,Glob"` と `timeout` で呼ぶ |

## 8. 移行

- 本イシューのマージ前に着手したイシューは、古い流れのまま最後まで進める（設計確認メモ）。スキルは各ワークツリーで checkout しているブランチから読み込まれるため、そのブランチが develop を取り込むまでは古いスキルが動く。/close の base 追従（`pr-base-sync.sh`）で新しいスキルが入ってくるが、その時点の /close は読み込み済みの古い手順で最後まで進む
- `/proceed` は、`STAGE_DONE:` が無い記録（新しい流れで始めていないイシュー）では再開先を決めず、その旨を報告して止まる（古い流れのイシューを新しい流れで誤って進めない）
- メモ（Claude の記憶）のうち、承認・コマンド待ちを前提にしたもの（実装は明示コマンドの後・方向性の選択だけで始めない ほか）は、マージ後に新しいルールへ書き換える

## 9. I185 の別イシュー候補（未起票）との関係

I185 報告書 §6 の「別イシュー」のうち、次は本イシューで扱う（起票しない）。

| I185 の案 | 本イシューでの扱い |
|---|---|
| P3 fix-loop の方針選びで止まらずに進める（実際の差分を確かめるゲート付きで） | fix-loop の承認待ちをなくし、L13 の `gate-check.sh` で実際の差分のレビューを強制する |
| P6 /test の手元の再実行を CI の確認に置き換え、CI 待ちを固める | `test-gate` の既定の再実行をやめる。`code-review.sh` の CI 待ちは打ち切り時に止まる（fail-closed）にする |
| P7 実装→コードレビュー→テストを止まらずに続ける | `/plan-issue` が段階のスキルを順に呼ぶ |
| P8 ハーネスの自動テストを CI で毎回実行する | §6 |
| P11 close 前の機械確認・レビューの時間上限 | L13・L8 |
| P12 運用手順書の古いルールを消す（P17・D8/DOC6 を同梱） | 手順書の書き直しと §6 の 2 本の修正。P17（工程の切れ目で `/clear`）は、段階をまたいで同じ会話で進める設計にしたため扱わない（各段階の状態はファイルにあり、文脈が溢れたら自動の要約に任せる） |
| P14 レビュー役を公式のサブエージェント定義に移す | §7 |
| P16 自作の security-review を改名し組み込みも使う | §4・§7 |

扱わないもの: P15（見張りを絞る。手間「大」で、本イシューの目的〔公式を土台にした流れ〕と独立）。

## 10. 取り下げの判断（I188・I192）

本イシューの /close で、I188（自作の置き換え）・I192（/code-review と /test の 1 本化）に残る作業があるかを確かめ、無ければ取り下げを提案する。
