# I117 自動テスト: auto_test テンプレートの実行コマンド例示を決定論ゲートセクションへ一本化

実行コマンド: `bash scripts/claude/tests/test_auto_test_template_lint.sh`（決定論ゲートとして下記セクションで実走。pytest/Jest/E2E はアプリコード変更なしのため非該当）

結果:
- backend: 非該当（コード変更なし）
- frontend: 非該当（コード変更なし）
- 専用テスト（test_auto_test_template_lint.sh）: **全 TC 合格・exit 0**（2026-07-18 実装時実走。スクリプト自体の不合格経路も実証済み: コピーの複製パターンを故意に破壊 → TC-07 NG・exit 1）

## テストケース一覧（スクリプト内 TC）

| TC | 検証内容 | 期待値 | 結果 |
|----|---------|--------|------|
| TC-01 | テンプレのゲートセクション外に fenced ```bash/```sh ブロックが 0 件（heavy 含む全 fenced が対象・AC1） | 件数 0 | OK（0 件） |
| TC-02 | 冒頭誘導注記の存在（「決定論ゲート（自動実走）」への誘導＋omission-lint 言及・AC2） | grep ヒット | OK |
| TC-03 | omission_lint() の 5 検知パターンに対応する 6 キーワード（`bash scripts/claude/tests/`・`grep -q`・`grep -L`・`python3 -m json.tool`・`bash -n`・`python3 -m py_compile`）がゲートセクション内コメントに全て存在し、セクション外に列挙の複製が無い（AC3） | 6/6 存在・複製 0 | OK（6/6・複製 0） |
| TC-04 | 是正後テンプレに omission-lint ロジック適用 → OK（AC4） | OK | OK |
| TC-05 | ゲートセクションに実コマンドを記載した生成文書 → OK（AC4） | OK | OK |
| TC-06 | decoy 反証: セクション外 fenced に allowlist コマンド注入 → HIGH 検知（false-green 防止・AC5） | HIGH | OK（HIGH 検知） |
| TC-07 | スクリプトの複製 grep パターンが code-review.sh の I084-OM-GREP 行と一致（乖離検知） | 一致 | OK（一致） |

- 合否インターフェース: **合格 = exit 0**（いずれかの TC 失敗で非ゼロ終了＋NG 内容を出力）。
- 計画時実証（2026-07-17・/grill-me）: TC-04/05/06 相当のロジックを omission_lint() と同一実装で実走済み — 現テンプレ OK・罠注入 **HIGH**（失敗条件注入で不合格になることを確認済み＝false-green でない）・是正後 OK・完成文書 OK。

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_auto_test_template_lint.sh
```
