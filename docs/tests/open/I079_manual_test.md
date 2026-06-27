# I079 手動テスト（権限プロンプト挙動）

実装（deny 追加・コミット）完了後、**設定が反映された新規セッション**で確認する。
権限プロンプトの有無はセッション内での実操作で観測する（自動化できないため Claude が実操作を試み、プロンプト発生を観測して記録する）。

> ⚠️ **前提（必須）: デフォルト権限モードで実施すること。** `acceptEdits` / `auto` モードでは Edit/Write が自動承認/自動実行され allow/deny が評価されないため検証にならない（モード循環: default→accept edits→plan→auto、Shift+Tab）。
>
> Claude Code では `deny` は「プロンプト」ではなく「**ブロック（自動拒否＝ツールがエラーを返す）**」。期待結果はすべて「ブロックされる」と読む。
>
> 🔴 **fix-loop I079 の確定結論（2026-06-27・default モードで実測）**:
> **Edit/Write では、パスが allow と deny の両方に一致すると allow が優先され、deny は上書きしない。** deny が効くのは allow と重複しないパスのみ。
> - 根拠: `./.env`（deny のみ）の Read は **ブロック**された＝deny 自体は機能（モード由来でない）。一方 `backend/Dockerfile`・`migrations`（broad allow と重複）の Edit は **ブロックされず成功**。
> - 帰結: 高リスク群は `backend/**`・`frontend/**` 配下のため deny で保護**できていない**。→ fix-loop で修正方式（案A `./`アンカー / 案B narrow allow）を決定し再検証する。

### 旧設計（settings `deny`）での実測 — 2026-06-27 default モード（記録）
| No | 手順 | 旧期待 | 実結果 | 備考 |
|---:|------|--------|--------|------|
| M1 | `backend/problems/views.py` を Edit | 通る（allow） | ✅ OK | allow 機能 |
| M2 | `backend/Dockerfile`（deny）を Edit | ブロック | ❌ FAIL（通った） | deny が allow に負ける |
| M3 | `migrations/0001_*.py`（deny）を Edit | ブロック | ❌ FAIL（通った） | 同上 |
| M_env 対照 | `./.env`（deny のみ）を Read | ブロック | ✅ OK（ブロック） | deny 自体は機能＝重複時のみ allow 優先 |

→ **旧設計は ❌ NG**。原因確定（重複 allow 下で deny 不発）。**案D（PreToolUse フックで保護）に変更**。

### 案D（フックで高リスク Edit/Write をブロック）での再検証 — フック実装後に実施
| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1' | `backend/problems/views.py` を Edit | プロンプトなしで成功（素通し） | Claude | ⏳ 実装後 | broad allow 維持（フックは ask を出さない） |
| M2' | `backend/Dockerfile` を Edit | **フックが ask＝プロンプトが出る**。承認すれば編集可 | Claude | ⏳ 実装後 | TC-H1 と整合 |
| M3' | `migrations/0001_*.py` を Edit | **プロンプトが出る（ask）** | Claude | ⏳ 実装後 | パスに `/migrations/` |
| M4' | `frontend/package.json` を Edit | **プロンプトが出る（ask）** | Claude | ⏳ 実装後 | サプライチェーン |
| M5' | `./.env`/`secrets` の Read/Edit | 既存 settings `deny` で**ブロック維持** | Claude | ⏳ 実装後 | フックでなく settings deny が担当（ask でなくブロック） |

注: 旧設計の検証用コメント追記は `git checkout` で revert 済み（無改変）。M_env/M5' は Read 中心（無改変）。案D の挙動確認は **default モード**で行う（acceptEdits/auto では Edit が素通り）。フック単体の決定論検証は自動テスト TC-H1〜H3（`I079_auto_test.md`）が主、本手動テストは統合挙動の最終確認。
