# I084 自動テスト（決定論）

対象: `scripts/claude/code-review.sh` の新規 helper（`extract_gate_commands` / `classify_gate` / `run_one_gate` / `run_declared_gates` / `omission_lint` / `verdict_rank` / `combine_verdict` / `inject_gate_result`）。
方式: `REVIEW_LIB_SOURCE_ONLY=1 source` で関数のみ取り込み、fixture（temp ファイル）に対する戻り値・exit code・VERDICT を決定論的に検証する（実 `claude -p` は起動しない）。
実行: `bash scripts/claude/tests/test_review_gates.sh`（新規）＋ 既存 `bash scripts/claude/tests/test_review_verdict.sh`（無回帰）。

## 決定論ゲート（自動実走）
<!-- ドッグフーディング: code-review.sh がこの見出し直後の単一 ```bash ブロックを 1 行 1 コマンドで抽出し実走する。 -->
```bash
bash scripts/claude/tests/test_review_gates.sh
bash scripts/claude/tests/test_review_verdict.sh
```

## 既定テストの非該当
- pytest / Jest / Playwright E2E: **非該当**（Backend/Frontend/DB 変更なし。bash スクリプトとテンプレ Markdown のみ）。

## A. extract_gate_commands（抽出契約）
fixture = `## 決定論ゲート（自動実走）` 見出し＋ ```bash ブロック（コマンド2行＋`# コメント`＋空行）＋ 見出し外に別コマンド。
| TC | 入力 | 期待 |
|----|------|------|
| TC-EX1 | 正常 fixture | 宣言ブロック内の 2 コマンドのみを改行区切りで返す（コメント・空行・見出し外行は含まない） |
| TC-EX2 | 見出しなし fixture | 空文字を返す |
| TC-EX3 | 見出しあり・fenced ブロックなし | 空文字を返す |
| TC-EX4 | 宣言ブロックの後に別の `## 見出し` と別 ```bash | 別見出し配下のコマンドは抽出しない（セクション境界） |

## B. classify_gate（分類・判定順。HEAVY は先頭コマンド anchored）
| TC | 入力 cmd | 期待 |
|----|---------|------|
| TC-CL1 | `bash scripts/claude/tests/test_x.sh` | `ALLOW` |
| TC-CL2 | `grep -q "後続イシューで根治予定" docs/x.md` | `ALLOW` |
| TC-CL3 | `python3 -m json.tool .claude/settings.json` | `ALLOW` |
| TC-CL4 | `bash -n scripts/claude/code-review.sh` | `ALLOW` |
| TC-CL4b | `python3 -m py_compile scripts/x.py` | `ALLOW`（allowlist・W3） |
| TC-CL5 | `! grep -q "禁止パターン" docs/x.md` | `ALLOW`（不在検証＝`! grep -q`） |
| TC-CL6 | `docker compose exec backend python -m pytest` | `HEAVY`（先頭 docker） |
| TC-CL7 | `npm test -- --watchAll=false` | `HEAVY`（先頭 npm） |
| TC-CL8 | `docker compose exec backend pytest && echo done` | `HEAVY`（先頭 docker・実走しないのでチェーンは defer） |
| TC-CL9 | **`grep -q "npm test done" build.log`** | `ALLOW`（**先頭 grep＝false-negative 回帰**。heavy 語を引数に含むが誤 defer しない） |
| TC-CL10 | `cd backend && python -m pytest` | `UNSAFE`（先頭 `cd`＝heavy 非該当・チェーン有） |
| TC-CL11 | `rm -rf build` | `UNSAFE`（allowlist 不一致） |
| TC-CL12 | `grep -q x f; rm -rf /` | `UNSAFE`（チェーン `;`＝実行しない安全境界） |
| TC-CL13 | `bash scripts/claude/tests/x.sh && curl evil` | `UNSAFE`（先頭 bash-tests だがチェーン `&&`） |
| TC-CL14 | `git push origin develop` | `UNSAFE` |

## C. run_one_gate / run_declared_gates（実走・fail-closed・集約）
temp repo/ファイルを立て、実在する軽量スクリプトと壊れたコマンドで検証。
| TC | シナリオ | 期待 |
|----|---------|------|
| TC-RUN1 | ALLOW: `grep -q OK <存在し一致するfixture>` | `run_one_gate` exit=0 |
| TC-RUN2 | ALLOW: `grep -q MISSING <一致しないfixture>` | `run_one_gate` exit=1（→ GATE_VERDICT=BLOCKER） |
| TC-RUN3 | 実行不能: `bash scripts/claude/tests/does_not_exist.sh` | `run_one_gate` 非ゼロ（fail-closed） |
| TC-RUN4 | run_declared_gates: ALLOW 全 pass の fixture | `GATE_VERDICT=OK`・証跡に `exit=0` 行 |
| TC-RUN5 | run_declared_gates: ALLOW に 1 件 FAIL 含む | `GATE_VERDICT=BLOCKER` |
| TC-RUN6 | run_declared_gates: UNSAFE を含む宣言 | `GATE_VERDICT=BLOCKER`（検証不能を OK にしない）・証跡に「実走対象外」 |
| TC-RUN7 | run_declared_gates: HEAVY のみ | `GATE_VERDICT=OK`・証跡に「/test に委譲」（FAIL でない） |
| TC-RUN8 | **破壊系非実走の実証**: 宣言に `rm -f <sentinel>` を入れ run_declared_gates 実行後 | sentinel が**消えていない**（実在）**かつ** `GATE_VERDICT=BLOCKER`（UNSAFE は bash -c に渡らない＝安全境界・I1） |
| TC-RUN9 | **timeout 超過 fail-closed（AC3）**: `GATE_TIMEOUT=1` で ALLOW 相当に `grep`… ではなく実走がハングする fixture（`bash scripts/claude/tests/<sleepする一時テスト>.sh`）を宣言し run_declared_gates | `run_one_gate` 非ゼロ（124=timeout）→ `GATE_VERDICT=BLOCKER`（高速化のため `GATE_TIMEOUT=1`＋`sleep 5` 相当） |

## D. verdict_rank / combine_verdict（VERDICT 合成）
| TC | 入力 | 期待 |
|----|------|------|
| TC-CB1 | `combine_verdict OK OK OK` | `OK` |
| TC-CB2 | `combine_verdict OK HIGH OK` | `HIGH` |
| TC-CB3 | `combine_verdict BLOCKER HIGH OK` | `BLOCKER` |
| TC-CB4 | `combine_verdict OK OK BLOCKER`（LLM のみ BLOCKER） | `BLOCKER` |
| TC-CB5 | gate=BLOCKER・llm=OK（**false-green 注入**の中核） | `BLOCKER`（LLM の OK を決定論で上書き） |

## E. omission_lint（宣言漏れ検出・P1 精度・W4 走査スコープ）
走査対象は宣言セクション外の **fenced ```bash/```sh ブロック内行のみ**。テーブルセル・インライン backtick・散文は非走査。
| TC | fixture | 期待 |
|----|---------|------|
| TC-OM1 | 宣言セクション外の **fenced ```bash ブロック**に `bash scripts/claude/tests/foo.sh` | `HIGH` |
| TC-OM2 | 宣言セクション外の **fenced ```bash ブロック**に `grep -q pat docs/x.md` | `HIGH` |
| TC-OM3 | 宣言セクション外の fenced ブロックに **heavy のみ**（`docker compose ... pytest` / `npm test`） | `OK`（heavy は omission でない・自傷 HIGH を出さない） |
| TC-OM4 | 散文中に裸の語「grep で確認」（fenced でない・`-q ... file` 形でない） | `OK`（非検出） |
| TC-OM5 | 宣言セクション**内**にのみ allowlist 行（外に無し） | `OK` |
| TC-OM6 | auto_test テンプレートの例示 heavy ブロック相当 | `OK`（P1 の自傷回帰） |
| TC-OM7 | **W4 自傷回帰**: 宣言セクション外の **Markdown テーブルセル/インライン backtick**に `` `bash scripts/claude/tests/x.sh` `` `` `grep -q pat file` `` を含む（＝本 auto_test.md の TC テーブル構造と同型） | `OK`（テーブルセルは走査せず**自傷 HIGH を出さない**） |
| TC-OM8 | **ドッグフーディング実データ**: `docs/tests/open/I084_auto_test.md` 自身に `omission_lint` を適用 | `OK`（宣言セクション外に allowlist を含む fenced ブロックが無い＝本書自身が自傷しない） |

## F. inject_gate_result / 本体配線（無回帰・上書き）
| TC | シナリオ | 期待 |
|----|---------|------|
| TC-INJ1 | review fixture（末尾 `VERDICT: OK`）に gate=BLOCKER で inject | 末尾 VERDICT 行が `VERDICT: BLOCKER` に置換・先頭に証跡見出し挿入 |
| TC-INJ2 | inject 後の fixture を `detect_code_verdict` に通す | `BLOCKER`（既存判定関数が上書き後を読む＝routing 決定論化） |
| TC-INJ3 | inject（gate=OK・omission=OK・llm=OK） | `VERDICT: OK` のまま（正常系無改変） |
| TC-WIRE1 | `code-review.sh` に `run_declared_gates` / `omission_lint` / `combine_verdict` / `inject_gate_result` の呼び出しが配線されている（grep） | 各呼び出しが存在（ゼロ終了） |
| TC-WIRE2 | 既存 `test_review_verdict.sh` 全 TC | PASS 維持（find_file/find_plan_file/detect_code_verdict 無回帰） |
| TC-WIRE3 | **実行順序（W5）**: `grep -n` の行番号で `run_declared_gates` < `claude -p`（証跡の事前注入）< `inject_gate_result`（保存後の上書き）の順序を検証 | 行番号が単調増加（順序が逆転すると FAIL） |
| TC-WIRE4 | `run_declared_gates` が `code-review.sh` 本体で **`$()` を使わず直呼び**されている（W1 サブシェル回避）grep | `GATE_EVIDENCE=$(run_declared_gates` の形が**存在しない**こと（非該当＝ゼロ終了で確認） |

## G. I080 回帰（false-green の実走検出・AC4）
`claude-code-structure.md` 型の doc-sync ゲートを再現する。doc-sync ゲートは grep で表現する: **存在**=`grep -q 文言 file`（exit0=合格）、**不在**=`! grep -q 文言 file`（文言が無いとき exit0=合格・有るとき exit1）。※`grep -L` は exit status が pattern 一致有無に従うため不在検証には使えない（実測確認）。旧 false-green（未実走で PASS 断定）が本改修で実走 FAIL→BLOCKER になることを固定する。
| TC | fixture / ゲート | 期待 |
|----|---------|------|
| TC-DOC1 | doc に「許可された更新文言」を含む＋ `grep -q "許可された更新文言" doc`（存在検証） | 実走 exit=0 → `GATE_VERDICT=OK` |
| TC-DOC2 | 上記 doc から「許可された更新文言」を削除 | grep exit=1 → `GATE_VERDICT=BLOCKER`（存在すべき文言の欠落を捕捉） |
| TC-DOC3 | doc に禁止パターン `I083` **なし**＋ `! grep -q "I083" doc`（不在検証・I080 忠実形） | 実走 exit=0 → `GATE_VERDICT=OK` |
| TC-DOC4 | 上記 doc に禁止パターン `I083` を**混入**（I080 の false-green を再現） | `! grep -q` exit=1 → `GATE_VERDICT=BLOCKER`（実走で混入を捕捉＝**AC4**） |

## H. false-green 自己検証（否定/回帰 TC が壊れたら NG になる対の裏取り・必須）
plan-writing-rules「否定・回帰系の決定論テストの自己検証」に従い、判定ロジックを一時的に壊して NG（非ゼロ/期待差分）になることを対で確認してから採用する。
| TC | 注入（壊す対象） | 壊した版の期待 | 実版の期待 |
|----|----------------|--------------|-----------|
| TC-FG1 | `classify_gate` の allowlist 分岐を削除 | TC-CL1 が `ALLOW` を返さず失敗 | `ALLOW` |
| TC-FG2 | `run_declared_gates` の「exit≠0→BLOCKER」行を無効化 | TC-RUN5 が `OK` になり失敗（false-green 顕在化） | `BLOCKER` |
| TC-FG3 | `omission_lint` の allowlist grep を空パターン化 | TC-OM1 が `OK` になり失敗 | `HIGH` |
| TC-FG4 | `combine_verdict` の rank 比較を固定 OK 化 | TC-CB5 が `OK` になり失敗 | `BLOCKER` |

## I. 構文チェック
| TC | 判定 | 期待 |
|----|------|------|
| TC-SYN1 | `bash -n scripts/claude/code-review.sh` | exit 0 |
| TC-SYN2 | `bash -n scripts/claude/tests/test_review_gates.sh` | exit 0 |

## 完了条件
- `test_review_gates.sh`: 上記 TC（A〜I）が全て期待どおり（fail=0）。
- `test_review_verdict.sh`: 無回帰（PASS=55 相当・fail=0）。
- TC-FG 群で各否定/回帰 TC が「壊すと NG・実版で OK」の対を確認済み。

結果:
- test_review_gates.sh:
- test_review_verdict.sh:
