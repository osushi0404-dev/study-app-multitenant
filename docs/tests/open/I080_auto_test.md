# I080 自動テスト（決定論）

フック単体の exit code 検証＋settings.json/ドキュメントの決定論ファイル検証。
実行: `bash scripts/claude/tests/test_pretooluse_push_guard.sh`（TC-P 群）＋個別コマンド（TC-S/TC-DOC）。

## 前提
- `test_pretooluse_push_guard.sh` は temp git repo を立て、フックへ stdin JSON（`{"tool_name":"Bash","tool_input":{"command":"..."}}`）を投入し exit code を判定する（実 push は行わない）。
- `develop` ブランチ・`feature/x` ブランチの2環境で同じフックを評価する。
- 期待: protected 宛先 push＝exit 2 / 安全 push＝exit 0 / DANGER_OK 前置＝exit 0。

## TC-P（フック exit code・`test_pretooluse_push_guard.sh`）

### develop ブランチ上
| TC | コマンド | 期待 exit | 観点 |
|----|---------|:---:|------|
| TC-P1 | `git push` | 2 | 引数なし push＝現ブランチ(develop)宛先 |
| TC-P2 | `git push origin` | 2 | remote のみ＝現ブランチ宛先 |
| TC-P3 | `git push -u origin` | 2 | upstream 設定でも宛先=現ブランチ |
| TC-P4 | `git push origin develop` | 2 | 明示名 |
| TC-P5 | `git push origin feature` | 0 | 別ブランチ(feature)宛先＝安全 |
| TC-P6 | `DANGER_OK=1 git push origin develop` | 0 | release/hotfix escape |
| TC-P7 | `DANGER_OK=1 git push` | 0 | 引数なしも escape |

### feature/x ブランチ上
| TC | コマンド | 期待 exit | 観点 |
|----|---------|:---:|------|
| TC-P8  | `git push` | 0 | feature の素 push＝安全 |
| TC-P9  | `git push origin` | 0 | 同上 |
| TC-P10 | `git push -u origin feature` | 0 | feature への upstream push |
| TC-P11 | `git push origin develop` | 2 | 明示名 develop |
| TC-P12 | `git push origin main` | 2 | 明示名 main |
| TC-P13 | `git push origin feat:main` | 2 | refspec 宛先 main |
| TC-P14 | `git push origin HEAD:develop` | 2 | refspec 宛先 develop |
| TC-P15 | `git push origin +develop` | 2 | force-shorthand |
| TC-P16 | `git push origin refs/heads/develop` | 2 | 完全修飾 ref |
| TC-P17 | `git push origin HEAD:refs/heads/main` | 2 | 完全修飾 refspec |
| TC-P18 | `git push origin develop-fix` | 0 | **FP 解消**（部分一致でない） |
| TC-P19 | `git push origin main-backup` | 0 | **FP 解消** |
| TC-P20 | `git push origin feat:feat` | 0 | feature への refspec＝安全 |
| TC-P21 | `git push --all` | 2 | 全 ref 一括（protected 含む） |
| TC-P22 | `git push --mirror` | 2 | 同上 |
| TC-P23 | `DANGER_OK=1 git push origin develop` | 0 | escape |
| TC-P24 | `DANGER_OK=1 git push --all` | 0 | escape |
| TC-P25 | `git push --force origin feature` | 2 | force(非 protected)＝既定 block |
| TC-P26 | `DANGER_OK=1 git push --force origin feature` | 0 | force escape |
| TC-P27 | `git -C /tmp push origin develop` | 2 | `git -C <dir>` 形でも push 検出 |
| TC-P28 | `git push --repo=origin develop:main` | 2 | `--repo=` evasion（positional 無し remote） |
| TC-P29 | `git push --repo=origin +develop` | 2 | `--repo=` ＋ force-shorthand evasion |
| TC-P30 | `git push --repo origin develop:main` | 2 | `--repo`（空白形）evasion |
| TC-P31 | `DANGER_OK=1 git push --repo=origin develop:main` | 0 | `--repo` の DANGER_OK escape |
| TC-P32 | `git push --repo=origin feature` | 2 | `--repo` はフラグごと block（vestigial・正当用途無＝許容的 over-block） |
| TC-P33 | `git push origin feat:+refs/heads/main` | 2 | dst 側 `+`（force-shorthand）も `lstrip("+")` で正規化して main を捕捉（code-review Low 対応） |

### 回帰（既存ガード維持）
| TC | コマンド/操作 | 期待 | 観点 |
|----|---------|:---:|------|
| TC-Pregr1 | `git push --force origin x`（既存 G9 相当） | exit 2 | force 回帰維持 |
| TC-Pregr2 | `bash scripts/claude/tests/test_pretooluse_checkout_guard.sh` | pass=14 fail=0 | checkout guard 無回帰 |

### false-green 注入（必須・自己検証）
protected 宛先判定（`_push_protected_target`）と `--all`/`--mirror` 判定は**独立した2つの判定行**のため、**各々**に注入を行い両方の load-bearing を裏取りする（AC「protected 宛先 push・`--all`/`--mirror` で…注入確認」を満たす）。

| TC | 手順 | 期待 | 観点 |
|----|------|:---:|------|
| TC-FALSEGREEN-A | `_push_protected_target` 判定を無効化した複製フック（`sed 's/dest = _push_protected_target(cmd)/dest = None/'`）で TC-P11（`git push origin develop` on feature）を実行 | exit 0（素通り） | protected 判定行を外すと protected が通る＝テストが実体に依存 |
| TC-FALSEGREEN-B | 実体フックで TC-P11 を実行 | exit 2（block） | 実体は block。A との差分で「protected block は判定行に依存」を機械裏取り |
| TC-FALSEGREEN-C | `--all`/`--mirror` 判定の regex を無効化した複製フック（`sed 's/(--all|--mirror)/(--xxall|--xxmirror)/'`）で TC-P21（`git push --all` on feature）を実行 | exit 0（素通り） | `--all`/`--mirror` 判定行を外すと一括 push が通る＝テストが実体に依存 |
| TC-FALSEGREEN-D | 実体フックで TC-P21 を実行 | exit 2（block） | 実体は block。C との差分で「`--all`/`--mirror` block は regex 行に依存」を機械裏取り |
| TC-FALSEGREEN-E | `--repo` 判定の regex を無効化した複製フック（`sed 's/--repo(\\s|=)/--xxrepo(\\s|=)/'`）で TC-P28（`git push --repo=origin develop:main` on feature）を実行 | exit 0（素通り） | `--repo` 判定行を外すと evasion 形が通る＝テストが実体に依存 |
| TC-FALSEGREEN-F | 実体フックで TC-P28 を実行 | exit 2（block） | 実体は block。E との差分で「`--repo` block は regex 行に依存」を機械裏取り |

> A/B は protected 判定行、C/D は `--all`/`--mirror` 判定行、E/F は `--repo` 判定行を**それぞれ独立に**無効化して「複製=素通り(0)・実体=block(2)」を対で確認する（I081 の FALSEGREEN 手法に準拠）。3判定が独立しているため一方の注入では他を裏取りできない（本 TC 群が3判定すべてを担保する）。

## TC-S（settings.json・決定論ファイル検証）
配列の所属（allow/ask/deny）を厳密に区別するため、grep でなく JSON をパースして検証する。各 TC は下記ワンライナーが **exit 0** で合格。

| TC | 検証コマンド | 合格条件 |
|----|------|---------|
| TC-S1 | `python3 -m json.tool .claude/settings.json` | exit 0（有効な JSON） |
| TC-S2 | `python3 -c "import json;a=json.load(open('.claude/settings.json'))['permissions']['allow'];assert 'Bash(git push)' in a and 'Bash(git push *)' in a"` | exit 0（allow に両方存在） |
| TC-S3 | `python3 -c "import json;k=json.load(open('.claude/settings.json'))['permissions']['ask'];assert 'Bash(git push *)' not in k"` | exit 0（ask に不在） |
| TC-S4 | `python3 -c "import json;d=json.load(open('.claude/settings.json'))['permissions']['deny'];assert all(x in d for x in ['Bash(git push origin develop)','Bash(git push origin main)','Bash(git push -u origin develop)','Bash(git push -u origin main)','Bash(git push -u origin HEAD)','Bash(git push * --force*)'])"` | exit 0（deny に保護/force 全エントリ存在） |
| TC-S5 | `python3 -c "import json;a=json.load(open('.claude/settings.json'))['permissions']['allow'];assert 'Bash(git push -u origin *)' not in a"` | exit 0（冗長エントリが削除済み） |

## TC-DOC（claude-code-structure.md 同期）
> **合否方向（convention）**: TC-DOC1・TC-DOC3 は grep が**マッチ無し（非ゼロ終了）で合格**（残存していないこと／含まれないことを検証）。TC-DOC2 は**マッチあり（exit 0）で合格**。方向は各行「合格条件」に明記。
> **コマンド衛生**: 各検証はパイプで束ねず**単体コマンド**で実行する（`feedback_atomic_allowlisted_commands` 準拠）。TC-DOC3 は diff を一旦ファイルへ出し、単一 grep で判定する2ステップに分割。

| TC | 検証コマンド（単体） | 合格条件 |
|----|------|---------|
| TC-DOC1 | `grep -nE 'ask.*git push \*\|git push \*.*ask' docs/claude-code-structure.md` | **マッチ無し（非ゼロ終了）で合格**：旧「ask: `git push *`」記述が残っていない（allow 側に移っている） |
| TC-DOC2 | `grep -nE 'danger-op\|DANGER_OK\|既定.*block\|解除可' docs/claude-code-structure.md` | **マッチあり（exit 0）で合格**：protected push の danger-op 化（既定 block・DANGER_OK 解除可）の文言が存在 |
| TC-DOC3-a | `git diff origin/develop -- docs/claude-code-structure.md > /tmp/i080_doc.diff` | diff をファイルへ出力（exit 0） |
| TC-DOC3-b | `grep -nE '^\+.*I0[0-9]{2}' /tmp/i080_doc.diff` | **マッチ無し（非ゼロ終了）で合格**：追加行（`^+`）にイシュー番号 `I0\d\d` が無い＝一般形（`^\+.*I0[0-9]{2}` を単一 grep で判定・パイプ不要） |

## 実施結果
（/test 実行時に追記）
