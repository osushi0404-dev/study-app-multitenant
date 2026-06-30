# I083 自動テスト（決定論）

対象: `scripts/claude/hooks/pretooluse_guard.py` の push ガード（欠陥1=動的宛先 ask／欠陥2=force 取りこぼし）。
実行: `bash scripts/claude/tests/test_pretooluse_push_guard.sh`（既存 40 件に追記）。
方式: 実フックへ stdin JSON を投入し **exit code**（block=2 / pass・ask=0）と、ask は **stdout JSON の `"permissionDecision": "ask"`** で判定する（実 push はしない）。

## ハーネス追加（テストスクリプト側）
- 既存 `run`（exit code のみ）に加え、**ask 判定用ヘルパー `cka`** を追加する:
  - `cka "label" "$(runj 'cmd')"` … `runj` は stdout を捕捉し `exit 0 かつ stdout に "permissionDecision": "ask" を含む` なら `ASK`、それ以外は実 exit を返す。`cka` は `ASK` を期待値に取る。
- 現ブランチ依存 TC（protected 宛先・引数なし push）は既存同様 temp git repo（develop / feature/x）を立てて実行する。

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
| TC | コマンド | 期待 |
|---|---|---|
| TC-FP1 | `git push origin feature; echo "use --force later"` | exit 0（ask も block も無し） |
| TC-FP2 | `git push origin feature && echo "--force"` | exit 0 |
| TC-FP3 | `git push --push-option=force origin x` | exit 0 |
| TC-FP4 | `rm -f x && git push origin feature` | exit 0（`rm -f` は rm -rf ではない・force でもない） |

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
壊した版（`rung` で判定行を無効化したフックのコピー）で「素通り」を、実版で「捕捉」を確認する**対**で固定する。
| TC | 注入対象（無効化する行/式） | 壊した版の期待 | 実版の期待 |
|---|---|---|---|
| TC-FG-G | `_push_has_force` を `return False` 化 | `git push -f origin x` → exit 0 | exit 2 |
| TC-FG-H | `_is_force_flag` の短縮クラスタ分岐を削除 | `git push -uf origin x` → exit 0 | exit 2 |
| TC-FG-I | `_push_is_dynamic` を `return False` 化 | `git push origin $(echo develop)`（develop）→ exit 0 | ASK |
| TC-FG-J | `_push_is_dynamic` の構造的ラッパー分岐を削除 | `eval "git push origin develop"`（develop）→ exit 0 | ASK |

> 注: false-green 注入は plan-writing-rules「否定・回帰系の決定論テストの自己検証」に従い、判定行を実際に壊して NG（期待差分）が出ることを確認してから採用する。

## 完了条件
- 上記 TC が全て期待どおり（push guard テスト総数 = 既存 40 ＋ 追加分、fail=0）。
- 既存 `test_pretooluse_checkout_guard.sh`（14 件）無回帰。
