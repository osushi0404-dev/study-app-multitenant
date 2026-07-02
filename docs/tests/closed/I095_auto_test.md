# I095 自動テスト: 別 worktree 配下への編集ハードブロック

実行は下記「決定論ゲート（自動実走）」セクションのコマンドで行う（code-review が自動実走する）。個別実行もそのコマンドを参照。

結果:
- backend: 該当なし（ハーネスフックのため・pytest 非該当）
- frontend: 該当なし（Jest 非該当）
- 専用自動テスト `test_pretooluse_worktree_guard.sh`: **27/27 PASS**（2026-07-02）
- 決定論ゲート 8/8 exit=0（回帰 checkout/push・py_compile・json.tool・runbook/matcher grep 含む）

## テストケース一覧

`test_pretooluse_worktree_guard.sh` が temp git repo に linked worktree を生やし、フックへ stdin JSON を投入して exit code を検証する（実書込はしない・判定のみ）。`0`=素通し / `2`=ブロック。

### 判定コア（TC-A1〜A5）
| TC | 入力 | 期待 exit |
|----|------|-----------|
| TC-A1 | Edit file_path = 別worktree配下の絶対パス | 2（block） |
| TC-A2 | Edit file_path = 現worktree配下の絶対パス | 0（allow） |
| TC-A3 | Edit file_path = リポジトリ外（/tmp 配下）の絶対パス | 0（allow） |
| TC-A4 | Edit file_path = 別worktreeと兄弟名で部分一致する別ディレクトリ（`<root>-foo/x`）※decoy | 0（allow・部分一致で誤ブロックしない） |
| TC-A5 | Edit file_path = 現worktree配下の相対パス | 0（allow） |

### 書込ツール網羅（TC-A6〜A10）
| TC | 入力 | 期待 exit |
|----|------|-----------|
| TC-A6 | Write file_path = 別worktree配下 | 2 |
| TC-A7 | MultiEdit file_path = 別worktree配下 | 2 |
| TC-A8 | NotebookEdit notebook_path = 別worktree配下 | 2 |
| TC-A9 | Write file_path = 現worktree配下 | 0 |
| TC-A10 | Edit file_path = 別worktree配下（`realpath` 経由のシンボリックリンク）※decoy | 2（リンク解決後も block） |

### Bash 書込経路（TC-A11〜A15）
| TC | 入力コマンド | 期待 exit |
|----|------|-----------|
| TC-A11 | `echo x > <別wt>/f`（先頭付着形 `>|<別wt>/f`・`>> ` も別行で） | 2 |
| TC-A11b | `echo x>/<別wt>/f`（**語中埋め込み形**・shlex 単一トークン `x>/...`）※W1 | 2 |
| TC-A12 | `tee <別wt>/f` / `tee -a <別wt>/f` | 2 |
| TC-A13 | `cp a.txt <別wt>/`（宛先が別wt） | 2 |
| TC-A14 | `mv a.txt <別wt>/b.txt` | 2 |
| TC-A15 | `sed -i s/x/y/ <別wt>/f` | 2 |

### 読み取り許可・非書込（TC-A16〜A17）
| TC | 入力 | 期待 exit |
|----|------|-----------|
| TC-A16 | `cp <別wt>/src.txt ./dest.txt`（別wt を**読む**・宛先は現wt） | 0（allow） |
| TC-A17 | `cat <別wt>/f` / `grep x <別wt>/f`（読み取り） | 0（allow） |

### fail-safe・エスケープ無し・回帰・false-green（TC-A18〜A22）
| TC | 入力 | 期待 exit |
|----|------|-----------|
| TC-A18 | worktree 列挙失敗を注入した状態で Edit（別/現不問の書込） | 2（fail-safe block） |
| TC-A19 | `DANGER_OK=1` を前置した別wt宛 Bash 書込 | 2（エスケープで解除されない） |
| TC-A20 | 既存回帰: clean checkout・dirty checkout block・force push block 等が従来どおり | 既存期待値維持 |
| TC-A21 | **false-green 注入**: `_cross_worktree` の戻りを常に False 化した複製フックでは別wt宛が素通し(0)、実体では block(2) | 複製=0 / 実体=2 |
| TC-A22 | Bash 書込語を含むが絶対パス宛先を抽出できない（`cd <別wt> && echo x > f`）→ stderr に未カバー注意が出る | 0（block しない）かつ stderr に部分文字列 `絶対パス宛先のみ検査` が出る（`grep -q` で確認）※W2 |
| TC-A23 | 別wt から読み `cp <別wt>/src ./dest`（cd/変数なし）→ **未カバー警告を誤発火しない**（Medium 対応） | 0（block しない）かつ stderr に `絶対パス宛先のみ検査` が**出ない** |

## 決定論ゲート（自動実走）
<!--
  code-review が本見出し直後の単一 bash ブロックを 1 行 1 コマンドで抽出・実走し exit code を VERDICT に注入する。
  許可コマンドのみ・チェーン不可。heavy は /test に委譲。
-->
```bash
bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
bash scripts/claude/tests/test_pretooluse_checkout_guard.sh
bash scripts/claude/tests/test_pretooluse_push_guard.sh
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
python3 -m json.tool .claude/settings.json
grep -q "pretooluse_guard.py" docs/runbooks/worktree.md
grep -q "MultiEdit" .claude/settings.json
grep -q "NotebookEdit" .claude/settings.json
```
<!-- 注: grep パターンに `|`（パイプ）を含めない。code-review ランナーの allowlist が
     チェーン系とみなして fail-closed（未実走→omission-lint HIGH）にするため、MultiEdit /
     NotebookEdit の存在は別々の pipe-free grep で確認する。 -->
