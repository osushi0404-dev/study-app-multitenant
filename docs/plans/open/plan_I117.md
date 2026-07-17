# I117 計画書: auto_test テンプレートの実行コマンド例示を決定論ゲートセクションへ一本化 — omission-lint 誤 HIGH の再発防止

## 基本情報
- **計画書ID**: plan_I117
- **関連イシュー**: #215（統合: #190 = I100・同一ファイル/同一根本原因。本イシュークローズ時に重複クローズ）
- **Draft PR**: #229
- **作成根拠資料**: docs/issues/open/I117.md（起点イシュー・/grill-me 設計確認メモ5件を含む）
- **実装後評価**: docs/reviews/open/I117_review.md
- **作成日**: 2026-07-17

## 1. 背景/目的

### 原因の概要
auto_test テンプレートの冒頭に fenced ```bash の「実行コマンド（例）」ブロックがあり、利用者が自然にそこへテストスクリプトを書くと、omission-lint（I084）が「決定論ゲート宣言漏れ」として誤 HIGH を出す。**テンプレート通りに書くと機械チェックに落ちる**構造的な罠になっている。

### 詳細な原因分析
- omission-lint（`scripts/claude/code-review.sh` の `omission_lint()`・l.155-166）は「`## 決定論ゲート（自動実走）` セクション**外**の fenced ```bash/```sh 内に allowlist ゲートパターン（`bash scripts/claude/tests/*.sh`・`grep -[qL]`・`python3 -m json.tool`・`bash -n `・`python3 -m py_compile`）があると HIGH」を返す仕様（宣言漏れ検出としては妥当）。
- 一方テンプレート（`docs/tests/templates/auto_test_template.md` l.12-16）の冒頭は fenced ```bash の例示ブロックで、既定の中身は heavy コマンド（docker compose）のため単体では発火しないが、**テストスクリプトを書き足すと即 HIGH** になる。
- 実害: I098（コミット d22822d でインライン化して解消）・I109（code-review 初回 NG → 文書手直し1往復）の2回発生。
- 根本原因: omission-lint（I084）導入時に、lint が参照するテンプレートの既存例示部分との整合を同時監査する手順が無かった（I109 retro 5 Whys）。

### 目的
テンプレートの構造から罠を排除し（冒頭の fenced ブロック廃止）、恒久テストスクリプトで退行（fenced 例示の復活等）を機械検知できる状態にする。

## 調査結果（計画時実証・すべて実行済み）

### スパイク実証（omission-lint 挙動・2026-07-17 実測）
`omission_lint()` と同一ロジック（awk セクション抽出＋grep パターン）をテンプレートに対して実行し、4パターンを確認済み（スパイク完了。未知リスクなし）:
1. 現テンプレそのまま → **OK**（罠は潜在）
2. 冒頭 fenced にテストスクリプトを記載（罠再現）→ **HIGH**（false-green でないことを確認: 失敗条件注入で非合格になる）
3. 冒頭をインライン表記化した是正後テンプレ → **OK**
4. 是正後＋ゲートセクションに実コマンドを書いた完成文書 → **OK**

### 消費箇所の全件確認（grep 済み）
- テンプレート構造に依存する消費箇所: `code-review.sh` の `omission_lint()`（仕様は変更しない）のみ。
- スキル（test/implement/plan-issue/close/fix-loop）の auto_test 言及はフロー参照のみで、冒頭ブロック構造に非依存 → 変更不要。
- runbook は `issue-flow.md` がテンプレのパスを案内するのみ → 変更不要。「omission」への言及は runbook/スキルに存在しない。
- フック（pretooluse/posttooluse）: 無関係。

### 参照先実在性（機械確認済み）
- `docs/tests/templates/auto_test_template.md` ✅（Read 済み）
- `scripts/claude/code-review.sh` の `omission_lint()`・`I084-OM-GREP` マーカー行 ✅（Read 済み）
- `scripts/claude/tests/` ディレクトリ ✅（ls 済み・既存15スクリプト）

### 環境前提・ベースライン
- 使用ツール bash/awk/grep/sed/mktemp はスパイク実証で実走済み（本 WSL2 環境で動作確認済み。code-review.sh 自体が同ツールを使用）。
- 既存テスト（pytest/Jest/E2E）: アプリコード変更なしのため非該当。関連ベースラインは「現テンプレで omission-lint = OK」（上記1）。

## 2. 受け入れ条件
- [ ] auto_test_template.md の `## 決定論ゲート（自動実走）` セクション外に fenced ```bash ブロックが存在しない（冒頭の実行コマンド例はインラインコード表記）
- [ ] テンプレート冒頭に誘導注記（ゲート系コマンドはゲートセクションに書く・セクション外は omission-lint が HIGH）が含まれる
- [ ] allowlist パターンの列挙はゲートセクション内コメント1箇所のみに存在し（冒頭に複製しない）、その列挙が `omission_lint()` 実装と一致している
- [ ] テンプレートから生成した文書がそのまま omission-lint を PASS する
- [ ] `scripts/claude/tests/test_auto_test_template_lint.sh` が exit 0 で合格し、罠注入ケースで HIGH を検知する（decoy 反証込み）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `docs/tests/templates/auto_test_template.md`（変更）・`scripts/claude/tests/test_auto_test_template_lint.sh`（新規）

## 4. 変更点一覧（具体）

### 4-1. `docs/tests/templates/auto_test_template.md`
**修正方針**: 冒頭の fenced ```bash 例示を構造的に排除し、インラインコード列挙＋ゲートセクションへの誘導注記に置き換える。allowlist の列挙は既存のゲートセクション内コメント1箇所に集約し複製しない（code-review.sh 変更時の乖離ポイントを増やさない・grill Q3 確定）。

変更前（l.12-16）:
````markdown
実行コマンド（例）:
```bash
docker compose exec backend python manage.py test
docker compose exec frontend npm test
```
````

変更後（インライン表記＋誘導注記。注記内の行頭に ``` を置かない — omission-lint の fence トグルに干渉させないため）:
```markdown
<!--
  実行コマンド欄の書き方（I117）:
  - heavy な実行例はインラインコード表記で書く（下の既定例を参照）。fenced の bash ブロックはここに作らない。
  - ゲート系コマンド（テストスクリプト等）は必ず「## 決定論ゲート（自動実走）」セクションに書く。
    セクション外の fenced ブロックに書くと code-review.sh の omission-lint が「宣言漏れ」として HIGH を出す。
    対象コマンドの一覧（allowlist）はゲートセクション内コメントを参照。
-->
実行コマンド（例）: `docker compose exec backend python manage.py test` / `docker compose exec frontend npm test`
```

「結果:」欄は現状維持。「## 決定論ゲート（自動実走）」セクションは、コメント内 allowlist 列挙の grep 表記のみ omission-lint の検知対象 `grep -[qL]` と一致するよう更新する（プランレビュー 20260717_2345 Warning 対応。実走側 `classify_gate()` は `grep *` 前方一致で `-L` も許可済みのため、コメント追記のみで整合する）:

変更前（ゲートセクションコメント内）:
```
`bash scripts/claude/tests/*.sh` / `grep -q 文言 file`（存在）/ `! grep -q 文言 file`（不在）/
```

変更後:
```
`bash scripts/claude/tests/*.sh` / `grep -q 文言 file`（存在）/ `grep -L 文言 dir/*`（不在ファイル一覧）/ `! grep -q 文言 file`（不在）/
```

### 4-2. `scripts/claude/tests/test_auto_test_template_lint.sh`（新規）
**修正方針**: テンプレートと omission-lint の整合を恒久検証する。`omission_lint()` と同一の判定ロジック（awk＋grep）をスクリプト内に持ち、複製乖離は TC-07（パターン同期チェック）で機械検知する。**合格 = exit 0**・失敗時は非ゼロ終了＋NG 内容を stderr に出力（I122 の方向性と整合）。

検証内容（スクリプト内 TC）:
| TC | 検証内容 | 期待値 |
|----|---------|--------|
| TC-01 | テンプレのゲートセクション外に fenced ```bash/```sh ブロックが 0 件（AC1・heavy 含む全 fenced が対象） | 件数 0 |
| TC-02 | 冒頭誘導注記が存在（「決定論ゲート（自動実走）」への誘導文言と omission-lint への言及） | grep ヒット |
| TC-03 | omission_lint() の 5 検知パターンに対応する 6 キーワード（`bash scripts/claude/tests/`・`grep -q`・`grep -L`・`python3 -m json.tool`・`bash -n`・`python3 -m py_compile`）がゲートセクション内コメントに全て存在し、セクション外に列挙の複製が無い（AC3） | 6/6 存在・複製 0 |
| TC-04 | 是正後テンプレそのものに omission-lint ロジック → OK（AC4） | OK |
| TC-05 | ゲートセクションに実コマンド（`bash scripts/claude/tests/test_auto_test_template_lint.sh`）を書いた生成文書 → OK（AC4） | OK |
| TC-06 | decoy 反証: セクション外 fenced に allowlist コマンドを注入した一時文書 → HIGH を検知（false-green 防止） | HIGH |
| TC-07 | スクリプト内の複製 grep パターンが `code-review.sh` の `I084-OM-GREP` マーカー行のパターンと一致（複製乖離検知） | 一致 |

- ヘッダーコメントに `# I117: ...` で由来を記載（命名は機能名・grill Q4 確定）。
- 一時ファイルは `mktemp` で作成し必ず削除。`code-review.sh` 本体は読み取りのみで変更しない。

## 5. 実装手順（ステップ）
1. **テンプレート是正**: 4-1 の通り `auto_test_template.md` の冒頭を変更する（→ TC-01/02/03/04 参照）。
2. **テストスクリプト作成**: 4-2 の通り `test_auto_test_template_lint.sh` を新規作成し実行権限を付与する（→ TC-01〜07 参照。ステップ1完了が前提: 是正後テンプレを検証対象とするため）。
3. **決定論ゲートの実走・記録**: auto_test 文書（docs/tests/open/I117_auto_test.md）の全 TC を実行し結果を記録する。

- 未知リスク先行: なし（最大の不確実要素だった omission-lint 挙動は計画時スパイクで実証済み）。
- 垂直スライス: 対象がテンプレ1＋スクリプト1で完結するため該当なし。
- サービス再起動: 不要（docs・スクリプトのみ）。

## 6. テスト計画
### 自動
- `docs/tests/open/I117_auto_test.md` の決定論ゲート: `bash scripts/claude/tests/test_auto_test_template_lint.sh`（TC-01〜07 を内包・合格=exit 0）。
- 既定テスト（pytest/Jest/E2E）: 非該当（アプリコード変更なし）。auto_test.md にその旨明記。
### 手動
- `docs/tests/open/I117_manual_test.md` 参照（テンプレ可読性の目視確認: Claude によるファイル確認＋Human による文言の平易さ確認）。

## 7. ロールバック
- `git revert` のみ（docs 1 ファイル変更＋スクリプト 1 ファイル追加。DB・設定・サービスへの影響なし）。

## 8. Risk & 回避策
- **R1: 注記集約により冒頭だけ読むと allowlist の具体が見えない** → 冒頭注記にゲートセクション内コメントへの誘導を明記（grill Q3 で許容確定・テンプレは1画面規模）。
- **R2: テストスクリプトの複製ロジックが code-review.sh と乖離** → TC-07 のパターン同期チェックで機械検知（`I084-OM-GREP` マーカー行と突き合わせ）。
- **R3: 既存 open/closed のテスト文書は遡及修正しない** → スコープ外（イシュー明記）。既存文書で HIGH が出る場合は当該イシューで個別対応。
- **R4: 注記の行頭 ``` が omission-lint の fence トグルを誤作動させる** → 変更後テキストで行頭 ``` を使わない構成にし、TC-04 で機械確認。

## 9. セキュリティ・品質チェック（plan-issue 必須確認）
- **セキュリティ影響なし**（docs テンプレとテストスクリプトのみ。認証・認可・入力・機密データ・依存ライブラリの変更なし。スクリプトは読み取り＋mktemp 一時ファイルのみで破壊的操作なし）。
- **P3/P5/P8 影響なし**（DB変更・外部API・非同期・バッチ・新規インフラ・依存関係ファイル変更なし）。
- **P6 影響なし**（フロントエンド変更・性能懸念なし）。
- **P9 影響なし**（個人情報・未成年データ・テナントデータを扱わない）。
- **要件適合性**: 変更は AC の範囲内（仕様追加なし）。マルチテナント・ステータス遷移: 非該当。
- **テスト計画**: バグ（構造的罠）の再発防止テスト = TC-01/TC-06。テストレベル = 決定論シェルテスト（ユニット相当）。認可テスト: 非該当。

## 10. 承認ポイント
- [ ] 計画内容（変更点/影響）: テンプレ冒頭のインライン化＋誘導注記（列挙はゲートセクションに集約）・恒久テストスクリプト新規作成
- [ ] Danger Ops: 無（docs＋テストスクリプトのみ・ロールバックは revert のみ）
- [ ] テスト計画: 決定論ゲート TC-01〜07（decoy 反証込み）＋手動目視

## レビュー結果
- [20260717_2345 判定: ✅ 完了](../../reviews/I117_plan_review_20260717_2345.md)
