# I062 自動テスト

- **関連イシュー**: #128
- **計画書**: docs/plans/open/plan_I062.md
- **対象**: `scripts/claude/code-review.sh` / `scripts/claude/plan-issue-review.sh` / `.claude/review-agents/code-reviewer.md` / `.claude/review-agents/plan-reviewer.md` / `scripts/claude/tests/test_review_verdict.sh`

## 実行方法（重要）
全 TC は回帰テストスクリプトに集約し、**スクリプトファイルとして `bash` 実行**する:

```bash
bash scripts/claude/tests/test_review_verdict.sh
```

> ⚠️ 対話シェルへ直接コマンドを貼り付けないこと。Claude Code の対話シェルでは `grep` が同梱 `ugrep` ラッパーに上書きされており `-E`/`-o` パイプが誤動作する。`bash script.sh` のサブプロセスでは実 GNU grep が使われるため、必ずスクリプトとして実行する。期待終了コード: **0**（全 PASS）。

テストは両スクリプトを `REVIEW_LIB_SOURCE_ONLY=1` で source し、実関数（`find_plan_file` / `detect_code_verdict` / `detect_plan_verdict`）を直接アサートする（実装と乖離しない）。

## 実行結果（2026-06-15）
- `bash scripts/claude/tests/test_review_verdict.sh` → **PASS=45 / FAIL=0（EXIT=0）**（2026-06-16 ステップ5実装後に再実行）。TC-01〜TC-23 を網羅（retro C1 の TC-21・P1 gate の TC-22・P1 do の TC-23 を含む。1 TC が複数アサートに分割されている箇所あり）。
- 実アーティファクト検証: 末尾アンカー適用後も実 OK レビュー（code/plan）は `OK`、太字 Blocker 実ファイルは `BLOCKER` を返すことを確認（正常系の非退行）。
- 補助スモーク: `bash scripts/claude/code-review.sh`（引数なし）→ 41行目 Usage エラー（本体実行＝source ガードが通常実行を阻害しないことを確認）。`plan-issue-review.sh` も同様。`find_file` 定義は各スクリプト 1 箇所のみ（重複なし）。
- **結論: 全自動 TC PASS**。実 `claude -p` 経路の VERDICT 出力は手動テスト No.1〜3 で実アーティファクトを確認済み（`/test` 時に `/code-review`・`/plan-issue-review` を実行し、生成レビューファイルが新契約 `VERDICT: OK` で終端することを確認）。

### テスト隔離方針（リポジトリ汚染防止）
- `find_plan_file` / `detect_*` 用のダミー fixture（`plan_I999.md`・ダミーレビュー等）は **`mktemp -d` の一時ディレクトリ配下に作成**し、`docs/plans/` や `docs/reviews/` を汚さない。`trap 'rm -rf "$TMP"' EXIT`（テストスクリプト内、`DANGER_OK` 不要なスクリプト実行コンテキスト）でクリーンアップする。`find_plan_file` は CWD 相対パスを見るため、fixture 検証時は一時ディレクトリへ `cd` する。
- リポジトリ内の確定パスを使うのは **TC-05（実ファイル回帰）のみ**。該当ファイルは `docs/reviews/I060_code_review_20260612_0045.md`（**フラット配置を実在確認済み**。`closed/` ではない）。

---

## find_plan_file（連番数値順・最大選択）

| TC | 前提（fixture） | 入力 | 期待結果 | 実施者 | 実結果 |
|---:|----------------|------|----------|--------|--------|
| TC-01 | `open/plan_I999.md` のみ | `find_plan_file I999` | `docs/plans/open/plan_I999.md` | Claude | ✅ PASS |
| TC-02 | `open/plan_I999.md` + `open/plan_I999_2.md` | `find_plan_file I999` | `..._2.md`（`_2` > 無印） | Claude | ✅ PASS |
| TC-03 | `_2` `_9` `_10` 併存 | `find_plan_file I999` | `..._10.md`（数値ソート、辞書順でない） | Claude | ✅ PASS |
| TC-04 | `closed/plan_I888.md` + `open/plan_I888_3.md` | `find_plan_file I888` | `open/plan_I888_3.md`（open/closed 横断で最大サフィックス） | Claude | ✅ PASS |
| TC-05f | 該当なし | `find_plan_file I777` | 空文字 `""` | Claude | ✅ PASS |

## 既存 find_file 回帰（issues/tests/reviews を壊さない）

| TC | 前提 | 入力 | 期待結果 | 実施者 | 実結果 |
|---:|------|------|----------|--------|--------|
| TC-06 | `issues/open/I###.md` 実在 | `find_file "issues" "I062.md"` | open パスを返す | Claude | ✅ PASS |
| TC-06b | open になく closed にある | `find_file` | closed パスにフォールバック | Claude | ✅ PASS |
| TC-06c | どちらにも無い | `find_file` | 空文字 `""` | Claude | ✅ PASS |

## detect_code_verdict（一次=VERDICT 行 / 保険=装飾許容 grep）

| TC | 入力ファイル内容 | 期待 verdict | 実施者 | 実結果 |
|---:|------------------|-------------|--------|--------|
| TC-01c | 末尾に `VERDICT: BLOCKER` | `BLOCKER` | Claude | ✅ PASS |
| TC-02c | 末尾に `VERDICT: HIGH` | `HIGH` | Claude | ✅ PASS |
| TC-03c | 末尾に `VERDICT: OK` | `OK` | Claude | ✅ PASS |
| TC-04c | 本文に `| **Blocker** |` だが `VERDICT: OK` | `OK`（一次=VERDICT が正本） | Claude | ✅ PASS |
| TC-05 | **実ファイル** `docs/reviews/I060_code_review_20260612_0045.md`（太字 Blocker・VERDICT 無し） | `BLOCKER`（**バグ回帰：誤 ✅ を出さない**） | Claude | ✅ PASS |
| TC-07 | VERDICT 無し・`| Blocker | x |`（プレーン） | `BLOCKER`（保険・後方互換） | Claude | ✅ PASS |
| TC-08 | VERDICT 無し・`| High | x |` | `HIGH` | Claude | ✅ PASS |
| TC-09 | VERDICT 無し・`| **High** | x |`（太字） | `HIGH` | Claude | ✅ PASS |
| TC-10 | VERDICT 無し・指摘なしのクリーン本文 | `OK` | Claude | ✅ PASS |
| TC-11 | code-review.sh の最終 `case` 連携（`detect_code_verdict`→ ⛔/❌/✅ メッセージ分岐） | BLOCKER→⛔ / HIGH→❌ / OK→✅ | Claude | ✅ PASS |
| TC-12 | 旧 grep `^\| Blocker \|` が太字に非マッチであること（バグの存在確認＝修正前提の固定化） | 非マッチ（exit 1） | Claude | ✅ PASS |

## detect_plan_verdict（一次=VERDICT 行 / 保険=既存プレーン判定）

| TC | 入力ファイル内容 | 期待 verdict | 実施者 | 実結果 |
|---:|------------------|-------------|--------|--------|
| TC-13 | 末尾に `VERDICT: BLOCKER` | `BLOCKER` | Claude | ✅ PASS |
| TC-14 | 末尾に `VERDICT: HIGHRISK` | `HIGHRISK` | Claude | ✅ PASS |
| TC-15 | 末尾に `VERDICT: OK` | `OK` | Claude | ✅ PASS |
| TC-16 | VERDICT 無し・`## 判定: 差し戻し（Blocker 2件）` | `BLOCKER`（保険・後方互換） | Claude | ✅ PASS |
| TC-17 | VERDICT 無し・`## 判定: ✅ 完了`・指摘なし | `OK` | Claude | ✅ PASS |

## エージェント定義の契約・観点

| TC | 対象 | 期待 | 実施者 | 実結果 |
|---:|------|------|--------|--------|
| TC-18a | `code-reviewer.md` | `VERDICT: BLOCKER` / `HIGH` / `OK` の契約記載が存在 | Claude | ✅ PASS |
| TC-18b | `plan-reviewer.md` | `VERDICT: BLOCKER` / `HIGHRISK` / `OK` の契約記載が存在 | Claude | ✅ PASS |
| TC-18c | `code-reviewer.md` / `plan-reviewer.md` | P1 gate 観点（「消費箇所」「取りこぼし」相当の文言）が両ファイルに存在 | Claude | ✅ PASS |

## 構文・静的チェック

| TC | 対象 | 期待 | 実施者 | 実結果 |
|---:|------|------|--------|--------|
| TC-19 | `code-review.sh` / `plan-issue-review.sh` を `REVIEW_LIB_SOURCE_ONLY=1` で source | 本体（CI 待機・claude -p）を実行せず関数のみ定義される | Claude | ✅ PASS |
| TC-20 | `bash -n` 構文チェック（両スクリプト＋テストスクリプト） | 構文エラーなし（exit 0） | Claude | ✅ PASS |

## retro 由来（C1 堅牢化・P1 予防処置）※ステップ5 実装後に検証

| TC | 対象 | 期待 | 実施者 | 実結果 |
|---:|------|------|--------|--------|
| TC-21a | `detect_code_verdict`：末尾に `VERDICT: HIGHRISK`（plan用値が混入）かつ Blocker/High 表記なし | `OK`（`HIGH` に部分一致せず保険もヒットせず） | Claude | ✅ PASS |
| TC-21b | `detect_plan_verdict`：末尾に `VERDICT: HIGH`（code用値が混入）かつ差し戻し/高リスク表記なし | `OK`（`HIGHRISK` に部分一致しない） | Claude | ✅ PASS |
| TC-21c | `detect_code_verdict`：正常な `VERDICT: OK`（末尾アンカー後も正常系が壊れない） | `OK` | Claude | ✅ PASS |
| TC-22 | `code-reviewer.md` | テスト妥当性観点に「シェル…決定論」相当の文言が存在（gate層） | Claude | ✅ PASS |
| TC-23 | `docs/runbooks/common-commands.md` | シェルロジック検証の実行コンテキスト注意（`bash` 実行 / grep ラッパー）が記載（do層） | Claude | ✅ PASS |

---

## 実装前プロトタイプ検証（参考・調査フェーズで実測済み）
> 実装関数ではなく設計プロトタイプに対する事前検証。実装後は上記 TC で本関数を再検証する。

- find_plan_file プロトタイプ: TC-01〜TC-05f 相当 5 ケース **5/5 PASS**（2026-06-15、`/usr/bin/grep` 不使用・bash のみ）
- verdict 検出プロトタイプ: code/plan 両系統・太字回帰含む 14 ケース **14/14 PASS**（2026-06-15、`/usr/bin/grep` 使用）
- バグ再現: 旧 grep `^\| Blocker \|` が `I060_code_review_20260612_0045.md` に**非マッチ（exit 1）**を実測（TC-12 の根拠）
- source ガード: 直接実行で本体実行・source 時は本体スキップ＋関数利用可を実測
