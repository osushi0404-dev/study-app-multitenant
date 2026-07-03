# I098 計画書: 採番権威の堅牢化 — 全 worktree 横断採番スクリプトへの一元化

## 基本情報
- **計画書ID**: plan_I098
- **関連イシュー**: #184
- **Draft PR**: #188
- **作成根拠資料**: docs/issues/open/I098.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I098_review.md
- **作成日**: 2026-07-04

---

## 1. 背景/目的

### 原因の概要（平易）
`/issue-bootstrap` 直後のイシューファイルは **untracked（未コミット）** で、それを作った worktree からしか見えない。別 worktree で起票すると互いの untracked が不可視で、**同じ番号を二重採番**しうる。現行採番は「単一 worktree の FS 最大 + git 履歴最大」しか見ておらず、他 worktree の untracked を含まないのが根本原因。

### 詳細な原因分析
- 採番の入力が現 worktree に閉じている（`find docs/issues ...` は自分の作業ツリーのみ）。
- untracked ゆえ git 共有もされないため、`git log` 経由でも他 worktree の起票中イシューは見えない。
- 結果として採番権威が「primary で採番する」という**人手規律**（worktree.md §8）に依存している。

### 調査結果（スパイク実証済み・稼働セッション内）
横断採番アルゴリズムを scratchpad プロトタイプで実証した（read-only）。実リポジトリの現状に対し:

- `study-app-multitenant`（primary）: `docs/issues` FS 最大 = **091**（＝レビュー時に「wt-harness から不可視」だった untracked I085〜I091 が、横断スキャンでは見える）
- `wt-harness`: FS 最大 = **098**
- `git log --all` 履歴最大 = **098**
- 横断 `max(091, 098, 098) + 1` = **I099** を出力（`exit 0`）

→ **本イシューの再現ケース（primary の untracked が別 worktree から不可視）が横断スキャンで解消されることを実機で確認**。

追加でパターンの健全性（I094 decoy）も実証:
- 既存の `\d+(?=\.md)` は **`draft-I200.md` を `200` と誤マッチ**（decoy 誤カウント）。
- アンカー版 `/I?\K\d+(?=\.md$)` は `I098.md`/`098.md` のみ一致し、`draft-I200.md`・`I098-backup.md`・`error_I016.md`・`issue_template.md` を全て不一致（decoy を排除）。
- git 履歴最大は **commit subject 走査**（現行 `grep -oP 'I0*\d+'`）だと無関係な番号言及を拾いうる。**touched file path をアンカー抽出**（`git log --all --name-only --pretty=format: -- 'docs/issues' | grep -oP '/I?\K\d+(?=\.md$)'`）に変えると、削除済みファイルも含めつつ subject 誤マッチを排除できることを確認（現状はどちらも 098）。

### 目的
採番の入力に**全 worktree 横断**（untracked 含む）を含める仕組みを単一スクリプトに一元化し、**任意の worktree で同一の大域一意番号**を算出可能にする（採番権威の単一化＝人手規律の撤廃・根治）。

---

## 2. 受け入れ条件
- [ ] 複数 worktree に未コミットのイシューが存在しても、採番が全 worktree を通じて一意になる（二重採番が起きない）
- [ ] 再現ケース（primary の untracked I085〜I091 が wt-harness から不可視）が更新後の採番手順（`scripts/claude/next-issue-num.sh`）で回避される
- [ ] `scripts/claude/next-issue-num.sh` が新規作成され、全 worktree 横断（untracked 含む）＋`git log --all` で `max(...)+1` を算出する
- [ ] 成功時は **3 桁ゼロ詰めの番号のみ**を stdout に出力し、重複検出時は stdout に番号を出さず**非 0 終了**する（consumer の `ISSUE_NUM=$(...)` 契約が成立）
- [ ] `docs/runbooks/issue-flow.md`（3 箇所）と `.claude/skills/issue-bootstrap/SKILL.md`（1 箇所）の計 4 箇所の採番 bash が `next-issue-num.sh` 呼び出しに置換され、ロジック重複が解消されている
- [ ] `docs/runbooks/worktree.md` §8 が「任意 worktree でスクリプト実行=権威単一化」に更新され、旧「primary で採番/速やかに取り込む」人手規律が撤廃されている
- [ ] 他 worktree の読み取りが I095 の読み取り許可方針と衝突しない（読み取りのみ・書込なし）
- [ ] `scripts/claude/tests/test_next_issue_num.sh` が再現ケース＋I094 decoy 反証を検証し、全 PASS する

---

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `scripts/claude/next-issue-num.sh`（新規）・`scripts/claude/tests/test_next_issue_num.sh`（新規）・`docs/runbooks/issue-flow.md`・`docs/runbooks/worktree.md`・`.claude/skills/issue-bootstrap/SKILL.md`

**波及チェック**: 依存関係ファイル（requirements/package）変更なし → Dockerfile/compose 波及なし。**セキュリティ影響なし**（read-only の bash・機密データ非取扱）。**P3/P5/P6/P8/P9 影響なし**（DB/外部API/UI/新規インフラ/個人情報なし）。

---

## 4. 変更点一覧（具体）

### 4-1. 新規 `scripts/claude/next-issue-num.sh`（採番権威の単一実装）
**修正方針**: 全 worktree 横断 FS 最大 ＋ git 履歴最大 の `max+1` を 3 桁で stdout 出力。read-only。重複検出で非 0 停止。

```bash
#!/usr/bin/env bash
set -euo pipefail
# I098: イシュー採番の単一権威。全 worktree（git worktree list）の docs/issues FS 最大
# （untracked 含む）＋ git 履歴最大から max+1 を算出し 3 桁ゼロ詰めで stdout に出力する。
# read-only（I095 は横断読み取りを許可）。確定番号が既存なら stderr にエラー・非 0 終了。
# 呼び出し元: docs/runbooks/issue-flow.md ・ .claude/skills/issue-bootstrap/SKILL.md

# パターン（I094 decoy 対策・アンカー）: パス末尾が /I###.md または /###.md のときの数字のみ抽出。
#   例: /.../open/I098.md→098 ・ /.../closed/098.md→098 ・ draft-I200.md/error_I016.md→不一致
ISSUE_NUM_RE='/I?\K\d+(?=\.md$)'

worktrees() { git worktree list --porcelain | sed -n 's/^worktree //p'; }

max=0
update_max() {  # $1=数字文字列（空可）。8 進誤解釈を防ぐ 10# で比較。
  local n="${1:-}"; [ -n "$n" ] || return 0
  n=$((10#$n)); [ "$n" -gt "$max" ] && max="$n"; return 0
}

# 1) 全 worktree の FS 最大（untracked 含む・docs/issues 配下のみ）
while IFS= read -r wt; do
  [ -d "$wt/docs/issues" ] || continue
  update_max "$(find "$wt/docs/issues" -name '*.md' 2>/dev/null \
                 | grep -oP "$ISSUE_NUM_RE" | sort -n | tail -1 || true)"
done < <(worktrees)

# 2) git 履歴最大（削除済み含む・全 ref・touched file path をアンカー抽出）
update_max "$(git log --all --name-only --pretty=format: -- 'docs/issues' 2>/dev/null \
               | grep -oP "$ISSUE_NUM_RE" | sort -n | tail -1 || true)"

ISSUE_NUM="$(printf '%03d' "$((max + 1))")"

# 3) gate（fail-loud）: 確定番号が全 worktree のいずれにも未存在であることを assert
while IFS= read -r wt; do
  for f in "$wt/docs/issues/open/I${ISSUE_NUM}.md"   "$wt/docs/issues/closed/I${ISSUE_NUM}.md" \
           "$wt/docs/issues/open/${ISSUE_NUM}.md"    "$wt/docs/issues/closed/${ISSUE_NUM}.md"; do
    [ -e "$f" ] && { echo "[next-issue-num] 確定番号 I${ISSUE_NUM} が既に存在: $f（採番権威の不整合）" >&2; exit 1; }
  done
done < <(worktrees)

printf '%s\n' "$ISSUE_NUM"
```

### 4-2. `docs/runbooks/issue-flow.md`（3 箇所の重複 bash を置換）
**修正方針**: 「### 採番ルール」（§イシュー新規作成時）・「### 1. イシュー番号の採番」（§自動実行フロー）・「ステップ1」（§フェーズ1）の 3 つの採番 bash ブロックを、以下のスクリプト呼び出しに置換。プロセス説明文の「FS 最大 + git 履歴最大」を「**全 worktree 横断（untracked 含む）+ git 履歴最大**」に更新し、`scripts/claude/next-issue-num.sh` を参照させる。

```bash
# 採番（全 worktree 横断＋git履歴。重複検出時は非0終了）
ISSUE_NUM=$(bash scripts/claude/next-issue-num.sh) || {
  echo "採番に失敗しました（重複検出またはエラー）。git worktree list と docs/issues を確認してください。" >&2
  exit 1
}
echo "次のイシュー番号: $ISSUE_NUM"
```

「**重要**: ファイルシステムだけでなく git 履歴も必ず確認」の注記は「**重要**: 採番は必ず `next-issue-num.sh` 経由で行う（全 worktree 横断＋git 履歴＋重複検出を一括実施）」に更新。

### 4-3. `.claude/skills/issue-bootstrap/SKILL.md`（1 箇所を置換）
**修正方針**: 「### 2. イシュー番号の採番」の bash ブロックを 4-2 と同一のスクリプト呼び出しに置換。直後の「**重要**: ...git 履歴も必ず確認」も同様に更新。step 3 以降（`I${ISSUE_NUM}.md` 生成）は既存契約（3 桁番号）のまま無改変。

### 4-4. `docs/runbooks/worktree.md` §8（人手規律の撤廃）
**修正方針**: §8「採番の一貫性」を、権威単一化に書き換える。

- Before（人手規律）: 「採番は権威となる作業ツリー（primary）で行うか、起票後すみやかに develop へ取り込む」
- After（機械化）: 「採番は必ず `scripts/claude/next-issue-num.sh` 経由で行う。本スクリプトは `git worktree list` で全 worktree の `docs/issues`（untracked 含む）＋`git log --all` を横断集計するため、**どの worktree から実行しても同一の大域一意番号**が得られる（採番権威が単一化）。primary 固定・事前取り込みの人手規律は不要。読み取りのみで I095 の横断ガードに抵触しない。」

### 4-5. 新規 `scripts/claude/tests/test_next_issue_num.sh`（決定論検証）
**修正方針**: `test_wt_port_offset.sh` と同じ隔離方式（temp bare origin + primary clone + linked worktree）で、docs/issues を作り込み、`next-issue-num.sh` の出力を検証。TC は §6 参照。

---

## 5. 実装手順（ステップ）

- **ステップ1**〔未知リスク先行〕: `scripts/claude/next-issue-num.sh` を新規作成（4-1）。※アルゴリズムは scratchpad で実証済み（調査結果）。→ 検証は TC-N1〜N6 参照（`docs/tests/open/I098_auto_test.md`）。
- **ステップ2**: `scripts/claude/tests/test_next_issue_num.sh` を新規作成（4-5）。→ TC-N1〜N6 を実装・全 PASS を確認。
- **ステップ3**: `docs/runbooks/issue-flow.md` の 3 箇所の採番 bash を置換（4-2）。→ TC-DOC1 参照。
- **ステップ4**: `.claude/skills/issue-bootstrap/SKILL.md` の 1 箇所を置換（4-3）。→ TC-DOC2 参照。
- **ステップ5**: `docs/runbooks/worktree.md` §8 を書き換え（4-4）。→ TC-DOC3 参照。
- **ステップ6**: 消費箇所の全件確認 — repo 全体を `grep -rn 'FS_MAX=\$(find docs/issues'` して旧採番 bash の残存が 0 であることを確認。→ TC-DOC4 参照。

**依存関係**: ステップ2 はステップ1 の完了が前提。ステップ3〜5 は独立（並行可）。ステップ6 はステップ3〜5 の完了が前提。

---

## 6. テスト計画

### 自動（`docs/tests/open/I098_auto_test.md`・`test_next_issue_num.sh`）
- **TC-N1（再現ケース・中核 AC）**: primary=`I050.md`（untracked）、linked worktree=`I030.md`（untracked）。linked worktree から実行 → **`051`**（他 worktree の高番号 untracked を横断で拾う）。
- **TC-N2（git 履歴・削除済み）**: `I060.md` を commit → 削除して commit（FS からは消える）。FS 最大が 40 でも履歴最大 60 → **`061`**。
- **TC-N3（I094 decoy: 部分一致）**: docs/issues に `draft-I200.md`・`I055-backup.md`（decoy）を置く。実 issue が `I040.md` のみ → decoy を無視して **`041`**（`200`/`055` に釣られない）。
- **TC-N4（I094 decoy: 非近接/subject 誤マッチ）**: 実 issue `I040.md`、別途 commit message に「refs docs/issues I900」等の高番号を含めても、file-path 抽出のため無視 → **`041`**。
- **TC-N5（出力契約）**: 成功時 stdout は `^[0-9]{3}$` の 1 行のみ（余計な行なし・末尾改行）。
- **TC-N6（gate fail-loud・false-green 反証）**: assert を除去した複製（`sed` で gate ブロックを無効化）に、確定番号と同じファイルを別 worktree へ注入 → 除去版は誤って番号を出力、**本体は非 0 終了 + stderr にエラー**（assert が実体の停止要因である反証）。

### 決定論ゲート（`/code-review` 自動実走・auto_test.md に記載）
- `bash scripts/claude/tests/test_next_issue_num.sh`

### 手動（`docs/tests/open/I098_manual_test.md`）
- 実リポジトリで `bash scripts/claude/next-issue-num.sh` を実行し、全 worktree 横断で妥当な次番号（現状 `099`）が返ることを確認（Claude 実施可）。
- issue-flow.md / SKILL.md / worktree.md §8 の記述整合を目視（Claude 実施可）。

### TC-DOC（記述整合・決定論）
- **TC-DOC1**: issue-flow.md に `next-issue-num.sh` が 3 箇所以上出現し、旧 `FS_MAX=$(find docs/issues` が 0 件。
- **TC-DOC2**: SKILL.md に `next-issue-num.sh` が出現し、旧 `FS_MAX=$(find docs/issues` が 0 件。
- **TC-DOC3**: worktree.md §8 に `next-issue-num.sh`・「権威」語が出現し、旧「primary で行うか」文言が除去されている。
- **TC-DOC4**: repo 全体で旧採番 bash（`FS_MAX=$(find docs/issues`）が 0 件。

---

## 7. ロールバック
- 全変更は文書＋新規スクリプトのみ。`git revert` で復旧可能。新規 2 ファイルを削除し、issue-flow.md / SKILL.md / worktree.md を元に戻せば旧採番（単一 worktree）に戻る。DB・データ非関与。

---

## 8. Risk & 回避策
- **R1: `find -name '*.md'` が docs/issues 配下の非イシュー md を拾う** → アンカー正規表現 `/I?\K\d+(?=\.md$)` で `I###.md`/`###.md` のみに限定（TC-N3 で反証）。
- **R2: git 履歴の subject 誤マッチ** → touched file path 抽出に変更（TC-N4 で反証）。
- **R3: 別 worktree 読み取りが I095 にブロックされる** → I095 は**書込のみ**ブロック・読み取りは許可（`pretooluse_guard.py` 実装確認済み）。本スクリプトは find/git の read-only のみ。
- **R4: 同時 bootstrap（2 worktree ほぼ同時）の TOCTOU** → **スコープ外**（単一逐次オペレータ前提）。gate（存在 assert）で事後の取りこぼしは fail-loud 化。ロック機構は入れない。
- **R5: `set -euo pipefail` 下で grep 無一致（exit 1）が全体を落とす** → 各コマンド置換に `|| true` を付与（プロトタイプで検証済み）。

---

## 9. 承認ポイント
- [ ] 計画内容（横断スキャン方式・スクリプト一元化・4 箇所置換・§8 撤廃）
- [ ] **【要判断①】I094 decoy 対策として、既存の緩いパターン `\d+(?=\.md)` を踏襲せず、アンカー版 `/I?\K\d+(?=\.md$)` に強化する**（スパイクで `draft-I200.md` 誤カウントを実証）。イシューは「両対応を踏襲」だったが、decoy 堅牢性のため**改善提案**。
- [ ] **【要判断②】git 履歴最大を commit subject 走査ではなく touched file path 抽出に変更する**（subject 誤マッチ排除・削除済みは維持）。同じく**改善提案**。
- [ ] Danger Ops: 無（read-only スクリプト＋文書更新）
- [ ] テスト計画（TC-N1〜N6＋TC-DOC1〜4・決定論ゲート自動実走）

### 設計判断の明示（イシュー明記 / 仮定・提案の区別）
| 判断 | 区分 |
|------|------|
| 横断スキャン方式・即コミット不採用 | イシュー明記（grill 確定） |
| スクリプト一元化・4 箇所置換 | イシュー明記 |
| 出力契約（3 桁 stdout・重複時非0） | イシュー明記 |
| 入力集合（全 worktree FS＋git履歴 の max+1） | イシュー明記 |
| 存在 assert（fail-loud gate）・TOCTOU スコープ外 | イシュー明記 |
| **アンカー正規表現への強化（要判断①）** | **提案（スパイク発見・イシューの「踏襲」から逸脱）** |
| **git 履歴を file path 抽出へ変更（要判断②）** | **提案（スパイク発見）** |
