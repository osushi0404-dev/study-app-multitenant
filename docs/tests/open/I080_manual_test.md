# I080 手動テスト（ハーネス権限レイヤー挙動）

決定論的なフック単体検証は `I080_auto_test.md`（TC-P/TC-S/TC-DOC）で担保。本書は **settings.json の権限レイヤー挙動**（allow/ask/deny の precedence・`DANGER_OK=1` 前置による deny 回避→フック danger-op 到達）を確認する。

> **実施環境列について**: これらの TC はハーネスの**権限モード／settings 権限のロード**に依存する。稼働中セッションは起動時にロードした settings を編集途中で再ロードしないため、編集後の挙動は**同セッションでは検証にならない**。該当 TC は「実施環境」列に明記した環境で実施する（plan-writing-rules §「ハーネス挙動テストの実施環境」準拠）。

| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|------|----------|----------|--------|--------|------|
| M1 | プレーン default の新規セッションを起動し、feature ブランチ上で `git push -u origin <feature>` を実行 | プロンプトが**出ずに**実行される（`ask: git push *` の shadow が解消され allow が効く） | プレーン default 新規セッション | Claude | OK | プロンプト無しで実行（`Everything up-to-date`・upstream 追跡済の no-op 安全 push）。allow `git push *` が効く＝I080 主目的の実証 |
| M2 | 同セッションで feature ブランチ上から `git push origin develop`（DANGER_OK 無し）を実行 | **遮断される**（deny ＋フックの二重）。push されない | プレーン default 新規セッション | Claude | OK | PreToolUse フックが exit 2 で遮断（`push to protected branch 'develop' is forbidden`）。実 push なし。フックが load-bearing なバックストップ（deny の完全一致 glob は付加引数で外れ得るがフックが確実に捕捉） |
| M3 | 同セッションで `DANGER_OK=1 git push origin develop` を実行（実際の push は行わず、フックが block せず権限に到達するかを観測。安全のため存在しない一時 remote 等を使う） | フックの danger-op が**解除**され（exit 0 相当）、deny の glob を外れて release/hotfix 経路が成立する | プレーン default 新規セッション | Claude | OK | 使い捨て bare repo に同一ターゲット `HEAD:develop` で対検証：M3-A（DANGER_OK 無し）→ フック exit 2 遮断／M3-B（DANGER_OK=1 リテラル行頭）→ 解除され実行成立（`* [new branch] HEAD -> develop`）。実 origin develop へは未 push。**知見**: DANGER_OK=1 は**コマンド行頭リテラル**でないと無効（先行する変数代入があると `danger_ok=False`＝安全側に倒れる fail-safe） |
| M4 | `bash scripts/claude/tests/test_pretooluse_push_guard.sh` を実行 | `pass=N fail=0`・exit 0。全 TC-P が PASS | 稼働中セッション可 | Claude | OK | pass=40 fail=0 を実走確認 |
| M5 | `python3 -m json.tool .claude/settings.json` ＋ allow/ask/deny を Read で確認 | JSON 有効・allow に `git push`/`git push *`・ask に `git push *` 不在・deny 維持 | 稼働中セッション可 | Claude | OK | TC-S1〜S5 全 PASS |

> M1〜M3 はハーネス権限挙動のため**新 settings をロードした新規セッション**で実施する必要があった。M4/M5 は稼働中セッションで実施可能（スクリプト実行・ファイル確認）。

## 実施結果（/test・2026-06-28）
- **M4（Claude）**: `test_pretooluse_push_guard.sh` → **pass=40 fail=0**（OK）。
- **M5（Claude）**: settings.json JSON 妥当・allow に `git push`/`git push *`・ask に `git push *` 不在・deny 維持・冗長エントリ削除（TC-S1〜S5 全 PASS）（OK）。

## 実施結果（M1〜M3・新セッション・2026-06-28）
新 settings をロードした新規セッションで Claude が実施（プロンプト UX はユーザー同席で観測）。安全策として実 origin develop へは一切 push せず、M3 は使い捨て bare repo を一時ターゲットに使用。
- **M1（Claude）OK**: feature ブランチへ `git push -u origin feature/I080-push-policy-guard` → プロンプト無しで実行（`Everything up-to-date`・既 upstream の no-op 安全 push）。allow `git push *` が効く＝**I080 主目的（安全 push 無確認化）の実証**。
- **M2（Claude）OK**: `git push origin develop`（DANGER_OK 無し）→ PreToolUse フックが **exit 2** で遮断、実 push なし。フックが load-bearing なバックストップ（deny 完全一致 glob は付加引数で外れ得るがフックが捕捉）。
- **M3（Claude）OK**: 使い捨て bare repo に同一ターゲット `HEAD:develop` で対検証。M3-A（DANGER_OK 無し）→ フック exit 2 遮断／M3-B（`DANGER_OK=1` リテラル行頭）→ danger-op 解除され**実行成立**（`* [new branch] HEAD -> develop`、使い捨て repo に develop 作成を確認）。release/hotfix escape hatch の到達確認。
- **知見（仕様確認）**: `DANGER_OK=1` は**コマンド行頭リテラル**でなければ無効（先行する変数代入等があると `raw.lstrip().startswith("DANGER_OK=1 ")` が False となり安全側＝block に倒れる fail-safe 挙動）。これは意図通り。
