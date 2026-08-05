# I146 計画書: 外部コード寄稿の受付方針明示と cross-repo PR ゲート（do 層＋gate 3 層）

## 基本情報
- **計画書ID**: plan_I146
- **関連イシュー**: #260
- **Draft PR**: #261
- **作成根拠資料**: docs/issues/open/I146.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I146_review.md
- **作成日**: 2026-08-04

---

## 1. 背景/目的

**背景**: 2026-08-04、I138(#247) の close 作業中に PR #257 が「out-of-date with the base branch」と E2E 失敗を示した。調査の結果、#257 は自前の PR ではなく、public リポジトリの issue #247 を第三者（@Dodothereal）が運用する自律 AI エージェントが拾い、fork から出してきた未依頼の外部寄稿だった。方針コメントを付けて close 済み。

**目的**:
1. 外部からのコード寄稿に対する受付方針を明文化し、寄稿者側にも自分たち側にも即座に判断がつく状態にする（do 層）。
2. 自前でない PR（cross-repo PR）を自分たちのクローズ・レビュー・マージ手順に載せてしまう事故を、決定論的に止める（gate 層）。

---

## 2. 調査結果

### 2-1. 原因の概要（平易な説明）

このリポジトリは公開されているため、イシューを見た第三者（特に自律 AI エージェント）が fork から PR を送ってくることがある。ところが (a) 受け付ける・受け付けないの方針がどこにも書かれておらず、(b) ハーネス側も「PR は自分たちが出したもの」という前提で組まれているため、外部の PR がそのまま自分たちの作業手順に流れ込んでしまう。

### 2-2. 詳細な原因分析

**発生の流れ（実際の経緯）**

1. 2026-07-19 07:55 UTC: issue #247 (I138) を公開で起票（label: documentation / track:harness）。
2. 2026-07-23 05:53 UTC: @Dodothereal の fork から PR #257 が作成される。head=`Dodothereal:fix/247-i138-plan-writing-rules` / base=`develop`。
3. 同時刻: E2E ワークフローは `action_required`（fork PR の GitHub 既定＝手動承認待ち）で停止。CI 結果が未確定だったため、失敗として可視化されなかった。
4. 2026-08-04 11:13:52 UTC: クローズ作業の一環としてワークフロー実行を承認（triggering_actor=`oshui0404`・attempt 2）。
5. 2026-08-04 11:14:14 UTC: PR #249（I134）が develop にマージされ、#257 が `BEHIND` になる。
6. 2026-08-04 11:16:44 UTC: E2E が `E2E_TEST_PASSWORD is not set.`（`e2e/global-setup.ts:14`）で失敗。fork PR には repository secrets が渡らないため。
7. 「out-of-date」と「E2E 失敗」の 2 症状として顕在化し、外部 PR であることに気づくまで、ブランチ追従案の検討まで進んだ。

**技術的背景**

- `.github/workflows/e2e.yml` は `secrets.E2E_TEST_PASSWORD` を参照している（L29・L46）。fork からの `pull_request` イベントでは secrets が空になるため、この PR は**何をしても CI がグリーンにならない**。
- `mergeStateStatus=BEHIND` は base が進んだだけで、close する PR に追従する意味はない。
- Actions の実行承認は GitHub UI 上の操作であり、ハーネス（スクリプト・hook）を経由しないため捕捉できない。

**根本原因（コードレベル）**

| # | 箇所 | 問題 |
|---|------|------|
| 1 | リポジトリルート | `CONTRIBUTING.md` が存在せず、受付方針が未記載。`SECURITY.md` も無く脆弱性の報告経路もない |
| 2 | `docs/runbooks/workflow.md` | `grep -n "外部\|CONTRIBUTING\|fork"` でヒット 0。外部 PR 発見時の扱いが未定義 |
| 3 | `scripts/claude/pr-base-sync.sh` | `mergeStateStatus` のみで分岐し、head リポジトリを検証しない。cross-repo PR に対しても `git merge origin/<base>` を実行しようとする（L73-83・L86-103） |
| 4 | `scripts/claude/hooks/pretooluse_guard.py` | `gh pr` 系コマンドの判定が存在しない。`gh pr merge` は素通し（実測: exit 0） |
| 5 | `.claude/settings.json` | PreToolUse の matcher が `Edit\|Write\|MultiEdit\|NotebookEdit` と `Bash` のみ。**MCP 経由の GitHub 操作（`mcp__github__merge_pull_request` 等）は hook を通らない**（L143-162） |
| 6 | `.claude/settings.json` | `Bash(gh pr edit *)` が allow 済み（L53）。外部 PR への `gh pr edit` が無確認で通る |

### 2-3. 環境前提確認（全イシュー必須）

| 確認項目 | コマンド | 実測結果 |
|---|---|---|
| 実行環境（ホスト/コンテナ） | `test -f /.dockerenv` | exit 1 = **ホスト**。本イシューの全作業はホストで実施する |
| Python | `python3 --version` | Python 3.12.3（hook 実行系） |
| GitHub CLI | `gh --version` | gh 2.88.1（2026-03-12） |
| 出力先 | `docs/plans/open` / `docs/tests/open` / `docs/reviews/open` | 既存ディレクトリ・書き込み可（本計画書ほか生成済み） |

コンテナ・DB・フロントエンドのビルドは本イシューの手順に含まれないため、`docker compose ps` 等の確認は不要。

### 2-4. スパイク実証（未知リスクの先行検証）

**(1) 稼働中セッションで実証可能なもの — 実証済み**

| # | 検証した前提 | 方法 | 結果 |
|---|---|---|---|
| S1 | fork 判定を 1 フィールドで取得できる | `gh pr view 257 --json isCrossRepository -q .isCrossRepository` | `true`（外部 PR）✅ |
| S2 | 自前 PR では false になる | `gh pr view 256 --json isCrossRepository -q .isCrossRepository` | `false` ✅ |
| S3 | 解決不能な PR 番号では取得が失敗する（fail-closed 経路の実在） | `gh pr view 999999 --json isCrossRepository` | stderr に GraphQL エラー・**exit 1** ✅ |
| S4 | 現状の guard は `gh pr merge` を素通しする（TDD Red のベースライン） | guard へ stdin JSON を投入 | **exit 0**（素通し）✅ |
| S5 | 既存テストのベースライン | `bash scripts/claude/tests/test_pr_base_sync.sh` | `RESULT: OK (16/16 cases, 23 assertions)` ✅ |
| S6 | 既存テストのベースライン | `bash scripts/claude/tests/test_pretooluse_push_guard.sh` | `pass=87 fail=0` ✅ |
| S7 | 脆弱性の非公開報告の現状 | `gh api repos/osushi0404-dev/study-app-multitenant/private-vulnerability-reporting` | `{"enabled":false}` ✅ |
| S8 | develop のブランチ保護・ルールセット | `gh api .../branches/develop/protection` / `.../rules/branches/develop` | 404 / `[]` = **保護なし**。BEHIND はマージ阻止要因ではない ✅ |
| S9 | MCP GitHub ツールの `tool_input` キー名（plan review Blocker） | 対象 3 ツールの JSON Schema を実取得して確認 | **`pull_number`（スネークケース）・`owner`・`repo`**。`create_pull_request_review` は `event`（`APPROVE`/`REQUEST_CHANGES`/`COMMENT`）。3 ツールとも `owner`/`repo`/`pull_number` が required ✅ |
| S10 | 1 回の照会で head リポジトリ名も取れるか | `gh pr view 257 --json isCrossRepository,headRepositoryOwner,headRepository` | 3 フィールドを同時取得できる（照会回数は 1 回のまま）✅ |

→ 判定手段（`isCrossRepository`）は成立。origin の owner/name を引いて文字列比較する設計は不要。
→ S9 により、MCP 経路のキー名は**キャメルケースではなくスネークケース**であることが確定した（当初案の `pullNumber` は誤り）。
→ S10 により、ask 文言に head リポジトリ名を含めても**照会回数は増えない**（同一クエリでフィールドを増やすだけ）。

**(2) 稼働中セッションでは実証不能なもの — 実装ステップ 1 のゲートに前倒し**

- **hook の実挙動**（`_block` の exit 2 が実際にツール実行を止めるか／`_ask` が実際にプロンプト化するか）は、稼働中セッションでは権限モード・フックのロード状態を区別できないため実証できない。
- **MCP ツール呼び出し時に hook へ渡る `tool_input` の実データ**も同様に実証不能である。S9 でツールのスキーマ（`owner`/`repo`/`pull_number` が required）は確定したが、ハーネスがそのまま hook に渡すことの実地確認は新規セッションでしか行えない。
- 対応: **手動テスト No.1・No.2・No.11 を「プレーン default 新規セッション」で実施**し、**実装ステップ 1 完了直後のゲート**として扱う。不成立なら設計をやり直す（ステップ 2 以降に進まない）。No.11 は MCP 経路（`mcp__github__update_pull_request_branch`）で ask が出ることの確認である。
- 判定ロジック自体は決定論テスト（TC-03・TC-04）で in-session に担保する。キー名は S9 の実測値（スネークケース）をテストと実装の両方で使い、**取得できなかった場合は素通しさせず ask に降格**することで、キー名の想定違いが黙って穴になることを防ぐ。

### 2-5. 既存テスト・lint のベースライン

- `test_pr_base_sync.sh`: 16/16 cases・23 assertions PASS（S5）
- `test_pretooluse_push_guard.sh`: pass=87 / fail=0（S6）
- 既存の壊れたテストは無し。backend/frontend のコード変更が無いため flake8 / eslint / pytest / npm test の計測は対象外（**lint 影響なし**）。

### 2-6. 参照先実在性の確認

本計画で新規参照するパスの実在性:

| パス | 状態 |
|---|---|
| `scripts/claude/pr-base-sync.sh` | 実在（103 行） |
| `scripts/claude/hooks/pretooluse_guard.py` | 実在（523 行） |
| `scripts/claude/tests/test_pr_base_sync.sh` | 実在（131 行） |
| `scripts/claude/tests/test_pretooluse_push_guard.sh` | 実在（188 行・新規テストの雛形） |
| `.claude/skills/close/SKILL.md` | 実在（step 0 が L15-26） |
| `.github/pull_request_template.md` | 実在 |
| `docs/runbooks/workflow.md` | 実在（`## 外部（fork）からの PR の扱い` は新規追加） |
| `CONTRIBUTING.md` / `SECURITY.md` | **不在（本イシューで新規作成）** |

---

## 3. 受け入れ条件

イシュー #260 の受け入れ条件をそのまま採用し、MCP 経路の追加分（AC-9・AC-10）を加える。

| # | 条件 | 検証 |
|---|------|------|
| AC-1 | ルートに `CONTRIBUTING.md` があり、(a) コードの寄稿（PR）を受け付けない方針と理由、(b) イシューは受け付けるが対応を約束しない旨、(c) 脆弱性は `SECURITY.md` へ、が英語と日本語の両方で記載されている | TC-06 |
| AC-2 | ルートに `SECURITY.md` があり、GitHub の Private vulnerability reporting へ誘導している（メールアドレスの記載がない） | TC-06 |
| AC-3 | リポジトリの Private vulnerability reporting が有効である | TC-07 |
| AC-4 | `.github/pull_request_template.md` の冒頭に、外部からの PR を受け付けていない旨と `CONTRIBUTING.md` へのリンクが 1 行で追加されている（既存項目は無改変） | TC-06 |
| AC-5 | `pr-base-sync.sh` が cross-repo PR に対して exit 1 で STOP する（sync / final 両モード） | TC-01（T17・T18） |
| AC-6 | `isCrossRepository` の取得失敗・空値・想定外値でも exit 1 で STOP する（fail-closed） | TC-01（T19・T20・T21） |
| AC-7 | 自前 PR では `pr-base-sync.sh` の従来の挙動が変わらない | TC-01（T1〜T16 が従来どおりの終了コード） |
| AC-8 | `pretooluse_guard.py` が cross-repo PR への `gh pr merge` を block（exit 2）、`gh pr ready` / `gh pr edit` / `gh pr review --approve` を ask、read-only・`close`・`comment`・`review --comment` を素通しする | TC-03（G1〜G12） |
| AC-9 | `pretooluse_guard.py` が MCP 経由の `mcp__github__merge_pull_request` を block、`mcp__github__update_pull_request_branch` / `mcp__github__create_pull_request_review`（approve）を ask する | TC-03（G13〜G16） |
| AC-10 | `.claude/settings.json` の PreToolUse matcher に上記 MCP ツール名が登録されている | TC-06 |
| AC-11 | `gh` 照会失敗・タイムアウト時に block ではなく ask に降格する | TC-03（G17） |
| AC-12 | 自前 PR に対する `gh pr` / MCP 操作の挙動を一切変えない（素通し） | TC-03（G18〜G20） |
| AC-13 | `.claude/skills/close/SKILL.md` step 0 に `isCrossRepository` の確認と `true` 時の STOP 手順が記載されている | TC-06 |
| AC-14 | 外部 PR 発見時の扱いが `docs/runbooks/workflow.md` に記載されている | TC-06 |
| AC-15 | 両テストが全 PASS し、既存の push guard テストも回帰しない | TC-01・TC-03・TC-08 |
| AC-16 | 否定・回帰系 TC が false-green でない（失敗条件注入で NG になる） | TC-02・TC-04 |
| AC-17 | MCP 経路で `pull_number` が取得できない場合、照会せずに ask へ降格する（別の PR を検査して素通しさせない） | TC-03（G23） |
| AC-18 | 対象外の MCP ツール（例: `mcp__github__get_pull_request`）は素通しし、`gh` 照会も行わない | TC-03（G24） |

---

## 4. 影響範囲

- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**:
  - `.claude/settings.json`（PreToolUse matcher に MCP GitHub ツールを追加）
  - `.github/pull_request_template.md`（1 行追加）
  - GitHub リポジトリ設定: Private vulnerability reporting の有効化（**ユーザー承認が必要**・`gh api -X DELETE` で取り消し可）
- **Harness**:
  - `scripts/claude/pr-base-sync.sh`（/close step 0・step 5.5 の挙動）
  - `scripts/claude/hooks/pretooluse_guard.py`（全 Bash 実行＋対象 MCP 呼び出しの PreToolUse 判定）
  - `.claude/skills/close/SKILL.md`（step 0）
  - `docs/runbooks/workflow.md`（新規セクション）
  - `CONTRIBUTING.md` / `SECURITY.md`（新規）
- **テスト**:
  - `scripts/claude/tests/test_pr_base_sync.sh`（スタブ拡張＋T17〜T21）
  - `scripts/claude/tests/test_pretooluse_gh_pr_guard.sh`（新規）
- **依存関係ファイル**: `requirements*.txt` / `package*.json` の変更は**なし**（Dockerfile・docker-compose.yml への波及なし）

---

## 5. 変更点一覧

| # | ファイル | 変更内容 |
|---|---|---|
| 5-1 | `scripts/claude/hooks/pretooluse_guard.py` | cross-repo PR 判定（`_gh_pr_target` / `_mcp_pr_target` / `_pr_is_cross_repo`）と block / ask 分岐を追加 |
| 5-2 | `.claude/settings.json` | PreToolUse に MCP GitHub ツール用の matcher を追加 |
| 5-3 | `scripts/claude/tests/test_pretooluse_gh_pr_guard.sh` | 新規。G1〜G20＋false-green 注入 |
| 5-4 | `scripts/claude/pr-base-sync.sh` | cross-repo チェックを MODE 分岐前に追加 |
| 5-5 | `scripts/claude/tests/test_pr_base_sync.sh` | `gh` スタブに `isCrossRepository` 分岐を追加＋T17〜T21 |
| 5-6 | `.claude/skills/close/SKILL.md` | step 0 に cross-repo 確認を追加 |
| 5-7 | `CONTRIBUTING.md`（新規） | 受付方針（英語＋日本語） |
| 5-8 | `SECURITY.md`（新規） | 脆弱性報告の経路 |
| 5-9 | `.github/pull_request_template.md` | 冒頭に 1 行 |
| 5-10 | `docs/runbooks/workflow.md` | 末尾に `## 外部（fork）からの PR の扱い` を追加 |
| 5-11 | GitHub リポジトリ設定 | Private vulnerability reporting を有効化 |

### 5-1. `scripts/claude/hooks/pretooluse_guard.py`

**修正方針**: 「fork 由来の PR に対して、取り込み方向の操作をしようとしたら止める」判定を追加する。判定の単一ソースは `gh pr view <識別子> --json isCrossRepository`。read-only と、外部 PR を断るのに必要な操作（close / comment）は素通しさせる。ネットワーク照会は対象サブコマンドに一致したときだけ行い、それ以外の Bash 実行には一切影響させない。

既存の `_segments`（shlex ベース）を使い、素朴な `str.split()` は新規に持ち込まない。

```python
# --- I146: cross-repo（fork）PR への取り込み系操作の防止 ---
# 判定の単一ソースは `gh pr view <識別子> --json isCrossRepository`。
# block = 不可逆かつ方針上ありえない操作（外部コードが develop に入る）。
# ask   = 取り込み方向だが可逆な操作。close/comment/read-only は素通し
#         （外部 PR を断るのに必要な操作を塞いではならない）。
_GH_PR_BLOCK_VERBS = ("merge",)
_GH_PR_ASK_VERBS = ("ready", "edit")
_GH_PR_APPROVE_FLAGS = ("--approve", "-a")

_MCP_PR_BLOCK_TOOLS = ("mcp__github__merge_pull_request",)
_MCP_PR_ASK_TOOLS = (
    "mcp__github__update_pull_request_branch",
    "mcp__github__create_pull_request_review",
)

_GH_TIMEOUT = 5  # 秒。ハーネスを長く止めない（超過時は ask に降格）


def _pr_is_cross_repo(ident, repo=None):
    """(cross, head) を返す。cross は fork 由来 True / 自前 False / 判定不能 None（＝ask 降格）。
    head は "owner/repo" 形式の head リポジトリ名（取れなければ None）。
    ident が None のときはカレントブランチの PR を解決させる（gh の既定挙動）。
    head も同一クエリで取得するため照会回数は 1 回のまま（S10）。"""
    argv = ["gh", "pr", "view"]
    if ident:
        argv.append(ident)
    if repo:
        argv += ["--repo", repo]
    argv += ["--json", "isCrossRepository,headRepositoryOwner,headRepository"]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=_GH_TIMEOUT)
    except Exception:
        return None, None
    if r.returncode != 0:
        return None, None
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None, None
    v = d.get("isCrossRepository")
    owner = (d.get("headRepositoryOwner") or {}).get("login")
    name = (d.get("headRepository") or {}).get("name")
    head = f"{owner}/{name}" if owner and name else None
    if v is True:
        return True, head
    if v is False:
        return False, head
    return None, head


def _gh_pr_target(cmd: str):
    """`gh pr <verb> [識別子]` を検出して (kind, ident) を返す。非該当は None。
    kind は "block" / "ask"。識別子（番号・URL・ブランチ名）は解釈せず gh へそのまま渡す。"""
    for toks in _segments(cmd):
        if len(toks) < 3 or toks[0] != "gh" or toks[1] != "pr":
            continue
        verb = toks[2]
        rest = toks[3:]
        if verb in _GH_PR_BLOCK_VERBS:
            kind = "block"
        elif verb in _GH_PR_ASK_VERBS:
            kind = "ask"
        elif verb == "review" and any(f in rest for f in _GH_PR_APPROVE_FLAGS):
            kind = "ask"
        else:
            continue  # view/checks/diff/list/close/comment/review --comment は対象外
        ident = next((t for t in rest if not t.startswith("-")), None)
        return kind, ident
    return None


def _mcp_pr_target(tool_name: str, tool_input: dict):
    """対象 MCP ツールなら (kind, ident, repo) を返す。非該当は None。
    create_pull_request_review は event=APPROVE のときのみ対象にする。
    キー名は対象 3 ツールのスキーマ実測値（S9）: owner / repo / pull_number（スネークケース・全て required）。
    別実装の MCP サーバに備えてキャメルケースも読むが、正は snake_case。"""
    if tool_name in _MCP_PR_BLOCK_TOOLS:
        kind = "block"
    elif tool_name in _MCP_PR_ASK_TOOLS:
        if tool_name.endswith("create_pull_request_review") and \
                str(tool_input.get("event", "")).upper() != "APPROVE":
            return None
        kind = "ask"
    else:
        return None
    num = tool_input.get("pull_number")
    if num is None:
        num = tool_input.get("pullNumber")
    owner = tool_input.get("owner")
    repo = tool_input.get("repo")
    ident = str(num) if num is not None else None
    full = f"{owner}/{repo}" if owner and repo else None
    return kind, ident, full


def _guard_cross_repo(kind: str, ident, repo, raw: str, require_ident: bool = False):
    """cross-repo 判定に応じて block / ask / 素通しを決める。判定不能は ask（fail-safe）。
    require_ident=True（MCP 経路）で識別子が取れない場合は照会せず ask する。
    MCP はカレントブランチという概念を持たず、ident=None のまま照会すると
    「別の PR（カレントブランチの PR）を検査して素通しする」誤判定になり得るため。"""
    if require_ident and not ident:
        _ask("対象 PR の番号を特定できませんでした（tool_input に pull_number がない）。"
             "外部（fork）由来の PR でないか確認してください。")
    cross, head = _pr_is_cross_repo(ident, repo)
    label = f"PR {ident}" if ident else "カレントブランチの PR"
    origin = f"（head: {head}）" if head else ""
    if cross is None:
        _ask(f"{label} が自前のものか判定できませんでした（gh 照会失敗/タイムアウト）。"
             f"外部（fork）由来の PR でないか確認してください。")
    if cross is False:
        return  # 自前 PR → 従来どおり素通し
    if kind == "block":
        _block(
            f"{label} は fork（外部リポジトリ）由来です{origin}。外部からのコード寄稿は受け付けていません"
            f"（CONTRIBUTING.md）。マージせず、方針コメント付きで close してください。"
            f"どうしても必要なら DANGER_OK=1 を前置してください。",
            raw,
        )
    _ask(f"{label} は fork（外部リポジトリ）由来です{origin}。取り込み方向の操作になります。"
         f"CONTRIBUTING.md の方針（外部からのコード寄稿は受け付けない）を確認してください。")
```

`main()` への組み込み:

```python
def main():
    data = _load()
    tool_name = data.get("tool_name")
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        ...  # 既存のまま
    # I146: MCP 経由の PR 取り込み操作（Bash を通らない経路）
    if str(tool_name or "").startswith("mcp__github__"):
        t = _mcp_pr_target(tool_name, data.get("tool_input") or {})
        if t:
            _guard_cross_repo(t[0], t[1], t[2], tool_name, require_ident=True)
        sys.exit(0)
    if tool_name != "Bash":
        sys.exit(0)
    ...
    if not danger_ok:
        ...  # 既存の hard-block 群（rm -rf / push / reset --hard / psql …）はそのまま先に評価する
        # I146: cross-repo PR ガード（既存 hard-block の後・_push_is_dynamic の ask より前）
        t = _gh_pr_target(cmd)
        if t:
            _guard_cross_repo(t[0], t[1], None, raw)

        if _push_is_dynamic(cmd):
            ...
```

**配置の根拠**: 既存の hard-block 群より後に置くことで、`gh pr merge ... && rm -rf x` のように danger-op が同居する場合に ask で先食いしない（I083 で確立した順序方針を踏襲）。`if not danger_ok:` の内側に置くため、`DANGER_OK=1` を前置した明示的な操作は従来どおり抜けられる（danger-ops.md の枠組みに合わせる）。

### 5-2. `.claude/settings.json`

**修正方針**: MCP 経由の GitHub 操作は現状 hook を通らない。対象 3 ツールだけを matcher に追加する（他の MCP ツールには影響させない）。

```json
      {
        "matcher": "mcp__github__merge_pull_request|mcp__github__update_pull_request_branch|mcp__github__create_pull_request_review",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/scripts/claude/hooks/pretooluse_guard.py"
          }
        ]
      }
```

### 5-4. `scripts/claude/pr-base-sync.sh`

**修正方針**: PR 番号が確定した直後（`BASE` の取得より前）に cross-repo チェックを置き、fork 由来なら base 追従も CI 待機もせずに STOP する。既存の fail-closed 方針（取得失敗・未知値は STOP）と終了コードの意味（0/1/2）を変えない。

```bash
# I146: cross-repo（fork）PR ガード。MODE 分岐より前＝sync/final 共通で必ず走る。
# 自前でない PR に base 追従・push をしない（fail-closed: 取得失敗・未知値も STOP）。
CROSS=$(gh pr view "$PR_NUM" --json isCrossRepository -q .isCrossRepository) \
  || { echo "⛔ isCrossRepository の取得に失敗しました。STOP してユーザーに報告"; exit 1; }
case "$CROSS" in
  false) ;;   # 自前 PR → 続行
  true)
    echo "⛔ PR #${PR_NUM} は fork（外部リポジトリ）由来です。base 追従・push・CI 対応はしません。"
    echo "   外部からのコード寄稿は受け付けていません（CONTRIBUTING.md）。"
    echo "   方針コメント付きで close してください（docs/runbooks/workflow.md）。"
    exit 1 ;;
  *)
    echo "⛔ isCrossRepository が想定外の値です: '${CROSS}'。STOP してユーザーに報告"; exit 1 ;;
esac
```

（`case` による完全一致で判定する。部分一致だと `true` を含む別値を誤判定し得るため。）

### 5-5. `scripts/claude/tests/test_pr_base_sync.sh`

**修正方針**: 既存の `gh` スタブは未知の照会に対して `*) exit 0`（空出力）を返すため、新しい照会を足すと空値 → fail-closed で **T1〜T16 が全滅する**。スタブに分岐を追加し、値をケースごとに注入できるようにする。

```bash
# gh スタブに追加（mergeStateStatus 分岐より前でも後でもよいが、文字列は排他）
  *isCrossRepository*)
    [ "${GH_FAIL_CROSS:-0}" = "1" ] && exit 1
    echo "${CROSS_VALUE:-false}"
    ;;
```

`run_case` の env 受け渡しに `CROSS_VALUE` / `GH_FAIL_CROSS` を追加する:

```bash
  STATE_FILE="$state_file" CHECKS_FILE="$checks_file" GIT_LOG="$LAST_LOG" \
    MERGE_FAIL="$merge_fail" GH_FAIL="$gh_fail" \
    CROSS_VALUE="${CROSS_VALUE:-false}" GH_FAIL_CROSS="${GH_FAIL_CROSS:-0}" \
    PBS_RETRY_INTERVAL=0 ...
```

追加ケース（呼び出し側で `CROSS_VALUE=true run_case ...` のように前置して注入する）:

```bash
# --- I146: cross-repo ガード ---
CROSS_VALUE=true  run_case "T17 sync cross-repo=STOP"   sync  "CLEAN" "$CHECKS_GREEN" 0 0 3 1
log_not  "merge"                                        "T17 副作用なし（merge が呼ばれない）"
CROSS_VALUE=true  run_case "T18 final cross-repo=STOP"  final "CLEAN" "$CHECKS_GREEN" 0 0 3 1
GH_FAIL_CROSS=1   run_case "T19 sync 照会失敗=STOP"      sync  "CLEAN" "$CHECKS_GREEN" 0 0 3 1
CROSS_VALUE=""    run_case "T20 sync 空値=STOP"          sync  "CLEAN" "$CHECKS_GREEN" 0 0 3 1
CROSS_VALUE=hoge  run_case "T21 sync 想定外値=STOP"      sync  "CLEAN" "$CHECKS_GREEN" 0 0 3 1
```

（`CROSS_VALUE=""` は既定値の `false` に落ちないよう、`run_case` 内では `${CROSS_VALUE-false}`（`:-` ではなく `-`）で受ける。空文字と未設定を区別する。）

### 5-3. `scripts/claude/tests/test_pretooluse_gh_pr_guard.sh`（新規）

**修正方針**: `test_pretooluse_push_guard.sh` と同方式（stdin JSON 投入・exit code / ask JSON で判定・false-green 注入）。実 GitHub に依存させないため `gh` スタブを PATH 先頭に置き、`CROSS_VALUE` で fork/自前を切り替える。

```bash
#!/usr/bin/env bash
# I146: pretooluse_guard.py の cross-repo PR ポリシーを決定論検証する。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/bin"; mkdir -p "$STUB"
cat > "$STUB/gh" <<'EOF'
#!/bin/bash
case "$*" in
  *isCrossRepository*) [ "${GH_FAIL_CROSS:-0}" = "1" ] && exit 1; echo "${CROSS_VALUE:-false}" ;;
  *) exit 0 ;;
esac
EOF
chmod +x "$STUB/gh"

# Bash 用 / MCP 用の stdin JSON をそれぞれ組み立てる（" や ` を含んでも安全にエスケープする）
json()  { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
mjson() { python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":json.loads(sys.argv[2])}))' "$1" "$2"; }

# 判定ヘルパ: ASK は「exit 0 かつ stdout に permissionDecision=ask」。それ以外は exit code をそのまま返す。
_decide() { local out="$1" code="$2"
  if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; then
    echo "ASK"; else echo "$code"; fi; }
# Bash コマンド用（$1=command・$2=guard 省略時は実体）
runj()  { local out code; out=$(json "$1" | PATH="$STUB:$PATH" python3 "${2:-$GUARD}" 2>/dev/null); code=$?;
          _decide "$out" "$code"; }
# MCP ツール用（$1=tool_name・$2=tool_input JSON・$3=guard 省略時は実体）
runm()  { local out code; out=$(mjson "$1" "$2" | PATH="$STUB:$PATH" python3 "${3:-$GUARD}" 2>/dev/null); code=$?;
          _decide "$out" "$code"; }
```

MCP ケースの投入例（キー名は S9 の実測値・スネークケース）:

```bash
MCP_PR='{"owner":"osushi0404-dev","repo":"study-app-multitenant","pull_number":257}'
MCP_APPROVE='{"owner":"osushi0404-dev","repo":"study-app-multitenant","pull_number":257,"body":"x","event":"APPROVE"}'
MCP_NONUM='{"owner":"osushi0404-dev","repo":"study-app-multitenant"}'
CROSS_VALUE=true ck "G13 mcp merge (fork)" 2 "$(runm mcp__github__merge_pull_request "$MCP_PR")"
```

検証ケース（`CROSS_VALUE=true` = 外部 PR / `false` = 自前 PR）:

| # | 入力 | CROSS_VALUE | 期待 |
|---|---|---|---|
| G1 | `gh pr merge 257 --squash` | true | 2（block） |
| G2 | `gh pr merge 257` | false | 0（素通し） |
| G3 | `gh pr ready 257` | true | ASK |
| G4 | `gh pr edit 257 --base develop` | true | ASK |
| G5 | `gh pr review 257 --approve` | true | ASK |
| G6 | `gh pr review 257 --comment --body x` | true | 0（断るのに必要） |
| G7 | `gh pr close 257` | true | 0（断るのに必要） |
| G8 | `gh pr comment 257 --body x` | true | 0 |
| G9 | `gh pr view 257 --json state` | true | 0（read-only） |
| G10 | `gh pr checks 257` | true | 0 |
| G11 | `gh pr merge`（識別子なし） | true | 2 |
| G12 | `gh pr merge https://github.com/o/r/pull/257` | true | 2（URL 形式） |
| G13 | MCP `merge_pull_request` | true | 2 |
| G14 | MCP `update_pull_request_branch` | true | ASK |
| G15 | MCP `create_pull_request_review`(event=APPROVE) | true | ASK |
| G16 | MCP `create_pull_request_review`(event=COMMENT) | true | 0 |
| G17 | `gh pr merge 257`（`GH_FAIL_CROSS=1`） | - | ASK（block しない＝降格） |
| G18 | `gh pr ready 257` | false | 0 |
| G19 | MCP `merge_pull_request` | false | 0 |
| G20 | `ls -la`（無関係コマンド） | true | 0（`gh` を呼ばない） |
| G21 | `DANGER_OK=1 gh pr merge 257` | true | 0（明示エスケープ） |
| G22 | `gh pr merge 257 && rm -rf x` | true | 2（既存 hard-block が先に効く回帰） |
| G23 | MCP `merge_pull_request`（`pull_number` なし） | true | ASK（識別子不明のまま照会せず降格） |
| G24 | MCP `get_pull_request`（対象外ツール） | true | 0（素通し・`gh` を呼ばない） |

false-green 注入（判定行ごと）:

| # | 注入 | 期待 |
|---|---|---|
| FG-A | `_gh_pr_target` を常に `None` にしたコピー | G1 が 0 になる（＝テストが検出する） |
| FG-B | 実体では G1 が 2 |  |
| FG-C | `_pr_is_cross_repo` を常に `False, None` にしたコピー（**2-タプルを返す**。`return False` を注入すると `cross, head = ...` のアンパックで `TypeError` になり、素通しではなく exit 1 になって注入テスト自体が偽陰性になる） | G1 が 0 になる |
| FG-D | `_mcp_pr_target` を常に `None` にしたコピー | G13 が 0 になる |

### 5-6. `.claude/skills/close/SKILL.md`（step 0）

**修正方針**: 既存の base 確認と**同じ粒度**（具体コマンド＋分岐の指示）で 1 ブロック追加する（コマンド粒度パリティ）。

```bash
   # cross-repo チェック（I146）: 自前の PR であることを先に確認する
   gh pr view <PR番号> --json isCrossRepository -q .isCrossRepository
   # → "false" であること。"true"（fork 由来の外部 PR）なら **STOP**。
   #   base 追従も CI 対応もせず、CONTRIBUTING.md の方針に沿って方針コメント付きで close する
   #   （手順: docs/runbooks/workflow.md「外部（fork）からの PR の扱い」）。
```

### 5-7. `CONTRIBUTING.md`（新規・ルート）

**修正方針**: 読み手は外部の寄稿者なので英語を先に、リポジトリの運用者向けに日本語を後段に置く。「断る」ではなく「この形では受け取れない・理由はこれ」と読める文面にする。

構成（英語 → 日本語の同内容）:
- **Code contributions are not accepted.** — PR は受け付けない。
- 理由: 変更ごとに計画・テスト・レビューの記録を必須とする内部ワークフローで開発しており、外部の変更はその記録を伴わない。また `docs/runbooks/` と `.claude/` はレビュー AI の判断基準そのもので、無審査の変更は以後の全レビューに影響する。
- **Issues are welcome**（バグ報告・提案）。ただし対応・返信を約束しない。
- 脆弱性は Issue ではなく `SECURITY.md` の手順で報告してほしい。
- 送られた PR は、内容にかかわらず方針として close する（寄稿者の努力への否定ではないことを明記）。

### 5-8. `SECURITY.md`（新規・ルート）

**修正方針**: GitHub の Private vulnerability reporting に一本化する。メールアドレスは書かない（公開リポジトリでのアドレス収集を避ける）。英語＋日本語。

- 報告先: リポジトリの Security タブ →「Report a vulnerability」
- 公開 Issue に脆弱性を書かないでほしい旨
- 対応時期を約束しない旨（個人プロジェクト）

### 5-9. `.github/pull_request_template.md`

**修正方針**: 既存項目は無改変。冒頭に 1 行だけ追加する。

```markdown
> 外部からの PR は受け付けていません（[CONTRIBUTING.md](../CONTRIBUTING.md)）。このテンプレートはメンテナ用です。
```

### 5-10. `docs/runbooks/workflow.md`

**修正方針**: 末尾に新規セクションを追加する。

```markdown
## 外部（fork）からの PR の扱い

public リポジトリのため、第三者（自律 AI エージェントを含む）から fork 経由の PR が届くことがある。
外部からのコード寄稿は受け付けない（CONTRIBUTING.md）。届いた場合は次の手順で処理する。

1. head リポジトリを確認する: `gh pr view <PR番号> --json isCrossRepository -q .isCrossRepository` → `true` なら外部 PR。
2. **Actions の実行を承認しない**（fork PR には repository secrets が渡らず、E2E は原理的に失敗する）。
3. **base 追従・CI 対応・レビューをしない**（マージしない PR に投じる意味がない）。
4. 方針コメントを付けて close する: `gh pr comment <PR番号> --body-file <file>` → `gh pr close <PR番号>`。
5. 対象のイシューは OPEN のまま残し、必要なら通常のハーネス手順（/plan-issue 以降）で自前実装する。

判定は `pr-base-sync.sh` と PreToolUse ガードでも自動検知されるが、上記は人が最初に見たときの手順である。
```

---

## 6. 実装手順

**依存関係**: ステップ 1 と ステップ 3 は並行実施可能。ステップ 2 はステップ 1 の完了（M1・M2 のゲート通過）が前提。ステップ 4 は独立。ステップ 5 はステップ 1〜4 の完了が前提。

### ステップ 1: hook 層（未知リスク先行）

最も不確実なのは「hook の判定が実際のハーネス上で意図どおり block / ask になるか」であり、これを最初に置く。

1-1. `scripts/claude/hooks/pretooluse_guard.py` に 5-1 の判定・分岐を追加する。
1-2. `.claude/settings.json` に 5-2 の MCP matcher を追加する。
1-3. `scripts/claude/tests/test_pretooluse_gh_pr_guard.sh` を新規作成する（5-3）。
→ 検証は TC-03・TC-04・TC-05 参照。

**ゲート（実証不能クラスの前倒し）**: ステップ 1 完了直後に、**プレーン default の新規セッション**で手動テスト M1・M2 を実施する。ここが不成立なら設計をやり直し、ステップ 2 以降へ進まない。

### ステップ 2: script 層

2-1. `scripts/claude/pr-base-sync.sh` に 5-4 の cross-repo チェックを追加する。
2-2. `scripts/claude/tests/test_pr_base_sync.sh` のスタブを拡張し T17〜T21 を追加する（5-5）。
→ 検証は TC-01・TC-02・TC-05 参照。

### ステップ 3: skill 層

3-1. `.claude/skills/close/SKILL.md` step 0 に 5-6 のブロックを追加する。
→ 検証は TC-06 参照。

### ステップ 4: do 層（文書＋リポジトリ設定）

4-1. `CONTRIBUTING.md` を新規作成する（5-7）。
4-2. `SECURITY.md` を新規作成する（5-8）。
4-3. `.github/pull_request_template.md` に 1 行追加する（5-9）。
4-4. `docs/runbooks/workflow.md` に新規セクションを追加する（5-10）。
4-5. **ユーザー承認を得てから** Private vulnerability reporting を有効化する: `gh api -X PUT repos/osushi0404-dev/study-app-multitenant/private-vulnerability-reporting`
→ 検証は TC-06・TC-07 参照。

### ステップ 5: 全体回帰

5-1. 既存テスト（push guard・pr-base-sync）を通し、回帰がないことを確認する。
→ 検証は TC-08 参照。

**サービス再起動**: 不要（ファイル削除・サービス停止を伴わない）。ただし `.claude/settings.json` の matcher 追加は**セッション再起動で反映**されるため、M1・M2 は新規セッションで実施する。

---

## 7. テスト計画

- **テストレベルの選択**: 本イシューはアプリのビジネスロジックを含まないため、ユニット/結合/E2E の区分ではなく、(a) hook・スクリプトの**判定ロジックの決定論テスト**（`scripts/claude/tests/*.sh`）と (b) **文書・設定の存在/文言の決定論 grep**、(c) ハーネス実挙動の**手動テスト**の 3 種で構成する。
- **再発防止テスト**: 本イシューは事故（外部 PR の誤処理）の再発防止そのものであり、G1〜G22・T17〜T21 が再発防止テストに当たる。
- **認可・テナント境界のテスト**: 該当なし（アプリの認可を変更しない）。
- **false-green 対策**: 否定・不在・無改変を判定する TC（TC-06 の grep 群・G2/G6〜G10 の素通し系）は、失敗条件を注入して NG になることを TC-02・TC-04 で裏取りする。
- 詳細は `docs/tests/open/I146_auto_test.md` / `docs/tests/open/I146_manual_test.md`。

---

## 8. ロールバック

| 対象 | 手順 |
|---|---|
| コード・文書の変更 | `git revert <コミット>`（PR 未マージなら Draft PR を閉じてブランチ削除） |
| `CONTRIBUTING.md` / `SECURITY.md` / 新規テスト | ファイル削除（新規追加のみのため副作用なし） |
| `.claude/settings.json` の matcher | 追加したオブジェクトを削除（既存 2 エントリは無改変のため元に戻る） |
| Private vulnerability reporting | `gh api -X DELETE repos/osushi0404-dev/study-app-multitenant/private-vulnerability-reporting` |

いずれもデータ破壊を伴わず、即時に元へ戻せる。

---

## 9. Risk & 回避策

| # | リスク | 影響 | 回避策 |
|---|---|---|---|
| R1 | hook 内の `gh` 照会でハーネスが待たされる | 体感遅延 | 対象サブコマンド／対象 MCP ツールに一致した場合のみ照会する。タイムアウト 5 秒。無関係コマンドは `gh` を呼ばない（G20 で検証） |
| R2 | オフライン・未認証で照会が失敗し作業できなくなる | 作業停止 | 失敗・タイムアウト・想定外値は **block せず ask に降格**（G17 で検証） |
| R3 | 既存テスト（T1〜T16）がスタブ不足で全滅する | 誤った赤 | スタブ拡張を 5-5 に明記。TC-01 で全件確認 |
| R4 | `gh pr` の識別子（番号・URL・ブランチ名）の解釈違い | 誤判定 | 識別子は解釈せず `gh` にそのまま渡す。URL 形式は G12 で検証 |
| R5 | GitHub UI からのマージ・Actions 承認は捕捉できない | 残存ギャップ | 設計上の限界として明記（下記）。do 層（runbook・CONTRIBUTING）で補う |
| R6 | 読み取り中心の調査での思い込みは hook でも止まらない | 残存ギャップ | 同上。`/close` step 0（skill 層）で作業開始時に必ず一度確認する導線を作る |
| R7 | `.claude/settings.json` の matcher 追加が既存 hook 動作に影響する | 誤 block | 追加は新規オブジェクトのみ。既存 2 エントリは無改変（TC-06 で無改変を grep 検証・TC-08 で push guard 回帰） |
| R8 | 将来 `gh pr` に新しい取り込み系サブコマンドが増える | 取りこぼし | 対象 verb は定数（`_GH_PR_BLOCK_VERBS` / `_GH_PR_ASK_VERBS`）に集約し、追加が 1 行で済む形にする |

### 設計上の限界（no silent caps）

本対策が**止められない**経路を明示する。

- GitHub UI 上の操作（マージ・Actions 実行承認・ブランチ更新）はハーネスを経由しないため捕捉できない。
- 読み取り操作（`gh pr view` 等）は素通しさせるため、調査中に外部 PR を自前だと思い込むこと自体は防げない。
- API を直接叩く経路（`gh api -X PUT .../merge`・`curl` で GitHub API を叩く等）は対象外。判定は `gh pr <verb>` の形と対象 MCP ツールに限る。
- ラッパー越しの隠蔽（`eval "gh pr merge 257"`・`bash -c "..."`）は検出しない。push ガードは `_push_is_dynamic` で ask に降格させているが、本ガードでは同等の降格を入れない（`gh` を含む文字列の誤 ask が増え、日常操作の妨げになるため）。脅威モデルは「うっかり外部 PR を取り込む」であり、隠蔽の意図がある操作は対象外とする。

---

## 10〜15. 条件付きセクションの該当有無

- **10) データ整合性設計**: 該当なし（DB 変更なし）。
- **11) 運用設計**: 該当あり（hook から外部コマンド `gh` を呼ぶため）。タイムアウト 5 秒・リトライなし（ハーネスを止めないことを優先）・失敗時フォールバックは ask 降格。ログは hook の既存方式（stderr へ `[guard] ...`）に合わせ、新しいログ基盤は導入しない。Feature Flag は導入しない（`DANGER_OK=1` が明示エスケープを兼ねる）。
- **12) コスト・保守見積もり**: 該当なし（新規インフラ・外部サービスの追加なし）。追加の維持対象はテスト 1 本と定数 2 つ。
- **13) 性能・UX設計**: **P6 影響なし**（フロントエンド変更なし）。hook のレイテンシは R1 で扱う。
- **14) 学習効果設計**: 該当なし。
- **15) プライバシー・コンプライアンス設計**: **P9 影響なし**（個人情報・未成年データ・テナントデータを扱わない）。`SECURITY.md` にメールアドレス等の連絡先個人情報を記載しない方針は 5-8 に明記。

### セキュリティ・ベストプラクティスチェック

- **セキュリティ影響**: バックエンド・フロントエンドのコード変更がないため、入力バリデーション・認証認可・OWASP Top 10・Django/React 規約の適用対象は**該当なし**。
- 一方で本イシュー自体がセキュリティ運用の改善（外部からの無審査変更の流入防止・脆弱性報告経路の新設）である。
- 機密データ: 追加しない。`SECURITY.md` に連絡先メールを書かない。`gh` の認証情報を hook がログ出力しないこと（`[guard]` は PR 番号と fork である事実のみ出力する）。
- 依存ライブラリの追加: **なし**（`subprocess` / `shlex` は既存 import・pip / npm パッケージ追加なし）。よって pip-audit / npm audit の新規実行は不要。
- スキャンツールの重大度基準: 本変更は Python 1 ファイル・Bash 2 ファイルの変更で、pre-commit の bandit / shellcheck が適用される。**bandit は MEDIUM 以上を修正対象・LOW は `# nosec` で抑制、npm audit は high/critical を修正対象**（既存基準を踏襲）。`subprocess.run` はシェルを介さない引数リスト形式で呼ぶ（`shell=True` を使わない）ため B602 系には該当しない。

---

## 16. 承認ポイント

（本文は「承認ポイント」として会話側に提示する。）

## レビュー結果
- [20260804_2322 判定: ✅ 完了](../../reviews/I146_plan_review_20260804_2322.md)
- [20260804_2311 判定: 差し戻し（Blocker 1件）](../../reviews/I146_plan_review_20260804_2311.md)
