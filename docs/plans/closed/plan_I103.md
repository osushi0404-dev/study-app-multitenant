## 基本情報
- **計画書ID**: plan_I103
- **関連イシュー**: #193
- **Draft PR**: #201
- **作成根拠資料**: docs/issues/open/I103.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I103_review.md
- **作成日**: 2026-07-14

---

## 1. 背景/目的

問題作成 API で、組織管理者（`role=='admin'`）が**自組織以外の科目（subject）に問題を作成できてしまう**マルチテナント越境書き込みの穴を塞ぐ。`perform_update` には SEC-1（越境 subject 付け替え拒否）があるが、**create 側は非対称に無防備**。さらに grill で、同型の穴が **AI生成2経路（`generate_ai`/`generate_adaptive`）にも存在**することが判明した（`Subject.objects.get(id=subject_id)` を組織フィルタ無しで取得し、その subject 配下に問題を作成）。

本イシューは問題を作成する**全3経路**にテナント境界検証を追加し、越境を **403** で拒否する。

## 調査結果

### 前提（I102 マージ済み・develop 上で確認）
- `ProblemViewSet.permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]`（`backend/problems/views.py:152`）。参照含む全経路が admin 限定。したがって本穴を突けるのは管理者のみ＝**他組織管理者による越境注入**を塞ぐ差分。

### 根本原因（コードレベル・develop 現況）
- `perform_create`（`views.py:234`）: subject の組織検証が無い。`ProblemService.create_problem_with_images` は `validated_data['subject']` を信頼し `organization = subject.organization` を導出（`services/problem_service.py:72-77`）。→ 投稿 subject の組織に無条件で書き込む。
- `generate_ai`（`views.py:354`）: `subject = Subject.objects.get(id=subject_id)`（`:373`）を**組織フィルタ無し**で取得→ `_save_ai_problem_to_db` で `Problem(subject=subject)` 作成（`save_to_db=True` 時。`save_to_db=False` は非永続だが他組織 subject を使った生成自体が境界逸脱）。
- `generate_adaptive`（`views.py:483`）: `Subject.objects.get(id=subject_id)`（`:496`）で同型。常に永続。
- 対照: `perform_update` SEC-1 は「永続化済み `problem.subject` を権威とし投稿 subject を信頼しない」方式（`services/problem_service.py:259-261`、view 側チェックは `views.py:298-299`）。create には永続化済み subject が無い（投稿値が唯一のソース）ため、**view 層の明示チェックが正しい防御層**。

### status の既存不整合（→ 403 に収束）
同一 ViewSet 内で越境拒否 status が割れている: `upload_image`（`views.py:612`）・`delete_image`（`:729`）＝**403**（`権限がありません`） / `perform_update` SEC-1（`:298-299`）＝400。**403 が既存多数派**。本イシューは create/AI を **403** で追加して多数派に揃える。`perform_update` SEC-1 の 400→403 統一は別イシュー（`test_I073_image_update.py` の 400 アサート7箇所を巻き込むため分離）。本イシューの間は create/AI=403・update=400 の一時的不整合を許容。

### テスト baseline
- `docker compose exec -T backend python -m pytest problems/tests/ -q` → **50 passed**（クリーン）。
- 既存 fixture: `test_I102_problem_authz.py` に org/admin/user/subject/problem/choice の生成パターン・`_valid_payload(subject_id)`・`APIClient.force_authenticate` あり。本イシューの越境テストは**第2組織（org B）＋その subject** を追加して流用する。

## 2. 受け入れ条件（Acceptance Criteria）
- [ ] org A の admin が org B の `subject` を指定して `POST /api/problems/` すると **403**（`他組織の科目には問題を作成できません`）で拒否され、Problem が作成されない
- [ ] org A の admin が org B の `subject_id` で `POST /api/problems/generate_ai/`（`save_to_db` の True/False 双方）・`POST /api/problems/generate_adaptive/` を実行すると **403** で拒否され、Problem が作成されない
- [ ] org A の admin が自組織の `subject` で `POST /api/problems/` すると従来どおり **201** で成功する
- [ ] org A の admin が自組織の `subject_id` で AI 生成2経路を叩くと **403 にならない**（認可通過・org 検証通過）
- [ ] 3経路の検証がいずれも同一判定（`subject.organization_id != request.user.organization_id`）で越境を拒否している
- [ ] 上記を検証する回帰テスト（TC-AUTO-01〜05）が追加され全て PASS、既存 50 件も回帰なし

## 3. 影響範囲
- **Backend**: `backend/problems/views.py`（`perform_create`/`generate_ai`/`generate_adaptive` に org 検証・403）、`backend/problems/tests/`（越境回帰テスト新規）
- **Frontend**: なし
- **DB**: なし（P3 影響なし）
- **Config/Infra**: なし（P8 影響なし）
- 依存関係ファイル（requirements/package）変更なし → Dockerfile/compose 波及なし

## 4. 変更点一覧

| ファイル | 関数 | 変更内容 |
|---------|------|---------|
| `backend/problems/views.py` | `ProblemViewSet.perform_create`（:234） | 冒頭で `subject = serializer.validated_data['subject']`（`Problem.subject` は NOT NULL・serializer でも required のため create 時は必ず存在＝未指定は serializer で 400 済み。None ガードは不要）を取り、`subject.organization_id != self.request.user.organization_id` なら `PermissionDenied('他組織の科目には問題を作成できません')`（→403）。既存の画像収集・`ProblemService` 呼び出しの前に配置。`from rest_framework.exceptions import PermissionDenied` はファイル先頭に置く |
| `backend/problems/views.py` | `ProblemViewSet.generate_ai`（:354） | `subject = Subject.objects.get(id=subject_id)`（:373）取得直後・`DoesNotExist`（404）処理の後、生成 try ブロックの前に、`subject.organization_id != request.user.organization_id` なら `Response({'error': '他組織の科目には問題を作成できません'}, status=status.HTTP_403_FORBIDDEN)`。`save_to_db` の値に関わらず一律 |
| `backend/problems/views.py` | `ProblemViewSet.generate_adaptive`（:483） | `Subject.objects.get(id=subject_id)`（:496）取得直後・`DoesNotExist`（404）処理の後、生成の前に同じ org チェックで 403 を返す |
| `backend/problems/tests/test_I103_cross_org_create.py`（新規） | — | 越境作成の回帰テスト（下記テスト計画 TC-AUTO-01〜05） |

### 実装コード例

`perform_create`（冒頭に追加。`from rest_framework.exceptions import PermissionDenied` はファイル先頭へ）:
```python
def perform_create(self, serializer):
    # subject は Problem.subject=NOT NULL・serializer required のため create 時は必ず存在
    # （未指定なら serializer バリデーションで 400 済み）。よって None ガードは不要。
    subject = serializer.validated_data['subject']
    if subject.organization_id != self.request.user.organization_id:
        raise PermissionDenied('他組織の科目には問題を作成できません')
    # 以降は現行のまま（画像収集 → ProblemService.create_problem_with_images ...）
```

`generate_ai`（subject 取得の `except Subject.DoesNotExist` ブロック直後に追加）:
```python
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response({'error': '指定された科目が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

    # I103: 越境 subject への作成を拒否（save_to_db に関わらず生成前）
    if subject.organization_id != request.user.organization_id:
        return Response({'error': '他組織の科目には問題を作成できません'},
                        status=status.HTTP_403_FORBIDDEN)
```

`generate_adaptive`（同様に subject 取得の `except` 直後）:
```python
    # I103: 越境 subject への作成を拒否
    if subject.organization_id != request.user.organization_id:
        return Response({'error': '他組織の科目には問題を作成できません'},
                        status=status.HTTP_403_FORBIDDEN)
```

## 5. 実装手順（垂直スライス・TDD）

前提: 3経路とも同一の検証ロジック。BE のみ（UI なし）。各ステップは「新規TCをまず現行コードに対して実行し RED（403 期待が現行 201/非403 で失敗）を確認 → ガード追加 → GREEN」の TDD で進める（false-green 防止＝否定/回帰 TC の失敗注入確認を兼ねる）。

- **ステップ1: create 経路（垂直スライス1）**
  1. `test_I103_cross_org_create.py` に TC-AUTO-01（越境 create=403・未作成）と TC-AUTO-04（自組織 create=201）を追加。
  2. 現行コードに対し TC-AUTO-01 を実行し **RED**（現状 201 で 403 アサート失敗）を確認・記録 → TC-AUTO-01/04 参照。
  3. `perform_create` に org チェックを追加 → TC-AUTO-01/04 が GREEN。
- **ステップ2: AI生成2経路（垂直スライス2、ステップ1と独立・並行可）**
  1. TC-AUTO-02（generate_ai 越境=403、save_to_db True/False）・TC-AUTO-03（generate_adaptive 越境=403）・TC-AUTO-05（自組織 AI 経路が非403）を追加。
  2. TC-AUTO-02/03 を現行コードに対し実行し **RED** を確認・記録 → TC-AUTO-02/03 参照。
  3. `generate_ai`/`generate_adaptive` に org チェックを追加 → GREEN。
- **ステップ3: 全体回帰**
  1. `problems/tests/` 全体を実行し、新規 TC 全 PASS＋既存 50 件回帰なしを確認 → TC-AUTO-06 参照。

依存関係: ステップ1とステップ2は独立（並行実施可）。ステップ3は1・2の完了が前提。

## 6. テスト計画

### 自動テスト（`docs/tests/open/I103_auto_test.md` に詳細）
- テストレベル: **API 結合テスト**（DRF `APIClient`）。認可・テナント境界の検証は結合レベルが適切（permission/viewset/service を通す）。
- 再発防止: 越境 create/AI が 403 で拒否されることを固定（回帰防止）。
- 認可・テナント境界テスト: org A admin × org B subject の越境を3経路で検証。

### 手動テスト（`docs/tests/open/I103_manual_test.md`）
- BE のみ・UI 変更なしのため、Claude が API/コード/ログで確認できる範囲が中心（実施者 Claude）。

## 7. ロールバック
- `views.py` の追加ブロック（各経路の org チェック）を削除すれば従来動作へ戻る。DB 変更なしのためマイグレーション巻き戻し不要。テストファイルは削除。

## 8. Risk & 回避策
- **リスク1**: 自組織の正常な作成・AI生成を誤って 403 で弾く（過剰拒否）。→ 回避: 判定は `subject.organization_id != request.user.organization_id`（SEC-1 と同一・upload/delete と同一概念）。TC-AUTO-04/05 で自組織成功・非403 を担保。
- **リスク2**: AI生成の org チェックが AI 呼び出しの後になり、越境でも外部 API を消費/例外に飲まれる。→ 回避: `Subject.objects.get` 直後・生成 try ブロックの前に配置（例外の広域 `except`→500 に飲まれない）。TC-AUTO-02/03 で 403（500/404 でない）を固定。
- **リスク3**: create=403 と update SEC-1=400 の一時的不整合。→ 許容（別イシューで 403 統一予定）。本計画では意図的差分として明記。

## セキュリティ・ベストプラクティスチェック
- **認可・最小権限**: 本イシュー自体がテナント境界（越境書き込み禁止）の是正。3経路に一貫適用。
- **入力バリデーション**: subject の所属組織を検証（信頼できない入力＝投稿 subject_id を検証）。
- **情報露出**: 越境時 403（存在露呈）だが、既存 upload/delete=403 と一致した規約に収束（あえて 404 で隠す方針は取らない＝決定済み）。
- **機密データ**: パスワード/トークン/個人情報の新規取扱いなし。
- **OWASP**: A01 Broken Access Control（テナント越境）への直接的な是正。
- bandit/npm audit: 依存追加なし・新規スキャン対象なし → 該当なし。

## 高リスク判定（必須）
- **判定: Yes**。plan-reviewer の高リスク基準のうち「**認証・認可・ロール変更**」「**マルチテナント境界変更**」「**画面制御していても API 直叩きで事故りうる変更**」に該当する。
- I043（未成年/個人情報の高リスク＝プライバシー軸）としては非該当だが、**認可・テナント境界軸で高リスク**。
- **推奨フロー**: `/plan-issue-review I103`（`VERDICT: HIGHRISK` 想定）→ **`/security-review I103`** → `/implement I103`。実装前に security-review を通す。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: DB 変更なし。
- **P5（運用設計/外部API/非同期/バッチ）影響なし**: 既存の AI 生成挙動は不変更（前段に検証を足すのみ・新規外部連携/非同期/バッチなし）。
- **P6（性能・UX）影響なし**: UI なし・追加クエリは既存 subject 参照の属性アクセスのみ（新規 N+1 なし）。
- **P8（コスト）影響なし**: 新規インフラ/外部サービスなし。
- **P9（プライバシー）**: テナント分離を**強化**する変更（C2 に資する）。新規の個人情報/未成年データ処理なし → I043（プライバシー軸の高リスク）としては非該当。ただし認可・テナント境界軸では高リスクのため security-review を通す（上記「高リスク判定」参照）。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| 対象は create 3経路（perform_create/generate_ai/generate_adaptive） | イシュー明記（grill 確定） |
| 判定式 `subject.organization_id != request.user.organization_id` | イシュー明記（SEC-1 と同一概念） |
| 拒否 status = 403（perform_create=`PermissionDenied` / AI=`Response(403)`） | イシュー明記（grill 確定・upload/delete と一致） |
| エラー message = `他組織の科目には問題を作成できません` | イシュー明記 |
| `save_to_db=False` でも一律チェック | イシュー明記（grill 確定） |
| SEC-1 400→403 統一は別イシュー | イシュー明記（grill 確定） |
| queryset 二重防御は不採用 | イシュー明記 |
| 新規テストファイル名 `test_I103_cross_org_create.py` | 仮定で決めた（既存 `test_I###_*.py` 命名に準拠） |

→ 「仮定で決めた」項目は**テストファイル名のみ**（命名規約に沿った軽微な決定）。他は全てイシュー本文に明記済み。

## セキュリティレビュー結果

**実施日**: 2026-07-14

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Low | OWASP(enumeration)/機密情報 | 越境時 403 が「他組織に当該 subject が実在」を露呈（403 vs 404）。到達者は自組織 admin のみ（I102） | 設計決定済み：`upload_image`/`delete_image` の既存 403 と統一。許容。将来 404 統一は別途検討可 |
| Low | 入力検証 | `generate_ai`/`generate_adaptive` の `Subject.objects.get(id=subject_id)` は非整数 subject_id で `ValueError`→500（`DoesNotExist` 非該当）。**I103 以前からの既存挙動**（org チェックは get 後に追加＝本変更が導入したものではない） | 本イシュー対象外（越境バイパスにはならない）。堅牢化は別イシュー候補 |

その他（認証・認可／マルチテナント（本変更が是正）／ファイル操作（越境ファイル書込みも同時封鎖＝改善）／外部通信（org チェックが AI 呼び出し前）／依存ライブラリ）: リスクなし。

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化 | 手動確認 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `POST /api/problems/` | org A admin | org B subject_id で作成 | 403・Problem 未作成・越境ファイル書込みなし | Yes: TC-AUTO-01 | No | なし | 封鎖 |
| 2 | `POST /generate_ai/` | org A admin | org B subject_id で生成（save_to_db T/F） | 403・生成前停止（AI 未呼出）・未作成 | Yes: TC-AUTO-02a/b | No | なし | 封鎖 |
| 3 | `POST /generate_adaptive/` | org A admin | org B subject_id で適応生成 | 403・未作成 | Yes: TC-AUTO-03 | No | なし | 封鎖 |
| 4 | 3経路 | 非admin(role=user) | 直叩き | 403（IsOrgAdmin・I102 前段防御） | Yes: I102 TC 済 | No | なし（多層） | — |
| 5 | 3経路 | org A admin | 自組織 subject | 正常成功（過剰拒否なし） | Yes: TC-AUTO-04/05 | No | なし | — |
| 6 | `POST /generate_ai/` | org A admin | 非整数 subject_id | 500 になる既存挙動 | No | No | 既存・越境バイパスでない | Low |

**サマリー**: Blocker 0 / High 0（新規リスクは本変更で封鎖）/ Medium 0 / Low 2（既存挙動・設計決定済みの残余）。

### 残余リスク処遇
（/retro で決定する）
- Low-1（403 enumeration）: 設計決定として許容。将来 404 統一の是非は SEC-1 status 統一の別イシューと併せて検討。
- Low-2（非整数 subject_id→500）: 既存挙動。堅牢化（400 化）は別イシュー候補。

## 9. 承認ポイント（チェックリスト）
- [ ] 対象3経路（perform_create / generate_ai / generate_adaptive）と各実装位置でよいか
- [ ] 拒否 status = **403**、message = `他組織の科目には問題を作成できません` でよいか
- [ ] `perform_create` は `PermissionDenied`（→`{"detail":...}`）、AI経路は `Response({"error":...}, 403)` という body 形状差（DRF 慣用差・既存も混在）を許容するか
- [ ] `generate_ai` の `save_to_db=False` でも 403 で弾く方針でよいか
- [ ] SEC-1（update）の 400→403 統一を本イシューに含めず別イシューとする（当面 create/AI=403・update=400 の一時的不整合を許容）でよいか
- [ ] テストファイル名 `test_I103_cross_org_create.py`（新規）でよいか

## 完了情報
- **完了日**: 2026-07-15
- **対応者**: Claude Code
- **レビュー結果**: OK（plan-review: Blocker 0 / security-review: Blocker 0・Low 2 / code-review: VERDICT OK・Low 2）
- **テスト**: `problems/tests/` 56 passed（既存50＋新規6・回帰なし）・false-green 検証済み・CI 全ジョブ green
- **retro 派生**: P4/P5 → I105 同梱 / P3 → I111（#206）起票 / 残余リスク Low×3 は追跡

## レビュー結果
- [20260714_2159 判定: ✅ 完了](../../reviews/closed/I103_plan_review_20260714_2159.md)
