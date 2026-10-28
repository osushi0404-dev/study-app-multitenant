# I211 レビュー: ハーネスのテストの python・PyYAML・pre-commit の版を CI と手元でぴったり揃える

## 変更概要
- ハーネスのテストの python の道具の版の正を uv の公式のファイル（`scripts/claude/tests/.python-version`・`uv.lock`・`pyproject.toml` の `required-version`）にし、手元も CI も `bash scripts/claude/tests/run-all.sh` が uv の環境で流す

## 変更点
- 新規 `scripts/claude/tests/pyproject.toml`・`.python-version`（3.11.18）・`uv.lock`（PyYAML 6.0.3・pre-commit 4.7.0）・`test_i211_version_pin.sh`
- `run-all.sh`: uv の環境の外なら `uv run --locked` で流し直す・引数で一部のテストを流す
- `check-tools.sh`・`required-tools.txt`: 版の列を `-`／`lock`（正とぴったり）にし、`--pip-specs` をやめた。出力が空のときの字下げの空行を出さない
- `.github/workflows/ci.yml`（Harness Tests）: setup-python と pip install をやめ、`astral-sh/setup-uv@v10.3.3`（`version-file: scripts/claude/tests/pyproject.toml`）に
- `test_i204_tool_sync.sh`: 4 列の一覧・CI が版の正だけを読むことの確かめ（install の検出の強化・setup-uv の版の形）
- `docs/runbooks/onboarding.md`: 初回の準備・一部のテストの流し方・版を上げる手順
- `docs/reviews/backlog/I204.md`: F2・F3・F5 を同梱して消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/ci.yml`（harness-tests ジョブ）・手元の開発環境（pipx の uv）

## テスト結果
- 自動: 決定論ゲート 4 本 exit 0。CI 全ジョブ pass（3.11.18: run 40717058976／3.12.3: run 40732184953・どちらも Harness Tests `run-all: pass=48 fail=0`）。3.12.3 の差分は組み込みの /security-review を直接実行して指摘なし・敵対的レビュー 2 周目 OK。基本レビュー OK（止める指摘 0・Low 6）・敵対的レビュー OK（未検証 0・新しい Critical/High 0）
- 手動: No.1〜No.4 OK（3.12.3 でやり直し・すべて Claude・Human の項目なし）

## 計画との差分
- あり: 計画変更記録 1〜3（失敗したテストの案内の形・ロックの版の記録・/simplify の整理）と fix-loop 2 回（setup-uv の版を細かい版のタグで書く・FG-K2 の `--offline` を外す）。方式・範囲・受け入れ条件は変えていない

## ロールバック
- PR を revert。手元の uv は `pipx uninstall uv`

## 振り返り

### I211 振り返り（かんたんなまとめ）

#### 良かった点
- 手元と CI の版がぴったり同じになった（python 3.11.18・PyYAML 6.0.3・pre-commit 4.7.0・uv 0.13.6）。CI のログと手元の出力が同じ文字列になることまで確かめた（理由: 版の正を uv の公式のファイルにし、手元も CI も同じ入口 `run-all.sh` から流す形にしたため）
- 計画の前に、uv の動きを小さな試し（スパイク）で 8 点確かめたので、実装中に方式の作り直しが起きなかった
- 「失敗の理由まで見る」テストが、CI でネットワークが使えないという別の理由で落ちたのを合格にしなかった（偽の合格を防げた）
- 途中でユーザーから出た「Actions の承認は必須か」を、同じ目的の既存イシュー（I200）にまとめて入れ、I211 の範囲を広げなかった

#### 今回の問題への直接の対処
- CI が 2 回落ちた。1 回目は、uv の公式の GitHub の部品（setup-uv）に「v10」という大きな版の目印が無かったため。2 回目は、整理の段階で付けた「ネットワークを使わない」指定が、キャッシュの無い CI で効かなかったため。→ どちらも fix-loop で直した（細かい版 `v10.3.3` で書き、書き方をテストで確かめる／その 1 か所の指定を外す）。どちらも CI がすぐに捕まえ、手戻りは小さかった
- テストを直に流すと OS の python のまま動く道が残っている（計画で残余リスクとして残した）。→ 「流すテストを選ぶ」仕組みを作る I201（#337）に、`run-all.sh` に渡す形にするよう申し送った
- 第三者の GitHub の部品を、タグではなくコミットの番号で固定するかは、リポジトリ全体の方針の話。→ これから起票する「Dependabot の点検」のイシューの候補に入れた（起票コマンドに追記）

#### 同じ問題を次回から防ぐ改善
- 新しく足す改善は無し。どちらの CI の失敗も、CI とテストがその場で捕まえ、直すのも 1 回で済んだ。手順や確認項目を足しても、失う時間のほうが大きい（「その場で捕まって手戻りの小さい見逃しには手順を足さない」方針）

#### マージ前の見直し（python を 3.12.3 に揃え直した回）で追加
- 良かった点: マージ前にユーザーが「BP として適切か」を問い、揃える python を見張りが実際に動く版（3.12.3）に直せた。版を 1 か所に置いた仕組みのおかげで、変更は版の数字 2 行とロックファイルの作り直しだけで済んだ。CI も手元も、OS にもともと入っている python 3.12.3 そのものを使うようになった
- 今回の問題への直接の対処: 最初に揃える版を選んだとき、「アプリが 3.11 だから」と決め、ハーネスのテストが確かめる見張りがどこで動くかを考えに入れていなかった。→ マージ前の PR に入れて直した（計画変更記録 4・5）
- 同じ問題を次回から防ぐ改善: レビューの仕組みの穴を見つけた。組み込みのセキュリティレビューが動かなかった回の記録を、やり直しのレビューが「もう見た」起点として使い、セキュリティレビューを一度も通さずに OK を出した（今回は私が気づいて手で補った）。→ 判定の仕組みの直しなので、I212（#358）として起票した（次のハーネスの作業で最優先）

### I211 振り返り（詳細）

#### 良かった点
- 版の正を uv の公式のファイル（`.python-version`・`uv.lock`・`required-version`）に置き、uv 自身の `--locked`・`required-version` と `check-tools.sh`・`test_i204_tool_sync.sh` の 3 段でずれを止める形にできた（決定論のチェックで担保）
- スパイク 8 点（計画書 1 の調査結果）で、実装中に方式の変更が起きなかった
- FG-K2 が失敗の理由（`update`）まで見ていたので、CI の別の理由の失敗を合格にしなかった
- ユーザーの要望（Actions の承認の絞り込み）を既存の I200（#335）に同梱し、I211 の範囲を守った

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | setup-uv は細かい版のタグだけを出し、`v10` の動くタグが無い。スパイクは action.yml の入力だけを見て、タグの有無を見ていなかった | fix-loop 1 で `@v10.3.3` にし、`ci_check` に版の形の確かめ＋失敗注入を足した（済） |
| C2 | 予期しない問題 | /simplify で足した `--offline` が、新しいキャッシュの CI では解決し直しに使えない | fix-loop 2 で FG-K2 だけ外した（済） |
| C3 | 技術選択 | テストを直に流すと OS の python のまま動く（計画書 R3） | I201（#337）に同梱（コメント済み: `run-all.sh <選んだテスト>` に渡す） |
| C4 | セキュリティ（残余リスク） | 第三者の action をコミットの SHA で固定していない（設計レビューの Medium → 細かい版のタグにしたので台帳では Low・F6） | ユーザーが起票予定の Dependabot の点検のイシューの候補 ⑦ に入れた（起票コマンドに追記） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | プロセス（判定の仕組み） | 差分のレビューの起点を「最後にレビューした記録」で選び、「最後に合格した記録」で選んでいない。`OFFICIAL_SECURITY: FAILED`・HIGH の記録もやり直しの起点になり、範囲 0 本で OK が出た（`docs/reviews/I211_code_review_20261029_0155.md` → `_0204.md`） | 差分のレビューの起点を合格した記録に限り、失敗した記録を起点にしないことを失敗注入つきの決定論のテストで固定する（I212 #358 として起票・次のハーネスの作業で最優先） | `scripts/claude/code-review.sh`・`scripts/claude/gate-check.sh`（必要なら）・`scripts/claude/tests/`・`.claude/skills/review-gate/SKILL.md` |
| C5 | 技術選択 | 揃える python を選ぶとき、ハーネスのテストが確かめる見張りの実際の動作環境（OS の python）を見ず、アプリ（Docker）に合わせた | マージ前に 3.12.3 に直した（計画変更記録 4・5・済）。設計確認の観点の追加は見送り（ユーザーの見直しでマージ前に捕まり、直しも小さかった） | — |

見送り（2.7 の 4 問）:
- 「第三者の action を足すときにタグの有無を確かめる」手順を計画レビューの観点に足す案 → 見送り。CI がその場で捕まえ（3 秒で失敗）、直しは 1 回で済んだ。手順を足すと毎回のコストがかかる。決定論のチェック（版の形の確かめ）は C1 で足した
- 「整理（/simplify）で足したキャッシュ・ネットワークに頼る指定を、新しい環境で確かめる」手順を足す案 → 見送り。CI と失敗の理由まで見るテストがその場で捕まえた
- 「承認画面が出る操作を事前に予告する」の徹底（1 回目の ci.yml の編集で予告しなかった）→ 見送り。すでにある決まり（メモリ）の守り漏れで、I200 で Actions の確認そのものを絞るので、出る場面が減る

設計ルール昇格: 今回の設計レビュー・組み込みの /security-review で見つかった問題の型（第三者の action の固定）は、Dependabot の点検のイシューで方針として扱うので、計画レビューの観点には昇格しない。
残余リスク処遇: 設計レビューの Medium（setup-uv の浮動タグ）→ 細かい版のタグにして縮小・台帳 F6（Low）・SHA 固定は Dependabot の点検のイシューの候補。High 以上は無し。

## 自律判断の記録
- [plan] 版の正を uv の公式のファイルにし、入口の `run-all.sh` が uv の環境で流し直す形にした — 公式の仕組みがずれを止め、許可ルールを変えずに済む（計画書 9 の D1・D2）
- [plan] 手元の uv は Claude が `pipx install uv==0.13.6` で入れる — 設計確認メモの「ユーザーが入れる」よりユーザーの手間が少なく、pipx で戻せる（D3）
- [plan] `run-all.sh` に引数で一部のテストを流す形を足した — 一部のテストも同じ版の環境で流すため（D6）
- [plan-review] Warning（setup-uv が runner で required-version と python を読めるか未実証）は計画のステップ 3・手動 No.1・R1 のまま進める — 実際の runner でしか確かめられず、確かめる手順と失敗時の対応が計画にある
- [plan-review] Warning（setup-uv を SHA に固定していない）は直さない — 既存の `actions/*@v4` と同じ運用。SHA 固定はリポジトリ全体の方針として扱う
- [plan-review] Info（`OK: uv uv 0.13.6` の名前の重複表示）は直さない — 既存の git の行（`OK: git git version`）と同じ表示で、見た目だけ
- [design-security-review] Blocker・High なし。Medium（setup-uv の浮動タグ）は残余リスクとして retro へ — 既存の action と同じ運用で、harness-tests は秘密情報を持たない
- [implement] 手元に `pipx install uv==0.13.6` で uv を入れた — 計画の D3 どおり（`pipx uninstall uv` で戻せる）
- [implement] /simplify の点検（4 観点）で、テスト専用の抜け道（`pyproject.toml` が無ければ流し直さない）を消し、場所の書き方・変数の渡し方・K1・`--offline`・runbook を整理した（計画変更記録 3）。見送り: 版の確かめを uv に任せて `check-tools.sh` の lock の行をやめる案（AC4 の止まり方と CI のログでの版の確認〔手動 No.1〕が無くなる）／install の検出をやめる案（AC7 と I204 の敵対的レビューの指摘に反する）／setup-uv の `with` を緩める案（版の正を迂回する入力を通さないため今の固定のまま）／テストの一時のリポジトリの準備を共通にする案（テストのファイルは自分の中で完結させるのがこのリポジトリの書き方）／CI で python もキャッシュする案（数秒のための ci.yml の変更は範囲外）
- [fix-loop] CI の失敗（setup-uv に `v10` の動くタグが無い）を案 A（細かい版 `v10.3.3` で書く＋`ci_check` で版の形を確かめる）で直した — 配布元の版の付け方どおりで粗く確実。SHA 固定（案 B）はリポジトリ全体の方針として残余リスクのまま（診断レビュー PASS: docs/reviews/I211_fix_diagnosis_review_20261029_0014.md）
- [fix-loop] CI の FG-K2 の失敗（`--offline` で別の理由の失敗になった）を、FG-K2 だけ `--offline` を外して直した — 確かめたい失敗（ロックのずれ）を確実に起こすため（診断レビュー PASS: docs/reviews/I211_fix_diagnosis_review_20261029_0029.md）
- [fix-loop] ユーザーの指示（Actions の承認は秘密・個人情報が出うる書き換えだけに）を I200（#335）の設計確認メモ・解決方針・受け入れ条件に同梱した — I200 が「見張りの確認を本当に危ない操作だけに絞る」イシューで目的が同じ。I211 の範囲（版揃え）は変えない
- [retro] 台帳の残り: F1〜F6 と敵対的レビューの Low（A1）は `docs/reviews/backlog/I211.md` へ（後続イシュー行きは 0 件）
- [retro] 改善案の振り分け: C1・C2 は直した（fix-loop）／C3 は I201（#337）に同梱（コメント済み）／C4 はユーザーが起票予定の Dependabot の点検のイシューの候補 ⑦ に追記（scratchpad の起票コマンド）／予防処置は無し（見送り 3 件・理由は「## 振り返り」）
- [close の後・マージ前] ユーザーの見直し（「BP 的に最適なのは？」→「OK」）で、揃える python を 3.11.18 から 3.12.3（見張り・スクリプトが実際に動く OS の python・CI の runner の python）に変える。記録を open に戻し、計画変更記録 4 を書いて計画レビューから通り直す — 受け入れ条件 AC1 を変えるため。OS の python の更新を自動で止める確かめは足さない（手元と CI の runner の更新時期のずれで CI が揺れるため。runbook に書く・計画書 D4）
- [plan-review 2] HIGHRISK・Blocker なし。Warning 1（セキュリティの記載が古い `@v10`）は計画書を直した。Warning 2（テストの結果欄が 3.11.18 のまま）は test-gate で書き直す。Warning 3（3.12.3 の取得が未実証）は implement で `uv lock`・`uv run --locked` を流して記録し、CI で確定する。Info（OS の python の更新は人が気づく）は D4 のまま — 直した内容は記載の整合だけで、方式・範囲・受け入れ条件は変えないので再レビューはしない
- [implement 2] python を 3.12.3 に変え `uv lock` を作り直した（計画変更記録 5）。/simplify は呼ばなかった — 変更は版の数字 2 行・自動で作り直したロックファイル・runbook の 1 行だけで、整理の対象になるコードが無い（前回の実装で /simplify 済み）
- [review-gate 2] 基本レビューの 1 回目（`docs/reviews/I211_code_review_20261029_0155.md`）は組み込みの /security-review が動かず HIGH（基盤の失敗）。やり直し（`_0204.md`）は失敗した回の `REVIEWED_COMMIT` を起点に「範囲 0 本」と判断し、/security-review を通さずに OK を出した（レビューの仕組みの穴。retro で扱う）。3.12.3 の変更が一度もセキュリティレビューを通らないのを避けるため、組み込みの /security-review を直接実行して補った → 指摘なし（ワークフローの起動条件・権限・秘密情報の参照なし・uv.lock のハッシュと `--locked`・run-all.sh の流し直しの引数・check-tools.sh の probe の出どころを確認）
- [retro 2] 台帳の残り: 後続イシュー行き 0 件。一覧に F7・A2・A3 を足した（`docs/reviews/backlog/I211.md`）。改善案: P1（差分のレビューが失敗した記録を起点にする穴）は I212（#358）として起票（同梱先の既存イシューが無い・判定の仕組みなので次のハーネスの作業で最優先）／C5（揃える版の選び方）は直した・観点の追加は見送り

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
STAGE_DONE: close NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
