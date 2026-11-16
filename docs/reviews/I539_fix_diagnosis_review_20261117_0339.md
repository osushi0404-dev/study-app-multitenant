# 診断レビュー [I539 / F5]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 根本原因は成立している。`Count('problems')` は削除済みも数え、出題側の `available_problems` は `is_deleted=False` で絞る。この食い違いを、コードで確かめた行番号つきで説明できている。 | `subject_service.py:68,76,160`、`tenant_scope.py:33-35` |
| Info | 対応方針 | 案 A（共通の式を 1 つ置き、3 か所で使う）は妥当。案 B は `OuterRef` が要って重くなり、案 C は同じ穴を残す。却下理由も適切。`available_problems` と同じ条件だと分かるよう、式のそばにコメントを置く対応も入っている。 | 対応方針 |
| Info | 影響調査 | 「既存テストに削除済みを数える前提のものが無い」ことは、メモでは確認手順の記載だけで結果が書かれていない。grep では `problem_count` を見るテストは I494、I431、I539 の 3 つだった。どれも削除済みを数える前提ではなく、I539 のテストには削除済みを除く確認が既にある。着手時に実行結果を一言残せばよい。 | 影響調査の最終項 |
| Info | 影響調査 | `problem_count` の使われ方を grep した範囲では、シリアライザ 2 つ（`serializers.py:23,63`）と openapi だけだった。`studylogs/models.py` の `problem_count` は別の概念（弱点分析）で無関係。`problems/utils.py:234` や `core/tasks.py:126` など `Problem` を数える他の箇所は、すでに `is_deleted=False` で絞ってある。 | 影響調査 |
| Info | 対応方針 | 科目管理の「問題数」も削除済みを除く側に変わる。一覧の見え方が変わるので、完了報告に 1 行書くとよい。 | 案 A の影響 |

## 影響調査の網羅性評価
- 同型バグ（同じパターンの別箇所）: `Count('problems'` はバックエンド全体で `core/subject_service.py` の 3 か所だけ、というメモの主張を grep で確認した。他に同型の数え方は無い。
- 呼び出し箇所: `get_user_subjects` は `problems/views.py:52`、`get_user_selected_subjects` は `api/views/user_subjects.py` 経由で、どちらも調査済みと読める。`dashboard/selectors.py:177` と `studylogs/views.py:259` は `annotate_count` を使わないので影響しない。
- キャッシュ: キャッシュ復元側の `:68` も同じ式に直す計画になっている。キャッシュには ID しか入れないので、数のずれは残らない。

調査は十分で、推奨案で修正に進んでよい。

VERDICT: OK
