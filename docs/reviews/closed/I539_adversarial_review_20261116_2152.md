# 敵対的レビュー [I539]（別プロセス・2026-11-16 21:52）

- 見た範囲: origin/develop...280b0d8ab659465cceb3c4e9131bda59cf3455df
- 所要時間: 24 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（13 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I539.md の「## 必ず確かめる項目」（8 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 19 秒 | 0 | 0 | $0.2422 | ― | ― | ― |
| 2 | 報告あり | 19 秒 | 0 | 0 | $0.2689 | ― | ― | ― |
| 3 | 報告あり | 20 秒 | 0 | 0 | $0.2615 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I539] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし） | - | 静的読解のみ。実験は流していない |

反証失敗（新規指摘なし）。探索した仮説は次の 3 本です。

1. **本文の `organization_id` で他の組織に入れる。**
   - `organization_id` のフィールドは `UserRegistrationSerializer` から消えています。そのため、本文に入れても無視されます。
   - 登録先はビューが `context` で渡し、`create()` はその `context` だけを使います。
   - TC-06 は `school.id` を実際に本文へ入れて送ります。その後、`user.organization_id != school.id` と `school.users.count()` が増えないことを確かめています。
2. **`invitable()` の抜け道。**
   - `exclude(type=personal, slug=personal)` は SQL では `NOT (type AND slug)` になります。そのため、共有の `personal` 組織だけが外れます。
   - 種類が既定の `personal` の招待用の組織は外れません（TC-07b）。
   - 本人ひとりの組織は `is_individual=False` の条件で外れます。
   - 登録・slug の確認・公開の科目一覧の 3 つの入口が、すべて `invitable()` を通ります。
   - TC-07 は、共有の `personal` と新しく作った個人用の組織の両方で、400・404・`[]` を確かめています。また、登録の前後で利用者数が増えないことも見ています。
3. **マイグレーションの冪等性と運営用のアカウント。**
   - 0023 は `is_staff=False, is_superuser=False` の利用者だけを対象にします。
   - 対象は共有の組織にいる人だけです。1 回目で移された人は共有の組織を離れるので、2 回目の対象にはなりません。
   - TC-14〜16 は、本物のマイグレーションのモジュールの関数を `importlib` で読み込んで呼んでいます。写しではありません。
   - TC-23 は、`context` が無い場合と両方ある場合に `ImproperlyConfigured` になることを確かめています。
   - ビューの広い `except` は 400 を返すだけです。黙って個人用の組織を作る経路はありません。
   - 失敗時は、`create()` の `@transaction.atomic` とビューの `atomic` が組織の作成を巻き戻します。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V5 RESULT=read
> ITEM: V8 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I539] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green | TC-04（重複のユーザー ID）は、`validate_user_id` が `create()` より前に弾く。個人用の組織の作成が検証の後に回るので、組織が増えないのは当然の結果になる。「組織を作った後で失敗しても巻き戻る」という `transaction.atomic` の効きは確かめていない。ただしこの案件の失敗条件（検証が失敗したら組織が増えない）には届いている。TC-03 も同じで、`subject_ids` の検証は `create()` の前に失敗する。 | test_I539_personal_org_signup.py の `test_failed_registration_leaves_no_org` | 静的読解。3 つの検証経路とも、前後の `Organization.objects.count()` を比べている。 |
| Low | tautology | TC-33 の Enter 押下の部分は、送信の処理の中のガードを実際には通らない可能性がある。ボタンが無効のとき、jsdom は暗黙の送信を起こさない（仕様どおり）。そのためこの部分は、ガードを外しても落ちないおそれがある。ボタンが無効なことは `toBeDisabled` で確かめている。`register` が呼ばれないことも、ボタンが無効という経路で確かめている。 | Register.test.tsx:148-151 | 静的読解。実験は未実施。 |

- 探索した仮説は 4 つある。
  - TC-03・TC-04 が組織の数の前後を比べているか。比べている。
  - TC-33 が失敗の応答を作っているか。`mockRejectedValueOnce` で作っている。
  - ボタンが無効で `register` が呼ばれないことを見ているか。見ている。
  - 失敗の後に再読み込みして復帰できることまで確かめているか。確かめている。
- 以上から、V4・V7 の失敗条件は実質的に守られている。Critical・High に当たる false-green は見つからなかった。

> ITEM: V4 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I539] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説は次のとおり。

- **個人用の組織の管理者による他組織の科目・問題の参照**
  - 科目は `get_user_subjects` で組織ごとに絞られる。
  - 問題は `ProblemViewSet.get_queryset` と、`organization_id != request.user.organization_id` を弾く各所の判定で絞られる。
  - 新しい経路は増えていない。
  - 個人用の組織が使う `IsOrgAdmin` は `role='admin'` だけを見る。ほかの組織の管理者と同じ境界に載るので、横断は増えない。
  - TC-13 は科目・利用可能科目・問題の一覧・問題の番号指定を見ている。
- **slug の重複による引き当ての取り違え**
  - slug は一意でない。
  - 個人用の slug は `pick_unused_slug` で既存と重ならない。
  - 後から同じ slug の招待用の組織ができても、`invitable()` が `is_individual=False` で絞るので個人用の組織は引かれない。
- **学ぶ科目の自動追加の範囲（V6）**
  - 追加は `subject.organization.is_individual` のときだけ。
  - 学校の組織と、種類が既定の `personal` の招待用の組織は `is_individual=False` のままなので追加されない。
  - TC-12 が学校の組織と種類が既定の招待用の組織の両方を確かめている。
  - 共有の `personal` 組織は `is_individual=False` なので入らない。
- **`public` の `register` 変換と slug 未指定**
  - どちらも共有の `personal` 組織に寄せられ、`invitable()` が除外するので常に `[]` になる。
  - 招待の入口が抜ける経路は見つからなかった。

読解だけで確かめたので、実験は不要と判断した。

> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 280b0d8ab659465cceb3c4e9131bda59cf3455df
ROUNDS: 1
VERDICT: OK
