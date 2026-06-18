# I066 自動テスト

対象: `scripts/claude/tests/test_review_verdict.sh`（関数 source 方式のユニットテスト）
実行（必ず bash でファイル実行・対話シェルの grep ラッパー回避）:
```bash
bash scripts/claude/tests/test_review_verdict.sh
```

## ベースライン（実装前・分岐元 develop=I065 込み）
```
PASS=44 FAIL=1
FAIL TC-05  expected[BLOCKER] got[OK]   ← I065 移動で fixture パス破損（ステップ1で是正）
```

## 事前検証（修正アプローチの実証・実行済み）
`/tmp/i066_validate.sh` を `bash` 実行し、各 TC が固定する挙動を実装前に実証した。**結果: PASS=8 FAIL=0**。
- #1 旧 `grep -qiE "高リスク判定.*Yes"` は多行 fixture に**空振り（非ゼロ）= バグ確認**（→ TC-27 が固定）
- #1 新 `awk` 範囲検出: 多行 `判定: Yes`→検出 / `判定: No`→非検出 / 別セクションの `判定: Yes`→非検出（→ TC-24/25/26）
- #3 旧追記 2 回で `## レビュー結果` 見出し**2 個（バグ）** / 新冪等追記は見出し**1 個維持・リンク履歴保持**（→ TC-29/30/31）
- fixture 合成 hermetic 化（`bash /tmp/i066_fixture_ideal.sh` で **PASS=2**）: 合成太字 Blocker（VERDICT 行なし）→ `detect_code_verdict=BLOCKER`、旧プレーン grep `^\| Blocker \|` 非マッチ（→ TC-05/TC-12 是正・実ファイル依存撤去）

## テストケース一覧

### ステップ1: TC-05/TC-12 の hermetic 化（実ファイル依存撤去）
`REAL_BOLD_BLOCKER` の実ファイル依存（19 行）を撤去し、合成太字 fixture（`printf '\| **Blocker** \| 説明 \|\n指摘あり\n' > $TMP/c5`）に置換する。外部ファイル移動・削除・編集に不変。
| TC | 内容 | 入力（fixture 内容） | 期待結果 |
|----|------|----------------------|----------|
| TC-05（是正） | 太字 Blocker・VERDICT 行なし → 保険経路で BLOCKER | `\| **Blocker** \| 説明 \|`\n`指摘あり`（合成） | `detect_code_verdict` = `BLOCKER` |
| TC-12（是正） | 旧プレーン grep が太字 Blocker に非マッチ（バグ固定） | 同上（合成 c5） | `grep -qE '^\| Blocker \|'` 非ゼロ（`ck_false` PASS） |

### ステップ2: #1 高リスク保険判定の多行対応（VERDICT 行なし fixture）
| TC | 内容 | 入力（fixture 内容） | 期待結果 |
|----|------|----------------------|----------|
| TC-24 | 多行高リスク Yes を保険検出 | `## 高リスク判定`\n`判定: Yes`\n`該当条件: ...`（VERDICT 無し） | `detect_plan_verdict` = `HIGHRISK` |
| TC-25 | 多行高リスク No は OK | `## 高リスク判定`\n`判定: No` | `detect_plan_verdict` = `OK` |
| TC-26 | アンカリング（誤検出しない） | `## 高リスク判定`\n`判定: No`\n`## その他`\n`判定: Yes` | `detect_plan_verdict` = `OK` |
| TC-27 | バグ固定（旧 grep 非マッチ） | TC-24 と同じ多行 Yes fixture | `grep -qiE "高リスク判定.*Yes"` が非ゼロ（`ck_false` PASS） |

### ステップ3: #3 計画書追記の冪等化（`append_review_link` を source）
| TC | 内容 | 入力 | 期待結果 |
|----|------|------|----------|
| TC-28 | 関数定義の存在 | — | `declare -F append_review_link` 成功（exit 0） |
| TC-29 | 2 回追記で見出し単一 | 空 plan に 2 回 `append_review_link` | `grep -c '^## レビュー結果$'` = `1` |
| TC-30 | リンク履歴保持 | 同上 | `grep -c '^- \['` = `2` |
| TC-31 | 見出し無し plan への初回追記 | `## レビュー結果` を含まない plan に 1 回 | 見出し `1` 個・リンク行 `1` 個が生成 |

### ステップ4: 全回帰・健全性
| TC | 内容 | 期待結果 |
|----|------|----------|
| TC-20（既存） | `bash -n` 構文チェック（code/plan/self） | いずれも成功 |
| 全体 | 全 TC 実行 | **FAIL=0**（既存 TC-01〜TC-23 + 新規 TC-24〜TC-31、TC-05/TC-12 是正含む） |

## 実行結果記録（/test で記入）
- 実行日時: （未実施）
- 結果: PASS=__ / FAIL=__
- 備考:
