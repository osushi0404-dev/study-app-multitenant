# 診断レビュー [I609]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 原因は成立している。一覧は 1 時間キャッシュされ、`import_problems` だけが無効化を呼ばない。再現（キャッシュ作成→取り込み→開き直し）と DB の 3 問の確認があり、証拠も足りている。 | import_problems.py:415 |
| Info | 対応方針 | 案 A は妥当。ただし `invalidate_problems_cache` は `subject_id` を無視して問題キャッシュ全体を消す。診断メモの「科目を指定して消す」という含みは実装とずれるが、案 A の実装には影響しない。実装時は、引数が後方互換用であることをコメントに残すとよい。 | cache_service.py:122-135 |
| Info | 影響調査 | `serializers.py:264` の `Problem.objects.create` と `problem_service.py:80` が、診断メモの同型調査に載っていない。ただし、どちらも API／AI 生成の経路で呼び出し側のビューが無効化している（`views.py:283,415,439,527`）。実装時に呼び出し元で漏れがないか、一度確認するとよい。 | serializers.py:264 / problem_service.py:80 |
| Info | 影響調査 | `generate_ai_problems` コマンドを同型の抜けとして認識している。範囲外とし retro で扱う判断は、動いていない経路であることを理由にしており許容できる。retro での起票は確実に行うこと。 | generate_ai_problems.py |

## 影響調査の網羅性評価
- 同型の抜けは、問題を作る経路（API、AI 生成、`import_problems`、`generate_ai_problems`）で調べてある。実装で唯一の未対応が `generate_ai_problems` だと特定でき、扱いの理由もある。
- 更新・削除の経路は無効化の行を列挙してある。
- キャッシュしない `problem_count` と、DB を直接読むクイズ出題も確認してあり、関連機能への波及も足りている。
- 案 B（シグナル）と案 C を比較したうえで、案 A を推奨している。その理由も妥当。
- テスト（TC-15）を、直す前に落ちることを確かめる形で計画している。

VERDICT: OK
