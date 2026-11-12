# 計画書: I472 解説画像がある問題へのクイズの回答の 500 を直し、新しい形式の解説画像と問題の画像もクイズで表示する

## 基本情報
- **計画書ID**: plan_I472
- **関連イシュー**: #472
- **Draft PR**: #474
- **作成根拠資料**: docs/issues/open/I472.md（GitHub #472 の本文の写し）
- **実装後評価**: docs/reviews/open/I472_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
イシューの「背景/目的」と同じ。クイズの回答の応答（`POST /api/quiz/<id>/submit_answer/`）が、文字列の欄 `Problem.explanation_image` に `.url` を呼ぶので、古い形式の解説画像がある問題に答えると 500 になる。しかも 500 の時点で、回答・回の集計・復習の予定（I452）は保存済み。あわせて、新しい形式（MediaAsset）の解説画像と問題の画像が、クイズの画面に出ていない。

この計画で、(1) 応答の解説画像の URL を他の経路と同じ作り方にする、(2) 応答の組み立てを保存と同じトランザクションに入れ、組み立てに失敗したら何も残さない、(3) 応答に新しい形式の解説画像を入れ、クイズの画面で問題文の画像と解説画像を問題管理のプレビューと同じ選び方・並べ方で出す（設計確認メモ 2026-11-12）。

### 調査結果
**原因の概要**: 回答の応答だけが、解説画像の欄を「ファイルの欄」と取り違えて書かれている。応答を作る処理が保存の後・トランザクションの外にあるため、そこで失敗すると「保存されたのに画面にはエラー」になる。クイズの画面は古い形式の画像しか知らない。

**エラーの詳細**: `AttributeError: 'str' object has no attribute 'url'`（`backend/problems/views.py:988` `'explanation_image': problem.explanation_image.url if problem.explanation_image else None`）。2026-10-26 にロールバック付きの実験で再現（イシュー）。

**詳細な原因分析**:
1. エラーの流れ: `submit_answer` が `transaction.atomic()`（`views.py:942-982`）の中で QuizAnswer の作成・正誤・回の集計（`session.save(update_fields=[...])`）・復習の予定（`spaced_repetition_service(...).record_quiz_answer`）を済ませる → ブロックを抜けてコミット → `views.py:985-997` で応答の辞書を作る → `problem.explanation_image` が空でなければ `.url` で例外 → Django の 500（`custom_exception_handler` は DRF の例外以外を扱わず、`ATOMIC_REQUESTS` も設定なし〔`backend/core/settings.py` に無い〕）
2. 技術的な背景: `Problem.explanation_image` は `CharField`（`models.py:138`・ファイル名だけ）。URL は `get_explanation_image_url()`（`models.py:174-179`・`/media/<科目の解説画像の場所>/<ファイル名>`）で作る。`ProblemSerializer`・`ProblemDisplaySerializer` の `get_explanation_image`（`serializers.py:229-231・285-287`）はこれを使う
3. なぜ起きたか: 応答を手書きの辞書で組み立てていて、解説画像の URL の作り方が 1 か所にまとまっていなかった（FileField だった頃の書き方が残った）。dev DB に古い形式の解説画像が 0 件のため、表に出なかった
4. 新しい形式の画像: `ProblemDisplaySerializer`（次の問題の応答・`views.py:898`）には `question_images`・`explanation_images` があるが、回答の応答には `explanation_images` が無い。画面（`frontend/src/pages/QuizSession.tsx:494-509` の問題画像・`621-650` の解説画像）は古い形式の `question_image`・`explanation_image` だけを使い、URL は `${process.env.REACT_APP_API_BASE_URL}${…}` で作る
5. 問題管理のプレビュー（`frontend/src/components/ProblemPreview.tsx`）: 選び方は「新しい形式が 1 枚以上あれば新しい形式だけ・無ければ古い形式 1 枚」（`68-86`）、並べ方は `renderImages`（`91-139`・`ImageList`・1 枚なら 1 列・2 枚以上なら min(枚数, 3) 列・gap 8・高さ最大 300・`objectFit: contain`・`role="button"`・`tabIndex=0`・`aria-label="<alt> <n>枚目。クリックで拡大表示"`・クリックと Enter／スペースで拡大・URL は `getMediaUrl()`）。解説画像は解説文があるときだけ出す（`193-207`）。テストは無い
6. 新しい形式の URL は `MediaAsset.get_url()` = `/media/<storage_key>`（`models.py:407-409`）。`Problem.get_media_assets(usage_kind)`（`models.py:160-165`）が `select_related('asset')`・`position` 順で 1 クエリ。新しい形式の画像の応答の作り方（`MediaAssetSerializer([link.asset …], many=True).data`）は `serializers.py` に同じ 2 行が 4 か所ある（`233-241`・`289-297`）

**根本原因（コード）**: `backend/problems/views.py:985-997` の手書きの応答（`.url` の呼び出しと、トランザクションの外での組み立て）。`frontend/src/pages/QuizSession.tsx:494-509・621-650` の古い形式だけを見る表示。

### 環境前提
- app-1 のコンテナ（backend・db・frontend・redis）が動いている（2026-11-12 `docker compose ps`）。`gh` は Draft PR #474 の作成で確認済み
- 画面確認は Playwright MCP（`docs/runbooks/frontend-verify.md`）。dev のメディアは Django が配信する（`backend/core/urls.py:40-43`）。確認用の画像には `backend/media/` の既存の png を写して使う
- テストは CI が正。手元では新しいテストと、守りにする既存のテストのファイルだけを流す（全テストは流さない）

## 2. 受け入れ条件（Acceptance Criteria）
イシューの受け入れ条件と同じ。この計画での合格の基準:
- [ ] AC1: 古い形式の解説画像（`explanation_image` にファイル名）がある問題に回答すると 200 で、応答の `explanation_image` が `get_explanation_image_url()` と同じ URL（TC-01）
- [ ] AC2: 応答の組み立てに失敗すると 500 で、QuizAnswer・回の集計（`completed_problems`・`correct_answers`）・復習のカード（`SpacedRepetitionCard`）・復習記録（`SpacedRepetitionReview`）がどれも残らない（TC-04）
- [ ] AC3: 新しい形式の解説画像がある問題に回答すると、応答の `explanation_images` に表示順で入り、回答後の解説に出る（TC-02・TC-09・手動 No.2）
- [ ] AC4: 回答後の解説画像は、新しい形式が 1 枚以上あれば新しい形式だけ・無ければ古い形式 1 枚。並べ方は `ProblemPreview.tsx` と同じ（1 枚 1 列・2 枚以上 min(枚数, 3) 列・高さ最大 300・クリックと Enter／スペースで拡大）（TC-07・TC-08・TC-09）
- [ ] AC5: 解説文が無く解説画像だけの問題でも、回答後に解説の枠と画像が出る（TC-09）
- [ ] AC6: 新しい形式の問題の画像（`question_images`）がある問題では、問題文の下にその画像が出る（解説画像と同じ選び方・並べ方）（TC-09・手動 No.2）
- [ ] AC7: 回帰テストが追加され、全テストが pass（既存テストの件数を減らさない）（TC-06・TC-11・TC-12）

## 3. 影響範囲
- Backend:
  - `backend/problems/views.py`（`QuizSessionViewSet.submit_answer` の応答）
  - `backend/problems/serializers.py`（新しい形式の画像の応答の共通関数・回答の解説の serializer）
  - `backend/problems/tests/test_I472_quiz_answer_explanation_image.py`（新規）
- Frontend:
  - `frontend/src/utils/problemImages.ts`（新規・画像の選び方）
  - `frontend/src/components/ProblemImageList.tsx`（新規・画像の並べ方。`ProblemPreview.tsx` の `renderImages` を切り出す）
  - `frontend/src/components/ProblemPreview.tsx`（上の 2 つを使う。見え方は変えない）
  - `frontend/src/pages/QuizSession.tsx`（問題文の画像・回答後の解説画像）
  - `frontend/src/types/quiz.ts`（`Problem`・`QuizResult` に新しい形式の欄）
  - テスト: `frontend/src/pages/__tests__/QuizSession.test.tsx`（追記）・`frontend/src/utils/__tests__/problemImages.test.ts`（新規）・`frontend/src/components/__tests__/ProblemImageList.test.tsx`（新規）・`frontend/src/components/__tests__/ProblemPreview.test.tsx`（新規）
- DB: なし（スキーマ変更・migration なし）
- Config/Infra: なし（依存の追加なし）

## 4. 変更点一覧

### 修正アプローチ
サーバーは、回答の応答の「解説」の部分（解説文・古い形式の画像の URL・新しい形式の画像）を serializer に任せ、URL の作り方を他の経路と同じにする。応答の辞書の組み立てを、保存と同じ `transaction.atomic()` の中に移す（組み立てに失敗すれば保存も巻き戻る）。画面は、画像の「選び方」（関数）と「並べ方」（部品）を `ProblemPreview.tsx` から切り出し、プレビューとクイズの問題文・解説の 3 か所で同じものを使う（同じ見え方を作りで保証する）。

### 4-1. 新しい形式の画像の応答の共通関数と、回答の解説の serializer（`backend/problems/serializers.py`）
**修正方針**: 同じ 2 行が 4 か所にある新しい形式の画像の応答を 1 つの関数にし、既存の 4 つのメソッドと新しい serializer から使う（既存の応答の中身は変えない）。回答の解説は `Problem` の ModelSerializer で、URL は `get_explanation_image_url()`。

```python
def serialize_media_assets(problem, usage_kind):
    """問題に紐づく新しい形式の画像（usage_kind の分・表示順）の応答"""
    media_links = problem.get_media_assets(usage_kind=usage_kind)
    return MediaAssetSerializer([link.asset for link in media_links], many=True).data
```
`ProblemSerializer`・`ProblemDisplaySerializer` の `get_question_images` は `return serialize_media_assets(obj, 'problem')`、`get_explanation_images` は `return serialize_media_assets(obj, 'explanation')` にする。

```python
class AnswerExplanationSerializer(serializers.ModelSerializer):
    """クイズの回答の応答に入れる解説（解説文・古い形式の画像の URL・新しい形式の画像）"""
    explanation_image = serializers.SerializerMethodField()
    explanation_images = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = ['explanation', 'explanation_image', 'explanation_images']

    def get_explanation_image(self, obj):
        """古い形式の解説画像の URL（他の経路と同じ作り方）"""
        return obj.get_explanation_image_url()

    def get_explanation_images(self, obj):
        """新しい形式の解説画像（表示順）"""
        return serialize_media_assets(obj, 'explanation')
```
置き場所は `ProblemDisplaySerializer` の後。

### 4-2. 回答の応答（`backend/problems/views.py` `QuizSessionViewSet.submit_answer`）
**修正方針**: 応答の辞書を `with transaction.atomic():` の中の最後（復習の予定の後）で組み立て、ブロックの外で `Response(result)` を返す。解説の 3 つの欄は 4-1 の serializer から入れる。ほかの欄（`is_correct`・`correct_choices`・`session_complete`・`session`・`session_stats`）の中身は変えない。I158 の `update_fields`・I452 の 1 つのトランザクション・I166 の問題の取得は変えない。

```python
            spaced_repetition_service(session.user).record_quiz_answer(
                problem, is_correct, time_taken)

            # 応答も同じトランザクションの中で作る（作るのに失敗したら回答・集計・復習の予定を残さない）
            result = {
                'is_correct': is_correct,
                **AnswerExplanationSerializer(problem).data,
                'correct_choices': list(problem.choices.filter(is_correct=True).values('id', 'text')),
                'session_complete': not session.is_active,
                'session': QuizSessionSerializer(session).data,
                'session_stats': {  # 後方互換性のため残す
                    'completed': session.completed_problems,
                    'total': session.total_problems,
                    'correct': session.correct_answers
                }
            }

        return Response(result)
```
`from .serializers import (...)` に `AnswerExplanationSerializer` を足す。元のコメント `# Return result with explanation and updated session` は上の新しいコメントに置き換える。

### 4-3. 画像の選び方（`frontend/src/utils/problemImages.ts`・新規）
**修正方針**: プレビューの `getQuestionImageUrls`・`getExplanationImageUrls`（`ProblemPreview.tsx:68-86`）と同じ規則を 1 つの関数にする。

```ts
import { MediaAsset } from '../services/types';

/**
 * 表示する画像の URL（新しい形式が 1 枚以上あれば新しい形式だけ、無ければ古い形式の 1 枚）
 * 問題管理のプレビューとクイズの画面で同じ規則を使う（I472）
 */
export const pickImageUrls = (
  assets: MediaAsset[] | null | undefined,
  legacyUrl: string | null | undefined,
): string[] => {
  if (assets && assets.length > 0) {
    return assets.map((asset) => asset.url);
  }
  return legacyUrl ? [legacyUrl] : [];
};
```

### 4-4. 画像の並べ方（`frontend/src/components/ProblemImageList.tsx`・新規）
**修正方針**: `ProblemPreview.tsx:91-139` の `renderImages` の JSX をそのまま部品にする（見た目・属性・キー操作を変えない）。拡大の状態は持たず、押された画像の完全な URL（`getMediaUrl(url)`）を `onImageClick` で親に渡す（親が今の `ImageModal` を持ち続ける）。

```tsx
interface ProblemImageListProps {
  /** 表示する画像の URL（API の相対パス・pickImageUrls の戻り値） */
  images: string[];
  /** 代替テキストの頭（例: '問題画像' → 「問題画像 1」） */
  alt: string;
  /** 画像を押したとき（クリック・Enter・スペース）に、完全な URL を受け取る */
  onImageClick: (fullUrl: string) => void;
}
```
`images` が空なら `null` を返す。中身は `renderImages` と同じ（`Box mt=2` → `ImageList cols={images.length === 1 ? 1 : Math.min(images.length, 3)} gap={8}` → 各 `ImageListItem` に `Box component="img"`・同じ `sx`・`alt={`${alt} ${index + 1}`}`・`aria-label={`${alt} ${index + 1}枚目。クリックで拡大表示`}`・`loading="lazy"`）。`React.memo` は使わない（親の再描画が軽く、props の配列は毎回作り直すので効かない）。

### 4-5. 問題管理のプレビュー（`frontend/src/components/ProblemPreview.tsx`）
**修正方針**: 見え方を変えずに、`getQuestionImageUrls`・`getExplanationImageUrls`・`renderImages` を 4-3・4-4 に置き換える。`questionImages = pickImageUrls(problem.question_images, problem.question_image)`・`explanationImages = pickImageUrls(problem.explanation_images, problem.explanation_image)`・`<ProblemImageList images={questionImages} alt="問題画像" onImageClick={setImageModalOpen} />`（解説も同じ・`alt="解説画像"`）。解説文が無いと解説画像を出さない動き（`showExplanation && problem.explanation &&`）は変えない（イシューの「含まない」）。使わなくなった `ImageList`・`ImageListItem`・`getMediaUrl` の import を消す。

### 4-6. クイズの画面（`frontend/src/pages/QuizSession.tsx`）
**修正方針**: 問題文の画像と回答後の解説画像を、4-3 で選び 4-4 で並べる。拡大は今の `imageModalOpen`・`ImageModal`（`706-710`）をそのまま使う。
- 問題文の画像（`494-509` の `{currentProblem.question_image && (<Box mt={2}><img …/></Box>)}`）を次に置き換える:
  ```tsx
  <ProblemImageList
    images={pickImageUrls(currentProblem.question_images, currentProblem.question_image)}
    alt="問題画像"
    onImageClick={setImageModalOpen}
  />
  ```
- 回答後の解説（`619-651`）: `const explanationImages = result ? pickImageUrls(result.explanation_images, result.explanation_image) : [];` を、早期の `return` の後・`return (` の前（`if (!currentProblem || !session)` の後）で作る。枠を出す条件を `(result.explanation || explanationImages.length > 0)` にし、`{result.explanation_image && (<Box …><img …/></Box>)}` を `<ProblemImageList images={explanationImages} alt="解説画像" onImageClick={setImageModalOpen} />` に置き換える（解説文が無くても画像があれば枠と画像を出す・設計確認メモ）。コメント `{/* 解説ボックス: 解説文または解説画像がある場合に表示 */}` はそのまま
- 画像の余白は部品の `mt=2` になる（今の解説画像は解説文が無いと `mt=0`。プレビューと同じ見え方にそろえる）
- `process.env.REACT_APP_API_BASE_URL` を前に付ける書き方は、この画面から無くなる（URL は部品の `getMediaUrl()`）

### 4-7. 型（`frontend/src/types/quiz.ts`）
**修正方針**: 応答にある欄を型に足す。`import { MediaAsset } from '../services/types';`
- `Problem` に `question_images?: MediaAsset[];`・`explanation_images?: MediaAsset[];`（次の問題の応答 `ProblemDisplaySerializer` にある）
- `QuizResult` に `explanation_images?: MediaAsset[];`
- 古い形式の `question_image?`・`explanation_image?` は `string | null`（API は空なら `null` を返す）にする

### 4-8. テスト
**バックエンド**（`backend/problems/tests/test_I472_quiz_answer_explanation_image.py`・新規）: データの作り方は I166 のテスト（組織・科目・問題・選択肢・`force_authenticate`）にそろえる。組織 A の slug は `org-i472-a`、科目の slug は `subj-i472`。
- `test_legacy_explanation_image_returns_200`（TC-01）: `explanation_image='sample.png'` の問題に正解を送る → 200・`explanation_image == problem.get_explanation_image_url() == '/media/org/org-i472-a/subjects/subj-i472/explanation/sample.png'`・`explanation_images == []`・QuizAnswer が 1 件・回の `completed_problems == 1`
- `test_new_format_explanation_images`（TC-02）: 解説用の MediaAsset 2 枚（`position` 2 と 1 の順に作る）と問題用 1 枚を紐づけ、古い形式の `explanation_image` も入れる → 応答の `explanation_images` は解説用の 2 枚だけを `position` の順に、各要素は `id`・`url`（`/media/<storage_key>`）・`usage_kind`（`explanation`）・`original_filename`・`mime_type`・`file_size_bytes`・`created_at` を持つ。`explanation_image` は古い形式の URL（API は両方を返し、選ぶのは画面）
- `test_response_keys_without_images`（TC-03）: 画像の無い問題 → `explanation_image is None`・`explanation_images == []`・応答のキーの集合が `{'is_correct','explanation','explanation_image','explanation_images','correct_choices','session_complete','session','session_stats'}`・`explanation` が問題の解説文
- `test_build_failure_leaves_nothing`（TC-04）: `APIClient(raise_request_exception=False)` で、(a) `Problem.get_explanation_image_url` を例外を出す関数に差し替える (b) `QuizSessionSerializer.to_representation` を例外を出す関数に差し替える（組み立ての最後の欄）。それぞれ → 500・その回の QuizAnswer 0 件・回の `completed_problems == 0`・`correct_answers == 0`（DB から読み直す）・その利用者と問題の `SpacedRepetitionCard`・`SpacedRepetitionReview` が 0 件。差し替えを戻して同じ問題に答え直すと 200（「Problem already answered」の 400 にならない）。差し替えは pytest の `monkeypatch`（失敗の注入。本番のコードにテストのための口は作らない）
- `test_serializers_share_media_assets`（TC-05）: 問題用・解説用の画像を持つ問題で、`ProblemDisplaySerializer`・`ProblemSerializer` の `question_images`・`explanation_images` と、`AnswerExplanationSerializer` の `explanation_images` が、用途ごとに作った画像だけを表示順で返す（4-1 の共通化で既存の応答が変わらない）

**フロントエンド**:
- `frontend/src/utils/__tests__/problemImages.test.ts`（TC-07）: (a) 新 2 枚＋古 → 新 2 枚の URL を順に (b) 新が空配列＋古 → `[古]` (c) 新 `undefined`＋古 `null` → `[]` (d) 新 1 枚＋古 `undefined` → `[新]`
- `frontend/src/components/__tests__/ProblemImageList.test.tsx`（TC-08）: (a) 1 枚 → `ImageList`（`ul`）の `grid-template-columns` が `repeat(1, 1fr)`・`img` の `alt` が「解説画像 1」・`aria-label` が「解説画像 1枚目。クリックで拡大表示」・`role="button"`・`tabindex="0"`・`src` が `getMediaUrl(url)` (b) 2 枚 → `repeat(2, 1fr)` (c) 4 枚 → `repeat(3, 1fr)` (d) クリック・Enter・スペースで `onImageClick` が完全な URL で呼ばれる（ほかのキーでは呼ばれない）(e) 空配列 → 何も描かない (f) `https://` で始まる URL はそのまま `src` に入る
- `frontend/src/pages/__tests__/QuizSession.test.tsx`（追記・TC-09）: 既存の `mockSession`・`mockProblem` を使い、単一選択の即時回答で応答を返す。(a) 応答に `explanation_images` 2 枚と `explanation_image` → 「解説画像 1」「解説画像 2」が新しい形式の URL で出て、古い形式の URL の `img` は無い (b) `explanation_image` だけ → 「解説画像 1」が古い形式の URL で 1 枚 (c) `explanation: ''`・`explanation_images` 1 枚 → `answer-result` の中に「解説画像 1」があり、「解説:」は無い (d) 解説画像を押すと拡大の画面（`role="dialog"`）が開き、その中の `img` の `src` が押した画像の完全な URL (e) 問題に `question_images` 1 枚と `question_image` → 回答の前に「問題画像 1」が新しい形式の URL で出る (f) `question_image` だけ → 「問題画像 1」が古い形式の URL (g) どちらも無い → 代替テキストが「問題画像」で始まる `img` が無い
- `frontend/src/components/__tests__/ProblemPreview.test.tsx`（新規・TC-10）: 切り出しの前後で見え方が変わらないことの守り。(a) 新しい形式の解説画像 2 枚＋古い形式 → 「解説画像 1」「解説画像 2」が新しい形式の URL (b) 古い形式だけ → 「解説画像 1」が古い形式の URL (c) 解説文が空 → 解説画像が出ない (d) 問題画像を押すと拡大の画面が開く

## 5. 実装手順
- ステップ 1（未知リスク先行・サーバーの縦の 1 本）: 4-1・4-2 と 4-8 のバックエンドのテスト。TC-01 は直す前のコードで 500（Red）を確かめてから直す。→ TC-01〜TC-05・TC-06
- ステップ 2（ステップ 1 と並行可）: 4-3・4-4・4-5 と TC-07・TC-08・TC-10（プレビューの見え方が変わらないことを先に固定する）
- ステップ 3（ステップ 1・2 が前提）: 4-6・4-7 と TC-09・TC-11。続けて画面確認（手動 No.1〜No.3）
- ステップ 4: /simplify の後に TC-13 の流し直し

## 6. テスト計画
- 自動: `docs/tests/open/I472_auto_test.md`。テストレベル: サーバーは API の結合テスト（`APIClient` で `submit_answer` を呼ぶ・DB の残りを確かめる）と serializer の単体、画面は関数と部品の単体・ページの結合（Jest・API は差し替え）。新しい E2E は足さない（画像の有無で分かれる表示は Jest で全分岐を確かめられ、E2E の既存のクイズの流れ〔`e2e/tests/quiz-session.spec.ts`〕は CI で無退行を見る）
- 再発防止: TC-01（`.url` に戻すと 500）・TC-04（応答の組み立てをトランザクションの外に戻すと、残りが 0 件の確かめで落ちる）・TC-09（新しい形式を見なくなると落ちる）
- 手動: `docs/tests/open/I472_manual_test.md`（Claude が Playwright MCP で行う。Human の項目なし）
- 認可・テナント: 問題の取得（I166 の `available_problems`）は変えない。画像は問題に紐づいたものだけを返し、他の問題・組織の画像を返す経路を足さない。守りに I166 のテストを流す（TC-06）

## 7. ロールバック
コードだけの変更（DB の形は変えない）。PR を revert すれば戻る。サービスの再起動は通常のデプロイだけ。手動テストで dev DB に足した確認用のデータは、確認の後に問題を論理削除（1 件ずつ `is_deleted=True` で `save()`）する（`.delete()`・一括 `update()` は使わない）。

## 8. Risk & 回避策
- R1 応答の組み立てをトランザクションに入れたことで、ロックの保持がわずかに長くなる → 増えるのは読み出し 2〜3 クエリ（選択肢の正解・画像の紐づけ・回の serializer は DB を読まない）。行のロックは `session.save` の更新行だけで、同じ回の回答は 1 人の利用者の順番の操作
- R2 4-1 の共通化で既存の問題の応答（問題管理・次の問題）が変わる → 中身は同じ 2 行の移動だけ。TC-05 と既存の `problems/tests/test_serializers.py`・`test_views.py`（TC-06）で守る
- R3 4-5 の切り出しでプレビューの見え方が変わる → JSX をそのまま移す。TC-10 で選び方・代替テキスト・解説文が無いときの動き・拡大を固定する（今までテストが無かった）
- R4 クイズの問題画像の見え方が変わる（今は 1 枚を横幅いっぱい・代替テキスト「問題画像」→ 高さ最大 300・「問題画像 1」） → 設計確認メモで「解説画像と同じ並べ方」に決めた変更。代替テキストを使う既存のテスト・E2E は無い（2026-11-12 `grep -rn "問題画像\|解説画像" frontend/src e2e`）
- R5 TC-04 の差し替えが、組み立ての「最初」と「最後」以外の失敗を見ない → 組み立ての全体が同じ `with` の中にあることは 4-2 のコードで決まり、2 点（最初の解説の欄・最後の回の欄）で確かめれば間の欄も同じブロック。V2 で読んで確かめる
- R6 API の `explanation_images` に削除済み（`is_deleted=True`）の紐づけ・画像が入る → 今のプレビュー・次の問題の応答と同じ取り出し（`get_media_assets`）で、扱いを変えない（イシューの範囲外。画像の削除の API は紐づけを物理削除する〔`views.py:761` 付近〕）

## 9. 確定事項と自律判断
**イシューに明記されていること**:
- 回答の応答の `explanation_image` を `get_explanation_image_url()` で作る・`explanation_images` を応答に入れる（`ProblemDisplaySerializer` の作り方にそろえる）
- 「保存されたのに 500」を無くす（方式は計画で決める）・I158 の `update_fields`・I452 の 1 つのトランザクション・I166 の取得を崩さない
- 画面の選び方・並べ方はプレビューと同じ・解説文が無くても解説画像は出す・新しい形式の問題の画像も出す（設計確認メモ 2026-11-12）
- 共通にする作り（部品に切り出すか、プレビューと共有するか）は計画で決める
- `ProblemPreview.tsx` の見え方は変えない

**Claude が技術的に決めたこと（理由）**:
- 「保存されたのに 500」は、応答の組み立てを I452 のトランザクションの中に入れる形にした（保存の前に組み立てる案は採らない） — 応答の `session`・`session_stats`・`session_complete` は保存した後の値なので、保存の前には作れない。中に入れれば、組み立てのどこで失敗しても回答・集計・復習の予定がまとめて巻き戻る（AC2 を作りで満たす）。500 は返るが、記録と画面は食い違わない
- 解説の 3 つの欄を `AnswerExplanationSerializer`（ModelSerializer）にした — URL の作り方を他の経路と同じメソッドに寄せ、手書きの辞書で取り違える余地をなくす（根本原因の「作り方が 1 か所にまとまっていない」）。応答全体の serializer にはしない（回答の記録をサービス層へ移す #470 で応答の作りを整理するため、今は解説の部分だけ）
- 新しい形式の画像の応答の 2 行を `serialize_media_assets` にまとめた — 同じ 2 行の 5 つ目の写しを作らないため（既存の 4 か所も置き換える。中身は同じ）
- 画面は「選び方の関数（`utils/problemImages.ts`）」と「並べ方の部品（`components/ProblemImageList.tsx`）」に切り出し、プレビューも使う形にした（プレビューから写す案は採らない） — 「プレビューと同じ見え方」を作りで保証し、片方だけ変わるずれを防ぐ。#471（クイズの画面の分割）でも部品のまま使える。拡大の状態は親に残す（プレビューは問題と解説で 1 つの `ImageModal` を共有していて、部品ごとに持つと画面に拡大の部品が 2 つになる）
- 部品の置き場所は `frontend/src/components/`（`ImageModal.tsx`・`ProblemPreview.tsx` と同じ）、関数は `frontend/src/utils/`（`url.ts` と同じ）
- 部品の名前は `ProblemImageList`（MUI の `ImageList` を包む・問題の画像用）
- 画面のテストは、イシューの実装対象の表どおり `QuizSession.test.tsx` に追記する。プレビューの守りのテスト（TC-10）を新しく足す — プレビューにテストが無く、切り出しで見え方を変えないことを機械で確かめるため
- TC-04 の失敗の注入は pytest の `monkeypatch` で行う — 失敗の経路を起こすための差し替えで、本番のコードにテストのための口は作らない（通常の動きのテストに差し替えは使わない）
- 古い形式の欄の型を `string | null` にした — API は空のとき `null` を返す（`get_*_image_url` の戻り値）。`pickImageUrls` は `null`・`undefined` の両方を空として扱う
- 空の扱い: 画像の配列が空・欄が `null`／`undefined` はどれも「画像なし」。解説の枠は解説文か画像が 1 枚以上あるときに出す
- 手動確認のデータは dev DB に足し、確認の後に問題を 1 件ずつ論理削除する（物理削除は危険操作に当たるため行わない。確認用の科目・画像の行は dev DB に残る。CI は毎回新しい DB なので影響しない）

**要件適合性・業務ロジック**: 受け入れ条件を超える仕様の追加・変更は無い（応答に欄を 1 つ足す・画面の画像の選び方と並べ方を設計確認メモどおりにする）。閲覧範囲: 回答できる問題は I166 のまま（自組織かつ回の科目）。画像は答えた問題に紐づくものだけを返す。ステータス遷移: 回の `is_active` は書き戻さない（I158 の `update_fields` のまま）。境界の値: 画像なし・古い形式だけ・新しい形式だけ・両方・新しい形式 1／2／4 枚・解説文が空・組み立ての失敗を TC で確かめる。

**セキュリティ・BP**: 入力の検証は変えない（`SubmitAnswerSerializer` のまま）。認可は変えない（`IsAuthenticated`・`get_object()` の本人の回・I166 の問題の取得）。機密データは扱わない（画像の URL とファイル名・MIME・大きさは、問題管理と次の問題の応答に既に出ている欄）。XSS: 画像の URL は React の属性として入る（文字列の HTML の組み立てなし）。`getMediaUrl` は `http(s)://` で始まる URL をそのまま使うが、URL はサーバーが作る `/media/…`（利用者の入力ではない）。SQL は ORM のまま。依存の追加なし。bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える（新しいコードに該当なし見込み）。npm audit は high／critical を直す（依存を変えないので対象なし）。Django・DRF の推奨（ModelSerializer・`transaction.atomic`）と React の推奨（表示の部品化・純粋な関数）に沿う。

**P3/P5/P8 影響なし**: DB の形・外部 API・非同期処理・インフラ・依存は変えない（トランザクションの範囲の変更は 4-2・R1）。
**P6（性能・UX）**: 13 章に書く。
**P9 影響なし**: 個人情報・未成年データを新しく扱わない。テナントの閲覧範囲は変えない。

**台帳の残りの一覧**:
- 一覧 I224.md F9: 残す — ハーネスの項目で、このイシューの変更点と関係しない（`FILE=-`）
- 一覧 I223.md B1〜B4: 残す — bot の停止に関する項目で、このイシューの変更点と関係しない（`FILE=-`）
- 実装対象のファイルに当たる行は無し

## 13. 性能・UX設計
- 性能: 回答の応答に増えるクエリは画像の紐づけの 1 回（`select_related('asset')`）。次の問題の応答は変えない（もともと 2 回）。画像は `loading="lazy"`（プレビューと同じ）
- 読み込み中・空・エラー: 画像が無ければ何も描かない（枠も出さない。解説の枠は解説文があれば出る）。回答の送信の読み込み中・失敗（トースト「回答の送信に失敗しました」）は今のまま。画像の読み込みの失敗は `alt` の文字が出る（プレビューと同じ・新しい表示は足さない）
- 破壊的操作: 無し
- アクセシビリティ: 画像は `role="button"`・`tabIndex=0`・`aria-label`（「<種類> <n>枚目。クリックで拡大表示」）・Enter／スペースで拡大・フォーカスの枠（プレビューと同じ）。クイズの問題画像・解説画像は今はキーボードで拡大できないので、良くなる

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 古い形式の解説画像がある問題への回答が 200 で、`explanation_image` が `get_explanation_image_url()` と同じ（TC-01。直す前のコードで 500 の Red を実測） |
| V2 | 2 | 実験必須 | 応答の組み立てで失敗すると、QuizAnswer・回の集計・復習のカードと復習記録が残らない（TC-04 の 2 点の注入）。FG: 応答の組み立てを `with` の外に戻すと TC-04 が落ちる |
| V3 | 2 | 読んで可 | 4-2 の変更で、I158 の `update_fields`・I452 の 1 つのトランザクション・I166 の問題の取得・ほかの応答の欄の中身が変わらない（差分と、守りのテスト TC-06） |
| V4 | 3 | 実験必須 | 画面の選び方（新しい形式があれば新しい形式だけ・無ければ古い形式）と並べ方（1・2・3 列・拡大のキー操作）、解説文が無いときの解説画像、問題文の画像（TC-07〜TC-09）。プレビューの見え方が変わらない（TC-10） |
| V5 | 1 | 読んで可 | 応答に入る画像が、答えた問題に紐づくものだけ（`get_media_assets` は `problem.media_links`）で、他の問題・他の組織の画像の経路が無い |

## 計画変更記録
- plan-review（20261112_1559・OK）の Warning 2 件への対応: 手動テスト No.1・No.5 のデータ作成・後片付けのコードの渡し方を「スクラッチパッドのファイル → `docker compose cp` で `/tmp/` → `manage.py shell --command` で 1 コマンドずつ」に具体化し、No.1 のあいまいな「`GET /api/quiz/` 相当の確かめ」を削った（No.2 で確かめる）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）

## レビュー結果
- [20261112_1559 判定: ✅ 完了](../../reviews/I472_plan_review_20261112_1559.md)
（plan-review の後に追記）
