# I185 自動テスト: 開発環境の総点検と改善

実行コマンド: 下の「決定論ゲート」を `/code-review` が実走する（heavy なテストは無し。段 A は文書の追加のみ）

対象ファイル: `docs/proposals/I185_dev_env_review.md`（段 A のステップ 3 で作成）

| TC | 確かめること | 合否（exit code） |
|---|---|---|
| TC-01 | 観点一覧の見出し `## 1. ベストプラクティスの観点` がある | 合格=0 |
| TC-02 | 公式ドキュメントの出典 URL（`https://code.claude.com/docs/`）が載っている | 合格=0 |
| TC-03 | 記録の数字の見出し `## 2. 作業記録の数字` がある | 合格=0 |
| TC-04 | 数え方が「リポジトリ内の記録で数えるもの」に分けて書かれている | 合格=0 |
| TC-05 | 数え方が「手元の記録でしか数えられないもの」に分けて書かれている | 合格=0 |
| TC-06 | 漏れと手間の一覧の見出し `## 3. 止めている漏れとかかる手間` がある | 合格=0 |
| TC-07 | 公式機能との差分の見出し `## 4. 公式機能との差分` がある | 合格=0 |
| TC-08 | 改善案の見出し `## 5. 改善案` がある | 合格=0 |
| TC-09 | 採否の見出し `## 6. 採否` がある | 合格=0 |

段 B の TC（改善ごとの確かめ方）は、計画変更記録で本文書に追加する。

### 計画時の false-green 確認（2026-10-24）
- 見出しは行頭・行末を固定（`^...$`）して判定する。最初の案（固定なし）は、似た見出し「## 6. 採否の候補」でも合格してしまうことを、非対話の bash（`/usr/bin/grep`）で確かめたため直した。
- 似た見出し・欠けた見出しだけのおとりファイルで 9 件とも exit=1（不合格）、必要な見出しをすべて持つファイルで 9 件とも exit=0（合格）になることを確認済み。報告書が未作成の現時点では 9 件とも exit=2（不合格）。

結果:
- 段 A（報告書作成時・2026-10-24）: TC-01〜TC-09 すべて exit=0（非対話 bash の `/usr/bin/grep` で実走）

## 決定論ゲート（自動実走）
```bash
grep -q "^## 1\. ベストプラクティスの観点$" docs/proposals/I185_dev_env_review.md
grep -q "https://code\.claude\.com/docs/" docs/proposals/I185_dev_env_review.md
grep -q "^## 2\. 作業記録の数字$" docs/proposals/I185_dev_env_review.md
grep -q "^#### リポジトリ内の記録で数えるもの$" docs/proposals/I185_dev_env_review.md
grep -q "^#### 手元の記録でしか数えられないもの$" docs/proposals/I185_dev_env_review.md
grep -q "^## 3\. 止めている漏れとかかる手間$" docs/proposals/I185_dev_env_review.md
grep -q "^## 4\. 公式機能との差分$" docs/proposals/I185_dev_env_review.md
grep -q "^## 5\. 改善案$" docs/proposals/I185_dev_env_review.md
grep -q "^## 6\. 採否$" docs/proposals/I185_dev_env_review.md
```
