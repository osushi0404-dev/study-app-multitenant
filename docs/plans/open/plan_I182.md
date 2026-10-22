# I182 計画書: 「GitHub から復旧できる」前提が成り立たない操作を防ぐ（秘密情報の push など）

## 基本情報
- **計画書ID**: plan_I182
- **関連イシュー**: #307
- **Draft PR**: #308
- **作成根拠資料**: docs/issues/open/I182.md（起点イシュー・設計確認メモ＝grill-me 2026-10-22）
- **実装後評価**: docs/reviews/open/I182_review.md
- **作成日**: 2026-10-22

## 1. 背景/目的
- **背景**: I179・I174・I181 では「develop/main は GitHub 側で保護され、Claude がローカルを壊しても GitHub から復旧できる」を前提に、手元の見張りとレビューを軽くした。棚卸しで、この前提が成り立たない操作（公開リポジトリへの秘密情報の push・PR を出した時点で secrets 付きで動くワークフローの書き換え など）があると分かった。
- **目的**:
  1. 「GitHub から復旧できない」操作を一覧にして、それぞれを止める・確認にする・対策しない理由を記録する。
  2. 見張りの失敗（例外・時間切れ・メモリ不足）を素通しにしない。
  3. 復旧できる範囲（ローカルのファイル操作）は確認待ちを減らす。
  4. 前提（復旧できる範囲）を手順書に書き、関連する記述をそろえる。

## 2. 受け入れ条件
イシュー `## 受け入れ条件` のとおり（本計画の「計画時の変更 1」で CI の項目を書き換える。下の 4-0 参照）。

## 調査結果

### 環境前提確認（2026-10-22）
| 項目 | 結果 |
|------|------|
| Python | 3.12.3（`signal.SIGALRM`・`resource.RLIMIT_DATA` が使える Linux） |
| git / gh | git 2.43.0・gh 2.88.1（認証済み） |
| detect-secrets / pre-commit | 1.5.0（`/home/tacic/.local/bin/`）・pre-commit あり。このワークツリーの pre-commit フックは有効（コミット時に `Detect secrets ... Passed` が出る） |
| PyYAML | 6.0.1（テストで ci.yml を読むのに使う） |
| GitHub 権限 | bot は `repos/.../branches/develop/protection` が 404・`actions/permissions` が 403（管理権限なし）。`security_and_analysis` も null（読めない）→ push protection の有効化と確認はユーザーの UI 操作 |

### 原因の概要
「GitHub が最後の守り」は、「GitHub 上のものは bot がマージできないので壊れない」という意味では正しい。しかし公開リポジトリでは **push した時点で中身が公開される**こと、**PR を出した時点で PR 側のワークフローが secrets 付きで動く**ことが抜けていた。また、見張りの一部の判定は失敗すると素通りする作りのままだった。

### 詳細な原因分析
| 問題 | 発生箇所（具体） | 技術的な原因 |
|------|-----------------|-------------|
| 秘密情報の push を飛ばせる | `pretooluse_guard.py` の `_cmd_danger`（2069 行目〜）に `git commit` の判定が無い | 手元の守りは pre-commit の detect-secrets だけで、`git commit --no-verify`／`-n` で飛ばせる |
| ワークフローの書き換えで secrets に触れる | `.github/workflows/ci.yml`・`e2e.yml` の `on: pull_request: branches: [develop, main]`、`e2e.yml` の `${{ secrets.E2E_TEST_PASSWORD }}` | 同じリポジトリのブランチからの PR では、PR 側（head）のワークフローが secrets 付きで動く（GitHub の仕様）。bot は feature ブランチへの push と PR の作成ができる |
| リモートブランチの削除が素通り | `_cmd_danger` の push 判定（2111〜2117 行目）は保護ブランチ宛て・強制 push だけ | `git push --delete`・`:<ブランチ>`・`--prune` の判定が無い |
| 見張りの失敗で素通り | `main()`（3414 行目〜）は `_analyze`（3448 行目）と `_safety_net`（3506 行目）だけ try で包む | `_danger_reasons`・`_bash_write_targets`・`_guard_gh_pr_targets`・Edit/Write・MCP の分岐の例外、時間切れ・メモリ不足は exit 0/2 以外で終わる＝Claude Code は止めない |
| 記録突き合わせの誤不合格 | `guard_corpus_diff.py` 100〜107 行目 | 「見張りを最後に変えたコミット」がマージコミット（develop の取り込み）だと、第 1 親＝取り込み前と比べ、取り込んだ他の変更を「新しい確認・停止」と数える |
| 確認待ちが多い | `.claude/settings.json` の `ask`: `Bash(rm *)`・`Bash(mv *)`・`Bash(cp *)`・`Bash(chmod *)`・`Bash(chown *)` | ローカルだけで直せる操作まで一律に確認していた。`rm -rf` は見張りが別に止めている |

### 計画時に分かったこと（イシューとの差分）
- **CI はすでに秘密情報を検査している**（イシュー「現状の問題 2」の「CI にも秘密情報の検査が無い」は誤り）: `ci.yml` の `Backend Lint & Security` ジョブの `pre-commit/action@v3.0.1`（`SKIP: eslint`）が `pre-commit run --all-files` を実行し、detect-secrets も全ファイルに走る。実際の CI ログ（run 39643726812・2026-10-21）に `Detect secrets....Passed` がある。このジョブは `docs/runbooks/branch-protection-setup.md` §2 で develop/main の必須チェック 5 件の 1 つとして登録する決まり。→ **CI に新しいジョブは足さない**。代わりに「この検査が外されていないこと」を決定論テストで守る（4-4・TC C1〜C3）。必須チェックに入っていることはユーザーに画面で確かめてもらう（M2）。
- **detect-secrets の実走結果**: 作業ツリー全体の `detect-secrets scan`（`package-lock.json` 除外）で 22 件。baseline（12 件）に無い 10 件はすべて `.secrets.baseline` 自身への検出（pre-commit のフックは baseline を対象外にする）＝新しい秘密情報は 0 件。
- **メモリ上限のスパイク（成立／不成立）**:
  - `RLIMIT_AS` 512MB: **不成立**。見張りが呼ぶ `gh` が `fatal error: failed to reserve page summary memory` で落ちる（Go は起動時に大きな仮想アドレスを予約する）。
  - `RLIMIT_DATA` 512MB: **成立**。`git status`・`gh --version`・`gh pr view 308`・`docker compose ps` はすべて rc=0、Python で 700MB を確保すると `MemoryError`。→ `RLIMIT_DATA` を使う。
- **時間上限のスパイク（成立）**: `SIGALRM` で `BaseException` の派生例外を投げると、`subprocess.run` の途中でも 2.0 秒で打ち切られ、途中の `except Exception` に飲まれず最上位で捕まる。
- **上限値の根拠**: 過去の作業コマンド 2,939 件（`~/.cache/claude-guard-corpus/wt-harness.json`）を 12 並列で見張りに流した所要時間は、中央値 0.09 秒・99% 0.74 秒・最大 1.59 秒（5 秒超 0 件）。長いコマンド上位 200 件の最大メモリは 41MB（git の子プロセスを含む）。→ 20 秒・512MB はどちらも 10 倍以上の余裕があり、ふだんのコマンドで上限に当たらない。
- **記録突き合わせの誤不合格の再現**: このブランチ（develop の取り込みマージ `ac236d6` が見張りの最終変更）で `bash scripts/claude/tests/test_guard_corpus_diff.sh` → `FAIL: 新しく確認・停止になったものが 99 件`。

### ベースライン（実装前・2026-10-22）
| テスト | 結果 |
|-------|------|
| `test_guard_bash_oracle.sh` | cases=4560・見逃し=0・余計な停止=0 |
| `test_pretooluse_guard_matrix.sh` | pass=301 fail=0 |
| `test_settings_permissions.sh` | pass=12 fail=0 |
| `test_pretooluse_push_guard.sh` | pass=185 fail=0 |
| `test_guard_corpus_diff.sh` | FAIL（99 件・上の誤不合格。4-1 で直す） |

アプリ（backend / frontend）のコードは変えないので、pytest・Jest・E2E は対象外。

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.claude/settings.json`（ask の整理）・`.github/workflows/ci.yml`・`.github/workflows/e2e.yml`（最上位に `permissions: contents: read` を足すだけ・4-9。ジョブの中身は変えない）。GitHub の設定（push protection の有効化・必須チェックの確認）はユーザーの UI 操作
- Harness: `scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/tests/`（既存 2 本の更新・新規 3 本）・`scripts/claude/tests/guard_corpus_diff.py`・`docs/runbooks/danger-ops.md`・`docs/runbooks/review-rules.md`・`docs/runbooks/worktree.md`・`docs/issues/open/I181.md`（ローカル・未コミットのまま）

## 4. 変更点一覧

### 修正アプローチ
GitHub から復旧できない操作だけを、単純で安い規則で止める・確認にする。見張りは最上位で全体を包み、失敗・時間切れ・メモリ超過をすべて「確認」に倒す。ローカルで直せるファイル操作の確認は外す。結論を `danger-ops.md` に表でまとめ、他の文書はそこを参照する。

### 4-0. 「GitHub から復旧できない」操作の一覧と対策（受け入れ条件 1）
| 操作 | なぜ復旧できないか | 対策 |
|------|-------------------|------|
| 秘密情報を含むコミットの push | 公開リポジトリなので、push した時点で全世界に公開される。消しても複製・キャッシュが残る | ① push protection（GitHub が push を拒否。ユーザーが有効化）② 見張りが `git commit --no-verify`／`-n`・`git push --no-verify` を停止（4-3）③ CI の `Backend Lint & Security` の detect-secrets（既存の必須チェック。push 後の検出）④ 漏れたときの手順（4-6） |
| ワークフロー（`.github/workflows/`）・秘密情報の検査設定（`.pre-commit-config.yaml`・`.secrets.baseline`）の書き換え | PR を出した時点で PR 側のワークフローが secrets（`E2E_TEST_PASSWORD`・`GITHUB_TOKEN`）付きで動く。検査設定を外すと CI の検出も効かなくなる | 見張りが Edit/Write を確認にする（4-3）・レビュー観点に追加（4-7）・CI の検査が外されていないことを決定論テストで守る（4-4） |
| ワークフローが実行するコード（`backend/` のテスト・`e2e/` のテスト・`package.json` の scripts・`manage.py` のコマンド 等）の変更（/security-review で追加） | ワークフローを書き換えなくても、PR 側のこれらのコードが CI の中で動き、そのジョブの `GITHUB_TOKEN` と（e2e では）`E2E_TEST_PASSWORD` に触れられる。`ci.yml`・`e2e.yml` には `permissions:` が無く、`GITHUB_TOKEN` の権限はリポジトリの既定（bot からは読めない）に任されている | ① `ci.yml`・`e2e.yml` の最上位に `permissions: contents: read` を書き、`GITHUB_TOKEN` を読み取りだけに絞る（4-9）② `E2E_TEST_PASSWORD` は E2E 用の試験アカウントのパスワード（`seed_e2e` で作る）で、ログでは GitHub が伏せ字にする→ 対応不要（セキュリティレビュー結果の「残余リスク処遇」で確定） |
| リモートブランチの削除（`git push --delete`・`-d`・`<remote> :<ブランチ>`・`--prune`） | 手元に無い（別ワークツリー・別セッションの）ブランチの push 済みの作業は戻せない。PR も閉じる | 見張りが確認にする（4-3） |
| イシュー・PR への書き込み（`gh issue edit --body-file` 等） | 公開されるが、bot 自身が編集・削除できる | 対策しない。書くのは Claude が書いた記録ファイルで、秘密情報を扱わない。同期の前の detect-secrets も足さない（費用に見合わない。必要になったら決定論ゲートとして別途足す） |
| リポジトリ設定の変更・リリースの作成・ワークフローの手動実行（`gh api`・`gh release`・`gh workflow run`） | — | 対策不要。bot に管理権限が無い、または `settings.json` の allow に無く、ふだんの権限確認が出る |
| 保護ブランチへの push・強制 push・MCP からのマージ・別リポジトリの PR の取り込み | — | 既存のまま（単純で安いガードは残す） |
| マージ・cherry-pick・rebase で作るコミット | pre-commit（detect-secrets）は `git commit` でしか動かない | 対策しない（残余リスクとして記録）。push protection と CI の detect-secrets で拾う |

意図的な回避（`SKIP=detect-secrets`・`core.hooksPath` の書き換え・Bash でのワークフローの書き換え〔`sed -i`・`cat >`〕など）は対象外（見張りの脅威モデルは「事故」。`danger-ops.md` の既存の方針と同じ）。

### 4-1. 記録突き合わせ（`scripts/claude/tests/guard_corpus_diff.py`）の比べる相手
**修正方針**: 未コミットの変更が無いときの比べる相手を、「このブランチが develop から分かれた点（`git merge-base HEAD origin/develop`）」にする。develop を取り込んでいても、分かれた点は取り込んだ develop の先頭になるので、このブランチ自身の変更だけを比べられる。HEAD が分かれた点と同じ（develop の上・ブランチ固有のコミットが無い）ときだけ、今までと同じく「見張りを最後に変えたコミットの直前」と比べる。ここでは `--first-parent` を使い、マージコミットなら第 1 親（develop の取り込み前＝その PR の変更全体）と比べる。

```python
UPSTREAM = "origin/develop"

def base_rev(git) -> tuple:
    """未コミットの変更が無いときの比べる相手 (rev, 説明)。無ければ (None, 理由)。"""
    head = git("rev-parse", "HEAD").stdout.strip()
    mb = git("merge-base", "HEAD", UPSTREAM).stdout.strip()
    if mb and mb != head:
        return mb, f"{mb[:7]}（{UPSTREAM} との分かれた点）"
    last = git("log", "-1", "--first-parent", "--format=%H", "--", GUARD_REL).stdout.strip()
    if not last:
        return None, "比べる前の版の guard がありません"
    return f"{last}^1", f"{last[:7]}^1（guard を最後に変えたコミットの直前）"
```
- `main()` の `if same and a.base == "HEAD":` の中身を `base_rev(git)` の呼び出しに置き換える。`git show <rev>:<GUARD_REL>` が失敗したら今までどおり SKIP。
- `--base` を明示したときの動きは変えない。

### 4-2. 見張りの失敗を確認に倒す（`pretooluse_guard.py`）
**修正方針**: 見張り全体を最上位で包み、どこで失敗しても「確認」を返す。時間とメモリの上限を見張りの内側に設け、外からの時間切れ（素通りになる）より先に自分で打ち切る。値は定数にする。

```python
_TIME_LIMIT_SEC = 20                  # 見張りの所要時間の上限（計測の最大 1.59 秒の 10 倍以上）
_MEM_LIMIT_BYTES = 512 * 1024 * 1024  # データ領域の上限（計測の最大 41MB の 10 倍以上）

class _GuardTimeout(BaseException):
    """時間の上限を超えた（途中の except Exception に飲まれないよう BaseException から作る）。"""

def _on_alarm(signum, frame):
    raise _GuardTimeout()

def _install_limits():
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(_TIME_LIMIT_SEC)
    try:
        # RLIMIT_AS は gh（Go）が起動できなくなるので使わない（計画書 調査結果のスパイク）
        _, hard = resource.getrlimit(resource.RLIMIT_DATA)
        resource.setrlimit(resource.RLIMIT_DATA, (_MEM_LIMIT_BYTES, hard))
    except (ValueError, OSError):
        pass

def _fail_safe(e: BaseException):
    if isinstance(e, _GuardTimeout):
        why = f"時間の上限（{_TIME_LIMIT_SEC} 秒）を超えた"
    elif isinstance(e, MemoryError):
        why = f"メモリの上限（{_MEM_LIMIT_BYTES // 1024 // 1024}MB）を超えた"
    else:
        why = f"判定中に失敗した（{type(e).__name__}）"
    _ask(f"見張りが{why}ため、判定できませんでした。内容を確認してください。")

if __name__ == "__main__":
    _install_limits()
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:   # 例外・時間切れ・メモリ不足を素通し（exit 0/2 以外）にしない
        _fail_safe(e)
```
- `_ask`・`_block`・`_block_cross_worktree` の先頭で `signal.alarm(0)` を呼ぶ（出力の途中で打ち切られて、壊れた JSON が出ないように）。
- 既存の `_analyze`・`_safety_net` の try（確認に倒す）はそのまま残す（理由の表示が具体的なため）。
- 確認の理由には例外の**型名だけ**を出し、例外のメッセージ・コマンドの中身は出さない（コマンドに秘密情報が含まれうるため。/security-review の必須防御条件。TC F1 で `i182` という注入メッセージが理由に出ないことも確かめる）。
- 停止（exit 2）ではなく確認にする理由: 見張りの不具合で全操作が止まり、作業できなくなるのを避ける。人が内容を見て決める。
- 残余リスク: 途中の `except Exception`（`_trusted_repos` 等）が `MemoryError` を飲むと、その判定は「信頼しない場所」側（確認）に倒れる。素通しの側には倒れない。

### 4-3. 見張りの規則の追加（`pretooluse_guard.py`）
**修正方針**: GitHub から復旧できない操作だけを、コマンドの単純な読み取り（既存の `_cmd_danger` の git の分岐）で判定する。入れ子のシェル・安全網の経路でも同じに効くよう、単純コマンドごとの判定（`_cmd_danger`）に足す。

(a) **`--no-verify` の停止**（危険操作＝exit 2・`DANGER_OK=1` で確認）:
```python
_COMMIT_VALUE_SHORT = "mFCcSt"   # git commit で値を取る短いオプション（-m msg・-F file・-C/-c commit・-S keyid・-t file）
_COMMIT_VALUE_LONG = ("--message", "--file", "--reuse-message", "--reedit-message", "--author", "--date",
                      "--template", "--fixup", "--squash", "--trailer", "--cleanup", "--pathspec-from-file")

def _commit_no_verify(args: list) -> bool:
    """git commit の引数に --no-verify / -n（まとめた短縮形 -an も）があれば True。値（-m の本文など）は見ない。"""
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return False
        if a == "--no-verify":
            return True
        if a in _COMMIT_VALUE_LONG:
            i += 2
            continue
        step = 1
        if a.startswith("-") and not a.startswith("--") and len(a) > 1:
            for k, ch in enumerate(a[1:], 1):
                if ch == "n":
                    return True
                if ch in _COMMIT_VALUE_SHORT:
                    # getopt と同じ: 値を取る文字の後ろに文字が残ればそれが値、残らなければ次の語が値
                    step = 1 if k < len(a) - 1 else 2
                    break
        i += step                        # 進めるのはここ 1 か所だけ（-a -n のように分けて書いた形も 1 語ずつ見る）
    return False
```
`_cmd_danger` の git の分岐に追加:
```python
if sub == "commit" and _commit_no_verify(args):
    r.append("秘密情報の検査（pre-commit）を飛ばす git commit --no-verify / -n requires DANGER_OK=1")
if sub == "push" and "--no-verify" in args:
    r.append("git push --no-verify requires DANGER_OK=1")
```
- `git push -n` は `--dry-run` なので対象外（`--no-verify` だけ）。

(b) **リモートブランチの削除の確認**:
```python
def _push_deletes(args: list) -> bool:
    """git push がリモートのブランチを消す形（--delete・-d・--prune・<remote> :<ブランチ>）なら True。"""
    if "--delete" in args or "--prune" in args or _has_short([a for a in args if not a.startswith("--")], "d"):
        return True
    return any(r.lstrip("+").startswith(":") and r.lstrip("+") != ":" for r in _push_positionals(args)[1:])
```
- `_cmd_danger` の `sub == "push"` で `_push_deletes(args)` なら `c["remote_ask"] = "リモートブランチの削除（git push --delete / -d / :<ブランチ> / --prune）"` を立てる。
- `_analyze` の結果に `"remote_ask"` を足して集め（`git_unsure` と同じ扱い）、`_safety_net` の集める項目にも足す。`main()` で `an["remote_ask"]` または `net["remote_ask"]` があれば `_ask("GitHub から戻せないことがある操作です（…）。確認してください。")`。
- 保護ブランチの削除（`:develop`）・`git push origin :`（全部）は既存の判定で停止のまま（確認に格下げしない。判定の順は危険操作が先）。

(c) **ワークフロー・秘密情報の検査設定の Edit/Write の確認**:
```python
# PR を出した時点で secrets 付きで動くワークフローと、秘密情報の検査の設定（I182）。編集時に確認する
SECRET_GATE_EDIT_PATTERNS = [
    r"(?:^|/)\.github/workflows/",
    r"(?:^|/)\.pre-commit-config\.yaml$",
    r"(?:^|/)\.secrets\.baseline$",
]
```
`_check_edit_write` の `HIGH_RISK_EDIT_PATTERNS` の後に:
```python
for pat in SECRET_GATE_EDIT_PATTERNS:
    if re.search(pat, rel):
        _ask("PR を出した時点で secrets 付きで動くワークフロー・秘密情報の検査の設定の編集です"
             f"（GitHub から復旧できない範囲・danger-ops.md）。確認してください: {rel}")
```

### 4-4. CI の秘密情報の検査が外されていないことのテスト（新規 `scripts/claude/tests/test_i182_secret_gates.sh`）
**修正方針**: CI に新しいジョブは足さず、既存の検査（`Backend Lint & Security` の pre-commit で detect-secrets が全ファイルに走る）が残っていることを決定論テストで守る（TC C1〜C3・FG-C1〜FG-C3）。

### 4-5. 確認待ちの削減（`.claude/settings.json`・`scripts/claude/tests/test_settings_permissions.sh`）
**修正方針**: `ask` から `Bash(rm *)`・`Bash(mv *)`・`Bash(cp *)`・`Bash(chmod *)`・`Bash(chown *)` を外し、`allow` に移す（`ask` から外すだけだと、既定の権限確認が出て減らないため）。`ask` には `Bash(git rebase *)`・`Bash(psql *)` を残す。
- `rm -r`／`rm -rf`・`find -delete`・`xargs rm`・`git reset --hard` は見張りが危険操作として止める（`DANGER_OK=1` で人の承認）ので、CLAUDE.md の絶対ルール 4 は崩れない。別ワークツリーへの書き込み（絶対パス）も見張りが止める。
- 既存の allow `Bash(mv docs/*/open/* docs/*/closed/)`・`Bash(rm docs/*/open/*)` は `Bash(mv *)`・`Bash(rm *)` に含まれるので消す（重複の整理）。
- `test_settings_permissions.sh` の期待を変える: `keep_ask = ["Bash(git rebase *)", "Bash(psql *)"]`・新しく `to_allow = ["Bash(rm *)", "Bash(mv *)", "Bash(cp *)", "Bash(chmod *)", "Bash(chown *)"]` が allow にあり ask に無いこと。S2 の注入を「`Bash(rm *)` を ask に戻すと不合格」「`Bash(psql *)` を ask から外すと不合格」に置き換える（TC S1〜S2b・既存の S3〜S12）。

### 4-6. 手順書（`docs/runbooks/danger-ops.md`）
**修正方針**: 前提（復旧できる範囲）と漏れたときの手順を、ここに 1 か所でまとめる。
- 新しい節「## GitHub から復旧できる範囲（I182）」: 「develop/main は GitHub 側で保護され bot はマージできないので、ローカルで壊しても GitHub から復旧できる。失いうるのは push していない手元の変更だけ」という前提と、**その例外**（4-0 の表を移す）を書く。
- 新しい節「## 秘密情報を push してしまったとき（I182）」: 1) すぐにユーザーへ報告し、作業を止める 2) その鍵を発行元で無効化・再発行する（OpenAI・SendGrid は管理画面で失効、Django の `SECRET_KEY`・DB のパスワードは値を変えて `.env` と本番の設定を更新）。履歴を書き換えても公開は取り消せないので、無効化が先 3) その後でコミットから消す（push 前なら `git commit --amend`・未 push のコミットの作り直し。push 済みの書き換えは強制 push＝危険操作なので、計画書と承認で行う） 4) push protection に拒否されたとき（`GH013`・`push protection` の文言）は、拒否を回避しない（GitHub の「bypass」を使わない）。push 前なのでまだ公開されていない→ 該当のコミットから秘密情報を消してから push し直す。
- 「見張りの扱い（I174）」の 2. に `git commit --no-verify`／`-n`・`git push --no-verify` を、3. に「リモートブランチの削除」と「`.github/workflows/`・`.pre-commit-config.yaml`・`.secrets.baseline` の編集」を足す。新しい箇条書き: 「見張りが判定中に失敗した・20 秒を超えた・メモリが 512MB を超えたときは、素通しにせず確認にする」。
- 「例」の Git の行に `git commit --no-verify`／`-n` を足す。

### 4-7. その他の文書
- `docs/runbooks/review-rules.md`: 新しい節「## GitHub から復旧できない変更のレビュー観点（I182）」: ワークフロー（`.github/workflows/`）の変更は PR を出した時点で secrets 付きで動くので、PR を出す前に確かめる（secrets を出力・外部送信していない・`pull_request_target` を足していない・`permissions` を広げていない・`SKIP` に detect-secrets を足していない）。`.pre-commit-config.yaml`・`.secrets.baseline` の変更は detect-secrets を外す・新しい秘密情報を baseline に足していないかを確かめる。詳細の一覧は `danger-ops.md` を参照。
- `docs/runbooks/worktree.md`（「削除・破棄は技術的には止めない（I179 計画変更記録 6）」の段落）: 「ローカルが壊れても GitHub から復旧できるため」の後に「（例外は秘密情報の push とワークフローの変更など。`danger-ops.md`「GitHub から復旧できる範囲」）」を足す。
- `docs/issues/open/I181.md`（ローカル・未コミット。I181 の計画時にコミットされる）: 「前提」の「この前提には穴がある」の段落を、I182 の結論（例外の一覧は `danger-ops.md`「GitHub から復旧できる範囲」・そこに当たる変更は「GitHub が最後の守り」の対象外）に書き換える。「記録突き合わせの比べる相手」の項目（68 行目）は「I182 で対応済み」と書き換える。
- `scripts/claude/tests/test_pretooluse_guard_matrix.sh` の `OPS` に 3 行を足す: `"2|git commit --no-verify -m wip"`・`"2|git commit -anm wip"`・`"ASK|git push origin --delete feature/old"`（29 の書き方すべてで同じ結果になること）。

### 4-9. ワークフローの `GITHUB_TOKEN` を読み取りだけにする（`.github/workflows/ci.yml`・`.github/workflows/e2e.yml`・/security-review で追加）
**修正方針**: 最小権限の原則に沿って、2 つのワークフローの最上位（`on:` の後・`jobs:` の前）に次を足す。どちらのジョブも `actions/checkout`・`actions/setup-*`・`actions/upload-artifact`（`GITHUB_TOKEN` ではなく実行環境の別の権限で動く）しか使わず、書き込みの権限は要らない。`dependency-audit.yml` はすでに `permissions:` を持つので変えない。
```yaml
permissions:
  contents: read
```
- 効き目: PR 側のテスト・スクリプトが CI の中で動いても、`GITHUB_TOKEN` でブランチへの push・イシューや PR への書き込み・リリースの作成ができない。
- 確認: TC C4・FG-C4（両方のファイルの最上位の `permissions` が `{contents: read}` だけ）と、この PR の CI がすべて緑のまま（TC R7）。

### 4-8. GitHub の設定（ユーザーの UI 操作）
- **push protection の有効化**（計画の承認時に依頼する。以降の push を守るため早いほどよい）: リポジトリの Settings → Advanced Security（または Code security）→ 「Secret Protection」（Secret scanning）を Enable → 「Push protection」を Enable。
- **必須チェックの確認**（新しい設定は無い）: Settings → Branches（または Rules）→ develop の規則の「Require status checks to pass」に `Backend Lint & Security` が入っていることを確かめる。

## 5. 実装手順
1. **ステップ 1: 記録突き合わせの比べる相手（4-1）** → TC B1〜B4・FG-B1・R3。後のステップで見張りを変えたときのゲート（`test_guard_corpus_diff.sh`）を正しく動かすため最初に行う。
2. **ステップ 2: 見張りの失敗を確認に倒す（4-2）** → TC F1〜F6・FG-F1。ステップ 1 の後（ゲートで異常終了・新しい確認が増えないことを見る）。
3. **ステップ 3: 見張りの規則の追加（4-3）とマトリクスの追加（4-7 の最後）** → TC N1〜N10・D1〜D7・E1〜E6・FG-N1・FG-D1・FG-E1・R1〜R6。ステップ 2 の後（同じファイルを変えるため順に行う）。
4. **ステップ 4: CI の検査のテスト（4-4）とワークフローの権限（4-9）** → TC C1〜C4・FG-C1〜FG-C4・R7。ステップ 1〜3 と並行して行ってよい。ワークフローの変更は push で CI が動くので、R7 はこのステップの push の後に見る。
5. **ステップ 5: 確認待ちの削減（4-5）** → TC S1〜S12・手動 M3。ステップ 3 の後（危険な `rm` は見張りが止めることを先に確かめてから外す）。
6. **ステップ 6: 手順書・文書（4-6・4-7）** → TC DOC1〜DOC6・FG-DOC1・FG-DOC2・手動 M4・M5。ステップ 3・5 の後（書く内容が確定してから）。
7. **ステップ 7: GitHub の設定の確認（4-8）** → 手動 M1・M2（Human）。push protection の有効化は承認時に依頼し、ここで結果を記録する。

見張りを変えたステップ（1〜3）では、`danger-ops.md` の 3 つのテスト（TC R1〜R3）を流してからコミットする。

## 6. テスト計画
- 自動: `docs/tests/open/I182_auto_test.md`（すべて使い捨ての入力・複製・一時リポジトリで動くシェルの決定論テスト。合格＝exit 0）。テストレベル: 見張りはフックに stdin JSON を渡して exit code／ask を見る結合テスト、`guard_corpus_diff.py` は一時 git リポジトリでの結合テスト、設定・CI・文書は JSON／YAML／grep の静的テスト。
- 手動: `docs/tests/open/I182_manual_test.md`（GitHub の画面での push protection と必須チェックの確認＝Human。権限確認が実際に減ったかの確認＝プレーン default 新規セッション）。
- 再発防止テスト: 記録突き合わせのマージコミットの誤不合格（B1・FG-B1）・見張りの失敗の素通し（F1〜F4・FG-F1）。

## 7. ロールバック
- すべてファイルの変更なので、該当のコミットを `git revert` する。GitHub の設定（push protection）は Settings で Disable に戻せる（戻す理由は無い想定）。

## 8. Risk & 回避策
| Risk | 回避策 |
|------|--------|
| 見張りの新しい規則が、ふだんのコマンドを止める（例: `git commit -m "-n …"`） | `_commit_no_verify` は値を取るオプションの値を見ない（N4・N5）。記録突き合わせ（R3）で新しい確認・停止が記録の 1% を超えないことを見る |
| 20 秒・512MB の上限に、ふだんのコマンドで当たる | 計測の最大の 10 倍以上の値。R3（2,939 件）で新しい確認が増えないことを見る |
| `RLIMIT_DATA` が環境によって効かない・設定できない | 設定に失敗したら上限なしで続ける（今と同じ）。時間の上限と最上位の包みは別に効く |
| `rm *` を allow にして、ローカルの未コミットの作業を消す | `rm -r` 系は見張りが止める。単発の `rm` で消えるのは「push していない手元の変更」だけで、前提（復旧できる範囲）の内側。こまめな commit・push（`worktree.md`）で小さくする |
| Bash（`sed -i`・`cat >`）でワークフローを書き換える | 対象外（意図的な回避・脅威モデルは事故）として記録。レビュー観点（4-7）で PR 前に見る |
| push protection が既知の形式の鍵しか拾わない | CI の detect-secrets（汎用の鍵・パスワードの検出）と、見張りの `--no-verify` 停止で手元の detect-secrets を必ず通す |

## 9. 承認ポイント
（チャットで提示。下記と同じ）
- [ ] 計画時の変更 1: CI の秘密情報の検査は**既存**（`Backend Lint & Security` の pre-commit で detect-secrets を全ファイルに実行・必須チェック）だったため、新しいジョブは足さず、検査が外されないことのテスト（4-4）に置き換える。イシューの受け入れ条件 3 もそのように書き換える
- [ ] 計画時の変更 2: メモリの上限は `RLIMIT_AS` では `gh` が動かなくなるため `RLIMIT_DATA` にする
- [ ] Claude の判断で決めた範囲: `.pre-commit-config.yaml`・`.secrets.baseline` の編集もワークフローと同じく確認にする／`rm`・`mv`・`cp`・`chmod`・`chown` は ask から外すだけでなく allow に移す（外すだけでは既定の確認が出るため）・重複する allow 2 行を消す／リモートブランチの削除には `--prune` も含める／停止・確認の文言
- [ ] push protection の有効化をお願いします（4-8・承認と同時に）

## 計画時の変更記録
- **計画時の変更 1（2026-10-22）**: イシューの設計確認メモ「③ CI に detect-secrets のジョブを足し、develop の必須チェックにする」は、既存の `Backend Lint & Security` ジョブが detect-secrets を全ファイルに実行しており必須チェックでもあるため、「既存の検査が外されないことを決定論テストで守る」に置き換えた。イシュー本文（受け入れ条件・実装対象・制約）も同時に更新した。
- **計画時の変更 2（2026-10-22）**: 設計確認メモの「`resource.setrlimit(RLIMIT_AS)`」は、スパイクで `gh` が起動できなくなることが分かったため `RLIMIT_DATA` に変更した（イシュー本文も更新）。
- **計画時の変更 3（2026-10-23・/security-review）**: ワークフローを書き換えなくても、PR 側のテスト・スクリプトが CI の中で `GITHUB_TOKEN` に触れられることが分かったため、`ci.yml`・`e2e.yml` の最上位に `permissions: contents: read` を足す（4-9・TC C4・FG-C4・R7）。4-0 の表に 1 行を足し、イシュー本文・テスト文書・レビュー文書も同時に更新した。`.github/workflows/` を変えるので、Actions に関わる範囲の敵対的レビュー（1 周・時間上限付き）の対象に入る。

## レビュー結果
- [20261023_0036 判定: ✅ 完了](../../reviews/I182_plan_review_20261023_0036.md)
- [20261022_2231 判定: ✅ 完了](../../reviews/I182_plan_review_20261022_2231.md)
  - Warning 1（`_commit_no_verify` の `-a -n`）: 計画のコードでは `-a` で 1 つだけ進むため見逃さない（指摘の「2 増加」は for-else 後の `continue` を読み違えたもの）が、`i` を進める場所を 1 か所にまとめて読みやすくし、TC N10（`git commit -a -n -m x` → 2）を追加した。Info（冗長な `continue`）も同じ修正で解消
  - Warning 2（FG-N1 が 1 回だけの記録）: スクリプト内で毎回、複製から規則を外して N・D・E が不合格になることを確かめる形（FG-N1・FG-D1・FG-E1）に変更した
  - 高リスク判定 Yes（見張りの最上位の包み直し）: `/security-review I182` を実行してから `/implement` に進む

## セキュリティレビュー結果

**実施日**: 2026-10-23

対象: アプリ（backend / frontend）のコード変更なし。対象はハーネス（見張り・テスト・設定）と GitHub Actions の設定。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 認証・認可／外部通信 | `ci.yml`・`e2e.yml` に `permissions:` が無く、`GITHUB_TOKEN` の権限がリポジトリの既定に任されている。ワークフローを書き換えなくても、PR 側のテスト・`package.json` の scripts・`manage.py` のコマンドが CI の中で動き、そのトークン（既定が書き込み可なら push・イシュー/PR への書き込み）に触れられる。4-3 の「ワークフローの編集を確認」では防げない | **必須防御条件**: 両ファイルの最上位に `permissions: contents: read`（4-9）。ジョブ単位で広げない。TC C4・FG-C4 で守り、R7 で CI が緑のままを確かめる |
| Low | 機密情報 | 見張りの失敗時の確認の理由に、例外のメッセージやコマンドの中身（秘密情報を含みうる）が出る | **禁止事項**: 理由に例外のメッセージ・コマンドを出さない（型名だけ）。TC F1 で注入メッセージが出ないことを確かめる |
| Low | 機密情報 | `e2e.yml` の `E2E_TEST_PASSWORD` は、PR 側の e2e テストのコードから読める（GitHub の仕様）。失敗時に上げる Playwright のレポート（artifact）に、入力したパスワードが記録されうる | 値は E2E 用の試験アカウント（`seed_e2e` で作る）のもので、ログでは GitHub が伏せ字にする。下の「残余リスク処遇」で対応不要と確定 |
| Low | セキュリティ設定ミス | 見張りの失敗を「停止」ではなく「確認」に倒すため、本来止める操作が、判定の失敗で確認に下がりうる | 人が内容を見て承認する経路は残る（素通しにはならない）。設計どおり（4-2 の理由）。既存の `_analyze` の失敗時と同じ扱い |
| Low | ファイル操作 | `rm`・`mv` を allow にすると、git で管理していない秘密ファイル（`backend/.env`・`e2e/.env.e2e`）を確認なしで消す・動かすことがある。これは GitHub からも戻せない | `rm -r` 系は見張りが止める。単発の削除で失うのは手元のファイルで、作り直しと鍵の再発行で戻せる。下の「残余リスク処遇」で対応不要と確定 |
| Low | セキュリティ設定ミス | ワークフロー・検査設定を Bash（`sed -i`・`cat >`）で書き換えると、Edit/Write の確認を通らない | 対象外として記録済み（脅威モデルは事故・4-0）。レビュー観点（4-7）で PR の前に見る |

入力検証・マルチテナント・依存ライブラリ: なし（アプリのコードと依存の変更なし）。

### 攻撃シナリオレビュー

アプリのエンドポイントの追加・変更は無い。見張り・CI の変更について、「事故・誤操作」と「PR 側のコードが CI で動く」場面を想定する。

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | Bash（見張り） | Claude（bot） | `git commit --no-verify`／`-n` で pre-commit の detect-secrets を飛ばしてコミットし push | 停止（`DANGER_OK=1` でも人の承認） | Yes: N1〜N10・FG-N1・マトリクス | Yes: M3（新しいセッションで止まる） | `SKIP=`・`core.hooksPath` の書き換え（意図的な回避・対象外） | Medium |
| 2 | git push | Claude（bot） | 秘密情報を含むコミットを feature ブランチへ push | GitHub が push を拒否（push protection）／CI の detect-secrets が検出 | Yes: C1〜C3・FG-C1〜C3（CI の検査が外されない） | Yes: M1（push protection 有効）・M2（必須チェック） | push protection は既知の形式の鍵だけ。CI は push の後（公開後）の検出 | Medium |
| 3 | PR 側のコード（テスト・scripts） | PR を出せる者（bot） | CI の中で `GITHUB_TOKEN` を使ってブランチ・イシュー・リリースを書き換える | `GITHUB_TOKEN` が読み取りだけ | Yes: C4・FG-C4・R7 | No | `E2E_TEST_PASSWORD` は読める（試験アカウント・伏せ字） | Medium |
| 4 | Edit/Write | Claude（bot） | ワークフローや検査設定を書き換えて PR を出す（secrets の出力・`pull_request_target` の追加・`SKIP` の追加） | 編集時に確認・PR 前のレビュー観点 | Yes: E1〜E6・FG-E1 | No | Bash での書き換え（対象外） | Medium |
| 5 | Bash（見張り） | Claude（bot） | `git push origin --delete <他のセッションのブランチ>` | 確認 | Yes: D1〜D7・FG-D1 | No | `gh api -X DELETE`（allow に無くふだんの確認が出る） | Low |
| 6 | 見張りへの入力 | Claude（bot） | 判定に時間・メモリのかかる書き方や、判定の例外を起こす書き方で、止めるはずの操作を素通りさせる | 失敗・20 秒超え・512MB 超えは確認 | Yes: F1〜F6・FG-F1 | No | 途中の `except Exception` に飲まれた `MemoryError` は、その判定が「信頼しない場所」側（確認）に倒れる | Medium |
| 7 | Bash（`rm`・`mv` の allow） | Claude（bot） | 確認なしで `rm backend/.env` | — | No | No | 手元の秘密ファイルを失う（GitHub からも戻せない）。上の設計レビューの Low | Low |

### 残余リスク処遇
2026-10-23 にユーザー判断で、/retro を待たずに確定した（判断基準: ループ／ハーネスエンジニアリングのベストプラクティス・サクサク進める）。

| 残余リスク | 処遇 | 理由 |
|-----------|------|------|
| `E2E_TEST_PASSWORD` が PR 側の e2e テストから読める・Playwright のレポートに残りうる | 対応不要 | E2E 用の試験アカウントの値で、ログは GitHub が伏せ字にする。事故として起きにくい |
| `rm`・`mv` の allow で、git 管理外の秘密ファイル（`.env`）を確認なしで消す・動かす | 対応不要 | 「失いうるのは手元のもの」という前提の内側で、作り直しと鍵の再発行で戻せる。見張りを足すのは「ローカルの安全装置は最小限」の方針に反する |
| 見張りの失敗時は停止でなく確認に下がる | 対応不要（設計どおり） | 人が承認する経路が残る。4-2 の理由のとおり |
| ワークフロー・検査設定を Bash で書き換えると Edit/Write の確認を通らない | 対応不要（記録済み） | 見張りの脅威モデルは「普通の書き方の事故」で、意図的な回避は対象外（4-0）。PR 前のレビュー観点（4-7）で見る |

### 計画の再レビューの時期
計画時の変更 3（4-9）で計画を変えたため、計画レビュー（`/plan-issue-review I182`）をやり直す。実装中の計画変更もまとめて見るため、**`/code-review` の直前に 1 回だけ**行う（2026-10-23 ユーザー判断）。
- 2026-10-23 にユーザーが実装前に再実行し、✅ 完了（`docs/reviews/I182_plan_review_20261023_0036.md`）。計画時の変更 3 までは確認済み。`/code-review` の直前の再レビューは、実装中に計画を変えたときだけ行う。
- 同レビューの Info（`--base` を明示したときの決定論テストが B 群に無い）: 対応しない。`--base` を明示した経路は今回変えない（`base_rev()` は `--base` が既定の `HEAD` で未コミットの変更が無いときだけ呼ぶ）ため、回帰の入り口が無い。
