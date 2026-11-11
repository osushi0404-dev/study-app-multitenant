# 敵対的レビュー [I446]（別プロセス・2026-11-12 02:40）

- 見た範囲: cc77b27ae901d741ab7521f4181a5150a502c79f...13116063ad4bfc68dad9cdaf9dea345df790ce3c
- 所要時間: 91 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I446.md の「## 必ず確かめる項目」（9 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V3 | 2 | 実験必須 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V9 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 82 秒 | 1 | 0 | $0.2629 | ― | ― | ― |
| 2 | 報告あり | 58 秒 | 1 | 0 | $0.2628 | ― | ― | ― |
| 3 | 報告あり | 18 秒 | 0 | 0 | $0.1321 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
docker compose exec -T backend bash -c 'ulimit -v 2097152; timeout 60 python -m pytest -p no:cacheprovider -q core/tests/test_I446_cross_api_tenant_isolation.py -k "problems or quiz or noorg or scope_removed"'
~~~
出力の先頭:
~~~
is_error=false
......................x.......                                           [100%]
=============================== warnings summary ===============================
core/tests/test_I446_cross_api_tenant_isolation.py::test_id_check[GET api/problems/ subject]
  /app/core/storage_service.py:2: DeprecationWarning: 'imghdr' is deprecated and slated for removal in Python 3.13
    import imghdr

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
29 passed, 103 deselected, 1 xfailed, 1 warning in 6.25s
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 docker compose exec -T backend pytest problems/tests/test_I166_quiz_tenant_isolation.py core/tests/test_I446_cross_api_tenant_isolation.py -q -p no:cacheprovider -k "I166 or quiz or scope_removed or own_check" 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
...........................                                              [100%]
=============================== warnings summary ===============================
problems/tests/test_I166_quiz_tenant_isolation.py::test_start_with_other_org_subject_is_rejected_like_missing
  /app/core/storage_service.py:2: DeprecationWarning: 'imghdr' is deprecated and slated for removal in Python 3.13
    import imghdr

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
27 passed, 120 deselected, 1 warning in 9.54s
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I446] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | ― | 反証失敗（新規指摘なし） | ― | P1-E1: 29 passed・1 xfailed。TC-07 の 4 件を含み、問題・クイズ・組織が空の組織管理者の確かめが今回の HEAD で通った |

探索した仮説:
- **問題の作成・付け替え・AI 生成**: 他組織・全体共有の科目が、存在しない科目と同じ応答になるかを調べた。P1-E1 の `problems` の確かめは通った。
- **クイズの回**: 他組織の科目の回や、科目なしの回の中の他組織の問題への回答が、応答に出ないかを調べた。`quiz` の確かめは通った。
- **組織が空の組織管理者**: 全体共有の問題を一覧・詳細で見られないかを調べた。`noorg` の確かめは通った。
- **TC-07 の差し替え**: `mock.patch` で `get_queryset` を差し替える方式を読んだ。`self` が束縛されるので差し替えは効く。`pytest.raises(AssertionError)` が広い点は既知 F7 と同旨で、Low として扱った。
- **本番コードの変更**: 今回の差分にはテストと文書しかなく、`frontend/src` も変わっていない。V8 は前回の読解を引き継ぐ。
- **未実測の点**: 修正前の FAIL（TC-20）は、作業ツリーに書けない制約のため実測できていない。判定には使っていない。

> ITEM: V1 RESULT=experiment EXP=P1-E1
> ITEM: V2 RESULT=experiment EXP=P1-E1
> ITEM: V8 RESULT=read
> ITEM: V9 RESULT=experiment EXP=P1-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I446] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- TC-07 の `mock.patch` による `get_queryset` の差し替えが空振りして、false-green になる可能性。
  - `mock.patch` でクラス属性を関数に置き換えるので、`self` は束縛され、差し替えは有効になる。
  - 空振りなら `pytest.raises` は「DID NOT RAISE」で赤になる。作者は確かめ方を空にして、4 件とも赤になることを実測している。
- `deny-all-goal` が、正の対照（自組織の記録が読めること）以外の理由で落ちている可能性。
  - `own_status=200` の期待が崩れて落ちるのは意図どおり。
  - `pytest.raises(AssertionError)` が落ちた理由を区別しない点は、既知 findings の F7 と同一なので再報告しない。
- TC-07 が実装の再確認（tautology）になっている可能性。
  - 検査の対象は本番コードではなく、表の確かめ方。
  - 期待値は「存在しない番号と同じ応答」「伏せた本文が同じ」という、実装とは独立したもの。
  - 差し替えの手写しが本番とずれる点は、既知 findings の F9 に含まれる。
- V3: 今回の差分は本番コードを変えない。P2-E1 で、I166 のクイズ関連のテストと、新しいテストのうち `quiz`・`own_check`・`scope_removed` に当たる分が、合わせて 27 件すべて通った。自組織の回の出題・回答・終了は変わっていない。
- V4: `ProblemSerializer(...)` の呼び出しはすべて出力用で、`ProblemAdminSerializer` は継承の定義のみ。request の無い文脈で書き込みに使う箇所は無い。本番コードは今回の差分で未変更。

> ITEM: V3 RESULT=experiment EXP=P2-E1
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I446] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗(新規指摘なし)。探索した仮説:
- **V5(表と経路の突き合わせ)**:
  - `test_route_table_matches_urlconf`(521-531 行)は、次の 5 つで落ちる。
    - 経路が表に無い(`routes - table`)。
    - 実在しない行が表にある(`table - routes`)。
    - `ROUTE_TABLE` と `OUT_OF_SCOPE` の両方に載っている。
    - `OUT_OF_SCOPE` の理由が空。
    - 確かめ方の並びが空。
  - 新しい経路と古い行の両方向を見ているので、読んだ範囲に漏れは無い。FG1 の実測はしていない。
- **V6(絞り込みを外す失敗注入)**:
  - 差分の TC-07 は、`get_queryset` を差し替えて確かめ方が `AssertionError` を出すことを CI で毎回確かめる。
  - 注入は 4 種類(組織の絞り込みを外す 2、本人の絞り込みを外す 1、何でも断る 1)。
  - 何でも断る実装は、`own_status=200` の正の対照(588 行)で落ちる。
  - 空を返すだけ・すべて 404 を返すだけの実装は、`ListCheck` に正の対照が無い。ただ、`OwnCheck`・I166・I431 のテストと組み合わさる設計である。
  - 代表経路だけなので網羅は限定的だが、既知 findings の F7・F9 と実質同一なので新規には数えない。
  - 実測はしていない。差分内の記録(TC-07 を空にすると 4 件とも DID NOT RAISE)に依拠した。
- **V7(対象外の各行の理由)**:
  - 前周の確認に加えて、`api/auth/me/` の PUT・PATCH で組織・役割が書き換えられないことを確かめた。
    - 前周が読んだ `UserSerializer.read_only_fields`(accounts/serializers.py:187-203)を根拠に、読んで確かめた。
    - 今回は同ファイルを再読していない。
  - 他の対象外の行の理由は、ビューのコードと 1 行ずつ突き合わせていない。
  - 脅威モデル上、Critical/High になりうる穴は見つからなかった。
- **エッジケース(組織が空の組織管理者)**: TC-06 が一覧 `[]` と詳細 404 の同一応答を固定しており、抜けは無い。

> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 13116063ad4bfc68dad9cdaf9dea345df790ce3c
ROUNDS: 1
VERDICT: OK
