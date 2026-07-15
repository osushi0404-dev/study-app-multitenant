# I078 手動テスト（正解選択肢の表示・編集保持）

- 関連: docs/issues/open/I078.md / docs/plans/open/plan_I078.md / GitHub #156 / Draft PR #218
- **実施結果（2026-07-16）: 全9項目 OK**（Claude 4 項目・Human 5 項目。Human 分はユーザーのスクリーンショットで確認）
- 前提: BE（is_correct 露出）＋ FE（プレビュー正解マーク）の変更。API 露出の正否は自動テスト（`I078_auto_test.md`）が主で、本文書は UI 目視と配線確認。
- 使用アカウント（既存・I102 手動テストでパスワード認証確認済み 2026-07-07）:
  - **管理者**: `i102_admin@example.com` / `I102ManualTest!`（org: cute_school・問題 22 件あり）— UI テストの主アカウント
  - **一般ユーザー**: `i102_user@example.com` / `I102ManualTest!`（org: cute_school・role=user）— 出題画面の目視用
- URL: `http://localhost:3000`（frontend）/ 問題管理画面 = ログイン後メニューの「問題管理」（`/quiz-management`）

## 注意（キャッシュ）
問題一覧はユーザー別キャッシュ（TTL 1時間）のため、**実装反映直後は旧形式（is_correct 無し）が残り得る**。UI テストは No.4 の「問題を1件編集して保存」（キャッシュ無効化）を最初に実施してから確認する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec -T backend python -m pytest problems/tests/test_I078_is_correct_exposure.py -q` を実行 | TC-AUTO-01〜07 全 PASS | Claude | OK | 7 passed（2026-07-16） |
| 2 | `docker compose exec -T backend python -m pytest problems/tests -q` を実行 | 既存 61 件＋新規が全 PASS（回帰なし＝TC-AUTO-08） | Claude | OK | 68 passed（2026-07-16） |
| 3 | `ProblemAdminSerializer` の参照箇所を grep で確認（`grep -rn "ProblemAdminSerializer" backend/`） | 定義（serializers.py）と `ProblemViewSet.serializer_class`・import（views.py）のみ。出題・結果・AI 応答（`ProblemDisplaySerializer`／`QuizAnswerDetailSerializer`／`generate_ai`/`generate_adaptive` の `ProblemSerializer(...)`）に混入していない | Claude | OK | 定義2＋import1＋serializer_class1 の計4箇所のみ（2026-07-16） |
| 4 | `i102_admin@example.com` でログイン→問題管理→任意の問題を編集で開き**そのまま保存**（キャッシュ無効化）→同じ問題の**プレビュー（目のアイコン）**を開く | 正解の選択肢の行だけ緑枠＋緑背景で、行の右端に**チェックアイコン＋「正解」の緑 Chip** が表示される。不正解の選択肢にはマークが無い | Human | OK | 2026-07-16 スクリーンショット確認（ID247: book/water に正解 Chip・C/D にマーク無し） |
| 5 | 単一選択（single_choice）の問題で**編集ダイアログ**を開く | 正解の選択肢のラジオが**最初から選択済み**（全未選択ではない） | Human | OK | 2026-07-16 |
| 6 | 複数選択（multiple_choice）の問題で編集ダイアログを開く。**準備済み**: 科目「高校英語」の問題 ID 247「【I078手動テスト用・複数選択】次のうち、動詞として使える単語をすべて選びなさい。」（正解: book / water の2つ） | 正解の選択肢**複数**（book と water）のチェックが最初から入っている | Human | OK | 2026-07-16 スクリーンショット確認（A/B にチェック済み・C/D 未チェック） |
| 7 | No.5 の問題で**問題文だけ**書き換えて保存→再度編集ダイアログを開く | 保存が正常に完了し（「正解の選択肢を選択してください」エラーが出ない）、再表示時も**元の正解が保持**されている | Human | OK | 2026-07-16 スクリーンショット確認（「問題文修正」追記後も book/water が正解のまま） |
| 8 | `i102_user@example.com` でログイン→クイズ画面で **科目「高校英語」**を選択してクイズを開始し、問題を表示する | 出題画面の選択肢に正解マーク・「正解」ラベルが**表示されない**（従来どおり回答後にのみ正解が分かる） | Human | OK | 2026-07-16 スクリーンショット確認（出題中は正解マーク無し・回答後にのみ ✓ と解説表示＝従来どおり）。初回実施時「科目が登録されていません」→ i102_user に科目「高校英語」の `UserSubjectAccess` を付与（granted_by=i102_admin・キャッシュ無効化済み）して再実施 |
| 9 | `docker compose exec -T frontend npm test -- --watchAll=false` を実行 | 既存 2 suites / 7 tests PASS（FE 回帰なし） | Claude | OK | 7 passed・`npm run build` も成功（2026-07-16） |
