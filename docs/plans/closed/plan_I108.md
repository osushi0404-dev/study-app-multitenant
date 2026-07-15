# 計画書: I108 Pillow 12.3.0 へのセキュリティアップデート（pip-audit CI ブロッカー解消）

## 基本情報
- **計画書ID**: plan_I108
- **関連イシュー**: #203
- **Draft PR**: #204
- **作成根拠資料**: docs/issues/open/I108.md（起点イシュー）
- **実装後評価**: docs/reviews/closed/I108_review.md
- **作成日**: 2026-07-15

---

## 背景/目的

### 原因の概要
依存ライブラリ Pillow のピン版（12.2.0）に対して 2026-07-09〜07-14 の間に新規 CVE が5件公開され、CI の pip-audit ゲート（既知脆弱性ゼロを要求）に抵触した。リポジトリ側の変更なしに発生した環境ドリフトであり、**全 PR の CI（Backend Lint & Security ジョブ）がブロック**されている。

### 詳細な原因分析
- CI の Backend Lint & Security ジョブ（`.github/workflows/ci.yml:26-28`）は `pip-audit -r requirements.txt` を実行し、既知脆弱性が1件でもあれば exit 1 で失敗する。
- `backend/requirements.txt:9` は `Pillow==12.2.0` をピンしている。
- 2026-07-14 の PR #202 CI 実行で Pillow 12.2.0 に対し **PYSEC-2026-2253 / 2254 / 2255 / 2256 / 2257** の5件が検出された（Fix Versions はすべて **12.3.0**）。
- develop の最終 CI（2026-07-09、PR #194/#195）は成功していたため、これらの CVE はその後に公開されたもの。以後どのブランチの PR でも再現する。
- コードの不具合ではなく、セキュリティゲートが設計どおり動作した結果の依存更新要求（根本原因はピン版に対する新規 CVE 公開）。

### 調査結果（計画時に実走・確認済み）

**ツール実走による完了基準の確定（/grill-me・2026-07-15 実施）**:
| 実走内容 | 結果 |
|---------|------|
| `pip-audit -r backend/requirements.txt --no-deps`（現行ピン 12.2.0） | **exit 1**。pillow 12.2.0 に PYSEC-2026-2253〜2257 の5件（Fix Versions すべて 12.3.0）。イシュー記載の CI ログと一致 |
| `pip-audit -r <Pillow==12.3.0 に置換した requirements>`（**CI 同条件**: `--no-deps` なし＝推移的依存込みの完全解決） | **exit 0**。`No known vulnerabilities found`。**他パッケージに新規 CVE はなく、Pillow 1行更新のみで AC「pip-audit exit 0」は達成可能**（依存解決も成功＝Pillow 12.3.0 は PyPI に存在しインストール可能） |

**環境前提確認**:
- ローカル: `pipx run pip-audit`（2.10.1）で実行可能（上記実走に使用）。CI は `backend/requirements-dev.txt` の `pip-audit==2.10.0` を使用。バージョンは異なるが、いずれも同一の脆弱性 DB（PyPI Advisory / OSV）を照会するため判定は等価。
- `gh` CLI: 認証済み（本計画の Draft PR #204 作成に使用済み）。

**ピン箇所・使用箇所の全件確認**:
- Pillow のピンは `backend/requirements.txt:9` の**1箇所のみ**（`requirements-dev.txt`・`pyproject.toml`・Dockerfile 等に重複ピンなし。repo 全体 grep で確認）。
- Pillow（PIL）の import 箇所: `backend/problems/utils.py`（画像処理）と `backend/problems/tests/test_I073_image_update.py`（既存回帰テスト）。既存テストが CI Backend Tests で実行されるため、パッチ更新の回帰は CI で検出可能。

**依存ファイル変更の波及先（Dockerfile / docker-compose）**:
- `backend/Dockerfile`: `base` ステージ（18-19行目）で `requirements.txt` を `pip install`。`dev` / `production` ステージは `base` を継承 → **backend イメージの再ビルドで反映**。
- `docker-compose.yml` で backend Dockerfile をビルドするサービス: `backend` / `celery` / `celery-beat` / `e2e-init` の4つ。ローカル開発環境では `docker compose build` による再ビルドが必要（CI は毎回クリーンビルドのため対応不要）。

**既存テストの事前実行（ベースライン）について**:
- 本イシューの failing gate は pip-audit であり、そのベースライン（12.2.0 → exit 1 / 5件）と修正後判定（12.3.0 → exit 0）は上記のとおり実走済み。
- Backend Tests / E2E のベースラインは develop 最終 CI（2026-07-09・グリーン）を採用する。本変更はコード無改変の依存1行更新であり、回帰検証は CI の全ジョブ実行（TC-03）で行う。

---

## 受け入れ条件（イシューから転記）

- [ ] `backend/requirements.txt` が `Pillow==12.3.0` になっている
- [ ] `pip-audit -r backend/requirements.txt` が exit 0（CI の Backend Lint & Security ジョブが pass）
- [ ] CI の Backend Tests / E2E Tests / Frontend 系ジョブがすべて pass（画像機能の回帰なし）
- [ ] develop へマージ後、後続 PR（例: I107 の PR #202）が develop 取り込みで CI グリーンになれる状態

---

## 影響範囲

| 領域 | 影響 |
|------|------|
| Backend | 依存ライブラリ1件のバージョン更新（`backend/requirements.txt:9`）。アプリコード変更なし |
| Frontend | なし |
| DB | なし |
| Config/Infra | backend Docker イメージの再ビルドが必要（`backend/Dockerfile` base ステージが requirements.txt をインストール。波及サービス: `backend` / `celery` / `celery-beat` / `e2e-init`）。CI は毎回クリーンビルドのため追加作業なし。ローカル開発環境は次回 `docker compose build` 時に反映 |

---

## 変更点一覧

| ファイル | 変更内容 |
|---------|---------|
| `backend/requirements.txt` | 9行目 `Pillow==12.2.0` → `Pillow==12.3.0`（1行のみ） |

---

## 修正対象と具体的変更内容

### 修正アプローチ
pip-audit が提示する修正版（12.3.0）へ Pillow のピンを1行更新することで、検出された5件の既知脆弱性をすべて解消し、CI の pip-audit ゲートを exit 0 に戻す。コードは無改変とし、画像機能の回帰有無は CI の既存テスト（Backend Tests の `test_I073_image_update.py` 含む・E2E Tests）で検証する。

### 修正項目1: backend/requirements.txt の Pillow ピン更新
**修正方針**: 検出された PYSEC-2026-2253〜2257 の Fix Version である 12.3.0 へ更新し、既知脆弱性ゼロの状態に戻す。パッチ/マイナー更新のため API 互換（メジャー更新ではない）。

```diff
 django-filter==23.4
-Pillow==12.2.0
+Pillow==12.3.0
 celery==5.3.4
```

---

## 実装手順

**ステップ1**: `backend/requirements.txt:9` を `Pillow==12.3.0` へ更新する（上記 diff どおり・1行）
→ 検証は TC-01 参照

**ステップ2**: 更新後の requirements で pip-audit を CI 同条件（依存解決込み）で実行し、exit 0 を確認する
→ 検証は TC-02 参照（計画時スパイクで exit 0 を実証済み。実装時に再実行して CVE 追加公開がないことを確認する）

**ステップ3**: コミット・プッシュし、Draft PR #204 の CI 全ジョブ（Backend Lint & Security / Backend Tests / E2E Tests / Frontend 系）の pass を確認する
→ 検証は TC-03 参照

- 依存関係: ステップ2はステップ1の完了が前提。ステップ3はステップ2の完了が前提（ローカルで exit 0 を確認してから push する）。
- 垂直スライス原則: 変更が1ファイル1行のため、分割せず単一スライスで実施する。
- 未知リスク先行原則: 最大の不確実要素（「12.3.0 で pip-audit が exit 0 になるか・他パッケージに未検出 CVE がないか」）は計画時スパイクで実証済み（調査結果参照）。残る不確実要素は CI 上での回帰検証のみで、ステップ3で顕在化する。
- サービス再起動: ファイル削除・サービス停止なし。ローカル開発環境への反映は次回の `docker compose build`（実装フローのブロッカーではない。CI はクリーンビルド）。

---

## テスト計画

- 自動テスト: `docs/tests/open/I108_auto_test.md`（TC-01〜TC-03。requirements 内容の決定論判定・pip-audit exit 0・CI 全ジョブ pass）
- 手動テスト: `docs/tests/open/I108_manual_test.md`（CI 結果確認・マージ後の後続 PR 解除確認。全行 Claude 実施可）
- テストレベルの選択: 本変更はコード無改変の依存更新のため、新規ユニットテストは追加しない。回帰検証は**既存の CI テストスイート**（Backend Tests: `test_I073_image_update.py` 含む / E2E Tests）に委譲する。ゲート判定（pip-audit）は決定論 TC として明文化する。
- 再発防止テスト: pip-audit ゲート自体が再発防止機構（新規 CVE 公開時に CI が fail する設計どおりの挙動）。ゲート仕様の変更はイシューのスコープ外。
- false-green 検証（実施済み・2026-07-15）:
  - TC-01（`grep -E '^Pillow==12\.3\.0$'`）: 失敗条件＝現状の 12.2.0 の requirements に対して実行し **exit 1（NG）** を確認済み。
  - TC-02（pip-audit exit 0 判定）: 失敗条件＝現行ピン 12.2.0 に対して実行し **exit 1（5件検出・NG）** を確認済み。

---

## ロールバック

- `git revert` で本 PR のコミットを打ち消す（ピンが 12.2.0 に戻る）。
- ただし 12.2.0 に戻すと pip-audit ゲートが再び fail する（既知 CVE 5件）ため、ロールバックは「12.3.0 起因の重大回帰が CI/本番で判明した場合」のみの緊急措置とし、その際は pip-audit ゲートの一時 ignore 運用（スコープ外・別イシュー）とセットで判断する。
- DB・データへの影響はゼロ（依存1行のみ）のため、データのバックアップ・復旧は不要。

---

## Risk & 回避策

| リスク | 対策 |
|--------|------|
| Pillow 12.3.0 での画像処理の挙動回帰 | パッチ/マイナー更新で API 互換。既存回帰テスト（`test_I073_image_update.py`）を含む CI Backend Tests / E2E Tests で検証（TC-03）。fail 時はロールバック方針に従う |
| 計画時スパイク〜実装の間に他パッケージへ新規 CVE が公開され、Pillow 更新だけでは exit 0 にならない | 実装ステップ2で pip-audit を再実行して確認（TC-02）。新規検出があれば計画書との不一致として即中断し、ユーザーへ報告（勝手に他パッケージを更新しない） |
| ローカル pip-audit（2.10.1）と CI（2.10.0）のバージョン差による判定差 | 両者とも同一の脆弱性 DB（PyPI Advisory / OSV）を照会するため判定は等価。最終判定は CI（TC-03）を正とする |
| ローカル開発環境で古い Pillow が残留 | requirements.txt は Dockerfile のインストール対象のため、次回 `docker compose build` で反映される旨を影響範囲に明記済み |

---

## 条件付きセクションの該当判定

- セクション10（データ整合性設計）: **P3 影響なし**（DB 変更なし）
- セクション11（運用設計）: **P5 影響なし**（外部 API・非同期処理・バッチの変更なし。celery はイメージ再ビルドのみで設定・コード無改変）
- セクション12（コスト・保守見積もり）: **P8 影響なし**（新規インフラ・外部サービス追加なし。依存1行更新）
- セクション13（性能・UX設計）: **P6 影響なし**（フロントエンド変更なし・性能要件変更なし）
- セクション14（学習効果設計）: 該当なし（学習機能・学習データ・学習体験の変更なし）
- セクション15（プライバシー・コンプライアンス設計）: **P9 影響なし**（個人情報・未成年データ・テナントデータの扱いの変更なし。本更新はむしろ C2（プライバシー/セキュリティ）を改善する方向の依存更新であり、新たなデータ取扱いは発生しない）

---

## 承認ポイント

**セキュリティ影響**: あり（改善方向）。既知 CVE 5件（PYSEC-2026-2253〜2257）を持つ Pillow 12.2.0 を修正版 12.3.0 へ更新する。更新後の依存ツリー全体に既知脆弱性がないことを pip-audit（CI 同条件）で実走確認済み。入力バリデーション・認証認可・機密データの扱いに変更なし。

**設計判断の明示**

| 判断事項 | 根拠 |
|----------|------|
| 更新先を 12.3.0 とする（それ以上へ上げない） | イシューに明記（pip-audit の提示する Fix Version。スコープ「Pillow 以外の依存更新・一括アップデートは含まない」） |
| コード無改変・回帰検証は CI 既存テストに委譲 | イシューに明記（解決方針） |
| 新規ユニットテストを追加しない | イシューのスコープから導出（画像処理機能の仕様変更なし・既存回帰テスト `test_I073_image_update.py` が存在）。**仮定で決定 → 承認確認** |
| 本イシューを wt-harness worktree（本セッション）で計画・実装する | **仮定で決定 → 承認確認**。イシュー本文は「primary checkout（track:app）側で実施が原則」と記載するが、primary は現在 feature/I103 作業中であり、本イシューは本トラック（I107/PR #202）のブロッカーでもある。ユーザーが本セッションで /plan-issue I108 を実行したことから本 worktree での実施と解釈（worktree.md §9 の禁止事項「他トラック worktree への直接書込」には抵触しない）。承認された場合、イシュー本文の「解決方針/制約」の worktree 記載を実態に合わせて更新する |

---

📋 計画書を作成しました: docs/plans/open/plan_I108.md

⏸️ **承認待ち中**: 実際の修正作業は開始しません
✅ 承認いただけましたら「OK」または「承認」とお答えください
❌ 修正が必要でしたら具体的な指示をお願いします

## レビュー結果
- [20260715_0332 判定: ✅ 完了](../../reviews/closed/I108_plan_review_20260715_0332.md)

## 完了情報
- **完了日時**: 2026-07-15
- **対応者**: Claude Code
- **レビュー結果**: OK（plan-review 指摘ゼロ / code-review 指摘ゼロ・FINAL VERDICT OK / TC-01〜03 PASS・MT-1〜3 OK。MT-4 は develop マージ後に実施）
