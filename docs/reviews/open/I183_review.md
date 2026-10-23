# I183 レビュー: djangorestframework 3.18.0 → 3.18.2（pip-audit 失敗の解消）

## 基本情報
- **対象計画書**: docs/plans/open/plan_I183.md
- **関連イシュー**: #309（docs/issues/open/I183.md）
- **Draft PR**: #310

## レビュー目的
- 変更が `backend/requirements.txt` の DRF の 1 行だけであること（ほかの依存・アプリのコード・CI 定義・Dockerfile が変わっていないこと）
- CI と同条件の `pip-audit -r requirements.txt` が既知の脆弱性 0 件で終わること
- 3.18.1/3.18.2 の振る舞いの変化（計画書 §2 の表）でアプリの正常な動作が変わっていないこと（pytest 103 件・E2E）
- simplejwt 5.5.1 と共存できること（pip check・JWT 認証を通るテスト）
- 手元イメージを作り直し、テストが 3.18.2 で実行されたこと（TC-04）

## 期待する成果
- develop 宛ての全 PR の CI 停止が解除され、I182（PR #308）の `/code-review` を再開できる

## 変更概要
- `backend/requirements.txt` の djangorestframework を 3.18.0 → 3.18.2 に更新し、CVE-2026-114136/114137/114138 を解消（CI の pip-audit を通す）。

## 変更点
- `backend/requirements.txt`: 2 行目 `djangorestframework==3.18.0` → `==3.18.2`（計画 §6 ステップ1）
- アプリのコード・ほかの依存・CI 定義・Dockerfile: 変更なし（TC-02 で機械検証）

## 影響範囲
- Backend: `backend/requirements.txt` のみ（アプリのコード変更なし）
- Frontend / DB / CI 定義: なし
- Docker（手元）: `backend`・`celery`・`celery-beat`・`e2e-init` のイメージの作り直し

## 実装結果評価
- 計画書 §6 ステップ1〜3 のとおり実装（2026-10-23）。requirements.txt 1 行の変更 → 手元 4 イメージの作り直し・3 サービスの再起動 → 回帰確認。
- plan review: VERDICT OK（Info 1 件＝TC-05 の false-green 検証欄の説明不足は実装前に auto_test・計画書 §7 へ反映済み）。

## テスト結果
- 自動: TC-01〜TC-07 **全 PASS**（2026-10-23）。pip-audit 0 件・コンテナの版 3.18.2・pytest 103 passed（ベースライン同数）・pip check 整合・マイグレーション差分なし。
- 手動: M1/M2 は push 後の CI で確認（未実施）。M3 は I182 側の作業（対象外）。
- code review: VERDICT OK・高リスク No（Low 1 件＝M1/M2 の実結果欄が空白・/test で記録するフロー上の正常状態）。
- /test（2026-10-24）: 自動 TC-01〜TC-07 全 PASS（実装時と同値）。手動 M1 OK（PR #310 の全 6 チェック pass・E2E 9m59s）・M2 OK（CI の pip-audit 出力 `No known vulnerabilities found`）。Human 実施項目なし。

## 計画との差分
- なし

## ロールバック
- requirements.txt 更新コミットの revert → イメージの作り直し・再起動で 3.18.0 に戻る。データ影響なし。
