# plan_I083: push ガードの回避経路を塞ぐ（動的宛先 ask 化＋force 取りこぼし修正）

## 基本情報
- **計画書ID**: plan_I083
- **関連イシュー**: #166
- **Draft PR**: #171
- **作成根拠資料**: docs/issues/open/I083.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I083_review.md
- **作成日**: 2026-07-01

---

## 1. 背景/目的

I080 で導入した PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）の push ガードに残る
**2つの回避経路**を実コードで根治する。いずれも I080 実装後の敵対的レビューで発見・実機実証済み。

- **欠陥1（R5・動的宛先すり抜け）**: シェル展開前の生コマンドを静的解析するため、`$(...)`/`$VAR`/
  エイリアス/`eval`・`sh -c`・`bash -c` ラッパー経由の protected push が無確認で実行到達する。
- **欠陥2（R6/F1・force 取りこぼし）**: force 判定が `re.match`（先頭アンカー）＋`--force` 文字列限定のため、
  `-f` 短縮形・複合コマンド（`cd foo && git push --force`）が danger-op ゲートを回避する。

設計判断（方式 (a) allowlist／fail-safe・ask degrade・force は `_segments` ベース・ラッパー検出は構造的 等）は
イシュー I083 の「設計確認メモ（/grill-me）」Q1〜Q8 で確定済み。本計画書はその確定値を実装に落とす。

### 調査結果（事前実証）

本イシューの正しさはハーネスのフック挙動に依存するため、**稼働中セッションで実フックにスパイク**して
前提を実証した（plan-writing-rules「外部/ハーネス挙動依存のスパイク実証」(1) 稼働中で実証可能な挙動）。

**ベースライン（develop の現行コード）**:
- `pretooluse_guard.py:243` の force 判定は `re.match(r"git\s+push\b.*--force", cmd, re.I)`（先頭アンカー＋`--force` 文字列限定）。
- 既存決定論テスト: `test_pretooluse_push_guard.sh` = **40 件 PASS**／`test_pretooluse_checkout_guard.sh` = **14 件 PASS**（無回帰ベースライン）。
- `docs/claude-code-structure.md:164` に「既知の限界（静的形のみ・後続イシューで根治予定）」注記が存在。

**実フックへの stdin JSON 投入による実測（`json.dumps` でクリーン入力・本セッション実行）**:

| コマンド | 現行 exit | 判定 |
|---|:---:|---|
| `git push --force origin x`（対照） | 2 | ✅ 正しく block |
| `git push -f origin x` | **0** | ❌ 欠陥2（短縮形すり抜け） |
| `cd foo && git push --force origin x` | **0** | ❌ 欠陥2（複合すり抜け） |
| `git push origin feature; echo "use --force later"` | **2** | ❌ **潜在誤 block**（安全 push を後続 echo の `--force` まで貪欲一致） |
| `git push origin feature && echo "--force"` | **2** | ❌ **潜在誤 block** |
| `git push --force-with-lease origin x` | 2 | △ 偶発的に block（cmd 先頭が `git push` のため `.*` が届く。複合形では漏れる） |

→ 欠陥2（取りこぼし）と**現行 `re.match` 由来の潜在誤 block** の双方を実コードで確認。pure `_segments` 化で双方を同時に根治する
（force 判定方式は Python プロトタイプで全12ケース期待一致を確認済み＝grill 第2パス記録）。動的宛先（R5）と
ラッパー構造的検出（Q8）も同様にプロトタイプで全件検証済み。

---

## 2. 受け入れ条件（Acceptance Criteria）

イシュー I083「受け入れ条件」を継承する（再掲は省略し、本計画書では実装・テストで満たす項目として扱う）。要点:

1. 6 回避形（`$(...)`・`$(git rev-parse ...)`・`$VAR`・`-c alias.`・`eval`・`sh -c`）が `not danger_ok` で全て **ask**（`permissionDecision=ask`＋exit 0）。
2. 誤検知＝hard block(exit 2) と定義。正当な動的 feature push が exit 2 されない（ask は許容）。
3. 静的安全 push（素 push・`-u origin <feature>`）が **無確認通過**（ask も block もしない）。
4. 静的 protected 形（`origin develop` 等）は従来どおり **exit 2 block** で無回帰。
5. 【F1】force 取りこぼし形（`-f`/`-uf`/`--force-with-lease`/`--force-if-includes`/`cd foo && --force`/`true; --force`）が **exit 2 block**。
6. 【F1 誤 block 回帰】`git push origin feature; echo "--force"`・`&& echo "--force"`・`--push-option=force`・`rm -f x && git push origin feature` が **無確認 pass**。
7. 【ラッパー隠蔽 force】`eval "git push --force origin x"` は block ではなく **ask**。
8. 【ラッパー誤 ask 回帰】`git push origin bash-feature`・`sh-fix`・`eval-remote feature`・`git -c user.name=x push origin feature` が **無確認 pass**。
9. `DANGER_OK=1` 前置時の escape（動的形・force 含む）維持。
10. false-green 注入で新判定行（静的安全判定／動的→ask／force／構造的ラッパー）が load-bearing であることを対で裏取り。
11. `.claude/settings.json` 不変。`docs/claude-code-structure.md` の限界注記を「対応済み（ask degrade）」＋残余既知限界へ更新。
12. 既存 `test_pretooluse_push_guard.sh`（40件）・`test_pretooluse_checkout_guard.sh`（14件）無回帰。

---

## 3. 影響範囲（Backend/Frontend/DB/Config）
- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**: `scripts/claude/hooks/pretooluse_guard.py`（PreToolUse フック）／`scripts/claude/tests/test_pretooluse_push_guard.sh`（決定論テスト）／`docs/claude-code-structure.md`（ドキュメント）。`.claude/settings.json` は**変更しない**。

セキュリティ影響: 本件はハーネス安全機構（危険操作ガード）の堅牢化そのもの。Django/React のアプリコード変更なし＝**OWASP/認可/個人情報の観点は対象外**。ガードを「より誤検知少なく・より取りこぼし少なく」する方向の変更で、権限を緩める変更は含まない（`allow: Bash(git push *)` 維持・判定はフックに集約）。

---

## 4. 変更点一覧（ファイル/関数）

### 4-1. `scripts/claude/hooks/pretooluse_guard.py`

**修正アプローチ**: (A) force 判定を pure `_segments` ベースの新ヘルパー `_push_has_force()` に置換して欠陥2＋潜在誤 block を根治。(B) 動的・不透明 push を検出する新ヘルパー `_push_is_dynamic()` を追加し、全 hard-block の**後**に `_ask()` で degrade（欠陥1）。既存の `_segments`/`_ask`/`_block` 基盤を再利用し、新規依存・新規パターンは導入しない。

| 関数 | 種別 | 内容 |
|---|---|---|
| `_FORCE_LONG` 定数 ＋ `_is_force_flag(tok)` | 新規 | force 系フラグ判定。`--force`/`--force-with-lease[=...]`/`--force-if-includes`（`=` 前で照合）＋単一ダッシュ短縮クラスタで `f` を含む（`-f`/`-uf`/`-fu`）を True。`--push-option=force` 等は False。 |
| `_push_has_force(cmd)` | 新規 | `_segments` で push を含むセグメントの `push` 以降トークンに `_is_force_flag` 該当があれば True。 |
| `_push_is_dynamic(cmd)` | 新規 | (i) 直接 push: git+push を含むセグメントの `push` 以降引数に動的メタ文字（`$` `` ` `` `{` `(`）があれば True。(ii) 構造的ラッパー: セグメント先頭が `eval`／`sh`・`bash`・`dash`・`zsh`＋`-c`／`git` の `-c` 値が `alias.` 始まり、かつ**その wrapper セグメント自体が `push` を含む**場合 True。グローバルに `git`/`push` 両方が無ければ即 False。 |
| `main()` 内 force 判定 | 置換 | 既存 `if re.match(r"git\s+push\b.*--force", ...)`（:242-244）を `if _push_has_force(cmd):` に置換（block メッセージは現行踏襲）。 |
| `main()` 末尾（`not danger_ok` ブロックの psql 判定の後・`sys.exit(0)` の直前） | 追加 | `if _push_is_dynamic(cmd): _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")`。**全 hard-block の後**に置くことで rm -rf 等の同居 danger-op を ask で先食いしない。 |

**具体コード例（実装の確定形）**:

```python
# --- force フラグ判定（_segments ベース・I083 欠陥2/F1） ---
_FORCE_LONG = ("--force", "--force-with-lease", "--force-if-includes")

def _is_force_flag(tok: str) -> bool:
    """push の force 系フラグなら True。--push-option=force 等の非 force 用法は False。"""
    if tok.startswith("--"):
        return tok.split("=", 1)[0] in _FORCE_LONG
    if tok.startswith("-") and len(tok) > 1:          # 単一ダッシュ短縮クラスタ（-f/-uf/-fu）
        # 単一ダッシュで 'f' を含む全クラスタを force として扱う（git push の短縮フラグで 'f' は -f のみ）。
        # 注: `-rf` 等の非実在フラグも True になるが、push セグメント内で `-rf` は無効構文＝実害なし。
        return "f" in tok[1:]
    return False

def _push_has_force(cmd: str) -> bool:
    """push を含むセグメントの push 以降トークンに force 系フラグがあれば True。
    複合コマンド・短縮結合形に頑健（_segments でセグメント分割）。"""
    for toks in _segments(cmd):
        if "git" in toks and "push" in toks:
            after = toks[toks.index("push") + 1:]
            if any(_is_force_flag(t) for t in after):
                return True
    return False

# --- 動的・不透明 push 判定（ask degrade・I083 欠陥1） ---
_WRAP_SHELLS = ("sh", "bash", "dash", "zsh")

def _push_is_dynamic(cmd: str) -> bool:
    """静的に宛先を確定できない push なら True（ask に degrade する対象）。
    (i) 直接 push の引数に動的メタ文字。(ii) 構造的に不透明なラッパーが push を隠蔽。
    脅威モデル=事故。push トークンが完全隠蔽される eval \"$VAR\" 形は対象外（既知の限界）。"""
    if not (re.search(r"\bgit\b", cmd) and re.search(r"\bpush\b", cmd)):
        return False
    for toks in _segments(cmd):
        # (i) 直接 push: push 以降の引数領域に動的メタ文字（宛先トークン分離に依存しない）
        if "git" in toks and "push" in toks:
            after = " ".join(toks[toks.index("push") + 1:])
            if any(ch in after for ch in "$`{("):
                return True
        # (ii) 構造的に不透明なラッパー（先頭トークンで判定＝branch/remote 名の偶然一致を排除）
        if not toks:
            continue
        head = toks[0]
        if head == "eval" and any("push" in t for t in toks[1:]):
            return True
        if head in _WRAP_SHELLS and "-c" in toks:
            ci = toks.index("-c")
            wrapped = toks[ci + 1] if ci + 1 < len(toks) else ""
            if "push" in wrapped:
                return True
        if head == "git":
            for i, t in enumerate(toks[:-1]):
                if t == "-c" and toks[i + 1].startswith("alias.") and "push" in toks[i + 1]:
                    return True
    return False
```

### 4-2. `scripts/claude/tests/test_pretooluse_push_guard.sh`
I083_auto_test.md の TC 群（動的→ask・force 取りこぼし→block・force 誤 block 回帰→pass・ラッパー隠蔽 force→ask・ラッパー誤 ask 回帰→pass・DANGER_OK escape・false-green 注入・限界注記 grep）を追記。
**ヘルパー**: 既存 `run`/`rung`（exit code）・`ck` を流用。**新規追加** `runj`（実フックの stdout を捕捉し `exit 0 ＋ "permissionDecision": "ask"` なら文字列 `ASK`、それ以外は exit code を返す）と `rungj`（壊した版フック変種）。**ask と pass は exit code が同一（0）**のため、ask 系・「ask されないこと」固定系・ask の false-green 注入（TC-FG-I/J/K）は必ず `runj`/`rungj` で判別する（詳細は auto_test.md「ハーネス追加」を参照）。

### 4-3. `docs/claude-code-structure.md`
`:164-166` の「既知の限界（静的形のみ・後続イシューで根治予定）」注記を「**対応済み（I083 / ask degrade）**」へ更新。残余の既知限界（push トークンを完全隠蔽する `eval "$VAR"` 形＝脅威モデル外・`DANGER_OK=1` 解除に委ねる）を honest scoping として明記。

---

## 5. 実装手順（ステップ）

各ステップの検証は自動テスト文書の TC を参照（plan-writing-rules「検証コマンドを書かない」）。本イシューは単一レイヤー（フック）の決定論ロジック変更のため、垂直スライスは「判定ロジック＋テスト＋ドキュメント」を 1 単位とする。ステップ2はステップ1の完了が前提（ステップ3・4は独立）。

- **ステップ0（未知リスク先行・実証済み）**: 実フックへのスパイクで欠陥2＋潜在誤 block を実測（§1 調査結果）。本セッションで成立済みのため、実装は確定設計で進められる。
- **ステップ1【欠陥2/F1: force】**: `_FORCE_LONG`/`_is_force_flag`/`_push_has_force` を追加し、`main()` の force 判定を置換。→ TC-F1〜F8 参照（取りこぼし→block・誤 block 回帰→pass・ラッパー隠蔽→後段 ask）。
- **ステップ2【欠陥1/R5: 動的 ask】**: `_push_is_dynamic` を追加し、`not danger_ok` ブロック末尾（全 hard-block の後）に `_ask` を追加。→ TC-D1〜D9・TC-W1〜W4 参照（動的→ask・静的安全→pass・ラッパー誤 ask 回帰→pass・rm -rf 同居→block 維持）。
- **ステップ3【false-green 注入】**: 新判定行（force `_push_has_force`／短縮クラスタ `_is_force_flag`／動的→ask `_push_is_dynamic`／構造的ラッパー `eval`・`sh -c` 分岐／`-c alias.` 分岐）を一時的に壊した入力で TC が NG になることを対で裏取り。ask 系（TC-FG-I/J/K）は exit code でなく ask JSON で判別。→ TC-FG-G/H/I/J/K 参照。
- **ステップ4【ドキュメント】**: `docs/claude-code-structure.md` の限界注記を更新。→ TC-DOC1（a/b/c）参照（grep で旧注記不在・新注記存在・残余限界明記を判定）。

---

## 6. テスト計画（自動/手動）
- **自動（決定論）**: `docs/tests/open/I083_auto_test.md`。`test_pretooluse_push_guard.sh` を拡張。テストレベル＝**ユニット相当**（実フックへ stdin JSON を投入し exit code／stdout JSON を検証）。再発防止テスト（force 取りこぼし・潜在誤 block の双方）を**負例・正例の対**で固定。false-green 注入で各判定行が load-bearing であることを裏取り。
- **手動**: `docs/tests/open/I083_manual_test.md`。大半は Claude がテストスクリプト実行で代替可。**ハーネス統合の 1 点のみ**（ask JSON が実セッションで実際の確認プロンプトとして描画されるか）は稼働中セッションでは発生源を区別できないため **プレーン default 新規セッション／Human 目視**（実施環境列）。

---

## 7. ロールバック
フック・テスト・ドキュメントのみの変更で、DB マイグレーション・サービス再起動は不要。問題時は当該コミットを revert すれば I080 時点の挙動に戻る（フックは即時反映＝次の Bash 呼び出しから旧判定）。`.claude/settings.json` は不変のため権限面の巻き戻しは不要。

---

## 8. Risk & 回避策
| Risk | 回避策 |
|---|---|
| ask degrade が正当な動的 feature push を過剰に止める（運用ノイズ） | Q2 で確定: 誤検知＝hard block のみ。ask は exit 0 で承認すれば実行可。ノイズは「曖昧なら安全側」の許容コストとして AC で固定。アラーム疲労を避けるためラッパー検出は構造的＝branch/remote 名の偶然一致では発火しない（TC-W1〜W4）。 |
| 動的 ask を hard-block より前に置くと rm -rf 等の同居 danger-op を ask で先食いする | `_push_is_dynamic` の `_ask` を `not danger_ok` ブロック**末尾**（全 hard-block の後）に配置。`git push origin $VAR && rm -rf x` は rm -rf block(exit2) が先に効くことを TC-D9 で固定。 |
| force 判定の `_segments` 化で既存 block 形が漏れる | AC4 force 形＋既存 P25/P26/Pregr1 を TC で無回帰確認。false-green 注入（TC-FG-G/H）で判定行が load-bearing であることを裏取り。 |
| ラッパー隠蔽 force（`eval "git push --force"`）が block されず弱体化 | 設計判断（Q7）: 脅威モデル＝事故では intent 可視。意図的偽装は対象外＋`DANGER_OK=1` 解除可。block でなく ask に degrade することを TC-F7 で固定（silent 実行は防止）。 |
| 残余の既知限界（`eval "$VAR"` 完全隠蔽）を「対応済み」と誤読 | `docs/claude-code-structure.md` に honest scoping として明記（TC-DOC1）。 |

---

## 9. 承認ポイント（ユーザーがOKを返すチェックリスト）

別途本文末尾に提示する。

## レビュー結果
- [20260701_0055 判定: ✅ 完了](../../reviews/I083_plan_review_20260701_0055.md)
