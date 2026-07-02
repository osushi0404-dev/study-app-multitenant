# I095 計画書: 別 worktree 配下への編集を PreToolUse フックでハードブロック

## 基本情報
- **計画書ID**: plan_I095
- **関連イシュー**: #181
- **Draft PR**: #185
- **作成根拠資料**: docs/issues/open/I095.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I095_review.md
- **作成日**: 2026-07-02

## 1. 背景/目的

worktree でトラック（ハーネス改善＝`wt-harness` / アプリ開発＝`study-app-multitenant`）を分離しても、あるトラックのセッションから**別トラックの作業ツリーを直接編集する**ことを止める技術的仕組みが無い。抑止は `worktree.md §9`・memory `feedback_respect_track_session_boundary` の**ソフトルールのみ**。憲法§3 の二重ガード（settings 権限 + PreToolUse フック）に worktree 横断ガードが欠けている。

本イシューは `scripts/claude/hooks/pretooluse_guard.py`（PreToolUse・全 worktree 共有）に「**対象パスが別 worktree ルート配下なら書込をブロック**」する判定を追加し、トラック横断の直接編集を**技術強制で不可能化**する。読み取りは許可。fail-safe（境界確定不能時はブロック）・エスケープ無し（DANGER_OK 解除なし）。

## 調査結果

### 環境前提確認
- `python3`（フック実行系）・`git`（worktree サブコマンド対応）・`bash`（テスト実行系）いずれも稼働環境に存在。
- `git worktree list --porcelain` の実出力（本セッションで確認）:
  ```
  worktree /mnt/c/app/study-app-multitenant
  worktree /mnt/c/app/wt-harness
  ```
  → `worktree <絶対パス>` 行を拾えば全 worktree ルートを列挙できる。現 worktree は `git rev-parse --show-toplevel`。
- `.claude/settings.json` の PreToolUse は `Edit|Write`（Edit/Write 用）と `Bash`（Bash 用）に `pretooluse_guard.py` を登録済み。commit 済み＝全 worktree 共有 → 判定追加は双方向に自動適用。
- 既存フック `main()` は `tool_name in ("Edit", "Write")` の**完全一致**で分岐するため、`MultiEdit`/`NotebookEdit` は現状フックロジックの対象外（マッチャの正規表現が部分一致で発火しても Python 側が素通し）。→ 本イシューで対象ツールを拡張し、マッチャも明示化する（下記スパイク／設計参照）。

### スパイク実証（核メカニズム・in-session 検証済み）
plan-writing-rules「外部/ハーネス挙動依存のスパイク実証(1)」に基づき、核ロジック（worktree 列挙＋別worktree配下判定）をスクラッチパッドの最小実装で実 worktree に対して検証した。結果 **全 PASS（fail=0）**:

| ケース | パス | 期待 | 結果 |
|--------|------|------|------|
| 別worktree配下 | `/mnt/c/app/study-app-multitenant/backend/foo.py` | block(True) | PASS |
| 現worktree配下 | `/mnt/c/app/wt-harness/scripts/x.py` | allow(False) | PASS |
| リポジトリ外 | `/tmp/.../scratch/x.txt` | allow(False) | PASS |
| 兄弟名の部分一致 decoy | `/mnt/c/app/study-app-multitenant-foo/x.py` | allow(False) | PASS |
| 相対パス（現worktree） | `scripts/x.py` | allow(False) | PASS |

→ 判定は `os.path.realpath` で正規化し、worktree ルートとの**境界一致**（`ap == root or ap.startswith(root + os.sep)`）で行うと、兄弟ディレクトリ名の部分一致（`-foo`）を正しく除外できることを実証した。

### in-session で実証不能な項目（実装ステップ1に前倒し）
- 「PreToolUse フックの exit 2 が実セッションの Edit/Bash を実際にブロックするか」「マッチャ拡張後に MultiEdit/NotebookEdit でフックが発火するか」は**権限モード／フックロード依存**（plan-writing-rules (2) 型）のため稼働中セッションでは実証不能。既存の push/checkout ガードが exit 2 で機能している実績はあるが、MultiEdit/NotebookEdit の発火は新規。→ 実装ステップ1（プレーン default 新規セッションでの目視）で確認する（手動テスト TC 参照）。決定論的な判定ロジック自体は自動テスト（stdin JSON 投入）で全件検証する。

## 2. 受け入れ条件
- [ ] `wt-harness` から `/mnt/c/app/study-app-multitenant/` 配下を Edit/Write すると `exit 2` でブロックされる（逆方向も同様）
- [ ] `MultiEdit`/`NotebookEdit` でも別 worktree 配下がブロックされる（マッチャ発火＋ロジック対象）
- [ ] Bash の `echo x > <別wt>/f`・`>> `・`>| `・`tee <別wt>/f`・`cp a <別wt>/`・`mv a <別wt>/`・`sed -i ... <別wt>/f` がブロックされる
- [ ] 現 worktree 配下の Edit/Write/Bash 書込は従来どおり通る（誤ブロック無し）
- [ ] `/tmp` スクラッチパッド等リポジトリ外への書込は通る
- [ ] 別 worktree 配下の Read/`cat`/`grep` 等の読み取りは通る（`cp <別wt>/src ./dest` のように別 worktree を**読む**のは通る）
- [ ] worktree 境界を確定できない場合（`git worktree list` 失敗をシミュレート）に書込が fail-safe でブロックされる
- [ ] `DANGER_OK=1` を前置しても横断書込は解除されない（エスケープ無し）
- [ ] Bash 未カバー経路（`cd` 経由・`eval`/変数展開越し）がある旨が stderr/log で明示される
- [ ] 既存の push/checkout/高リスクガードが回帰していない（既存テスト PASS）
- [ ] `docs/runbooks/worktree.md` §9 に技術強制済みである旨が追記されている

## 3. 影響範囲
- Backend: なし（Django アプリコード変更なし）
- Frontend: なし（React コード変更なし）
- DB: なし
- Config/Infra: `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`（PreToolUse マッチャ明示化）・`scripts/claude/tests/test_pretooluse_worktree_guard.sh`（新規）・`docs/runbooks/worktree.md`

## 4. 変更点一覧（具体）

### 4-1. `scripts/claude/hooks/pretooluse_guard.py`（追加関数）
- `_worktree_roots() -> list | None`: `git worktree list --porcelain` を実行し `worktree ` 行の絶対パスを `os.path.realpath` で正規化して返す。git 失敗/非ゼロは `None`（fail-safe 対象）。
- `_current_worktree_root() -> str | None`: `git rev-parse --show-toplevel` を realpath 正規化。失敗は `None`。
- `_cross_worktree(path: str) -> bool | None`: `path` を `realpath(abspath(path))` 化し、**現 worktree 以外**のルートに対し境界一致（`ap == root or ap.startswith(root + os.sep)`）すれば `True`。どのルート配下でもなければ `False`。列挙/現ルート取得失敗は `None`（判定不能）。
- `_edit_path(data) -> str`: `tool_input.file_path`（Edit/Write/MultiEdit）または `notebook_path`（NotebookEdit）を返す。
- `_bash_write_targets(cmd: str) -> list[str]`: `_segments()` で分割し、各セグメントから**書込先の絶対パス**のみを抽出:
  - リダイレクト: (a) トークンが `>`/`>>`/`>|` 単体でその次トークンが宛先、(b) 先頭付着形 `>file`/`>>file`/`>|file`、(c) **語中埋め込み形** `word>/path`（`echo x>/path/f` は shlex では `['echo','x>/path/f']` の単一トークンになる）→ トークン内に `>`/`>>`/`>|` を検出したら演算子で分割し**右側を宛先**として抽出する。いずれも右側が絶対パスのときのみ対象。
  - `tee`（`tee`/`tee -a`）: 直後の非フラグ file 引数（全て＝書込先）。
  - `cp`/`mv`: 末尾の非フラグ引数（宛先）。`-t <dir>` 指定時は `<dir>`。**src 側は対象外**（別 worktree を読むのは許可）。
  - `sed -i`（`-i`/`--in-place`）: セグメント内の非フラグ file 引数（全て in-place で書換＝書込先）。
  - 相対パス・変数/コマンド置換を含むトークンは対象外（絶対パスのみ判定・下記 log で限界明示）。
- `_block_cross_worktree(kind: str, path: str)`: `exit 2`（`_block()` 流用）でブロック。メッセージに「別 worktree（<root>）への<kind>は禁止（§9・引き継ぎはファイル経由）」を含める。判定不能（`None`）時は fail-safe 用に「worktree 境界を確定できないためブロック（git 状態を確認してください）」を出す。

### 4-2. `pretooluse_guard.py`（`main()` の分岐追加）
- 書込ツール分岐を拡張:
  ```
  if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
      path = _edit_path(data)
      x = _cross_worktree(path) if path else None   # パス未取得も None＝fail-safe(block)（Info#1 反映）
      if x is True or x is None:   # 別wt配下 / 判定不能 / パス未取得(fail-safe) → block（DANGER_OK でも解除しない）
          _block_cross_worktree("編集", path)
      if tool_name in ("Edit", "Write"):
          _check_edit_write(data)      # 既存の高リスク ask は Edit/Write のみ（現状維持・スコープ外）
      sys.exit(0)
  ```
- Bash 分岐: ハードブロック（rm -rf / 等）判定の**直後・`if not danger_ok:` の外**（＝エスケープ無し）に横断書込判定を追加:
  ```
  for tgt in _bash_write_targets(cmd):
      x = _cross_worktree(tgt)
      if x is True or x is None:
          _block_cross_worktree("Bash 書込", tgt)
  # 書込先を1件でも検出したが判定に絶対パスが無い等の未カバー経路は stderr に注意を出す（no silent caps）
  ```
  - 未カバー経路（`cd <別wt>` 後の相対書込・`eval`/`sh -c`/変数展開越しの宛先）は、Bash 書込コマンド語（`tee`/`cp`/`mv`/`sed -i`/リダイレクト）を含むのに絶対パス宛先を抽出できなかった場合に stderr へ**固定文字列**を出す（no silent caps・TC-A22 が grep 検証）。確定メッセージ: `[guard] worktree ガードは絶対パス宛先のみ検査します（cd/変数展開越しの宛先は非対象）` — TC-A22 は部分文字列 `絶対パス宛先のみ検査` を grep で確認する。

### 4-3. `.claude/settings.json`
- PreToolUse の Edit/Write 用マッチャ `"matcher": "Edit|Write"` を `"matcher": "Edit|Write|MultiEdit|NotebookEdit"` に変更（部分一致依存を排除し全書込ツールで確実に発火させる）。Bash 用マッチャは変更なし。

### 4-4. `scripts/claude/tests/test_pretooluse_worktree_guard.sh`（新規）
- 既存 `test_pretooluse_checkout_guard.sh` の型（temp git repo + stdin JSON 投入 + exit code 検証 + false-green 注入）を踏襲。temp repo に `git worktree add` で linked worktree を生やし、別worktree絶対パスへの各操作を検証（TC は自動テスト文書参照）。

### 4-5. `docs/runbooks/worktree.md`
- §9 に「本 runbook のソフトルールは PreToolUse フック（`pretooluse_guard.py`）で技術強制済み（別 worktree 配下への Edit/Write/MultiEdit/NotebookEdit・Bash 書込を exit 2 でブロック・読み取りは許可・fail-safe・エスケープ無し）」を追記。

## 5. 実装手順（ステップ）

1. **【未知リスク先行】マッチャ拡張＋フック発火の確認基盤**: `.claude/settings.json` のマッチャを `Edit|Write|MultiEdit|NotebookEdit` に変更。フックが MultiEdit/NotebookEdit で発火するか・exit 2 が実ブロックするかは in-session で実証不能なため、プレーン default 新規セッションでの目視確認を行う → TC-M1・TC-M2 参照。不成立なら設計をやり直す（後続のゲート）。
   - 依存: なし（最初に着手）。
2. **判定コア実装**: `pretooluse_guard.py` に `_worktree_roots` / `_current_worktree_root` / `_cross_worktree` / `_edit_path` を追加（スパイク実証済みロジックを移植）→ TC-A1〜A5 参照。
   - 依存: なし（ステップ1と並行可）。
3. **Edit/Write/MultiEdit/NotebookEdit 分岐**: `main()` の書込ツール分岐を拡張し、`_cross_worktree` が True/None で block（fail-safe）。高リスク ask（Edit/Write）は非回帰 → TC-A6〜A10・TC-A16 参照。
   - 依存: ステップ2。
4. **Bash 書込判定実装**: `_bash_write_targets` と `main()` Bash 分岐（danger_ok 非依存＝エスケープ無し）・未カバー経路の stderr 注意 → TC-A11〜A15・TC-A17 参照。
   - 依存: ステップ2。
5. **自動テスト作成**: `test_pretooluse_worktree_guard.sh` を作成（temp worktree・全 TC・false-green 注入）→ 自動テスト文書の決定論ゲートで実走。
   - 依存: ステップ2〜4。
6. **既存テスト回帰確認**: `test_pretooluse_checkout_guard.sh`・`test_pretooluse_push_guard.sh` が PASS のまま → TC-A18 参照。
   - 依存: ステップ3〜4。
7. **runbook 追記**: `worktree.md` §9 に技術強制済みを追記 → TC-A19 参照。
   - 依存: なし（並行可）。

## 6. テスト計画
### 自動（`docs/tests/open/I095_auto_test.md`）
- 判定ロジック（別wt block／現wt allow／リポジトリ外 allow／兄弟名 decoy／相対 allow）、Edit/Write/MultiEdit/NotebookEdit の block、Bash 各書込コマンドの block、src 読み取りの allow、fail-safe（worktree list 失敗注入）、DANGER_OK 非解除、既存回帰、false-green 注入。決定論ゲートで `test_pretooluse_worktree_guard.sh` と既存2テストを実走。
### 手動（`docs/tests/open/I095_manual_test.md`）
- TC-M1/M2: プレーン default 新規セッションで実 Edit/MultiEdit/Bash 書込が別 worktree に対して実際にブロックされることを目視（フックロード依存のため）。実施環境列付き。
- Claude 実施分: ファイル存在・追記内容の確認。

## 7. ロールバック
- `.claude/settings.json` のマッチャを `Edit|Write` に戻し、`pretooluse_guard.py` の追加関数・分岐・新規テスト・runbook 追記を revert すれば従来動作に戻る（フックは fail-open 側の既存挙動へ）。DB・外部状態変更なしのため revert のみで完結。

## 8. Risk & 回避策
- **R1 誤ブロック（現 worktree の正当編集を止める）**: 境界一致を realpath＋末尾 `os.sep` 接頭辞で厳密化し、兄弟名 decoy を自動テストで反証（スパイク実証済み）。
- **R2 fail-safe × エスケープ無しで git 失敗時に書込全面停止**: git 常在の本リポジトリでは実害ほぼ無い想定。ブロックメッセージに「git 状態を確認」を明記し詰まらない導線を確保。恒久停止を避けるため、判定不能は「書込のみ」ブロック（読み取り・非書込 Bash は通す）。
- **R3 Bash 検出の取りこぼし（cd/eval/変数越し）**: 既知の限界として stderr に明示（no silent caps）。完全網羅は別イシュー。絶対パス直書きの主要経路は確実に捕捉。
- **R4 MultiEdit/NotebookEdit のマッチャ非発火**: マッチャを明示列挙して部分一致依存を排除。ステップ1でプレーン新規セッション目視（TC-M2）。
- **R5 パフォーマンス（毎回 git 呼び出し）**: `git worktree list` は軽量。書込系ツール/コマンド時のみ実行（読み取りでは呼ばない）。

## セキュリティ・要件適合チェック（承認ポイント用）
- **セキュリティ影響**: Django/React アプリコード変更なし。本変更は開発ハーネスの安全ガード**強化**（横断書込の防止）であり、OWASP 系の新規攻撃面は増やさない。入力（フック stdin JSON・Bash コマンド文字列）はパス正規化と `shlex` 分割で扱い、パストラバーサルは realpath 正規化＋境界一致で無害化。機密データの取り扱いなし（`.env` は読まない）。
- **要件適合**: AC 範囲内。仕様追加なし。マルチテナント業務ロジック・DB・API 変更なし（P3/P5/P8/P6/P9 影響なし）。
- **設計判断の出所**:
  - fail-safe / エスケープ無し / Bash 実用網羅 → **イシューに明記**（grill-me 設計確認メモ）。
  - 対象ツールに MultiEdit/NotebookEdit を含め settings.json マッチャを明示化 → **planning 中の精緻化**（イシュー本文へ反映済み・grill 第2ラウンドで根拠提示）。仮定ではなくコード実査（`main()` の完全一致分岐）に基づく。
  - 境界一致を realpath＋末尾 sep 接頭辞で行う → **スパイク実証で決定**。

## 9. 承認ポイント
- [ ] 計画内容（`pretooluse_guard.py` への判定追加・settings.json マッチャ明示化・新規テスト・runbook 追記）で妥当か
- [ ] 対象ツールに MultiEdit/NotebookEdit を含め settings.json マッチャを `Edit|Write|MultiEdit|NotebookEdit` に変更する方針でよいか（planning 中の精緻化）
- [ ] fail-safe × エスケープ無しにより git 失敗時は書込がブロックされる挙動（読み取り・非書込は通す）でよいか
- [ ] Bash 検出は絶対パス宛先のみ・cd/eval/変数越しは既知の限界として log 明示する範囲でよいか
- [ ] Danger Ops: 無（破壊的操作なし・ガード強化のみ）
- [ ] テスト計画（自動＝決定論ゲート＋既存回帰／手動＝プレーン新規セッション目視）で妥当か

## レビュー結果
- [20260702_1539 判定: ✅ 完了（Blocker 0件）](../../reviews/I095_plan_review_20260702_1539.md)
