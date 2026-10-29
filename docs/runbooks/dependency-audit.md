# 依存監査と Dependabot の運用

依存脆弱性ドリフト（リポジトリ無変更でも時間経過で発生する新規 CVE）を、PR 契機を待たずに検知する仕組みの運用手順（I109）と、新しい版を PR で届ける Dependabot の受け取り方（I213・下の「## Dependabot（版上げの PR）」）。

**役割分担**: 依存監査は「今入っている版に穴がある」を毎日見つけてイシューにする。Dependabot は「直した版・新しい版」を PR で届ける。監査が fail したとき、Dependabot のセキュリティの修正の PR が来ていればそれを通すのが最短。来ていなければ下の「検知時の対応手順」で直す。

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

## Dependabot（版上げの PR）

設定は `.github/dependabot.yml`。書き間違いは pre-commit の `check-dependabot`（check-jsonschema の公式のスキーマ）が手元のコミット時と CI で止める。

### 見張るもの・見張らないもの
- 見張る: backend の pip・frontend の npm・e2e の npm・Docker（`backend`・`frontend` の Dockerfile と `docker-compose.yml`）・GitHub Actions・pre-commit。毎週確認する
- 見張らない:
  - ハーネスの道具の uv（`scripts/claude/tests`）: Dependabot の中で動く uv の版と、`pyproject.toml` の `required-version`（ぴったりの版・I211）がぶつかり、ロックファイルを作り直せない。版は onboarding.md「手元の準備（ハーネスのテスト）」の手順で手で上げる
  - 動かす環境の版を変える版上げ（python の minor 以上・node・postgres・redis の major）: `ignore` で出させない。上げるときは別のイシューを立てる

### 届き方
- minor・patch は対象ごとに 1 つの PR にまとまる（普段の版上げとセキュリティの修正の両方。画面の「Grouped security updates」は Off のままで、まとめ方はこの設定ファイルで決める）。major は 1 件ずつ
- 出たばかりの版は待つ（`cooldown`: 7 日。pip・npm の major は 14 日。ほかの対象は版の大きさ別の日数に対応していない）。セキュリティの修正は待たずに届く
- ラベル: `dependencies` と、アプリ側（pip・npm・Docker）は `track:app`、ハーネス側（GitHub Actions・pre-commit）は `track:harness`
- `target-branch` は書かない（書くとセキュリティの修正の PR にまとめ・ラベルの設定が効かない）。PR は既定のブランチ（今は develop）宛てに来る。既定のブランチを変えると、Dependabot の PR の宛先も変わる

### 届いた PR の通し方
| PR の種類 | CI | すること |
|---|---|---|
| minor・patch のまとめ／セキュリティの修正（major でも） | CI が緑 | イシュー → 計画の流れを通さず、ユーザーがマージする（自動マージは使わない） |
| 同上 | CI が赤 | マージしない。`/issue-bootstrap` で直すイシューを立てる（タイトルに PR 番号。セキュリティの修正なら優先度を上げる） |
| major（セキュリティの修正以外） | どちらでも | マージしない。`/issue-bootstrap` でイシューを立て、通常の流れで扱う（PR は通知として開いたまま置き、イシューの対応で置き換わったら閉じる） |

- Dependabot の PR の CI は secrets を使わない（E2E のパスワードは e2e.yml がジョブごとに作る）。pull_request で動くワークフローに secrets を足すと、Dependabot の PR の CI が落ちる（`scripts/claude/tests/test_i213_dependabot.sh` の W2 が止める）

### 取り込んだあと手元でやること
- 標準の起動コマンド `docker compose up -d --build --renew-anon-volumes` で起動し直すだけ（依存・土台イメージの指紋が変わっていれば作り直す。common-commands.md）
- ハーネスの uv・pre-commit・e2e の npm は、次の実行で自動で合わせる（`uv run --locked`・pre-commit の版ごとの環境・e2e の `npm install` と `npx playwright install chromium`）

### 固定の決まり（新しく足すときも）
- action はコミットの SHA で書き、行末に版を書く（例: `actions/checkout@<40 桁の SHA> # v4.4.0`）。Dependabot は SHA と版のコメントを一緒に上げる（W1 が止める）
- 土台イメージは「タグ＋指紋」で書く（例: `python:3.11-slim@sha256:<64 桁>`）。Dependabot は指紋の更新を PR にする（I1 が止める）。指紋は `docker buildx imagetools inspect <タグ>` の `Digest:` の値。OS の修正を急ぐときは、この値で手で上げてよい

### 止まったときに見る場所
- PR が来ない: Settings → Advanced Security の「Dependabot alerts」「Dependabot security updates」が On か（I213 の原因はここが無効だったこと）。Actions の「Dependabot Updates」の実行記録（対象ごとの成否とエラーの文言）
- 設定は bot から読めない（管理者権限が無い）ので、画面の確認と変更はユーザーの操作
