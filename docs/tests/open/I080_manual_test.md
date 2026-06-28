# I080 手動テスト（ハーネス権限レイヤー挙動）

決定論的なフック単体検証は `I080_auto_test.md`（TC-P/TC-S/TC-DOC）で担保。本書は **settings.json の権限レイヤー挙動**（allow/ask/deny の precedence・`DANGER_OK=1` 前置による deny 回避→フック danger-op 到達）を確認する。

> **実施環境列について**: これらの TC はハーネスの**権限モード／settings 権限のロード**に依存する。稼働中セッションは起動時にロードした settings を編集途中で再ロードしないため、編集後の挙動は**同セッションでは検証にならない**。該当 TC は「実施環境」列に明記した環境で実施する（plan-writing-rules §「ハーネス挙動テストの実施環境」準拠）。

| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|------|----------|----------|--------|--------|------|
| M1 | プレーン default の新規セッションを起動し、feature ブランチ上で `git push -u origin <feature>` を実行 | プロンプトが**出ずに**実行される（`ask: git push *` の shadow が解消され allow が効く） | プレーン default 新規セッション | Human | | I080 の主目的（安全 push 無確認化）の実証 |
| M2 | 同セッションで feature ブランチ上から `git push origin develop`（DANGER_OK 無し）を実行 | **遮断される**（deny ＋フックの二重）。push されない | プレーン default 新規セッション | Human | | 未承認 protected push のバックストップ確認 |
| M3 | 同セッションで `DANGER_OK=1 git push origin develop` を実行（実際の push は行わず、フックが block せず権限に到達するかを観測。安全のため存在しない一時 remote 等を使う） | フックの danger-op が**解除**され（exit 0 相当）、deny の glob を外れて release/hotfix 経路が成立する | プレーン default 新規セッション | Human | | release/hotfix の escape hatch 到達確認。実 develop へ push しないよう一時 remote で実施 |
| M4 | `bash scripts/claude/tests/test_pretooluse_push_guard.sh` を実行 | `pass=N fail=0`・exit 0。全 TC-P が PASS | 稼働中セッション可 | Claude | OK | pass=40 fail=0 を実走確認 |
| M5 | `python3 -m json.tool .claude/settings.json` ＋ allow/ask/deny を Read で確認 | JSON 有効・allow に `git push`/`git push *`・ask に `git push *` 不在・deny 維持 | 稼働中セッション可 | Claude | OK | TC-S1〜S5 全 PASS |

> M1〜M3 はハーネス権限挙動のため **Human がプレーン default 新規セッションで実施**。M4/M5 は Claude が稼働中セッションで実施可能（スクリプト実行・ファイル確認）。

## 実施結果（/test・2026-06-28）
- **M4（Claude）**: `test_pretooluse_push_guard.sh` → **pass=40 fail=0**（OK）。
- **M5（Claude）**: settings.json JSON 妥当・allow に `git push`/`git push *`・ask に `git push *` 不在・deny 維持・冗長エントリ削除（TC-S1〜S5 全 PASS）（OK）。
- **M1〜M3（Human・未実施）**: ハーネス権限レイヤーの挙動はプレーン default 新規セッションでないと検証にならない（本セッションは旧 settings ロード済み）。新規セッションでの実施待ち。
