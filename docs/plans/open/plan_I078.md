## 基本情報
- **計画書ID**: plan_I078
- **関連イシュー**: #156
- **Draft PR**: #218
- **作成根拠資料**: docs/issues/open/I078.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I078_review.md
- **作成日**: 2026-07-16

---

## 1. 背景/目的

問題管理画面で**正解の選択肢を確認・保持できない**不具合を解消する。

- **原因の概要**: 出題画面で答えを漏らさないため `ChoiceSerializer.is_correct` が `write_only=True` になっており、管理画面の GET でも正解が返らない。そのため参照プレビューで正解をマークできず、編集ダイアログで正解ラジオが初期選択されない（編集のたびに正解を選び直す必要があり、取り違え・未指定 400 のリスク）。
- **解決方針**: 出題・結果・AI 生成応答は `is_correct` 非露出のまま（答え漏洩防止＝セキュリティ要件）、**管理 `ProblemViewSet`（I102 で admin 限定済み）にだけ**管理専用シリアライザで `is_correct` を返す分離を実装し、フロントで正解の表示・編集初期選択を実現する。

## 調査結果

### 前提（I102 マージ済み・充足確認済み）
- `ProblemViewSet.permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]`（`backend/problems/views.py:154`）。参照含む全経路が admin 限定のため、`is_correct` を無条件露出しても到達できるのは admin のみ（Option B・grill 確定）。

### 根本原因（コードレベル）
- `ChoiceSerializer`（`backend/problems/serializers.py:19-25`）: `extra_kwargs = {'is_correct': {'write_only': True}}` により GET レスポンスに `is_correct` が含まれない。
- 消費関係（is_correct 露出の波及先を確定するための全件洗い出し）:
  - `ProblemSerializer.choices = ChoiceSerializer(many=True, required=False)`（`serializers.py:83`）← 管理 CRUD・AI 生成応答（`views.py:422/446/551` で直接インスタンス化）が使用
  - `QuizAnswerDetailSerializer.problem = ProblemSerializer` / `selected_choices = ChoiceSerializer`（`serializers.py:277-278`）← 結果経路（`GET /api/quiz/{id}/`）が使用
  - `ProblemDisplaySerializer.choices = ChoiceDisplaySerializer`（`serializers.py:228-229`）← 出題経路（`next_problem`）。`ChoiceDisplaySerializer` は fields に is_correct 自体を含まない（:28-31）
- フロント: `openEditDialog` は `is_correct: c.is_correct` を読むコードが**既に存在**（`frontend/src/pages/QuizManagement.tsx:397-400`）し、ラジオ/チェックは `watch('choices.N.is_correct')` で描画（:793/:798）。API が返せば編集初期選択は**コード変更なしで動作する**。プレビューの実体は共通コンポーネント `ProblemPreview.tsx` で、正解マーク（緑枠＋'✓' 文字）のコードが既存だが API 非露出のため不作動（`frontend/src/components/ProblemPreview.tsx:174-181`）。使用箇所は `QuizManagement.tsx:910-912`（`showCorrectAnswer={true}`）のみ。
- 型: `frontend/src/services/types.ts:107` に `Choice.is_correct: boolean`（必須）既存 → 型変更不要（grill 確定）。`@mui/icons-material ^5.15.10` 導入済み（アイコン追加に新規依存不要）。

### テスト baseline（事前実行済み）
- Backend: `docker compose exec -T backend pytest problems/tests -q` → **61 passed**（クリーン・2026-07-15）
- Frontend: `docker compose exec -T frontend npm test -- --watchAll=false` → **2 suites / 7 passed**（クリーン・2026-07-16）

### キャッシュ仕様（デプロイ直後の表示に影響）
- 問題一覧はユーザー別キャッシュ（`cache_service`、TTL=`problem_list: 3600`＝1時間、`core/settings.py:319`）。デプロイ直後は**旧形式（is_correct 無し）のキャッシュ**が最大1時間残り得る。問題の作成/更新/削除で `invalidate_problems_cache` が走るため恒久障害にはならない（→ Risk-4・手動テスト手順に反映）。

### 発見した既存バグ（本イシュー対象外・**別イシューで対応＝ユーザー決定 2026-07-16**）
- `_save_ai_problem_to_db`（`views.py:465-476`）が `Problem(title=..., description=...)` を使うが、`Problem` モデルに `title`/`description` フィールドは存在しない（`models.py:103-180`、本文フィールドは `question`）。`generate_ai`/`generate_adaptive` の `save_to_db=True` 経路は TypeError→500 になる**既存不具合**（I103 計画の「AI 未設定で 400/500 になり得る」注記とも整合）。このため **AI 生成応答の is_correct 非露出は API レベルではなくシリアライザ単体 TC（TC-AUTO-07）で担保**する（応答は `ProblemSerializer` 直接使用のため単体で構造的に固定できる）。

## 2. 受け入れ条件（Acceptance Criteria）
- [ ] 管理専用 `ProblemAdminSerializer`（`ProblemSerializer` 継承）＋`ChoiceAdminSerializer` が新設され、admin の `GET /api/problems/`（list）・`GET /api/problems/{id}/`（retrieve）で各選択肢に `is_correct` が返る（読み書き両可＝POST/PUT の保存も従来どおり機能）
- [ ] 既存 `ProblemSerializer`・共有 `ChoiceSerializer` は不変更（is_correct 非露出維持）
- [ ] 出題経路（`GET /api/quiz/{id}/next_problem/`）のレスポンスに `is_correct` が含まれない（回帰テストで固定）
- [ ] 結果経路（`GET /api/quiz/{id}/` の `answers[].problem.choices` / `answers[].selected_choices`）に `is_correct` が含まれない（回帰テストで固定）
- [ ] AI 生成応答が使う `ProblemSerializer` の表現に `is_correct` が含まれない（シリアライザ単体の回帰テストで固定）
- [ ] 参照プレビューで正解選択肢がチェックアイコン＋「正解」ラベル（緑系・色のみ非依存）でマークされる
- [ ] 編集ダイアログを開くと正解の選択肢が初期選択されている（single_choice=ラジオ / multiple_choice=チェック複数）
- [ ] 画像/テキストのみ編集して保存しても正解が保持される
- [ ] 上記を検証する自動テストが全て PASS し、既存スイート（BE 61 件・FE 7 件）に回帰がない

## 3. 影響範囲
- **Backend**: `backend/problems/serializers.py`（`ChoiceAdminSerializer`/`ProblemAdminSerializer` 新設）、`backend/problems/views.py`（`ProblemViewSet.serializer_class` 切替＋import）、`backend/problems/tests/`（新規テスト）
- **Frontend**: `frontend/src/components/ProblemPreview.tsx`（正解マークをアイコン＋ラベルに拡張）、`frontend/src/pages/QuizManagement.tsx`（**変更なし**・編集初期選択の動作確認のみ）、`frontend/src/services/types.ts`（**変更なし**・確認のみ）
- **DB**: なし（P3 影響なし）
- **Config/Infra**: なし（P8 影響なし）
- 依存関係ファイル（requirements/package）変更なし → Dockerfile/compose 波及なし

## 4. 変更点一覧

| ファイル | 対象 | 変更内容 |
|---------|------|---------|
| `backend/problems/serializers.py` | `ChoiceAdminSerializer`（新設） | `ChoiceSerializer` と同一 fields（`['id', 'text', 'is_correct', 'order']`）で `extra_kwargs` の write_only を持たない管理専用シリアライザ。`ProblemSerializer` 定義の直後（:226 付近・`ProblemDisplaySerializer` の前）に配置 |
| `backend/problems/serializers.py` | `ProblemAdminSerializer`（新設） | `ProblemSerializer` を継承し `choices = ChoiceAdminSerializer(many=True, required=False)` のみ上書き。`Meta`／`to_internal_value`／`validate_choices`／`create`／`update`／画像 SerializerMethodField は継承で再利用 |
| `backend/problems/views.py` | `ProblemViewSet.serializer_class`（:151） | `ProblemSerializer` → `ProblemAdminSerializer` に無条件切替。import（:12-16）に `ProblemAdminSerializer` を追加。`generate_ai`/`generate_adaptive` の `ProblemSerializer(...)` 直接使用（:422/:446/:551）は**不変更** |
| `frontend/src/components/ProblemPreview.tsx` | 選択肢表示（:166-185） | `' ✓'` 文字連結を、`CheckCircleIcon`＋`Chip label="正解" color="success"` に置換（緑枠・緑背景は維持）。`@mui/icons-material` の `CheckCircle` を import |
| `backend/problems/tests/test_I078_is_correct_exposure.py`（新規） | — | 露出/非露出の回帰テスト（テスト計画 TC-AUTO-01〜08） |

### 実装コード例

**修正アプローチ**: 「is_correct を返してよい経路」を新設クラスに分離し、既存クラスは1文字も変えない。これにより出題・結果・AI 応答（`role='user'` が到達し得る経路）は構造的に不変更で担保される。

`backend/problems/serializers.py`（`ProblemSerializer` の直後に追加）:
```python
class ChoiceAdminSerializer(serializers.ModelSerializer):
    """管理画面専用: is_correct を読み書き両可で露出する（I078）。

    ProblemViewSet（I102 で admin 限定）以外で使用しないこと。
    出題・結果・AI 応答は ChoiceSerializer / ChoiceDisplaySerializer（非露出）を維持する。
    ChoiceSerializer の fields を変更する場合は本クラスも合わせて更新すること（意図的な非継承＝既存クラス不変更方針のため）。
    """
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']


class ProblemAdminSerializer(ProblemSerializer):
    """管理画面専用: choices のみ is_correct 露出版に差し替える（I078）"""
    choices = ChoiceAdminSerializer(many=True, required=False)
```

`backend/problems/views.py`:
```python
from .serializers import (
    SubjectSerializer, ProblemSerializer, ProblemAdminSerializer, ProblemDisplaySerializer,
    QuizSessionSerializer, QuizSessionDetailSerializer,
    SubmitAnswerSerializer, MediaAssetSerializer
)
...
class ProblemViewSet(MultipartFormDataMixin, viewsets.ModelViewSet):
    serializer_class = ProblemAdminSerializer  # I078: 管理経路のみ is_correct 露出（I102 で admin 限定）
```

`frontend/src/components/ProblemPreview.tsx`（選択肢 Box 内・:179-182 の置換）:
```tsx
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
...
<Box
  key={choice.id || index}
  sx={{
    p: 1, mb: 1, border: 1, borderRadius: 1,
    borderColor: showCorrectAnswer && choice.is_correct ? 'success.main' : 'grey.300',
    backgroundColor: showCorrectAnswer && choice.is_correct ? 'success.light' : 'transparent',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  }}
>
  <Typography>
    {String.fromCharCode(65 + index)}. {choice.text}
  </Typography>
  {showCorrectAnswer && choice.is_correct && (
    <Chip icon={<CheckCircleIcon />} label="正解" size="small" color="success" />
  )}
</Box>
```

`frontend/src/pages/QuizManagement.tsx`: **コード変更なし**。`openEditDialog`（:397-400）が API の `is_correct` をそのまま初期値に流すため、BE 露出のみで初期選択が機能する（手動テストで検証。動作しない場合は実装を中断し、計画書更新→承認の手順を踏む）。

## 5. 実装手順（垂直スライス・TDD）

- **ステップ1: BE 露出＋漏洩防止回帰（垂直スライス1）**
  1. `test_I078_is_correct_exposure.py` に TC-AUTO-01〜07 を追加。
  2. 現行コードに対し実行: 露出系 TC-AUTO-01〜04 が **RED**（write_only で is_correct 欠落）、非露出系 TC-AUTO-05〜07 が GREEN であることを確認・記録 → TC 参照。
  3. `ChoiceAdminSerializer`/`ProblemAdminSerializer` 新設＋`serializer_class` 切替 → TC-AUTO-01〜07 全 GREEN。
  4. 非露出系 TC の false-green 注入検証を実施（→ auto_test 文書「false-green 自己検証」参照）。
- **ステップ2: FE プレビュー正解マーク（垂直スライス2・ステップ1完了が前提）**
  1. `ProblemPreview.tsx` を上記コード例どおり変更。
  2. 表示確認は手動テスト（manual_test No.4）で実施。
- **ステップ3: 編集初期選択の動作確認＋全体回帰（ステップ1完了が前提・ステップ2と並行可）**
  1. 編集ダイアログの初期選択（コード変更なし）を手動テスト（manual_test No.5-7）で確認。
  2. BE 全体回帰（TC-AUTO-08）・FE Jest 回帰を実行。

依存関係: ステップ2・3 はステップ1（API 露出）完了が前提。ステップ2 と 3 は並行実施可。サービス再起動: 不要（ホットリロード。ただし BE はコード反映のため dev サーバー自動リロードを確認）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I078_auto_test.md`）
- テストレベル: **API 結合テスト**（DRF `APIClient`・露出/非露出の経路検証）＋**シリアライザ単体テスト**（AI 応答経路の構造的担保）。
- 再発防止: 出題・結果・AI 応答への is_correct 漏洩を否定 TC で固定（答え漏洩リグレッション防止＝イシューのセキュリティ要件）。
- 認可テスト: 非admin の 403 は I102 のテストが既に担保（本イシューで重複実装しない・grill 確定）。

### 手動テスト（詳細: `docs/tests/open/I078_manual_test.md`）
- UI（プレビューの正解マーク・編集ダイアログ初期選択・保存後の正解保持）は Human 実施。使用アカウント: `admin@example.com`（cute_school・問題22件）を使用。
- コード確認・テスト実行・API レスポンス確認は Claude 実施。

## 7. ロールバック
- `views.py` の `serializer_class` を `ProblemSerializer` に戻し import を除去、`serializers.py` の新設2クラスを削除、`ProblemPreview.tsx` の変更を revert、テストファイルを削除すれば従来動作へ完全に戻る。DB 変更なしのためマイグレーション巻き戻し不要。

## 8. Risk & 回避策
- **リスク1（最重要）**: `ProblemAdminSerializer` が誤って出題・結果・AI 経路に配線され正解が学生に漏れる。→ 回避: 既存クラスは不変更（差分ゼロ）・新クラスの参照は `ProblemViewSet.serializer_class` の1箇所のみ（レビューで grep 確認）・TC-AUTO-05/06/07 が漏洩を恒久的に固定。
- **リスク2**: 継承により `create`/`update`/`validate_choices` の書き込み挙動が変わる。→ 回避: `write_only` は表現（GET）のみに影響し `validated_data` には従来から is_correct が入る＝書き込み経路は同一コード。TC-AUTO-03/04 で 201/200・DB 保存値を検証。
- **リスク3**: 編集ダイアログが is_correct 露出だけでは初期選択されない（未知の FE 依存）。→ 回避: コード読解では動作見込み（:397-400/:793/:798）。手動テスト No.5-6 で検証し、NG なら実装中断→計画書更新→承認の正規手順で対応（勝手に直さない）。
- **リスク4**: デプロイ直後、ユーザー別一覧キャッシュ（TTL 1時間）に旧形式（is_correct 無し）が残り、プレビューが一時的にマーク無しになる。→ 回避: 恒久障害ではない（create/update/delete で無効化・TTL で自然解消）。手動テストでは問題を1件編集（キャッシュ無効化）してから確認する手順にする。
- **リスク5**: `success.light` 背景と `Chip color="success"` のコントラスト・視認性。→ 回避: ラベル文字「正解」で色のみ非依存を担保（a11y）。見た目の最終判断は手動テスト（Human）で確認。

## セキュリティ・ベストプラクティスチェック
- **認可・最小権限**: is_correct の露出先は `ProblemViewSet` のみ＝I102 の `IsAuthenticated + IsOrgAdmin` が前段で防御（構造的に admin 以外到達不可）。`permission_classes` は不変更（I102 の担当・grill 確定）。
- **情報露出（本イシューの主リスク）**: 出題・結果・AI 応答の非露出を否定 TC（TC-AUTO-05/06/07）で固定。既存クラス不変更により構造的に担保。
- **入力バリデーション**: `validate_choices`（継承）を不変更で維持（正解0/最大10/空text/500字超の既存ルール）。
- **機密データ**: パスワード・トークン・個人情報の新規取扱いなし（is_correct は教材データ）。
- **OWASP**: A01（アクセス制御）は I102 の防御を継承。XSS: プレビューは MUI コンポーネント経由のテキスト描画（dangerouslySetInnerHTML 不使用）で既存パターン踏襲。
- **依存ライブラリ**: 追加なし（`@mui/icons-material` 導入済み）→ 新規 audit 対象なし。bandit/npm audit: 新規スキャン対象なし。

## 高リスク判定
- **判定: Yes**。「画面制御していても API 直叩きで事故りうる変更」（シリアライザ配線を誤ると学生に正解が漏れる情報露出軸）に該当。認可自体は不変更だが、答え漏洩はプロダクトの信頼性に直結（品質基準 C2）。
- **推奨フロー**: `/plan-issue-review I078` → **`/security-review I078`** → `/implement I078`。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: DB 変更なし（シリアライザの表現変更のみ）。
- **P5（運用設計/外部API/非同期/バッチ）影響なし**: AI 生成の挙動不変更・新規外部連携なし。
- **P6（性能・UX）**: 追加は choice ごとの boolean 1 フィールドのみ・choices は `prefetch_related` 済みで新規 N+1 なし。UI は既存プレビューの表示拡張（ローディング/空/エラー状態は既存のまま変更なし・破壊的操作なし）。a11y はラベル文字で色のみ非依存。→ セクション13 は本セクションと Risk-4/5 で充足。
- **P8（コスト）影響なし**: 新規インフラ/外部サービスなし。
- **P9（プライバシー）影響なし**: 個人情報・未成年データの新規取扱いなし（is_correct は教材データ）。テナント越境なし。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| `ProblemAdminSerializer` 新設＋`serializer_class` 無条件切替（ロール出し分け不要） | イシュー明記（grill 確定・Option B） |
| `ProblemSerializer` 継承・choices のみ差し替え | イシュー明記（grill 確定） |
| 既存 `ProblemSerializer`/`ChoiceSerializer` 不変更 | イシュー明記（grill 確定） |
| is_correct は読み書き両可の通常フィールド | イシュー明記（grill 確定） |
| プレビュー実装は `ProblemPreview.tsx` の既存表示を拡張 | イシュー明記（grill 確定・2026-07-15 追記） |
| 正解マーク＝チェックアイコン＋「正解」ラベル（緑系・色のみ非依存） | イシュー明記（grill 確定） |
| `QuizManagement.tsx` はコード変更なし（動作確認のみ） | 仮定で決めた（コード読解: :397-400/:793/:798 で動作見込み。NG 時は計画更新へ） |
| `ChoiceAdminSerializer` というクラス名 | 仮定で決めた（イシューは「管理専用 Choice シリアライザ」とのみ記載。既存 `ChoiceDisplaySerializer` の命名パターンに準拠） |
| 正解 Chip の配置＝選択肢行の右端（`justifyContent: 'space-between'`） | 仮定で決めた（UI 詳細は承認ポイントで事前確認） |
| AI 応答の漏洩防止はシリアライザ単体 TC で担保（API レベル不可） | 仮定で決めた（調査で発見した既存バグ＝`_save_ai_problem_to_db` の title/description 不整合により API 経路が 500 のため。**バグ自体は別イシューで対応＝ユーザー決定 2026-07-16**） |
| テストファイル名 `test_I078_is_correct_exposure.py` | 仮定で決めた（既存 `test_I###_*.py` 命名に準拠） |

→ 「仮定で決めた」5項目は次の承認ポイントで確認する。

## セキュリティレビュー結果

**実施日**: 2026-07-16

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Low | 機密情報/情報露出 | `ProblemAdminSerializer`/`ChoiceAdminSerializer` が将来、学生到達可能な経路（出題 `ProblemDisplaySerializer`・結果 `QuizAnswerDetailSerializer`・AI 応答）に誤配線されると正解が学生に漏れる | **禁止事項: 両クラスを `ProblemViewSet.serializer_class` 以外で使用しない**（docstring に明記）。否定 TC-AUTO-05/06/07 が漏洩を恒久固定（false-green 注入検証付き）。手動 No.3 で参照箇所を grep 全件確認 |
| Low | 機密情報 | 正解入りの問題一覧がユーザー別キャッシュ（Redis）に保存されるようになる | キャッシュキーは `user_id` スコープ（`cache_service.get/set_problems_cache`）で他ユーザーへ配信されない。Redis は内部ネットワーク限定の既存構成。許容 |
| Low | 保守 | `ChoiceAdminSerializer` が `ChoiceSerializer` 非継承（意図的＝既存クラス不変更方針）のため、将来のフィールド追加時に乖離し得る | docstring に「`ChoiceSerializer` の fields 変更時は本クラスも更新」を明記（plan-review Info 対応済み）。乖離は機能劣化方向であり漏洩方向ではない |

その他の分類: 認証・認可（`permission_classes` 不変更＝I102 の `IsAuthenticated + IsOrgAdmin` が前段防御・最小権限維持）／マルチテナント（`get_queryset` の組織フィルタ不変更＝露出は自組織データのみ）／入力検証（`validate_choices` 継承・不変更）／OWASP（XSS: MUI テキスト描画・dangerouslySetInnerHTML 不使用。IDOR: org フィルタで 404）／ファイル操作（画像経路不変更）／外部通信（AI 経路不変更・新規外部連携なし）／依存ライブラリ（追加なし）: **リスクなし**

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `GET /api/problems/`（list/retrieve） | 一般（role=user） | 直叩きで is_correct 入りデータの取得 | I102 の `IsOrgAdmin` が 403 | Yes: I102 既存 TC（`test_non_admin_cannot_read`） | No | なし（前段防御・本イシューで不変更） | 封鎖 |
| 2 | 同上 | 未認証 | 直叩き | `IsAuthenticated` が 401 | Yes: I102 既存 TC | No | なし | 封鎖 |
| 3 | `GET /api/quiz/{id}/next_problem/` | 一般（学生） | 出題レスポンスから回答前に正解を読む | `ChoiceDisplaySerializer`（is_correct 非含有）を維持 | Yes: TC-AUTO-05 | Yes: manual No.8（画面目視） | なし | 封鎖 |
| 4 | `GET /api/quiz/{id}/` | 一般（学生） | 結果詳細の `problem.choices`/`selected_choices` から正解を読む | 共有 `ChoiceSerializer` の write_only 維持 | Yes: TC-AUTO-06 | No | なし | 封鎖 |
| 5 | `POST /api/problems/generate_ai/` 等の応答 | admin（現状）・将来の権限緩和時 | AI 応答から is_correct を読む | `ProblemSerializer(...)` 直接使用を維持 | Yes: TC-AUTO-07（シリアライザ単体） | Yes: manual No.3（grep 配線確認） | API レベル検証は既存 500 バグ（別イシュー対応決定済み）により不可＝単体 TC で代替 | Low |
| 6 | `GET /api/problems/{他組織のid}/` | 他組織 admin | 越境で他組織の正解を取得 | `get_queryset` の `subject__organization` フィルタ → 404 | No（既存挙動・専用 TC なし） | No（コード確認済み） | 越境 retrieve の専用回帰テストが無い（既存挙動・本イシューで不変更。I106 の CRUD カバレッジ拡充で補完余地） | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 0件 | 0件 |
| Low     | 3件 | 2件 |

### 残余リスク処遇
（/retro で決定する）
- 設計 Low-1（誤配線漏洩）: 否定 TC＋grep で継続監視。/retro で追加ゲート要否を判断。
- 設計 Low-2（キャッシュ内の正解データ）: 既存構成で許容。
- 設計 Low-3（Admin シリアライザの保守乖離）: docstring 注記で運用。
- シナリオ Low-5（AI 応答の API レベル未検証）: 既存 500 バグの別イシュー（起票予定・メモリ記録済み）で解消後に API レベル TC 追加を検討。
- シナリオ Low-6（越境 retrieve の専用 TC 不在）: I106（テストカバレッジ負債）での補完を検討。

## 9. 承認ポイント（チェックリスト）
- [ ] BE 方式: `ChoiceAdminSerializer`＋`ProblemAdminSerializer`（継承・choices のみ差し替え）新設、`ProblemViewSet.serializer_class` 無条件切替、既存クラス不変更 — でよいか
- [ ] クラス名 `ChoiceAdminSerializer` でよいか（既存 `ChoiceDisplaySerializer` の命名パターン準拠）
- [ ] UI: プレビューの正解マークは**選択肢行の右端に `CheckCircle` アイコン＋「正解」Chip（緑・small）**、既存の緑枠・緑背景は維持 — この配置・ラベルでよいか
- [ ] `QuizManagement.tsx` はコード変更なし（編集初期選択は既存コードで動作見込み・手動テストで検証、NG なら計画更新に戻る）— でよいか
- [ ] AI 生成応答の漏洩防止テストは、既存バグ（`_save_ai_problem_to_db` の title/description 不整合→500・本イシュー対象外・**別イシューで対応＝決定済み**）により API レベルでなく **`ProblemSerializer` 単体 TC** で担保する — でよいか
- [ ] テストファイル名 `test_I078_is_correct_exposure.py` でよいか
- [ ] 高リスク判定 Yes（情報露出軸）→ plan-review 後に `/security-review I078` を通すフローでよいか

## レビュー結果
- [20260716_0038 判定: ✅ 完了](../../reviews/I078_plan_review_20260716_0038.md)
