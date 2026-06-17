# I063 自動テスト

- **関連イシュー**: #129
- **計画書**: docs/plans/open/plan_I063.md
- **対象**: `.claude/skills/implement/SKILL.md` / `.claude/skills/grill-me/SKILL.md` / `docs/runbooks/plan-writing-rules.md` / `docs/runbooks/review-rules.md`
- **テスト戦略（Q2=b）**: grep 存在確認（全7項目）＋ 振る舞いスモーク（item1/2）。

## 実行方法（重要）
シェルロジックを含む TC は**スクリプトファイルとして `bash` 実行**する。

> ⚠️ 対話シェルへ直接コマンドを貼り付けないこと。Claude Code の対話シェルでは `grep` が同梱 `ugrep` ラッパーに上書きされ `-E`/`-o` パイプが誤動作する。`bash script.sh` のサブプロセスでは実 GNU grep が使われる。期待終了コード: **0**。

## 実行結果（2026-06-17・実装後）
- 存在・静的検証（TC-01〜09 ＋ TC-S2b post-fix）: `bash` スクリプト実行で **PASS=10 / FAIL=0**。
- 振る舞いスモーク（TC-S1a/S1b/S2）: 一時 repo・サンプル文書で **PASS**（STOP ゲート発火/通過・不在パスのみ検出）。
- TC-S2b: 実装後の `review-rules.md` から `docs/reviews/README.md` 参照が**消失**（C1 デッドリンク是正済み）を確認。
- **結論: 全自動 TC PASS**。TC-S3（grill-me 実走観察）は手動テスト文書で Human 判断。

---

## grep 存在確認（実装後に各追記文言が対象ファイルに存在するか）

| TC | 対象ファイル | 期待（grep でヒットする文言の趣旨） | 実施者 | 実結果 |
|---:|-------------|--------------------------------------|--------|--------|
| TC-01 | `.claude/skills/implement/SKILL.md` | 手順3〜4間に `git diff origin/develop...HEAD` での反映検証＋未反映時ハード STOP（完了案内を出さず未コミット/未 push 報告）の記載 | Claude | ✅ PASS（2026-06-17） |
| TC-02 | `docs/runbooks/plan-writing-rules.md` | 「事前調査（必須）」に参照先（パス/ファイル/ディレクトリ）実在性の全件機械検証（`test -f`/`ls`・既存デッドリンク含む）の記載 | Claude | ✅ PASS（2026-06-17） |
| TC-03 | `.claude/skills/grill-me/SKILL.md` | 必須確認に「scope/AC を左右する scan/lint/audit/型チェックツールは概算でなく実行して全件分類・確定」の記載があり、かつ**「実行省略不可」相当の明示**で「質問を省略してよい」前置きに巻き込まれていない（W2） | Claude | ✅ PASS（2026-06-17） |
| TC-04 | `.claude/skills/grill-me/SKILL.md` | 手順4に「設計確認メモ追記後、矛盾する既存セクション（解決方針・スコープ・実装対象・AC）を整合更新」の記載 | Claude | ✅ PASS（2026-06-17） |
| TC-05 | `.claude/skills/grill-me/SKILL.md` | 手順4末尾に `gh issue edit <GitHub#> --body-file docs/issues/open/IXXX.md` で GitHub 本文同期・`gh` 不可なら skip（非ブロック）の記載（W1: `--body-file` を使用） | Claude | ✅ PASS（2026-06-17） |
| TC-06 | `docs/runbooks/plan-writing-rules.md` | 「事前調査（必須）」に規約是正時の旧パターン消費箇所（グロブ・ループ・相互参照・スクリプト）全件列挙（P1 do層）の記載 | Claude | ✅ PASS（2026-06-17） |
| TC-07 | `docs/runbooks/review-rules.md` | `reviews/README.md` 参照が**存在しない**こと（C1 デッドリンク削除済み・`grep -c` = 0） | Claude | ✅ PASS（2026-06-17） |

## 一般化・非退行

| TC | 対象 | 期待 | 実施者 | 実結果 |
|---:|------|------|--------|--------|
| TC-08 | 全追記文言 | `I060`/`I061` 等の固有イシュー番号に依存しない一般化表現である（追記ブロック内に固有番号が混入していない） | Claude | ✅ PASS（2026-06-17） |
| TC-09 | `implement/SKILL.md` の手順番号 | 既存の手順番号（1〜4）と他ファイルからの参照が壊れていない（item1 は 3.5 挿入で番号維持） | Claude | ✅ PASS（2026-06-17） |

---

## 振る舞いスモーク（プロトタイプ検証済み・実装後に本体で再確認）

> 下記 TC-S1/S2 のシェル機構は doc 編集に依存しないため、**計画段階でプロトタイプ実測済み（2026-06-17・`bash /tmp/i063_smoke.sh`・全 PASS）**。実装後は実ファイル（`implement/SKILL.md` の手順・実 `review-rules.md`）に対して再確認する。

| TC | 内容 | 期待 | 実施者 | 実結果 |
|---:|------|------|--------|--------|
| TC-S1a | 一時 repo で未コミットの作業ツリー変更に対し `git diff origin/develop...HEAD --name-only` | 空（＝STOP ゲートが発火・完了案内を出さない条件） | Claude | ✅ PASS（プロトタイプ 2026-06-17） |
| TC-S1b | 同 repo でコミット後に同コマンド | 変更ファイルが現れる（＝ゲート通過） | Claude | ✅ PASS（プロトタイプ 2026-06-17） |
| TC-S2 | 「不在パス」＋「実在パス」を含むサンプル文書に参照抽出＋`test -e` を適用 | **不在パスのみ**検出（実在パスは非検出） | Claude | ✅ PASS（プロトタイプ 2026-06-17） |
| TC-S2b | 実 `docs/runbooks/review-rules.md` のデッドリンク状態 | 実装前=`reviews/README.md` 参照あり（baseline）／実装後=参照なし（TC-07 と整合） | Claude | ✅ PASS（実装後=参照消失を確認 2026-06-17・TC-07 と整合） |

### スモークの隔離方針（リポジトリ汚染防止）
- TC-S1 は `mktemp -d` の一時 repo 内で `git init` し、`develop`/`origin-develop`/`feature` を擬似生成して検証する。**本リポジトリの develop/main・origin を一切触らない**。
- TC-S2 のサンプル文書も `mktemp -d` 配下に作成する。
- `rm -rf` は使用しない（PreToolUse ガードが `DANGER_OK=1` を要求するため）。一時ディレクトリは OS に委ねる。

---

## 実装前プロトタイプ検証（参考・調査フェーズで実測済み）
> 実装ステップ（doc 編集）ではなく、振る舞いスモークが依拠するシェル機構の事前検証。
- TC-S1 相当（STOP ゲート発火/通過）: 一時 repo で 2/2 PASS（2026-06-17）
- TC-S2 相当（不在パスのみ検出）: 1/1 PASS（2026-06-17）
- TC-S2b baseline（実 review-rules.md のデッドリンク存在）: 確認済み（2026-06-17・実装で削除予定）
