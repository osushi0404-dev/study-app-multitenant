## 基本情報
- **計画書ID**: plan_I134
- **関連イシュー**: #242
- **Draft PR**: #249
- **作成根拠資料**: docs/issues/open/I134.md（起点イシュー・grill-me 設計確認メモ確定済み）
- **実装後評価**: docs/reviews/open/I134_review.md
- **作成日**: 2026-07-19

---

## 1. 背景/目的

I132 のイシュー本文で `## 背景/目的` セクションに小見出し 3 つ（現状の問題・根本原因・解決方針）だけが書かれ、肝心の「背景」「目的」が記載されないままレビューを通過し、ユーザー指摘で発覚した。

- **原因の概要**: テンプレート（`docs/issues/templates/issue_template.md`）の `## 背景/目的` 直下にセクション名に対応する記述欄（プレースホルダ）が無いため、テンプレートを埋めるだけでは背景・目的が書かれない構造になっている。
- **詳細な原因分析**:
  1. テンプレートの `## 背景/目的`（6〜15 行目）は配下に「現状の問題」「根本原因」「解決方針」の 3 小見出しのみを持ち、背景（経緯）・目的（達成したい状態）を書く欄が無い。
  2. issue-review（`issue-reviewer.md`）は「テンプレートの説明文がそのまま残っている場合のみ未記入とする」判定のため、**そもそも記述欄が無い項目の抜けは検出できない**（I132 で実証）。
  3. この構造は全既存イシューに共通するため、/grill-me の点検実走で open イシューの**実質ほぼ全件**（ローカル 53 件中ラベル保有 3 件・GitHub 41 件中保有 3 件）に同じ抜けがあると確定した。
- **根本原因（ファイルレベル）**: `issue_template.md` の `## 背景/目的` 直下にプレースホルダ行が無いこと。

**目的**: テンプレートに `**背景**:` / `**目的**:` のプレースホルダ 2 行を追加して「テンプレート埋め＝抜けなし」の構造にし、既存 open イシュー全件にも同ラベル 2 行を追記して形式統一する（grill-me 確定: 形式統一方式・GitHub を正として更新・隣 worktree 分は引き継ぎ）。

## 調査結果

### 環境前提確認（2026-07-19 実施）
- `gh` 認証済み・イシュー本文の取得/編集可能（本セッションで `gh issue list` / `gh issue view` / `gh issue edit 242 --body-file` 実行成功済み）。
- 追加ツール不要（bash / grep / awk / diff のみ。`gh --jq` を使うため `jq` 単体は不要）。
- Docker・BE/FE テスト環境は不要（docs とスクリプト 1 本のみ・アプリコード変更ゼロ）。

### 消費箇所の全件列挙（テンプレート形式是正イシュー）
`## 背景/目的` の宣言箇所・消費箇所を grep で確認済み:
- **宣言箇所**: `docs/issues/templates/issue_template.md` の 1 箇所のみ。
- **消費箇所**: `issue-bootstrap/SKILL.md`（42 行目 `cp` でテンプレートを複製 → **テンプレート修正だけで自動追随・変更不要**）／`issue-reviewer.md`（プレースホルダ説明文の残存を未記入判定 → 追加する 2 行は `（…）` 形式のため**変更なしで検出対象に入る**・AC-2 成立）／`dependency-audit-issue.sh`（本文を `--body-file` で外部から受け取りテンプレート非依存 → 変更不要）／`.github/ISSUE_TEMPLATE` は不存在。
- → 実装対象はテンプレート 1 ファイル＋既存イシュー本文群のみで、スキル/スクリプト側の追随修正は不要。

### 参照先実在性の機械検証（2026-07-19 実施）
- `docs/issues/templates/issue_template.md`・`docs/issues/open/`（wt-harness 26 件）・`/mnt/c/app/study-app-multitenant/docs/issues/open/`（40 件）・`scripts/claude/check-memo-body-paths.sh` すべて実在確認済み（`ls` / Read）。

### sweep 対象の全件分類（ツール実行による完了基準の確定・2026-07-19 実測）

**(A) wt-harness ローカル（`docs/issues/open/*.md` 26 件）**: ラベル 2 行保有は I134 のみ。**欠落 25 件**:
- git 管理済み（本 PR でコミットする）12 件: `013` `I031` `I032` `I033` `I034` `I036` `I040` `I041` `I042` `I043` `I044` `I047`
- 未追跡（invariant により本 PR ではコミットしない）13 件: `I093` `I094` `I099` `I101` `I110` `I112` `I118` `I121` `I125` `I128` `I130` `I135` `I136`

**(B) GitHub open イシュー（41 件）**: ラベル保有は #242(I134)・#246(I137)・#247(I138) のみ。**欠落 38 件**（`gh issue view` 全件走査で実測）:
- wt-harness ローカルと対応（ローカル編集→ `--body-file` 同期）12 件: #179(I093) #180(I094) #189(I099) #191(I101) #208(I110) #207(I112) #216(I118) #230(I125) #233(I128) #237(I130) #244(I135) #245(I136)
- 隣 worktree ローカルと対応（GitHub 本文を直接更新）21 件: #153(I075) #154(I076) #155(I077) #168(I085) #170(I087) #172(I088) #173(I089) #175(I090) #176(I091) #197(I105) #199(I106) #206(I111) #214(I116) #221(I119) #222(I120) #226(I123) #227(I124) #231(I126) #235(I129) #239(I131) #241(I133)
- ローカルファイルがどちらの worktree にも無い（GitHub 本文を直接更新）5 件: #177(I092) #42(I020) #44(I021) #10(CLAUDE.md 完全移行・旧形式) #220(dependency-audit 自動生成・非テンプレ形式)

**(C) 隣 worktree（study-app-multitenant）ローカル 28 件（未追跡）**: ラベル保有は I134/I137/I138 のみ。**欠落 25 件** = GitHub 対応あり 21 件（上記 (B) 2 段目）＋ GitHub open イシュー無し 4 件（`I074` `I086` `I114` `I122`）。→ 本セッションからは編集せず**引き継ぎ**（後述セクション「引き継ぎ手順」）。

整合確認: (A)12+13=25・(B)12+21+5=38・(C)21+4=25。GitHub 41 − 欠落 38 = 保有 3（I134/I137/I138）で全数一致。

補足: wt-harness ローカルのうち GitHub open イシューが無い 13 件（013・I031〜I047 の旧形式 12 件＝GitHub 未登録または旧番号、I121＝GitHub 側クローズ済み）は**ローカル編集のみ**（GitHub 同期先なし）。open/closed 番号共存の棚卸し自体は I101(#191) の担当でありスコープ外。

### 決定論ゲートの false-green 前倒し実証（2026-07-19・計画時実施済み）
- **G1（テンプレートのラベル存在・TC-01）**: 現状（未実装）に対し `grep -q '^\*\*背景\*\*:'` / `'^\*\*目的\*\*:'` → **両方 exit 1（NG）** を実測＝欠落を正しく検知。実装後に exit 0 へ転じることが合否。
- **G2（ローカル全件のラベル存在・TC-02）**: チェックスクリプト（後述・dir 引数）を現状の `docs/issues/open` に実行 → **exit 1・MISSING 25 件**を実測（上記 (A) と同一リスト）。合格系: I134 のみのディレクトリで **exit 0**。注入系: ラベル無しダミー 1 件を混ぜて **exit 1** 復帰。3 方向とも期待どおり＝false-green でない。
- **G3（GitHub 全件のラベル存在・TC-03）**: 41 件ループ走査 → **exit 1・missing=38**（上記 (B) と同一リスト）。
- **G4（tracked 無削除・TC-04）**: numstat 判定 awk に削除 0 の入力 → exit 0・削除 1 を含む入力 → **exit 1** を実測。
- **G5（untracked 挿入のみ・TC-05）**: snapshot diff 判定に挿入のみ → 合格・行削除入り → **不合格（削除行 `^<` 検知）** を実測。

### 既存テストの事前実行
- 対象外（BE/FE コード変更ゼロ・docs とチェックスクリプト 1 本のみ）。CI への影響は docs 差分と shellcheck（新規 bash スクリプト）のみ。

### 実装後追記（敵対的レビュー周回1 対応・2026-07-19）
- **sweep 母集団のレース（周回1 High）**: sweep（TC-03 初回合格 total=41 missing=0）の後、隣 worktree で新規イシュー I140〜I142（#251〜#253）が旧テンプレートから起票され、GitHub open は 44 件・ラベル欠落 3 件が再発した。同一手順（原本退避→見出し直下挿入→`--body-file` 更新・冪等）で 3 件を追補し、TC-03 を 44 件で再実走して合格を確認（実施記録参照）。
- **レース窓の規定**: テンプレート修正が develop マージ・引き継ぎで全 worktree に伝播するまで、旧テンプレ起票によるラベル無し新規イシューは構造的に発生し得る。よって AC-4/TC-03 は「**実行時点の open 全件**」を対象とし、新規発生分は同一手順で追補する（既ラベル保有は skip＝冪等）。テンプレート伝播後は新規発生が構造的に止まる。
- **例外（受容）**: dependency-audit の自動起票（`dependency-audit-issue.sh`）は本文生成にテンプレートを使わないため、今後の scheduled 監査 fail 時にラベル無し open イシューが再生産され得る（周回1 Medium）。本イシューでは #220 への手動挿入で対応済み。根治（生成本文への定型 背景/目的 ブロック追加）は計画外変更のためスコープ外とし、対応要否はユーザー判断に委ねる（敵対レビュー記録参照）。
- **無改変ゲートの強化（周回1 High/Medium）**: tc05 をスナップショット側駆動に変更（ファイル丸ごと消失の検出を追加）・tc06 に期待件数引数を追加（原本保存漏れの検出）・チェッカーに dir 不在 exit 2／走査 0 件 exit 1 の fail-closed を追加。いずれも失敗注入で NG 転化を再実証（実施記録参照）。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC を採用（判定 TC を対応付け）:
- [ ] AC-1: `issue_template.md` の `## 背景/目的` 直下にプレースホルダ 2 行が存在する（TC-01・合格=exit 0）
- [ ] AC-2: テンプレートから新規作成したイシューで背景・目的の未記入が構造的に起きない（プレースホルダは `（…）` 形式のため issue-review の未記入検出対象・調査結果「消費箇所」で確認済み。TC-01 成立をもって構造成立と判定）
- [ ] AC-3: wt-harness の `docs/issues/open/*.md` 全件にラベル 2 行が存在することを機械検証済み（TC-02・対象一覧は調査結果 (A)）
- [ ] AC-4: **TC-03 実行時点の** GitHub open イシュー全件の本文にラベル 2 行が反映済み（計画時 41 件・sweep 後の新規発生分は同一手順で追補。件数と実測は実施記録に記録。TC-03・`gh issue edit --body-file` で更新）
- [ ] AC-5: 隣 worktree にのみ存在する**ラベル未保有ファイル（実行時点の全件）**への反映手順（スクリプト＋GitHub open イシューが無いファイル向けの挿入スニペット）が本計画書「引き継ぎ手順」に記載済み（**TC-07** でスニペット集合と実態の一致を機械検証・実施は Human/別セッション）
- [ ] 追加ゲート: 既存本文の無改変（挿入のみ・削除ゼロ）を機械検証（tracked=TC-04・untracked=TC-05・GitHub 直接更新分=TC-06）

## 3. 影響範囲
- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**: なし（docs テンプレート・イシュー文書・GitHub イシュー本文・検証スクリプト 1 本のみ。requirements/package 系変更なし）

## 4. 変更点一覧

**修正アプローチ**: テンプレートにプレースホルダ 2 行を追加して構造的再発防止を確立し（宣言箇所の是正）、既存 open イシュー全件へ同ラベル 2 行を「挿入のみ（既存記述の削除・書き換えゼロ）」で追記して形式統一する（旧値 sweep）。完了判定は目視でなく、ローカル/GitHub 双方の grep 走査（合格=exit 0）で締める。隣 worktree 分はトラック境界を守り、GitHub 本文を正に立てた上で機械的反映手順を引き継ぐ。

| # | 対象 | 変更内容 |
|---|------|---------|
| 1 | `docs/issues/templates/issue_template.md` | `## 背景/目的` 直下（`### 現状の問題` の前）にプレースホルダ 2 行を挿入（下記コード例） |
| 2 | `scripts/claude/check-issue-background.sh`（新規） | ラベル 2 行の全件存在チェッカー（dir 引数・合格=exit 0）。TC-02 の判定器・引き継ぎ先でも再利用（下記コード例） |
| 3 | `docs/issues/open/*.md` 25 件（調査結果 (A) のリスト） | `## 背景/目的` 直下にラベル 2 行を挿入（内容は各ファイルの既存記述＝現状の問題/根本原因/解決方針/関連資料から要約して書き起こす。既存行の削除・変更はしない） |
| 4 | GitHub open イシュー本文 38 件（調査結果 (B) のリスト） | 変更点 3 と同じ挿入（wt-harness 対応 12 件はローカル編集後 `--body-file` 同期・残り 26 件は取得→挿入→ `--body-file` 更新）。`## 背景/目的` 見出しが無い本文は冒頭に見出しごと挿入（実装時実測: 見出し無しは #10・#220 の 2 件。#42/#44 は旧形式だが見出し実在のため見出し直下挿入。計画時の見出し無し想定 4 件から事実訂正） |
| 5 | 本計画書「引き継ぎ手順」セクション | 隣 worktree 25 件への反映スクリプト＋GitHub 無し 4 件（I074/I086/I114/I122）の挿入スニペット（本計画書に記載済み・実装時は変更なし） |

### 実装コード例

**変更点 1** `issue_template.md`（挿入のみ・他は不変更）:
```markdown
## 背景/目的

**背景**: （このイシューに至った経緯。どの作業・レビュー・指摘から生まれたか）
**目的**: （このイシューで達成したい状態。何がどうなれば成功か）

### 現状の問題（証拠・再現手順）
```

**変更点 2** `scripts/claude/check-issue-background.sh`（新規・全文）:
```bash
#!/usr/bin/env bash
# I134: イシュー文書の **背景**:/**目的**: ラベル 2 行の全件存在チェック（合格=exit 0）
# 使い方: bash scripts/claude/check-issue-background.sh [対象ディレクトリ]（既定: docs/issues/open）
# fail-closed: 対象ディレクトリ不在は exit 2・走査 0 件は exit 1（引数タイプミス等を「全件合格」と誤認しない）
# 注意: auto_test の決定論ゲート（自動実走）として宣言する場合は scripts/claude/tests/ への移動が必要
#（code-review.sh classify_gate の allowlist は `bash scripts/claude/tests/*.sh` のみ ALLOW。allowlist の check-*.sh 拡張は I139(#250)）
set -u
DIR="${1:-docs/issues/open}"
if [ ! -d "$DIR" ]; then
  echo "ERROR: no such directory: $DIR"
  exit 2
fi
missing=0
scanned=0
for f in "$DIR"/*.md; do
  [ -f "$f" ] || continue
  scanned=$((scanned + 1))
  if ! grep -q '^\*\*背景\*\*:' "$f" || ! grep -q '^\*\*目的\*\*:' "$f"; then
    echo "MISSING: $f"
    missing=$((missing + 1))
  fi
done
if [ "$scanned" -eq 0 ]; then
  echo "NG: no .md files scanned in $DIR (fail-closed)"
  exit 1
fi
if [ "$missing" -gt 0 ]; then
  echo "NG: ${missing}/${scanned} file(s) missing 背景/目的 labels"
  exit 1
fi
echo "OK: all ${scanned} files have 背景/目的 labels"
exit 0
```
（このロジックは計画時に scratchpad 上で実走し、NG 検知・合格・注入 NG の 3 方向を実証済み＝調査結果 G2。`set -e`/`pipefail` は不採用: パイプ非使用かつ全コマンドの失敗が条件分岐で処理済みのため検知力が増えず、実証済みロジックとの同一性を優先する＝plan-review Info 対応・見送り確定）

**変更点 3/4 の挿入フォーマット**（全ファイル共通）: `## 背景/目的` 見出し行の直後に空行＋ラベル 2 行を挿入する。
```markdown
## 背景/目的

**背景**: （そのイシューの経緯を既存記述から要約・1〜2 文）
**目的**: （達成したい状態を既存記述から要約・1〜2 文）
```
見出しが無い本文はタイトル行（`# …`）直後（タイトル行も無い場合は本文冒頭）に空行＋`## 背景/目的`＋空行＋ラベル 2 行を挿入する（実装時実測: 該当は #10・#220 の 2 件のみ）。

## 5. 実装手順（ステップ）

本イシューに未知リスク（外部挙動依存・実現可能性不明の要素）は無い（gh 編集・grep 判定とも計画時に実走済み）。ステップは依存順に直列。

- **ステップ1: 構造的再発防止の確立**（変更点 1・2）
  1. テンプレートへプレースホルダ 2 行を挿入 → TC-01 参照。
  2. `scripts/claude/check-issue-background.sh` を新規作成（コード例どおり）→ TC-02 の注入系で検知能力を確認。
- **ステップ2: wt-harness ローカル sweep**（変更点 3。ステップ1 完了が前提）
  1. sweep 前に `docs/issues/open/` 全体を scratchpad へスナップショット（TC-05 の比較基準）。
  2. 調査結果 (A) の 25 件へ、各ファイルの既存記述から背景・目的を要約したラベル 2 行を挿入（Edit・挿入のみ）→ TC-02 / TC-04 / TC-05 参照。
- **ステップ3: GitHub sweep**（変更点 4。ステップ2 完了が前提）
  1. 更新前に 38 件の現行本文を scratchpad へ退避（ロールバック用）。
  2. wt-harness 対応 12 件: `gh issue edit <#> --body-file docs/issues/open/I###.md` で同期。
  3. 残り 26 件: `gh issue view <#> --json body` で取得→挿入フォーマットどおりラベル 2 行を挿入した一時ファイルを作成→ `gh issue edit <#> --body-file` で更新（既にラベルがある場合は skip＝再実行冪等）。
  4. → TC-03（**実行時点の open 全件**を grep 走査・missing=0）・TC-06（退避原本との diff に削除行なし・期待件数突合）参照。
- **ステップ4: 記録と引き継ぎ確定**（ステップ3 完了が前提）
  1. TC-01〜05 の実行結果を auto_test に記録。挿入した 25 件のラベル内容一覧（実施記録）を auto_test に残す。
  2. 「引き継ぎ手順」セクション（本計画書に記載済み）が実装結果と乖離していないか突き合わせ、乖離があれば同期する。

サービス再起動: 不要（docs・GitHub 本文・検証スクリプトのみ）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I134_auto_test.md`）
- テストレベル: **決定論 TC のみ**（grep / awk / diff の exit code 判定に統一・合格=exit 0）。ユニット/結合/E2E は対象コードが無いため非該当。
- 再発防止: TC-01（テンプレートのラベル存在）が「プレースホルダ無しテンプレートへの逆戻り」を、TC-02 用チェッカー（リポジトリに常設）が将来の点検再実行を可能にする。
- false-green 検証: G1〜G5 すべて計画時に NG 側・合格側の双方を実証済み（調査結果）。実装後の再注入は TC-02 の注入系（ダミーファイル）のみ実施（他は入力注入型で計画時実証から変化しないため再実施不要）。

### 手動テスト（詳細: `docs/tests/open/I134_manual_test.md`）
- No.1〜3 は Claude 実施（diff 範囲確認・GitHub 本文スポットチェック・PR CI 確認）。**No.4（書き起こした背景・目的の内容妥当性のサンプル目視）のみ Human**（要約の質は感覚的確認のため）。

## 7. ロールバック
- **tracked 分（テンプレート・旧 12 件・スクリプト）**: 本 PR を revert（または `git revert <commit>`）で完全復元。
- **untracked 分（13 件）**: 挿入した 2 行（＋空行）を Edit で除去すれば復元（挿入のみのため既存内容は無傷・TC-05 がそれを保証）。
- **GitHub 本文（退避原本の全件・初回 38＋レース追補 3＝41 件）**: ステップ3-1 で退避した scratchpad の原本 body を `gh issue edit --body-file` で書き戻す（GitHub 側にも編集履歴が残る）。
- DB 変更なし・マイグレーション不要・サービス再起動不要。

## 8. Risk & 回避策
- **リスク1: 書き起こす背景・目的が原文の意図とずれる** → 回避: 内容は各イシューの既存記述（現状の問題/根本原因/解決方針/関連資料の発見経緯）のみから要約し、新情報を足さない。既存行は一切削除・変更しない（TC-04/05 で機械保証）。質のサンプル確認を manual No.4（Human）に置く。
- **リスク2: grep 判定の false-green（引用/コードフェンス内の行頭 `**背景**:` を実ラベルと誤認）** → 現状この形を含むのは I134 本文の解決方針コード例のみで、I134 は正規ラベルも持つため実害なし。行頭アンカー（`^`）で本文中の言及とは区別済み。限界として記録し、将来誤検知が出た場合はセクション内判定へ強化する（本イシューでは過剰設計として見送り）。
- **リスク3: GitHub 本文更新が途中失敗（レート制限・ネットワーク）** → 回避: 更新は 1 件ずつ・既ラベル保有は skip の冪等設計。失敗時は TC-03 が missing を列挙するため残件から再実行。
- **リスク4: GitHub 本文とローカルの乖離（隣 worktree 分）** → 回避: 引き継ぎ手順（スクリプト＋ゲート）で解消。引き継ぎ実施までの一時的乖離は「ラベル 2 行の有無」のみで実害なし（grill 確定の運用）。
- **リスク5: #220（自動生成イシュー）の形式が dependency-audit スクリプトの後続コメントと衝突** → `dependency-audit-issue.sh` は既存イシューへは `gh issue comment` のみで body を書き換えないため衝突しない（調査結果「消費箇所」）。

## セキュリティ・ベストプラクティスチェック
- **セキュリティ影響なし**: アプリコード・認証認可・入力処理・機密データの扱いに変更なし。docs と読み取り専用チェックスクリプトのみ。依存追加なし（pip-audit / npm audit 対象変更なし）。
- スキャン基準: 新規 bash スクリプトは pre-commit の shellcheck を通過させる（既存基準どおり）。bandit/npm audit は対象外（該当コード変更なし）。

## 高リスク判定
- **自己評価: No**。認証・認可・ロール・個人情報・テナントデータ・公開 API の変更なし。docs・GitHub イシュー本文・検証スクリプトのみ。最終判定は `/plan-issue-review I134` に委ねる。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: DB 変更なし。
- **P5（運用設計）影響なし**: 外部 API 連携の新設なし（gh CLI の単発実行のみ・常駐/バッチなし）。
- **P6（性能・UX）影響なし**: UI 変更なし。
- **P8（コスト）影響なし**: 新規インフラ・外部サービスなし。
- **P9（プライバシー）影響なし**: 個人情報・未成年データ・テナントデータの取扱い変更なし。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| sweep は形式統一方式（全 open イシューにラベル 2 行・旧形式は既存文章を要約してラベル行化）・grep 機械検証で締める | イシュー明記（grill 確定・2026-07-19 ユーザー承認） |
| 隣 worktree 分は GitHub を正として本セッションから本文更新・ローカル反映は引き継ぎ | イシュー明記（grill 確定） |
| チェッカーを常設スクリプト `scripts/claude/check-issue-background.sh`（dir 引数）として追加 | **仮定で決めた**（イシューは「grep で機械検証」とのみ規定。引き継ぎ先での再利用と注入テスト可能性のため常設化・`check-memo-body-paths.sh` と同じ置き場所） |
| ラベル判定は行頭アンカー `^**背景**:` / `^**目的**:`（引用言及との区別・decoy 考慮） | **仮定で決めた**（リスク2 に限界を明記） |
| 見出しが無い本文はタイトル直後（タイトルも無ければ冒頭）に `## 背景/目的` 見出しごと挿入 | **仮定で決めた**（「open 全件」の AC を一様に満たすため。#220 の自動生成形式とも衝突しないことを確認済み。実装時実測で該当は #10・#220 の 2 件＝計画時想定 4 件から事実訂正） |
| tracked 旧 12 件は本 PR でコミット・untracked 13 件は未コミット維持 | **仮定で決めた**（イシューファイルは自イシューの close で回収する既存 invariant の踏襲） |
| I121 等「GitHub 側クローズ済みだがローカル open に残るファイル」もローカル sweep 対象（GitHub 側は対象外） | **仮定で決めた**（ゲートを「ディレクトリ全件」で単純に保つ。open/closed 共存の棚卸しは I101 の担当でスコープ外） |
| 無改変保証ゲート TC-04（tracked 削除ゼロ）/ TC-05（untracked 挿入のみ）/ TC-06（GitHub 直接更新分 挿入のみ）の追加 | **仮定で決めた**（「挿入のみ・既存記述を壊さない」主張を散文で終わらせないための決定論化） |

→ 「仮定で決めた」6 項目は下の承認ポイントで確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] テンプレートへの挿入はプレースホルダ 2 行のみ（コード例どおり・他行不変更）— でよいか
- [ ] チェッカーを常設スクリプト `scripts/claude/check-issue-background.sh` として追加（引き継ぎ先でも再利用）— でよいか
- [ ] 既存イシューへの挿入は「見出し直下にラベル 2 行」のみ・内容は既存記述からの要約・既存行の削除/変更ゼロ（TC-04/05 で機械保証）— でよいか
- [ ] 見出しの無い #10/#42/#44/#220 はタイトル直後に見出しごと挿入（#220 の自動生成イシューも対象に含める）— でよいか
- [ ] tracked 旧 12 件は本 PR でコミット・untracked 13 件は未コミット維持（invariant 踏襲）— でよいか
- [ ] GitHub 更新 38 件は原本退避→冪等更新・ロールバックは退避 body の書き戻し — でよいか
- [ ] 引き継ぎは「本計画書のスクリプト＋4 件スニペット」を隣 worktree セッション（またはユーザー）が実施 — でよいか
- [ ] 手動テストは No.4（要約内容のサンプル目視・3 件）のみ Human — でよいか
- [ ] 高リスク判定の自己評価 No（最終判定は plan-issue-review）— でよいか

---

## 検証スクリプト全文（TC-03〜06・scratchpad 実行用）

auto_test の TC-03〜06 が参照するスクリプト全文（実行時に scratchpad へ保存して `bash <ファイル>` で実行する）。auto_test 側に fenced で掲載すると omission-lint が宣言外ゲートと誤認して HIGH になるため、本計画書に配置する（code-review 20260719_2210 High 対応・診断記録 `docs/reviews/I134_fix_diagnosis_20260719_2221.md` 案 A。lint 側の根治は I139(#250)）。

### tc03_gh_labels.sh（GitHub open 全件のラベル存在・計画時 G3 実証と同一ロジック）
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

### tc04_no_deletion.sh（tracked 分の無改変保証）
```bash
#!/usr/bin/env bash
set -u
# I134.md 自身は sweep 対象でなく本イシューの管理文書（Draft PR 追記・AC 文言整合で行置換が正当に入る）ため
# numstat 判定からは除外する。ただし丸ごと削除は無警報になるため存在チェックのみ独立に課す（周回2 Medium 対応）
if [ ! -f docs/issues/open/I134.md ]; then
  echo "FILE-DELETED: docs/issues/open/I134.md"
  exit 1
fi
# 比較基底が解決できないと git が fatal を吐いても awk が空入力で exit 0 を返し合格に化けるため先に検証する（周回3 Medium 対応）
if ! git rev-parse --verify --quiet origin/develop > /dev/null; then
  echo "ERROR: base ref origin/develop is unresolvable (fail-closed)"
  exit 2
fi
git diff --numstat origin/develop...HEAD -- docs/issues/ ':(exclude)docs/issues/open/I134.md' | awk '$2!=0{print "DELETION:",$0; bad=1} END{exit bad?1:0}'
```

### tc05_untracked_insert_only.sh（untracked 分の無改変保証・引数=スナップショット dir）

スナップショット側を駆動することで「削除行」に加え「ファイル丸ごとの消失」も検出する（敵対レビュー周回1 H1 対応）。dir 不在は exit 2・走査 0 件も exit 2 の fail-closed。

```bash
#!/usr/bin/env bash
set -u
SNAP="${1:?Usage: $0 <snapshot_dir>}"
if [ ! -d "$SNAP" ]; then
  echo "ERROR: no such dir: $SNAP"
  exit 2
fi
bad=0
checked=0
for s in "$SNAP"/*.md; do
  [ -f "$s" ] || continue
  b=$(basename "$s")
  # I134.md 自身は sweep 対象でなく本イシューの管理文書（AC 文言整合等で行置換が正当に入る）ため除外（TC-04 と同一の設計）
  [ "$b" = "I134.md" ] && continue
  f="docs/issues/open/$b"
  checked=$((checked + 1))
  if [ ! -f "$f" ]; then
    echo "FILE-DELETED: $f"
    bad=1
    continue
  fi
  if diff "$s" "$f" | grep -q '^<'; then
    echo "DELETED-LINES: $f"
    bad=1
  fi
done
if [ "$checked" -eq 0 ]; then
  echo "ERROR: snapshot dir has no .md files (fail-closed)"
  exit 2
fi
echo "checked=$checked"
exit "$bad"
```

### tc07_handoff_snippets.sh（AC-5 の決定論判定・引数=隣 worktree のパス）

引き継ぎ手順の「GitHub open イシューが無いファイル向けスニペット」の集合が、隣 worktree の実態（ラベル未保有かつ GitHub open イシューが無いファイル）と一致することを機械検証する（周回3 Medium 対応＝AC-5 が決定論層に載っていなかった穴を塞ぐ）。

```bash
#!/usr/bin/env bash
set -u
WT="${1:?Usage: $0 <neighbor_worktree_path>}"
PLAN=docs/plans/open/plan_I134.md
if [ ! -d "$WT/docs/issues/open" ]; then
  echo "ERROR: no such dir: $WT/docs/issues/open"
  exit 2
fi
if [ ! -f "$PLAN" ]; then
  echo "ERROR: no such plan: $PLAN"
  exit 2
fi
need=$(mktemp)
have=$(mktemp)
scanned=0
for f in "$WT"/docs/issues/open/*.md; do
  [ -f "$f" ] || continue
  scanned=$((scanned + 1))
  grep -q '^\*\*背景\*\*:' "$f" && grep -q '^\*\*目的\*\*:' "$f" && continue
  base=$(basename "$f" .md)
  # 本ブランチで commit 済みのファイルは develop 取り込みでラベル付きが配布されるため対象外
  if git cat-file -e "HEAD:docs/issues/open/${base}.md" 2>/dev/null; then continue; fi
  num=$(gh issue list --state open --limit 100 --json number,title --jq ".[] | select(.title | startswith(\"${base}:\")) | .number" | head -1)
  [ -n "$num" ] && continue
  echo "$base" >> "$need"
done
if [ "$scanned" -eq 0 ]; then
  echo "ERROR: no issue files scanned (fail-closed)"
  exit 2
fi
grep -oE '^`docs/issues/open/I[0-9]+\.md`' "$PLAN" | tr -d '`' | xargs -r -n1 basename | sed 's/\.md$//' | sort -u > "$have"
sort -u -o "$need" "$need"
if ! diff "$need" "$have" > /dev/null; then
  echo "NG: snippet set mismatch (need vs have)"
  diff "$need" "$have"
  rm -f "$need" "$have"
  exit 1
fi
echo "OK: snippet set matches ($(wc -l < "$need") file(s))"
rm -f "$need" "$have"
exit 0
```

### tc06_gh_insert_only.sh（GitHub 直接更新分の無改変保証・引数=退避原本 dir と期待件数。原本は `<#>.md` 名で保存しておく）

期待件数の第 2 引数で「原本の保存漏れ・不完全な dir でも合格」を防ぐ（敵対レビュー周回1 Medium 対応）。

```bash
#!/usr/bin/env bash
set -u
ORIG="${1:?Usage: $0 <original_bodies_dir> <expected_count>}"
EXPECTED="${2:?Usage: $0 <original_bodies_dir> <expected_count>}"
if [ ! -d "$ORIG" ]; then
  echo "ERROR: no such dir: $ORIG"
  exit 2
fi
# 期待件数は正の整数のみ受理（非数値は test のエラーで照合が素通りするため fail-closed・周回2 Medium 対応）
# 桁あふれも同じ機構で素通りするため桁数上限も課す（周回3 Low 対応）
case "$EXPECTED" in
  ''|0|*[!0-9]*)
    echo "ERROR: expected_count must be a positive integer: $EXPECTED"
    exit 2 ;;
esac
if [ "${#EXPECTED}" -gt 6 ]; then
  echo "ERROR: expected_count out of range: $EXPECTED"
  exit 2
fi
bad=0
checked=0
for o in "$ORIG"/*.md; do
  [ -f "$o" ] || continue
  n=$(basename "$o" .md)
  checked=$((checked + 1))
  # 0 バイト原本は退避時の gh 失敗の痕跡。diff が全行追加扱いになり削除検出とロールバック原本が同時に無効化されるため弾く（周回3 Medium 対応）
  if [ ! -s "$o" ]; then
    echo "EMPTY-ORIGINAL: #$n"
    bad=1
    continue
  fi
  gh issue view "$n" --json body --jq .body > "$ORIG/$n.after"
  if diff "$o" "$ORIG/$n.after" | grep -q '^<'; then
    echo "DELETED-LINES: #$n"
    bad=1
  fi
done
echo "checked=$checked expected=$EXPECTED"
if [ "$checked" -eq 0 ]; then
  echo "ERROR: no original bodies scanned (fail-closed)"
  exit 2
fi
if [ "$checked" -ne "$EXPECTED" ]; then
  echo "NG: checked count mismatch (fail-closed)"
  exit 1
fi
exit "$bad"
```

---

## 引き継ぎ手順（隣 worktree: study-app-multitenant への反映）

**実施タイミング**: 本 PR (#249) マージ後、study-app-multitenant 側セッション（またはユーザー）が実施する。先に develop を取り込むこと（tracked 12 件・テンプレート・チェッカーは git 経由で反映される）。

**手順**:
1. develop 取り込み後、以下のスクリプトを worktree ルートで実行する（ラベル 2 行を持たない全ファイルへ、GitHub 本文からラベル 2 行を抽出して挿入する。**件数は固定せず実行時点の実態に従う**＝ラベル未保有ファイルのうち GitHub open イシューが対応するもの全件が対象。既ラベル保有・片ラベル・GitHub 無しは skip。実行のたびに対象数は変動する（イシューのクローズによる減少・旧テンプレ起票による増加）ため、件数の一致でなく**手順 3 のゲート exit 0 到達をもって完了と判定する**）:
```bash
#!/usr/bin/env bash
# I134 引き継ぎ: open イシューへ **背景**:/**目的**: ラベル 2 行を GitHub 本文から反映する（冪等）
set -u
cd "$(git rev-parse --show-toplevel)"
for f in docs/issues/open/*.md; do
  has_bg=0
  has_mk=0
  grep -q '^\*\*背景\*\*:' "$f" && has_bg=1
  grep -q '^\*\*目的\*\*:' "$f" && has_mk=1
  if [ "$has_bg" -eq 1 ] && [ "$has_mk" -eq 1 ]; then continue; fi
  if [ "$has_bg" -ne "$has_mk" ]; then
    # 片ラベルのみの中途状態に挿入すると重複するため停止して手動確認（周回2 対応）
    echo "SKIP(片ラベルのみ・手動確認): $f"
    continue
  fi
  base=$(basename "$f" .md)
  num=$(gh issue list --state open --limit 100 --json number,title \
        --jq ".[] | select(.title | startswith(\"${base}:\")) | .number" | head -1)
  if [ -z "$num" ]; then
    echo "SKIP(no GH issue): $f — 下記スニペットを手動挿入"
    continue
  fi
  body=$(gh issue view "$num" --json body --jq .body)
  bg=$(printf '%s\n' "$body" | grep -m1 '^\*\*背景\*\*:')
  mk=$(printf '%s\n' "$body" | grep -m1 '^\*\*目的\*\*:')
  if [ -z "$bg" ] || [ -z "$mk" ]; then
    echo "SKIP(GH 未反映): $f (#$num)"
    continue
  fi
  # awk -v はバックスラッシュをエスケープ解釈して内容が化けるため環境変数渡しにする（周回2 対応）
  bg="$bg" mk="$mk" awk \
    '{print} $0=="## 背景/目的" && !d {print ""; print ENVIRON["bg"]; print ENVIRON["mk"]; d=1}' \
    "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  if grep -q '^\*\*背景\*\*:' "$f" && grep -q '^\*\*目的\*\*:' "$f"; then
    echo "UPDATED: $f (#$num)"
  else
    echo "ERROR(見出し完全一致なし・未挿入): $f"
  fi
done
```
2. GitHub open イシューが無いファイル（2026-07-20 時点で I074/I086/I114/I122 の 4 件・**実行時点で手順 1 が `SKIP(no GH issue)` を出したファイルが正**）は、以下のスニペットを各ファイルの `## 背景/目的` 見出し直下（空行を挟んで）に挿入する。スニペットに無いファイルが SKIP された場合は、そのイシューの既存記述から同形式で背景・目的を書き起こす（TC-07 がこの集合一致を機械検証する）:

`docs/issues/open/I074.md`:
```markdown
**背景**: I073 振り返りの予防処置 P3。fix-loop が診断・実装・テストを独立レビューせず一括で進むため、原因誤特定や影響調査漏れ（キャッシュ読み取り経路の見落とし・同型バグ残存）が素通りした実例から生まれた。
**目的**: fix-loop に診断→実装→テストの 3 サブエージェントレビューを順次ゲート（前段 OK のときのみ次へ進む）として導入し、調査・方針段階の誤りを実装前に検出できる状態にする。
```

`docs/issues/open/I086.md`:
```markdown
**背景**: I080 のレビューで実装者の自己認証と単発 code-review が Critical/High を見逃し、ユーザーの促しで起動した敵対的サブエージェントレビューが初めて欠陥を捕捉した＝品質が人間の介入に依存していた。
**目的**: 高リスク判定 Yes をトリガに反証マンデートの多観点敵対的レビューステージを自動起動し、対応後再レビューまで含めて実装者の自己認証を非権威化した状態にする。
```

`docs/issues/open/I114.md`:
```markdown
**背景**: I104 の /retro でユーザーから「出力が全体的にわかりにくい」との指摘、平易化後には「簡略化しすぎで必要情報まで削っている」との再指摘があり、平易さと情報完全性を両立するルールが retro SKILL.md に無いことが判明した。
**目的**: retro の対ユーザー説明・確認出力を「専門用語を平易な言葉に置換しつつ経緯・理由は残す」ルールで平易化し、記録ファイルは詳細のまま維持される状態にする。
```

`docs/issues/open/I122.md`:
```markdown
**背景**: I121 の TC-02 が「grep -c 出力が 0」という合格時に exit 1 を返す判定形で書かれ、plan/code の独立レビュー 2 回で同じ反転リスク指摘が出た＝ルール不在の再発性が実証されたことから、I121 retro 予防処置 P1 として起票された。
**目的**: plan-writing-rules に「決定論 TC の合否判定は合格=exit 0 に統一」を明文化し、plan-reviewer の確認観点にも追加して、出力値判定の反転リスクを作成時とレビュー時の 2 層で防ぐ状態にする。
```

3. 最後にゲートを実行し合格（exit 0）を確認する:
```bash
bash scripts/claude/check-issue-background.sh docs/issues/open
```

## レビュー結果
- [20260719_2124 判定: ✅ 完了](../../reviews/I134_plan_review_20260719_2124.md)
