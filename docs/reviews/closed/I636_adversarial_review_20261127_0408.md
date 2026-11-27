# 敵対的レビュー [I636]（別プロセス・2026-11-27 04:08）

- 見た範囲: a233e69f50fa912ae0295b8032c94bdec1bf109c...c9eec7df7d479af927462f316bd563658ffc94bb
- 所要時間: 26 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（17 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I636.md の「## 必ず確かめる項目」（4 項目）
- 引き継ぎ: 引き継がない（I636_adversarial_review_20261127_0342.md の REVIEWED_COMMIT a233e69f50fa912ae0295b8032c94bdec1bf109c から HEAD までに記録の場所の外が変わった: frontend/src/pages/Settings.tsx frontend/src/pages/__tests__/Settings.test.tsx）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 14 秒 | 0 | 0 | $0.1504 | ― | ― | ― |
| 2 | 報告あり | 21 秒 | 0 | 0 | $0.1904 | ― | ― | ― |
| 3 | 報告あり | 18 秒 | 0 | 0 | $0.1701 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I636] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- 今回の差分は、設定画面 `Settings.tsx` の読み込みの効果に `ignore` の後片付けを足した変更と、そのテスト（TC-15）、記録の文書だけ。V1・V3 に関わる裏側のコード（`models.py`・`permissions.py`・`views.py`）は、この範囲では変わっていない。
- V1: 前の周の敵対的レビューが、`can_manage_members` と `/api/members/` の 200/403 の一致、および運営（`is_staff`）の扱いが前と変わらないことを確認済み。今回の差分はそれを動かさない。
- V3: 形の違う `passkey_id`・メンバーの ID の扱いも、前の周で確認済み。今回の差分の範囲外。
- `Settings.tsx` の `ignore` の使い方: 後片付け後の応答では `setSettings`・`resetSettingsForm`・`toast.error`・`setLoading` を呼ばない。StrictMode の 2 回目の取得の応答は捨てずに描くので、読み込み中のまま固まる経路は見当たらない。
- 軽微な点（Low・既知の F4 と同一）: TC-15 は実時間の 50ms 待ちに頼る。

実験は実行していない。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I636] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。静的読解のみで、実験は実行していない。

- **TC-02 の注入版が、鍵つきの引き直しの有無を見分けられないのではないか。**
  - `_unusable_after_consume` は、本物の `consume_challenge` を呼んだ直後にリンクを使えなくする（test_I620_registration_links.py:443-451）。1 回目の確かめは通り、止められるのは鍵つきの引き直しだけになる。
  - `_skip_locked_recheck` は `lock=True` のときだけ確かめずに行を返し、`lock=False` は本物を通す（同 454-463）。
  - 注入版の `test_i636_complete_without_locked_recheck_would_pass` は期限切れのまま確定まで進み、200 になる（同 489-497）。本来の `test_i636_complete_unusable_after_first_check` は 400 を期待するので、鍵つきの引き直しを外すと落ちる。
  - `revoked` を注入に使わない理由は、「使用済みかつ失効」を禁じる DB の制約にある。これは妥当。

- **TC-03 の待ち合わせの包みが、本物の検証を呼ばずに偽の緑になるのではないか。**
  - `wait_then_create` は待ち合わせの後に本物の `verify_and_create_passkey` を呼ぶ（同 558-573）。
  - 鍵がある場合は、2 本目が鍵で待たされて待ち合わせに届かない。1 本目だけが 2 秒で時間切れになって先へ進み、`broken` が記録される。2 本目は鍵の後の引き直しで 400 になり、結果は `[200, 400]` になる。
  - 鍵を外した注入版（`_without_row_lock`）は、鍵つきの引き直しを `lock=False` にする。2 本とも待ち合わせを通り、`broken` は空になる。結果は `[200, 200]`、Passkey は 2 件になる（同 621-630）。
  - 本来のテストの `assert broken` と `== [200, 400]` は、この版で落ちる。結果が実行の順に頼らず、鍵の有無で決まる作りになっている。

- **モックが別のモジュール参照に効かず、空振りしていないか。**
  - `mock.patch.object` の対象は `passkeys` と `registration_links` のモジュール属性で、実装側がそのモジュール属性として呼ぶ参照に効く。空振りの根拠は見当たらない。

Low として残す点が 1 つある。`Barrier(timeout=2)` は CI が極端に遅いと時間切れ前に揃う余地がある。ただし計画書 R3 が受け入れ済みで、手動テスト No.1 の 10 回の記録でも担保している。新規の指摘にはしない。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I636] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説（すべて読んで確認。実験は出していない）:
- **例外の中身とユーザー ID がログと応答に出る。**
  - `create_member`（`registration_links.py:162-167`）のログは `organization_id` だけで、`user_id` も例外の文字列も出さない。
  - 応答は固定文 `DUPLICATE_USER_ID` の `ValidationError` だけで、`IntegrityError` の内容は載らない。
- **外側のトランザクションが壊れる。**
  - `transaction.atomic()` は `create_user` の内側だけを囲む。
  - `IntegrityError` は `with` の外で受けるので、ロールバックされるのはセーブポイントだけで、外側のトランザクションは有効なまま残る。
- **別の制約の違反を「重複」と誤報する。**
  - `create_user` に渡す値は `user_id`・組織・役割だけで、`email` は `None`。
  - 組織は `request.user.organization`（既存の行）なので、外部キー違反は実質起きない。
  - この回の差分（`Settings.tsx` とドキュメント）は backend に触れておらず、V4 の挙動は前の周から変わらない。
- **差分の `Settings.tsx` に脅威モデル上の抜けがある。**
  - 設定の値の表示と保存の順序だけの変更で、認証・認可には関わらない。
  - 低い重大度の気づき: TC-15 は `act`/`waitFor` を使わず 50ms の実時間待ちに頼っている。これは既知の F4（台帳）と同じなので再報告しない。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: c9eec7df7d479af927462f316bd563658ffc94bb
ROUNDS: 1
VERDICT: OK
