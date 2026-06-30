# I083 自動テスト（決定論）

対象: `scripts/claude/hooks/pretooluse_guard.py` の push ガード（欠陥1=動的宛先 ask／欠陥2=force 取りこぼし）。
実行: `bash scripts/claude/tests/test_pretooluse_push_guard.sh`（既存 40 件に追記）。
方式: 実フックへ stdin JSON を投入し **exit code**（block=2 / pass・ask=0）と、ask は **stdout JSON の `"permissionDecision": "ask"`** で判定する（実 push はしない）。

## ハーネス追加（テストスクリプト側）
既存ヘルパー（流用）: `run`（実フックを叩き exit code のみ返す）／`rung "$guard" 'cmd'`（壊した版フックを叩き exit code を返す・false-green 用）／`ck`（期待値一致判定）。これらは現行 `test_pretooluse_push_guard.sh` に既存。

**新規追加ヘルパー（本イシューで追加）**:
- `runj 'cmd'` … 実フックを叩き **stdout を捕捉**して、`exit 0 かつ stdout に `"permissionDecision": "ask"` を含む`なら文字列 `ASK` を、それ以外は実 exit code（`0`/`2`）を返す。
- `rungj "$guard" 'cmd'` … `runj` の壊した版フック変種（false-green 注入で ask ロジックを裏取りするため。`$1`=guard パス・`$2`=command）。
- これにより `ck` は期待値 `ASK` / `0` / `2` を統一的に比較できる（`cka` 専用関数は設けず `ck` に集約）。

**実装例（既存 `run`/`rung` と並置して test script に追記する）**:
```bash
# stdout を捕捉し ask を判別する変種。code=$? はパイプ末尾(python)の exit を取る。
runj()  { local out code; out=$(json "$1" | python3 "$GUARD" 2>/dev/null); code=$?;
          if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
          then echo "ASK"; else echo "$code"; fi; }
rungj() { local out code; out=$(json "$2" | python3 "$1" 2>/dev/null); code=$?;
          if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
          then echo "ASK"; else echo "$code"; fi; }   # $1=guard, $2=command
```
> 注: `out=$(...)` 直後の `code=$?` で python の exit を捕捉する（bash はパイプ全体の `$?` を末尾コマンドの exit とするため `pipefail` 不要）。grep パターンは json.dumps の `": "` 区切りに `[[:space:]]*` で寛容に一致させる。

> **重要（ask と pass の判別）**: ask（degrade）も pass（無確認通過）も **exit code は 0** で同一。両者の判別は exit code では不可能なため、ask 系 TC（TC-D*・TC-F7・TC-FG-I/J/K）と「ask されないこと」を固定する TC（TC-S*・TC-W*・TC-FP*）は必ず `runj`/`rungj`（stdout JSON 判定）で検証する。block 系（exit 2）と force/protected 系は `run`/`rung`（exit code）で足りる。

- 現ブランチ依存 TC（protected 宛先・引数なし push・動的宛先）は既存同様 temp git repo（develop / feature/x）を立てて実行する。

## テストケース

### A. 欠陥1: 動的宛先 → ask degrade（`not danger_ok`）
| TC | コマンド | 実行ブランチ | 期待 | 検証 |
|---|---|---|---|---|
| TC-D1 | `git push origin $(echo develop)` | develop | **ASK** | exit0＋ask JSON |
| TC-D2 | `git push origin $(git rev-parse --abbrev-ref HEAD)` | develop | **ASK** | exit0＋ask JSON |
| TC-D3 | `D=develop; git push origin $D` | develop | **ASK** | exit0＋ask JSON |
| TC-D4 | `git -c alias.p="push origin develop" p` | develop | **ASK** | exit0＋ask JSON |
| TC-D5 | `eval "git push origin develop"` | develop | **ASK** | exit0＋ask JSON |
| TC-D6 | `sh -c "git push origin develop"` | develop | **ASK** | exit0＋ask JSON |
| TC-D7 | `git push origin $(git rev-parse --abbrev-ref HEAD)` | feature/x | **ASK**（≠ exit2＝誤検知ゼロ） | exit0＋ask JSON |
| TC-D8 | `git push origin ${BR}` | develop | **ASK** | exit0＋ask JSON |
| TC-D9 | `git push origin $VAR && rm -rf x` | feature/x | **exit 2**（rm -rf が先に block・ask で先食いしない） | exit2 |
| TC-D10 | ``git push origin `git rev-parse --abbrev-ref HEAD` `` （バッククォート代入形） | develop | **ASK** | exit0＋ask JSON（メタ文字 `` ` `` を検出） |

### B. 静的安全 push → 無確認通過（無回帰）
| TC | コマンド | 実行ブランチ | 期待 | 検証 |
|---|---|---|---|---|
| TC-S1 | `git push` | feature/x | exit 0（pass・ask 無し） | exit0＋ask JSON 無し |
| TC-S2 | `git push -u origin feature` | feature/x | exit 0 | exit0＋ask JSON 無し |
| TC-S3 | `git push origin develop-fix` | feature/x | exit 0（FP 安全名） | exit0＋ask JSON 無し |

### C. 静的 protected → exit 2 block（無回帰）
| TC | コマンド | 実行ブランチ | 期待 |
|---|---|---|---|
| TC-P1 | `git push origin develop` | feature/x | exit 2 |
| TC-P2 | `git push origin HEAD:main` | feature/x | exit 2 |

### D. 欠陥2/F1: force 取りこぼし → exit 2 block
| TC | コマンド | 期待 |
|---|---|---|
| TC-F1 | `git push -f origin x` | exit 2 |
| TC-F2 | `git push -uf origin x` | exit 2 |
| TC-F3 | `git push --force-with-lease origin x` | exit 2 |
| TC-F4 | `git push --force-if-includes origin x` | exit 2 |
| TC-F5 | `cd foo && git push --force origin x` | exit 2 |
| TC-F6 | `true; git push --force origin x` | exit 2 |

### E. force 誤 block 回帰（現行 `re.match` の潜在 FP を根治）→ 無確認 pass
**検証は `runj` で行い `0` を期待**（ask になっても exit 0 のため `run` では false-green になる。`0`＝ask も block も無しを保証）。
| TC | コマンド | 実行ブランチ | 期待（`runj`） |
|---|---|---|---|
| TC-FP1 | `git push origin feature; echo "use --force later"` | feature/x | `0`（ask も block も無し） |
| TC-FP2 | `git push origin feature && echo "--force"` | feature/x | `0` |
| TC-FP3 | `git push --push-option=force origin x` | feature/x | `0` |
| TC-FP4 | `rm -f x && git push origin feature` | feature/x | `0`（`rm -f` は rm -rf ではない・force でもない） |

### F. ラッパー隠蔽 force → ask（block しない・Q7）
| TC | コマンド | 実行ブランチ | 期待 |
|---|---|---|---|
| TC-F7 | `eval "git push --force origin x"` | feature/x | **ASK** |

### G. ラッパー誤 ask 回帰（構造的検出・branch/remote 名の偶然一致で発火しない・Q8）→ 無確認 pass
| TC | コマンド | 実行ブランチ | 期待 |
|---|---|---|---|
| TC-W1 | `git push origin bash-feature` | feature/x | exit 0（ask 無し） |
| TC-W2 | `git push origin sh-fix` | feature/x | exit 0 |
| TC-W3 | `git push eval-remote feature` | feature/x | exit 0 |
| TC-W4 | `git -c user.name=x push origin feature` | feature/x | exit 0（非 alias の `-c`） |

### H. DANGER_OK escape 維持
| TC | コマンド | 実行ブランチ | 期待 |
|---|---|---|---|
| TC-DOK1 | `DANGER_OK=1 git push origin $(echo develop)` | develop | exit 0（ask も block も無し＝escape） |
| TC-DOK2 | `DANGER_OK=1 git push -f origin x` | feature/x | exit 0 |
| TC-DOK3 | `DANGER_OK=1 eval "git push --force origin x"` | feature/x | exit 0 |

### I. false-green 注入（各判定行が load-bearing であることを対で裏取り）
壊した版（`sed` で判定行/式を無効化したフックのコピー）で「素通り」を、実版で「捕捉」を確認する**対**で固定する。
force/block 系（TC-FG-G/H）は exit code で判別できるため `rung`/`run`。**ask 系（TC-FG-I/J/K）は壊した版＝pass(exit0) と実版＝ask(exit0) が exit code 同一のため、必ず `rungj`/`runj`（stdout JSON）で判別する**（exit code 比較では false-green を見逃す）。
| TC | 注入対象（無効化する行/式） | 壊した版の期待 | 実版の期待 | 判別 |
|---|---|---|---|---|
| TC-FG-G | `_push_has_force` を `return False` 化 | `git push -f origin x` → `0` | `2` | `rung`/`run` |
| TC-FG-H | `_is_force_flag` の短縮クラスタ分岐を削除 | `git push -uf origin x` → `0` | `2` | `rung`/`run` |
| TC-FG-I | `_push_is_dynamic` を `return False` 化 | `git push origin $(echo develop)`（develop）→ `0`（pass・ask 無し） | `ASK` | `rungj`/`runj` |
| TC-FG-J | `_push_is_dynamic` の構造的ラッパー（`eval`/`sh -c`）分岐を削除 | `eval "git push origin develop"`（develop）→ `0` | `ASK` | `rungj`/`runj` |
| TC-FG-K | `_push_is_dynamic` の `git -c alias.` サブ分岐を削除 | `git -c alias.p="push origin develop" p`（develop）→ `0` | `ASK` | `rungj`/`runj` |
| TC-FG-L | `_push_is_dynamic` の `eval` 分岐を削除（TC-F7 裏取り） | `eval "git push --force origin x"`（feature/x）→ `0`（force は `_push_has_force` で捕捉されない＝ask も消える） | `ASK` | `rungj`/`runj` |

> 注: false-green 注入は plan-writing-rules「否定・回帰系の決定論テストの自己検証」に従い、判定行を実際に壊して NG（期待差分）が出ることを確認してから採用する。TC-FG-I/J/K は exit code でなく ask JSON の有無で「壊れたら ask が消える」ことを裏取りする（ask ロジックの load-bearing 性の本質的検証）。

### J. ドキュメント注記の更新（決定論 grep・限界注記クローズ）
`docs/claude-code-structure.md` の限界注記更新を grep で機械判定する（手動テスト No.4 の決定論版）。
| TC | 判定 | 期待 |
|---|---|---|
| TC-DOC1a | `grep -q "後続イシューで根治予定" docs/claude-code-structure.md` | **不在**（旧「未根治」注記が消えている＝非ゼロ終了） |
| TC-DOC1b | `grep -q "対応済み（I083" docs/claude-code-structure.md`（または「ask degrade」更新文言） | **存在**（ゼロ終了） |
| TC-DOC1c | 残余既知限界（`eval "$VAR"` 完全隠蔽が脅威モデル外）の明記が grep で存在 | **存在** |

> TC-DOC1 は plan_I083.md §5 ステップ4・§8 が参照する決定論 TC の実体。手動テスト No.4 と同一対象を機械判定で固定する（false-green 注入: 旧注記を残したダミーで TC-DOC1a が NG になることを確認）。

## 完了条件
- 上記 TC（A〜J）が全て期待どおり（push guard テスト総数 = 既存 40 ＋ I083 追加分、fail=0）。
- 既存 `test_pretooluse_checkout_guard.sh`（14 件）無回帰。
