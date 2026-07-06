---
name: fix-loop
description: When NG or tests fail: record facts, propose delta plan, get approval, fix, re-test.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /fix-loop

`$ARGUMENTS` = 対象イシュー（I###）。手順3.5／5.5／6.5 は `claude -p` サブエージェントによる
**順次ゲート**で、各レビュースクリプトの **exit code（0=次段へ／1=差し戻し）** を読む
（補助として stdout 末尾に `FIX_GATE: PASS|REMAND|SKIP` を出力）。

## 順次ゲートの共通ルール
- **しきい値**: 各レビューの VERDICT が `OK`（exit 0）のときのみ次段へ進む。**`BLOCKER`＋`HIGH` は差し戻し**（exit 1）。
- **差し戻しの形態（分類駆動）**: **診断 NG＝ユーザーに提示して停止**（手順2 で再診断・手順3 で別案）。実装/テスト NG は、まず NG を **(a) 実行の不備**（承認済み方針は正しく、実装/テストの実行だけ誤り）か **(b) 方針の誤り**（承認済みアプローチ自体が不適）に分類する（reviewer が付す「実行の不備/方針の誤り」の明示も参照）:
  - **(a) 実行の不備**: 自動で手順5（テストは手順5/6）へ戻り再修正 → 手順6 で**全テスト/lint/scan を再走（既存 OK 箇所への回帰＝無影響を確認）** → **手順5.5/6.5 で再レビュー**（手順4 のユーザー承認は不要＝自動・headless 維持）。原因/方針は自明のため手順3.5 は再実行しない。
  - **(b) 方針の誤り**: **手順2 へ環流して再診断 → 手順3 → 手順3.5 診断レビュー → 手順4 ユーザー承認（新案のため）→ 手順5…**。新方針の原因調査/方針を手順3.5 が審査する。2 回上限を待たず即エスカレーションしてよい。
  - **前回NG の明示検証（fail-closed）**: 実装/テスト再レビューでは、直前 REMAND のレビュー記録パスをスクリプトへ渡し（実装=第2引数・テスト=第3引数）、reviewer に各前回NG指摘の diff 上の解消を検証させる（未確認は未解消として REMAND）。
- **ループ暴走ガード**: 各ゲートの連続 NG が **2 回**に達したら自動ループバックを止め、ユーザーへエスカレーション（報告）する。カウンタは「各ゲート × 各 fix-loop 実行」で独立し、当該ゲートが PASS したら 0 にリセットする。
- **軽微例外**: 「単一ファイルのタイポ・フォーマット・コメント修正のみ、かつロジック・制御フロー・テスト対象の振る舞いを変えない」変更に限り、**実装/テストレビューのみ簡略化してよい**（診断レビューは常時必須・順次ゲート自体は維持）。適用可否は手順4 の承認時にユーザーが判断する（Claude 単独で skip しない・承認は「簡略化候補」扱いで手順5.5 の実 diff 再判定で最終確定）。
- **`claude -p` 不可時（未認証/headless/タイムアウト）**: 各スクリプトは `FIX_GATE: SKIP`＋exit 0（非ブロック）で「レビュー未実施」を記録に残す。fix-loop は停止せず次段へ進む（headless でも回る）。

## 手順

1) 失敗内容を「再現手順 / 期待値 / 実際値 / ログ」に分解して報告
2) 根本原因を調査・分析して報告（なぜ失敗したか）
   - セキュリティ観点も確認する（認証・認可の欠落、インジェクション、XSS、機密データ露出等に該当しないか）
3) 対応方法を複数案提示。各案に以下の軸でメリット・デメリットを添える:
   - セキュリティ影響（OWASP Top 10 関連リスクの有無、Django / React セキュリティガイドライン準拠）
   - ベストプラクティス適合（フレームワーク推奨パターン・コーディング規約との整合性）
   - 保守性・拡張性
   - リスク・副作用

3.5) **診断レビュー（修正前ゲート・診断は常時必須）**:
   - 診断メモ `docs/reviews/${ARGUMENTS}_fix_diagnosis_<ts>.md` を書く（章立て: 失敗分解／根本原因／対応方針＝**全案＋Claude 推奨**／影響調査の実施有無と結果＝同型バグ・他の呼び出し箇所・関連機能への波及）。
   - `bash scripts/claude/fix-diagnosis-review.sh $ARGUMENTS docs/reviews/${ARGUMENTS}_fix_diagnosis_<ts>.md` を実行（`<ts>` は上で生成したファイルのものをそのまま渡す）。
   - exit 0（`FIX_GATE: PASS`）→ 手順4 へ。exit 1（`FIX_GATE: REMAND`）→ **NG 内容をユーザーに提示して停止**（手順2 で再診断・手順3 で別案）。`FIX_GATE: SKIP`（未実施）→ その旨を手順4 で報告しユーザーが実施可否を判断。

4) 承認待ちで停止（ユーザーが案を選択。軽微例外による実装/テストレビュー簡略化の可否もここで判断）
5) 選択された案で修正

5.5) **実装レビュー（修正後・テスト前ゲート）**:
   - **fail-safe 再判定**: 手順4 で軽微例外を「簡略化候補」承認していた場合、実 diff が軽微例外条件（単一ファイル・振る舞い不変）に実際に合致するか再確認する。機械補助として `git diff --name-only`・`git diff --staged --name-only`・`git ls-files --others --exclude-standard`（**各単体コマンド。`| wc -l` 等のパイプで束ねない**）の変更ファイルが 1 つだけか、と振る舞い不変を確認する。合致すれば **`fix-implementation-review.sh` の呼び出しを省略して手順6 へ直行**（簡略化）。外れれば下記フルレビューへ。
   - `bash scripts/claude/fix-implementation-review.sh $ARGUMENTS` を実行（**再レビュー時は直前NGのレビュー記録を第2引数で渡す**: `bash scripts/claude/fix-implementation-review.sh $ARGUMENTS <前回NGレビュー記録.md>`）。exit 0 → 手順6 へ。exit 1 → **共通ルール「差し戻しの形態（分類駆動）」に従う**（(a) 実行の不備＝手順5 で再修正／(b) 方針の誤り＝手順2 へ環流し即エスカレーション）＋NG 報告（同一ゲート連続 NG 2 回でユーザーへエスカレーション）。`FIX_GATE: SKIP` → 記録して手順6 へ。

6) 自動テスト・リント・セキュリティスキャンを実行:
   - Backend: pytest / flake8（全エラー修正）/ bandit（MEDIUM 以上を修正対象。LOW は # nosec で抑制・理由記載必須）
   - Frontend: Jest / ESLint（error を修正対象、warning は記録）/ npm audit（high/critical を修正対象、moderate は記録・期限設定）
   - 成功（修正対象の警告・エラーなし）: 手順 6.5) へ
   - 失敗: 手順 1) に戻る（ループ）

6.5) **テストレビュー（テスト後ゲート）**:
   - (a) 手順6 で観測したテスト/lint/scan 出力を `docs/reviews/${ARGUMENTS}_fix_test_result_<ts>.md` に保存する（手順6 は再実行しない）。
   - (b) `bash scripts/claude/fix-test-review.sh $ARGUMENTS docs/reviews/${ARGUMENTS}_fix_test_result_<ts>.md` を実行（(a) で保存したパスをそのまま渡す。**再レビュー時は直前NGのテストレビュー記録を第3引数で渡す**）。
   - exit 0 → 手順7 へ。exit 1 → **共通ルール「差し戻しの形態（分類駆動）」に従う**（(a) 実行の不備＝手順5/6 でテスト追記・修正→再実行／(b) 方針の誤り＝手順2 へ環流し即エスカレーション）＋NG 報告（同一ゲート連続 NG 2 回でユーザーへエスカレーション）。`FIX_GATE: SKIP` → 記録して手順7 へ。

7) 再発防止記録を docs/tests/open/$ARGUMENTS_auto_test.md に追記:
   - なぜ失敗したか
   - 何を変えたか
   - セキュリティ上の考慮点（該当する場合）
   - 次回どう防ぐか
