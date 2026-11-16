# I539 計画書: 招待なしの会員登録を完了できるようにする（利用者ごとの個人用の組織）

## 基本情報
- **計画書ID**: plan_I539
- **関連イシュー**: #539
- **Draft PR**: #544
- **作成根拠資料**: docs/issues/open/I539.md（GitHub #539 の本文の写し・設計確認メモあり）
- **実装後評価**: docs/reviews/open/I539_review.md
- **作成日**: 2026-11-16

## 1. 背景/目的
- ログイン画面の「アカウントをお持ちでない方はこちら」（`/register`・組織の指定なし）から登録すると、2 段目の科目選びで「この組織には利用可能な科目がありません」と出て「登録を完了」が押せず、登録を終えられない（2026-11-16 の通し確認）。
- 目的: 招待リンクを持たない人でも登録を最後まで終え、自分の科目・問題を作ってクイズを始められるようにする。あわせて、科目 0 件の組織への招待登録でも行き止まりにならないようにする。

### 調査結果
- **原因の概要**: 組織を指定しない登録は、全員が 1 つの共有の「個人利用」組織（slug `personal`）に入る。その組織には科目が 0 件で、科目を作れるのは組織の管理者だけなのに、登録では科目を 1 つ以上選ぶことが必須になっている。だから必ず止まる。
- **詳細**:
  1. `frontend/src/pages/Register.tsx:173` が `/api/organizations/subjects/public/?slug=personal` を読み、空の配列が返る
  2. `Register.tsx:497-500` が「この組織には利用可能な科目がありません」を出し、`:757` が `selectedSubjects.length === 0` でボタンを無効にする
  3. 裏側も `backend/accounts/serializers.py:32-41`（`subject_ids` の `required=True`・`min_length=1`）で科目なしの登録を断る
  4. 組織の決め方は `backend/accounts/views.py:132-165`（`_get_organization`）。slug なしは `type='personal'` の先頭の組織（共有）を返す
- **根本原因**: 個人の利用者が学ぶ中身（科目・問題）を用意する決まりが無いまま、組織なしの登録の入口だけがあった（イシューの「根本原因」）。
- **ほかに見つけたこと（計画で手当てする）**:
  - `Organization.slug` は一意でない（`backend/accounts/models.py:38-43`・`unique=False`）。組織の引き当ては `filter(slug=…).first()`（`views.py:139`・`:219`・`problems/views.py:77`）。個人用の組織の slug は推測されず重ならないものにする
  - 科目の画像の置き場所は `org/<組織の slug>/subjects/…`（`problems/views.py:127-136`）。slug が重なると置き場所も重なるので、個人用の組織の slug は既存と重ならないことを作るときに確かめる
  - 科目を作っても作った人の学ぶ科目（`UserSubjectAccess`）には入らず（`problems/views.py:101-138`）、クイズに出るのは学ぶ科目だけ（`problems/permissions.py:13`・`core/subject_service.py:116-162`）
  - 利用者の記録（クイズの回・学習記録）の組織の境界は、記録が指す科目の組織で絞る（`problems/querysets.py:30-`）。共有の `personal` 組織は科目 0 件なので、利用者を別の組織に移しても、移る前の組織の科目を指す記録は存在しない
  - 組織の管理者（`role='admin'`）に増えるのは問題管理・科目管理（`frontend/src/components/Layout.tsx:77-80`）と、その API（`IsOrgAdmin`・`problems/views.py:32-41`・`:165`）。AI での問題作成（`problems/views.py:370` `generate_ai`）も含む
  - pytest は `--no-migrations`（`backend/pytest.ini`）。テストの DB には共有の `personal` 組織も「個人利用」のカテゴリ（マイグレーション 0017）も無い
  - **組織の種類（`type`）は既定が `'personal'`**（`accounts/models.py:44-49` `default='personal'`）。種類を指定せずに作られた招待用の組織も `type='personal'` になる。実例: 開発の DB の `e2e-org-a`・`e2e-org-b`（`seed_e2e.py:59-61`・`:85-87` が `type` を渡さない・カテゴリは「教育」）が `type='personal'`（2026-11-16 に `Organization.objects.all()` で確認）。テストでも `test_I115` の組織は `type` を渡さない。だから `type='personal'` は「本人ひとりの組織」の印に使えない（design-security-review で判明・計画変更記録）
  - E2E の CI はログイン・登録の回数制限を切っている（`.github/workflows/e2e.yml:32` `RATELIMIT_ENABLE: "false"`）。ログインはメールの確認を求めない（`accounts/serializers.py:124-184`）
- **環境前提の確認**: `docker compose exec -T backend python manage.py shell -c …` が動くことを grill-me で確認済み（2026-11-16。共有の `personal` 組織の利用者 0 人・うち `is_staff` 0 人）。追加のツール・依存は無い。

## 2. 受け入れ条件
イシューの受け入れ条件（`docs/issues/open/I539.md`）と同じ。番号は計画の中の参照用。
- [ ] AC1: ログイン画面の新規登録の入口から、招待リンクなしで登録した人が、科目選びで止まらずに登録を終えられ、ログインできる
- [ ] AC2: その人には専用の組織（名前「（ユーザーID）さんの学習」）が作られ、その人が管理者になっている。別の人が同じ入口で登録すると、別の組織になる
- [ ] AC3: その人がログインすると、ダッシュボードに「まず科目と問題を作りましょう」の案内と科目管理の画面へのボタンが出る
- [ ] AC4: 個人用の組織で科目を作ると、作った人の学ぶ科目に自動で入り、設定画面で選び直さずに、その科目の問題でクイズを始められる
- [ ] AC5: 個人用でない組織で管理者が科目を作っても、作った人の学ぶ科目は増えない
- [ ] AC6: 個人用の組織（登録で作った本人ひとりの組織〔`is_individual=True`〕と、共有の `personal` 組織〔`type='personal'`・slug `personal`〕）の slug を使った招待リンクの登録（`/register/<slug>`）は受け付けられず、その組織の利用者は増えない。未ログインの科目一覧（`/api/organizations/subjects/public/?slug=<その slug>`）は空の配列を返す（種類が既定の `personal` のままの招待用の組織〔例 `e2e-org-a`〕の招待は今のまま使える）
- [ ] AC7: 招待リンクで科目 0 件の組織に登録しようとしても、押せないボタンのまま止まらず登録を終えられ、ログイン後に「管理者が科目を用意するまでお待ちください」と出る
- [ ] AC8: 既に共有の `personal` 組織（slug `personal`）にいた一般の利用者（`is_staff=False`）は、一人ずつ専用の組織（名前「（ユーザーID）さんの学習」）に移って管理者になり、そのままログインして科目・問題を作れる。移した後、共有の `personal` 組織の一般の利用者は 0 人
- [ ] AC9: 共有の `personal` 組織にいる運営用のアカウント（`is_staff=True`）は移らず、組織も `role` も変わらない
- [ ] AC10: 移す操作は、何度流しても同じ結果になる（2 回目は何も変えない）
- [ ] AC11: 専用の組織の人から、ほかの利用者の科目・問題・記録が見えない
- [ ] AC12: 上の流れ（組織なしの登録→ログイン→科目・問題を作る→クイズを始める）が E2E で確かめられている
- [ ] AC13: 学ぶ科目はあるが、クイズの対象の科目（選んだ科目、「すべて」なら学ぶ科目の全部）に問題が 1 問も無いとき、ダッシュボードの「クイズを始める」は押せず（押してエラーの通知で戻されることが無い）、管理者には「問題を作りましょう」の案内と「問題を作る」のボタン、管理者でない人には「管理者が問題を用意するまでお待ちください」の案内が出る。「すべて」で問題のある科目と無い科目が混ざるときは、問題のある科目だけから始める（マージ前のユーザーの BP・UI/UX の確認で追加）

## 3. 影響範囲
| 区分 | 対象 |
|---|---|
| Backend | accounts（登録・組織の引き当て・個人用の組織の作成・データマイグレーション）／problems（未認証の科目一覧・科目の作成・学ぶ科目の応答に問題数〔`UserSubjectSerializer`〕）／api（`/api/user/subjects/` の GET・PUT が問題数を数える）／`backend/openapi.yaml`（作り直し） |
| Frontend | 会員登録の画面・ダッシュボードの「学習を開始」のカード・登録画面の科目の取得（React Query のフックを新設）・学ぶ科目の型（`UserSubject`・`frontend/src/types/api/schema.d.ts` の作り直し） |
| DB | `organizations` に列 `is_individual`（真偽・既定 False・DB の既定も False）を 1 つ足すスキーマのマイグレーション（0022・足すだけ）と、データマイグレーション 1 本（0023・共有の `personal` 組織の一般の利用者を専用の組織へ移す・Danger Ops） |
| E2E | `e2e/tests/auth.spec.ts` に登録の流れを 1 本追加（未認証のプロジェクトで動く） |
| Config/Infra | なし（依存ファイル・Dockerfile・docker-compose.yml の変更なし） |
| 参照のみ | `docs/runbooks/ux-rules.md`・`rules/react-coding-standards-integrated.md`・`rules/ultimate_django_coding_standards.md` |

## 4. 変更点一覧（具体）

### 修正アプローチ
組織を指定しない登録では、共有の組織を探すのをやめ、登録と同じトランザクションの中でその人だけの組織（`type='personal'`・`is_individual=True`）を作り、その人を管理者にする。「本人ひとりの組織」は種類（既定が `personal` で招待用の組織にも付いている）ではなく、新しい列 `is_individual` で見分ける。招待リンクで引き当てる組織からは本人ひとりの組織と共有の `personal` 組織を外し、他人が入れない・科目名も見えないようにする。科目が 0 件の組織では、登録の科目選びを飛ばす（裏側は 0 件のときだけ科目なしを認める）。個人用の組織で科目を作ったら作った人の学ぶ科目に入れ、ダッシュボードは科目 0 件のとき管理者かどうかで案内を分ける。共有の `personal` 組織に残る一般の利用者は、データマイグレーションで一人ずつ専用の組織へ移す。

### 4-1. `backend/accounts/models.py`
- **方針**: 「招待リンクで引き当ててよい組織」を 1 か所で決める（3 つの入口が同じ条件を使う）。種類・カテゴリの文字列を定数にする。
- `Organization` に定数 `TYPE_PERSONAL = 'personal'`・`SHARED_PERSONAL_SLUG = 'personal'` を足し、`TYPE_CHOICES` の `'personal'` を定数で書く。
- `Organization` に列 `is_individual = models.BooleanField(default=False, db_default=False, verbose_name='本人ひとりの組織', help_text='会員登録で作った、その利用者だけの組織（招待で入れない）')` を足す。`db_default` も付ける（コードを戻した後に古いコードが列を知らずに行を足しても、DB が False を入れて失敗しない・7）。マイグレーション `0022_organization_is_individual.py` は `makemigrations` で作る（`AddField` だけ・既存の行は False）
- `OrganizationQuerySet(models.QuerySet)` を新設し、`invitable()` = `self.filter(is_active=True, is_individual=False).exclude(type=Organization.TYPE_PERSONAL, slug=Organization.SHARED_PERSONAL_SLUG)` を持たせる（本人ひとりの組織と共有の `personal` 組織を外す。種類が既定の `personal` のままの招待用の組織は外さない）。`Organization.objects = OrganizationQuerySet.as_manager()`（`use_in_migrations` は付けないので、マネージャーの差分は出ない。0022 の後に `makemigrations --check` が差分なし・TC-21）。
- `OrganizationCategory` に定数 `PERSONAL_SLUG = 'personal'`（マイグレーション 0017 が作るカテゴリの slug）。

### 4-2. `backend/accounts/services.py`（新規）
- **方針**: 個人用の組織の作り方（名前・slug・カテゴリ）を 1 か所に置く。ビューを太らせない。
- `PERSONAL_ORG_SLUG_PREFIX = 'p-'`
- `personal_org_name(user_id: str) -> str`: `f'{user_id}さんの学習'`（`user_id` は 3〜30 文字なので `name` の 100 文字に収まる）
- `pick_unused_slug(candidates: Iterable[str]) -> str`: 候補を順に見て、`Organization.objects.filter(slug=…).exists()` が偽の最初のものを返す（重なりを避ける処理だけを分け、テストが候補の一覧を渡して直接確かめられるようにする・乱数を差し替えない）
- `new_personal_org_slug() -> str`: `pick_unused_slug('p-' + secrets.token_hex(6) for _ in itertools.count())`（14 文字・推測されない）
- `create_personal_organization(*, user_id: str, category: OrganizationCategory) -> Organization`: `Organization.objects.create(name=personal_org_name(user_id), slug=new_personal_org_slug(), type=Organization.TYPE_PERSONAL, is_individual=True, category=category, is_active=True)`
- `get_personal_category() -> OrganizationCategory | None`: `OrganizationCategory.objects.filter(slug=OrganizationCategory.PERSONAL_SLUG).first()`

### 4-3. `backend/accounts/serializers.py`（`UserRegistrationSerializer`）
- **方針**: 組織は利用者の入力から受け取らない（ビューが決めて `context` で渡す）。科目必須は「組織に科目があるときだけ」にする。
- `organization_id` のフィールドと `validate_organization_id` を消す（本文に `organization_id` を入れられても使われない）。`Meta.fields` からも外す。
- `subject_ids`: `required=False`・`default=list`・`min_length` を外す（`child=IntegerField()` は残す）。
- `validate(attrs)`:
  - パスワードの一致（今のまま）
  - 登録の種類は `context` で明示する: `context['organization']`（招待先）と `context['personal_category']`（個人用の組織を作る登録）の**ちょうど片方**があること。両方・どちらも無いときは `ImproperlyConfigured` を投げる（`context` の渡し忘れで黙って個人用の登録にならないように・fail-closed）
  - `organization = self.context.get('organization')`（招待。`None` なら個人用の組織を作る登録）
  - 個人用（`organization is None`）: `subject_ids` が空でなければ `{'subject_ids': '選択された科目の一部が無効です'}`（他組織の番号と存在しない番号を同じ応答にする・I446）
  - 招待: 組織の科目が 1 件以上で `subject_ids` が空なら `{'subject_ids': '科目を最低1つ選択してください'}`。`subject_ids` のうち組織の科目でないものがあれば `{'subject_ids': '選択された科目の一部が無効です'}`（今のまま。組織の科目が 0 件なら、空でない `subject_ids` はここで断られる）
- `create(validated_data)`（`@transaction.atomic` のまま）:
  - 個人用: `organization = create_personal_organization(user_id=validated_data['user_id'], category=self.context['personal_category'])`・`role='admin'`
  - 招待: `organization = self.context['organization']`・`role='user'`（今のまま）
  - `User.objects.create_user(**validated_data, organization=organization, role=role)`（組織を後から保存し直す 2 回目の save をやめる）
  - `UserSubjectAccess` の作成（`subject_ids` が空なら作らない）・`UserSettings`・`StudyStreak` は今のまま

### 4-4. `backend/accounts/views.py`
- **方針**: ビューは「どの組織に入れるか」だけを決め、作成はシリアライザ（とサービス）に任せる。
- `UserRegistrationView.create`:
  - slug あり: `organization = Organization.objects.invitable().filter(slug=slug).first()`。無ければ今の 400（`{'error': {'main_message': '組織の設定に失敗しました', 'sub_message': '無効な組織URLまたはシステムエラー'}}`）。`logger.info(f"Registration attempt for organization_id: {organization.id}")` は今のまま（`test_I437` が見る）
  - slug なし: `category = get_personal_category()`。無ければ `logger.error("Personal organization category (slug='personal') not found. Environment is misconfigured; slug-less registration rejected.")` を出して同じ 400（組織も利用者も作らない・I140 の考え方を引き継ぐ）
  - `mutable_data['organization_id'] = …` をやめ、招待なら `{'organization': organization}`、個人用なら `{'personal_category': category}` だけを `get_serializer_context()` に足して `UserRegistrationSerializer` に渡す（`request` などの既定の `context` は保つ）
  - 201 の本文は今のまま（`{'message': '登録完了。メール認証を行ってください。', 'user_id': str(user.id), 'organization': user.organization.name}`）
  - `_get_organization` は「slug から招待先を引く」だけにし、`type='personal'` の共有組織を探す分岐を消す
- `OrganizationSlugValidationView.get`: `Organization.objects.invitable().filter(slug=slug).first()`。個人用の組織の slug は今の「見つからない」と同じ 404（`{'valid': False, 'message': '組織 "<slug>" は見つかりません'}`）

### 4-5. `backend/problems/views.py`（`SubjectViewSet`）
- `public`: `Organization.objects.invitable().filter(slug=organization_slug).first()`。本人ひとりの組織・共有の `personal` 組織は「無い」と同じ 200 `[]`。`'register'`→`'personal'` の言い換えはそのまま（結果は `[]`）
- `perform_create`: `transaction.atomic()` の中で、科目を作った後、`subject.organization.is_individual` が真なら `UserSubjectAccess.objects.get_or_create(user=self.request.user, subject=subject, defaults={'granted_by': self.request.user})`（`post_save` のシグナルが学ぶ科目のキャッシュを消す・`problems/signals.py:35`）。それ以外の組織では作らない（今のまま）

### 4-6. `backend/accounts/migrations/0022_organization_is_individual.py`（新規・スキーマ）と `0023_move_shared_personal_users.py`（新規・データマイグレーション）
- 0022: `makemigrations accounts` が作る `AddField('organization', 'is_individual', BooleanField(default=False, db_default=False, …))` だけ（手で書き足さない）
- **方針**: 共有の `personal` 組織に残る一般の利用者を、一人ずつ専用の組織に移す。何度流しても同じ結果。過去のモデル（`apps.get_model`）だけを使い、アプリのコード（`accounts.services`）は読み込まない（後でコードが変わってもマイグレーションの意味が変わらないように）。名前・slug の作り方は 4-2 と同じ規則をこのファイルに書く。
- 0023: `dependencies = [('accounts', '0022_organization_is_individual')]`
- `move_shared_personal_users(apps, schema_editor)`:
  - `shared = Organization.objects.filter(type='personal', slug='personal')`
  - `targets = User.objects.filter(organization__in=shared, is_staff=False, is_superuser=False)`（運営用のアカウントは移さない・`role` も変えない）
  - 対象が 0 人なら何もしない
  - 「個人利用」カテゴリ（slug `personal`）が無いのに対象がいれば `RuntimeError`（黙って飛ばさない。0017 が作るので普通は起きない）
  - 対象ごとに `transaction.atomic()` の中で組織を作り（`type='personal'`・`is_individual=True`・名前「（ユーザーID）さんの学習」・`user_id` が空なら `email` の @ より前・それも無ければ `str(user.pk)[:8]`）、`user.organization` と `role='admin'` を `save(update_fields=['organization', 'role'])` で保存
- `reverse_code=migrations.RunPython.noop`（戻すときは利用者を動かさない・理由は 7）

### 4-7. フロントエンド
- `frontend/src/hooks/usePublicSubjects.ts`（新規）: 招待先の組織の科目（未ログイン）を React Query で読む。`publicSubjectsKey = (slug) => ['public-subjects', slug]`・`queryFn: () => SubjectService.getSubjects(slug)`・`enabled`（招待の slug があり、組織の確認が済んでいるときだけ）。`toLoadState` で 3 つの状態を返す（`useAvailableSubjects` と同じ形・規約 6.3）
- `frontend/src/pages/Register.tsx`:
  - 科目の取得を `useEffect` からフックに移す（`subjects` の state・取得の effect・デバッグの `console.log` を消す）。招待の組織の確認が済んだらすぐ読む（1 段目の時点で科目の有無が分かる）
  - `needsSubjectStep = !!organizationSlug && 科目が 1 件以上`
  - `needsSubjectStep` が偽: 段の表示（Stepper）を出さず、1 段目のボタンを「登録する」にし、押すと科目なしで登録する（`subjectIds: []`）
  - `needsSubjectStep` が真: 今のまま（「登録して次へ」→ 2 段目で選ぶ → 「登録を完了」）
  - 招待の科目を読み込み中: 1 段目のボタンを無効にして丸い読み込み表示。読めなかった: ボタンの上に「科目を読み込めませんでした」と「再読み込み」（`SubjectsRetryRow`）を出し、ボタンは無効（0 件と取り違えて科目なしで送らない）。ボタンが無効でも入力欄の Enter で送信が起きるので、1 段目の送信の処理の最初でも、科目を読めていなければ何もしない
  - 送信を 1 か所（`submitRegistration(info, subjectIds)`）にまとめ、1 段目・2 段目の両方から呼ぶ
- `frontend/src/components/dashboard/StartQuizCard.tsx`:
  - 新しい prop `isOrgAdmin: boolean`
  - `NoSubjectsGuide` の「組織の科目も 0 件」の分岐を分ける:
    - 管理者: `Alert`（info・`role="status"`）「まず科目と問題を作りましょう。科目管理で科目を作り、問題管理でその科目の問題を作ると、クイズを始められます」＋ボタン「科目を作る」（`/subject-management`・`variant="contained"`・`component={RouterLink}`）。次にやることを 1 つの目立つボタンにする（科目が無いうちは問題を作れないので「問題を作る」は出さない・計画変更記録）
    - 管理者でない: `Alert`（info・`role="status"`）「科目がまだ用意されていません。管理者が科目を用意するまでお待ちください」
  - 組織に科目があり選んだ科目が 0 件のとき（「学ぶ科目を選ぶ」）・取得の失敗は今のまま
  - 問題のある科目だけをクイズの対象にする（AC13）: `startable = 学ぶ科目のうち problem_count > 0`。対象は、科目を選んでいればその科目（問題が無ければ対象なし）、「すべて」なら `startable`。「すべて」で 1 件ならすぐ始め、2 件以上ならダイアログに `startable` だけを出す
  - 学ぶ科目はあるが対象が無いときの案内 `NoProblemsGuide`（`role="status"`）。「クイズを始める」は無効:
    - 管理者: 「問題を作りましょう。問題管理でこの科目の問題を作ると、クイズを始められます」（「すべて」のときは「問題を作りましょう。問題管理で学ぶ科目の問題を作ると、クイズを始められます」）＋ボタン「問題を作る」（`/quiz-management`・`variant="contained"`・`component={RouterLink}`）
    - 管理者でない: 「この科目にはまだ問題がありません。管理者が問題を用意するまでお待ちください」（「すべて」のときは「学ぶ科目にまだ問題がありません。管理者が問題を用意するまでお待ちください」）
- `frontend/src/services/subjectService.ts`・`frontend/src/hooks/useUserSubjects.ts`: 学ぶ科目の型を、OpenAPI から作った `UserSubject`（`problem_count` が必須）にする（`getUserSubjects` は `getAvailableSubjects` と同じく応答をそのまま返す。I493 の型の決まり）
- `frontend/src/constants/routes.ts`: `SUBJECT_MANAGEMENT_PATH = '/subject-management'`・`QUIZ_MANAGEMENT_PATH = '/quiz-management'` を足す（カードから使う）
- `frontend/src/pages/Dashboard.tsx`: `isOrgAdmin={user?.role === 'admin'}` を `StartQuizCard` に渡す
- `frontend/src/pages/SubjectManagement.tsx`: 変更しない（イシューの「変更が要るかは計画で確認」→ 不要。科目を作ると裏側で学ぶ科目に入り、ダッシュボードは開くたびに取り直す〔React Query の既定 `staleTime: 0`・`App.tsx:37-44`〕）

### 4-7b. 学ぶ科目の API に問題数を足す（AC13）
- `backend/problems/serializers.py` の `UserSubjectSerializer`: `problem_count = serializers.IntegerField(read_only=True)` を足し、`fields = ['id', 'name', 'problem_count']`
- `backend/api/views/user_subjects.py` の `UserSubjectsView`: GET・PUT の両方で `subject_service.get_user_selected_subjects(..., annotate_count=True)`（キャッシュは科目の番号だけなので、数は毎回 DB で数える・古い数は出ない。クエリは件数の `COUNT` の 1 本のまま）
- `backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts`: `docs/runbooks/common-commands.md`「API の形を変えたとき」の手順で作り直す（手で直さない）
- 組織の境界は今のまま（`get_user_selected_subjects` が今の組織の科目に絞る・数は自組織の科目の問題だけ）

### 4-8. テスト
- 新規 `backend/accounts/tests/test_I539_personal_org_signup.py`（TC-01〜TC-16）
- 直す `backend/accounts/tests/test_I140_personal_org_fallback.py`（共有の組織が無いときの 400 → 「個人利用」カテゴリが無いときの 400 に読み替える・TC-17）
- 直す `backend/accounts/tests/test_I131_org_id_rename.py` の TC-AUTO-06（slug なしは共有の組織ではなく専用の組織に入る・TC-18）
- `backend/problems/tests/test_I115_public_unauth.py` は変えない（TC-AUTO-05 の `[]` はそのまま通る・TC-19 で確かめる）
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py`・`backend/core/tests/test_I437_no_pii_in_logs.py` は変えない（TC-20）
- 新規 `frontend/src/pages/__tests__/Register.test.tsx`（TC-30〜TC-33）
- 直す `frontend/src/pages/__tests__/Dashboard.test.tsx`（`useAuth` の利用者を差し替えられる形にし、TC-05 の文言を変え、TC-43・TC-44 を足す）
- 追加 `e2e/tests/auth.spec.ts`（TC-50。科目を作った後・問題を作る前にダッシュボードの「問題を作る」の案内を確かめる段を足す・AC13）
- 新規 `backend/problems/tests/test_I539_user_subjects_problem_count.py`（TC-24）。`backend/problems/tests/test_I494_user_subjects.py` は応答の欄が増えるだけなので、欄を完全一致で見ている箇所があれば読み替える
- `Dashboard.test.tsx` に TC-45〜TC-47 を足し、学ぶ科目の差し替えの値に `problem_count` を入れる（無いと「始められない」側に倒れるため）

## 5. 実装手順（ステップ）
1. **裏側の登録を縦に通す**（4-1〜4-4・TC-01〜TC-10・TC-17・TC-18・TC-20〜TC-22）: 定数と `invitable()`、サービス、シリアライザ、ビュー。テストを先に書いて落ちることを見てから直す（TDD）。→ TC-01〜TC-10・TC-17・TC-18・TC-20〜TC-22 参照
2. **科目の作成と未ログインの科目一覧**（4-5・TC-11〜TC-13・TC-19）: ステップ 1 の後（`invitable()` を使う）。→ TC-11〜TC-13・TC-19 参照
3. **データマイグレーション**（4-6・TC-14〜TC-16）: ステップ 1 と並行してよい（モデルの定数に依らない）。→ TC-14〜TC-16 参照
4. **登録画面**（4-7 の `usePublicSubjects`・`Register.tsx`・TC-30〜TC-33）: ステップ 1 の後（科目なしの登録を裏側が受け付ける必要がある）。→ TC-30〜TC-33 参照
5. **ダッシュボードの案内**（4-7 の `StartQuizCard`・`routes.ts`・`Dashboard.tsx`・TC-05・TC-43・TC-44）: ステップ 4 と並行してよい。→ TC-05・TC-43・TC-44 参照
5b. **問題の無い科目の案内**（4-7b・4-7 の `StartQuizCard` の `startable`・`NoProblemsGuide`・TC-24・TC-45〜TC-47・AC13）: 裏側（serializer・ビュー・openapi の作り直し）→ 型の作り直し → 画面の順。→ TC-24・TC-45〜TC-47 参照
6. **E2E**（TC-50）: ステップ 1〜5b の後。→ TC-50 参照
7. 組み込みの `/simplify` で整理し、計画との一致を確かめる（implement 段階）

- 縦の切り方: 「組織なしの登録」はステップ 1（API）＋ステップ 4（画面）＋ステップ 6（通し）、「科目を作ってクイズ」はステップ 2（API）＋ステップ 5（画面）＋ステップ 6 で縦に通る。画面のテストは API の受け口が先にあると実物と同じ値で書けるので、API を先に置く。未知のリスク（外部サービス・新しいライブラリ）は無い

- サービスの再起動: マイグレーションを足すので、手元の開発環境では backend の再起動（起動時に `migrate` が走る）で 0022・0023 が当たる。開発の DB の 0023 の対象は 0 人（2026-11-16 に確認）なので、何も変わらない。

## 6. テスト計画
### 自動（テストレベルの使い分け）
- **結合（pytest・API を通す）**: 登録・組織の引き当て・科目の作成・テナントの境界は、ビュー・シリアライザ・権限・トランザクションが組み合わさって決まるので、API を通して確かめる（TC-01〜TC-13・TC-17〜TC-20）
- **単体（pytest・関数を直接呼ぶ）**: データマイグレーションの関数（`--no-migrations` のため `migrate` では走らない。モジュールを読み込み、`django.apps.apps` を渡して呼ぶ・TC-14〜TC-16）
- **部品（Jest・React Testing Library）**: 登録画面の段の出し分け・送る値・失敗の表示、ダッシュボードの案内の出し分け（TC-30〜TC-33・TC-05・TC-43・TC-44）
- **E2E（Playwright）**: 実際の画面で、組織なしの登録 → ログイン → 科目・問題を作る → クイズを始める（TC-50・AC12）
- **再発防止**: 「組織なしの登録が科目選びで止まる」不具合は TC-01（裏側）・TC-30（画面）・TC-50（通し）で止める
- **認可・テナント境界**: TC-06（本文の `organization_id` を使わない）・TC-07（個人用の組織への招待を断る）・TC-12（他の組織では学ぶ科目を増やさない）・TC-13（別の個人用の組織の科目が見えない）・TC-20（既存の横断テストが通る）
- pytest・Jest・E2E は CI が PR ごとに流す（手元で全体を流し直さない）。実装中は関係するテストだけを手元で流す
- `makemigrations --check`（スキーマの差分が出ないこと）は CI の backend のジョブが見る（`.github/workflows/ci.yml:38`）。実装中にも 1 回流す（TC-21）
- API の仕様書（`backend/openapi.yaml`）に載っている経路は `/api/dashboard/*`・`/api/settings/`・`/api/user/subjects/*` だけで、今回変える登録・科目の経路は載っていない（2026-11-16 に `grep -n "^  /" backend/openapi.yaml` で確認）。AC13 で `/api/user/subjects/` の応答に `problem_count` を足すので、仕様書と画面の型は手順どおり作り直す（4-7b）。CI の `core/tests/test_I493_openapi_contract.py`（TC-22）と `API Types Up To Date` ジョブが、作り直し忘れを止める
### 手動（`docs/tests/open/I539_manual_test.md`）
- Claude が Playwright MCP で画面を見る（登録画面の段の出し分け・ダッシュボードの案内・個人用の slug の招待の画面）。人の手動テストは無し

## 7. ロールバック
- PR を戻す（revert）。列 `is_individual` は DB に残してよい（`db_default=False` なので、列を知らない古いコードが組織を作っても DB が False を入れる）。列を消す巻き戻し（`migrate accounts 0021`）は Danger Ops なので、戻すときにも行わない。
- データマイグレーション 0023 の `reverse_code` は `noop`。戻した後も、移した利用者は専用の組織の管理者のまま残る。古いコードはどの組織の利用者も普通に扱える（組織の引き当ては招待の slug と、slug なしの登録だけ）ので、動きは壊れない。移した利用者を共有の組織に戻すと、その人が作った科目・問題が組織ごと消える（`Subject.organization` の削除の連鎖）か行き場を失うので、自動では戻さない。
- 戻した後に新しく登録する人は、古いコードどおり共有の `personal` 組織に入る（イシューの不具合が戻る）。
- 作られた個人用の組織は残る。消すのは別のイシュー（Danger Ops）で行う。

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 登録の本文に `organization_id` を入れて、招待なしで他の組織に入る | シリアライザから `organization_id` を消し、組織はビューが決めて `context` で渡す（TC-06） | 回避 |
| R2: 個人用の組織の slug を知った人が招待リンクの形で入る・科目名を見る | 3 つの入口（登録・slug の確認・未ログインの科目一覧）を `Organization.objects.invitable()` 1 か所の条件にそろえる。slug は 12 桁の乱数（TC-07） | 回避 |
| R10: 「本人ひとりの組織」を種類（`type='personal'`）で見分けると、種類が既定のままの招待用の組織（例 `e2e-org-a`）の招待リンクが使えなくなり、その組織で管理者が科目を作るたびに学ぶ科目が増える | 専用の列 `is_individual` で見分ける（登録・0023 で作る組織だけ真）。種類が既定の `personal` の招待用の組織の招待・科目の作成が今のままであることをテストで確かめる（TC-07b・TC-12） | 回避 |
| R11: 登録のシリアライザに `context` を渡し忘れると、黙って個人用の組織を作る登録になる | 招待先か「個人利用」カテゴリのちょうど片方が `context` に無ければ `ImproperlyConfigured`（TC-23） | 回避 |
| R3: 登録の途中の失敗（重複のメールなど）で、持ち主のいない組織が残る | 組織の作成をシリアライザの `create`（`@transaction.atomic`）の中に置き、検証が通った後にだけ作る（TC-04） | 回避 |
| R4: 誰でも登録して組織の管理者になれるので、AI での問題作成（OpenAI・使った分の料金）を回数の上限なく使える（全体の 300 回/分の制限だけ） | grill-me の後の確認でユーザーが「使えるようにする（今のまま）」と決め、料金が増えうることを受け入れた（2026-11-16・`docs/issues/open/I539.md` の設計確認メモ）。料金の上限・回数の制限を別のイシューにするかは retro で決め、マージ依頼の報告に載せる（計画レビューの Warning） | 受け入れ |
| R5: 誰でも登録して問題・解説の画像を置ける（1 問 5 枚まで）ので、保存の容量が増える | 画像の大きさ・形式の確かめは既存のまま（I031 以降）。個人の利用は品質基準で対象にしている使い方で、容量の上限は今回の範囲の外 | 受け入れ |
| R6: データマイグレーションが運営用のアカウントを動かす・2 回目に組織を増やす | `is_staff=False` かつ `is_superuser=False` だけを対象にし、対象を共有の組織に今いる人で決める（移した人は 2 回目の対象にならない）（TC-14・TC-15） | 回避 |
| R7: 本番で移す人数が多く、マイグレーションが長く掛かる | 1 人ずつ短いトランザクションで移す。開発の DB は 0 人。本番の件数はマージ依頼のときに数え方（下の 9 の Danger Ops）を示して確かめてもらう | 回避 |
| R8: 科目は作れたが問題が 0 件のままクイズを始めると、クイズの画面が「問題が無い」の応答になる（`problems/views.py:893` の既存の扱い） | 案内に「問題管理でその科目の問題を作ると、クイズを始められます」と書き、「問題を作る」ボタンを並べる。問題 0 件の科目の扱いの作り直しは今回の範囲の外 | 受け入れ |
| R9: 個人用の組織の slug が既存の組織の slug と重なり、画像の置き場所（`org/<slug>/`）が重なる | slug を作るときに全組織で重なりを確かめ、重なれば作り直す（TC-02） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 案 A: 組織を指定しない登録では、登録した人ごとに専用の組織（`type='personal'`・名前「（ユーザーID）さんの学習」）を作り、その人を管理者（`role='admin'`）にする
- 科目 0 件なら科目選びを飛ばして登録を終える（組織なし・招待の両方）
- ダッシュボードの案内: 管理者は「まず科目と問題を作りましょう」＋科目管理の画面へのボタン／管理者でない人は「管理者が科目を用意するまでお待ちください」
- 個人用の組織は招待リンクの登録先にせず、未ログインの科目一覧も空にする
- 共有の `personal` 組織の一般の利用者（`is_staff=False`）は一人ずつ専用の組織に移して管理者にする。運営用のアカウントは移さない。共有の組織は残す
- 個人用の組織で作った科目は、作った人の学ぶ科目に自動で入れる。ほかの組織では入れない
- 個人用の組織でも AI での問題作成は今のまま使える（/plan-issue の途中で確認・R4）
- 細部（文言の細部・案内の置き場所や見た目・導線）は BP と UI/UX の観点で Claude が決め、自律判断の記録に残す

Claude が決めた（技術的な選択と理由）:
- 組織は利用者の入力から受け取らない（`organization_id` をシリアライザから消す）— 最小権限・入力でテナントを決めない（R1）
- 「招待で引き当ててよい組織」を `OrganizationQuerySet.invitable()` 1 か所にする — 3 つの入口の条件がずれないように（R2）
- 「本人ひとりの組織」は新しい列 `is_individual` で見分ける（種類 `type` では見分けない）— 種類の既定が `personal` で、招待用の組織（`e2e-org-a` など）にも付いているため（R10）。イシューの AC6 の「`type='personal'`」は、この意味（本人ひとりの組織と共有の `personal` 組織）に言い直した（写しと計画の AC6 を直した・ユーザーの決定〔個人用の組織に他人が入れない〕は変えない）
- 列には `db_default=False` も付ける — コードを戻しても古いコードが組織を作れる（7）
- 個人用の組織の作成は `accounts/services.py` に置き、シリアライザの `create` から呼ぶ — ビューを太らせず、登録と同じトランザクションで作る（R3）
- 個人用の組織の slug は `p-` ＋ 12 桁の 16 進の乱数 — 推測されず、ユーザー ID（個人情報に近い）を URL・画像の置き場所に出さない
- 「個人利用」カテゴリが無いときは組織も利用者も作らず 400 と error ログ — I140 の「環境の異常で自動作成しない」を引き継ぐ
- データマイグレーションにする（管理コマンドではなく）— デプロイで確実に 1 回走り、手作業が要らない。逆向きは `noop`（7 の理由）
- データマイグレーションはアプリのコードを読み込まず、名前・slug の規則を自分の中に書く — 後でサービスが変わってもマイグレーションの意味が変わらない（Django の推奨）
- 運営用のアカウントの判定は `is_staff` または `is_superuser` — スーパーユーザーは `is_staff` が真のはずだが、念のため両方で外す（AC9 を広めに守る）
- 登録画面の科目の取得を React Query のフックに移す — 規約 6.3・取得の失敗を 0 件と取り違えないため（失敗のまま科目なしで送ると、裏側が「科目を最低1つ選択してください」で断る遠回りになる）
- 招待の科目は 1 段目の時点で読む — 科目の有無で 1 段目のボタンの文言（「登録して次へ」／「登録する」）と段の表示を決めるため
- ダッシュボードの管理者の判定は `user.role === 'admin'` — 既存の `Layout.tsx`・`SubjectManagement.tsx` と同じ判定。組織の種類を画面に渡す新しい項目は足さない（不要な露出を増やさない）
- `SubjectManagement.tsx` は変えない — 学ぶ科目への追加は裏側で済み、ダッシュボードは開くたびに取り直す

Claude が決めた（UI/UX の細部・ユーザーの指示「BP、UI/UX の観点でベストなやり方で」に沿う）:
- 科目選びの段が無い登録では、段の表示（「基本情報入力」「科目選択」）を出さない — 1 段しかないのに 2 段に見せない（ux-rules の「迷わせない」）
- そのときの 1 段目のボタンは「登録する」— 押した結果がその場で決まることを文言で示す
- 管理者の案内には「科目を作る」「問題を作る」の 2 つのボタンを並べる — 次の 2 つの操作がどちらも 1 回の押下で届く。問題が 0 件のままクイズに進む遠回り（R8）を減らす
- 管理者でない人の案内は「科目がまだ用意されていません。管理者が科目を用意するまでお待ちください」— 何が足りないかを先に言い、次にすること（待つ）を言う
- 案内は今の `Alert`（info・`role="status"`）とボタン（`outlined`）の形にそろえる — 既存の「学ぶ科目を選ぶ」と同じ見た目・読み上げ

一覧の照合（`docs/reviews/backlog/`）:
- 一覧 I224.md F9・I223.md B1〜B4（いずれも `FILE=-`）: 残す — ハーネスの運用の残り（bot・PR #404 など）で、このイシューの変更点と関係しない
- 実装対象のファイルに当たる行は無し

セキュリティ・ベストプラクティス:
- 入力の検証: `subject_ids` は整数の一覧（DRF の `IntegerField`）。組織は入力から受け取らない。ユーザー ID・メール・パスワードの検証は今のまま
- 認証・認可: 登録は今のまま `AllowAny`＋IP ごとの回数制限（10/5m）。科目の作成は `IsAuthenticated`＋`IsOrgAdmin`（今のまま）。個人用の組織の管理者は自分の組織の中だけ（`available_subjects`・`available_problems` の組織の絞り込み・I446）
- 機密データ: 組織名にユーザー ID を使うが、組織名を返すのは本人の情報（`/api/auth/me/` の `organization_name`）と登録の応答だけ。slug にはユーザー ID を入れない
- OWASP: 組織の引き当ては ORM（SQL を組み立てない）。画面の文言は React の既定のエスケープ。CSRF は JWT のヘッダ認証で今のまま
- フレームワークの推奨: マイグレーションは過去のモデルだけを使う。トランザクションは `transaction.atomic`
- 依存の追加なし（pip-audit・npm audit の新しい対象なし）
- セキュリティの検査の基準: bandit は MEDIUM 以上を直す（LOW は `# nosec` で理由を書いて抑える）。npm audit は high/critical を直す。`secrets.token_hex` は安全な乱数（bandit の B311 に当たらない）

データ整合性・運用性・コスト: 10・12 を参照。外部 API・非同期処理・バッチの追加は無い（P5 影響なし）

性能・UX: 13 を参照

プライバシー: 15 を参照

設計品質:
- ビューは組織の決定だけ（Fat View にしない）。作成はシリアライザ＋サービス
- 空の扱い: `subject_ids` は「無い」も「空の一覧」も空の一覧として扱う（`default=list`）
- エラー: 400 の本文の形は今のまま（`{'error': {'main_message', 'sub_message', 'details'}}`）
- 定数: 組織の種類・カテゴリの slug・個人用の slug の前置きを定数にする

Danger Ops（有無/手順/ロールバック）:
- **有**: データマイグレーション 0023（共有の `personal` 組織の一般の利用者の `organization` と `role` の一括の更新）
- 影響範囲: 共有の `personal` 組織（`type='personal'`・slug `personal`）の利用者のうち `is_staff=False` かつ `is_superuser=False` の人。開発の DB は 0 人（2026-11-16）
- 代替案: 管理コマンドにして手で流す → デプロイのたびの手作業が要り、流し忘れると共有の組織に人が残るので採らない
- 承認: ユーザーが grill-me で「移す」と決めた（2026-11-16）。マイグレーションは PR のレビューとマージで入り、デプロイ（コンテナの起動時の `migrate`）で走る。Claude は手元の開発の DB でも本番でも、このマイグレーションのために `DANGER_OK=1` の操作をしない。マージ依頼のときに、本番の対象の数え方（`docker compose exec -T backend python manage.py shell -c "from accounts.models import User; print(User.objects.filter(organization__type='personal', organization__slug='personal', is_staff=False, is_superuser=False).count())"`）と、「個人利用」カテゴリがあること（`… shell -c "from accounts.models import OrganizationCategory; print(OrganizationCategory.objects.filter(slug='personal').exists())"` が `True`。無いのに対象がいると 0023 が `RuntimeError` でデプロイの `migrate` を止める）と、デプロイで走ることを書いて確かめてもらう。PR に `danger-approved` のラベルを付けるのはユーザー
- ロールバック: 7 のとおり（逆向きは `noop`・コードを戻すだけ）

## 10. データ整合性設計
- 制約: 列 `is_individual`（`BooleanField`・NOT NULL・`default=False`・`db_default=False`）を足すだけ。既存の行はすべて False（招待用の組織・共有の `personal` 組織はそのまま）。`Organization.category` は `PROTECT`・必須（0019）なので、個人用の組織は「個人利用」カテゴリ（0017）を必ず指す。`User.organization` は `CASCADE`（組織を消すと利用者も消える）なので、このイシューでは組織を消さない
- トランザクション: 登録はシリアライザの `create`（`@transaction.atomic`）で、組織・利用者・学ぶ科目・設定・連続記録を 1 つにまとめる。ビューの `transaction.atomic()` もそのまま。マイグレーションは 1 人ずつ `transaction.atomic()`
- 冪等性: マイグレーションの対象は「今、共有の組織にいる一般の利用者」なので、2 回目は対象が 0 人で何もしない（TC-15）。科目の作成時の学ぶ科目は `get_or_create`（`unique_together = (user, subject)`）
- 同時の登録: 同じユーザー ID・メールの同時登録は今の一意の制約（`User.user_id`・`User.email`）で片方が失敗し、トランザクションごと戻るので組織は残らない。slug の重なりの確かめと作成の間の競合は、12 桁の乱数で実際上起きない（起きても組織の slug は一意の制約が無いので登録は失敗しない。画像の置き場所が重なるのは同じ瞬間の 2 件だけで、R9 の確かめで防ぐ範囲の外。受け入れる）
- マイグレーションの安全性: 0022 は NOT NULL の列を DB の既定つきで足すだけ（PostgreSQL は既定が定数の列の追加で表を書き直さない・組織の行は少ない）。古いコードとも両立する（7）。0023 は前進だけのデータの更新で、逆向きは `noop`（7）。テストは `--no-migrations` なので関数を直接呼んで確かめる（TC-14〜TC-16）。CI の `makemigrations --check` でモデルの差分が出ないことを見る（TC-21）

## 12. コスト・保守見積もり
- インフラ: 新しいリソースは無い。組織の行が登録ごとに 1 行増える（数は利用者数と同じ程度）
- 外部 API: AI での問題作成を使える人が増える（R4・ユーザーが受け入れ）
- 運用者の手作業: 無し（マイグレーションはデプロイで自動）。作られた個人用の組織の掃除の手順は無い（退会の仕組みは品質基準 C2 の未整備の範囲）

## 13. 性能・UX設計
- 性能: 登録 1 回で組織の作成 1 回と slug の重なりの確かめ（`exists()` の索引付きの問い合わせ・`slug` に索引あり）が増えるだけ。ダッシュボードは追加の取得なし（管理者かどうかは手元の利用者の情報で決める）
- 読み込み中: 招待の科目を読む間、1 段目のボタンを無効にして丸い読み込み表示（`CircularProgress`）
- 空: 招待の組織に科目が 0 件なら段を出さず「登録する」。ダッシュボードの科目 0 件は管理者／管理者でないで案内を分ける。学ぶ科目に問題が 0 問のときも同じく分け、「クイズを始める」は押せないまま（押してエラーで戻される流れを作らない・AC13）。案内のボタンは、その時点で次にやること 1 つだけを目立つ形（`contained`）で出す
- 性能（AC13）: 学ぶ科目の取得に問題数の `COUNT` を足す（科目と問題の結合 1 本・学ぶ科目は多くても数十件）。追加の取得は無い
- エラー: 招待の科目を読めなければ「科目を読み込めませんでした」＋「再読み込み」（ボタンは無効）。登録の失敗は今のまま `AuthContext` のトースト
- 破壊的な操作: 増やさない
- アクセシビリティ: 案内は `role="status"`（読み上げ）。ボタンはリンクの役割（`component={RouterLink}`）でキーボードで押せる。文言で行き先が分かる（「科目を作る」「問題を作る」）

## 14. 学習効果設計
- 登録した直後に学ぶ中身を自分で作れるようにし、作った科目は自動で学ぶ科目に入る（設定画面に寄り道しない）。学習を始めるまでの手数を減らすことが、このイシューの C1 への寄与。測る指標（KPI）・出題の仕組みは変えない

## 15. プライバシー・コンプライアンス設計
- 新しく集める個人情報は無い（登録の項目は今のまま）
- テナント分離: 個人用の組織は本人ひとりだけ（招待で入れない・未ログインで科目名が見えない・R2）。ほかの利用者の科目・問題・記録は今の組織の絞り込みで見えない（TC-13・TC-20）
- 組織名にユーザー ID が入る。組織名が出るのは本人の画面（科目管理の見出し・`/api/auth/me/`）と登録の応答だけ
- 保持期間・削除権・保護者の同意は今回変えない（品質基準 C2 の未整備の範囲。個人の登録で未成年が登録しうるのは今も同じ）
- 未成年データ・個人情報のテナント越境・目的外利用は無い

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 招待なしの登録で、本文の `organization_id`（他の組織の番号）が使われず、本人は新しい個人用の組織に入る。TC-06 が本当に他の組織の番号を送り、他の組織の利用者が増えないことまで見ているか |
| V2 | 1 | 読んで可 | 個人用の組織の slug で、登録（`/api/auth/register/<slug>/`）が 400・利用者が増えない、slug の確認が 404、未ログインの科目一覧が `[]`。共有の `personal` と、新しく作った個人用の組織の両方で確かめているか（TC-07）。種類が既定の `personal` の招待用の組織は今のまま招待できるか（TC-07b） |
| V3 | 3 | 読んで可 | 個人用の組織の管理者が、別の個人用の組織・学校の組織の科目・問題を一覧・番号指定で見られない（TC-13 と、組織管理者の横断の確かめ TC-20） |
| V4 | 2 | 読んで可 | 登録の検証が失敗したとき（重複のユーザー ID・空でない `subject_ids`）、組織が 1 つも増えない。TC-03・TC-04 が組織の数の前後を比べているか |
| V5 | 1 | 読んで可 | マイグレーションの関数が、運営用のアカウント（`is_staff`・`is_superuser`）を動かさず、2 回目は組織も利用者も変えない（TC-14・TC-15）。テストが本物のマイグレーションのファイルの関数を呼んでいるか（写しでないか） |
| V6 | 3 | 読んで可 | 科目の作成で学ぶ科目に入るのは本人ひとりの組織（`is_individual=True`）だけ。学校の組織と、種類が既定の `personal` の招待用の組織の管理者が科目を作っても学ぶ科目が増えない（TC-11・TC-12） |
| V8 | 1 | 読んで可 | 登録のシリアライザが `context` の渡し忘れ・両方の指定で `ImproperlyConfigured` になり、黙って個人用の組織を作らない（TC-23） |
| V7 | 2 | 読んで可 | 登録画面で、招待の科目を読めなかったときに「登録する」で科目なしの送信をしない（TC-33 が失敗の応答を作り、ボタンが無効で `register` が呼ばれないことを見ているか） |

## 計画変更記録
- 計画レビュー（20261116_2112）の Info（TC-02 の乱数の差し替え）: 4-2 に `pick_unused_slug(candidates)` を分け、TC-02 は候補の一覧を渡して直接確かめる（乱数を差し替えない）。Warning（0022 と 4-2 の規則のずれ）: TC-14 の slug の形を TC-01 と同じ正規表現 `^p-[0-9a-f]{12}$` にし、テストの中で 1 つの定数として両方から使う。Warning（R4 の後続）: R4 の回避策の欄に「retro で決めて報告に載せる」を足した。計画レビューのやり直し: 不要（findings への対応の追記だけ・方式・範囲・受け入れ条件は変えない）
- design-security-review（2026-11-16）の Blocker: 計画書の記載「`invitable()` = `filter(is_active=True).exclude(type='personal')`」「`subject.organization.type == 'personal'` なら学ぶ科目に入れる」。種類の既定が `personal` で、招待用の組織（開発の DB の `e2e-org-a`・`e2e-org-b`）にも付いているため、招待リンクが使えなくなる・関係ない組織で学ぶ科目が増える（R10）。採った方法: 列 `is_individual` を足し（0022・スキーマ）、データマイグレーションを 0023 にずらし、`invitable()`・科目の作成の判定を `is_individual` と共有の `personal` 組織（`type`＋slug）で決める。あわせて High（`context` の渡し忘れで黙って個人用の登録になる）に `ImproperlyConfigured` で備える（R11・TC-23）。AC6 の言い回しを同じ意味に直した（写しも）。計画レビューのやり直し: 要（方式・DB・受け入れ条件の言い回しを変える）
- 計画レビュー（20261116_2118）の Warning（本番にカテゴリが無いと 0023 がデプロイを止める）: 9 の Danger Ops のマージ依頼の確かめに、「個人利用」カテゴリの有無を足した。計画レビューのやり直し: 不要（findings への対応の追記だけ）
- implement（2026-11-16）: 計画書の記載「読めなかった: …ボタンは無効」。TC-33 で、ボタンが無効でも入力欄の Enter で送信が起き、科目なしで登録されることが分かった。採った方法: 1 段目の送信の処理の最初で、招待の科目を読めていなければ何もしない（4-7 に追記）。TC-33 に Enter での送信を足し、止め方を外すと落ちることを確かめた。計画レビューのやり直し: 不要（計画の意図〔科目なしで送らない〕を守る直しで、方式・範囲・受け入れ条件は変えない）
- implement の `/simplify`（2026-11-16）: 計画書の変更点に無い `frontend/src/services/subjectService.ts` の `getSubjectsWithLoading` を消した（呼び出し元は `Register.tsx` の消した取得の effect だけで、呼ぶ所が無くなった・`grep` で確認）。あわせて `Organization.type` の既定値と `SubjectViewSet.public` の `'personal'` を、足した定数（`TYPE_PERSONAL`・`SHARED_PERSONAL_SLUG`）で書いた（値は同じ・マイグレーションの差分なし）。見送り: 画面の道筋の定数を `Layout.tsx`・`App.tsx`・`SubjectDetail.tsx` でも使う直し（計画の外のファイル）・共有の組織に `is_individual` を付けて `invitable()` を簡単にする案（運営用のアカウントが残る組織なので意味が合わない）。計画レビューのやり直し: 不要（使われなくなったコードの片付けと書き方の統一だけで、動きは変えない）
- マージ前のユーザーの BP・UI/UX の確認（2026-11-17・ユーザー「BP,UI/UXの観点でベストなやり方で進めて。」）: close の後に見直すと、科目を作った後・問題を作る前は、ダッシュボードの案内が消えて「クイズを始める」が押せ、押すと「この科目には問題が登録されていません」のエラーの通知でダッシュボードに戻される（イシューの目的〔自分で科目・問題を作ってクイズを始められる〕の途中の行き止まり）。あわせて、科目 0 件の管理者の案内のボタン 2 つが同じ強さで、まだ使えない「問題を作る」も並んでいた。採った方法: AC13 を足し、学ぶ科目の API に問題数を足して（4-7b）、問題のある科目だけをクイズの対象にし、対象が無いときは管理者／管理者でないで案内を分ける。案内のボタンはその時点で次にやること 1 つだけ（科目 0 件は「科目を作る」、問題 0 問は「問題を作る」）を `contained` で出す。TC-24・TC-45〜TC-47 を足し、TC-43・TC-50 を直す。計画レビューのやり直し: 要（範囲・受け入れ条件・API の形を変える）

## レビュー結果
- [20261116_2118 判定: ✅ 完了](../../reviews/closed/I539_plan_review_20261116_2118.md)
- [20261116_2112 判定: ✅ 完了](../../reviews/closed/I539_plan_review_20261116_2112.md)

## セキュリティレビュー結果

**実施日**: 2026-11-16（1 回目で Blocker・High を計画で直し、計画レビュー〔20261116_2118〕の後に 2 回目をやり直した。2 回目は `is_individual` の設計・`invitable()` の条件・0022/0023 の順・`context` の fail-closed を読み直し、新しい Blocker・High なし。Low を 1 件足した）

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Blocker（計画で直した） | マルチテナント | 「本人ひとりの組織」を `type='personal'` で見分けると、種類の既定が `personal` の招待用の組織（開発の DB の `e2e-org-a`・`e2e-org-b`）の招待リンクが使えなくなり、その組織の管理者が科目を作るたびに学ぶ科目が増える | 列 `is_individual`（`db_default=False`）で見分ける。`invitable()` は `is_individual=False` かつ共有の `personal` 組織（`type`＋slug）でないもの。科目の作成時の学ぶ科目の追加は `is_individual` が真のときだけ（R10・TC-07b・TC-12） |
| High（計画で直した） | 認証・認可 | 登録のシリアライザが `context` に招待先が無いと個人用の登録とみなす作りだと、渡し忘れ（将来の別の入口）で黙って管理者の組織が作られる | 招待先か「個人利用」カテゴリのちょうど片方が無ければ `ImproperlyConfigured`（fail-closed・R11・TC-23） |
| Medium | 認証・認可 | 本文の `organization_id` で他の組織に入る（今は入口で上書きしているが、上書きを外すと開く） | シリアライザから `organization_id` を消し、組織はビューが決めて `context` で渡す（R1・TC-06） |
| Medium | マルチテナント | 個人用の組織の slug の推測・総当たりで招待の形の登録・科目名の取得 | slug は 12 桁の乱数。加えて 3 つの入口を `invitable()` で断り、応答は「無い」と同じ（R2・TC-07） |
| Low | 外部通信 | 誰でも登録して AI での問題作成（OpenAI）を使える（料金） | ユーザーが受け入れ（R4）。外部への送信先・鍵の扱いは変えない |
| Low | ファイル操作 | 誰でも画像を置ける（容量） | 既存の大きさ・形式の確かめのまま。置き場所は `org/<乱数の slug>/` で他の組織と重ならない（R5・R9） |
| Low | 機密情報 | 組織名にユーザー ID が入る | 組織名を返すのは本人の画面と登録の応答だけ。slug・画像の置き場所には入れない。ログの文言は今のまま（`test_I437`・TC-20） |
| Low（2 回目） | マルチテナント | `Organization.slug` は一意でない（既存の設計）ので、運営が後から管理画面で `p-…` と同じ slug の組織を手で作ると、画像の置き場所（`org/<slug>/`）が個人用の組織と重なりうる | 個人用の組織を作るときは全組織と重ならないことを確かめる（R9）。招待の引き当ては `invitable()` が個人用の組織を外すので、入る先は取り違えない。slug の一意化は今回の範囲の外（既存の設計の見直し） |
| なし | 入力検証 | — | `subject_ids` は整数の一覧。ほかの項目の検証は今のまま |
| なし | OWASP Top 10 | — | ORM のみ・React の既定のエスケープ・JWT のヘッダ認証。IDOR は他組織と存在しない番号を同じ応答（TC-03・TC-20） |
| なし | 依存ライブラリ | — | 追加なし |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `POST /api/auth/register/` | 未認証 | 本文に他の組織の `organization_id` を入れて、招待なしで学校の組織に入る | 組織は入力から決めない。本人は新しい個人用の組織に入り、学校の組織の利用者は増えない | Yes: TC-06 | No | なし | Medium |
| 2 | `POST /api/auth/register/<slug>/`・`GET /api/organizations/validate-slug/<slug>/`・`GET /api/(organizations/)subjects/public/?slug=` | 未認証 | 他人の個人用の組織（共有の `personal` を含む）の slug を使い、その組織に入る・科目名を見る | 400／404／`[]` で「無い組織」と同じ応答。利用者が増えない | Yes: TC-07 | Yes: 手動 8・9（画面の表示） | slug の総当たり（12 桁の乱数で現実的でない） | Medium |
| 3 | `POST /api/auth/register/` | 未認証 | 他の組織の科目の番号を `subject_ids` に入れ、その科目を学ぶ科目にする | 400 で断り、存在しない番号と同じ応答。利用者・組織が増えない | Yes: TC-03・TC-20 | No | なし | Medium |
| 4 | 個人用の組織の管理者の API（科目・問題・学ぶ科目） | 一般（個人用の組織の管理者） | 管理者になったことを使って、別の組織の科目・問題を一覧・番号指定で読む・書く | 自組織の中だけ（`available_subjects`・`available_problems`） | Yes: TC-13・TC-20 | No | なし | Medium |
| 5 | `POST /api/auth/register/` | 未認証 | 大量に登録して組織・管理者を量産する | IP ごとの 10/5m の回数制限（今のまま） | No | No | 分散した IP からの量産は止められない（行が増えるだけ・料金は R4） | Low |
| 6 | `POST /api/subjects/` | 管理者（学校・種類が既定の招待用の組織） | 科目の作成で、関係ない組織でも学ぶ科目が勝手に増える | 本人ひとりの組織だけで学ぶ科目に入れる | Yes: TC-11・TC-12 | No | なし | Medium |
| 7 | データマイグレーション 0023 | 運用（デプロイ） | 運営用のアカウントが個人用の組織に移り、権限・所属が変わる | `is_staff`・`is_superuser` を動かさない。2 回目は何もしない | Yes: TC-14・TC-15・TC-16 | No | 本番の対象数は未確認（マージ依頼で確かめる） | Medium |
| 8 | 登録のシリアライザ | 開発（将来の入口） | `context` を渡し忘れ、黙って管理者の組織を作る | `ImproperlyConfigured` で止まる | Yes: TC-23 | No | なし | Low |
| 9 | 問題管理の AI 作成 | 一般（個人用の組織の管理者） | 回数の上限なしで OpenAI を呼ぶ | 全体の 300 回/分の制限だけ（ユーザーが受け入れ・R4） | No | No | 料金が増えうる（受け入れ） | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件（1 回目の 1 件は計画で直した） | 0件 |
| High    | 0件（1 回目の 1 件は計画で直した） | 0件 |
| Medium  | 2件 | 6件 |
| Low     | 4件 | 3件 |

### 残余リスク処遇
- retro（2026-11-16）で決定: High 以上の残りなし。Medium はすべて計画で回避済み。Low・受け入れ（R4 AI の料金・R5 画像の容量・R8 問題 0 件の科目・slug の重なり・分散した IP からの量産）は受け入れ。個人用の組織の掃除は I548（#548）の F4 で検討（詳細は `docs/reviews/open/I539_review.md` の「## 振り返り」）
