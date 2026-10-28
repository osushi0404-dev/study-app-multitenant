# プロジェクト概要 / Onboarding

## このプロジェクトとは

**学習アプリ（study-app-multitenant）**
Django REST Framework + React TypeScript のマルチテナント対応学習アプリ。
Claude Code に実装を委任しながら、人間がゲートキーパーになる **安全寄り Vibe Coding** で開発している。

---

## 一言で言うなら

> 「Claude Code に実装を委任するが、人間がゲートキーパーになる Vibe Coding。GitHub が品質の最終防衛線。」

---

## 4つの特徴

### 1. スキル駆動のフロー（打つコマンドは少ない）

ユーザーが打つのは `/issue-bootstrap` と `/plan-issue` だけ。`/plan-issue` の後は、Claude が計画レビュー → 実装 → レビュー → テストまで段階を順に進め、人の手動テストの手前で止まる（I193）。

```
/issue-bootstrap →（任意で /grill-me）→ /plan-issue
   └→ plan-review →（高リスク時）design-security-review → implement → review-gate ⇄ fix-loop → test-gate
       → 人の手動テスト（結果を返信）→ retro → close → GitHub で Approve & Merge
```

| ユーザーが打つスキル | 内容 |
|---|---|
| `/issue-bootstrap [title]` | 採番・イシューファイル作成・自己完結度レビュー・GitHub 登録（要件・基本設計・UI/UX の質問があるときだけ止まる） |
| `/grill-me I###` | 計画書作成前に、要件・基本設計・UI/UX の曖昧な点だけを聞く（任意） |
| `/plan-issue I###` | ブランチ・Draft PR・計画書・テスト文書・レビュー文書を作り、手動テストの手前まで進める |
| `/proceed I###` | 途中で止まったとき・新しいセッションで、続きから再開する |

段階のスキル（`plan-review`・`design-security-review`・`implement`・`review-gate`・`test-gate`・`fix-loop`・`retro`・`close`）はユーザーが打たない。組み込み（公式）の `/code-review`・`/security-review`・`/simplify` は段階の中で Claude が使う。詳細は docs/runbooks/workflow.md。

### 2. 止める条件を絞った安全設計

- ユーザーの確認は「人がやる手動テスト」と「マージ」と、3 つの止める条件（要件・基本設計・UI/UX の価値判断／取り消せない操作・安全装置そのものの変更／安全側の選択肢も取れない上限到達）だけ。それ以外で Claude が決めたことは「自律判断の記録」に残り、止まったときにまとめて報告される
- 計画レビューを通すまで Claude はコードを書かない。修正の後は必ずレビューを通り直す（`scripts/claude/gate-check.sh` が決定論で確かめる）
- hooks（`scripts/claude/hooks/pretooluse_guard.py`）が危険操作を物理的にブロック（PreToolUse）
- hooks（`scripts/claude/hooks/posttooluse_check.py`）が Edit/Write 直後の `.py`/`.json`/`.yaml` 構文を検証（PostToolUse）

### 3. GitHub が品質ゲートになっている

| 仕組み | 役割 |
|---|---|
| **Draft PR** | イシュー開始時に即作成。WIP の可視化と early feedback |
| **CI（GitHub Actions）** | push/PR のたびに自動実行 |
| **PR 本文** | 目的・変更点・テスト結果・ロールバック手順・参照ドキュメントを必ず記載 |
| **develop/main 直 push 禁止** | 必ず PR 経由。レビューなしにマージ不可 |

CI の内容（全部 pass しないとマージ不可）:

- Backend: `flake8`（lint）+ `bandit`（セキュリティ）+ `pytest`
- Frontend: `tsc --noEmit`（型チェック）+ `ESLint` + `Jest`
- ハーネス: `scripts/claude/tests/run-all.sh`（道具は `scripts/claude/tests/required-tools.txt`）

### 4. すべてドキュメントが残る

`docs/` 以下に `open` → `closed` で状態遷移するファイルが常に存在し、「なぜ作ったか」まで追える。PR 本文にも必ずドキュメントへの参照リンクを貼る。

---

## 全体の流れ

```
ローカル                          GitHub
─────────────────────────────────────────────
/issue-bootstrap ──────────────→ GitHub Issue 登録
/plan-issue ───────────────────→ Draft PR 作成
  plan-review       （計画レビュー）
  implement ───────────────────→ push → CI 実行
  review-gate       （CI 結果確認・組み込み /code-review・自作レビュー）
  test-gate         （テスト確認）→ 人の手動テスト（結果を返信）
  retro             （振り返り・必須）
  close ───────────────────────→ PR 本文整備 → Approve & Merge の依頼 → develop へマージ
                                  （main へは定期リリース時のみ）
```

---

## ブランチ戦略

```
main (本番環境) ← 定期リリース時のみ
  ↑
develop (開発統合) ← 日常的な開発はここに集約
  ↑
feature/I###-xxx ← イシューごとに作成
```

- ブランチ命名: `feature/I{イシュー番号3桁}-{概要をケバブケース}`
- hotfix は `main` と `develop` の**両方**にマージする

---

## ドキュメント構成

```
docs/
├── issues/      open / closed / templates                 # イシューファイル
├── plans/       open / closed                             # 計画書
├── proposals/                                             # 改善提案資料
├── tests/       open / closed / templates                 # テスト文書（自動・手動）
└── reviews/     open / closed / templates                 # レビュー文書
```

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
| python（パッチ版） | `scripts/claude/tests/.python-version` を書き換える → `uv lock --project scripts/claude/tests` | 同じ | 同じ |
| uv | `pyproject.toml` の `required-version` を書き換える → 手元の uv を同じ版にする（pipx で入れたなら `pipx install --force uv==<新しい版>`、公式のインストーラで入れたなら `uv self update <新しい版>`） | 同じ | 同じ（CI の setup-uv が同じ行を読む） |
| python のマイナー版（例: 3.11 → 3.12） | `.python-version` と `pyproject.toml` の `requires-python` を両方書き換える（片方だけだと `test_i211_version_pin.sh` の K1 が止める）→ `uv lock --project scripts/claude/tests` | 同じ | 同じ |

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

**Q: CI が落ちたらどうする？**
→ review-gate 段階が CI の失敗を見て fix-loop 段階に回し、Claude が直して review-gate に戻す（ユーザーの操作は要らない）。

**Q: main にはどうマージする？**
→ develop に十分な機能が溜まったタイミングで、bot が develop → main の PR を作り、oshui0404 が承認・マージする（週1・月1等）。マージ後にバージョンタグを必ず付ける。手順は docs/runbooks/workflow.md「本番リリースフロー」。

**Q: 計画書なしに実装できる？**
→ できない。計画書と計画レビュー（plan-review 段階）が最初のゲート。より良い案があれば、計画書を先に直して計画レビューを通してから実装する。

---

## 参照先

- 運用フロー詳細: `docs/runbooks/workflow.md`
- イシューフロー: `docs/runbooks/issue-flow.md`
- 計画書の書き方: `docs/runbooks/plan-writing-rules.md`
- レビュールール: `docs/runbooks/review-rules.md`
- 危険操作: `docs/runbooks/danger-ops.md`
- よく使うコマンド: `docs/runbooks/common-commands.md`
- UX ルール: `docs/runbooks/ux-rules.md`
- バックエンドチェック: `docs/runbooks/backend-check.md`
- テンプレート同期: `docs/runbooks/template-sync.md`
- pre-commit 運用: `docs/runbooks/pre-commit.md`
- コーディング規約（Backend）: `rules/ultimate_django_coding_standards.md`
- コーディング規約（Frontend）: `rules/react-coding-standards-integrated.md`
