# 計画書 I081: Bash 実行作法を規約化（単体コマンド徹底・複合/パイプ禁止の明文化・未コミットファイルへの checkout/restore をフック防止）

## 基本情報
- **計画書ID**: plan_I081
- **関連イシュー**: #161
- **Draft PR**: #163（`feature/I081-bash-exec-hygiene-guard` → develop）
- **作成根拠資料**: docs/issues/open/I081.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I081_review.md
- **作成日**: 2026-06-28

## 1. 背景/目的
I079 retro の予防処置 P2・P4 を集約する。2 つの根本課題に対処する。

1. **承諾プロンプト多発**: `.claude/settings.json` の allow は単体コマンド形（例 `git push -u origin *`・`bash scripts/claude/*`）で定義されている。エージェントが `| tail`・`; echo "exit=$?"`・`&&`・inline heredoc で**複合化**すると、コマンド全体がどの単一 allow にも一致せず広い `ask` に落ちて毎回プロンプトになる。
2. **未コミット変更の消失**: 一時変更の取り消しに `git checkout/restore <file>` を使うと、同ファイルの未コミット変更が HEAD に戻され**消失**する（I079 でフック実装を一度失った）。

根本原因は、エージェントのシェル実行作法が **canonical なルール（runbook）として明文化されておらず**、個人記憶（feedback メモ）依存で生成時に抑止できていなかったこと。本イシューでこれを runbook・レビュー gate へ昇格し、加えて checkout のデータ消失のみフックで機械防止する。

### 調査結果
- **環境前提**: `python3`（既存フックが依存）・`git` ともに本セッションで使用済みで存在自明。アプリコード（backend/frontend/DB）変更なしのため pytest/eslint ベースライン・pip-audit/npm audit は非該当。
- **対象ファイルの実在確認**（全て存在）: `docs/runbooks/common-commands.md`・`docs/runbooks/danger-ops.md`・`.claude/review-agents/code-reviewer.md`・`.claude/review-agents/plan-reviewer.md`・`scripts/claude/hooks/pretooluse_guard.py`。
- **既存フック構造**（`pretooluse_guard.py`、I079 案D 実装済み・develop マージ済み 1f925d9）:
  - `main()` は `tool_name in ("Edit","Write")` → `_check_edit_write`、`tool_name == "Bash"` → 危険 bash 判定。
  - Bash 経路は `danger_ok = raw.lstrip().startswith("DANGER_OK=1 ")` を見て、`if not danger_ok:` ブロック内で force push / `reset --hard` / `docker compose down -v` / `rm -rf` / 破壊的 SQL を `_block`（`exit 2`）。
  - `_block(msg, raw)` が stderr 出力＋`sys.exit(2)`。`_norm` で空白正規化。
  - **checkout/restore の判定は現状なし**（本イシューで追加）。
- **`git status --porcelain` の形式**: 各行 2 文字 `XY`。X=index 列、Y=ワークツリー列、`??`=untracked。**ワークツリー変更**は `Y != ' '` かつ `XY != '??'`。`git checkout/restore <file>` が消すのはこのワークツリー変更分。
- **既存テスト規約**（`scripts/claude/tests/*.sh`）: `set -uo pipefail` → `REPO_ROOT="$(git rev-parse --show-toplevel)"` → `pass/fail` カウンタ＋`ck` ヘルパ。**必ず `bash scripts/claude/tests/<name>.sh` で実行**（対話シェルの ugrep ラッパー回避）。本イシューのフックテストは grep 非依存（exit code 判定）だが規約に合わせる。
- **本計画自体での規約違反（記録）**: 本計画作成中、環境確認に `which python3 git; git --version` と `bash ...; echo "exit=$?"` 相当の複合コマンドを生成しプロンプトを誘発した。これは本イシューが撲滅対象とする当のアンチパターンであり、runbook 明文化＋レビュー gate の必要性を裏づける具体例。

### スコープ外の関連事項（記録のみ・本計画では触らない）
- `ask: git push *` が allow `git push -u origin *` を precedence（ask>allow）で shadow し、安全な feature push でも毎回プロンプトになる件は **I080 の対応範囲**（I080 が `ask` から `git push *` を撤去予定）。本計画では `.claude/settings.json` の permissions を変更しない。

## 2. 受け入れ条件（イシュー AC を継承）
- [ ] `common-commands.md` に「単体 allowlist コマンドで実行・複合/パイプ/inline heredoc 禁止・`; echo "exit=$?"` を付けない・閲覧は Read」が明記されている
- [ ] 「未コミット変更があるファイルの一時取り消しに `git checkout/restore` を使わない（Edit で戻す）」が `danger-ops.md` に明記され、`common-commands.md` から相互参照されている
- [ ] `code-reviewer.md` / `plan-reviewer.md` に上記2点の gate 観点が追加されている
- [ ] `common-commands.md` の実行作法が「**原則**単体・検証目的の複合は例外許容」と明記（完全禁止でない）
- [ ] `pretooluse_guard.py` が「未コミット変更（unstaged worktree 変更）があるファイルへの `git checkout/restore <file>`」を `DANGER_OK=1` 無しで `exit 2` block する。untracked・`git restore --staged <file>`（index のみ）・clean ファイル・ブランチ切替（`git checkout <branch>`・`-b`・`git switch`）は素通し。全体 pathspec（`.`）はいずれか dirty なら block。決定論シェルテストで dirty→exit2 / clean→exit0 の両方を確認済み（false-green でない）
- [ ] 追記文言中にイシュー番号（`I079`・`I080` 等）が含まれていない（一般形であることを機械的に確認）

## 3. 影響範囲
- Backend: なし / Frontend: なし / DB: なし
- Config/Infra:
  - `docs/runbooks/common-commands.md`（実行作法の明文化）
  - `docs/runbooks/danger-ops.md`（checkout/restore データ消失注意）
  - `.claude/review-agents/code-reviewer.md`・`.claude/review-agents/plan-reviewer.md`（gate 観点追加）
  - `scripts/claude/hooks/pretooluse_guard.py`（Bash 経路に checkout/restore データ消失防止を追加）
  - `scripts/claude/tests/test_pretooluse_checkout_guard.sh`（**新規**・決定論テスト）

## 4. 変更点一覧

### 4-1. `docs/runbooks/common-commands.md`（新規セクション追記）
末尾付近に「## Bash 実行作法（allowlist 単体コマンド）」を追記:
- Bash は allowlist 済みの**単体コマンド**で実行する。`|` / `;` / `&&` / `2>&1 | tail` / inline heredoc（`<<EOF`）で複数コマンドを束ねない。
- 終了コードは出力で判断し `; echo "exit=$?"` を付けない。
- ファイル閲覧は **Read ツール**を使い、`sed` / `cat` / `head` で束ね読みしない。
- **原則であり完全禁止ではない**: 検証目的で複合/パイプが本質的に必要な場合のみ許容し、その際プロンプトが出ることを受容する（例外明示）。
- 取り消しに関する1行の相互参照: 「未コミット変更があるファイルの一時取り消しは `git checkout/restore` を使わない → `danger-ops.md` 参照」。

### 4-2. `docs/runbooks/danger-ops.md`（Git 項目に追記）
`## 例` の Git 行に注記を追加し、本文に1段落を追加:
- 「作業ツリーに**未コミット変更があるファイル**の一時変更を取り消す際、`git checkout/restore <file>` を使わない（未コミット分も HEAD に戻り消える）。一時変更は **Edit で元に戻す**。clean なファイルの revert やブランチ切替は通常どおり可。どうしても必要な場合のみ `DANGER_OK=1` を前置する（フックが未コミット時はブロックする）。」

### 4-3. `.claude/review-agents/code-reviewer.md`（「ベストプラクティス」観点に2項追加）
既存の「指示ファイルの分岐パリティ」項の近傍に追記:
- **コマンド衛生**: 検証/手順コマンドが複合化（`;`・`&&`・パイプ・inline heredoc）され、allowlist 単体形に置換可能なのに束ねられていないか（該当時 Low〜Medium）。
- **破壊的取り消し**: 未コミット変更があるファイルへの `git checkout/restore <file>` による取り消しが計画/手順に含まれていないか（データ消失リスク。該当時 High）。

### 4-4. `.claude/review-agents/plan-reviewer.md`（「ベストプラクティス」観点に2項追加）
- **コマンド衛生**: 計画/手順の検証コマンドが複合化され単体形に割れるのに束ねられていないか。
- **破壊的取り消し**: 計画/手順に未コミット変更ファイルへの `git checkout/restore <file>` が含まれていないか（Edit で戻す方針か）。

### 4-5. `scripts/claude/hooks/pretooluse_guard.py`（Bash 経路に判定追加）
`import shlex` を追加し、モジュール先頭付近にヘルパを追加。`main()` の `if not danger_ok:` ブロック内（既存 `rm -rf` 判定の後）に判定を追加する。

> **トークナイズは `shlex.split()`（クォート対応）で行う**。素朴な `str.split()` だと `git checkout -- "my file.py"` のような**空白を含むパスを取りこぼし黙って素通し（データ消失）**するため。データ消失を機械防止する決定論ゲートに沈黙の穴を残さない（理想状態基準の判断）。

```python
_SHELL_OPS = ("&&", "||", "|", ";")

def _segments(cmd: str) -> list:
    """コマンドをクォート対応で分割し、shell 演算子区切りごとのトークン列リストを返す。
    クォート不整合（実シェルでもエラー）の場合は素朴分割にフォールバック。"""
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()
    segs, seg = [], []
    for t in toks:
        if t in _SHELL_OPS:
            if seg:
                segs.append(seg); seg = []
        else:
            seg.append(t)
    if seg:
        segs.append(seg)
    return segs

def _worktree_dirty(path: str) -> bool:
    """<path>（'.' 可）にワークツリー変更があれば True。untracked('??')は除外。
    git 不在/失敗は False（fail-open＝既存方針と同じ）。"""
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--", path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return False
        for line in r.stdout.splitlines():
            if len(line) >= 2 and line[:2] != "??" and line[1] != " ":
                return True
        return False
    except Exception:
        return False

def _revert_targets(sub: str, args: list) -> list:
    """checkout/restore のうちワークツリーを破壊し得る pathspec を返す。破壊しない形は []。"""
    if sub == "checkout" and any(a in ("-b", "-B", "--orphan") for a in args):
        return []  # ブランチ作成
    if sub == "restore":
        has_staged = ("--staged" in args) or ("-S" in args)
        has_worktree = ("--worktree" in args) or ("-W" in args)
        if has_staged and not has_worktree:
            return []  # index のみ・ワークツリー非破壊
    cand = args[args.index("--") + 1:] if "--" in args else args
    return [a for a in cand if not a.startswith("-")]

def _git_revert_target_on_dirty(cmd: str):
    """複合コマンドを分割し、git checkout/restore の pathspec が dirty なら最初の該当パスを返す。"""
    for toks in _segments(cmd):
        if "git" not in toks:
            continue
        rest = toks[toks.index("git") + 1:]
        if not rest or rest[0] not in ("checkout", "restore"):
            continue
        for t in _revert_targets(rest[0], rest[1:]):
            if _worktree_dirty(t):
                return t
    return None
```

`main()` の `if not danger_ok:` 内（`rm -rf` ブロック判定の直後）:
```python
        # git checkout/restore on a file with uncommitted changes would discard them
        target = _git_revert_target_on_dirty(cmd)
        if target:
            _block(
                f"git checkout/restore would discard uncommitted changes in '{target}'. "
                f"Edit で戻すか、どうしても必要なら DANGER_OK=1 を前置してください。",
                raw,
            )
```

## 5. 修正アプローチ
**実行作法の canonical 化（runbook）＋レビュー gate（review-agents）＋データ消失の機械防止（フック）** の3層で対処する。

- **複合/パイプは機械ブロックしない**（正当用途があり強制ブロックは逆効果。retro で評価済み）。runbook 明文化＋レビュー gate で抑止し、生成時の作法は規約に従う。
- **checkout/restore のデータ消失のみフックで機械防止**する。判定は「コマンドを shell 区切りで分割 → `git checkout`/`git restore` セグメントの pathspec を抽出 → 各 pathspec が `git status --porcelain` のワークツリー列で変更ありなら `exit 2` block」。
  - ブランチ切替（`git checkout <branch>`・`-b`・`git switch`）は、pathspec が実在 dirty パスに解決しないため自然に素通し（rule (b) を `_worktree_dirty` で実装）。
  - `git restore --staged <file>`（index のみ）はワークツリー非破壊なので `_revert_targets` で除外。
  - 全体 pathspec（`.`）は `_worktree_dirty(".")` がワークツリー全体を見て、いずれか dirty なら block。
  - `DANGER_OK=1` 前置で迂回可（既存 danger_ok 機構を流用）。
- 既存の危険 bash ハードブロック（force push 等）は不変。

### 設計上の既知の限界
- 空白を含むパス（`"my file.py"`）は **`shlex.split()` で正しくトークン化されるため検出漏れしない**（TC-G10 で担保）。素朴分割の沈黙の穴は解消済み。
- `git restore --source HEAD~1 file`（`--source` がスペース区切り）の `HEAD~1` は非フラグ語として候補に入るが、`git status --porcelain -- HEAD~1` が空を返すため誤 block しない（安全）。
- クォート不整合のコマンド（実シェルでもエラーで非実行）は `shlex` が ValueError → 素朴分割にフォールバック。実害なし。

## 6. 実装手順
- **ステップ1**: `pretooluse_guard.py` にヘルパ（`_worktree_dirty`・`_revert_targets`・`_git_revert_target_on_dirty`）と `main()` 内判定を追加。→ TC-G1〜G8 参照
- **ステップ2**: `scripts/claude/tests/test_pretooluse_checkout_guard.sh` を新規作成（temp git repo を立てて dirty/clean/branch/staged/untracked/`.`/DANGER_OK を網羅）。false-green 注入を実施。→ TC-G1〜G8・TC-G-FALSEGREEN 参照
- **ステップ3**: `common-commands.md`・`danger-ops.md` に実行作法・取り消し注意を追記（相互参照リンクを張る）。→ TC-D1〜D3 参照
- **ステップ4**: `code-reviewer.md`・`plan-reviewer.md` に gate 観点を追加。→ TC-D4 参照
- **ステップ5**: 追記文言にイシュー番号が含まれないことを確認。→ TC-D5 参照

依存: ステップ2はステップ1完了が前提。ステップ3〜5は独立（並行可）。

## 7. テスト計画
- 自動（決定論・フック単体）: `I081_auto_test.md` の TC-G1〜G8（temp repo での block/素通し）・TC-G-FALSEGREEN（判定を外すと dirty でも素通しになる裏取り）・TC-G9（危険 bash `exit 2` 回帰維持）・TC-D1〜D5（runbook/review-agent の文言 grep・イシュー番号不在）。
- 手動（統合・実セッション）: `I081_manual_test.md`（実リポジトリで dirty ファイルへの `git checkout` が実際にブロックされ、clean/ブランチ切替は通ることの確認）。

## 8. ロールバック
`pretooluse_guard.py` の追加ヘルパ＋判定ブロックを除去し、新規テストスクリプトを削除。runbook・review-agent の追記分を revert。DB・サービス影響なし、再起動不要。

## 9. Risk & 回避策
| Risk | 影響 | 回避策 |
|------|------|--------|
| checkout 判定が**ブランチ切替を誤 block** し通常 revert/切替を妨げる | 中 | pathspec を `git status --porcelain -- <arg>` で実在 dirty 判定。ブランチ名は空を返し素通し。TC-G2/G6（`-b`・`<branch>` 切替が exit 0）で回帰防止 |
| 判定が**常に block**（false-green の逆＝過剰ブロック）になる | 中 | 同一 `git checkout -- file` を clean→exit0 / dirty→exit2 の対で検証（TC-G1 と G3）。判定が dirty 条件依存であることを裏取り |
| 判定が**効かず**未コミットを消失（false-green） | 高 | TC-G-FALSEGREEN: 判定を一時無効化すると dirty でも exit 0 になることを確認してから本実装に戻す |
| `git status` 実行のオーバーヘッド | 低 | subprocess は checkout/restore セグメント検出時のみ実行。他コマンドは文字列処理のみ |
| 複合/パイプを runbook で禁じても生成時にすり抜ける | 中 | 機械ブロックは非採用（正当用途）。レビュー gate（4-3/4-4）で人手検知＋生成時は規約遵守。完全防止はしない設計判断（イシュー確定） |

## セキュリティ・要件適合チェック結果
- **要件適合性**: イシュー AC の範囲内。仕様追加なし。マルチテナント/ステータス遷移/業務ロジックは非該当（アプリロジック変更なし・開発ハーネス）。
- **セキュリティ**: アプリのコード変更なし＝OWASP/入力バリデーション/認証認可への影響なし。本変更は開発ハーネスの規約・ガード。フック追加は**防御的強化**（データ消失防止）で、fail-open（git 不在時 False）により正規操作を妨げない。依存追加なし → pip-audit/npm audit 非該当。入力（フックの stdin JSON・コマンド文字列）は既存同様 `subprocess` を**リスト引数**で呼び shell=False のためコマンドインジェクションなし。「セキュリティ影響なし／ハーネスのガード強化」。
- **テスト計画**: バグ修正（I079 のデータ消失再発防止）に該当 → 再発防止テスト（TC-G3/G5）を用意。否定・回帰系（TC-G-FALSEGREEN・TC-D5）は失敗注入で NG 確認。
- **P3/P5/P8（データ整合性/運用/コスト）**: DB・外部API・非同期なし → 影響なし。インフラ追加なし。
- **P6（性能・UX）**: UI なし・データ量/外部API懸念なし → 影響なし。
- **P9（プライバシー）**: 個人情報・未成年・テナントデータを扱わない → 影響なし。
- **設計品質**: ヘルパ分割で責務分離。設定値ハードコードなし（パターンは仕様上の定数）。例外は fail-open で握り（`except Exception: return False`）— 既存フックの方針と一貫（git 不在環境でフックが落ちないため意図的）。

## 設計判断の明示
| 設計判断 | 出所 |
|----------|------|
| 複合/パイプは機械ブロックせず runbook＋レビュー gate で担保 | イシュー明記（grill-me 確定・スコープ「含まない」） |
| checkout/restore のデータ消失のみフックで `exit 2` block・`DANGER_OK=1` で迂回 | イシュー明記（grill-me 確定） |
| 検出範囲＝unstaged worktree 変更のみ（untracked・`restore --staged` は素通し） | イシュー明記（grill-me 第2回確定） |
| checkout 判別＝`--` 後ろを pathspec／`--` 無しは実在 dirty パスのみ復元扱い | イシュー明記（grill-me 第2回確定）。`_worktree_dirty` で rule (b) を実装 |
| 全体 pathspec（`.`）はいずれか dirty なら block | イシュー明記（grill-me 第2回確定） |
| テストは temp git repo を立てる決定論シェルテスト | イシュー明記（grill-me 第2回確定）＋既存テスト規約に準拠 |
| ヘルパ関数4分割（`_segments`/`_worktree_dirty`/`_revert_targets`/`_git_revert_target_on_dirty`）の構成 | 仮定で決めた（既存フックの `_block`/`_norm` 等の小関数分割に倣う） |
| トークナイズを `shlex.split()`（クォート対応）で行い空白パスの検出漏れを根治 | **理想状態基準で決定**（決定論ゲートに沈黙の穴を残さない）。素朴分割の許容案を棄却 |
| block メッセージ文言 | 仮定で決めた（実装時に簡潔化可） |
| settings.json（push ポリシー）は触らない | イシュー明記（スコープ「含まない」＝I080 の範疇） |

## レビュー結果
- [20260628_0311 判定: ✅ 完了](../../reviews/I081_plan_review_20260628_0311.md)
