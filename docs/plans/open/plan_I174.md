# I174 計画書: 確認が必要な操作の見直し（docker compose exec 等の一律確認をやめ、コンテナ内の危険操作だけを見張りで止める）

## 基本情報
- **計画書ID**: plan_I174
- **関連イシュー**: #292
- **Draft PR**: #293
- **作成根拠資料**: docs/issues/open/I174.md（起点イシュー・設計確認メモ 7 回分を含む）
- **実装後評価**: docs/reviews/open/I174_review.md
- **作成日**: 2026-10-16
- **ブランチ**: `feature/I174-guard-based-permission-review`（`origin/develop` から分岐）
- **作業場所**: primary checkout（`/mnt/c/app/study-app-multitenant`）。track:harness だが、wt-harness は I146 で使用中のため例外（2026-10-16 ユーザー決定）
- **マージ順の制約**: I146（#260）のマージ後にマージする（ステップ 6）

## 1. 背景/目的

**背景**: I151 の作業中に、`docker compose exec` の承認待ちが約 28 回出て作業が滞った。過去 51 セッションの集計では、確認対象の操作 125 回のうち 120 回（約 96%）が `docker compose exec` で、中身は pytest・ruff・pip-audit・npm audit・読み取りの `manage.py shell` が大半だった。`.claude/settings.json` の `permissions.ask` が「コマンドの種類」で一律に確認をかけていて、「危険かどうか」を見ていないのが原因である。

**目的**: 本当に危険な操作（`docs/runbooks/danger-ops.md` の定義）と外部への送信だけを、見張り（PreToolUse フック `scripts/claude/hooks/pretooluse_guard.py`）が止めるか、人に確認を求める。それ以外の操作は auto mode の判断で止まらずに進める。安全性は落とさない。むしろ、調査で見つかった見張りの既存の穴（破壊的 SQL の見逃し・DANGER_OK=1 の自己承認）も塞ぐ。

## 調査結果

### 原因の概要
「確認が必要な操作」の設定が、コンテナの中で何をするかを見ずに `docker compose exec` を一律で止めている。一方で見張りは、コンテナ内の危険操作をほとんど捕まえられていない。人の承認も、その一律の設定に頼っていた。そのため、設定を外したくても外せなかった。

### 詳細な原因分析（2026-10-16 にフックへ直接入力して実測）
1. **一律の ask**: `.claude/settings.json:84-89` の `Bash(docker compose exec *)` などが ask になっていて、auto mode が安全と判断できる操作でも必ずプロンプトが出る（画面表示 `Ask rule Bash(docker compose exec *) overrides auto mode for this command.`）。
2. **効いていない allow**: `.claude/settings.json:68-77` の `docker compose exec backend pytest *` などの 10 行は、ask が allow より優先されることと、実際のコマンドに `-T` が付いていて一致しないことから、一度も効いていない。`Write(...)` ルールの 10 行（allow 9・11・13・15・17 行目、deny 122・123・124・126・128 行目）も、Claude Code が「`Write(docs/**) is not matched by file permission checks — only Edit(path) rules are`」と警告していて効いていない（同じ範囲は `Edit(...)` が受け持っている）。
3. **破壊的 SQL の見逃し（既存の不具合）**: `pretooluse_guard.py:503-512` は判定語の前に空白を要求するので（`" drop "` など）、SQL 文が判定語で始まると一致しない。二重引用符の `-c "..."` しか見ていない。実測では `docker compose exec -T db psql -U postgres -c "DROP DATABASE migrate_check;"`・`... -c "TRUNCATE problems_problem;"`・`... -c "DELETE FROM problems_problem;"`・`... -c 'DROP DATABASE x;'` がすべて exit 0（素通り）だった。
4. **コンテナ内の危険操作は素通り**: `manage.py flush`・`migrate problems zero`・`sqlflush`・`dropdb`・`psql ... < dump.sql`・shell 内の `.delete()` は、すべて exit 0 だった。
5. **DANGER_OK=1 の自己承認**: `pretooluse_guard.py:454` の `if not danger_ok:` は、DANGER_OK=1 が付くと危険操作の判定をすべて飛ばす。現状で人の承認がかかるのは、ask ルール（`git reset *`・`docker compose down *`・`rm *` など）が当たっているからにすぎない。ask を外すと、Claude が `DANGER_OK=1` を付けるだけで通ってしまい、CLAUDE.md 絶対ルール 4（危険操作は承認制）に反する。
6. **`rm -rf` の止めすぎ（既存の不具合）**: hard-block の `\brm\s+-rf\s+/\b`（433 行目）は、ルート `/` だけでなく絶対パスの `rm -rf` すべてに一致し、DANGER_OK=1 でも解除できない（実測: `rm -rf /tmp/claude-1000/xyz` → exit 2）。さらに、通常ルールの `\brm\s+-rf\b`（491 行目）はコマンド行の文字列全体を見るので、grep の検索文字列やヒアドキュメントの中身にも反応する。本セッションでも、`grep -n -E "...rm -rf..."` と検証用スクリプトを書くヒアドキュメントの 2 回、誤って止められた。
7. **実メール・有料 API への送信**: 開発環境は `EMAIL_BACKEND` が SMTP 固定（`backend/core/settings.py:266`）である。送信経路は 3 つ: 登録（`accounts/views.py:197`）・パスワード再設定の依頼（同 320 行目）・`send_study_reminders_task`（`studylogs/tasks.py:70`）。OpenAI による AI 問題生成は、`problems/views.py:365`（`generate_ai`）・500 行目（`generate_adaptive`）・`manage.py generate_ai_problems` の 3 経路。いまは `openai.ChatCompletion.create` が廃止 API のため必ず失敗するが、I153 で直ると送信が始まる。ほかの外部 SDK は使われていない。

### 既存テストのベースライン（2026-10-16・本ブランチ）
| テスト | 結果 |
|---|---|
| `scripts/claude/tests/test_pretooluse_push_guard.sh` | pass=87 fail=0 |
| `scripts/claude/tests/test_pretooluse_checkout_guard.sh` | pass=14 fail=0 |
| `scripts/claude/tests/test_pretooluse_worktree_guard.sh` | pass=27 fail=0 |
| `scripts/claude/tests/test_adversarial_trigger.sh` | pass=40 fail=0 |

既存テストは exit code と `runj`（exit 0 ＋ `permissionDecision=ask` の JSON）だけで判定していて、stderr の文言は検査していない（`grep` で確認）。

### 環境前提
- `python3`（フック実行）・`bash`・`git`・`gh` はホストで使用中（本セッションで実行済み）。追加のツールは不要。
- フックの変更は、そのセッションで次に実行するツールから効く（フックは毎回 `python3` で起動されるため）。`.claude/settings.json` の権限変更は、**新しいセッションから**効く。

### ハーネス挙動の未実証事項（スパイク区分 (2)）
- **auto mode でフックの `permissionDecision=ask` が人へのプロンプトになるか**は、本計画の前提（解決方針 1(d)・(b2)）である。既存の `_ask`（`HIGH_RISK_EDIT_PATTERNS`・動的 push）は I079・I083 で使われているが、auto mode で観測した記録は見当たらない。稼働中のセッションでは、プロンプトがどこから出たか（フックの ask／通常の権限／モード）を区別できない。そのため「未実証」とし、**実装ステップ 1 で新しいセッションで実証する**。成り立たなければ、計画をやり直す（1(d) を「DANGER_OK=1 でも exit 2 にし、承認後に人が手で実行する」形に変えるなど）。

### 文書の消費箇所（grep・2026-10-16）
`DANGER_OK` と ask に触れている文書は次のとおり。変更が要るのは danger-ops.md だけである。
| ファイル | 記述 | 対応 |
|---|---|---|
| `docs/runbooks/danger-ops.md:3,17,23` | DANGER_OK=1 の運用・checkout のブロック | **更新**（ステップ 5） |
| `docs/runbooks/worktree.md:41,43,93` | `DANGER_OK=1 bash scripts/claude/wt-remove.sh` | 変更なし（スクリプト内の `down -v` は guard から見えない。既存の挙動のまま。リスク R7） |
| `docs/runbooks/worktree.md:173` | worktree 横断の書き込みは DANGER_OK でも解除しない | 変更なし（本計画でも exit 2 のまま） |
| `docs/runbooks/workflow.md:42`・`.claude/skills/implement/SKILL.md:19` | Danger Ops は danger-approved＋DANGER_OK=1 が必須 | 変更なし（記述は本計画後も正しい）。「DANGER_OK=1 を付けても guard が人の承認を求める」挙動の変化は、両ファイルが参照する danger-ops.md に書く（計画レビュー Info 1 を検討し、説明の重複を避けるため追記しないと判断） |

## 2. 受け入れ条件
イシュー I174 の受け入れ条件をそのまま採用する（ステップと TC の対応は「6. テスト計画」）。
- [ ] AC-1 `.claude/settings.json` の ask に `docker compose exec/run/down`・`docker-compose exec/run/down`・`git reset`・`git merge`・`git cherry-pick` が無い
- [ ] AC-2 効いていない exec の allow 10 行が無い
- [ ] AC-3 `Write(...)` ルールが無い
- [ ] AC-4 危険操作（破壊的 SQL・DB 全消去・マイグレーション巻き戻し・ダンプ流し込み・loaddata・Redis 全消去・shell 内の削除と一括更新・`rm -rf`）を exit 2 で止める。書き出し（ホスト／`docker exec`／`docker compose exec/run`／`docker-compose`／`sh -c`）に関係なく止める
- [ ] AC-5 上記に `DANGER_OK=1` を付けると ask を返す。既存の解除経路（reset --hard・down -v・checkout・push 系）も ask を返す
- [ ] AC-6 外部送信（メール・celery の起動・登録とパスワード再設定依頼の API・OpenAI）に ask を返す。ログインとパスワード再設定の確定には返さない
- [ ] AC-7 実行されるファイルの中身にも AC-4・AC-6 の判定をかける。読めなければ stderr に出して素通しする
- [ ] AC-8 `rm -rf /` と `rm -rf /*` は DANGER_OK=1 でも exit 2。ルート以外は通常の危険操作として扱う。grep の検索文字列やヒアドキュメントの中の `rm -rf` には反応しない
- [ ] AC-9 読み取り・テスト系（pytest・ruff・pip-audit・npm audit・makemigrations --check・migrate・`psql -c "\dt"`・CREATE DATABASE・読み取りの shell・1 件だけの更新・`redis-cli ping` / `KEYS`・dumpdata）は止めず、ask も返さない
- [ ] AC-10 既存の guard のテストが全件合格（DOK1〜3・P6・P7・P23・P24・P26・P31・G7 は ASK・A19 は exit 2）
- [ ] AC-11 danger-ops.md に、guard が止める操作・DANGER_OK=1 でも人の承認が要ること・回避の書き方を使わないことが書かれている
- [ ] AC-12 新しいセッションで `docker compose exec -T backend python -m pytest -q` にプロンプトが出ない

## 3. 影響範囲
- Backend: なし（アプリのコードは変更しない）
- Frontend: なし
- DB: なし
- Config/Infra:
  - `scripts/claude/hooks/pretooluse_guard.py`（判定の追加・是正）
  - `scripts/claude/tests/test_pretooluse_container_guard.sh`（新規）
  - `scripts/claude/tests/test_pretooluse_push_guard.sh`・`scripts/claude/tests/test_pretooluse_checkout_guard.sh`（DANGER_OK=1 の期待値を ASK に）
  - `.claude/settings.json`（ask・allow・deny の整理）
  - `docs/runbooks/danger-ops.md`（追記）
  - 波及: Claude Code の全セッション（primary と wt-harness の両方。settings.json と guard は commit で共有される）。新しいセッションから効く

## 4. 変更点一覧（具体）

### 4-1. 修正アプローチ（全体像）
見張りの判定を「コマンドの書き出し」ではなく「実際に何をするか」で行う形に作り替える。そのうえで、一律の確認設定を外す。判定は 3 種類に分ける。
- **常に止める（解除不可・exit 2）**: ルート `/` の削除・mkfs・dd・shred・別 worktree への書き込み（既存どおり）
- **危険操作（exit 2・DANGER_OK=1 を付けると人の確認）**: 既存の危険操作（保護ブランチへの push・force push・`reset --hard`・`down -v`・変更ありのファイルの checkout）＋本計画で足す危険操作
- **外部送信（人の確認）**: メール・celery の起動・OpenAI

文字列全体への部分一致はやめ、`_segments()`（shlex でのトークン分割）で得たトークン列に対して判定する。これで grep の検索文字列などへの誤反応を防ぐ。`sh -c` / `bash -c` の中身と `manage.py shell -c` / `python -c` のコードは、取り出して同じ判定にかける。

### 4-2. `pretooluse_guard.py` の変更

**(1) 判定の入口の作り替え（解決方針 1(d)）**
- 修正方針: `main()` の Bash 分岐で、危険操作の理由を `_danger_reasons(cmd)` に集めてから、DANGER_OK=1 の有無で分ける。DANGER_OK=1 が付いていても、該当すれば素通しせずに ask を返す。既存の判定（保護 push・`--all/--mirror`・`--repo`・force・`reset --hard`・`down -v`・checkout・破壊的 SQL）も、この入口に移す。
- 置き場所: 既存の hard-block（mkfs・dd・shred）と worktree 横断のブロックは、今の位置のまま（DANGER_OK でも解除しない）。
```python
def _danger_reasons(cmd: str) -> list:
    """DANGER_OK=1 で人の承認に切り替わる危険操作の理由を集める（該当なしは []）。"""
    reasons = []
    dest = _push_protected_target(cmd)
    if dest:
        reasons.append(f"push to protected branch '{dest}' is forbidden "
                       f"(release/hotfix は計画書明記＋danger-approved＋DANGER_OK=1 のみ)")
    # ... 既存の --all/--mirror・--repo・force・reset --hard・down -v・checkout をここへ移す（文言は既存のまま）
    reasons += _rm_rf_reasons(cmd)                 # (4) ルート以外の rm -rf
    reasons += _sql_reasons(cmd)                   # (2) 破壊的 SQL
    reasons += _container_danger_reasons(cmd)      # (3) DB 全消去・巻き戻し・流し込み・Redis・shell
    return reasons

# main() の Bash 分岐（hard-block・worktree の後）
reasons = _danger_reasons(cmd)
if reasons:
    if danger_ok:
        _ask("DANGER_OK=1 付きの危険操作です。内容を確認して承認してください: " + " / ".join(reasons))
    _block(reasons[0], raw)
external = _external_reasons(cmd)                  # (5) 外部送信
if external:
    _ask("外部への送信を伴う操作です。確認してください: " + " / ".join(external))
if _push_is_dynamic(cmd):                          # 既存。DANGER_OK=1 でも ask にする（DOK1〜3）
    _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")
```
- 既存のメッセージ文言は変えない（`requires DANGER_OK=1` など）。

**(2) 破壊的 SQL の判定（解決方針 1(a)）**
- 修正方針: 引用符の種類と書き出しに関係なく、`psql` のトークン列から SQL を取り出し、文（`;` 区切り）ごとに単語境界で判定する。
```python
def _sql_is_destructive(sql: str) -> bool:
    for stmt in sql.split(";"):
        s = stmt.lower()
        if re.search(r"\b(drop|truncate)\b", s) or re.search(r"\balter\s+table\b", s):
            return True
        has_where = re.search(r"\bwhere\b", s)
        if re.search(r"\bupdate\b", s) and re.search(r"\bset\b", s) and not has_where:
            return True
        if re.search(r"\bdelete\s+from\b", s) and not has_where:
            return True
    return False
```
- SQL を取り出す場所: `psql` を含むセグメントの `-c` / `--command` の次のトークンと `--command=...`。shlex が引用符を外すので、`"..."` と `'...'` の両方を扱える。
- shell・`python -c`・実行ファイルの中身では、引用符で囲まれた文字列リテラルだけにこの判定をかける（`(['"])(.*?)\1`）。コード全体にかけると、`.drop(` などに誤反応するため。

**(3) コンテナ内の危険操作（解決方針 1(b)）**
- 修正方針: セグメントの中で `manage.py`（`basename` が `manage.py` のトークン）・`psql`・`dropdb`・`pg_restore`・`redis-cli` を探し、その後ろのトークンで判定する。トークンをセグメントのどこからでも探すので、ホストで直接実行・`docker exec <名前>`・`docker compose exec/run`・`docker-compose` のどの書き出しでも同じ結果になる。`sh` / `bash` / `dash` / `zsh` の `-c` の次のトークンは、再帰的に `_segments()` に通す（深さ 3 まで）。
- 判定表:

| 対象 | 危険とする条件 |
|---|---|
| `manage.py` の次が `flush` / `sqlflush` / `reset_db` | 常に |
| `manage.py loaddata` | 常に |
| `manage.py migrate` | 位置引数が 2 つ以上（値を取るオプション `--database` / `--settings` / `--pythonpath` / `-v` / `--verbosity` の値は数えない） |
| `manage.py shell` | `-c` / `--command` のコードが (3-a) に該当、または `<` で流し込むファイルの中身が (3-a) に該当（(6) を参照） |
| `python` / `python3` の `-c` | コードが (3-a) に該当 |
| `psql` | `-f` / `--file` / `--file=`、`<` によるファイルの流し込み（`<` 単独のトークンと `<ファイル` の付着形の両方） |
| `dropdb` | 常に |
| `pg_restore` | `--clean` / `-c` |
| `redis-cli` | 引数のどれかが（大文字小文字を区別せず）`FLUSHALL` / `FLUSHDB` |

- (3-a) コードの危険パターン（Python のコード文字列に対して）:
```python
_CODE_DANGER = [
    (r"\.delete\(", "データ削除（.delete()）"),
    (r"\bobjects\b[^;\n]*\.update\(", "QuerySet の一括更新（.update()）"),
    (r"\.bulk_update\(", "一括更新（bulk_update）"),
    (r"call_command\(\s*['\"](flush|sqlflush|reset_db)['\"]", "管理コマンドによる DB 全消去"),
    (r"call_command\(\s*['\"]migrate['\"][^)]*['\"]zero['\"]", "管理コマンドによるマイグレーション巻き戻し"),
]
# ＋ 文字列リテラルへの _sql_is_destructive（(2)）
```

**(4) `rm -rf` の判定（解決方針 1(c)）**
- 修正方針: 433 行目と 491 行目の文字列への正規表現をやめ、セグメントのトークン列で判定する。`rm`（`basename` が `rm`）のトークンを探し、その後ろのフラグに再帰（`r` / `R` / `--recursive`）と強制（`f` / `--force`）の両方があるときだけ対象にする。対象（フラグ以外のトークン）に `/` または `/*` があれば **hard-block（解除不可）**、それ以外は**危険操作**（DANGER_OK=1 で ask）にする。`grep -n "rm -rf"` は `rm -rf` が 1 つのトークンになるので反応しない。ヒアドキュメントの中身は、shlex 上は別トークンになりうるが、`rm` の直前が `<<` の区切り語の後ろ……と厳密に追うのは難しい。そこで、ヒアドキュメント（`<<`）を含むコマンドは `<<` 以降を判定対象から外す。
```python
def _rm_rf_targets(cmd: str):
    """rm の再帰＋強制削除の対象を返す（[] は該当なし）。<< 以降（ヒアドキュメント本文）は見ない。"""
    head = cmd.split("<<", 1)[0]
    for toks in _expand_segments(head):            # sh -c の中身も展開する
        for i, t in enumerate(toks):
            if os.path.basename(t) != "rm":
                continue
            flags = [a for a in toks[i + 1:] if a.startswith("-")]
            short = "".join(a[1:] for a in flags if not a.startswith("--"))
            rec = any(c in short for c in "rR") or "--recursive" in flags
            force = "f" in short or "--force" in flags
            if rec and force:
                return [a for a in toks[i + 1:] if not a.startswith("-")]
    return []
```
- hard-block の判定（`/` または `/*`）は、既存の mkfs などと同じく DANGER_OK の前に行う。

**(5) 外部送信（解決方針 1(b2)）**
- 修正方針: 「実行されるコード」にだけ判定をかける。対象は `manage.py shell -c` のコード・`python -c` のコード・実行ファイルの中身（(6)）・構造で分かるもの（`celery ... call`・`manage.py generate_ai_problems`）である。コマンド行の文字列全体には判定をかけない（`grep -rn send_mail backend` のような検索で ask が出ないようにするため）。
```python
_CODE_EXTERNAL = [
    (r"\b(send_mail|send_mass_mail|mail_admins|mail_managers)\(", "メール送信"),
    (r"\bEmail(Message|MultiAlternatives)\b", "メール送信"),
    (r"\.(delay|apply_async)\(", "celery タスクの起動"),
    (r"\bsend_study_reminders_task\b", "学習リマインダー送信タスク"),
    (r"auth/register/", "登録 API（確認メールを送信）"),
    (r"auth/password-reset/", "パスワード再設定依頼 API（メールを送信）"),
    (r"\bAIQuestionGenerator\b|problems/generate_(ai|adaptive)/|\bopenai\.", "OpenAI への送信"),
]
```
- `auth/password-reset/` は、`auth/password-reset-confirm/` には一致しない（`password-reset-confirm/` には、末尾が `/` の `password-reset/` という並びが含まれないため）。
- 構造での判定: セグメントに `celery` と `call` の両方のトークンがある／`manage.py` の次が `generate_ai_problems`。

**(6) 実行ファイルの中身（解決方針 1(b3)）**
- 修正方針: 実行されるファイルを特定できるときは、中身に (3-a)・(2) の文字列リテラル判定・(5) をかける。
- 対象の形と、パスの読み方:

| 形 | パスの読み方 |
|---|---|
| `manage.py shell < <パス>`（`<` は単独トークンと付着形の両方） | ホストのパス（`<` はホストのシェルが処理するため） |
| `python` / `python3` の最初の位置引数が `.py` で終わる（`-m` / `-c` があるときは対象外） | コンテナ内の実行（セグメントに `exec` / `run` があり、その前に `docker` / `compose` / `docker-compose` がある）なら、コンテナのパスとして読み替える。それ以外はホストのパス |
| `sh` / `bash` の最初の位置引数（コンテナ内の実行のときだけ） | コンテナのパスとして読み替える |

- コンテナのパスの読み替え（`docker-compose.yml:48-49` のマウントに合わせ、guard に固定で持つ）: `/app/docs/<x>` → `<リポジトリ>/docs/<x>`、`/app/<x>` → `<リポジトリ>/backend/<x>`、相対パス `<x>` → `<リポジトリ>/backend/<x>`（作業ディレクトリが `/app` のため）。`<リポジトリ>` は `git rev-parse --show-toplevel`（`_current_worktree_root()`）。
- 対象外: ホストの `bash` / `sh` で実行するスクリプト（`bash scripts/claude/tests/*.sh` などのテストは、危険な命令を**入力データとして**含むため）。`scripts/claude/` 配下のファイル（ハーネス自身のコード。guard 自身も判定パターンを文字列として含むため）。
- 読めないとき（パスを解決できない・存在しない・1 MB を超える・UTF-8 で読めない）: 判定を飛ばし、stderr に `[guard] 実行ファイルの中身を確認できませんでした（判定を省略）: <パス>` と出す。exit 0。

**(7) 定数**
- コンテナのパスの対応表・判定パターンの表・ファイルの大きさの上限（`_MAX_SCRIPT_BYTES = 1_000_000`）は、モジュールの先頭付近の定数にまとめる（ハードコードを散らさない）。

### 4-3. テスト
- `scripts/claude/tests/test_pretooluse_container_guard.sh`（新規）: 既存の `test_pretooluse_push_guard.sh` と同じ形（`json()`・`run()`・`runj()`・`ck()`・最後に `pass=` / `fail=` を出して `[ "$fail" -eq 0 ]`）で書く。ケースは自動テスト文書の TC-01 の表を全件入れる。偽合格を防ぐため、判定関数の呼び出しを無効化した複製（`sed` で `_container_danger_reasons(cmd)` を `[]` に置き換えるなど）では素通しになり、実体では止まることも確かめる（既存の FALSEGREEN と同じ方式）。
- `scripts/claude/tests/test_pretooluse_push_guard.sh`: `DOK1`〜`DOK3`（114・140・141 行目）の期待値を `ASK` にする。`P6`・`P7`・`P23`・`P24`・`P26`・`P31`（51・52・71・72・74・79 行目）を `run` から `runj` に変え、期待値を `ASK` にする。
- `scripts/claude/tests/test_pretooluse_checkout_guard.sh`: `runj()` を `test_pretooluse_push_guard.sh:33-35` と同じ定義で追加し、`G7`（38 行目）を `runj` の `ASK` にする。

### 4-4. `.claude/settings.json`
- `permissions.ask` から削除（9 行）: `Bash(git merge *)`・`Bash(git reset *)`・`Bash(git cherry-pick *)`・`Bash(docker compose exec *)`・`Bash(docker compose run *)`・`Bash(docker compose down *)`・`Bash(docker-compose exec *)`・`Bash(docker-compose run *)`・`Bash(docker-compose down *)`
- `permissions.ask` に残す（7 行）: `Bash(git rebase *)`・`Bash(psql *)`・`Bash(rm *)`・`Bash(mv *)`・`Bash(cp *)`・`Bash(chmod *)`・`Bash(chown *)`
- `permissions.allow` から削除（15 行）: 68〜77 行目の `docker compose exec ...` / `docker-compose exec ...` 10 行、`Write(docs/**)`・`Write(docs/issues/**)`・`Write(backend/**)`・`Write(frontend/**)`・`Write(scripts/claude/**)` の 5 行
- `permissions.deny` から削除（5 行）: `Write(./.env)`・`Write(./.env.*)`・`Write(./secrets/**)`・`Write(**/*.pem)`・`Write(**/*.key)`（同じ範囲は `Edit(...)` の deny が残る）

### 4-5. `docs/runbooks/danger-ops.md`
- 「例」の DB に `manage.py flush` / `sqlflush` / `reset_db`・`migrate <app> <移動先>`（巻き戻し）・`loaddata`・ダンプと SQL ファイルの流し込み（`psql -f` / `< ファイル`・`pg_restore --clean`・`dropdb`）・shell 内の `.delete()` と一括更新を、Docker に `redis-cli FLUSHALL` / `FLUSHDB` を追記する。
- 新しい節「見張り（pretooluse_guard.py）の扱い」を追加する。中身は 4 点: ①上の操作は、ホスト・`docker exec`・`docker compose exec/run` のどれで実行しても止まる ②`DANGER_OK=1` を付けても、見張りは人の承認を求める（自分で付けて通すことはできない） ③外部送信（メール・celery の起動・OpenAI）は人の確認になる ④変数・`eval`・base64 での組み立て・`docker compose cp` 後の実行・コンテナ内で作ったファイルの実行などの、見張りを避ける書き方を使わない。

## 5. 実装手順（ステップ）
1. **スパイク: auto mode でフックの ask がプロンプトになるかを実証**（未知リスク先行）。→ 手動テスト No.1。**ゲート**: 成り立たなければステップ 2 以降に進まず、計画をやり直す。
2. **判定の入口の作り替え・破壊的 SQL・`rm -rf` の是正**（4-2 の (1)(2)(4)）と、既存テストの期待値の更新（4-3 の push・checkout）。新規テストには (1)(2)(4) のケースを先に入れる。ステップ 1 の完了が前提。→ TC-01（(1)(2)(4) の部分）・TC-02・TC-03・TC-04・TC-05・TC-10・TC-11 参照
3. **コンテナ内の危険操作・外部送信・実行ファイルの中身**（4-2 の (3)(5)(6)(7)）と、そのテストケース。ステップ 2 の完了が前提。→ TC-01（全件）・TC-10 参照
4. **`.claude/settings.json` の整理**（4-4）。ステップ 3 の完了が前提（見張りの強化を先に入れる順序の制約。コミットもこの順にする）。→ TC-06・TC-07・TC-08 参照
5. **danger-ops.md の追記**（4-5）。ステップ 4 と並行してよい。→ TC-09 参照
6. **I146 マージ後の取り込み**（マージ前に必須）。I146（#260）が develop にマージされたら、develop を本ブランチへ取り込み、`pretooluse_guard.py`・`.claude/settings.json` の競合を解消する。I146 が足した解除経路にも (1) の入口（DANGER_OK=1 で ask）を当てる。I146 マージ前に `/test` まで進んだ場合は、ここで止めて待つ。→ TC-12 参照
7. **新しいセッションでの確認**（設定はセッション開始時に読まれるため）。ステップ 4・6 の完了が前提。→ 手動テスト No.2〜No.4 参照

サービスの再起動は不要（アプリのコードを変えないため）。設定の反映には Claude Code のセッションを開き直す。

## 6. テスト計画
### 自動（`docs/tests/open/I174_auto_test.md`）
- テストレベル: すべて決定論の単体テスト（フックへ JSON を入れて exit code と ask の JSON を確かめる bash スクリプト）と、ファイルの静的検査（`grep` / `json.tool` / `py_compile` / `bash -n`）。アプリの pytest・E2E は、アプリのコードを変えないため対象外。
- TC と受け入れ条件の対応:

| TC | 内容 | AC |
|---|---|---|
| TC-01 | 新規 `test_pretooluse_container_guard.sh` | AC-4〜AC-9 |
| TC-02 | `test_pretooluse_push_guard.sh` | AC-5・AC-10 |
| TC-03 | `test_pretooluse_checkout_guard.sh` | AC-5・AC-10 |
| TC-04 | `test_pretooluse_worktree_guard.sh`（変更なし・回帰） | AC-10 |
| TC-05 | `test_adversarial_trigger.sh`（変更なし・回帰） | AC-10 |
| TC-06 | settings.json の JSON 構文 | AC-1〜AC-3 |
| TC-07 | 外した ask が無く、残す ask がある | AC-1・AC-2 |
| TC-08 | `Write(` が無い | AC-3 |
| TC-09 | danger-ops.md の追記 | AC-11 |
| TC-10 | guard の構文 | — |
| TC-11 | 新規テストの構文 | — |
| TC-12 | I146 マージ後の `test_pretooluse_gh_pr_guard.sh` | AC-10 |

- 再発防止: 破壊的 SQL の見逃しと `rm -rf` の止めすぎは既存の不具合なので、TC-01 に再現ケース（`-c "DROP ..."`・`-c '...'`・`rm -rf /tmp/xxx` が解除できること・grep の検索文字列に反応しないこと）を入れる。
- 偽合格の防止: TC-01 は判定の呼び出しを無効化した複製で素通しになることも確かめる。TC-07・TC-08・TC-09 は、実装前（違反がある状態）に実行して不合格になることを計画時点で確かめた（auto_test の実施記録）。

### 手動（`docs/tests/open/I174_manual_test.md`）
- No.1: フックの ask が auto mode でプロンプトになる（ステップ 1・新しいセッション・Human 目視）
- No.2: pytest にプロンプトが出ない（AC-12・新しいセッション）
- No.3: DANGER_OK=1 付きの危険操作にプロンプトが出る（新しいセッション）
- No.4: 外部送信にプロンプトが出る（新しいセッション）

## 7. ロールバック
- PR を revert する（`.claude/settings.json`・guard・テスト・danger-ops.md が一緒に戻る）。データの変更は無い。
- 一時的に戻すだけなら、`.claude/settings.json` の ask に `Bash(docker compose exec *)` などを戻して、セッションを開き直せばよい（guard の強化は残っても害はない）。

## 8. Risk & 回避策
| # | リスク | 回避策 |
|---|---|---|
| R1 | auto mode でフックの ask がプロンプトにならない | ステップ 1 のスパイクをゲートにする。不成立なら計画をやり直す |
| R2 | 誤検知で確認や停止が増える（例: `grep` の検索、テストスクリプト） | 判定を「実行されるコード」と「トークン」に限る。ホストの bash スクリプトと `scripts/claude/` を中身の判定から外す。TC-01 に誤検知しないケースを入れる |
| R3 | 見逃し（変数・eval・base64・`docker compose cp` 後の実行・コンテナ内で作ったファイル） | 受け入れる残余リスクとしてイシューと danger-ops.md に明記する。auto mode の判断を第 2 層にする。Claude は回避の書き方を使わない |
| R4 | I146 との競合（guard +256 行・settings.json +9 行） | マージを I146 の後にし、ステップ 6 で取り込む。I146 の解除経路にも (1) を当て、I146 のテスト（TC-12）を合格させる |
| R5 | 権限の変更が今のセッションに効かず、「直った」と誤認する | 手動テスト No.2〜No.4 は新しいセッションで行う |
| R6 | compose のマウントを変えると、(6) の読み替え表が古くなる | 表を guard の定数にまとめ、`docker-compose.yml:48-49` を参照するコメントを付ける |
| R7 | `DANGER_OK=1 bash scripts/claude/wt-remove.sh` の中の `down -v` は、guard から見えない（既存の挙動のまま） | 本計画では変えない（スクリプト自身が DANGER_OK=1 を要求する）。気づいた点としてレビュー文書に記録する |
| R9 | celery の起動（`.delay(` / `.apply_async(`・`celery ... call`）は、メールや OpenAI と関係のないタスクにも反応する。今後タスクが増えると確認が増えうる（2026-10-16 計画レビュー Warning 2） | 現状、shell から celery タスクを起動する作業はまれで、送信の有無はタスクの中を見ないと分からないため、広めに確認を出すほうを選ぶ。確認が頻繁に出るようになったら、送信するタスクの名前の一覧で判定する形に絞る（その時点で別イシュー） |
| R10 | ステップ 1 で、対話セッションの一部（wt-harness・版 2.1.300・permissionMode default）では、guard が ask を返しても承認画面が出ずに実行されると分かった（auto mode の対話セッションと、非対話の 3 モードでは承認が求められた。手動テスト No.1 の実結果） | 本計画の前提（auto mode）は成り立つので進める。ただし、DANGER_OK=1 の ask 化と外部送信の ask は、この条件のセッションでは効かない。手動テスト No.3・No.4 は auto mode で行う。原因（版・モード・セッション固有のどれか）の切り分けと Claude Code への報告は、本イシューの範囲外としてユーザーに引き継ぐ（I146 の手動テストの「gh pr 系が止まらない」も同じ現象の可能性が高い） |
| R8 | `\bdd\b`（437 行目）が `dd` という単語にも反応する止めすぎ | 本計画の範囲外（イシューのスコープ外）。気づいた点として記録する |

## 9. 承認ポイント
- [ ] 計画内容（4 章の変更点・3 章の影響範囲）
- [ ] 判定を 3 種類（常に止める／危険操作＝DANGER_OK=1 で人の確認／外部送信＝人の確認）に分ける設計
- [ ] イシューからの範囲の変更 2 点: ①`rm -rf` の判定をトークン単位にし、grep やヒアドキュメントへの誤反応も直す（イシューでは「含まない」だった。本セッションで 2 回起きたため含める）②実行ファイルの中身の判定から、ホストの bash スクリプトと `scripts/claude/` を外す（テストスクリプトと guard 自身が判定パターンを入力データとして含むため）
- [ ] Danger Ops: 無（権限設定とフックの変更のみ）
- [ ] テスト計画（自動 TC-01〜TC-12・手動 No.1〜No.4）
- [ ] マージ順（I146 の後）と作業場所（primary・例外）

## レビュー結果
- [20261016_1621 判定: ✅ 完了](../../reviews/I174_plan_review_20261016_1621.md)
