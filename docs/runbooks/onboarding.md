# プロジェクト概要 / Onboarding

## このプロジェクトとは

**学習アプリ（study-app-multitenant）**
Django REST Framework + React TypeScript のマルチテナント対応学習アプリ。
Claude Code が計画・実装・レビュー・テストを自律で進め、人は価値判断（要件・設計・画面）・人の手動テスト・マージだけを行う。最後の守りは GitHub（ブランチ保護と CI）。

---

## 進め方の要点（正は各手順書）

ユーザーが打つのは主に次の流れ（打つスキルと段階の正: `docs/runbooks/workflow.md`「使うスキル」「フロー」）:

```
/issue-bootstrap →（任意で /grill-me）→ /plan-issue
```

`/plan-issue` の後は Claude が段階を順に進め、人の手動テストの手前・マージ依頼で止まる。途中から続けるときは `/proceed I###`。

- 止めてユーザーに聞く場面: `docs/runbooks/workflow.md`「止めて聞く条件」
- 守りの層（サンドボックス・見張り・GitHub）: `docs/runbooks/danger-ops.md`
- マージに必須のチェック: `docs/runbooks/branch-protection-setup.md` §2
- ブランチ・記録の置き場所: `docs/runbooks/workflow.md`「ブランチ戦略」「ディレクトリ規約」
- 手順書の一覧: `CLAUDE.md`「0. 参照先」

---

## 手元の準備（サンドボックスの道具・I430）

Claude Code の Bash は公式のサンドボックスの中で動く（`.claude/settings.json` の `sandbox`・`docs/runbooks/danger-ops.md`「サンドボックス（第 1 層）」）。WSL2・Linux では bubblewrap と socat が要り、無いと Claude Code が起動しない（`failIfUnavailable: true`。`Error: sandbox required but unavailable … Refusing to start without a working sandbox` と出る）。新しい端末では、Claude Code とは別の WSL のターミナルで入れる（Claude Code の `!` からは sudo のパスワードを入れられない）:

```bash
sudo apt install -y bubblewrap socat
```

---

## 手元の準備（GitHub の名義）

Claude は GitHub App の名義で GitHub を操作する（I223）。新しい端末では `docs/runbooks/github-app-setup.md` の手順で設定する。

---

## 手元の準備（pre-commit）

`git commit` のときに秘密の検出・基本の品質チェックを流す（フックの一覧と運用: `docs/runbooks/pre-commit.md`）。新しい端末で 1 回だけ行う:

```bash
sudo apt-get install pipx
pipx install pre-commit
pipx install detect-secrets==1.5.0
pre-commit install
```

- detect-secrets の版は `.pre-commit-config.yaml` の `rev`（今は `v1.5.0`）と `.secrets.baseline` の `version` に合わせる（版が違うと baseline を作り直したときに差分が出る）
- `pre-commit install` はリポジトリのルートで行う（`.git/hooks/pre-commit` ができる）

---

## 手元の準備（ハーネスのテスト）

ハーネスのテスト（`scripts/claude/tests/run-all.sh`）は、手元も CI の Harness Tests も同じ版の道具で流す（I204・I211）。

- どの道具をどう確かめるかの正: `scripts/claude/tests/required-tools.txt`（`run-all.sh` の冒頭で `check-tools.sh` が確かめ、合わなければテストを流さずに不合格）
- 版の正（道具ごとに 1 か所。どれも `scripts/claude/tests/`）: python は `.python-version`、PyYAML・pre-commit は `uv.lock`、uv 自身は `pyproject.toml` の `required-version`
- python の版は、見張り（`.claude/settings.json` のフック）が実際に動く手元の OS の `python3` に合わせてある（アプリの Docker の python とは別）。OS の更新で `python3 --version` のマイナー版が変わったら、下の「python のマイナー版」の手順で `.python-version` を合わせる（パッチ版の違いは自動では止めない。手元と CI の runner の更新時期がずれて CI が揺れるため）

### 初回
```
pipx install uv==<scripts/claude/tests/pyproject.toml の required-version の版>
bash scripts/claude/tests/run-all.sh
```

- `run-all.sh` は uv の環境（`scripts/claude/tests/.venv`。ワークツリーごと）の外で呼ばれると、`uv run --locked` で python と道具を正の版で入れてから流し直す（初回は python のダウンロードでネットワークが要る）。OS の python は入れ替えない
- 一部のテストだけを流すときも `run-all.sh` に渡す（同じ版の環境で流れる）: `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_xxx.sh`。`bash scripts/claude/tests/test_xxx.sh` と直に流すと OS の python のままになる
- `⛔` の行が出たら、その行の「入れ方」に沿って直し、もう一度流す（全部 `OK:` で終了コード 0）

### 版を上げる手順（手元で確かめてから CI へ）
| 道具 | 1. 正を書き換える | 2. 手元で流す | 3. push |
|---|---|---|---|
| PyYAML・pre-commit | `uv lock --project scripts/claude/tests --upgrade-package <名前>`（`uv.lock` だけが変わる） | `bash scripts/claude/tests/run-all.sh`（uv が入れ直して流す） | commit・push（CI が同じ `uv.lock` で流す） |
| python（パッチ版） | `scripts/claude/tests/.python-version` を、手元の OS の `python3 --version` と同じパッチ版に書き換える（見張りが動く OS の python と黙ってずれないように、OS の更新に合わせて上げる。`uv.lock` はパッチ版を持たないので `uv lock` は要らない） | 同じ | 同じ |
| uv | `pyproject.toml` の `required-version` を書き換える → 手元の uv を同じ版にする（pipx で入れたなら `pipx install --force uv==<新しい版>`、公式のインストーラで入れたなら `uv self update <新しい版>`） | 同じ | 同じ（CI の setup-uv が同じ行を読む） |
| python のマイナー版（例: 3.12 → 3.13） | `.python-version` と `pyproject.toml` の `requires-python` を両方書き換える（片方だけだと `test_i211_version_pin.sh` の K1 が止める）→ `uv lock --project scripts/claude/tests` | 同じ | 同じ |

片方だけずれたら、次のどれかが止める:
- uv の版が `required-version` と違う → uv 自身が `Required uv version … does not match` で止める
- `pyproject.toml` と `uv.lock` がずれている → `uv run --locked`（`run-all.sh` の流し直し）が止める
- 手元の環境の版が正と違う → `check-tools.sh` が `⛔ 版が違う道具` で止める
- CI の `ci.yml` に版の指定・install・ほかの action を足す → `scripts/claude/tests/test_i204_tool_sync.sh` が止める

道具を足す・変えるときは一覧を書き換える（python の道具なら `pyproject.toml` の `dependencies` に足して `uv lock`）。

---

## よくある質問

**Q: Draft PR を最初に作る理由は？**
→ 実装前から変更が GitHub 上に見えるようにするため。CI も早めに回せる。

**Q: 計画書なしに実装できる？**
→ できない。計画書と計画レビュー（plan-review 段階）が最初のゲート。より良い案があれば、計画書を先に直して計画レビューを通してから実装する（`docs/runbooks/plan-writing-rules.md`）。
