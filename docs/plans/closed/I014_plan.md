# I014 計画書: /implement 細分化・/code-review・/test スキル新設

## 基本情報
- **計画書ID**: plan_I014
- **関連イシュー**: docs/issues/open/014.md
- **作成日**: 2026-03-27

---

## 背景/目的

現在の `/implement` スキルは「実装 → 自動テスト → push → CI 確認 → 手動テスト」を一括実行する。
これにより以下の問題がある：

- コードレビュー（要件面の確認）が自動テスト実行より前に存在しない
- CI を挟んだ品質ゲートフローが実現できていない

本計画では以下の新フローを実現する：

```
/implement（実装+push）
  ↓
/code-review I###（CI 確認 + 要件照合）
  ↓ OK                ↓ NG
/test I###         /fix-loop I### → /code-review に戻る
  ↓ OK                ↓ NG
/close I###        /fix-loop I### → /test に戻る
```

---

## 受け入れ条件

- [ ] `/implement I###` は実装・型チェック・push のみを行い、自動テストを実行しない
- [ ] `/code-review I###` を実行すると CI 確認→受け入れ条件照合を行いユーザーに OK/NG を求める
- [ ] `/test I###` を実行すると自動テスト（pytest + Jest）→手動テスト確認を行う
- [ ] `workflow.md` のフロー定義・移行案内テーブルが新フローに更新されている
- [ ] 既存の `/fix-loop` `/close` スキルが新フローと整合している（スキル自体の変更なし）

---

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `.claude/skills/implement/SKILL.md` 変更
  - `.claude/skills/code-review/SKILL.md` **新規作成**
  - `.claude/skills/test/SKILL.md` **新規作成**
  - `docs/runbooks/workflow.md` 更新

---

## 変更点一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `.claude/skills/implement/SKILL.md` | 変更 | 自動テスト・CI 確認・手動テスト手順を削除。push 後に `/code-review` を案内して停止 |
| `.claude/skills/code-review/SKILL.md` | **新規** | CI 確認 + 受け入れ条件照合スキル |
| `.claude/skills/test/SKILL.md` | **新規** | 自動テスト + 手動テスト確認スキル |
| `docs/runbooks/workflow.md` | 変更 | フロー定義・移行案内テーブルを新フローに更新 |

---

## 設計

### `/implement` 変更後の手順

```
1) 計画どおり実装
2) ビルド・型チェックを実行してクリーンを確認
3) commit/push して PR を更新
4) 停止し以下を案内:
   ✅ push 完了。
   👉 `/code-review I###` を実行してください。
```

除去するもの（現行 implement から削除）:
- step 3: pytest 環境確認
- step 4: 自動テスト実行
- step 5: docs/reviews・docs/tests への記録（→ /test に移動）
- step 6a: CI 確認（→ /code-review の冒頭に移動）
- step 7: 手動テスト確認（→ /test に移動）

### `/code-review` の手順（新規）

```
前提: /implement 完了・push 済み

1) CI 確認:
   gh pr checks [PR番号]
   - 全ジョブ pass: 手順 2) へ
   - pending: 数分待って再確認
   - 失敗あり: STOP。「CI が失敗しています。修正して再 push してください」と報告

2) 計画書・イシューの受け入れ条件を読む:
   - docs/issues/open/I###.md
   - docs/plans/open/I###_plan.md

3) 実装差分を確認:
   git diff origin/develop...HEAD

4) 各受け入れ条件の照合結果を以下の形式で報告:
   ## コードレビュー結果
   | # | 受け入れ条件 | 実装状況 | 備考 |
   |---|------------|---------|------|
   | 1 | ...        | ✅ 実装済み / ⚠️ 一部不足 / ❌ 未実装 | ... |

5) コードの品質・ロジック上の問題があれば追記

6) ユーザーに OK/NG 判断を求める:
   - OK → 「✅ レビュー完了。/test I### を実行してください。」
   - NG → 「❌ レビュー NG。/fix-loop I### を実行してください。」
```

ツール制限: Read, Bash, Glob, Grep のみ（Write/Edit 禁止 = コード変更しない）

### `/test` の手順（新規）

```
前提: /code-review OK

1) Backend 自動テスト:
   cd backend && python -m pytest --tb=short -q
   - 成功: 手順 2) へ
   - 失敗: STOP。失敗テスト名・エラーを報告し /fix-loop を案内

2) Frontend 自動テスト:
   cd frontend && npm test -- --watchAll=false
   - 成功: 手順 3) へ
   - 失敗: STOP。失敗テスト名・エラーを報告し /fix-loop を案内

3) docs/reviews と docs/tests に結果を記録

4) 手動テスト確認項目を提示（テスト計画書に基づく）:
   ## 手動テスト確認項目
   | # | 確認内容 | 操作手順 | 期待結果 | 結果(OK/NG) |

5) ユーザーテスト結果を受け取る:
   - OK → 「✅ テスト完了。/retro I### または /close I### を実行してください。」
   - NG → /fix-loop I### を案内
```

### `workflow.md` 更新内容

フロー定義（現行）:
```
3. /implement I### → 実装＆自動検証 → ユーザー検証（OK/NG）
4. NG の場合 /fix-loop I###
5. OK の場合 /close I###
```

フロー定義（更新後）:
```
3. /implement I### → 実装・型チェック・push
4. /code-review I### → CI 確認＋要件照合（OK/NG）
   NG の場合 /fix-loop I### → /code-review に戻る
5. /test I### → 自動テスト＋手動テスト確認（OK/NG）
   NG の場合 /fix-loop I### → /test に戻る
6. OK の場合 /close I###
```

移行案内テーブル（更新後）:
| タイミング | Claude がやること |
|-----------|-----------------|
| 計画書承認後 | `/implement I###` を入力してください |
| implement 完了後 | `/code-review I###` を入力してください |
| code-review OK 後 | `/test I###` を入力してください |
| code-review NG 後 | `/fix-loop I###` を入力してください（fix 後 `/code-review` に戻る） |
| test NG 後 | `/fix-loop I###` を入力してください（fix 後 `/test` に戻る） |
| test OK 後 | `/retro I###` または `/close I###` を入力してください |

---

## 実装手順

### Step 1: `.claude/skills/implement/SKILL.md` 変更

自動テスト・CI 確認・手動テスト手順を削除し、push 後に `/code-review` を案内して停止するよう変更。

### Step 2: `.claude/skills/code-review/SKILL.md` 新規作成

ディレクトリ `.claude/skills/code-review/` を作成し `SKILL.md` を配置。

### Step 3: `.claude/skills/test/SKILL.md` 新規作成

ディレクトリ `.claude/skills/test/` を作成し `SKILL.md` を配置。

### Step 4: `docs/runbooks/workflow.md` 更新

フロー定義・移行案内テーブルを新フローに変更。

---

## テスト計画

### 自動テスト
なし（スキルファイルはテキスト定義ファイルのため、自動テスト対象外）

### 手動テスト
docs/tests/open/I014_manual_test.md 参照

---

## ロールバック

- `git revert` で各スキルファイルを元に戻す
- または `.claude/skills/implement/SKILL.md` を変更前の内容に手動で戻す
- `/code-review` `/test` ディレクトリを削除する

---

## Risk & 回避策

| リスク | 回避策 |
|-------|-------|
| fix-loop 後の復帰先が不明確になる | workflow.md の移行案内テーブルに fix-loop 後の復帰先を明記する |
| CI 待ちで /code-review がブロックされる | pending 時は待機してから再確認するよう /code-review に明記 |
| /test スキルが /fix-loop と重複してテストを実行する | fix-loop は自前でテストを持つ設計を維持し、/test は fix-loop 後に呼ばれないよう workflow に明記 |

---

## 承認ポイント
（ユーザー確認後に記入）
