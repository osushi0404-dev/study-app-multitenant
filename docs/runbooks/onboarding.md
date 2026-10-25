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
