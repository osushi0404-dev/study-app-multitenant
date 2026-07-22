# 敵対的レビューステージ [I142]

- 起動条件: `/code-review I142` の基本レビューが `FINAL_VERDICT: OK` かつ高リスク判定 YES（外部公開 API の挙動・エラー応答形式の変更）
- 記録日時: 2026-07-22
- 上限: 最大 3 周・サブエージェント総数 15

---

## 第 1 周

### 観点とエージェント（5 観点・並列）
1. ロジック回避・実機 repro
2. テストの false-green・tautology
3. 要件・脅威モデルの網羅漏れ
4. 設定・マイグレーション・デプロイ運用（動的観点。1 度 stall したため範囲を絞って再実行）
5. ドキュメント整合・規約の自己矛盾（動的観点）

### findings（重複排除後）

| # | 重大度 | 指摘 | 対応 |
|---|--------|------|------|
| 1 | High | `next(iter(serializer.errors.values()))[0]` は `ListField` の index キー dict で `KeyError` → 広域 except 撤去後は **500**。`subject_ids` の 2 要素目以降が不正なだけで未認証エンドポイントが 500 を返す | `core.exceptions.first_error_message()` を新設しネスト非依存の取り出しに変更。TC-AUTO-18 を追加 |
| 2 | High | `token_blacklist` 有効化により既存設定 `BLACKLIST_AFTER_ROTATION=True` が初めて有効化され、refresh が単回使用になる。FE はローテート後の新 refresh を保存しないため強制ログアウトの潜在爆弾 | `BLACKLIST_AFTER_ROTATION=False` を明示設定して現行挙動を維持。TC-AUTO-19 で固定。FE 是正と再有効化は別イシュー（I145）へ |
| 3 | High | AC「logout が有効トークンを失効させる」は rotate 済みセッションでは不成立 | #2 の対応（ローテート後失効を無効化）により解消。TC-AUTO-19 で logout 200 まで固定 |
| 4 | High | plan §8 の「INSTALLED_APPS から 1 行削除でロールバック可」は誤り。設定だけ戻すと `RefreshToken.blacklist` が消え `AttributeError` → logout 500 | plan §8 を訂正（PR 全体 revert を第一手段・設定と views.py は同時に戻す） |
| 5 | Medium | `OutstandingToken` は refresh JWT を平文保存し、simplejwt が admin に自動登録するため staff 権限で全文閲覧可能 | `accounts/admin.py` で `OutstandingToken` / `BlacklistedToken` を unregister。TC-AUTO-20・手動 TC13 を追加。plan §14 を「P9 影響あり」に訂正 |
| 6 | Medium | 「可観測性は現状同等」は不成立。ハンドラが応答を返すため Django 標準 500 ログ・`got_request_exception`・`ErrorContextMiddleware._log_exception` を通らなくなる | ハンドラのログにビュー名・HTTP メソッド・パス・ユーザ ID を追加。plan §11 に失われる経路と APM 導入時の申し送りを明記 |
| 7 | Medium | migrate 未適用時の影響は logout だけでなく **login・refresh も 500**（`for_user` が無条件 INSERT） | plan の Risk 表を訂正。compose・E2E ワークフローに migrate があることを確認して明記 |
| 8 | Medium | 規約の修正済みコード例が Django の `ValidationError` を使っており、新ハンドラでは 500 になる（規約に従うほど 4xx が 5xx 化する） | 例を DRF の `ValidationError` に変更し、規約本文に「4xx を返すときは DRF 例外を使う」を明記 |
| 9 | Medium | `IntegrityError` の分類が計画書（想定外→500）と規約例（想定内→4xx）で逆 | 規約に「同じ例外型でも文脈で分類が変わる」判断基準を追記。plan 調査5 に登録ビューで捕捉しない理由を明記 |
| 10 | Medium | 失効管理テーブルの無制限増加・`flushexpiredtokens` 未整備が担当者不在の負債 | plan Risk 表・§10 に明記し、別イシュー（I146）としてタイトル案までイシュー本文へ記載 |
| 11 | Medium | mutation 生存: `except TokenError` → `except BaseException` に改悪しても全テスト GREEN（logout の想定外例外 TC が無い） | TC-AUTO-15 を追加（`blacklist` に RuntimeError 注入 → 500 + ログ） |
| 12 | Medium | mutation 生存: `EnvironmentMisconfiguredError` を無関係な `RuntimeError` に置換しても I140 の 4 件が GREEN（body が汎用 500 と同一で判別力なし） | TC-AUTO-16 を追加（例外型そのものを固定） |
| 13 | Medium | mutation 生存: handler の 5xx ログ（`response is not None` 側）を削除しても全 GREEN | TC-AUTO-17 を追加 |
| 14 | Medium | 手動テストの `.env.e2e` パスが誤り（実体は `e2e/.env.e2e`）で Human が実行不能 | 手動テスト文書を修正（`docker-compose.yml:150` の参照先に合わせた） |
| 15 | Low | TC-DET-01 の `grep -c 'except Exception'` は `except BaseException` / bare `except:` を見逃す（変異体で exit 0 を実測） | AST 判定に差し替え。変異体で exit 1 を実測 |
| 16 | Low | TC-DET-03 の `grep -q` はコメントアウト行にもマッチする | 設定値の意味論判定（`manage.py shell -c`）に差し替え。未登録相当で exit 1 を実測 |
| 17 | Low | 手動テスト No.8 の期待文言が slug なし時のもの（実際は組織名が前置される） | 実 DB の組織名で修正 |
| 18 | Low | 規約の Celery 例の注記が「許容 2 ケース」の分類に紐づいていない／bare `except:` が残存 | 注記を許容ケース 2 に紐づけ、bare except を `except DatabaseError` + ログに修正 |
| 19 | Low | 新設した非 dict body の 400 契約が AC 未記載 | イシュー AC・plan §3 に追加 |
| 20 | Low | 規約は全体規範を宣言したが他アプリに広域 except が約 50 箇所残存し横展開イシューが未起票 | イシュー「含まない」に別イシュー（I147）としてタイトル案を明記 |
| 21 | Low | 行番号参照（`:689` 等）が節追加で陳腐化し AC が検証不能 | イシュー・計画書の参照を関数名ベースに変更 |
| 22 | Low | `set_rollback()` はどのテストも通っていない（`ATOMIC_REQUESTS` 未設定で実質 no-op） | 実害なしのため実装は維持。plan Risk 表の記述どおりであることを確認（追加テストはしない） |

### 第 1 周の集計
- NEW_CRITICAL: 0
- NEW_HIGH: 4（重複排除後。エージェント素の合計は 5）
- 対応: 上記のとおり全件反映（設計判断を要した #2・#5 はユーザー確認のうえ方針決定）

### 第 1 周の対応後テスト結果
- accounts 配下: 26 passed
- 全体回帰: **110 passed**（回帰なし）
- TC-DET-01/02/03: いずれも exit 0（変異体では exit 1 を実測＝false-green でないことを確認）

（第 1 周は新規 High が 1 件以上あったため、修正の妥当性も反証対象に含めて第 2 周を実施する）

---

## 第 2 周

### 観点とエージェント（3 観点・並列）
1. 第 1 周修正の妥当性の反証（mutation で修正が tautology でないことを確認）
2. 残存するロジック回避・想定外 500 化（第 1 周とは別入力・別経路）
3. 既存レスポンス契約の回帰（第 1 周の `custom_exception_handler` 変更が全 API に波及していないか）

### 結果
- 観点1: NEW_CRITICAL 0 / NEW_HIGH 0。first_error_message・`BLACKLIST_AFTER_ROTATION=False`・admin unregister・500 ログの文脈追加・TC-AUTO-15〜20 のいずれも mutation で「壊すと落ちる」ことを実測（tautology でない）。Low 1 件（AST 判定が `except builtins.Exception:` の属性アクセス形を見逃す）
- 観点2: NEW_CRITICAL 0 / NEW_HIGH 0。登録の非 dict/QueryDict/ListField・validate-slug・logout の各種不正入力で想定外 500 化は再現せず。真の未捕捉例外は JSON 500 でレンダリングされ DEBUG=False で詳細非露出を実測。Low 2 件（いずれも I142 非変更の既存分岐・到達不能経路）
- 観点3: NEW_CRITICAL 0 / NEW_HIGH 0。ハンドラの非 None 経路は byte 一致で不変、`first_error_message` は登録ビュー内 1 箇所のみ、I127（429）・I131（body 完全一致）・I006（rollback）とも GREEN。非 accounts 全域 84 passed で契約回帰なし

### 第 2 周の集計
- **NEW_CRITICAL: 0 / NEW_HIGH: 0（合計 0 の周回＝収束）**
- Low 指摘への任意対応: `first_error_message(None)` に明示 None ガードを追加、TC-DET-01 の AST 判定を属性アクセス形（`builtins.Exception`）も検出するよう強化。対応後 accounts 16 passed・TC-DET-01 exit 0

---

## ステージ結論
第 2 周で新規 Critical/High がゼロの周回に到達（loop-until-dry 収束）。上限（3 周・15 エージェント）内。最終判定 = max(スクリプト FINAL_VERDICT=OK, 敵対ステージ=OK) = **OK**。

VERDICT: OK
