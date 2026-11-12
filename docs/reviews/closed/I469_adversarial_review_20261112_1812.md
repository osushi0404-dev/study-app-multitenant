# 敵対的レビュー [I469]（別プロセス・2026-11-12 18:12）

- 見た範囲: 2e929ab67d4c805f0b76920e92df5634656efed5...4c45d443ae4c808872e2e1a24ca460f2cf5ad8cb
- 所要時間: 121 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I469.md の「## 必ず確かめる項目」（3 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran  | 確認済み（実験） |
| V3 | 3 | 実験必須 | 実験で確認 | P3-E1=ran  | 確認済み（実験） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 117 秒 | 1 | 0 | $0.1931 | ― | ― | ― |
| 2 | 報告あり | 15 秒 | 0 | 0 | $0.0786 | ― | ― | ― |
| 3 | 報告あり | 35 秒 | 1 | 0 | $0.1838 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; for t in test_guard_must_stop_cases test_i463_guard_optspec test_i469_guard_optspec_leftovers test_i454_guard_env_writes test_i444_guard_gaps test_i200_guard_narrowing test_pretooluse_guard_matrix; do timeout 60 bash scripts/claude/tests/$t.sh >/tmp/p1e1_$t.log 2>&1; echo "$t exit=$?"; done'
~~~
出力の先頭:
~~~
is_error=false
test_guard_must_stop_cases exit=0
test_i463_guard_optspec exit=0
test_i469_guard_optspec_leftovers exit=0
test_i454_guard_env_writes exit=0
test_i444_guard_gaps exit=0
test_i200_guard_narrowing exit=0
test_pretooluse_guard_matrix exit=0
~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 python3 scripts/claude/hooks/pretooluse_guard.py <<< "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"grep -f .env x\"}}"; echo "code=$?"'
~~~
出力の先頭:
~~~
is_error=false
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "\u5916\u90e8\u3078\u306e\u9001\u4fe1\u30fb\u79d8\u5bc6\u60c5\u5831\u306e\u8868\u793a\u3092\u4f34\u3046\u64cd\u4f5c\u3067\u3059\u3002\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044: \u79d8\u5bc6\u60c5\u5831\u30d5\u30a1\u30a4\u30eb\u306e\u8aad\u307f\u51fa\u3057"}}
code=0
~~~

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; for c in "grep --exclude=.env foo x" "python3 -c \"\$X\" | head" "curl x | python3 -m json.tool" "curl x | python3 tool.py"; do j=$(python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c"); echo "$j" | timeout 60 python3 scripts/claude/hooks/pretooluse_guard.py >/tmp/p3e1.out 2>&1; echo "code=$? cmd=$c out=$(head -c 200 /tmp/p3e1.out)"; done'
~~~
出力の先頭:
~~~
is_error=false
code=0 cmd=grep --exclude=.env foo x out=
code=0 cmd=python3 -c "$X" | head out=
code=0 cmd=curl x | python3 -m json.tool out=
code=0 cmd=curl x | python3 tool.py out=[guard] 実行ファイルの中身を確認できませんでした（判定を省略）: tool.py
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I469] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 新規指摘なし | — | P1-E1・P1-E2 |

反証失敗（新規指摘なし）。探索した仮説:
- **V2 の止める側の後退**: 見張りの既存テスト 7 本(止めるべき形の一覧 TC-05、`test_i463`・`test_i469`・`test_i454`・`test_i444`・`test_i200`、判定の行列)をすべて実行した。全件 exit=0 だった(P1-E1)。変更前と同じかより強い判定になっている。
- **`paths` の「`-` で始まらない語」を残している点**: `grep -f .env x` を見張りに直接渡すと `permissionDecision: ask`(秘密情報ファイルの読み出し)で、確認のままだった(P1-E2)。
- **V1**: 決定論の TC-01〜TC-04 は P1-E1 の `test_i469_guard_optspec_leftovers` で exit=0 だった。失敗の注入 FG-01〜FG-04 は、このテストの一部として動く。変更前の見張りに対する失敗は、過去の実験 P2-E1 で実証済み。
- 今回の差分は記録ファイルだけで、見張りのコードには触れていない。

> ITEM: V1 RESULT=experiment EXP=P1-E1
> ITEM: V2 RESULT=experiment EXP=P1-E1,P1-E2
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I469] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説: [今回の差分は記録ファイル（レビュー記録の追加）だけで、テストと見張りのコードは変わっていない。したがって false-green が新たに生まれる場所が無い。前回記録の実験 P2-E1（変更前の見張りで新テストが FAIL）を根拠に、TC-01〜TC-04 が実装の再確認になっていないと判断した。今回の周では実験を実行していない]

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I469] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 新規指摘なし。V3 の 4 形はすべて exit 0 で通る。4 つ目の `curl x \| python3 tool.py` は、スクリプトの中身を確認できず判定を省略したという警告を stderr に出すが、止めてはいない。 | scripts/claude/hooks/pretooluse_guard.py | P3-E1: 4 形とも code=0 |

反証失敗(新規指摘なし)。探索した仮説:
- **通すべき形が止まる**: P3-E1 で、`grep --exclude=.env foo x`・`python3 -c "$X" | head`・`curl x | python3 -m json.tool`・`curl x | python3 tool.py` はすべて code=0 だった。止める対象は増えていない。
- **4 つ目の警告**: `tool.py` が作業ツリーに無く、中身を読めないために警告が出る。判定は通しており、V3 の要件（通るまま）は満たす。Low 相当の観察にとどめ、件数には数えない。
- **TC-07（作業記録の比較）**: 今回は実験していない。差分が記録ファイルの追加だけで、見張りのコードが変わっていないため、前回までの結果から変わらないと判断した。ただし TC-07 の「新しく確認・停止が 1% 以内」は、今回の周の実測では確かめていない。
- **差分の範囲**: 変更は文書だけで、新しい攻め筋は生まれない。

> ITEM: V3 RESULT=experiment EXP=P3-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 4c45d443ae4c808872e2e1a24ca460f2cf5ad8cb
ROUNDS: 1
VERDICT: OK
