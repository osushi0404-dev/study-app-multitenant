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

### 1. スキル駆動のフロー（コマンドで進む）

作業はスラッシュコマンドを打つだけで進む。Claude が次のコマンドを都度案内してくれる。

```
/issue-bootstrap → /plan-issue → /plan-issue-review
→ /implement → /code-review → /test → /retro → /close
```

| スキル | 内容 |
|---|---|
| `/issue-bootstrap [title]` | 採番・イシューファイル作成・ブランチ作成・Draft PR 作成 |
| `/plan-issue I###` | 計画書・テスト文書・レビュー文書を作成（承認待ち） |
| `/plan-issue-review I###` | 計画書をBP・セキュリティ・モダン開発観点でレビュー |
| `/implement I###` | 承認済み計画に沿って実装・型チェック・push |
| `/code-review I###` | CI 確認・受け入れ条件照合 |
| `/test I###` | 自動テスト（pytest + Jest）・手動テスト確認 |
| `/fix-loop I###` | NG 時の原因整理→差分計画→承認→修正→再テスト |
| `/retro I###` | テスト OK 後の振り返り |
| `/close I###` | open→closed へ整理・PR 説明整備・クローズ |

### 2. 承認ゲート付きの安全設計

- 計画書への OK を出すまで Claude はコードを一切書かない
- hooks（`scripts/claude/hooks/pretooluse_guard.py`）が危険操作を物理的にブロック
- Claude が「勝手に次フェーズへ進む」ことを禁止

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
/issue-bootstrap ──────────────→ Draft PR 作成
/plan-issue      （計画書作成）
/plan-issue-review（計画書レビュー）
/implement ────────────────────→ push → CI 実行
/code-review     （CI 結果確認）
/test            （テスト確認）
/retro           （振り返り・推奨）
/close ────────────────────────→ PR 本文整備 → develop へマージ
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
├── issues/      open / in_progress / closed / templates   # イシューファイル
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
→ `/fix-loop I###` で差分計画 → 承認 → 修正のサイクルを回す。

**Q: main にはどうマージする？**
→ develop に十分な機能が溜まったタイミングで手動リリース（週1・月1等）。バージョンタグを必ず付ける。

**Q: 計画書なしに実装できる？**
→ できない。計画書への承認が最初のゲート。より良い案があれば「提案 → 承認 → 計画書更新」が先。

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
- コーディング規約（Backend）: `rules/ultimate_django_coding_standards.md`
- コーディング規約（Frontend）: `rules/react-coding-standards-integrated.md`
