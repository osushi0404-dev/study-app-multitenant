# I078 手動テスト（正解選択肢の表示・編集保持）

- 関連: docs/issues/open/I078.md / docs/plans/open/plan_I078.md / GitHub #156 / Draft PR #218
- 前提: BE（is_correct 露出）＋ FE（プレビュー正解マーク）の変更。API 露出の正否は自動テスト（`I078_auto_test.md`）が主で、本文書は UI 目視と配線確認。
- 使用アカウント（既存・確認済み）:
  - **管理者**: `admin@example.com`（org: cute_school・問題 22 件あり）— UI テストの主アカウント
  - **一般ユーザー**: `i102_user@example.com`（org: cute_school・role=user）— 出題画面の目視用
- URL: `http://localhost:3000`（frontend）/ 問題管理画面 = ログイン後メニューの「問題管理」（`/quiz-management`）

## 注意（キャッシュ）
問題一覧はユーザー別キャッシュ（TTL 1時間）のため、**実装反映直後は旧形式（is_correct 無し）が残り得る**。UI テストは No.4 の「問題を1件編集して保存」（キャッシュ無効化）を最初に実施してから確認する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec -T backend python -m pytest problems/tests/test_I078_is_correct_exposure.py -q` を実行 | TC-AUTO-01〜07 全 PASS | Claude | | |
| 2 | `docker compose exec -T backend python -m pytest problems/tests -q` を実行 | 既存 61 件＋新規が全 PASS（回帰なし＝TC-AUTO-08） | Claude | | |
| 3 | `ProblemAdminSerializer` の参照箇所を grep で確認（`grep -rn "ProblemAdminSerializer" backend/`） | 定義（serializers.py）と `ProblemViewSet.serializer_class`・import（views.py）のみ。出題・結果・AI 応答（`ProblemDisplaySerializer`／`QuizAnswerDetailSerializer`／`generate_ai`/`generate_adaptive` の `ProblemSerializer(...)`）に混入していない | Claude | | 漏洩配線チェック |
| 4 | `admin@example.com` でログイン→問題管理→任意の問題を編集で開き**そのまま保存**（キャッシュ無効化）→同じ問題の**プレビュー（目のアイコン）**を開く | 正解の選択肢の行だけ緑枠＋緑背景で、行の右端に**チェックアイコン＋「正解」の緑 Chip** が表示される。不正解の選択肢にはマークが無い | Human | | |
| 5 | 単一選択（single_choice）の問題で**編集ダイアログ**を開く | 正解の選択肢のラジオが**最初から選択済み**（全未選択ではない） | Human | | |
| 6 | 複数選択（multiple_choice）の問題で編集ダイアログを開く（無ければ「問題を追加」で複数選択・正解2つの問題を新規作成してから開く） | 正解の選択肢**複数**のチェックが最初から入っている | Human | | |
| 7 | No.5 の問題で**問題文だけ**書き換えて保存→再度編集ダイアログを開く | 保存が正常に完了し（「正解の選択肢を選択してください」エラーが出ない）、再表示時も**元の正解が保持**されている | Human | | AC「正解の取り違え・未指定エラーなし」 |
| 8 | `i102_user@example.com` でログイン→クイズ画面で **No.4 で使用した問題と同じ科目**を選択してクイズを開始し、問題を表示する | 出題画面の選択肢に正解マーク・「正解」ラベルが**表示されない**（従来どおり回答後にのみ正解が分かる） | Human | | 答え漏洩なしの目視（API は TC-AUTO-05 で担保済み）。No.4 実施時に使用した科目名を備考欄に控えておく |
| 9 | `docker compose exec -T frontend npm test -- --watchAll=false` を実行 | 既存 2 suites / 7 tests PASS（FE 回帰なし） | Claude | | |
