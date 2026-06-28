# 計画書 I080: push ポリシー見直し（feature push 無確認化・危険 push はフック danger-op で阻止）

## 基本情報
- **計画書ID**: plan_I080
- **関連イシュー**: #160
- **Draft PR**: #165（`feature/I080-push-policy-guard` → develop）
- **作成根拠資料**: docs/issues/open/I080.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I080_review.md
- **作成日**: 2026-06-28

> **【限定注記・2026-06-29／本計画内の「網羅／全形／全宛先形／全経路」表現すべてに優先】** これらは **static（静的）形に限る**。実装後の敵対的レビュー・再レビューで2つの残余が判明: **R5（Critical）** 動的宛先（`$(...)`/`$VAR`/`-c alias.`/`eval`・`sh -c`）の静的解析すり抜け、**R6/F1（High）** force push の `-f`/複合コマンド取りこぼし。いずれもフック・deny の双方を擦り抜ける。I080 は静的形保護にスコープ確定し、両者の根治は **I083（#166）** で対応する（§10 Risk・残余リスク処遇 参照）。

## 1. 背景/目的

### 原因の概要（平易な説明）
安全な feature ブランチへの push でも毎回「承諾しますか?」が出る。これは権限設定の `ask: Bash(git push *)` が、安全な push 用の `allow: Bash(git push -u origin *)` を**上書き（shadow）**しているため。一方、危険な push（develop/main 宛先・force）はフックで止めているが、フックの判定に**複数の穴**（引数なし push・refspec・`+develop`・完全修飾 ref・`--all`/`--mirror`）がある。本イシューは「安全な push は無確認・危険な push はフックが確実に止める」を穴ゼロで実現する。

### 詳細な原因分析
1. **承諾プロンプト多発（権限 precedence）**: Claude Code の権限評価は `deny > ask > allow`。`git push -u origin <feature>` は `allow: Bash(git push -u origin *)` に一致するが、同時に `ask: Bash(git push *)` にも一致し、**ask が allow を shadow** して必ずプロンプトになる。引数なし `git push` はそもそも allow エントリが無く ask に落ちる。
   - **本計画作成中に実証**: 本ブランチ（I080 未適用の develop ベース）で `git push -u origin feature/I080-push-policy-guard`（単体・パイプ無し）を実行したところ、`ask: Bash(git push *)` でプロンプトが出た。これは shadow が原因（パイプ等の複合化は無関係）であることを実機確認した。
2. **フックの protected-push 検出の穴**: 既存フック（`pretooluse_guard.py`）は `if not danger_ok:` 内で `origin (develop|main)` 正規表現・`HEAD on protected`・`--force` のみ block。下記「調査結果」のとおり、引数なし push（保護ブランチ上）・refspec `<src>:develop|main`・`+develop`・`refs/heads/develop`・`HEAD:refs/heads/main`・`--all`/`--mirror` は素通り（exit 0）。

### 根本原因（コードレベル）
- `.claude/settings.json`: `ask` に `Bash(git push *)` が残り allow を shadow。安全 push 用の allow が機能していない。
- `pretooluse_guard.py`: protected 宛先の判定が「`origin` 直後の `develop|main`」という限定的な正規表現＋HEAD 限定で、宛先トークンを正規化していないため多数の形を取りこぼす。加えて `\b` 部分一致で `develop-fix`/`main-backup` を誤遮断（FP）。

## 2. 調査結果

### 環境前提
- `python3`（3.12.3）・`git`（2.43.0）本セッションで存在確認済み。アプリコード（backend/frontend/DB）変更なし → pytest/eslint ベースライン・pip-audit/npm audit は非該当。
- 既存テスト `bash scripts/claude/tests/test_pretooluse_checkout_guard.sh` を実行 → **pass=14 fail=0**（ベースライン健全）。
- I079（#159）・I081（#163）・I082（#164）は develop マージ済み。本ブランチは `origin/develop` 基点で作成済み（settings.json の I079 衝突懸念は解消）。

### 現状フックの穴（実機検証・stdin JSON 投入で exit code 観測）
develop 上:
| コマンド | 現状 exit | あるべき |
|---|---|---|
| `git push` / `git push origin` / `git push -u origin` | 0（素通り） | 2 |

任意（feature）ブランチ上:
| コマンド | 現状 exit | あるべき |
|---|---|---|
| `git push origin feat:main` / `HEAD:develop` / `x:main` | 0（素通り） | 2 |
| `git push origin +develop` | 0（素通り） | 2 |
| `git push origin refs/heads/develop` | 0（素通り） | 2 |
| `git push origin HEAD:refs/heads/main` | 0（素通り） | 2 |
| `git push --all` / `--mirror` | 0（素通り） | 2 |
| `git push origin develop-fix` / `main-backup` | 2（**誤遮断 FP**） | 0 |
| `git push origin develop` / `main` / `--force ...` | 2 | 2（維持） |

### 設計（最終形）の in-session スパイク実証（plan-writing-rules §「スパイク実証」(1) 該当）
最終設計の判定関数（`_push_protected_target` ＋ `_norm_push_dest`）を試作し、develop/feature 両ブランチで**全 22 ケース**を実行 → **fails=0**（成立）。網羅: 引数なし push（保護ブランチ）・refspec・`+develop`・`refs/heads/`・`HEAD:refs/heads/main`・`--all`/`--mirror`・`git -C <dir> push`・DANGER_OK escape（→0）・FP 解消（`develop-fix`/`main-backup`→0）・安全 push（→0）。スパイク結果は本設計の前提（文字列正規化＋現ブランチ解決で全宛先形を判定可能）が成立することを示す。

### ハーネス挙動の未実証部分（plan-writing-rules §「スパイク実証」(2) 該当）
**settings.json の権限レイヤー挙動**（`ask` から `git push *` 撤去後に安全 push が実際に無確認になるか／`deny` が未承認 protected push を止めるか／`DANGER_OK=1 ` 前置で deny を素通りしてフックの danger-op 解除に到達するか）は、**稼働中セッションでは実証不能**（セッション起動時にロードした settings を編集途中で再ロードしないため）。これは「未実証」とし、**プレーン default 新規セッションでの実証を実装ステップ1のゲート**に置く（手動テスト TC-M に実施環境列で明記）。フックの exit code 挙動は (1) で実証済みのため auto_test で決定論検証する。

## 3. 受け入れ条件（イシュー AC を継承）
- [ ] `allow` に `Bash(git push)`・`Bash(git push *)` が含まれ、`ask` から `Bash(git push *)` が除かれている
- [ ] `deny` の保護ブランチ/force エントリが維持されている
- [ ] settings.json が有効な JSON（`python3 -m json.tool` でパス）
- [ ] フックが protected 宛先 push の**静的形**を既定 exit 2 ブロック（明示名・保護ブランチ上の引数なし push・refspec `<src>:develop|main`・`+develop`・`refs/heads/develop`・`HEAD:refs/heads/main`）。**動的宛先（コマンド置換/変数展開/エイリアス/`eval`・`sh -c` ラッパー）は静的解析の対象外＝既知の限界、根治は I083(#166)**
- [ ] protected 宛先 push が `DANGER_OK=1` 前置で exit 0（release/hotfix 解除経路）／`DANGER_OK` 無しは exit 2
- [ ] 宛先正規化が完全一致で、`develop-fix`/`main-backup` 宛先 push が exit 0（部分一致 FP なし）
- [ ] `git push --all`/`--mirror` が既定 exit 2・`DANGER_OK=1` で exit 0
- [ ] `git push --repo[=]origin ...`（evasion 形）が既定 exit 2・`DANGER_OK=1` で exit 0（security-review 由来の hardening）
- [ ] `--force`（非 protected）が従来どおり DANGER_OK 解除可
- [ ] feature 上の安全 push（素 push・`-u origin <feature>`・`<src>:<feature>`）が exit 0（誤検知ゼロ）
- [ ] フック異常系テストが false-green でない（protected 宛先 push・`--all`/`--mirror`・`--repo` の各判定行無効化複製との差分で注入確認）
- [ ] `docs/claude-code-structure.md` が新仕様に同期（`git push *` を ask でなく allow と記載・protected push の danger-op 化を反映）

## 4. 影響範囲
- Backend: なし / Frontend: なし / DB: なし
- Config/Infra:
  - `.claude/settings.json`（allow/ask の調整・deny 維持）
  - `scripts/claude/hooks/pretooluse_guard.py`（protected 宛先判定の正規化統一・`--all`/`--mirror`・`--repo` 追加）
  - `scripts/claude/tests/test_pretooluse_push_guard.sh`（**新規**・決定論テスト）
- Docs: `docs/claude-code-structure.md`（フック/権限説明の同期）

## 5. 変更点一覧

### 5-1. `.claude/settings.json`
- `allow` に追加: `"Bash(git push)"`・`"Bash(git push *)"`。
- `allow` から削除: `"Bash(git push -u origin *)"`（`git push *` に完全包含される冗長エントリ。理想形＝「`git push` を広く allow・フックが番人」の単一モデルに集約し死んだ重複を残さない）。→ allow の git push 系は `Bash(git push)`＋`Bash(git push *)` の2本に集約。
- `ask` から削除: `"Bash(git push *)"`。
- `deny` は不変（`git push origin develop`/`main`・`-u origin develop`/`main`/`HEAD`・`* --force*`）。
- 完了条件: `python3 -m json.tool .claude/settings.json` がパス（TC-S1）。allow/ask/deny の内容を検証（TC-S2〜S5）。

> **設計判断（allow `git push *` の安全性）**: `git push *` を allow にしてもフックが protected 宛先・`--all`/`--mirror` を既定 block するため危険 push は通らない。deny（テキストで自明な形）はバックストップとして残す。`deny > ask > allow` の precedence により、未承認の `git push origin develop` 等は deny で permission レイヤー遮断され、`DANGER_OK=1 ` 前置時のみ deny の glob を外れてフックの danger-op 解除（計画的 release/hotfix）に到達する。

### 5-2. `scripts/claude/hooks/pretooluse_guard.py`

**追加ヘルパ**（モジュール先頭付近・既存 `_segments`（I081）を再利用）:
```python
PROTECTED_BRANCHES = ("develop", "main")

def _current_branch():
    """現ブランチ名を返す。git 不在/失敗は None（fail-open＝既存 HEAD チェックと同方針）。"""
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def _norm_push_dest(token: str, cur_branch):
    """push 宛先トークンを正規化して宛先ブランチ名を返す（判定不能は None）。
    'src:dst' なら dst 採用 → force-shorthand '+'（先頭/dst 側いずれも）除去 → 'refs/heads/' 接頭辞除去 → 'HEAD' は現ブランチ解決。
    注: 'src:dst' 分割を先に行い、その後 lstrip('+') する順序が必須。逆順だと dst 側 '+'（例 feat:+refs/heads/main）を取り逃す（TC-P33・code-review Low 対応）。"""
    t = token
    if ":" in t:
        t = t.split(":", 1)[1]      # 'src:dst' の dst を採用
    t = t.lstrip("+")               # force-shorthand '+'（先頭 / dst 側）を除去
    if t.startswith("refs/heads/"):
        t = t[len("refs/heads/"):]
    if t == "HEAD":
        return cur_branch           # None 可（detached/fail-open）
    return t or None

def _push_protected_target(cmd: str):
    """git push が protected ブランチを **名前/refspec で宛先**にするなら宛先名を返す。非該当は None。
    単一責務（named/refspec の protected 宛先判定のみ）。--all/--mirror は別チェックで扱う。
    複合コマンドは _segments（I081）で分割して各セグメントを判定。"""
    for toks in _segments(cmd):
        if "git" not in toks or "push" not in toks:
            continue
        after = toks[toks.index("push") + 1:]
        positionals = [a for a in after if not a.startswith("-")]
        refspecs = positionals[1:] if positionals else []   # [0]=remote、以降=refspec
        cur = None
        if not refspecs:                                     # 宛先明示なし → 現ブランチが宛先
            cur = _current_branch()
            if cur in PROTECTED_BRANCHES:
                return cur
            continue
        for rs in refspecs:
            if cur is None:
                cur = _current_branch()
            dest = _norm_push_dest(rs, cur)
            if dest in PROTECTED_BRANCHES:
                return dest
    return None
```

**`main()` の `if not danger_ok:` 内**（既存の force/origin/HEAD push 判定を**置換**。protected 宛先・`--all`/`--mirror`・force を各々独立チェックにする＝既存の force/reset/docker-down と同じ構造）:
```python
        # push to a protected branch by name/refspec — danger-op:
        # release/hotfix のローカル push のみ DANGER_OK=1 で解除可（danger-ops.md 枠組み）
        dest = _push_protected_target(cmd)
        if dest:
            _block(
                f"push to protected branch '{dest}' is forbidden "
                f"(release/hotfix は計画書明記＋danger-approved＋DANGER_OK=1 のみ)",
                raw,
            )

        # bulk push of all refs (includes protected) — danger-op
        if re.search(r"\bgit\s+push\b.*\s(--all|--mirror)\b", cmd, re.I):
            _block("git push --all/--mirror pushes all refs incl. protected; requires DANGER_OK=1", raw)

        # vestigial --repo flag sets the remote without a positional arg, which
        # evades the positional-based protected detector (security-review 指摘) → block outright
        if re.search(r"\bgit\s+push\b.*\s--repo(\s|=)", cmd, re.I):
            _block("git push --repo can evade protected-branch detection and is unused in this workflow; requires DANGER_OK=1", raw)

        # force push to non-protected (protected 宛先は上で先に block)
        if re.match(r"git\s+push\b.*--force", cmd, re.I):
            _block("force push requires DANGER_OK=1", raw)
```
- **削除**: 既存の `origin (develop|main)` 正規表現 block・`HEAD on protected`（rev-parse）block（`_push_protected_target` に統合）。
- **単一責務**: `_push_protected_target` は named/refspec の宛先のみ判定。`--all`/`--mirror`・`--repo` は独立 regex チェック（develop/main を名指ししない／positional を持たないため関数に混ぜない）。
- **`--repo` ブロックの根拠（security-review）**: `--repo[=]<remote>` は remote を positional 無しで指定でき、`_push_protected_target` の「positionals[0]=remote」前提を崩して `git push --repo=origin develop:main` 等で protected へ素通りし得る（`allow: git push *` 化で**無確認**になるため silent push になる）。`--repo` は本 PR ベース運用で正当用途が無いため、パースを増やさず**フラグごと danger-op として block**（DANGER_OK 解除可）し、評価の rabbit hole を避けつつ evasion クラスを一掃する。
- **維持**: `reset --hard`・`docker compose down -v`・`rm -rf`・checkout/restore（I081）・破壊的 SQL の各判定は不変。

### 5-3. `scripts/claude/tests/test_pretooluse_push_guard.sh`（新規）
I081 の `test_pretooluse_checkout_guard.sh` 規約に準拠（`set -uo pipefail`・temp git repo・`ck` ヘルパ・stdin JSON 投入・false-green 注入）。develop/feature 両ブランチで全宛先形を検証。詳細 TC は `I080_auto_test.md` 参照。

### 5-4. `docs/claude-code-structure.md`
- `git push *` を **ask** カテゴリと記載している箇所（L133 付近）を **allow** へ修正。
- 保護ブランチ push の説明（L145 付近・「直接 push 禁止」）に、フックが danger-op（既定 block・`DANGER_OK=1` 解除可）として宛先正規化で**静的形**を検出する旨を反映（実際の編集では併せて動的宛先・force 取りこぼしの「既知の限界（I083 #166）」注記も追加した）。
- 追記文言にイシュー番号（`I080` 等）を含めない（一般形・TC-DOC で確認）。

## 6. 修正アプローチ
**(A) 権限レイヤー**: `ask` の shadow を撤去し安全 push を無確認化。`deny` はバックストップ維持。
**(B) フックレイヤー**: protected 宛先の判定を「宛先トークン正規化＋完全一致」の単一関数に統一し、全宛先形を網羅＋FP 解消。`--all`/`--mirror` を追加。判定は全て `if not danger_ok:` 内＝**danger-op**（release/hotfix のみ `DANGER_OK=1` で解除）。
**(C) ドキュメント**: `claude-code-structure.md` を新仕様へ同期。

## 7. 実装手順
- **ステップ1（ゲート・未知リスク先行）**: `.claude/settings.json` を変更（allow 追加・ask 撤去・deny 維持）。**プレーン default 新規セッションで権限レイヤー挙動を実証**（安全 push が無確認・未承認 protected push が deny・`DANGER_OK=1` 前置でフック danger-op に到達）。→ TC-S1〜S4（決定論ファイル検証）＋ TC-M1〜M3（実施環境=プレーン default 新規セッション）参照。**不成立なら設計をやり直す**（後続ステップを止めるゲート）。
- **ステップ2**: `pretooluse_guard.py` にヘルパ（`_current_branch`・`_norm_push_dest`・`_push_protected_target`）追加、`main()` の protected/HEAD push 判定を置換、`--all`/`--mirror` を追加。→ TC-P 群参照。
- **ステップ3**: `test_pretooluse_push_guard.sh` を新規作成（全宛先形 exit 2＋DANGER_OK escape＋安全 push exit 0＋FP→0＋false-green 注入）。既存 `test_pretooluse_checkout_guard.sh` の回帰も確認。→ TC-P 群・TC-FALSEGREEN 参照。
- **ステップ4**: `docs/claude-code-structure.md` を新仕様へ同期。→ TC-DOC 参照。

依存: ステップ2はステップ1（設計成立ゲート）後。ステップ3はステップ2完了が前提。ステップ4は独立（並行可）。

## 8. テスト計画
- **自動（決定論・フック単体）**: `I080_auto_test.md` の TC-P1〜（develop/feature 両ブランチの全宛先形 block/素通し・DANGER_OK escape・FP→0・`--repo` evasion 形）・**TC-FALSEGREEN-A/B（protected 判定行）＋ C/D（`--all`/`--mirror` 判定行）＋ E/F（`--repo` 判定行）の3系統**（独立判定行ごとに無効化注入して裏取り）・TC-Pregr（既存 checkout guard 14/14 維持）・TC-S1〜S5（settings.json の JSON 妥当性・allow/ask/deny 内容・冗長エントリ削除）・TC-DOC（claude-code-structure.md 同期・イシュー番号不在）。
- **手動（ハーネス権限レイヤー・実施環境明記）**: `I080_manual_test.md` の TC-M1〜M3（プレーン default 新規セッションで安全 push 無確認・未承認 protected push が deny・`DANGER_OK=1` で release/hotfix が解除に到達）。稼働中セッションでは検証不能のため実施環境列で明記。

## 9. ロールバック
`settings.json` の allow 追加・ask 撤去を元に戻す（deny は不変）。`pretooluse_guard.py` の追加ヘルパ＋判定置換を revert（旧 `origin (develop|main)`/HEAD 判定に戻す）。新規テストスクリプトを削除。`claude-code-structure.md` の追記を revert。DB・サービス影響なし、再起動不要（フックは次回 Bash 呼び出しから有効）。

## 10. Risk & 回避策
| Risk | 影響 | 回避策 |
|------|------|--------|
| `_push_protected_target` が**安全 push を誤遮断**（FP） | 中 | 完全一致判定。`develop-fix`/`main-backup`/`<src>:<feature>`/feature 上の素 push が exit 0 を TC で固定（誤検知ゼロ確認） |
| protected 宛先の**取りこぼし**（false-green） | 高 | TC-FALSEGREEN: 判定関数を一時無効化すると protected 宛先が exit 0 になることを確認してから本実装に戻す。全宛先形（refspec/`+`/`refs/heads/`/`HEAD:refs/heads/`）を TC で網羅 |
| `allow: git push *` が**危険 push を無確認で通す** | 高 | フックが protected/`--all`/`--mirror` を既定 block・deny がバックストップ。安全性はフック網羅性に依存するため TC で全形を固定 |
| 権限レイヤー挙動が想定と違う（ask 撤去後も prompt 等） | 中 | ステップ1をゲート化し**プレーン default 新規セッションで実証**してから後続へ。不成立なら設計やり直し |
| `git rev-parse` 失敗時の fail-open で protected 判定が漏れる | 低 | 既存 HEAD チェックと同方針。git 不在環境では `git push` 自体も失敗するため実害なし |
| 既存 checkout guard テストの回帰 | 低 | ステップ3で `test_pretooluse_checkout_guard.sh` 14/14 を再確認（G9 force は非 protected 宛先で不変） |

## セキュリティ・要件適合チェック結果
- **要件適合性**: イシュー AC の範囲内。仕様追加なし。アプリのビジネスロジック・マルチテナント・ステータス遷移は非該当（開発ハーネスの権限/ガード）。
- **セキュリティ**: アプリのコード変更なし＝OWASP/入力バリデーション/認証認可への直接影響なし。本変更は開発ハーネスの**防御的強化**（protected 宛先 push の検出網羅・FP 解消）＋権限ノイズ削減。`allow: git push *` の緩和はフック（protected/`--all`/`--mirror` を既定 block）＋deny で二重に担保。フックは `subprocess` を**リスト引数**で呼び `shell=False`＝コマンドインジェクションなし。`DANGER_OK=1` 解除は release/hotfix の意図的 escape（danger-ops.md 枠組み）。依存追加なし → pip-audit/npm audit 非該当。**結論: セキュリティ影響はハーネスのガード強化（静的形に限り厳密化）**。
  > **【再レビューによる訂正・2026-06-29】** 上記「二重に担保／むしろ厳密化」は **static 形に限る**。実装後の敵対的レビューで、(R5) 動的宛先（`$(...)`/`$VAR`/`-c alias.`/`eval`・`sh -c`）と (R6) force push の `-f`/複合コマンド取りこぼし（F1・High）が**フック・deny の双方を擦り抜ける**ことが判明（残余 Critical/High）。二重担保は静的形のみ成立。根治は **I083（#166）** で対応。
- **テスト計画**: 新規振る舞い（protected 検出網羅・FP 解消）に対し決定論テストを用意。否定・回帰系（TC-FALSEGREEN）は判定無効化注入で exit 0 化を確認＝false-green でない。認可/テナント境界テストは非該当（アプリ認可ロジック不変）。
- **P3/P5/P8（データ整合性/運用/コスト）**: DB・外部API・非同期・インフラ追加なし → 影響なし。
- **P6（性能・UX）**: UI なし・データ量/外部API懸念なし → 影響なし。`subprocess`（rev-parse）は push コマンド検出時のみ・1回 → オーバーヘッド軽微。
- **P9（プライバシー）**: 個人情報・未成年・テナントデータを扱わない → 影響なし。
- **設計品質**: ヘルパ分割で責務分離（`_current_branch`/`_norm_push_dest`/`_push_protected_target`）。`PROTECTED_BRANCHES` を定数化（ハードコード回避）。例外は fail-open で握り（既存フック方針と一貫）。アンチパターン（巨大関数・Raw 正規表現の乱用）を避け、正規化関数に集約。

## 設計判断の明示
| 設計判断 | 出所 |
|----------|------|
| 遮断範囲＝C（全 protected-write 経路網羅） | イシュー明記（grill 1回目確定） |
| protected 宛先検出＝宛先正規化＋完全一致の単一関数に統一・既存規則を置換改修 | イシュー明記（grill 2回目確定） |
| protected 宛先 push＝danger-op（既定 block・`DANGER_OK=1` 解除可）。無条件化は撤回 | イシュー明記（grill 4回目確定・release/hotfix のローカル push を維持するため） |
| `--all`/`--mirror` を既定 block・DANGER_OK 解除可 | イシュー明記（grill 確定） |
| テスト＝新規 `test_pretooluse_push_guard.sh`（決定論・false-green 注入） | イシュー明記（grill 3回目確定） |
| doc 同期＝`claude-code-structure.md` のみ I080 内・`issue-flow.md` vs 絶対ルール3 矛盾は別イシュー | イシュー明記（grill 4回目確定） |
| ヘルパ関数3分割（`_current_branch`/`_norm_push_dest`/`_push_protected_target`）・`PROTECTED_BRANCHES` 定数 | **理想状態基準で決定**。`_norm_push_dest` は現ブランチを引数で受ける純関数＝git 非依存で単体テスト可能。定数で単一の真実源 |
| `--all`/`--mirror` を `_push_protected_target` に混ぜず**独立チェック**に分離 | **理想状態基準で決定**（単一責務。`--all`/`--mirror` は develop/main を名指ししない別概念。既存 force/reset/docker-down と同じ独立チェック構造に統一） |
| `--repo[=]` フラグを danger-op として独立 block（パース増やさずフラグごと遮断） | **security-review で発見・決定**。`--repo` は positional 無しで remote 指定でき positional ベース検出を evade（silent protected push）。vestigial で正当用途無 → フラグ block が最小複雑度の根治。33/33 スパイク実証 |
| settings の `Bash(git push -u origin *)` を**削除**（`git push *` に完全包含される冗長エントリ） | **理想状態基準で決定**（死んだ重複を残さず「broad allow＋フックが番人」の単一モデルに集約） |
| block メッセージ文言 | 仮定で決めた（実装時に簡潔化可・挙動に影響なし） |

## レビュー結果
- [20260629_0047 判定: ✅ 完了](../../reviews/I080_plan_review_20260629_0047.md)
- [20260628_1754 判定: ✅ 完了](../../reviews/I080_plan_review_20260628_1754.md)
- [20260628_1505 判定: 差し戻し（Blocker 1件）](../../reviews/I080_plan_review_20260628_1505.md)

## セキュリティレビュー結果

**実施日**: 2026-06-28

対象はハーネスの権限設定（`.claude/settings.json`）と PreToolUse ガード（`pretooluse_guard.py`）の変更。**バックエンド/フロントエンドのアプリコード変更なし**（認証・認可・シリアライザ・モデル・URL の変更なし）。本レビューは「ガードのバイパス可能性」を中心に評価する（`git push *` を allow 化したことで、フックが取りこぼした push 形は**無確認＝silent** で protected へ到達し得るため）。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium→解消 | OWASP（Broken Access Control 類似・ガードバイパス） | `git push --repo[=]origin develop:main` 等、`--repo` で remote を positional 無しに指定すると `_push_protected_target` の「positionals[0]=remote」前提を崩し protected へ silent push し得る | `--repo[=]` を danger-op として独立 block（`DANGER_OK=1` 解除可）。33/33 スパイク実証・TC-P28〜32・TC-FALSEGREEN-E/F で担保。**解消済み** |
| Low（残余） | OWASP（Security Misconfiguration） | `git push *` を allow 化＝permission 層での push 無確認化。フック退行時に危険 push が silent 化するリスク | フック（protected/`--all`/`--mirror`/`--repo` 検出）＋`deny`（literal 形）の二重防御を維持。フック網羅性は決定論テスト＋false-green 注入で固定。`deny` は削除しない（必須） |
| Low（残余） | 認証・認可（DANGER_OK の悪用） | `DANGER_OK=1 ` 前置で protected push の escape hatch に到達できる。エージェントが手続きを無視して付与する可能性 | `DANGER_OK` は danger-ops.md の手続き（計画書明記＋danger-approved）で担保する手続き層。I080 固有でなく全 danger-op 共通の性質。機械強制はしない設計（force/reset/checkout と同一） |
| なし | 入力検証 | フックは stdin JSON のコマンド文字列を解析。ReDoS/コマンドインジェクション | 正規表現は単純（`.*` ＋ literal で catastrophic backtracking なし）。`subprocess` は**リスト引数（shell=False）**でインジェクション不可。`shlex`/`_segments` は I081 既存・検証済み |
| なし | マルチテナント / 機密情報 / ファイル操作 / 外部通信 / 依存ライブラリ | 該当なし（アプリデータ・秘匿情報・ファイル I/O・ネットワーク・新規依存いずれも無し。フックは git をローカル subprocess で呼ぶのみ） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `git push`（Claude Bash） | agent | 引数なし/refspec/`+`/`refs/heads/`/`HEAD:` で protected へ push | protected 宛先は既定 exit 2 | Yes: TC-P1〜P20,P27 | No | **静的形は網羅。動的宛先（`$(...)`/`$VAR`/`-c alias.`/`eval`・`sh -c`）は静的解析で捕捉不可＝実装後の敵対的レビューで発見・実機実証** | **残余あり→I083(#166)** |
| 2 | `git push --repo` | agent | `--repo` で remote 指定し positional ベース検出を evade | `--repo[=]` は既定 block | Yes: TC-P28〜32, FALSEGREEN-E/F | No | git 新版で未知フラグが出れば再評価要 | Low |
| 3 | `git push --all`/`--mirror` | agent | 全 ref 一括 push で protected を含める | 既定 block | Yes: TC-P21,22, FALSEGREEN-C/D | No | なし | 解消 |
| 4 | `DANGER_OK=1 git push origin develop` | agent/operator | escape hatch で protected push | release/hotfix の意図的 escape のみ。手続き（danger-approved）で担保 | Yes: TC-P6,23,31(escape が効くこと) | No: 手続き遵守は人間ゲート | DANGER_OK は手続き層・機械強制せず | Low |
| 5 | `.claude/settings.json` 自体の編集 | agent | allow/deny を書換えてガード無効化 | settings.json 編集は allow に無く ask 化 | No（I080 スコープ外） | Yes: 設定編集権限は別軸 | 設定編集権限の強化は I080 範囲外 | Low（スコープ外） |

### 残余リスク処遇
（/retro で決定する）

- **R1（Low）**: `git push *` allow 化に伴い、フック退行時の silent 危険 push。→ false-green 注入テスト（A〜F）と `deny` バックストップで継続防御。CI でフックテストを回す検討は retro 候補。
- **R2（Low）**: `DANGER_OK` の機械非強制。→ 全 danger-op 共通。手続き（danger-ops.md）で担保。I080 固有対応は不要。
- **R3（Low）**: 将来の git バージョンの未知 push フラグによる evasion。→ 現 git 2.43 では realistic 形＋`--repo` を網羅。新フラグ顕在時に再評価。
- **R4（Low・スコープ外）**: `.claude/settings.json` 自体の編集権限。→ I080 範囲外（別途検討）。
- **R5（Critical→繰り越し）**: 静的トークナイザの原理的限界により、コマンド置換 `$(...)`／変数展開 `$VAR`・`${...}`／git エイリアス `-c alias.x=...`／`eval`・`sh -c`・`bash -c` ラッパー経由の protected push を捕捉できず**無確認ですり抜ける**（例: `git push origin $(git rev-parse --abbrev-ref HEAD)` を develop 上）。**I080 実装後レビューの敵対的サブエージェントレビューで発見・実機実証**。本計画のセキュリティレビュー（攻撃シナリオ1）が「静的形＝realistic 網羅」と見做し動的宛先を検討対象外としていたのが見落としの原因。I080 は静的形保護にスコープ確定し、動的宛先の根治は **I083（#166）** で対応する（2026-06-28 決定）。
- **R6（High→繰り越し・F1）**: force push の danger-op 判定（`pretooluse_guard.py` の `re.match(r"git\s+push\b.*--force", ...)`）が**先頭アンカー＋`--force` 文字列限定**のため、`-f` 短縮形（`git push -f origin x`＝単体ですり抜け）と複合コマンド（`cd foo && git push --force origin x`）で回避される（実測 exit 0）。deny glob `Bash(git push * --force*)` も先頭一致せず空振りし、**非保護ブランチへの force push が無防備**。force 判定だけ他の danger-op（`re.search`）と一貫性を欠いていたのが原因（保護ブランチ宛は `_push_protected_target` が `_segments` 分割で捕捉するため漏れは非保護宛に限定）。**再レビュー（2026-06-29）で発見・実機実証**。根治（`re.search` 化＋`-f`/`--force-with-lease` 対応＋理想は `_segments` ベース）は **I083（#166）** で対応。
