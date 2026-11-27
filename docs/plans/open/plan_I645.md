# I645 計画書: 選択肢の記号（ア・イ・ウ・エ）と選んだ誤答の印

## 基本情報
- **計画書ID**: plan_I645
- **関連イシュー**: #645
- **Draft PR**: #648
- **作成根拠資料**: docs/issues/open/I645.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I645_review.md
- **作成日**: 2026-11-27

## 1. 背景/目的
- IPA の過去問のように、問題文や図が「ア」「イ」などの記号で選択肢を指す問題を、記号と本文が分かれた見やすい形で出す
- 答えた後に、自分が選んだ誤答が分かるようにする（今は正解に緑の印が付くだけで、選んだ誤答は他の選択肢と同じ灰色）

### 調査結果
**原因の概要**: 選択肢の画面は本文だけを出していて、記号を付ける仕組みが無い。誤答の赤い文字の指定はあるが、答えた後に選択肢を押せなくする（disabled）ときの灰色の指定のほうが強く、上書きされている。

**詳細**:
1. 記号: クイズの画面は `{choice.text}` だけを出す（`frontend/src/pages/QuizSession.tsx:555`・`:599`）。問題管理のプレビュー（`frontend/src/components/ProblemPreview.tsx:118`）と AI の問題作成の画面（`frontend/src/components/AIQuestionGenerator.tsx:383`）は `String.fromCharCode(65 + index)` で「A. 」を付ける。記号の作り方が 2 か所に別々に書かれている
2. 並び: 選択肢はいつも `Choice.Meta.ordering = ['order', 'id']`（`backend/problems/models.py:143-144`）の順で返り、backend・frontend とも並べ替える処理は無い（`shuffle`・`random` を grep・2026-11-27）。だから画面が順番から付けた記号は、問題文が指す記号と一致する。並びの入れ替えは後続の I647（#647）で、記号は表示の順に付ける決まりのまま
3. 誤答の色: MUI 5 の `FormControlLabel` は、ラベルに `[& .MuiFormControlLabel-label]: { [&.Mui-disabled]: { color: text.disabled } }` を持つ（コンテナの `node_modules/@mui/material/FormControlLabel/FormControlLabel.js:74-77` を 2026-11-27 に読んだ）。セレクタは `.<root> .MuiFormControlLabel-label.Mui-disabled`（クラス 3 つ）で、画面の `sx` の `& .MuiFormControlLabel-label`（クラス 2 つ）より強い。答えた後は `disabled={showResult}`（単一選択は `FormControlLabel`、複数選択は `Checkbox`。`FormControlLabel` は部品の disabled を引き継ぐ・同ファイル `:116`）なので、正解の緑の文字も誤答の赤い文字も灰色に負ける。イシューの根本原因 2 の「詳しい優先の仕組みは未特定」はこれで特定した
4. 誤答の印: 正解には `CheckCircleOutline` を出すが、誤答には何も出さない（`QuizSession.tsx:556-560`・`:600-604`）。`Cancel` は同じファイルで既に import されている（`:23`・結果の `Alert` のアイコンに使う）
5. 既存のテスト: `getByLabelText('選択肢1')`（`frontend/src/pages/__tests__/QuizSession.test.tsx:132`・`:287`、`QuizSession.source.test.tsx:85`・`:108`）・`getByLabelText('選択肢A')`（`QuizSession.review.test.tsx:81`）・`getByText('A. 正解')`（`frontend/src/components/__tests__/ProblemPreview.test.tsx:99`）が選択肢の名前を使う。E2E（`e2e/tests/quiz-session.spec.ts`・`auth.spec.ts:112`）は `data-testid="choice-option"` で探すので名前の変化に左右されない
6. E2E の問題（`backend/accounts/management/commands/seed_e2e.py:166-175`）: 選択肢は 2 つで、1 つ目（`order=0`）が「正解の選択肢」、2 つ目（`order=1`）が「不正解の選択肢」
7. テーマ: `frontend/src/contexts/ThemeContext.tsx` は MUI の既定の色（light の `error.main` は `#d32f2f`、`success.main` は `#2e7d32`）。白の背景との明るさの比はどちらも 4.5:1 以上（`docs/runbooks/ux-rules.md` §6）
8. 選択肢の数に上限は無い（`backend/problems/serializers.py:232` の `validate_choices` は数を限らない）
9. develop の最新の CI（E2E Tests・CI）は成功（`gh run list --branch develop`・2026-11-27）

## 2. 受け入れ条件
- [ ] クイズの画面の選択肢（単一選択・複数選択）に、上から順に「ア・イ・ウ・エ」（5 個目からはオ・カ・キ…）の記号が、本文と別の要素として出る（区切りの文字に頼らない）
- [ ] 問題管理のプレビューと AI の問題作成の画面も同じ記号を出し、「A. 」は出ない
- [ ] 誤答を選んで答えると、選んだ選択肢に赤い×の印（`Cancel`）が付き、その文字が赤（`error.main`）になる。灰色（disabled の色）にならない
- [ ] 答えた後、正解の選択肢には今までどおり緑のチェック（`CheckCircleOutline`）が付き、その文字は緑（`success.main`）になる。正解でも選んだ誤答でもない選択肢は今までどおり灰色
- [ ] 選択肢が記号の表（46 個）より多いときも画面が壊れず、表を超えた分は数字（47・48…）で出る
- [ ] 記号の無い今までの問題の表示（並び・押し方・答えた後の流れ）が崩れない
- [ ] 勉強用のワークツリーの 25 問（本文の先頭に「ア．」）の直し方が記録（この計画書の「## 16. 今の 25 問の直し方」）に書いてある
- [ ] Backend・DB・API は変わらない

## 3. 影響範囲
- Backend: なし（`backend/problems/models.py` は並び順の根拠として読むだけ）
- Frontend: `frontend/src/pages/QuizSession.tsx`・`frontend/src/components/ProblemPreview.tsx`・`frontend/src/components/AIQuestionGenerator.tsx`・新しい `frontend/src/utils/choiceLabel.ts`・新しい `frontend/src/components/ChoiceLabelText.tsx`・新しい `frontend/src/components/QuizChoices.tsx`・テスト（下の 6）・E2E（`e2e/tests/quiz-session.spec.ts`）
- DB: なし
- Config/Infra: なし（依存の追加なし）

## 4. 変更点一覧（具体）

### 修正アプローチ
- 記号を作る処理を 1 か所（`utils/choiceLabel.ts`）にまとめ、記号と本文を並べて出す小さな部品（`ChoiceLabelText`）を 3 つの画面で使う。記号の作り方と見た目を 1 か所で決めるので、画面ごとにずれない
- クイズの画面の選択肢の部分（単一選択・複数選択の 2 つの塊）を `QuizChoices` の部品に切り出し、そこで記号・正解の印・誤答の印・色を出す。`QuizSession.tsx` は 721 行あり、規約の「200 行を超えたら分ける」（React 規約 §4）に照らして、今回書き直す部分だけを切り出す（ほかの部分は動かさない）
- 色は、MUI の disabled の指定と同じ強さ以上のセレクタ（`& .MuiFormControlLabel-label.Mui-disabled`）にも同じ色を書いて、灰色に負けないようにする。`!important` は使わない

### 4-1. `frontend/src/utils/choiceLabel.ts`（新規）
何を達成するか: 選択肢の順番（0 から）から記号を出す、ただ 1 つの場所。
```ts
/** 選択肢の記号（I645）。IPA の過去問にそろえ、五十音の順に ア・イ・ウ・エ… と付ける */
export const CHOICE_LABELS: readonly string[] = [
  'ア','イ','ウ','エ','オ','カ','キ','ク','ケ','コ','サ','シ','ス','セ','ソ','タ','チ','ツ','テ','ト',
  'ナ','ニ','ヌ','ネ','ノ','ハ','ヒ','フ','ヘ','ホ','マ','ミ','ム','メ','モ','ヤ','ユ','ヨ',
  'ラ','リ','ル','レ','ロ','ワ','ヲ','ン',
];
/** 順番（0 から）の記号。表を超えたら 1 から数えた数字を返す */
export const choiceLabel = (index: number): string => CHOICE_LABELS[index] ?? String(index + 1);
```

### 4-2. `frontend/src/components/ChoiceLabelText.tsx`（新規）
何を達成するか: 記号と本文を別の要素で並べ、区切りの文字なしで見分けられるようにする。
- props: `{ index: number; text: string }`
- 形: 横並びの `Box component="span"`（`display: 'inline-flex'`・`alignItems: 'baseline'`・`gap: 1.5`）。記号は `Box component="span"`（`fontWeight: 700`・`minWidth: '1.5em'`・`flexShrink: 0`）、本文はその後ろの `span`。色は親から受け継ぐ（クイズの画面で正解・誤答の色が記号にも付く）
- 記号の要素に `data-testid` は付けない（テストは見える文字で探す）

### 4-3. `frontend/src/components/QuizChoices.tsx`（新規）と `frontend/src/pages/QuizSession.tsx`
何を達成するか: クイズの選択肢に記号を付け、答えた後に正解・選んだ誤答を形と色で分けて出す。
- `QuizSession.tsx:540-620` の単一選択（`RadioGroup`）と複数選択（`FormGroup`）の塊を `QuizChoices` に移す。`QuizSession.tsx` はその場所で `<QuizChoices problemType={...} choices={...} selectedChoices={...} onSelect={handleChoiceSelect} showResult={showResult} correctChoiceIds={...} />` を呼ぶ
  - `correctChoiceIds`: `result?.correct_choices` の id の配列（今の `result?.correct_choices?.some((c: any) => c.id === choice.id)` と同じ判定を、部品の外で一度だけ作る。`any` はやめ、`frontend/src/types/quiz.ts:65` の `QuizResult.correct_choices?: Choice[]` から取る。`QuizChoices` の props の選択肢の型も `types/quiz.ts` の `Choice` にそろえる〔`services/types.ts` の同名の型は使わない〕）
  - 単一選択の「選んだ誤答」: 選んだ選択肢で、正解の id に入っていないもの（今の `!result?.is_correct` と同じ結果。複数選択と同じ判定にそろえる）
  - 複数選択の「選んだ誤答」: 今と同じ（選んで、正解の id に入っていないもの）
- 各選択肢の表示:
  - ラベル: `<ChoiceLabelText index={i} text={choice.text} />` の後ろに、正解なら `CheckCircleOutline`（`color: 'success.main'`・`fontSize: 20`・今と同じ）、選んだ誤答なら `Cancel`（`color: 'error.main'`・`fontSize: 20`）
  - 色: 正解は `success.main`、選んだ誤答は `error.main` を、`'& .MuiFormControlLabel-label, & .MuiFormControlLabel-label.Mui-disabled'` の両方に書く。どちらでもない選択肢は色を書かない（disabled の灰色のまま・今と同じ）。太さは正解だけ 600（今と同じ）
  - 名前: 入力（`Radio`・`Checkbox`）に `inputProps={{ 'aria-label': `${choiceLabel(i)} ${choice.text}` }}` を付ける。読み上げで記号と本文が分かれて聞こえ、テストで名前が決まった形になる（ラベルの中の要素の並びから名前を作らせると、要素の間に空白が入るかが表示の形に左右される）
  - 今の `data-testid="choice-option"`（単一選択の `Box`）は残す（E2E が使う）。複数選択の `Box` には今も付いていないので、付け方は変えない
  - `key` は今と同じ `choice.id`
- 印のアイコンは今の正解の印と同じく飾り（読み上げない・MUI の既定）。正誤の結果は今の結果の `Alert`（`QuizSession.tsx:629-634`・「正解です！」「不正解です」の文字とアイコンあり）が伝える

### 4-4. `frontend/src/components/ProblemPreview.tsx`
何を達成するか: プレビューの記号をクイズの画面とそろえ、「A. 」と本文の記号が並ばないようにする。
- `:118` の `{String.fromCharCode(65 + index)}. {choice.text}` を `<ChoiceLabelText index={index} text={choice.text} />` に置き換える（`Typography` の中に置く。枠・正解の Chip は今のまま）

### 4-5. `frontend/src/components/AIQuestionGenerator.tsx`
何を達成するか: AI の問題作成の画面の記号もそろえる。
- `:383` の `{String.fromCharCode(65 + choiceIndex)}. {choice.text}` を `<ChoiceLabelText index={choiceIndex} text={choice.text} />` に置き換える（後ろの `' ✓'`・色・太さは今のまま）。`key={choiceIndex}` はこのイシューでは変えない（下の 9 の判断）

### 4-6. テスト
- 新規 `frontend/src/utils/__tests__/choiceLabel.test.ts`（TC-01）
- 新規 `frontend/src/components/__tests__/QuizChoices.test.tsx`（TC-02〜TC-06）
- 既存の名前の直し: `QuizSession.test.tsx:132`・`:287`、`QuizSession.source.test.tsx:85`・`:108` の `getByLabelText('選択肢1')` → `getByLabelText('ア 選択肢1')`、`QuizSession.review.test.tsx:81` の `getByLabelText('選択肢A')` → `getByLabelText('ア 選択肢A')`、`ProblemPreview.test.tsx:99` の `getByText('A. 正解')` → 記号の「ア」と本文の「正解」で探す形（TC-07）
- `frontend/src/components/__tests__/ProblemPreview.test.tsx` に記号の TC（TC-07）
- E2E: `e2e/tests/quiz-session.spec.ts` に「誤答を選ぶと、その選択肢に×の印と赤い文字が付く」（TC-08）。色の強さの勝ち負けは本物のブラウザでしか正しく測れないので、ここで確かめる

## 5. 実装手順（ステップ）
1. `utils/choiceLabel.ts` と `ChoiceLabelText` を作る → TC-01
2. `QuizChoices` を作り、`QuizSession.tsx` の選択肢の塊を置き換える。記号・印・色・名前を入れる。既存のテストの名前を直す → TC-02〜TC-06・TC-09（ステップ 1 の後）
3. `ProblemPreview.tsx`・`AIQuestionGenerator.tsx` を `ChoiceLabelText` に置き換え、プレビューのテストを直す → TC-07（ステップ 1 の後。ステップ 2 と並行してよい）
4. E2E を足す → TC-08（ステップ 2 の後）
5. 画面で確かめる（Playwright MCP・手動テスト No.1〜No.4）→ 手動テスト文書（ステップ 2〜3 の後）

## 6. テスト計画
### 自動
- テストのレベル: 記号の作り方はユニット（TC-01）、部品の出し分けは React Testing Library（TC-02〜TC-07）、色が disabled に勝つことは E2E（TC-08。jsdom はセレクタの強さによる上書きを本物のブラウザと同じには計算しないので、部品のテストでは色の勝ち負けを判定にしない）
- 再発防止: 誤答の色が灰色に負けた不具合は TC-08 が本物のブラウザで止める
- 認可・テナントの境界: 変更なし（API を変えない）ので追加しない
- 決定論ゲート: なし（守る決まりはテストが CI で毎回確かめる。「A. 」が残っていないことは TC-07 と画面で見る）
### 手動
- 画面の見た目（記号と本文の間・赤と緑の見え方・ダークモード・スマホの幅）を Claude が Playwright MCP で確かめる（`docs/tests/open/I645_manual_test.md`）

## 7. ロールバック
- この PR を revert する（画面だけの変更。DB・API は変えない）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 入力の名前を `aria-label` で決めると、ラベルの文字と名前が食い違う変更が後で入りうる | 名前は `choiceLabel(i)` と `choice.text` から作り、見える文字と同じ材料を使う。TC-02 で名前を確かめる | 回避 |
| R2: 色のセレクタが MUI の版の更新（#561 の MUI 9）で効かなくなる | TC-08（E2E）が本物のブラウザで色を確かめ、版を上げた PR で落ちる | 回避 |
| R3: 本文に「ア．」と書いた 25 問は、直すまで「ア」「ア．本文」と記号が二重に見える | grill-me で受け入れると決めた。直し方を「## 16」に書く | 受け入れ |
| R4: 選択肢の塊を切り出すと、今の押し方（単一選択は押してすぐ送る・複数選択は「回答する」で送る）が変わる | 押す処理（`handleChoiceSelect`）は `QuizSession.tsx` に残し、部品は呼ぶだけにする。既存のテスト（`QuizSession.test.tsx` の即時送信・「回答する」）と TC-09 で確かめる | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 全問で、画面が順番から「ア・イ・ウ・エ」を付ける。データ・API・DB は変えない。問題ごとの設定は持たない
- プレビューと AI の問題作成の画面の「A. 」も同じ記号にそろえる
- 今の 25 問の「ア．」はアプリで削らず、直し方を記録に書く（直すのはこのイシューの外）
- 選んだ誤答に `Cancel` の赤い印と `error.main` の赤い文字。正解は今どおり緑のチェック。「あなたの回答」の文字は足さない
- 5 個目より後は五十音の順に続ける
Claude が決めた（技術的な選択と理由）:
- 記号の表は五十音の 46 字（ア〜ン・ヰヱは除く）で、超えたら数字 — 理由: 選択肢の数に上限が無い（調査結果 8）。46 を超える選択肢は現実には無いが、表の外で `undefined` を出さないため。仮定で決めた・技術的
- 記号を `utils/choiceLabel.ts`、見た目を `components/ChoiceLabelText.tsx` に置く — 理由: React 規約 §2 の置き場所（小さな関数は `utils/`・部品は `components/`）。2 か所に書かれていた `String.fromCharCode` を 1 か所にする。仮定で決めた・技術的
- 選択肢の塊を `components/QuizChoices.tsx` に切り出す — 理由: React 規約 §4（200 行を超えた部品は分ける）。書き直す部分だけを切り出し、押す処理は残す（R4）。仮定で決めた・技術的
- 色は `& .MuiFormControlLabel-label.Mui-disabled` にも書く（`!important` は使わない） — 理由: 調査結果 3 の MUI の指定と同じ強さで、後に書いた `sx` が勝つ。`!important` はテーマの上書きを難しくする。仮定で決めた・技術的
- 正解の文字も緑になる（今は灰色に負けて灰色） — 理由: 今のコードが意図していた色（`success.main`）で、同じ原因の直しで戻る。AC の「今までどおり」は緑の印のことで、文字の色は意図に戻すだけ。UI の見た目の変化はあるが、もともとの意図と grill-me の「正解は今どおり緑」に沿うので、価値判断の新しい仮定ではない
- 単一選択の「選んだ誤答」の判定を、`!result.is_correct` から「正解の id に入っていない」にそろえる — 理由: 単一選択では結果は同じで、2 つの判定を 1 つにできる。仮定で決めた・技術的
- 入力に `aria-label`（`ア 選択肢の本文`）を付ける — 理由: 読み上げで記号を本文と分けて伝える（React 規約 §13）。名前の作られ方を表示の形に頼らない（4-3）。仮定で決めた・技術的
- 印のアイコンは飾りのまま（読み上げの文字を足さない） — 理由: 今の正解の印と同じ扱い。正誤は結果の `Alert` が文字で伝える。「あなたの回答」の文字は足さないと grill-me で決めた。仮定で決めた・技術的
- `AIQuestionGenerator.tsx` の `key={choiceIndex}`（添字の key・React 規約 §4 に反する）は直さない — 理由: AI が作った問題の選択肢には id が無く、並べ替えも消しもしない一覧で害が無い。直すのは #510 などの規約の移行の範囲。仮定で決めた・技術的
- 一覧 `docs/reviews/backlog/I224.md` F9: 残す — 理由: ハーネスの話で、このイシューの画面と関係しない
- 一覧 `docs/reviews/backlog/I223.md` B1〜B4: 残す — 理由: bot の停止中の後始末で、このイシューと関係しない
- 要件適合性: 計画は AC の範囲だけ。テナント・ステータスの変化は無い（画面の表示だけ）
- セキュリティ: 変更は表示だけ。`choice.text` は React がそのまま文字として出す（`dangerouslySetInnerHTML` を使わない・React 規約 §11）。入力の検証・認可・個人情報の扱いは変えない。依存の追加なし。bandit・npm audit の基準（bandit MEDIUM 以上・npm audit high/critical）は CI のまま。セキュリティ影響なし
- P3/P5/P8 影響なし（DB・外部 API・非同期処理・新しい費用は無い）
- P9 影響なし（個人情報・テナントのデータの扱いは変えない）
- 設計品質: Fat な部品を分ける方向（`QuizChoices`）。`any` を減らす（`correct_choices` の判定）。色はテーマの値（`success.main`・`error.main`）で書き、色の値を直接書かない。記号の表は定数で 1 か所
Danger Ops（有無。有りのときは 影響範囲・代替案・ロールバック・実行コマンド を書く。条件と手順は docs/runbooks/danger-ops.md）:
- 無（DB・データを変えない。25 問の直しはこのイシューの外）

## 13. 性能・UX設計
- 読み込み中・失敗・空の表示は変えない（選択肢の塊の中だけの変更）
- 削除などの壊す操作は無い
- 性能: 記号は配列の参照だけ。N+1 などの懸念は無い
- アクセシビリティ: 正誤は色に加えて形の違うアイコン（✓ と ×）で示す（`docs/runbooks/ux-rules.md` §6）。記号は太字で、本文と間を空けて並べる。明るさの比は MUI の既定の `success.main`・`error.main` で 4.5:1 以上（調査結果 7）。ダークモードとスマホの幅（360px）で崩れないかを手動テストで見る

## 14. 学習効果設計
- 品質基準 C1（学習効果）の「つまずき検知」に関わる。答えた直後に、自分の誤答と正解を並べて見られるので、何を取り違えたかを振り返れる
- 効果の指標は新しく測らない（表示だけの変更。誤答の記録は今までどおり `ProblemAttempt` に残る）

## 16. 今の 25 問の直し方（このイシューの外で行う）
- 対象: 勉強用のワークツリーの DB の、I586 で登録した 25 問の選択肢（リポジトリには問題のデータは無い）
- 直すこと: 選択肢の本文の先頭の「ア．」「イ．」「ウ．」「エ．」（全角のカナ 1 字と全角の句点「．」）を外す。画像の選択肢「ア．画像のア」は「画像のア」にする（記号は画面が付ける）
- やり方（どちらか）:
  - 画面: 問題管理で 25 問を 1 問ずつ編集し、各選択肢の先頭の 2 字を消して保存する
  - 一括: 勉強用のワークツリーの backend で `python manage.py shell` を開き、25 問の選択肢のうち本文が正規表現 `^[ア-ン]．` で始まるものだけ、その 2 字を外して保存する。データを書き換える操作なので、先に `bash scripts/claude/db-backup.sh` で控えを取り、Danger Ops の扱い（`docs/runbooks/danger-ops.md`）に従う
- 直した後の確かめ: クイズの画面で記号が 1 つだけ（「ア　本文」）に見えること

## 計画変更記録
- 2026-11-27 plan-review: 計画書の記載: 結果の表示を「Chip」・複数選択の行の取り方が無い・手動 No.4 の基準が主観 → 採った方法: 結果の表示を `Alert` に直し、`QuizChoices` の型を `types/quiz.ts` にそろえると明記。TC-04・TC-06 の行は名前の入力から `closest('label')` で取る・TC-07 の置き換えの式・TC-08 の失敗の注入を手元で流せないときの代わり（Playwright MCP で色を測る）・手動 No.4 の切り替え手順と色の値と明るさの比を書いた — 理由: 計画レビューの Warning 4 件・Info 2 件への対応。計画レビューのやり直し: 不要（findings への対応の追記だけ）

## レビュー結果
- [20261127_1931 判定: ✅ 完了](../../reviews/I645_plan_review_20261127_1931.md)
