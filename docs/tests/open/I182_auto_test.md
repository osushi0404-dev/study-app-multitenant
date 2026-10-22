# I182 自動テスト: 「GitHub から復旧できる」前提が成り立たない操作を防ぐ

実行コマンド: `bash scripts/claude/tests/test_i182_corpus_base.sh` / `bash scripts/claude/tests/test_i182_guard_failsafe.sh` / `bash scripts/claude/tests/test_i182_secret_gates.sh` / `bash scripts/claude/tests/test_settings_permissions.sh` / `bash scripts/claude/tests/test_i182_docs.sh` ＋ 既存の見張りテスト（R1〜R5）

アプリ（backend / frontend）のコード変更は無いため pytest・Jest・E2E は対象外。すべて、見張りに stdin JSON を渡して exit code／`"permissionDecision": "ask"` を見るか、一時 git リポジトリ・複製ファイル・JSON／YAML の読み取りで動く決定論テスト。各スクリプトは全 TC 合格で exit 0、1 つでも不合格なら非ゼロで終わる（合否は exit code）。

表の「期待」: `0`＝素通し（exit 0・ask なし）／`2`＝停止（exit 2）／`ASK`＝確認（exit 0・ask あり）。

結果:
- backend: 対象外（コード変更なし）
- frontend: 対象外（コード変更なし）
- 計画時（実装前・2026-10-22）: 下記「ベースライン」
- 実装時: （/implement で記入）
- 実装後: （/test で記入）

## ベースライン（実装前・2026-10-22）
| テスト | 結果 |
|-------|------|
| `test_guard_bash_oracle.sh` | cases=4560・見逃し=0・余計な停止=0 |
| `test_pretooluse_guard_matrix.sh` | pass=301 fail=0 |
| `test_settings_permissions.sh` | pass=12 fail=0 |
| `test_pretooluse_push_guard.sh` | pass=185 fail=0 |
| `test_guard_corpus_diff.sh` | FAIL（99 件・マージコミットの誤不合格＝B 群で直す対象） |

## テストケース

### B. 記録突き合わせの比べる相手（新規 `scripts/claude/tests/test_i182_corpus_base.sh`）
テスト環境: 一時 git リポジトリに `scripts/claude/hooks/pretooluse_guard.py`（中身は 1 行のダミー）を置く。`c0`（v0）→ ブランチ `develop` で `c2`（別の行を追加＝v2）、ブランチ `feature` で `c1`（v1）。`refs/remotes/origin/develop` を `c2` に向ける。`feature` に `develop` をマージ（`M`）。`guard_corpus_diff.py` の `base_rev()` を、その一時リポジトリを作業ディレクトリにして import して呼ぶ。

| TC | 内容 | 期待 |
|----|------|------|
| B1 | `feature`（develop を取り込んだ `M` が見張りの最終変更）で `base_rev()` | `c2`（develop との分かれた点）を返す（**再発防止**） |
| B2 | `M` を作る前の `feature`（`c1` のみ）で `base_rev()` | `c0`（分かれた点）を返す |
| B3 | `develop` に `feature` をマージした `M2`（HEAD＝`origin/develop`）で `base_rev()` | `M2^1`（その PR の取り込み前）を返す |
| B4 | `origin/develop` が無いリポジトリの `feature`（`c1`）で `base_rev()` | `c1^1` を返す（今までどおり） |
| FG-B1 | 失敗注入: B1 と同じ状態で、旧ロジック（`git log -1 --format=%H -- <guard>` の直前）の結果 | `c1`（≠ B1 の期待＝この状態が誤不合格を再現していることの証明） |

### F. 見張りの失敗を確認に倒す（新規 `scripts/claude/tests/test_i182_guard_failsafe.sh`）
テスト環境: 見張りを一時ディレクトリへ複製し、複製だけを書き換えて注入する（本物は変えない）。

| TC | 注入（複製のみ） | 入力 | 期待 |
|----|----------------|------|------|
| F1 | `main()` の先頭に `raise RuntimeError("i182")` | Bash `ls` | `ASK`・理由に `RuntimeError` があり、注入したメッセージ `i182` は無い（例外のメッセージを出さない） |
| ~~F2~~ | （計画変更記録 1 で削除: 時間の上限は自作の `SIGALRM` をやめ、公式の `timeout: 20`＋`onFailure: "block"` にした。設定は S13、停止する挙動は手動 M6 で確かめる） | — | — |
| F3 | `main()` の先頭に `bytearray(1024 ** 3)`（1GB） | Bash `ls` | `ASK`・理由に「メモリの上限」 |
| F4 | `_edit_path()` の先頭に `raise ValueError("i182")` | Edit `docs/x.md` | `ASK`・理由に `ValueError` |
| F5 | `_danger_reasons()` の先頭に `raise KeyError("i182")`（今まで包まれていなかった判定） | Bash `ls` | `ASK` |
| F6 | 注入なし（本物） | Bash `ls` → `0`／`git push origin develop` → `2`／Edit `docs/x.md` → `0` | 括弧内のとおり（ふだんの判定は変わらない） |
| FG-F1 | 失敗注入: F1 の注入に加え、複製の `if __name__ == "__main__":` の中を `main()` だけにする（包みなし＝修正前の作り） | Bash `ls` | exit 1（ASK でも 2 でもない＝F1 が包みの欠落を捕まえることの証明） |

### N・D・E・C. 復旧できない操作の規則と CI の検査（新規 `scripts/claude/tests/test_i182_secret_gates.sh`）
テスト環境: リポジトリの最上位を作業ディレクトリにして、本物の見張りに入力を渡す（コマンドは実行しない）。

**N. `--no-verify` の停止**
| TC | 入力（Bash） | 期待 |
|----|------|------|
| N1 | `git commit --no-verify -m x` | 2 |
| N2 | `git commit -n -m x` | 2 |
| N3 | `git commit -anm x` | 2 |
| N4 | `git commit -m -n` | 0（`-n` は `-m` の値） |
| N5 | `git commit -mn` | 0（`n` は `-m` の値） |
| N6 | `git push --no-verify origin feature/x` | 2 |
| N7 | `DANGER_OK=1 git commit --no-verify -m x` | ASK |
| N8 | `git commit -m "fix -n option"` | 0 |
| N9 | `git push -n origin feature/x` | 0（`-n` は push の `--dry-run`） |
| N10 | `git commit -a -n -m x` | 2（分けて書いた形。プランレビュー 20261022_2231 Warning 1） |

**D. リモートブランチの削除の確認**
| TC | 入力（Bash） | 期待 |
|----|------|------|
| D1 | `git push origin --delete feature/x` | ASK |
| D2 | `git push -d origin feature/x` | ASK |
| D3 | `git push origin :feature/x` | ASK |
| D4 | `git push --prune origin feature/x` | ASK |
| D5 | `git push origin :develop` | 2（保護ブランチは停止のまま） |
| D6 | `git push origin feature/x` | 0 |
| D7 | `bash -c "git push origin --delete feature/x"` | ASK（入れ子のシェルでも同じ） |

**E. ワークフロー・秘密情報の検査設定・高リスクファイルの Edit/Write の確認**（計画変更記録 1 で、見張りではなく `.claude/settings.json` の `ask`〔公式の権限ルール〕で行う形に置き換えた。旧 E1〜E6 と FG-E1 は削除し、設定の中身を S14・S15 で、効き目を E7 と手動 M3 で確かめる）

| TC | 内容 | 期待 |
|----|------|------|
| E7 | 見張りに Edit/Write の入力（`.github/workflows/ci.yml`・`.pre-commit-config.yaml`・`backend/requirements.txt`・`docs/x.md`）を渡す | どれも 0（見張りは別ワークツリーへの書き込みの停止だけを行い、編集の確認は settings.json の `ask` に任せる＝二重に判定しない） |

**C. CI の秘密情報の検査が残っていること・ワークフローの権限**（PyYAML で読む。`on` は YAML 1.1 で `True` に読まれるので両方を見る）
| C1 | `.github/workflows/ci.yml` の `name: Backend Lint & Security` のジョブに `uses: pre-commit/action@…` のステップがあり、その `env.SKIP`（カンマ区切り）に `detect-secrets` が無い | exit 0 |
| C2 | `.pre-commit-config.yaml` に `id: detect-secrets` のフックがあり、`args` に `--baseline` と `.secrets.baseline` がある | exit 0 |
| C3 | `ci.yml` の `on.pull_request.branches` に `develop` がある | exit 0 |
| C4 | `.github/workflows/ci.yml` と `.github/workflows/e2e.yml` の最上位の `permissions` が `{"contents": "read"}` だけ（ジョブ単位で `permissions` を広げていない＝どのジョブにも `permissions` が無いか、あっても `read`／`none` だけ） | exit 0 |
| FG-C4 | 失敗注入: e2e.yml の複製から最上位の `permissions` を消す／ci.yml の複製の 1 ジョブに `permissions: {contents: write}` を足す → C4 の判定 | どちらも非ゼロ |
| FG-C1 | 失敗注入: ci.yml の複製で `SKIP: eslint,detect-secrets` にする → C1 の判定 | 非ゼロ |
| FG-C2 | 失敗注入: .pre-commit-config.yaml の複製から detect-secrets の repo を消す → C2 の判定 | 非ゼロ |
| FG-C3 | 失敗注入: ci.yml の複製から pre-commit/action のステップを消す → C1 の判定 | 非ゼロ |
**FG-N1・FG-D1（スクリプト内で毎回確かめる）**: 見張りを一時ディレクトリへ複製し、複製だけで新しい規則を外す（`_commit_no_verify(args)` の呼び出しを `False` に・`"--no-verify" in args` を `False` に・`_push_deletes(args)` の呼び出しを `False` に）。置き換えがそれぞれ 1 か所以上で起きたことを確かめ（起きなければその FG 自体を不合格にする）、複製に N1・N2・N3・N6・N10（FG-N1）・D1〜D4・D7（FG-D1）を当てて、**すべて期待と違う結果（0）になる**ことを確かめる＝これらの TC が規則の欠落を捕まえることの証明（プランレビュー 20261022_2231 Warning 2 で、1 回だけの記録から変更）。
### S. 確認待ちの削減（`scripts/claude/tests/test_settings_permissions.sh` を更新）
| S1 | 実体の settings.json: `ask` が `Bash(git rebase *)`・`Bash(psql *)` の 2 つだけ・`Bash(rm *)`・`Bash(mv *)`・`Bash(cp *)`・`Bash(chmod *)`・`Bash(chown *)` が allow にあり ask に無い・既存の条件（deny・フック登録・広すぎる allow なし 等） | exit 0 |
| S2 | 失敗注入: `Bash(rm *)` を ask に戻す | 不合格（1） |
| S2a | 失敗注入: `Bash(psql *)` を ask から外す | 不合格（1） |
| S2b | 失敗注入: `Bash(chmod *)` を allow から外す（どちらにも無い＝既定の確認が出る） | 不合格（1） |
| S3〜S12 | 既存の注入（exec の ask を戻す・Write(...)・.env の deny・Bash(*)・bypass・フック登録の削除 等） | 不合格（1）（既存どおり） |
| S13 | 実体の settings.json: 見張り（`pretooluse_guard.py`）を呼ぶ PreToolUse フック 3 つ（Edit 系・Bash・MCP）すべてに `"timeout": 20` と `"onFailure": "block"` がある。失敗注入: どれか 1 つの `onFailure` を消す／`timeout` を 600 にする | 実体は合格（0）・注入はどちらも不合格（1）（計画変更記録 1） |
| S14 | 実体の settings.json の `ask` に、4-3(c) の `Edit(...)` 14 行（`Edit(.github/workflows/**)`・`Edit(.pre-commit-config.yaml)`・`Edit(.secrets.baseline)`・Dockerfile 4 つ・`frontend/nginx.conf`・`backend/requirements*.txt`・`backend/pyproject.toml`・`frontend/package.json`・`frontend/package-lock.json`・`**/migrations/*.py`・`backend/init-db.sql`）がすべてある。失敗注入: `Edit(.github/workflows/**)` を消す | 実体は合格（0）・注入は不合格（1） |
| S15 | `ask`・`deny` に `Write(`・`NotebookEdit(`・`MultiEdit(` で始まる行が無い（公式は `Edit(...)` だけを見るため）。失敗注入: `ask` に `Write(.github/workflows/**)` を足す | 実体は合格（0）・注入は不合格（1） |
### DOC. 文書（新規 `scripts/claude/tests/test_i182_docs.sh`）
| DOC1 | `docs/runbooks/danger-ops.md` に見出し `## GitHub から復旧できる範囲（I182）` があり、その節に `秘密情報`・`.github/workflows/`・`リモートブランチの削除`・`イシュー・PR への書き込み` がある | exit 0 |
| DOC2 | `danger-ops.md` に見出し `## 秘密情報を push してしまったとき（I182）` があり、その節に `無効化`・`push protection` がある | exit 0 |
| DOC3 | `danger-ops.md` の「見張り（pretooluse_guard.py）の扱い」の節に `--no-verify`・`20 秒`・`512MB` がある | exit 0 |
| DOC4 | `docs/runbooks/review-rules.md` に見出し `## GitHub から復旧できない変更のレビュー観点（I182）` があり、その節に `pull_request_target`・`.secrets.baseline` がある | exit 0 |
| DOC5 | `docs/runbooks/worktree.md` に `GitHub から復旧できる範囲` がある | exit 0 |
| DOC6 | DOC1〜DOC4 の新しい節の中でバッククォートで書いたパス（`/` を含むもの。`<…>`・`*`・空白を含むもの・gitignore 済みのもの〔`backend/.env` 等〕は除く。実装時に、`/` を含まないファイル名だけの言及〔`ci.yml` 等〕は対象外に変更）が、すべてリポジトリに実在する（`test -e`） | exit 0 |
| FG-DOC1 | 失敗注入: danger-ops.md の複製から見出し `## GitHub から復旧できる範囲（I182）` を消す → DOC1 の判定 | 非ゼロ |
| FG-DOC2 | 失敗注入: danger-ops.md の複製の新しい節に `` `docs/runbooks/no_such_file.md` `` を足す → DOC6 の判定 | 非ゼロ |
### R. 既存の見張りのテスト（回帰）
| R1 | `bash scripts/claude/tests/test_guard_bash_oracle.sh` | 見逃し=0・余計な停止=0（exit 0） |
| R2 | `bash scripts/claude/tests/test_pretooluse_guard_matrix.sh`（OPS に 3 行追加後） | pass=391 fail=0（13 操作 × 30 + 偽合格の防止 1。exit 0） |
| R3 | `bash scripts/claude/tests/test_guard_corpus_diff.sh` | `OK:`（新しく確認・停止が記録の 1% 以下・異常終了 0 件。exit 0）。新しく停止・確認になったコマンドの一覧を実装時に記録し、意図どおり（`--no-verify`・リモートブランチの削除）かを確かめる |
| R4 | `bash scripts/claude/tests/test_pretooluse_push_guard.sh` | pass=185 fail=0（exit 0） |
| R5 | `test_pretooluse_checkout_guard.sh`・`test_pretooluse_container_guard.sh`・`test_pretooluse_gh_pr_guard.sh`・`test_pretooluse_worktree_guard.sh` | すべて fail=0（exit 0） |
| R7 | ステップ 4 の push の後、`gh pr checks 308 --required` | 必須チェック 5 件がすべて `pass`（exit 0）。`permissions: contents: read` で CI が壊れていない |
| R6 | `python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py scripts/claude/tests/guard_corpus_diff.py`・`python3 -m json.tool .claude/settings.json` | exit 0 |
## 計画時の自己検証
- B・F・N・D・E・C・S・DOC のスクリプトは実装ステップで作る（計画時点では対象の実装が無いので実行できない）。各 FG（失敗注入）は、スクリプトの中で注入した複製に当てて非ゼロになることを毎回確かめる形にしてある（正常系だけで合格する false-green を防ぐ）。
- 計画時に実行できたものはベースライン（上表）とスパイク（計画書「調査結果」）。
