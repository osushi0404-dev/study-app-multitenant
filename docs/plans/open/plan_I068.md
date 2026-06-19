# plan_I068: ワークフロー指示ファイル編集のメタ規律（P3 決定論ゲート＋P1/P2 手続き＋gate）

## 基本情報
- **計画書ID**: plan_I068
- **関連イシュー**: #140
- **Draft PR**: #142
- **作成根拠資料**: docs/issues/open/I068.md（起点イシュー・/grill-me 設計確認メモ確定済み）
- **実装後評価**: docs/reviews/open/I068_review.md
- **作成日**: 2026-06-19

---

## 1. 背景/目的

ワークフロー指示ファイル（`.claude/skills/*/SKILL.md`・`docs/runbooks/*`・`.claude/review-agents/*`）の編集に、コード並みの一貫性・決定論チェックが無く、I067 で 3 件（code-review Medium×1・plan-review Warning×2）がレビュー段階で初めて顕在化した。単一根本原因＝「指示ファイル編集にコード並みのチェックが無い」を、検証強度で階層化した 3 予防策で塞ぐ。

本イシューは bash スクリプト＋markdown 指示文の変更で、Django/React の app コードは無い。

### 調査結果
- **P3 母体は grill-me に既存**: `.claude/skills/grill-me/SKILL.md:54`「本文整合（必須）」が設計メモ↔本文の整合を散文で指示済み。P3 はこれを機械化する（コード確認済み）。
- **issue-review は不適**: `scripts/claude/issue-review.sh` は issue-bootstrap step3.5（grill-me より前）に走り、設計メモが未生成のため比較対象が無い（コード確認済み）。→ P3 ゲートは grill-me（メモ生成後）に置く。
- **P2 母体**: `docs/runbooks/plan-writing-rules.md:79`「規約是正時の消費箇所の全件列挙」。概念・セマンティクス変更に拡張する。
- **review-agents 実在**: `.claude/review-agents/{plan-reviewer,code-reviewer,issue-reviewer}.md` を確認。gate はここに追加。
- 既存テスト/lint ベースライン計測は不要（app コード・lint 対象の変更なし）。新規 bash スクリプトは pre-commit の shellcheck 対象になるため shellcheck 通過を実装時に確認する。

---

## 2. 受け入れ条件（Acceptance Criteria）
- [ ] P3: `scripts/claude/check-memo-body-paths.sh`（新規）が memo ⊆ body を機械判定し、メモにあって本文に無いパスを警告・非ゼロ終了する。`grill-me/SKILL.md` が「本文整合（必須）」直後に同スクリプトを実行する do を持ち、`plan-reviewer.md` に grill-me skip 時の backstop 観点がある
- [ ] P2: `plan-writing-rules.md` の消費箇所列挙ルールが「概念・セマンティクスの変更」を明示的に含み、`plan-reviewer.md` に対応する gate 観点が追加される
- [ ] P1: `plan-writing-rules.md` に分岐コマンド粒度パリティの do が、`plan-reviewer.md`・`code-reviewer.md` に対応する gate 観点が追加される
- [ ] I067 で発生した 3 件を新ルール/ゲートに当てはめ、計画段階または機械検証で検出できることを Claude が確認する（P3 は I068.md 等でゲートを実行しログを残す・P1/P2 は計画書の確認項目に当てはめ結果を記載）

---

## 3. 影響範囲
- Backend: なし / Frontend: なし / DB: なし
- Config/Infra: `scripts/claude/check-memo-body-paths.sh`（新規）／`.claude/skills/grill-me/SKILL.md`／`docs/runbooks/plan-writing-rules.md`／`.claude/review-agents/plan-reviewer.md`・`code-reviewer.md`

P3/P5/P8 影響なし（DB・外部API/非同期/バッチ・新規インフラ/依存ライブラリ追加なし）。P6 影響なし（UI なし）。

**セキュリティ**: 新規 bash スクリプトを追加するため以下を設計に含める（最小権限・入力検証）:
- 引数 `ISSUE` は `^I[0-9]{3}$` で検証してからパスに使う（パストラバーサル防止。close/SKILL.md の踏襲）。
- スクリプトはイシューファイルの内容を `awk`/`grep` で**読むだけ**で `eval`/実行しない（ファイル内容の任意実行リスクなし）。
- bandit/pip-audit/npm audit 対象外（Python/JS 依存変更なし）。pre-commit の **shellcheck** を通すことを完了条件とする。

---

## 4. 変更点一覧

| # | ファイル | 変更内容 |
|---|---------|---------|
| P3-a | `scripts/claude/check-memo-body-paths.sh`（新規） | 設計メモブロックのバックティック囲みパス ⊆ 本文構造化セクション（実装対象テーブル＋影響範囲）のパス、を判定。不一致を列挙し非ゼロ終了。プレースホルダ除外・引数検証付き |
| P3-b | `.claude/skills/grill-me/SKILL.md` | 「本文整合（必須）」直後に `bash scripts/claude/check-memo-body-paths.sh I###` を実行し、不一致があれば本文を整合（または意図的除外を本文明記）してから完了する do を追加 |
| P3-c | `.claude/review-agents/plan-reviewer.md` | backstop: 「設計メモのパスが本文の実装対象/影響範囲に反映されているか（grill-me skip 時の保険）」観点を追加 |
| P2-a | `docs/runbooks/plan-writing-rules.md` | 「規約是正時の消費箇所の全件列挙」を**概念・セマンティクスの変更**（判定基準・正とする対象等）にも拡張。P3 ゲートはこの決定論的インスタンスと明記 |
| P2-b | `.claude/review-agents/plan-reviewer.md` | gate: 「中核概念を変更する変更で、その概念を参照する同一ファイル内の全箇所が更新されているか」観点を追加 |
| P1-a | `docs/runbooks/plan-writing-rules.md` | do: 「指示ファイルへ条件分岐を追加する場合、対になる既存手順と同じ粒度（具体コマンド/ステップ）で書き暗黙の省略を残さない」を追加 |
| P1-b | `.claude/review-agents/plan-reviewer.md`・`code-reviewer.md` | gate: 「新規追加の条件分岐に、対の既存手順が明示するコマンド・ステップの非対称な省略が無いか」観点を追加 |

---

## 5. 実装手順（ステップ）

> 検証は自動テスト文書（`docs/tests/open/I068_auto_test.md`）の TC を参照。本文に検証コマンドを書かない。
> **未知リスク先行原則**: 新規スクリプト（P3）を最初に置く。**TDD（新規の振る舞い）**: P3 スクリプトは Red→Green→Refactor で実装する。

### ステップ1: P3 ゲートスクリプトを TDD で実装（変更 P3-a）
**修正方針**: 設計メモのパスが本文に反映されているかを機械判定する決定論ゲートを作る。memo ⊆ body（メモにあって本文に無いパスを検出）。誤検出抑制のため「バックティック囲み・`/` と拡張子を含むパス様トークン」のみ抽出し、本文側は構造化セクションに限定、プレースホルダ行は除外する。

**スクリプト設計（要点）**:
- 引数 `ISSUE`（`I###`）を `^I[0-9]{3}$` で検証 → `docs/issues/{open,closed}/I###.md` を探索。未検出は非ブロック（`exit 0`・警告）。
- セクション抽出: `awk` で「`## <見出し>` 行から次の `## ` まで」を切り出す。
- パス抽出: `grep -oE '` + "`" + `[^` + "`" + `]+` + "`" + `'` → バッククォート除去 → `grep -E '/.*\.[A-Za-z0-9]+$'`（`/` と拡張子を持つもののみ）→ `sort -u`。
- メモ集合 = `## 設計確認メモ（/grill-me）` セクション（`未特定`/`未定` を含む行を除外）からのパス。
- 本文集合 = `## 実装対象（既知のもの）` ＋ `## 影響範囲（想定）` セクションからのパス。
- `comm -23 <(memo) <(body)` で「メモにあって本文に無い」差分を算出。差分ありなら一覧表示し `exit 1`、無ければ `✅` で `exit 0`。
- **意図的除外の扱い**: 本文側が当該パスを（例: 「注: …は除外」の形で）言及していれば本文集合に含まれ整合扱いになる。言及が一切無いパスのみ警告される（ソフト警告＝Claude が追記 or 意図的除外を本文明記して解消）。

→ 検証: TC-A〜TC-E（Red で先にテスト作成→失敗確認→実装→PASS）

### ステップ2: grill-me に P3 実行 do ＋ plan-reviewer backstop（変更 P3-b / P3-c）
**修正方針**: grill-me の既存「本文整合（必須）」直後に P3 スクリプトを実行する手順を追加し、機械検証で締める。grill-me を skip する経路のために plan-reviewer に backstop 観点を追加する。
→ 検証: TC-F・TC-G(backstop)

### ステップ3: P2 — 消費箇所列挙を概念変更に拡張＋gate（変更 P2-a / P2-b）
**修正方針**: plan-writing-rules.md の消費箇所列挙ルールを概念・セマンティクス変更にも適用すると明記し、P3 ゲートをその決定論的インスタンスと位置づける。plan-reviewer に gate 観点を追加。
→ 検証: TC-H・TC-I

### ステップ4: P1 — 分岐パリティ do＋gate（変更 P1-a / P1-b）
**修正方針**: plan-writing-rules.md に分岐のコマンド粒度パリティ do を追加し、plan-reviewer・code-reviewer に gate 観点を追加。
→ 検証: TC-J・TC-K・TC-L

### ステップ5: ドッグフーディング・整合確認
**修正方針**: 完成した P3 スクリプトを実在イシュー（I068.md・I069.md）に対し実行し整合を確認。I067 の 3 件を新ルール/ゲートに当てはめて検出可能性を確認。
→ 検証: TC-E・TC-M

**依存関係**: ステップ1→2 は順序依存（do がスクリプトを参照）。ステップ3・4 は相互独立・ステップ1 と並行可。ステップ5 は全完了後。

---

## 6. テスト計画（自動/手動）

### 自動テスト（計画駆動）— 本イシューの正
`docs/tests/open/I068_auto_test.md` の TC-A〜TC-M を正とする。内訳:
- **P3 スクリプト単体テスト（TC-A〜E）**: 一時 fixture を heredoc で生成し `check-memo-body-paths.sh` を実行、終了コードと出力を assert（整合=0／不一致=1／プレースホルダ除外／バックティック無し無視／実 I068 でのドッグフード）。
- **指示文/ルール grep（TC-F〜L）**: grill-me 実行 do・plan-writing-rules 拡張・分岐パリティ do・各 review-agent の gate 観点の存在を `grep -F` 検証。
- **shellcheck（TC-M）**: 新規スクリプトが `shellcheck` を非エラーで通る。
- 既定 pytest/Jest/E2E は **非該当**（app コード変更なし）。
- テストレベル: ユニット（スクリプト挙動）＋結合（文書 grep）＋ドッグフード（実イシュー実行）。認証・認可・テナント境界テストは該当なし（認可変更なし）。
- **新規ツールの異常系**: P3 スクリプトは「不一致 fixture で非ゼロ終了」を TC-B で実行・記録する（文書品質ゲート準拠。スクリプトは実装ステップで作成するため、TC は実装時 TDD の Red→Green で実行・記録する）。

### 手動テスト
`docs/tests/open/I068_manual_test.md` 参照。文書レビュー（gate 文言の妥当性・誤検出可能性の確認）が中心。

---

## 7. ロールバック
- 新規スクリプト 1 ファイル＋4 文書のテキスト追記。`git revert <commit>` またはスクリプト削除＋該当ブロック削除で即時ロールバック可。サービス再起動不要。

---

## 8. Risk & 回避策
| Risk | 影響 | 回避策 |
|------|------|--------|
| P3 が memo 内の「意図的除外」パスを誤検出 | grill-me で余分な警告 | 本文が当該パスを言及（除外注記）すれば本文集合に入り整合扱い。言及無しのみ警告＝ソフト警告で Claude が追記 or 除外明記。TC で挙動固定 |
| バックティック無し/相対ファイル名のパスを取りこぼす | 一部不整合を見逃す | full-path（`/`＋拡張子）に限定するのは誤検出回避の意図的トレードオフ。backstop（plan-reviewer）と併用。Risk として明記 |
| glob パス（`*` 含む）の比較で不一致 | 余分な警告 | ソフト警告のため Claude が判断。必要なら本文に同 glob を記載して整合。実害は限定的 |
| 引数経由のパストラバーサル | 任意ファイル読取 | `^I[0-9]{3}$` 検証を必須化（close 踏襲）。TC で不正引数の非処理を確認 |
| shellcheck 違反で pre-commit 失敗 | commit ブロック | 実装時に `shellcheck` をローカル実行して通す（TC-M） |

---

## 9. 承認ポイント

### 設計判断の明示（イシュー明記 / 仮定）
| 判断 | 区分 | 根拠 |
|------|------|------|
| P3 を grill-me 主＋plan-reviewer backstop に配置（issue-review 除外） | **イシュー明記**（設計確認メモ） | I068.md 設計確認メモ・コード確認（issue-review はメモ前） |
| P3 を独立スクリプトで実装 | **イシュー明記**（設計確認メモ） | 同上（再利用・単体テスト可能な②） |
| 抽出はバックティック囲み full-path、本文は構造化セクション、memo ⊆ body、プレースホルダ除外 | **イシュー明記**（設計確認メモ） | 同上 |
| 不一致はソフト警告（非ゼロ終了・grill-me で整合） | **イシュー明記**（設計確認メモ） | 同上 |
| 引数 `^I[0-9]{3}$` 検証・read-only（セキュリティ） | **仮定（ベストプラクティス導出）** | イシューに明記なし。close/SKILL.md のパストラバーサル防止を踏襲した安全側の設計 |
| P1/P2 は①手続き＋gate（決定論化しない） | **イシュー明記**（設計確認メモ・retro 階層化） | I068.md |

> 仮定は「引数検証・read-only のセキュリティ設計」1 点のみ（ベストプラクティスからの導出で、リスク低減方向）。これを計画に含めてよいかご確認ください（既定推奨: 含める）。

### チェックリスト
- [x] 要件適合性: 受け入れ条件の範囲内（P1/P2/P3 の do＋gate＋P3 スクリプト）。スコープ外（I069 のレビュー記録 commit・I067 の完了分）には触れない
- [x] マルチテナント/ステータス遷移/認可: 該当なし（コード・認可変更なし）
- [x] セキュリティ: 新規スクリプトに引数検証・read-only を設計。shellcheck 通過を完了条件化。app/依存変更なしで bandit/audit 非該当
- [x] テスト計画: 再発防止＝TC-A〜M がスクリプト挙動・文書 gate・shellcheck を検証。テストレベル明示（ユニット＋結合＋ドッグフード、pytest/Jest/E2E 非該当）。P3 は TDD（Red→Green）
- [x] 設計品質: アンチパターンなし。ハードコード回避（イシュー番号・パスは引数/探索）。例外時は非ブロック `exit 0`（イシュー未検出時）
- [x] 文書品質ゲート: API/permission/DB は該当なし。auto_test の期待値（終了コード・出力文字列・grep ヒット）を具体記載。実装ステップ本文に検証コマンドを残さず TC 参照に統一。新規ツール異常系（TC-B）は実装時 TDD で実行・記録する旨を明記
- [x] P3/P5/P6/P8: 影響なし（上記）

### 文書間整合
- 計画書・auto_test.md・manual_test.md・review.md を同時作成。設計変更時は 4 文書を同時更新する。
