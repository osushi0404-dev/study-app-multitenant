# I107 計画書: GitHubイシューのトラック軸ラベル分類（track:app / track:harness）導入

## 基本情報
- **計画書ID**: plan_I107
- **関連イシュー**: docs/issues/open/I107.md（GitHub Issue: #200）
- **Draft PR**: #202
- **作成根拠資料**: docs/issues/open/I107.md（起点イシュー・grill-me 設計確認メモ含む）
- **実装後評価**: docs/reviews/open/I107_review.md
- **作成日**: 2026-07-14

## 1. 背景/目的
- 単一リポジトリに「学習アプリ開発」（primary checkout: study-app-multitenant）と「ハーネス改善」（linked worktree: wt-harness）の2トラックのイシューが混在するが、GitHubラベルは種別軸（bug/enhancement/documentation/refactoring）のみで、トラック軸が存在しない。
- 種別と独立した第2軸ラベル `track:app` / `track:harness` を新設し、起票フローで両軸付与を必須化・既存オープンイシューへバックフィルすることで、`gh issue list --label track:*` によるトラック別の一覧・棚卸しを可能にする。

## 調査結果（事前調査・2026-07-14 実施）

### 環境前提確認
- `gh` CLI: **v2.88.1**（認証済み。`gh label list` / `gh issue list` / `gh issue edit` / `gh label create` を使用。すべて本セッションで実行実績あり）
- 追加ツール不要（JSON 抽出は `gh` 組み込みの `--jq` を使用。外部 `jq` に依存しない）

### 消費箇所の全件列挙（grep 照合済み）
`--label`・「ラベル」を docs/ .claude/ scripts/ に対して grep し、ラベル付与ルールの宣言・消費箇所を全件特定した:
| 箇所 | 内容 | 本イシューでの扱い |
|------|------|------------------|
| `.claude/skills/issue-bootstrap/SKILL.md` step 4 | `gh issue create --label "[種別に応じたラベル]"` ＋種別4分類の定義 | **更新対象**（2軸必須化＋判定基準追記） |
| `docs/runbooks/issue-flow.md` 冒頭「イシュー作成時の自動実行フロー」ステップ3 | 同上の種別4分類の定義 | **更新対象** |
| `docs/runbooks/issue-flow.md` 「イシューフロー（統合ルール）」ステップ2 | `gh issue create --label` のコマンド例 | **更新対象** |
| `docs/claude-code-structure.md:202` | 「`gh issue create` で GitHub Issue を登録（ラベル付き）」の一般記述 | 対象外（具体ラベル名を持たないため track 軸導入後も記述として正しい） |
| `docs/runbooks/worktree.md §10` | トラック構成表（ラベル記述なし・「ラベル」grep 非ヒット） | **更新対象に追加**（plan-review Warning-1 採用。対応 GitHub ラベル列を追記し GitHub 側と照合可能にする） |
| その他（closed 計画書・legacy CLAUDE.md・migration 資料・UIラベルの話） | 歴史的文書・無関係 | 対象外 |

### GitHub 現状（ツール実走済み）
- 既存ラベル10種: bug(#d73a4a) / documentation(#0075ca) / duplicate(#cfd3d7) / enhancement(#a2eeef) / good first issue(#7057ff) / help wanted(#008672) / invalid(#e4e669) / question(#d876e3) / wontfix(#ffffff) / refactoring(#fbca04)。`track:` prefix のラベルは **0件**。
- オープンイシュー: **25件**（既存24件＋I107=#200）。track ラベルをちょうど1つ持つもの: 0件（未付与25件）。
- バックフィル分類は grill-me で**ユーザー承認済み**（イシューの「設計確認メモ」参照。app 8件 / harness 17件）。

### 決定論ゲートの false-green 自己検証（失敗条件の注入＝実装前の現状態で実走）
| 検証コマンド | 実装前（現状態）の結果 | 実装後の期待 | 判定 |
|-------------|----------------------|-------------|------|
| `grep -q "track:harness" .claude/skills/issue-bootstrap/SKILL.md` | **exit 1（不合格）** | exit 0 | false-green でない ✅ |
| `grep -q "track:harness" docs/runbooks/issue-flow.md` | **exit 1（不合格）** | exit 0 | false-green でない ✅ |
| track ラベル数カウント（AT-01/02 の検証式） | **0（不合格。期待値2と不一致）** | 2 | false-green でない ✅ |
| track ラベル非1件のオープンイシュー数（AT-05 の検証式） | **25（不合格。期待値0と不一致）** | 0 | false-green でない ✅ |
| `grep -q "track:app" docs/runbooks/worktree.md`（G5 の一部） | **exit 1（不合格）** | exit 0 | false-green でない ✅ |

いずれも「変更が存在しない状態で確実に不合格を返す」ことを実走で確認済み。G5（回帰ゲートスクリプト）自体はスクリプト新設が実装ステップのため、実装手順ステップ2 で「文書更新前に実走 → exit 非0」を記録して false-green 実証を完了する。

## 2. 受け入れ条件（イシューの AC を転記）
- [ ] `gh label list` に `track:app` / `track:harness` が存在し、description に対応 worktree（study-app-multitenant / wt-harness）が明記されている
- [ ] issue-bootstrap SKILL.md の step 4 が「種別＋トラックの2ラベル必須付与」になっており、トラック判定基準（対象パスベース）が記載されている
- [ ] docs/runbooks/issue-flow.md のラベル設定記載箇所（2箇所）に同じトラックラベルルールが記載されている
- [ ] オープンイシュー全件に `track:app` / `track:harness` のいずれか1つが付与されている（検証: `gh issue list --state open --limit 200 --json number,labels` の各要素で track ラベル数がちょうど1。無し・二重付与が0件）
- [ ] バックフィルの付与内容が、「設計確認メモ」のユーザー承認済み分類表（app 8件 / harness 17件）と一致している
- [ ] `gh issue list --label track:harness` / `--label track:app` でトラック別一覧が取得できる
- [ ] `bash scripts/claude/tests/test_i107_track_label_docs.sh` が exit 0（かつ文書更新前の実走で exit 非0 を記録済み＝false-green でない）
- [ ] docs/runbooks/worktree.md §10 の表に対応 GitHub ラベル（track:app / track:harness）が記載されている

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: GitHub リポジトリのラベル定義（2件追加のみ・既存ラベル変更なし）、オープンイシュー25件のラベル（追加のみ・本文変更なし）
- ドキュメント: `.claude/skills/issue-bootstrap/SKILL.md`、`docs/runbooks/issue-flow.md`、`docs/runbooks/worktree.md`（§10 への対応ラベル追記のみ）
- スクリプト: `scripts/claude/tests/test_i107_track_label_docs.sh`（新設・文書回帰ゲート）

## 4. 変更点一覧（具体）

### 4-1. GitHubラベル新設（2件）
既存10ラベルの色（上記調査結果）と重複しない2色を使用する:
```bash
gh label create "track:app" --description "学習アプリ開発トラック（worktree: study-app-multitenant）" --color "0e8a16"
gh label create "track:harness" --description "ハーネス改善トラック（worktree: wt-harness）" --color "5319e7"
```
- `track:app` = `#0e8a16`（緑）/ `track:harness` = `#5319e7`（紫）。GitHub 標準パレットの色で、既存ラベルと非重複。

### 4-2. `.claude/skills/issue-bootstrap/SKILL.md` — step 4 の更新
コマンド例の `--label` を2軸に変更し、「ラベル設定」を以下の内容に置き換える（既存の種別4分類は維持）。複数ラベルはコンマ区切りでなく **`--label` フラグの分割形式**で記述する（gh CLI で確実に動作する形式。plan-review 指摘 Info の採用）:

```
--label "[種別ラベル]" --label "[トラックラベル]"
```

**ラベル設定（2軸・両方必須）**:
- **種別ラベル**（既存どおり）: Bug → `bug` / Feature → `enhancement` / Documentation → `documentation` / Refactoring → `refactoring`
- **トラックラベル**（`track:app` / `track:harness` のどちらか1つを必須付与）:
  - 変更対象が `docs/runbooks/`・`scripts/claude/`・`.claude/`（skills/hooks/settings）・レビュー/ゲート/テンプレートの仕組み → `track:harness`（対応 worktree: wt-harness）
  - 変更対象が `backend/`・`frontend/`・`e2e/` 等のアプリ機能・アプリのテスト → `track:app`（対応 worktree: study-app-multitenant）
  - 両方にまたがる場合は主目的側に**単一付与**（両付与はしない。判断に迷う場合はユーザーに確認）

### 4-3. `docs/runbooks/issue-flow.md` — ラベル設定2箇所の更新
- 冒頭「イシュー作成時の自動実行フロー」ステップ3の「ラベル設定」と、「イシューフロー（統合ルール）」ステップ2のコマンド例の**両方**に、4-2 と同一のルール（コマンド例の `--label` 2軸化＋トラックラベル定義・判定基準）を反映する。
- 2箇所の記述は 4-2 の SKILL.md と**同一粒度**（具体ラベル名・判定基準の対象パスまで明記）とし、分岐間パリティを保つ。

### 4-4. `docs/runbooks/worktree.md` — §10 トラック構成表への対応ラベル追記（plan-review 指摘 Warning-1 の採用）
§10「現時点のトラック構成（参考）」の表に「対応 GitHub ラベル」列を追加し、ハーネス改善 → `track:harness`、アプリ開発 → `track:app` を記載する（表のスナップショット性は維持・1行ずつの追記のみ）。

### 4-5. `scripts/claude/tests/test_i107_track_label_docs.sh` — 文書回帰ゲートの新設（plan-review 指摘 Warning-2 の採用）
G1〜G4 の `grep -q` は「1回でも存在」しか検証できず、issue-flow.md の**2箇所更新**を保証しない（1箇所のみ更新でも合格する偽陽性）。これを補強する回帰ゲートスクリプトを新設する:
- 検証内容（行数カウントの下限チェック）: `track:app` / `track:harness` の各文言が、`.claude/skills/issue-bootstrap/SKILL.md` に**1行以上**、`docs/runbooks/issue-flow.md` に**2行以上**（2箇所更新の代理指標）、`docs/runbooks/worktree.md` に**1行以上**存在すること。不足があれば不足箇所を stderr に列挙し **exit 1**。
- 既存の `scripts/claude/tests/test_*.sh` と同じ配置・命名規約。将来、文書編集でルール記述が消えた場合の回帰検知として恒久的に機能する。
- 実装時の false-green 実証手順は「5. 実装手順」ステップ2 に組み込む（文書更新**前**に実走して exit 非0 を記録 → 文書更新**後**に exit 0）。

### 4-6. 既存オープンイシューへのバックフィル（25件・承認済み分類表どおり）
`gh issue edit <番号> --add-label <トラックラベル>` を1件ずつ実行する（`--add-label` は追加のみで既存ラベル・本文に影響しない）:
- `track:app`（8件）: **#199, #196, #193, #170, #156, #155, #44, #42**
- `track:harness`（17件）: **#197, #191, #190, #189, #180, #179, #177, #176, #175, #173, #172, #169, #168, #154, #153, #10, #200**

## 5. 実装手順（ステップ）

> 本イシューは GitHub 設定＋運用ドキュメントのみの変更で、DB/API/UI のレイヤーを持たないため、垂直スライス原則は「ラベル実体 → 運用ルール → 適用（バックフィル）」の縦貫通として読み替える。未知リスクは事前調査で解消済み（gh コマンドはすべて本セッションで実行実績あり）。

1. **ステップ1: GitHubラベル新設**（4-1 のコマンド2件を実行）→ AT-01/AT-02 参照
2. **ステップ2: 文書回帰ゲートスクリプト新設**（4-5 の内容）。文書更新**前**にこの時点で実走し、**exit 非0（不合格）となることを記録**する（G5 の false-green 実証。以降のステップ3/4 が完了するまで合格しないことが正しい）→ AT-08 参照
3. **ステップ3: issue-bootstrap SKILL.md の step 4 更新**（4-2 の内容。ステップ1と独立・並行可）→ AT-03 参照
4. **ステップ4: issue-flow.md の2箇所＋worktree.md §10 更新**（4-3 / 4-4 の内容。ステップ3と同一内容の反映。完了後に G5 を再実走し exit 0 を確認）→ AT-04/AT-08 参照
5. **ステップ5: バックフィル25件**（4-6 の一覧どおり。**ステップ1の完了が前提**）→ AT-05/AT-06/AT-07 参照
6. **ステップ6: 文書コミット・プッシュ**（SKILL.md / issue-flow.md / worktree.md / テストスクリプト / 計画・テスト・レビュー文書一式を feature ブランチにコミット）

## 6. テスト計画
- **テストレベルの選択**: 対象がGitHub設定と運用文書のため、ユニット/結合/E2E は該当なし。検証は (a) 文書側 = grep による決定論ゲート（自動テスト文書の「決定論ゲート」セクション）、(b) GitHub側 = `gh` コマンド実走による状態検証（自動テスト文書 TC・/test で Claude が実行）の2層で行う。
- **自動**: docs/tests/open/I107_auto_test.md（AT-01〜AT-08。ラベル存在・文書更新・バックフィル全件一致・フィルタ動作・文書回帰ゲート）。決定論ゲートは G1〜G4（grep）＋ G5（回帰ゲートスクリプト＝issue-flow.md の2箇所更新を行数下限で担保）。
- **手動**: docs/tests/open/I107_manual_test.md（Claude 実施4件＋Human 実施1件=GitHub Web UI でのフィルタ目視）
- 再発防止テスト: 該当なし（バグ修正ではない）。認可・テナント境界: 該当なし（アプリコード変更なし）。

## 7. ロールバック
```bash
# ラベル自体を撤去する場合（付与済みイシューからも自動的に外れる）
gh label delete "track:app" --yes
gh label delete "track:harness" --yes
# 個別付与のみ取り消す場合
gh issue edit <番号> --remove-label "track:app"   # または track:harness
```
- 文書変更は `git revert`（または feature ブランチ破棄）で復元可能。
- いずれも既存ラベル・イシュー本文には影響しない（追加分の削除のみ）。

## 8. Risk & 回避策
| リスク | 回避策 |
|--------|--------|
| バックフィルの誤分類 | 分類表は grill-me でユーザー承認済み（イシューの設計確認メモ）。AT-06 で承認済み分類表との全件一致を機械検証する |
| バックフィル中の中断（部分適用） | `--add-label` は冪等（再実行しても二重にならない）。AT-05（全件ちょうど1）が完了判定になる |
| 実装とAC検証の間に新規イシューが起票され「track無し」が混入 | AT-05 実行時点の差分として検出される。混入分は判定基準に従い付与（本イシューのルール適用第1号として扱う） |
| ラベル名の打鍵ミス（例: track:harnes） | AT-01/02 が name 完全一致で検証。AT-05 は `track:` prefix 判定のため誤名も「ちょうど1」に数えられるが、AT-01/02 の完全一致検証と AT-06 の分類表一致検証で捕捉される |
| セキュリティ影響 | **セキュリティ影響なし**（コード変更なし・認証認可変更なし・機密データなし・依存追加なし。gh は認証済み既存環境を使用） |

- **P3/P5/P8 影響なし**（DB変更なし・外部API/非同期/バッチなし・新規インフラなし。gh によるGitHub API 呼び出しは既存運用の範囲内でコスト増なし）
- **P6 影響なし**（フロントエンド変更なし・性能要件なし）
- **P9 影響なし**（個人情報・未成年データ・テナントデータを扱わない）

## 9. 承認ポイント
- [ ] 計画内容（変更点/影響）: ラベル2件新設＋文書3ファイル更新（SKILL.md / issue-flow.md / worktree.md §10）＋文書回帰ゲートスクリプト新設＋バックフィル25件（承認済み分類表どおり）
- [ ] ラベルの具体値: 名称 `track:app` / `track:harness`（イシューで確定済み）、**色 = app:`#0e8a16`（緑）/ harness:`#5319e7`（紫）**（イシューの制約「既存と重複しない2色」の範囲内で本計画が確定した具体値）
- [ ] Danger Ops: **無**（追加のみ・非破壊。ロールバックはラベル削除/付与解除で可逆）
- [ ] テスト計画: 決定論ゲート（grep 4件・false-green 検証済み）＋ gh 実走検証（AT-01〜07）＋ Human 目視1件

### 設計判断の明示（イシュー明記 / 仮定の区別）
| 設計判断 | 出所 |
|---------|------|
| ラベル名 `track:app` / `track:harness`・prefix方式 | イシューに明記 |
| トラック判定基準（対象パスベース）・両属イシューは主目的側に単一付与 | イシューに明記 |
| バックフィル分類（app 8件 / harness 17件） | イシューに明記（grill-me でユーザー承認済み） |
| クローズ済みイシューは対象外・検知ゲート新設はスコープ外 | イシューに明記 |
| ラベル色（`#0e8a16` / `#5319e7`） | イシューの制約（既存と重複しない2色）内で計画が確定 → 本承認ポイントで確認 |
| バックフィルを `gh issue edit --add-label` で1件ずつ実行 | 仮定ではなく gh の標準操作（追加のみ・冪等・非破壊のため採用） |
| `--label` の分割形式・worktree.md §10 追記・文書回帰ゲートスクリプト新設 | plan-review（I107_plan_review_20260714_2158.md）の指摘 Info/Warning-1/Warning-2 を採用 |

## レビュー結果
- [20260714_2208 判定: ✅ 完了](../../reviews/closed/I107_plan_review_20260714_2208.md)
- [20260714_2158 判定: ✅ 完了](../../reviews/closed/I107_plan_review_20260714_2158.md)

### レビュー指摘への対応記録
- 2158 レビュー（Warning×2・Info×1）: 3件すべて採用し計画・テスト・イシューに反映（§4-2 分割形式 / §4-4 worktree.md §10 / §4-5 回帰ゲート）→ 2208 で再レビュー済み。
- 2208 レビュー（Warning×1・Info×1）: §2 に AC 2項目を転記・AT-06 に判定方法を追記。いずれもレビューの「対応」欄が指定した転記/追記のみで新規設計判断を含まないため、3回目の再レビューは免除（I089 の免除理由記録）。
