# 診断レビュー [I587]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 根本原因は成立している。`APIView` から `GenericAPIView` に変えたことで `get_object()` が `filter_queryset()` を通る。全体設定の `OrderingFilter` はこのビューに `serializer_class` も `ordering_fields` も無いと例外を出す。再現テスト（`?ordering=id` で 500、`?search=x`・`?page=2` は通る）がその説明と合っている。 | `problems/views.py:653-668`、`settings.py:149` |
| Info | 対応方針 | 案 A が妥当。案 B・C を退ける理由も妥当。`pagination_class = None` は、`get_object()` が使わないため実害は無い。ただ、意図の明示としては有益。ビュー側のコメントに「1 件配信なので一覧の仕組みを切る」と一言書くとよい。 | 案 A |
| Info | 影響調査 | `GenericAPIView` 系でこのビューと同型の欠落があるのは `MediaAssetContentView` だけ、という結論は妥当。`UserProfileView`・`UserSettingsView`・`StudyStreakView`・`UserRegistrationView` は `serializer_class` を持つ。`FieldValidationView` も `serializer_class` を持ち、POST のみで `filter_queryset` を呼ばない。 | `accounts/views.py` |

## 影響調査の網羅性評価
- **同型バグ:** `views*.py` の `generics.` と `GenericAPIView` を grep で確認した。`serializer_class` も `ordering_fields` も無いビューは、このビューだけだった。`ViewSet` 系は今回の変更対象外で、すべて `serializer_class` を持つ前提。診断メモは `ViewSet` を全数確認したとまでは書いていないが、既存コードで I587 の変更範囲外なので問題ない。
- **波及:** `filter_backends = []` にしても、組織の境界と論理削除の絞り込みは `get_queryset()`（`visible_media_assets`）が担うので変わらない。404 の挙動も変わらず、TC-07 で確認できる。
- **テスト:** `?ordering=id` の再現テストが既にある。修正後は、`filter` や `format` などの別パラメータでも 200 になることを回帰テストに含めるとなお良い。

VERDICT: OK
