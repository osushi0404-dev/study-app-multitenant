---
name: implement
description: Implement an approved plan, run type checks, push to PR.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /implement

必読:
- docs/plans/open/plan_$ARGUMENTS.md
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/reviews/open/$ARGUMENTS_review.md

ルール:
- 計画書に書いていない実装は禁止。必要なら停止→提案→承認→計画更新。
- Danger Ops は danger-approved + DANGER_OK=1 が必須。
- テストフレームワーク（pytest 等）が存在しない・追加が必要な場合はユーザーに承認を得てからインストールする。
- 既存テストファイルのフレームワーク・形式（pytest / Django TestCase 等）を変更する場合もユーザーの承認が必須。承認なしの形式変更は禁止。

前提:
- /plan-issue の承認（「OK」「承認」等）だけでは実装を開始しない
- ユーザーが明示的に /implement を実行して初めて実装を開始する

手順:
━━ 【新規の振る舞いを追加する場合】新しいエンドポイント・ビジネスロジック・コンポーネントの追加が対象 ━━
先に TDD サイクルを完了してから 1) へ進む（強制。テストを書かずに 1) を開始した場合は STOP）。

[Red フェーズ]
- `docs/tests/open/$ARGUMENTS_auto_test.md` を読み、対象の振る舞いに対応するテストコードを先に実装する
- 認証・認可・テナント境界を検証するテストも必ずこの時点で実装する
- Backend（ローカル）: `python -m pytest <対象テストファイル> --tb=short` を実行し、テストが失敗することを確認する
- Frontend（ローカル）: `npm test -- --watchAll=false --testPathPattern=<対象テスト>` を実行し、テストが失敗することを確認する
- テストが失敗しない場合は STOP → ユーザーに報告してテスト内容を確認する

[Green フェーズ]
- テストを通過させる最小限の実装を行う
- 同じコマンドでテストが通過することを確認してから Refactor へ進む

[Refactor フェーズ]
- 可読性改善・重複削除など内部整理のみ行う
- 新機能追加・設計変更は計画書更新が必要（STOP → 提案 → 承認 → 計画書更新）

**注**: TDD サイクル中のテスト実行は「高速フィードバック確認」が目的でローカル実行で十分。
     `/test` スキルは「環境パリティを含む最終確認」が目的であり役割が異なる。

━━ 【それ以外（バグ修正・リファクタ・既存コード変更）】TDD は任意。1) から開始する ━━

1) 計画どおり実装
   - セキュリティ・ベストプラクティス・モダン開発の観点で最適な実装を採用する
   - より良い方法がある場合は plan-writing-rules.md の「改善提案フォーマット」に従い提案してから実装する
2) ビルド・型チェック・リント・セキュリティスキャンを実行してクリーンを確認:
   - Backend: flake8（全エラー修正）/ bandit（MEDIUM 以上を修正対象。LOW は # nosec で抑制・理由記載必須）/ 未使用変数・import の残留がないこと
   - Frontend: react-scripts build（型チェック）/ ESLint（error を修正対象、warning は記録）/ npm audit（high/critical を修正対象、moderate は記録・期限設定）
   - 修正対象の警告・エラーがある場合は修正してから次のステップへ
3) commit/push して PR を更新
4) 停止し以下を案内:
   ```
   ✅ push 完了。
   👉 `/code-review $ARGUMENTS` を実行してください。
   ```
