# I097 手動テスト

- **関連**: docs/plans/open/plan_I097.md / docs/issues/open/I097.md（#183, PR #187）
- 大半の検証は決定論自動テスト（I097_auto_test.md）に昇格済み。本書は自動化しにくい「実 2 スタック同時 up の目視スモーク」と、Claude が実行可能なファイル/コマンド確認を扱う。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `bash scripts/claude/tests/test_wt_port_offset.sh` を実行 | `pass=N fail=0`（全 TC PASS） | Claude | | 決定論テスト① |
| 2 | `bash scripts/claude/tests/test_compose_ports.sh` を実行 | docker 有: 全 TC PASS / docker 無: `SKIP` で exit 0 | Claude | | 決定論テスト② |
| 3 | `bash scripts/claude/tests/test_wt_lifecycle.sh` を実行（回帰） | `pass=55 fail=0`（既存挙動の無改変） | Claude | | 後方互換 |
| 4 | `docker compose config` をリポジトリ直下（`.env` 無し）で実行し published を確認 | `5432/6379/8000/3000` が publish される（後方互換） | Claude | | AC1 |
| 5 | 直下に一時 `.env`（`BACKEND_PORT=8010` 等）を置き `docker compose config` を実行 | published が `5442/6389/8010/3010` に変わる。確認後 `.env` を削除 | Claude | | AC2 の裏付け |
| 6 | `git check-ignore .env` / `git status` で root `.env` が未追跡・ignore 済みを確認、`.env.example` は追跡対象を確認 | `.env` は ignore、`.env.example` は tracked | Claude | | 誤コミット防止 |
| 7 | 実際に 2 つの worktree（例: offset=10 と offset=20）で **同時に** `docker compose up -d` し、両スタックが起動することをブラウザ/ポートで目視 | 両 frontend（例 3010 / 3020）へアクセスでき、片方が起動失敗しない | Human | | 実環境の同時 up 目視スモーク（任意・環境依存） |
| 8 | 2 スタック同時稼働中に `docker compose ps` を各 worktree で確認し、`COMPOSE_PROJECT_NAME`（ディレクトリ名）でコンテナが分離されていることを確認 | 各 worktree のコンテナ名が別プロジェクトで分離 | Human | | AC4 の実環境確認（任意） |

**実施者の判定根拠**:
- No1〜6: コマンド実行・出力確認・ファイル/ignore 確認で完結 → Claude。
- No7〜8: 実 Docker デーモンでの複数スタック同時起動とブラウザ/ポート目視 → Human（環境依存・任意スモーク。決定論テスト②が AC3 を機械的に立証するため、これは補助確認）。
