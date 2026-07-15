# I107 自動テスト: GitHubイシューのトラック軸ラベル分類（track:app / track:harness）導入

対象がGitHub設定と運用文書のため、backend/frontend のテストスイートは対象外。
検証は (a) 文書側の決定論ゲート（grep）と (b) GitHub側の状態検証（gh 実走）で行う。

実行コマンド:
- AT-01〜AT-07 の各TCに記載の `gh` コマンドを /test 実行時に Claude が実走し、期待値と突き合わせて結果を記録する。
- 文書側は「決定論ゲート」セクションの grep 4件（/code-review が自動実走）。

結果:
- backend: 対象外（コード変更なし）
- frontend: 対象外（コード変更なし）
- gh 実走TC（AT-01〜07）: **全 PASS**（2026-07-15 /test 実走）
  - AT-01: PASS — `track:app` 1件ヒット・description「学習アプリ開発トラック（worktree: study-app-multitenant）」・color `0e8a16`
  - AT-02: PASS — `track:harness` 1件ヒット・description「ハーネス改善トラック（worktree: wt-harness）」・color `5319e7`
  - AT-03: PASS — 決定論ゲート G1/G2 exit=0（/code-review 実走）＋Read で SKILL.md step 4 の `--label` 分割2軸形式・判定基準3条件を確認
  - AT-04: PASS — 決定論ゲート G3/G4/G5 exit=0＋Read で issue-flow.md 2箇所（自動実行フロー ステップ3 L49-63・統合ルール ステップ2 L189-202）とも同一粒度の記載を確認
  - AT-05: PASS — jq 判定 `0`（track ラベル無し・二重付与ともに0件。オープン26件全件がちょうど1つ）
  - AT-06: PASS — sort+diff 突き合わせで承認済み25行と過不足なし。増分1行のみ `205:track:app`（I109・2026-07-15 検証前起票。track ラベルちょうど1つで許容条件に適合）
  - AT-07: PASS — `track:app` 9件（承認8件＋#205 増分・AT-06 と整合）/ `track:harness` 17件
  - AT-08: PASS — `bash scripts/claude/tests/test_i107_track_label_docs.sh` exit=0（6項目全 PASS: SKILL.md 2行/2行・issue-flow.md 4行/4行・worktree.md 1行/1行）。false-green 実証は下記記録どおり（更新前 exit=1）
- CI（PR #202）: 全6ジョブ pass（Backend Lint & Security / Backend Tests / Frontend Lint & Security / Frontend Tests / Frontend Type Check / E2E Tests）

## テストケース

### AT-01: track:app ラベルの存在・定義
- コマンド: `gh label list --json name,description,color --jq '.[] | select(.name == "track:app")'`
- 期待値: 1件ヒットし、`description` に `study-app-multitenant` を含み、`color` が `0e8a16`

### AT-02: track:harness ラベルの存在・定義
- コマンド: `gh label list --json name,description,color --jq '.[] | select(.name == "track:harness")'`
- 期待値: 1件ヒットし、`description` に `wt-harness` を含み、`color` が `5319e7`

### AT-03: issue-bootstrap SKILL.md の2軸ルール記載（→ 決定論ゲート G1/G2）
- 決定論ゲート G1/G2 の grep で機械判定（track:app / track:harness の両文言が SKILL.md に存在）
- 加えて /test 時に Read で step 4 を確認: `--label` が2軸形式・トラック判定基準（`docs/runbooks/`・`scripts/claude/`・`.claude/` → harness、`backend/`・`frontend/`・`e2e/` → app、両属は主目的側に単一付与）が記載されていること

### AT-04: issue-flow.md の2箇所記載（→ 決定論ゲート G3/G4/G5）
- 決定論ゲート G3/G4 の grep で機械判定（track:app / track:harness の両文言が issue-flow.md に存在）
- G5（回帰ゲートスクリプト）が issue-flow.md 内の各 track 文言**2行以上**を機械判定し、「1箇所のみ更新」の偽陽性を補強する（plan-review Warning-2 対応）
- 加えて /test 時に Read で確認: 「イシュー作成時の自動実行フロー」ステップ3と「統合ルール」ステップ2の**2箇所とも**にトラックラベルルールが記載されていること（1箇所のみの更新は不合格）

### AT-05: オープンイシュー全件が track ラベルをちょうど1つ持つ
- コマンド: `gh issue list --state open --limit 200 --json number,labels --jq '[.[] | select(([.labels[].name | select(startswith("track:"))] | length) != 1)] | length'`
- 期待値: `0`（無し・二重付与ともに0件）
- false-green 検証: 実装前の実走で `25`（不合格）を返すことを確認済み（2026-07-14・plan_I107 調査結果）

### AT-06: バックフィルが承認済み分類表と全件一致
- コマンド: `gh issue list --state open --limit 200 --json number,labels --jq '.[] | [(.number|tostring), ([.labels[].name | select(startswith("track:"))] | join(","))] | join(":")'`
- 判定方法: 出力行と、下記期待値から構成した25行の双方を `sort` して diff で突き合わせ、過不足ゼロを確認する（役割分担: AT-05 が「ちょうど1」、AT-07 が件数、本TCが**割当先の正しさ**を担保する）
- 期待値: 以下の25行と過不足なく一致する（実装〜検証の間に新規起票があった場合はその番号のみ追加行として現れてよいが、その行も track ラベルちょうど1つであること）:
  - `track:app`: 199, 196, 193, 170, 156, 155, 44, 42
  - `track:harness`: 197, 191, 190, 189, 180, 179, 177, 176, 175, 173, 172, 169, 168, 154, 153, 10, 200

### AT-07: トラック別フィルタの動作
- コマンド: `gh issue list --state open --limit 200 --label "track:app" --json number --jq 'length'` → 期待値: `8`
- コマンド: `gh issue list --state open --limit 200 --label "track:harness" --json number --jq 'length'` → 期待値: `17`
- （AT-06 の注記どおり新規起票があった場合は、その分の増分を許容し AT-06 の結果と整合していること）

### AT-08: 文書回帰ゲートスクリプト（→ 決定論ゲート G5）
- コマンド: `bash scripts/claude/tests/test_i107_track_label_docs.sh`
- 検証内容: `track:app` / `track:harness` の各文言の行数下限 — SKILL.md ≥1行・issue-flow.md ≥**2行**（2箇所更新の代理指標）・worktree.md ≥1行。不足箇所を列挙して exit 1。
- 期待値: exit 0
- false-green 検証: 実装ステップ2 でスクリプト新設直後（文書更新前）に実走し **exit 非0** を記録すること（plan_I107 実装手順ステップ2）。worktree.md の grep は実装前に exit 1 を確認済み（2026-07-14・plan_I107 調査結果）
- **false-green 実証記録（2026-07-15・実装ステップ2 実施済み）**: 文書更新前の実走で **exit=1**（6項目全 FAIL: SKILL.md 0行/0行・issue-flow.md 0行/0行・worktree.md 0行/0行）→ 文書更新後（ステップ4完了時）の再実走で **exit=0**（6項目全 PASS: SKILL.md 2行/2行・issue-flow.md 4行/4行・worktree.md 1行/1行）

## 決定論ゲート（自動実走）
<!-- G1〜G5。G1〜G4 は実装前の実走で全件 exit 1（不合格）を確認済み。G5 はスクリプト新設直後（文書更新前）の実走で exit 非0 を記録する（plan_I107 調査結果・実装手順ステップ2） -->
```bash
grep -q "track:app" .claude/skills/issue-bootstrap/SKILL.md
grep -q "track:harness" .claude/skills/issue-bootstrap/SKILL.md
grep -q "track:app" docs/runbooks/issue-flow.md
grep -q "track:harness" docs/runbooks/issue-flow.md
bash scripts/claude/tests/test_i107_track_label_docs.sh
```
