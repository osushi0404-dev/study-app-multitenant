# I074 自動テスト: fix-loop 多段サブエージェントレビュー順次ゲート

対象: `scripts/claude/fix-review-lib.sh`（共有 lib）/ `fix-diagnosis-review.sh`・`fix-implementation-review.sh`・`fix-test-review.sh`（エントリポイント）/ `.claude/review-agents/fix-{diagnosis,implementation,test}-reviewer.md` / `.claude/skills/fix-loop/SKILL.md` / `scripts/claude/tests/test_fix_review.sh`

実行コマンド: `bash scripts/claude/tests/test_fix_review.sh`（決定論ゲートとして下記「## 決定論ゲート（自動実走）」で実走）

結果:
- backend: N/A（bash スクリプト・指示ファイルのみ・Django 非関与）
- frontend: N/A

方式: `test_fix_review.sh` が `REVIEW_LIB_SOURCE_ONLY=1 source fix-review-lib.sh` で helper のみを取り出し（本体未実行）、`claude -p` を呼ばずに判定純関数・存在・回帰を決定論的に検証する（docker/ネットワーク非依存・read-only）。

## テストケース

| TC | 目的 | セットアップ | 期待値 |
|----|------|-------------|--------|
| TC-01 | source ガードで helper のみ定義（本体未実行） | `REVIEW_LIB_SOURCE_ONLY=1 source fix-review-lib.sh` | `detect_fix_verdict`・`verdict_to_gate`・`gate_exit_code`・`commit_review_artifact`・`run_fix_review` が `declare -F` で定義済み・本体（引数エラー等）が走らない |
| TC-02 | `detect_fix_verdict` = BLOCKER | 末尾に `VERDICT: BLOCKER` を持つ一時ファイル | 返り値 `BLOCKER` |
| TC-03 | `detect_fix_verdict` = HIGH | 末尾 `VERDICT: HIGH` | 返り値 `HIGH` |
| TC-04 | `detect_fix_verdict` = OK | 末尾 `VERDICT: OK` | 返り値 `OK` |
| TC-05 | `detect_fix_verdict` VERDICT 行不在→**空文字（判定不能）** | VERDICT 行なしのファイル | 返り値が**空文字**（`OK` を返さない＝false-green 回避。run_fix_review はこれを SKIP＝「判定不能」に落とし PASS にしない） |
| TC-06 | **decoy 部分一致に釣られない（I094）** | 本文に `VERDICThHIGH`・`# VERDICT: HIGH（例示）`（行頭でない/装飾付き）を含み、末尾に正規 `VERDICT: OK` | 返り値 `OK`（アンカー `^VERDICT:...$` 完全一致で decoy を拾わない） |
| TC-07 | **decoy 非近接キーワード（I094）** | 散文中に `BLOCKER` `HIGH` 単語が登場、末尾に `VERDICT: OK` | 返り値 `OK`（末尾 VERDICT 行のみ判定） |
| TC-07b | **decoy 中間行の正規 VERDICT（`tail -1` 検証）** | ファイル中間に行頭・正規フォーマットの `VERDICT: HIGH`（reviewer が対話例で記述）を置き、末尾に正規 `VERDICT: OK` | 返り値 `OK`（`| tail -1` で最後の判定を採り中間行に釣られない。`tail -1` を外した複製は `HIGH` を返す反証込み） |
| TC-08 | `verdict_to_gate` BLOCKER→REMAND | — | `REMAND` |
| TC-09 | `verdict_to_gate` HIGH→REMAND | — | `REMAND` |
| TC-10 | `verdict_to_gate` OK→PASS | — | `PASS` |
| TC-11 | `gate_exit_code` PASS→0 / REMAND→1 | — | `gate_exit_code PASS`＝`0`・`gate_exit_code REMAND`＝`1` |
| TC-12 | **false-green 反証: HIGH が PASS に漏れない** | しきい値を「BLOCKER のみ REMAND」に**壊した複製関数** `verdict_to_gate_broken` に HIGH を渡す | 壊した複製は `PASS`（=バグ）を返す一方、正規 `verdict_to_gate HIGH` は `REMAND` を返す ⇒ HIGH を確実に差し戻す実体があることの反証（両者の差分で検出） |
| TC-13 | **false-green 反証: ゲートが常時 0 の空振りでない** | 正規 `gate_exit_code`（`verdict_to_gate` 経由） | `OK`→exit0 だが `HIGH`/`BLOCKER`→exit1（TC-08/09/11）。全入力で 0 を返すマッピングではないことを確認 |
| TC-14 | reviewer 3 定義の存在＋契約 | 実ファイル | `fix-diagnosis-reviewer.md`・`fix-implementation-reviewer.md`・`fix-test-reviewer.md` が存在し、各々に「読み取り専用（Read/Grep/Glob）」記述と末尾 `VERDICT:`（`BLOCKER`/`HIGH`/`OK` 列挙）を含む |
| TC-15 | reviewer の観点キーワード | 実ファイル | 診断＝「影響調査」「同型」/ 実装＝「回帰」「副作用」/ テスト＝「false-green」または「否定」「異常系」を各々含む |
| TC-16 | 3 スクリプトの存在＋起動契約 | 実ファイル | 3 エントリポイントが存在し、各々（または source する lib）に `claude -p`・`--tools "Read,Grep,Glob"`・`--model claude-sonnet-4-6` を含む |
| TC-17 | **decoy: `--tools` に書込ツールが混入していない（最小権限回帰）** | 3 スクリプト＋lib の実ファイル、および反証用に `--tools "Read,Write,Glob"` を含む文字列変数 | 実ファイルの `--tools "..."` **引用符内**に `Write`/`Edit`/`Bash`/`MultiEdit` が現れない（`grep -E '\-\-tools[[:space:]]+"[^"]*(Write|Edit|Bash|MultiEdit)[^"]*"'` が0件＝コメント行の「`# --tools に Write を含めない`」等で false-positive しないよう引用符内限定・ツール名は引用符内の任意位置を許容）。**反証**: `--tools "Read,Write,Glob"` を含む文字列に対し同 grep が**一致（検出成功）**することを確認＝検出ロジックが実体を持つ（常時 0 件を返す空振りでない） |
| TC-18 | fix-test-review が全差分＋結果を入力にする | `fix-test-review.sh` | `git diff`（修正＋テスト）と第2引数のテスト結果を context に含める記述（テスト差分単体でない） |
| TC-19 | SKILL.md に 3 手順が追加 | 実ファイル | `手順3.5`・`手順5.5`・`手順6.5`（診断/実装/テストの対応）が出現 |
| TC-20 | SKILL.md にゲート仕様＋exit code が明記 | 実ファイル | `BLOCKER` と `HIGH` を差し戻し対象／`OK` のみ次段／exit code（0=次段・1=差し戻し）／連続 NG 上限 `2` が出現 |
| TC-21 | SKILL.md に差し戻し導線 | 実ファイル | 「診断」×「停止」/「実装」×「手順5」/「テスト」×「手順5/6」の対応が出現 |
| TC-22 | SKILL.md に fail-safe 再判定・軽微例外・skip | 実ファイル | 「手順5.5」×「実 diff」/「軽微例外」×「振る舞い」/「skip」×「未実施」が出現 |
| TC-23 | **回帰: 既存手順1〜7 の非後退** | SKILL.md | `pytest`・`flake8`・`bandit`・`Jest`・`ESLint`・`npm audit` が全て残存し、手順1（失敗分解）〜手順7（再発防止記録）の骨子が消えていない |
| TC-24 | **回帰の false-green 反証** | SKILL.md を対象に必須キーワードを 1 つ削除した複製 | 複製に対し TC-23 判定ロジックが **NG（非ゼロ）** を返す（正常系で合格するだけの空振りでない） |
| TC-25 | 新規 `docs/fixes/` を作らない | repo | `docs/fixes/` ディレクトリが存在しない・出力パスが `docs/reviews/I###_fix_*` 形式 |

## 決定論ゲート（自動実走）
<!--
  code-review.sh がこの見出し直後の単一 ```bash ブロックを 1 行 1 コマンドで抽出・実走する。
  test_fix_review.sh は決定論（claude -p を呼ばず helper を source するのみ・docker/ネットワーク非依存）なのでここで実走してよい。
-->
```bash
bash scripts/claude/tests/test_fix_review.sh
```

補足（false-green 自己検証の実施タイミング）: 上記 TC-12/TC-13/TC-17/TC-24 は「壊した複製へ注入すると NG を返す」反証を含む。実装未着手の現時点（plan フェーズ）では対象コードが存在しないため未実行。`/implement` で各ファイル生成後、テスト作成時に注入反証まで実走・記録してから green とする（plan-writing-rules「否定・回帰系の false-green 禁止」を実装時に充足）。
