# I545 自動テスト: コードの書き方の決まりをベストプラクティスのあるべき状態に見直す

実行コマンド: 文書だけの変更のため、pytest・Jest・E2E は CI に任せる（このイシューでは足さない）。

結果:
- backend: 対象外（変更なし）
- frontend: 対象外（変更なし）

## テストケース
| TC | 確かめること | 合否 | 失敗の注入（FG） |
|---|---|---|---|
| TC-01 | 規約 2 本の冒頭に「前提の版」の節がある | 下のゲートの 1〜2 行目が exit 0 | 実装前の今の規約で実行し、exit 1（不合格）になることを確認 |
| TC-02 | 正でない規約 4 本が `rules/` 直下に無い | ゲートの 3〜6 行目が exit 0 | 実装前の今（4 本がある）で実行し、exit 1 になることを確認 |
| TC-03 | `rules/bk/` の控えが無い | ゲートの 7〜10 行目が exit 0 | 実装前の今（控えがある）で実行し、exit 1 になることを確認 |
| TC-04 | `docs/runbooks/issue-flow.md` が「`/rules/` 配下の関連ルールファイル」と書かず、正の 2 本を名指ししている | ゲートの 11〜13 行目が exit 0 | 実装前の今の `issue-flow.md` で実行し、11 行目が exit 1 になることを確認 |
| TC-05 | `docs/runbooks/backend-check.md` に curl で API を叩く手順（`curl -X`・`curl -s`・`curl http…` の形のどれも）が残っていない | ゲートの 14 行目が exit 0 | 実装前の今（curl の手順がある）で実行し、exit 1 になることを確認 |
| TC-06 | `docs/runbooks/ux-rules.md` に計画書の UX の節のひな形が残っていない | ゲートの 15 行目が exit 0 | 実装前の今（ひな形がある）で実行し、exit 1 になることを確認 |

FG の記録（計画の時点・実装前）: 下の「FG の実行記録」に書く。

## 決定論ゲート（自動実走）
```bash
grep -q "前提の版" rules/ultimate_django_coding_standards.md
grep -q "前提の版" rules/react-coding-standards-integrated.md
! grep -qs "" rules/backend-django-coding-standards.md
! grep -qs "" "rules/backend_python_django_coding_guidelines（cursor_claude_code）v_1.md"
! grep -qs "" "rules/frontend_react_coding_guidelines（cursor_claude_code）v_1.md"
! grep -qs "" rules/react-coding-standards.md
! grep -qs "" rules/bk/backend-django-coding-standards.md
! grep -qs "" "rules/bk/backend_python_django_coding_guidelines（cursor_claude_code）v_1.md"
! grep -qs "" "rules/bk/frontend_react_coding_guidelines（cursor_claude_code）v_1.md"
! grep -qs "" rules/bk/react-coding-standards.md
! grep -q "配下の関連ルールファイル" docs/runbooks/issue-flow.md
grep -q "rules/ultimate_django_coding_standards.md" docs/runbooks/issue-flow.md
grep -q "rules/react-coding-standards-integrated.md" docs/runbooks/issue-flow.md
! grep -qE "curl +(-|http)" docs/runbooks/backend-check.md
! grep -q "### 改善後のユーザー体験" docs/runbooks/ux-rules.md
```

## FG の実行記録
- 2026-11-17（計画の時点・実装前）: ゲートの 15 行を 1 行ずつ `bash -c` で実行し、15 行すべて exit 1（不合格）。実装前の状態（前提の版の節が無い・古い規約と控えがある・issue-flow が名指ししていない・backend-check に curl の手順・ux-rules にひな形）を捕まえることを確認した
- 同日・合格側の確認: 無いファイルに `! grep -qs ""` が exit 0、無い文言に `! grep -q` が exit 0（直した後の状態で合格する形であることを確認）
- 同日・計画レビューの Warning で TC-05 を `curl +(-|http)` に広げた: 今の backend-check.md で exit 1、`TOKEN=$(curl -s http://x)` と `curl http://x` を入れた写しで exit 1、「curl で API を叩く手順は使わない」という文だけの写しで exit 0（文中の言及は捕まえない）
- 実装後の合否は review-gate の決定論ゲートの実走で記録する
