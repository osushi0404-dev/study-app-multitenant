# 依存監査（定期検知）の運用

依存脆弱性ドリフト（リポジトリ無変更でも時間経過で発生する新規 CVE）を、PR 契機を待たずに検知する仕組みの運用手順（I109）。

## 仕組みの概要

- `.github/workflows/dependency-audit.yml` が**毎日 JST 7:00**（cron `0 22 * * *` UTC）に develop（`ref: develop` 固定）を checkout し、**PR ゲート（ci.yml）と同一条件**の監査を実行する:
  - backend: `pip-audit -r requirements.txt`（全件 fail 対象）
  - frontend: `npm audit --audit-level=critical --omit=dev`（critical のみ fail 対象）
  - 「同一条件」は**判定条件**の同一を指す。frontend の `npm ci` は省略している（npm audit は package-lock.json とレジストリ advisory DB のみで判定するため node_modules 不要・判定結果は PR ゲートと同一）
- 監査 fail 時は `scripts/claude/dependency-audit-issue.sh` が GitHub イシューを自動起票する:
  - タイトル: `[dependency-audit] <backend|frontend>: 依存脆弱性を検知（scheduled audit）`・ラベル: `dependency-audit`
  - **重複防止**: 監査種別ごとに open イシュー最大 1 本。既存 open があれば新規作成せず**コメント追記**（＝open のまま放置すると毎朝コメントが増えるが、イシューは乱立しない）
- 検知するのは GitHub イシューのみ。ローカルの `docs/issues/open/I###.md` は自動作成しない（採番権威 `next-issue-num.sh` との衝突回避。下記の 2 段階運用）。

## 検知時の対応手順（2 段階運用）

1. 起票されたイシューを確認する: `gh issue list --label dependency-audit --state open`
2. `/issue-bootstrap` でローカルイシュー（I###）を正式起票し、通常のイシューフロー（計画 → 実装 → テスト）で CVE に対応する（イシュー本文に dependency-audit イシューの番号を関連資料として記載する）
3. 対応完了（依存更新が develop にマージ）後、dependency-audit イシューをクローズする: `gh issue close <番号> --comment "I### で対応済み"`
4. クローズ後に監査が再度 fail した場合（新規 CVE）は新しいイシューが起票される

## 手動実行（検証・任意時点の監査）

```bash
gh workflow run dependency-audit.yml
gh run list --workflow=dependency-audit.yml
```

- `simulate_failure` 入力（none/backend/frontend）は**検知動作のテスト専用**（監査を強制 fail させて起票経路を検証する）。通常運用では使わない。

## 検知漏れ・workflow 失敗時の確認

- 実行履歴: `gh run list --workflow=dependency-audit.yml`（GitHub 高負荷時に schedule がスキップ・遅延することがある。daily 実行のため翌日リカバーされるが、必要なら上記の手動実行で即時監査できる）
- 自動起票が 403 等で失敗する場合: リポジトリの Settings → Actions → General → Workflow permissions を確認する（オーナー操作。workflow 側は `permissions: issues: write` を宣言済みだが、リポジトリ設定が read-only 強制だとキャップされる）

## 前提・変更時の注意

- **workflow 定義が default branch（現在: develop）上に存在すること**が schedule / workflow_dispatch の発火条件（GitHub 仕様）。default branch を main に戻す場合は、develop → main のマージで本 workflow が main に載っていれば schedule は継続する。
- **監査コマンドは ci.yml（PR ゲート）と同一条件を維持すること**。どちらかを変更する場合は両方を同時に更新する。乖離は決定論ゲート `scripts/claude/tests/test_i109_dependency_audit.sh`（ペア検証）が検知する。
- 判定基準の変更（例: npm audit のレベル変更）は、PR ゲートとの判定一貫性（「定期監査グリーンなら PR もグリーン」）を壊さないかを必ず検討する。
