# レビュールール

## 参照（レビューの前提となる基準）
- プロダクト品質基準（C1〜C8・設計の北極星）: `docs/proposals/learning_app_quality_criteria.md`
- レビュー観点フレームワーク（P1〜P9）: `docs/proposals/review_perspective_framework.md`

## レビューの記録
- 実装の後の評価は `/plan-issue` が計画書と同時に作る `docs/reviews/open/I###_review.md`（形はひな形 `docs/reviews/templates/review_template.md`）の「テスト結果」「計画との差分」「自律判断の記録」と、retro の「振り返り」に書く。計画書の `## 基本情報` と相互に指す
- 計画書に書いてあることをレビューの記録に写さない

### 命名と置き場所
| 種別 | 命名 | 作るもの | 置き場所 |
|------|------|--------|----------------------|
| ライフサイクルレビュー | `I###_review.md` | `/plan-issue` | `docs/reviews/open/` → close 段階が `docs/reviews/closed/` へ移す |
| コードレビューの記録 | `I###_code_review_<timestamp>.md` | `scripts/claude/code-review.sh` | イシューが open の間は `docs/reviews/` の直下に貯まり、close 段階がそのイシューの分を `closed/` へ移す（I065） |
| 計画レビューの記録 | `I###_plan_review_<timestamp>.md` | `scripts/claude/plan-issue-review.sh` | 同上 |
| イシューレビューの記録 | `I###_issue_review_<timestamp>.md` | `scripts/claude/issue-review.sh` | 同上 |
| 敵対的レビューの記録 | `I###_adversarial_review_<timestamp>.md` | `scripts/claude/adversarial-review.sh` | 同上 |
| 診断レビューの記録 | `I###_fix_diagnosis_<timestamp>.md` | `scripts/claude/fix-diagnosis-review.sh` | 同上 |
| 軽い指摘の一覧 | `I###.md` | retro（`code-review.sh --route backlog`） | `docs/reviews/backlog/`（イシューを閉じても残る。計画で実装対象に当たる行を拾う） |

- `<timestamp>` は `YYYYMMDD_HHMM`（同じ分に 2 つ目ができると `_<n>` が付く）
- 古い通し番号の記録（`review001` など）は `docs/reviews/closed/` にそのまま残す

---

## 検証の全体設計（I197）

何を・どの段階で・何で確かめるか。LLM に任せるのは「読んで判断すること」だけにし、実行したかどうか・合否は決定論で出す。

| 層 | 何を確かめる | 何で | いつ（段階） | 止まり方 |
|---|---|---|---|---|
| 1 決定論 | テスト（pytest・Jest・E2E・ハーネステスト）・lint・型・注入（守りを壊すとテストが落ちるか）・計画が宣言した決定論ゲート・レビュー後の変更の有無 | CI・`code-review.sh` の決定論ゲート実走・`gate-check.sh` | implement の後・review-gate・test-gate・close | 失敗＝不合格（exit code） |
| 2 基本レビュー（独立した目） | 受け入れ条件・計画との照合・BP・セキュリティの見落とし | 組み込み `/code-review`（パスの判定が YES のときは `/security-review`。台帳の目印・計画レビューで高リスクになった分は敵対的レビューが受け持つ）・`code-reviewer`。どちらも別プロセスの `claude -p`・読むだけ・承認なし | review-gate 1 | 時間切れ・失敗・空は BLOCKER |
| 3 敵対的レビュー（高リスク時・独立した目） | 「合格」の反証。脅威モデル・要件の漏れ・設計の筋と、計画の「## 必ず確かめる項目」の各項目 | `scripts/claude/adversarial-review.sh`: 読むだけのレビュー役 3 観点を別プロセスで並列に起動し、実験案は実験役（別プロセス・自動承認モード・承認なし）が実行して `--resume` で結果を返す。判定は一覧からスクリプトが出す | review-gate 3 | 未検証・報告なし・時間切れ・拒否・作業ツリーの変更は合格にしない |
| 4 人 | 価値判断・操作感 | 手動テスト（Human の行）・マージ | test-gate・close | 人の返事 |

- **黙って止まらない・記録に残す**: 検証する側は別プロセスの `claude -p` を `--permission-prompts none` で起動する（承認が要る操作は待たずに拒否され、出力の `permission_denials` に残る）。会話の中のサブエージェントでは判定・時間・拒否が記録に残らず、実装した会話の文脈も持ち込むので、検証を任せない（I166。会話の中で手分けの調べ物をサブエージェントに任せるときは、時間と攻め筋の上限をプロンプトに書く）
- **周が収束する（I197）**: 基本レビューは 1 回目だけブランチ全体を見て、指摘を台帳（番号・重大度・状態）にする。やり直しは、見終えた最新の記録の `REVIEWED_COMMIT` からの差分（組み込みの `/security-review` が動かなかった回などは起点にしない・I212）と、台帳の止める指摘が直ったかだけを見る（全体を探し直すと指摘が減らないため）。fix-loop の中の実装・テストのレビューはやめ、診断だけを残す（同じ差分を重ねて見ない）。高リスク（敵対的レビューを走らせるか）は計画レビューの判定・パスの判定・台帳の目印（`RISK=up`・I202）で決め、一度 YES になったら戻さない。
- **止める基準は変更の種類で分ける（I205）**: 合否はスクリプト（`code-review.sh` の `blocking()`）が、code-reviewer の FINDING 行の欄（FILE・LINE・STOP・再現）から決定論で出す。code-reviewer の VERDICT 行・直す側の判断は使わない。種類は指摘の FILE のパスで決まる。

  | 変更の種類 | 止めるもの |
  |---|---|
  | アプリ本体（`app`。下の 2 つ以外すべて＝知らない場所は厳しい側） | イシューに関係する（ブランチで変えた行と前後 3 行、または受け入れ条件の未達 `STOP=ac:<番号>`）、再現のある Blocker・High・Medium（指摘 0 を目指す。Low の改善提案は止めない） |
  | GitHub から復旧できない例外（`guard`。`path_risk_trigger()` の集合） | Blocker・High（再現を問わない・I197 のまま） |
  | それ以外のハーネス（`harness`。`.claude/`・`scripts/claude/`・`docs/`・`rules/`・`CLAUDE.md` など） | 止める条件の一覧に当たり、再現のある指摘だけ（重大度は見ない）: ① 流れが動かなくなる（`flow`）② 秘密情報・個人情報が外に出る（`leak`）③ develop・main を直接壊す／GitHub から戻せない設定を壊す（`github`）④ 受け入れ条件の未達（`ac:<番号>`・番号必須） |

  - 共通: 再現（`| 再現: 入力・手順・壊れ方`）の無い指摘は止めない（guard を除く）。差分の外でも、セキュリティの Blocker（再現あり）は止める。差分の中か外かは行で決める（行が読めない・ファイルが無いときは止める側）。
  - 関所の穴（判定をすり抜けられる穴）は一覧に入れない。止めずに台帳に残す（後続のイシューに回ったときは最優先にする）。ハーネスは完璧を目指さない（GitHub が最後の守り）。
  - 止めない指摘は台帳に残り、retro が `bash scripts/claude/code-review.sh --route <issue|backlog> I###`（I208）で、台帳の欄の値だけで振り分ける（`.claude/skills/retro/SKILL.md` 4-0・I207）:
    - 後続のイシュー（1 件にまとめるか既存に同梱）: 止める指摘・再現のある Medium 以上・`SECURITY=yes` で再現ありか Medium 以上（Low かつ再現なしは一覧・I480）・アプリ本体（`KIND=app`）・guard の Medium 以上（再現を問わない）
    - 軽い指摘の一覧（`docs/reviews/backlog/`）: それ以外（Low、または再現なし）。出力の行を貼り、計画（`/plan-issue`）で実装対象のファイルに当たる行を見る
    - 受け入れの目印（`ACCEPTED=R<番号>`・I512）: 計画書の「## 8. Risk & 回避策」で処遇が `受け入れ` の R 番号（code-reviewer が付け、`--route` が計画書と照合する）で、Medium 以下・再現なし・アプリ本体でない行は一覧に回す。振り分けだけに効き、止める判定には効かない
  - review-gate ⇄ fix-loop の回数の上限（5 回目で止める）は最後の安全網。当たったら止め方の見直しの兆しとして止めて聞く。
- **自己申告で通さない**: レビュー役の「実験した」は、実験役の記録（実行したコマンド・拒否・結果）で確かめる。報告の無い観点・項目の行の無い項目は未検証。実装したセッションが書く自己レビューは判定の根拠にしない（自己認証の非権威化）。実装セッションは段取りを呼ぶだけで、判定に自分の読みを混ぜない。
- **網羅は計画の段階で決める**: 高リスクに当たりうる計画は「## 必ず確かめる項目」（項目ごとに `実験必須`／`読んで可`）を持つ。書き方（TC で覆える項目を含む）は `docs/runbooks/plan-writing-rules.md`「高リスクの計画の「必ず確かめる項目」（I228）」。
- **工程を減らす・まとめるとき**: レビュー・チェック・ゲートを減らす・まとめる案は、その工程が止めている漏れの種類と、回数を押し上げている上流の原因を分けて示してから出す。別々の漏れを止める工程はまとめず、中身を減らす（I181）。
- 方式の比較（裏のサブエージェント・メイン側・別プロセス・組み込み・GitHub 側）と採否の理由は `docs/plans/closed/plan_I197.md` §4.2。

## 高リスク変更の敵対的レビューステージ（自己認証の非権威化・I086／対象と上限・I181）

- **前提（GitHub が最後の守り）**: develop/main は GitHub 側で保護され（ブランチ保護・CODEOWNERS・承認必須）、bot はマージできない。手元のハーネスが壊れても GitHub から復旧できるので、手元のハーネスの変更は決定論ゲートと基本レビューで先へ進む。例外（GitHub から復旧できない操作）は `docs/runbooks/danger-ops.md`「GitHub から復旧できる範囲（I182）」。
- **対象**: 高リスク判定 YES の変更は、敵対的レビューステージ（反証マンデート×多観点・対応後の再レビュー）の通過を合格条件とする（review-gate 段階が自動で起動する）。高リスク判定 YES になるのは次のどれか:
  - (a) アプリの高リスク条件（`.claude/agents/code-reviewer.md`「高リスク判定の条件」）に当たる変更（計画レビューが判定する）
  - (b) ハーネスでは、例外に関わるファイルの変更だけ: `.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json`（正は `scripts/claude/code-review.sh` の `path_risk_trigger()`）
  - (c) 台帳の目印: 計画レビューが No でも、基本レビューの code-reviewer が (a) に当たる変更を差分に見つけて FINDING 行に `RISK=up` を付けたとき（I202。一度 YES になったら戻らない）
- **上限**: 1 周 10 分（`scripts/claude/adversarial-review.sh` が締め切る）・攻め筋 3 本・実験の往復は 1 観点 2 回まで・1 周 3 観点・イシュー全体で 2 周（review-gate のやり直しで数え直さない。報告の無い観点がある周は `ROUNDS: 0` で数えない）。2 周目は記録の `REVIEWED_COMMIT` からの差分だけ。判定は計画の「## 必ず確かめる項目」から決定論で出し、未検証が 1 件でも残れば合格にしない（I197）。前の周に実験で確かめた項目は、その周の `REVIEWED_COMMIT` から記録の場所の外と項目の行が変わっていなければ引き継ぐ（I228。正は `scripts/claude/adversarial-review.sh` の `carry_items`）。ガード・見張りは「普通の書き方による事故」までを Critical/High にする。手順の正は `.claude/skills/review-gate/SKILL.md` §3。
- **上限到達**: 自動 OK にせず、FINAL VERDICT HIGH 以上で停止してユーザーにエスカレーションする（`docs/runbooks/workflow.md`「止めて聞く条件」3。セキュリティにかかわる指摘を受け入れて進む判断は Claude だけではしない）。残った指摘と過去の周の指摘を種類ごとに集計し、同じ種類が 2 周続いていれば「止める場所・方式の見直し」を選択肢の先頭に置く。
- 敵対的レビューの周ごとに計画レビューを挟まない。計画レビューのやり直しの条件は `docs/runbooks/workflow.md`「ゲート」が正。

## GitHub から復旧できない変更のレビュー観点（I182）

公開リポジトリでは、次の変更は**マージしなくても PR を出した（push した）時点で**影響が出る。PR を出す前に確かめる（一覧と理由は `docs/runbooks/danger-ops.md`「GitHub から復旧できる範囲」）。

- **ワークフロー（`.github/workflows/`）の変更**: PR 側のワークフローが secrets 付きで動く。secrets を出力・外部へ送信していないか、`pull_request_target` を足していないか、`permissions` を広げていないか（最上位は `contents: read`）、pre-commit の `SKIP` に `detect-secrets` を足していないかを見る。
- **秘密情報の検査設定（`.pre-commit-config.yaml`・`.secrets.baseline`）の変更**: detect-secrets を外していないか、新しい秘密情報を baseline に足していないか（行番号の更新だけか）を見る。
- **コミットに秘密情報が入っていないか**: push protection は既知の形式の鍵しか拾わないので、`.env` の値・パスワード・トークンらしい文字列が差分に無いかを見る。

---

## スキルファイル変更時の Claude Code ベストプラクティス準拠（必須）

`.claude/skills/` の下のファイルを変えるイシューでは、変更が次の公式の推奨（https://code.claude.com/docs/en/skills ・2026-11-17 に照合）に沿っているかを確かめる。計画レビュー（`.claude/agents/plan-reviewer.md`）の観点に入っている。

### チェックリスト

| # | チェック項目 | 観点 |
|---|---|---|
| 1 | 使えるツールを絞る必要があるスキルは `disallowed-tools` で制限しているか。`allowed-tools` は「確認なしで使ってよい」事前許可で制限にはならないので、付けるなら本当に事前許可が要るものだけに絞っているか（素の `Bash` を事前許可していないか）（I185 P4） | セキュリティ |
| 2 | 呼び方を正しく絞っているか: ユーザーだけが始めるスキル（`/plan-issue`・`/grill-me` など）は `disable-model-invocation: true`、流れの中で Claude だけが呼ぶ段階のスキルは `user-invocable: false`（`disable-model-invocation: true` にすると Claude が呼べなくなる） | 安全性 |
| 3 | `argument-hint` が書いてあるか | 発見性 |
| 4 | `description` の先頭に「いつ使うか」があるか（`description` と `when_to_use` の合計 1,536 文字を超えると切られる） | 発見性 |
| 5 | 指示文に明確な停止条件・完了条件が書いてあるか | 明確性 |
| 6 | `$ARGUMENTS` などの変数が一貫して使われているか | 一貫性 |
| 7 | SKILL.md が 500 行以内か（超えるなら補助のファイルへ分ける） | コンテキスト効率 |
