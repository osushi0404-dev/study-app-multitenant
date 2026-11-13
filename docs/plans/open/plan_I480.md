# I480 計画書: SECURITY=yes でも Low・再現なしの指摘は軽い指摘の一覧に回す

## 基本情報
- **計画書ID**: plan_I480
- **関連イシュー**: #480
- **Draft PR**: #495
- **作成根拠資料**: docs/issues/open/I480.md（GitHub #480 の本文の写し）
- **実装後評価**: docs/reviews/open/I480_review.md
- **作成日**: 2026-11-13

## 1. 背景/目的
- retro の手順 4-0 は、コードレビューの台帳の残りを `code-review.sh --route` で「後続イシュー」と「軽い指摘の一覧（`docs/reviews/backlog/`）」に振り分ける。今は `SECURITY=yes` の行が重さ・再現に関係なく後続イシューになり、さらに「次のハーネスの作業で最優先」と書かれる
- 見張りの直し（I444 → I454 → I463 → I469 → #477）では、レビュー役が見つけた軽い読み漏れが毎回 `SECURITY=yes` で付き、最優先の後続が途切れずに続いた（レビューが収束しない）
- 目的: `SEV=Low` かつ `REPRO=no` の行は `SECURITY=yes` でも一覧に回し、最優先の後続の連鎖を止める。再現のある行・Medium 以上の行は今までどおり後続イシューにする

### 調査結果
- **原因の概要**: 振り分けの決まりが「秘密情報に関わる指摘は、どんなに軽くても後続イシュー」になっているため、軽くて再現の無い指摘まで最優先の後続に上がる
- **詳細な原因分析**:
  - `scripts/claude/code-review.sh` の `route_reasons()`（767 行）は `if sec == "yes": r.append("SECURITY=yes")` で、重さ（`sev`）と再現（`repro`）を見ていない
  - retro の `.claude/skills/retro/SKILL.md` 154 行は「`SECURITY=yes`（重さに関係なく）」、163 行は「後続イシューに回した行に … `SECURITY=yes` の指摘が入っていれば … 最優先」と書く。`docs/runbooks/review-rules.md` 70 行も同じ決まりを要約している
  - I208 で、秘密情報の指摘を取りこぼさない安全側の決まりとして入れた
- **影響の実測（過去の記録の台帳の open・`SECURITY=yes` の行。周ごとの重複を含む延べ数）**: Low・再現なしは harness 8・guard 10・app 10。この変更で一覧に移るのは harness・guard の 18 行。app の 10 行は「アプリ本体」の理由で今までどおり後続イシュー（ただし最優先は付かない。§9）。Medium 以上・再現なしの `SECURITY=yes` は 0 行
- **境界の確認（コードを読んで確定）**:
  - 「Medium 以上」は既存の `RANK = {"Low": 0, "Medium": 1, "High": 2, "Blocker": 3}` で `RANK[sev] >= 1`
  - `REPRO` は台帳の正規表現 `LEDG`（660 行）が `yes|no` しか受け付けない。欄の無い古い形の行は `read_ledger` が既定値 `REPRO=yes`（止める側）で読むので、振り分けも後続イシュー側に倒れる。yes／no 以外の値は台帳の行として読まれない（今回の変更で扱いは変わらない）
  - 止める判定 `blocking()`（738 行）は今回触らない。`route_reasons()` は `blocking(e)` が真なら「止める指摘」の理由を必ず付けるので、止める行が一覧に落ちることはない
- **既存テストのベースライン（2026-11-13）**: `test_i202_ledger_cleanup.sh` pass=157 fail=0・`test_i205_stop_criteria.sh` pass=91 fail=0
- **環境前提**: `bash`・`python3`（テストが使う）。ローカル・CI（`scripts/claude/tests/run-all.sh`）で動いている

## 2. 受け入れ条件
- [ ] AC1: `SEV=Low REPRO=no SECURITY=yes`（KIND=harness・guard）の台帳の行が `--route backlog` に出て、`--route issue` に出ない
- [ ] AC2: `SECURITY=yes` で `REPRO=yes` または Medium 以上の行は、今までどおり `--route issue` に出て、理由に `SECURITY=yes` が付く
- [ ] AC3: 上の 2 つが決定論のテスト（失敗の注入つき）で固定され、既存の I208 のテストが合格する
- [ ] AC4: retro の手順 4-0 の説明（振り分けと「最優先」の条件）と review-rules の要約が新しい決まりと一致している
- [ ] AC5: 止める判定（`blocking()`）の結果が変わらない（既存の `test_i205_stop_criteria.sh` と `test_i202_ledger_cleanup.sh` の止める判定の項目で確かめる）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: retro の台帳の振り分け（ハーネスの流れ）。`blocking()`・台帳の書き方・レビューの合否は変えない

## 4. 変更点一覧（具体）
| ファイル | 関数・箇所 | 変更内容 |
|---|---|---|
| `scripts/claude/code-review.sh` | `route_reasons()` の `SECURITY=yes` の条件 | `if sec == "yes":` → `if sec == "yes" and (repro == "yes" or RANK[sev] >= 1):`。理由の文言 `SECURITY=yes` は変えない |
| `scripts/claude/code-review.sh` | `route_reasons()` の guard の行のコメント | 一覧 I208 F1 を同梱: 「blocking() と同じく再現を問わない」→「再現を問わない（GitHub から復旧できない例外。blocking() の guard は High 以上で、こちらは Medium 以上）」 |
| `.claude/skills/retro/SKILL.md` | 手順 4-0 の 154 行・163 行 | 154 行の「`SECURITY=yes`（重さに関係なく）」→「`SECURITY=yes` で再現ありか Medium 以上（Low かつ再現なしは一覧）」。163 行の最優先の条件の「`SECURITY=yes` の指摘」→「出力の理由に `SECURITY=yes` が付いた行」 |
| `docs/runbooks/review-rules.md` | 70 行の振り分けの要約 | 「`SECURITY=yes`」→「`SECURITY=yes` で再現ありか Medium 以上」 |
| `scripts/claude/tests/test_i202_ledger_cleanup.sh` | Q7 の期待値・FG-Q7 | Q7 の F8（Low・再現なし・harness・`SECURITY=yes`）を一覧側へ（`Q7_WANT='I:F1,F7,F9,F12 B:F2,F3,F4,F5,F6,F8,F10,F11'`）。FG-Q7 は「条件を外す」が F8 で検出できなくなるので、「新しい条件を前の `if sec == "yes":` に戻すと F8 が後続イシューに上がり不合格」に置き換える |
| `scripts/claude/tests/test_i202_ledger_cleanup.sh` | 新しい Q10（I480） | 下の §6 の行で、振り分けと理由の付き方を固定し、3 つの失敗の注入（FG-Q10a〜c）を付ける |
| `docs/reviews/backlog/I208.md` | F1 の行 | 同梱して直したので消す |

## 5. 実装手順（ステップ）
1. `route_reasons()` の条件とコメントを直す（§4 の 1・2 行目）。→ TC-01・TC-02 参照
2. `test_i202_ledger_cleanup.sh` の Q7・FG-Q7 を直し、Q10・FG-Q10a〜c を足す（ステップ 1 の後）。→ TC-01 参照
3. retro の手順 4-0 と review-rules の説明を直す（ステップ 1・2 と並行可）。→ TC-03 参照
4. 一覧 `docs/reviews/backlog/I208.md` の F1 の行を消す（ステップ 1 の後）

## 6. テスト計画
### 自動（`scripts/claude/tests/test_i202_ledger_cleanup.sh` の Q10。テストレベルは振り分けの関数の単体〔`lib "$CR" ledger_route`〕）
台帳（すべて `STATUS=open SCOPE=delta STOP=- RISK=-`。F6 だけ `SCOPE=outside`）:

| 行 | SEV | KIND | REPRO | SECURITY | 期待 |
|---|---|---|---|---|---|
| F1 | Low | harness | no | yes | 一覧（理由 `Low／再現なし`） |
| F2 | Low | guard | no | yes | 一覧（#477 の形） |
| F3 | Low | harness | yes | yes | 後続イシュー・理由 `SECURITY=yes` |
| F4 | Medium | harness | no | yes | 後続イシュー・理由 `SECURITY=yes` |
| F5 | Low | app | no | yes | 後続イシュー・理由は `アプリ本体` だけ（`SECURITY=yes` は付かない＝最優先にしない） |
| F6 | Blocker | harness | no | yes | 後続イシュー・理由 `SECURITY=yes` |

- Q10: `I:F3,F4,F5,F6 B:F1,F2`、かつ後続イシュー側の理由に `SECURITY=yes` を含む行が F3・F4・F6 の 3 行で、F5 の理由は `アプリ本体` だけ
- FG-Q10a（前の条件に戻す `if sec == "yes":`）: F1・F2 が後続イシュー側に上がり不合格
- FG-Q10b（再現を外す `if sec == "yes" and RANK[sev] >= 1:`）: F3 が一覧側に落ち不合格
- FG-Q10c（Medium 以上を外す `if sec == "yes" and repro == "yes":`）: F4・F6 が一覧側に落ち不合格
- Q7・FG-Q7 は §4 のとおり直す。止める判定（AC5）は既存の `test_i205_stop_criteria.sh` 全体と `test_i202_ledger_cleanup.sh` の止める判定の項目で確かめる（`blocking()` を触らないので新しい項目は足さない）
- 文言の固定テストは作らない（plan-writing-rules「決定論テストの対象の選び方」: retro・review-rules の文言は意図的な変更でしか消えず、レビューで見る）。既存の D1・D3・D4（`--route`・`最優先` がある）は合格のまま
### 手動
- retro・review-rules の説明が §4 の新しい決まりと一致していることを読んで確かめる（Claude）

## 7. ロールバック
- このブランチのコミットを revert する（データ・設定の変更なし）。既に一覧に回した行がある場合は、その行を手で後続イシューに移す

## 8. Risk & 回避策
- 秘密情報に関わる軽い指摘が一覧に埋もれる → 一覧は `/plan-issue` の「台帳の残りの一覧」で実装対象のファイルに当たる行を必ず見る。再現のある行・Medium 以上・アプリ本体・止める指摘は今までどおり後続イシュー。GitHub から復旧できない例外（見張りの High 以上）は `blocking()` で止まる（変更しない）
- 新しい条件で一覧に回す理由の無い行ができる → `route` モードは理由の無い行で exit 2 を出す守りがある（Low かつ再現なしの行は理由 `Low／再現なし` が付くので起きない）。Q10 で F1・F2 の一覧の行を確かめる
- テストの書き換えで守りが弱まる（FG-Q7 の置き換え） → FG-Q10a〜c と置き換えた FG-Q7 で、条件の 3 つの部分（Low・再現なしを外す／再現／Medium 以上）をそれぞれ壊すと落ちることを確かめる

## 9. 確定事項と自律判断
イシューに明記されている:
- `route_reasons()` の `SECURITY=yes` の条件を「`SECURITY=yes` かつ（再現あり または Medium 以上）」にする（解決方針）
- retro 4-0 の振り分けと「最優先」の条件を同じに直す（解決方針）
- `blocking()` は変えない・#477・#430 の扱いは変えない（スコープ）
- 判定は台帳の欄の値だけで行う（制約・I208）

Claude が決めた（技術的な選択と理由）:
- 「最優先」の条件を「出力の理由に `SECURITY=yes` が付いた行」と書く — 振り分けと同じ条件を、retro が出力から機械的に読める形にするため。アプリ本体の Low・再現なしの `SECURITY=yes` は「アプリ本体」の理由で後続イシューになるが、最優先は付かない（イシューの「条件を同じに直す」をそのまま当てはめた結果）
- 理由の文言は `SECURITY=yes` のまま変えない — 既存の出力の形・retro の読み方を変えないため
- `docs/runbooks/review-rules.md` 70 行も直す — 同じ決まりの要約で、残すと説明が食い違う（plan-writing-rules「消費箇所の全件列挙」）
- テストは既存の `test_i202_ledger_cleanup.sh`（I208 の振り分けのテストがある所）に Q10 として足す — 補助関数（`route`・`ids`・`broken`）をそのまま使える
- 一覧 `docs/reviews/backlog/I208.md` F1: 同梱 — 同じ関数の guard のコメントの不正確さで、今回の編集範囲の 1 行。直したら一覧から消す
- 一覧 `docs/reviews/backlog/I208.md` F2・F3・F5、`I207.md` F6・F7、`I206.md` F4、`I212.md` F2・F3・F4・F6、`I227.md` F1・F2・F4・F5・R1（`scripts/claude/code-review.sh`）: 残す — 振り分けの条件と関係の無い別の関数（`merged()`・`--route` の引数の検査・一時ファイル・`/security-review` の読み取りなど）で、このイシューの目的に入らない
- 一覧 `docs/reviews/backlog/I208.md` F4・F6、`I210.md` F2・F3・F7（`scripts/claude/tests/test_i202_ledger_cleanup.sh`）: 残す — FG-Q4・D1・A1・N17 などの別の項目で、今回触る Q7・Q10 と関係しない
- 一覧 `docs/reviews/backlog/I223.md` B1〜B4・`I224.md` F9（`FILE=-`）: 残す — bot・PR の後片付けと別イシューの実測で、関係しない
- 一覧の `.claude/skills/retro/SKILL.md`・`docs/runbooks/review-rules.md`・`scripts/claude/tests/test_i205_stop_criteria.sh` に当たる行: 該当なし

要件適合性: 受け入れ条件の範囲を超える仕様の追加は無い（review-rules の要約の同期とコメントの直しだけ）。マルチテナント・ステータス遷移: 該当なし（ハーネスの振り分けだけ）。
セキュリティ影響: アプリのコードの変更なし（入力検証・認証認可・OWASP・依存の追加は該当なし。bandit・npm audit の対象外）。ハーネスの安全側の決まりを 1 か所緩める変更なので、緩める範囲（Low かつ再現なし・KIND が app 以外）をテストで固定し、止める判定は変えない。
P3/P5/P8 影響なし（DB・外部 API・非同期・インフラ・依存の変更なし）。P6 影響なし（画面なし・データ量の懸念なし）。P9 影響なし（個人情報・テナントデータを扱わない）。
設計品質: 振り分けの条件は今までどおり `route_reasons()` の 1 か所。重さの比較は既存の `RANK` を使い、新しい定数を足さない。
コーディング規約（Django・React）: 対象のコードが無いので該当なし。

Danger Ops（有無/手順/ロールバック）:
- 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 2 | 読んで可 | TC-01 の FG-Q10a〜c と置き換えた FG-Q7 が、新しい条件の 3 つの部分（Low かつ再現なしを一覧へ・再現ありは後続・Medium 以上は後続）をそれぞれ壊すと不合格になり、条件を確かめているか |
| V2 | 3 | 読んで可 | 一覧に移るのは `SECURITY=yes`・`SEV=Low`・`REPRO=no` で、止める指摘・アプリ本体・guard の Medium 以上に当たらない行だけか（`route_reasons()` のほかの理由と `blocking()` が変わっていない。TC-01 の Q10 の F5・TC-02） |
| V3 | 3 | 読んで可 | retro 4-0 の「最優先」の条件（理由に `SECURITY=yes` が付いた行）が、`route_reasons()` の出力と食い違わないか（TC-03） |
