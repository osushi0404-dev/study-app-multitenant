# Claude Code ファイル構成一覧

このプロジェクトで Claude Code（バイブコーディング）が参照するファイルの全体像をまとめたリファレンスです。

> **I193（2026-10）で開発の流れを組み直しました。** スキルの構成・呼び出し方・止める条件の正は `docs/runbooks/workflow.md`、設計の根拠は `docs/proposals/I193_official_base_flow.md` です。この文書の後半（各スキルの詳細・フロー図）には I193 より前の書き方が残っている箇所があり、食い違うときは workflow.md を正とします。

---

## ディレクトリ構成（全体図）

```
study-app-multitenant/
│
├── CLAUDE.md                                ← [★ 起点] プロジェクト憲法・絶対ルール
│
├── .claude/                                 ← Claude Code 設定ディレクトリ
│   ├── settings.json                        ← 権限設定（allow / ask / deny）+ hooks
│   ├── settings.local.json                  ← ローカル権限の一時的な追加許可
│   ├── agents/                              ← レビュー役（公式のサブエージェント定義・tools で読み取り専用）
│   └── skills/                              ← カスタムスキル
│       ├── issue-bootstrap/SKILL.md         ← /issue-bootstrap（ユーザーが打つ）
│       ├── grill-me/SKILL.md                ← /grill-me（ユーザーが打つ・任意）
│       ├── plan-issue/SKILL.md              ← /plan-issue（ユーザーが打つ）
│       ├── proceed/SKILL.md                 ← /proceed（ユーザーが打つ・途中から再開）
│       ├── plan-review/SKILL.md             ← 段階（以下、ユーザーは打たない）
│       ├── design-security-review/SKILL.md
│       ├── implement/SKILL.md
│       ├── review-gate/SKILL.md
│       ├── test-gate/SKILL.md
│       ├── fix-loop/SKILL.md
│       ├── retro/SKILL.md
│       └── close/SKILL.md
│
├── docs/
│   ├── runbooks/                            ← 詳細ルール集（CLAUDE.md から参照）
│   │   ├── workflow.md                      ← 流れ・段階・止めて聞く条件・ブランチ戦略
│   │   ├── plan-writing-rules.md            ← 計画書・テスト文書の書き方
│   │   ├── issue-flow.md                    ← イシューの扱い（番号・置き場所・起票・ラベル）
│   │   ├── danger-ops.md                    ← 危険操作・サンドボックス・見張り
│   │   ├── common-commands.md               ← よく使うコマンド集
│   │   ├── backend-check.md                 ← バックエンドを変えたときの確かめ方
│   │   ├── review-rules.md                  ← レビューの決まり・記録の名前
│   │   ├── ux-rules.md                      ← 画面の使い勝手の原則・確かめること
│   │   └── （ほかの手順書の一覧は CLAUDE.md「0. 参照先」）
│   │
│   ├── issues/                              ← イシューの写し（I427 以降の正は GitHub・docs/runbooks/issue-flow.md）
│   │   ├── open/I###.md                     ← /plan-issue が写して commit
│   │   ├── closed/I###.md                   ← close で移す
│   │   └── templates/issue_template.md      ← イシュー作成テンプレート
│   │
│   ├── plans/                               ← 計画書
│   │   ├── open/plan_I###.md                ← 作業中
│   │   ├── closed/                          ← 完了済み
│   │   └── templates/plan_template.md       ← 計画書テンプレート（形の正）
│   │
│   ├── tests/                               ← テスト文書
│   │   ├── open/I###_manual_test.md         ← 手動テスト（実施者は原則 Claude）
│   │   ├── open/I###_auto_test.md           ← 自動テスト・決定論ゲート
│   │   ├── closed/
│   │   └── templates/                       ← manual_test_template.md・auto_test_template.md
│   │
│   └── reviews/                             ← レビューの記録（名前の正は docs/runbooks/review-rules.md）
│       ├── open/I###_review.md              ← 段階の結線（STAGE_DONE）・自律判断の記録
│       ├── I###_code_review_<ts>.md など    ← 各段階のレビューの監査記録
│       ├── backlog/I###.md                  ← 止めない軽い指摘の一覧
│       ├── closed/                          ← 完了済み
│       └── templates/review_template.md     ← レビューテンプレート
│
├── rules/                                   ← コーディング規約（実装時に参照）
│   ├── ultimate_django_coding_standards.md  ← バックエンド規約（Django / DRF）
│   └── react-coding-standards-integrated.md ← フロントエンド規約（React / TypeScript）
│
├── scripts/
│   └── claude/                              ← 段階のスクリプト・レビュー役の起動・テスト
│       └── hooks/
│           └── pretooluse_guard.py          ← 危険操作をブロックする安全フック（PreToolUse）
│
└── .github/
    └── workflows/                           ← ci.yml・e2e.yml・dependency-audit.yml（必須チェックは docs/runbooks/branch-protection-setup.md §2）
```

---

## ファイル別・役割詳細

### CLAUDE.md（プロジェクト憲法）

**役割**: Claude Code が会話開始時に自動で読み込む「憲法ファイル」。詳細ルールは各 runbook に委譲し、このファイル自体は短く保つ設計。

#### 絶対ルール（5 箇条）

中身の正は `CLAUDE.md`「1. 絶対ルール」（この文書には写さない）。計画外の実装をしない・ユーザーの確認は止めて聞く条件のときだけ・develop/main への直 push 禁止（GitHub のブランチ保護が止める）・危険操作は承認制（`docs/runbooks/danger-ops.md`）・記録を残す、の 5 つ。

#### 参照先

一覧と役割の正は `CLAUDE.md`「0. 参照先」（この文書には写さない）。

---

### .claude/settings.json（権限設定）

権限（allow / ask / deny）・フック・サンドボックスの設定の正は `.claude/settings.json` そのもの。守りの考え方（3 層・見張りが何を止めるか）の正は `docs/runbooks/danger-ops.md`（この文書には写さない）。

`git push` は安全な feature push を allow（確認なし）にする。**保護ブランチ（develop/main）を宛先とする push は、I430 から GitHub のブランチ保護（PR 必須・bypass 不可・Restrict who can push。bot は push できない）に任せ、フックの判定は消した**（`deny` はテキストで自明な形のバックストップとして残す）。フックは force push・`--all`/`--mirror`・push の宛先や強制を変える設定を止める（`docs/runbooks/danger-ops.md`）。Bash は公式のサンドボックスの中で動き、`git` はその外で動く（同上「サンドボックス（第 1 層）」）。

> **force push の取りこぼしへの対応（I083 で対応済み）**: force の判定は push の部分ごとの語の走査（`_push_has_force`）で、`-f`・`-uf`・`--force-with-lease`・複合コマンドも捕まえる。
> - **残余の既知限界（脅威モデル外）**: push の語を完全に隠蔽する形（`eval "$VAR"`・`sh -c "$CMD"`）は対象外。脅威モデルは「事故による force push の防止」。

---

### .claude/settings.local.json（ローカル追加許可）

**役割**: セッションや作業ごとに一時的なコマンド許可を追記するファイル。

- settings.json と同じ形式で `permissions.allow` に追記する
- `.gitignore` への追記を推奨（機密性の高い一時許可を共有しないため）
- 例：特定の migration コマンドや一時的な調査コマンドを許可する際に使用

---

### .claude/skills/（カスタムスキル）

`/コマンド名` で呼び出せるプロンプトテンプレート。各 `SKILL.md` に Claude が実行すべき手順が記述されており、呼び出すと Claude がその手順に従って自動的に処理を進める。

各スキルの手順の正は `.claude/skills/<名前>/SKILL.md`、段階の流れと呼び方の正は `docs/runbooks/workflow.md`「使うスキル」「フロー」、書き方の確認は `docs/runbooks/review-rules.md`「スキルファイル変更時の Claude Code ベストプラクティス準拠（必須）」。この文書には写さない。

---

### docs/runbooks/（詳細ルール集）

CLAUDE.md から参照される詳細ルールをまとめたディレクトリ。Claude Code は実装前・実装中に該当ファイルを参照する。各手順書の中身の正は手順書そのもので、この文書には写さない（一覧と役割は `CLAUDE.md`「0. 参照先」）。

| 手順書 | 役割 |
|---|---|
| `workflow.md` | 使うスキル・段階の流れ・止めて聞く条件・ゲート・ブランチ戦略 |
| `plan-writing-rules.md` | 計画書・テスト文書の書き方（形の正はテンプレート）・計画変更記録・実施者の区別 |
| `issue-flow.md` | イシューの番号・置き場所・起票・ラベル |
| `review-rules.md` | 検証の全体設計・止める基準・敵対的レビュー・記録の名前 |
| `danger-ops.md` | 危険操作の承認・サンドボックス・見張り・GitHub から復旧できる範囲・外部 PR |
| `worktree.md` | 並行トラック（ワークツリー）の運用 |
| `common-commands.md` | よく使うコマンド |
| `backend-check.md`・`ux-rules.md` | バックエンドの確かめ方・画面の使い勝手の原則 |

---

### docs/（作業ドキュメント）

イシューごとに Claude Code が作る記録。名前・置き場所・作るタイミングの正は、`docs/runbooks/workflow.md`「ディレクトリ規約」・`docs/runbooks/review-rules.md`（レビューの記録の名前）・各テンプレート。

---

### rules/（コーディング規約）

実装時に Claude Code が参照するコーディング標準。`/plan` や `/implement` のスキルが参照する必読ファイル。

| ファイル | 対象 | 主な規約内容 |
|---------|------|-----------|
| `ultimate_django_coding_standards.md` | Backend | このプロジェクトのバックエンドの書き方の決まり（節は本文の見出し） |
| `react-coding-standards-integrated.md` | Frontend | このプロジェクトの画面の書き方の決まり（節は本文の見出し） |

どちらも冒頭に前提の版と点検した日、最後に今のコードとの差（移行のイシュー）を持つ（I545）。

---

### scripts/claude/hooks/pretooluse_guard.py（安全フック）

**役割**: `settings.json` の deny リストに加え、パターンマッチで危険な Bash コマンドをプログラム的にブロックする二重ガード。

- Claude Code が Bash ツールを呼び出すたびに自動実行される（PreToolUse フック）
- コマンド内容を解析し、危険なパターン（`DROP TABLE`・`rm -rf`・`force push` 等）を検知したらブロックして理由を返す
- settings.json だけでは防げない動的なコマンド合成にも対応

---

## スキル実行フロー（全体像）

流れの正は `docs/runbooks/workflow.md`「フロー」（この文書には写さない）。

---

## 権限の守りの構造

守りは 3 層（Bash のサンドボックス・見張りのフック・GitHub のブランチ保護）。正は `docs/runbooks/danger-ops.md`。下の図は settings.json と見張りの 2 つの関係だけを示す。

```
ユーザーの指示
      │
      ▼
Claude Code がツール（Bash）を呼び出し
      │
      ▼
┌─────────────────────────────────────┐
│ [1st ガード] settings.json          │
│                                     │
│  allow → 自動実行                    │
│  ask   → ユーザーに確認プロンプト      │
│  deny  → ブロック（実行不可）          │
└─────────────────────────────────────┘
      │（Bash ツールの場合のみ）
      ▼
┌─────────────────────────────────────┐
│ [2nd ガード] pretooluse_guard.py    │
│ （PreToolUse hook）                 │
│                                     │
│  危険パターン検知 → 強制ブロック        │
│  正常パターン    → 通過              │
└─────────────────────────────────────┘
      │
      ▼
実行
```

deny の中身の正は `.claude/settings.json`（この文書には写さない）。

---

## ファイル間の依存関係

```
CLAUDE.md（起点）
  │
  ├─ 参照 ──→ docs/runbooks/*.md（詳細ルール）
  │             ├─ workflow.md
  │             ├─ plan-writing-rules.md  ←── plan-issue が必読
  │             ├─ issue-flow.md          ←── /issue-bootstrap が参照
  │             ├─ backend-check.md       ←── バックエンドを変えたときの確かめ方
  │             ├─ review-rules.md        ←── plan-issue・implement・close の段階が参照
  │             └─ ...
  │
  ├─ 参照 ──→ rules/*.md（コーディング規約）
  │             ├─ ultimate_django_coding_standards.md  ←── plan-issue・implement の段階が必読
  │             └─ react-coding-standards-integrated.md ←── plan-issue・implement の段階が必読
  │
  └─ 参照 ──→ .claude/settings.json（権限）
                └─ hooks → scripts/claude/hooks/pretooluse_guard.py
```
