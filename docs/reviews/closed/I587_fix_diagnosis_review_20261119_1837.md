# 診断レビュー [I587]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | F1 は成立している。`views.py:731` の `ProblemMediaAsset.objects.filter(asset=media_asset).exists()` には `is_deleted=False` が付いていない。`problem_service.py:384` と `:418` には付いている。`ProblemMediaAsset` はカスタムマネージャーも `delete` のオーバーライドも持たない。そのため `problem_link.delete()` は物理削除で、自分の紐づけが判定に残ることはない。残るのは `delete_problem` が論理削除した相手の紐づけだけで、メモの再現手順と一致する。 | views.py:717-732 |
| Info | 対応方針 | F1-a（1行修正とTC-10への再現テスト追加）は的確。F1-b を見送る理由（止める指摘ではない F4 まで広がる）も妥当。 | 対応方針 F1 |
| Info | 対応方針 | F2 の推奨 F2-a は、AC9 を PR の外に出す。そのためユーザー確認が必要で、メモもそう書いている（止める条件 1）。F2-b を Claude だけで選ばない点、F2-c を grill-me の決定に反するとして退ける点は妥当。手順4の前に、確認を取る手順を必ず挟むこと。 | 対応方針 F2 |
| Info | 影響調査 | `.gitignore` の戻しと `backend/media` の復元が、ほかのテストやゲートに影響しないかは、TC-20〜22 が `backend/media` を見ないという記述で足りている。復元後に実際に確認するとなお良い。 | 影響調査 F2 |

## 影響調査の網羅性評価
共有判定の同型3か所（`_reconcile_images`・`delete_problem`・`delete_image`）を調べてあり、実コードでも確認できた。`_discard_asset` の呼び出し元と、中身の削除が1か所に集約されている点も押さえてある。F2 では、波及先（`LEGACY_MEDIA_ROOT`、app-1 の DB に行が無いこと、決定論ゲート）を挙げている。これを再診断（ゲートNG起因）とは読めないので、観点4は対象外。

VERDICT: OK
