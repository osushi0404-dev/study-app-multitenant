# I134 自動テスト（issue_template 背景/目的プレースホルダ追加＋open イシュー形式統一 sweep）

- 関連: docs/issues/open/I134.md / docs/plans/open/plan_I134.md / GitHub #242 / Draft PR #249
- 対象: `docs/issues/templates/issue_template.md`・`scripts/claude/check-issue-background.sh`（新規）・`docs/issues/open/*.md`（25 件）・GitHub open イシュー本文（38 件）
- テストレベル: 決定論 TC のみ（grep / awk / diff・合否判定は exit code に統一・合格=exit 0）。ユニット/結合/E2E は対象コードが無いため非該当。

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-01 | テンプレートにプレースホルダ 2 行が存在（AC-1/2） | (a) `grep -q '^\*\*背景\*\*:' docs/issues/templates/issue_template.md` (b) `grep -q '^\*\*目的\*\*:' docs/issues/templates/issue_template.md` | (a)(b) とも **exit 0** | Claude |
| TC-02 | wt-harness open 全件にラベル 2 行が存在（AC-3） | `bash scripts/claude/check-issue-background.sh docs/issues/open` | **exit 0**（`OK: all files have 背景/目的 labels`） | Claude |
| TC-02-inject | TC-02 チェッカーの検知能力（実装後の注入再確認） | scratchpad にラベル無しダミー md を置いたディレクトリへ `bash scripts/claude/check-issue-background.sh <dir>` | **exit 1**（MISSING 列挙）→ ダミー削除 | Claude |
| TC-03 | GitHub open 全 41 件の本文にラベル 2 行が反映（AC-4） | 下記「TC-03 スクリプト」を scratchpad に保存し `bash <scratchpad>/tc03_gh_labels.sh` を実行 | **exit 0**（`total=41 missing=0`） | Claude |
| TC-04 | tracked 分の無改変保証（挿入のみ・削除ゼロ） | 下記「TC-04 スクリプト」を scratchpad に保存し `bash <scratchpad>/tc04_no_deletion.sh` を実行 | **exit 0**（削除列がすべて 0） | Claude |
| TC-05 | untracked 分の無改変保証（挿入のみ） | 下記「TC-05 スクリプト」を scratchpad に保存し `bash <scratchpad>/tc05_untracked_insert_only.sh <snapshot_dir>` を実行（比較基準はステップ2-1 のスナップショット） | **exit 0**（全 13 件で削除行なし） | Claude |
| TC-06 | GitHub 直接更新分の無改変保証（挿入のみ・ローカル対応の無い 26 件） | 下記「TC-06 スクリプト」を scratchpad に保存し `bash <scratchpad>/tc06_gh_insert_only.sh <退避dir>` を実行（比較基準はステップ3-1 の退避原本） | **exit 0**（全 26 件で削除行なし） | Claude |

注:
- 合否判定インターフェースは全 TC で exit code に統一（合格=exit 0）。不在・無削除の判定は `! grep -q` / awk の exit 畳み込み形。
- TC-03〜06 はスクリプトファイル実行形（`bash <file>`）に統一する（plan-review Warning 対応: パイプ複合コマンドの直接実行を避け、allowlist 単体形 `bash` 1 コマンドで走らせる。スクリプト本文は下記に全文を記載し実装者の再構築を不要にする）。

### TC-03 スクリプト（tc03_gh_labels.sh・計画時 G3 実証と同一ロジック）
```bash
#!/usr/bin/env bash
set -u
missing=0
total=0
for n in $(gh issue list --state open --limit 100 --json number --jq '.[].number'); do
  total=$((total + 1))
  body=$(gh issue view "$n" --json body --jq .body)
  if ! printf '%s\n' "$body" | grep -q '^\*\*背景\*\*:' || ! printf '%s\n' "$body" | grep -q '^\*\*目的\*\*:'; then
    echo "MISSING: #$n"
    missing=$((missing + 1))
  fi
done
echo "total=$total missing=$missing"
[ "$missing" -eq 0 ] && exit 0 || exit 1
```

### TC-04 スクリプト（tc04_no_deletion.sh）
```bash
#!/usr/bin/env bash
set -u
# I134.md 自身は sweep 対象でなく本イシューの管理文書（Draft PR 追記・AC 文言整合で行置換が正当に入る）ため除外する
git diff --numstat origin/develop...HEAD -- docs/issues/ ':(exclude)docs/issues/open/I134.md' | awk '$2!=0{print "DELETION:",$0; bad=1} END{exit bad?1:0}'
```

### TC-05 スクリプト（tc05_untracked_insert_only.sh・引数=スナップショット dir）
```bash
#!/usr/bin/env bash
set -u
SNAP="${1:?Usage: $0 <snapshot_dir>}"
bad=0
for f in docs/issues/open/*.md; do
  b=$(basename "$f")
  [ -f "$SNAP/$b" ] || continue
  if diff "$SNAP/$b" "$f" | grep -q '^<'; then
    echo "DELETED-LINES: $f"
    bad=1
  fi
done
exit "$bad"
```

### TC-06 スクリプト（tc06_gh_insert_only.sh・引数=退避原本 dir。原本は `<#>.md` 名で保存しておく）
```bash
#!/usr/bin/env bash
set -u
ORIG="${1:?Usage: $0 <original_bodies_dir>}"
bad=0
for o in "$ORIG"/*.md; do
  n=$(basename "$o" .md)
  gh issue view "$n" --json body --jq .body > "$ORIG/$n.after"
  if diff "$o" "$ORIG/$n.after" | grep -q '^<'; then
    echo "DELETED-LINES: #$n"
    bad=1
  fi
done
exit "$bad"
```
- ラベル判定は行頭アンカー（`^\*\*背景\*\*:`）。引用ブロック内の同形行との誤検知限界は計画 リスク2 に記録済み（現状の該当は I134 本文のみで実害なし）。

## false-green 自己検証

### 計画時に前倒し実施済み（2026-07-19）
- **TC-01 相当（G1）**: 未実装のテンプレートに対し grep 2 本 → **両方 exit 1（NG）** 実測＝欠落を正しく検知。実装後の exit 0 転化が合否。
- **TC-02 相当（G2）**: チェッカーロジックを現状 `docs/issues/open` へ実行 → **exit 1・MISSING 25 件**（計画 調査結果 (A) と同一リスト）。合格系（I134 のみの dir）→ **exit 0**。注入系（ラベル無しダミー混入）→ **exit 1** 復帰。
- **TC-03 相当（G3）**: GitHub 41 件走査 → **exit 1・missing=38**（計画 調査結果 (B) と同一リスト）。
- **TC-04 相当（G4）**: awk 判定へ削除 0 入力 → exit 0・削除 1 入力 → **exit 1** 実測。
- **TC-05/06 相当（G5・同一ロジック）**: diff 判定へ挿入のみ → 合格・行削除入り → **不合格（`^<` 検知）** 実測。

### 実装後に実施
- **TC-02-inject**: リポジトリ常設のチェッカー本体に対する注入再確認（ダミーファイル方式・上表）。他の TC は入力注入型で計画時実証から判定ロジックが変わらないため再注入不要。

## 実施記録
（/implement・/test 実施時に記入）
