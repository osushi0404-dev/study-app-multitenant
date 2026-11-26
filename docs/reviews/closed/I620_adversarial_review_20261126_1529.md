# 敵対的レビュー [I620]（別プロセス・2026-11-26 15:29）

- 見た範囲: 7039746791ae53467caf2600ae7ada1c1ec65744...d91c31054762d6293df5095b6ac189d83ca9dfa5
- 所要時間: 22 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（4 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I620.md の「## 必ず確かめる項目」（7 項目）
- 引き継ぎ: 引き継がない（I620_adversarial_review_20261126_1445.md の REVIEWED_COMMIT 7039746791ae53467caf2600ae7ada1c1ec65744 から HEAD までに記録の場所の外が変わった: e2e/tests/registration-link.spec.ts frontend/src/pages/MemberManagement.tsx）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 13 秒 | 0 | 0 | $0.1439 | ― | ― | ― |
| 2 | 報告あり | 18 秒 | 0 | 0 | $0.1720 | ― | ― | ― |
| 3 | 報告あり | 13 秒 | 0 | 0 | $0.1560 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I620] ── 観点: ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- この周の差分は、`MemberManagement.tsx` の表の幅指定、E2E の 360px の確かめ、docs だけだ。V1・V2・V3・V7 に関わるバックエンド（権限の絞り込み、`select_for_update`、発行時の失効、`HasRecentReauth`）には変更が無い。
- 前の周（既知 findings）で、この 4 項目は読んで確認されている。その後にこれらを壊す変更が入っていないことを、差分の一覧で確かめた。
- フロントの変更（`nowrap`・`minWidth`）で、本人確認や自組織への絞り込みを迂回できる経路は生まれない。この表示の変更はサーバー側の認可に影響しない。
- 既知の Medium（`passkey_id` の正規表現で、UUID でない値が通ると 500 になるおそれ）と Low（`OutstandingToken` が無い古い refresh トークン）は既知 findings に含まれるため、再報告しない。

実験: この周は静的読解のみ。差分がバックエンドに触れないので実験は不要と判断した。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I620] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **`complete` 側の拒否**:
  - `test_tc06_complete_logs_in` は、使用済みを 2 つの形で確かめている。
    - 先に取っておいた古い `options` で `complete` を呼ぶ。
    - 使用後に `options` を取り直す。
    - どちらも 400 と `LINK_UNUSABLE` になる。
  - 期限切れ・失効・無効の利用者・無効の組織は、`complete` 側を直接確かめていない。これは既知 findings（前回の敵対的レビューの観点 2 の Medium）と同じ内容なので、再報告しない。
- **`options` 側**:
  - `test_tc05_options_unusable` は、DB を直接 `update` して 5 つの状態を作る。実装の分岐をなぞる形ではない。
  - `reason=` のログ文字列も同時に確かめるので、どの分岐で拒まれたかを区別できる。
  - 状態は `update()` で作るので、実装が使う `save()` の副作用には依存しない。
- **別の用途・別の利用者の challenge**:
  - `test_tc06_complete_rejects_other_challenges` は、`register` 用途の challenge と、別の利用者の `link_register` の challenge の 2 つを使う。
  - どちらの場合も、認証器は渡した `options` の challenge に対して署名する。
  - 署名の側に差が無いので、400 になる原因は用途と利用者の確認だけだ。
  - 確認を外すと 200 になって落ちる。
  - 最後に `used_at is None` も確かめている。
- **ログイン済みの再登録（`test_tc06_reactivated_user`）**: 無効だった利用者を有効に戻した後は 200 になる。無効の拒否が、固定の状態の確認になっていないことを裏付ける。
- **`test_tc07`**: 順序の非決定性は、既知 findings にある Low と同じ内容なので再報告しない。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I620] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **V4（平文の残り）**: DB の `RegistrationLink` は `token_hash` だけを持つ。`registration_links.py:87-159` のログ出力は user_id・link_id・reason・passkey_id だけで、リンクの値もハッシュも出さない。リンクの値は `#token=` の後ろに付くので、サーバーのアクセスログにも出ない。
- **V6（運営の API の境界）**: `registration_links.py:28-54` の `CANNOT_TARGET_SELF`・`STAFF_TARGET`・`INDIVIDUAL_TARGET` はどれも `PasskeyError`（400）になる。組織の管理者が運営の API を呼ぶと、`IsAdminUser` で 403 になる。
- **今回の差分（`MemberManagement.tsx` の CSS と E2E）**: 認可・ログ・リンクの値の扱いには触れていない。リンクの値は表に出ない。表の `minWidth` と折り返さない指定は、脅威モデルに関係しない。
- **残るリスク（受け入れ済み）**: 組織の管理者が、同じ組織のほかの管理者あてに発行できる。計画で決めた仕様で、発行の前に本人確認があり、ログにも残る。

> ITEM: V4 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: d91c31054762d6293df5095b6ac189d83ca9dfa5
ROUNDS: 1
VERDICT: OK
