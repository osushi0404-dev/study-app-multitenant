# Claude Code ファイル構成一覧

このプロジェクトで Claude Code（バイブコーディング）が参照するファイルの全体像をまとめたリファレンスです。

---

## ディレクトリ構成（全体図）

```
study-app-multitenant/
│
├── CLAUDE.md                          ← [★ 起点] プロジェクト憲法・絶対ルール
│
├── .claude/                           ← Claude Code 設定ディレクトリ
│   ├── settings.json                  ← 権限設定（allow / ask / deny）+ hooks
│   ├── settings.local.json            ← ローカル権限の一時的な追加許可
│   └── skills/                        ← カスタムスキル（スラッシュコマンド）
│       ├── issue-bootstrap/SKILL.md   ← /issue-bootstrap コマンド定義
│       ├── plan/SKILL.md              ← /plan コマンド定義
│       ├── implement/SKILL.md         ← /implement コマンド定義
│       ├── fix-loop/SKILL.md          ← /fix-loop コマンド定義
│       └── close/SKILL.md             ← /close コマンド定義
│
├── docs/
│   ├── runbooks/                      ← 詳細ルール集（CLAUDE.md から参照）
│   │   ├── workflow.md                ← 運用フロー・ブランチ戦略・承認ワークフロー
│   │   ├── plan-writing-rules.md      ← 計画書の書き方・一致性保証ルール
│   │   ├── issue-flow.md              ← イシュー作成〜クローズの詳細手順
│   │   ├── danger-ops.md              ← 危険操作の承認ルール
│   │   ├── common-commands.md         ← よく使うコマンド集
│   │   ├── backend-check.md           ← バックエンド修正時の診断・検証手順
│   │   ├── review-rules.md            ← レビューファイルの作成・管理ルール
│   │   ├── ux-rules.md                ← UX 設計・チェックリスト
│   │   └── template-sync.md           ← ルール変更時のテンプレート同期手順
│   │
│   ├── issues/                        ← イシューファイル（作業チケット）
│   │   ├── open/XXX.md                ← 対応中
│   │   ├── in_progress/XXX.md         ← 実装中
│   │   ├── closed/XXX.md              ← 完了
│   │   └── templates/issue_template.md
│   │
│   ├── plans/                         ← 計画書（実装前に作成・承認必須）
│   │   ├── open/plan_IXXX_概要.md     ← 承認待ち・作業中
│   │   ├── closed/                    ← 完了済み
│   │   └── templates/plan_template.md
│   │
│   ├── tests/                         ← テストケース・エラー管理
│   │   ├── open/test_IXXX_manual.md   ← ユーザーテスト手順
│   │   ├── open/test_IXXX_auto.md     ← 自動テスト手順
│   │   ├── open/error_IXXX.md         ← エラー管理（NG時に作成）
│   │   ├── closed/
│   │   └── templates/
│   │
│   └── reviews/                       ← レビューファイル（品質記録）
│       ├── open/reviewXXX_IXXX.md     ← 実装前に枠作成・後で記入
│       ├── in_progress/
│       ├── closed/
│       └── templates/review_template.md
│
├── rules/                             ← コーディング規約（実装時に参照）
│   ├── ultimate_django_coding_standards.md    ← バックエンド規約
│   └── react-coding-standards-integrated.md  ← フロントエンド規約
│
├── scripts/
│   └── claude/
│       └── hooks/
│           └── pretooluse_guard.py    ← 危険操作をブロックする安全フック
│
└── .github/
    └── workflows/
        └── plan-gate.yml              ← PR マージ前の自動チェック
```

---

## ファイル別・役割詳細

### CLAUDE.md（プロジェクト憲法）

**役割**: Claude Code が最初に読む「憲法ファイル」。絶対ルールとスキルの一覧を定義。

| 項目 | 内容 |
|------|------|
| 参照先 | 詳細ルールを各 runbook に委譲（このファイル自体は短く保つ） |
| 絶対ルール | 計画書外の実装禁止・承認前のコード変更禁止・main/develop への直 push 禁止 |
| スキル一覧 | `/issue-bootstrap` `/plan` `/implement` `/fix-loop` `/close` |
| 権限・二重ガード | settings.json の allow/ask/deny + hooks による二重保護 |

---

### .claude/ ディレクトリ

#### settings.json（権限設定）

Claude Code が実行できる Bash コマンドを 3 段階で制御する。

| 区分 | 内容 |
|------|------|
| `allow` | 読み取り系・git status/diff/log・docker logs・テスト実行など（確認なし） |
| `ask` | git push/merge/reset・docker exec/down・rm/mv など（毎回確認） |
| `deny` | curl/wget/ssh/sudo・main/develop への push・.env の読み書きなど（常に禁止） |
| `hooks.PreToolUse` | Bash 実行前に `pretooluse_guard.py` を呼び出して二重ガード |

#### settings.local.json（ローカル追加許可）

一時的なコマンド許可などを追記するファイル。git 管理対象外推奨。

#### .claude/skills/（カスタムスキル）

`/コマンド名` で呼び出せるプロンプトテンプレート。各ファイルに手順が書かれており、呼び出すと Claude が自動で実行する。

| スキル | 呼び出し | 役割 |
|--------|---------|------|
| `issue-bootstrap/SKILL.md` | `/issue-bootstrap [title]` | イシュー番号採番 → ファイル作成 → ブランチ作成 → GitHub Issue 登録 → Draft PR 作成 |
| `plan/SKILL.md` | `/plan I###` | 計画書 + テスト（manual/auto）+ レビュー枠 作成 → 承認待ちで停止 |
| `implement/SKILL.md` | `/implement I###` | 計画書に従って実装 → 自動テスト実行 → レビュー/テストに結果記録 → PR 更新 → ユーザー検証待ち |
| `fix-loop/SKILL.md` | `/fix-loop I###` | NG 内容を記録 → 差分計画作成 → 承認待ち → 修正 → 再テスト |
| `close/SKILL.md` | `/close I###` | open ファイルを closed へ移動 → PR 説明整備 → Merge 依頼 |

---

### docs/runbooks/（詳細ルール集）

CLAUDE.md から参照される詳細ルールをまとめたディレクトリ。

| ファイル | 役割 |
|---------|------|
| `workflow.md` | 開発フロー全体（Issue→Plan→Implement→Test→Close）・ブランチ戦略（3ブランチ）・承認ワークフロー・コマンド実行前説明ルール |
| `plan-writing-rules.md` | 計画書の書き方・必須記載項目（背景/受入条件/影響範囲/手順/テスト/ロールバック）・計画書と実装の一致性保証ルール・改善提案フォーマット |
| `issue-flow.md` | イシュー番号の採番ルール・作成〜クローズまでの 27 ステップ詳細フロー・各ファイルの命名規則 |
| `danger-ops.md` | 危険操作の定義（DROP/TRUNCATE/force push/rm -rf など）・実行時の必須条件（計画書明記 + 明示承認 + `DANGER_OK=1`） |
| `common-commands.md` | 開発環境起動・ログ確認・テスト実行・エラー調査コマンド一覧 |
| `backend-check.md` | モデル・DB 整合性チェック手順・API 統合テスト手順・要件適合性検証手順・修正完了の判定基準 |
| `review-rules.md` | レビューファイルの命名規則（reviewXXX_IXXX）・作成タイミング・必須記載項目・文書間の相互参照ルール |
| `ux-rules.md` | フロントエンド実装時の UX 必須確認事項（エラー処理・ローディング・フォーム・ナビゲーション・アクセシビリティ）・計画書への UX セクション必須記載 |
| `template-sync.md` | ルール変更時にテンプレートファイルを同時更新するための手順・チェックリスト |

---

### docs/（作業ドキュメント）

実際の開発作業で Claude Code が生成・更新するファイル群。

```
状態管理: open（作業中）→ in_progress（処理中）→ closed（完了）
```

| ディレクトリ | 命名規則 | 役割 |
|-------------|---------|------|
| `docs/issues/` | `XXX.md`（3桁連番） | 作業チケット。何を実装するかの定義 |
| `docs/plans/` | `plan_IXXX_概要.md` | 実装前に作成する計画書。承認なしに実装不可 |
| `docs/tests/` | `test_IXXX_manual.md` / `test_IXXX_auto.md` / `error_IXXX.md` | テスト手順書・エラー管理 |
| `docs/reviews/` | `reviewXXX_IXXX.md` | 品質記録。実装前に枠作成、実装後に結果を記入 |

---

### rules/（コーディング規約）

実装時に Claude Code が参照するコーディング標準。

| ファイル | 対象 | 役割 |
|---------|------|------|
| `ultimate_django_coding_standards.md` | Backend | Django REST Framework のモデル・ビュー・シリアライザー・テスト等の規約 |
| `react-coding-standards-integrated.md` | Frontend | React TypeScript のコンポーネント設計・状態管理・型定義等の規約 |

---

### scripts/claude/hooks/pretooluse_guard.py（安全フック）

**役割**: Bash ツール実行前に呼び出されるガードスクリプト。settings.json の deny リストを超えた危険操作を二重にブロックする。

---

### .github/workflows/plan-gate.yml（CI ゲート）

**役割**: PR マージ前に自動チェックを実行する GitHub Actions ワークフロー。

---

## スキル実行フロー（全体像）

```
[ユーザー指示]
      │
      ▼
/issue-bootstrap [title]
  → docs/issues/open/XXX.md 作成
  → feature/IXXX-xxx ブランチ作成
  → GitHub Issue 登録
  → Draft PR 作成
      │
      ▼ ユーザー確認 OK
      │
/plan I###
  → docs/plans/open/plan_IXXX_概要.md
  → docs/tests/open/test_IXXX_manual.md
  → docs/tests/open/test_IXXX_auto.md
  → docs/reviews/open/reviewXXX_IXXX.md（枠のみ）
  → ★ 承認待ちで停止
      │
      ▼ ユーザー「OK」
      │
/implement I###
  → コード実装（計画書の範囲内のみ）
  → 自動テスト実行
  → レビュー・テストに結果記録
  → commit/push・PR 更新
  → ★ ユーザー手動テスト待ち
      │
      ├─ NG → /fix-loop I### → 差分計画 → 承認 → 修正 → 再テスト
      │
      ▼ ユーザー「OK」
      │
/close I###
  → 全ドキュメントを open → closed に移動
  → PR 説明整備
  → Approve & Merge をユーザーに依頼
```

---

## 権限の二重ガード構造

```
ユーザーの指示
      │
      ▼
Claude Code がツール呼び出し
      │
      ▼
[1st ガード] settings.json の allow/ask/deny
  allow → 自動実行
  ask   → ユーザーに確認プロンプト
  deny  → ブロック
      │
      ▼（Bash の場合のみ）
[2nd ガード] pretooluse_guard.py（PreToolUse hook）
  危険パターン検知 → 強制ブロック
```
