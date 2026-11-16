# I524 自動テスト: ダッシュボードの確かめ用データを各科目・各曜日 10 問以上にし、開発の起動のたびに作り直す

実行コマンド（例）: `docker compose exec backend python -m pytest dashboard/tests/test_I524_dashboard_verify_volume.py dashboard/tests/test_I513_seed_dashboard_verify.py studylogs/tests/test_I455_org_scoped_querysets.py`
（CI が PR ごとに全体を流す。手元では関係するテストだけ）

結果（implement 段階の手元の実行・2026-11-16。正は CI）:
- backend: `test_I524_dashboard_verify_volume.py`・`test_I513_seed_dashboard_verify.py`・`studylogs/tests/test_I455_org_scoped_querysets.py` 312 passed（`/simplify` の整理の後にも流し直して 312 passed）。Red: 実装前は TC-01〜TC-06 が落ちた（`--soft-stop` が無い・解答の無い日が 2 日・10 問未満・問題が 5 問・22:59:58）。TC-07 は今のコマンドの正しい動きを固定するテストで、実装前から通る（FG-6 で落ちることを確かめた）
- TC-05 の「環境変数が無い」経路（計画レビューの Warning）: `clear=True` の `{}` でも `パスワードが空` の分岐を通って合格した
- frontend: 変更なし

FG の結果（2026-11-16。壊す・戻すはスクラッチパッドの Python で行い、元の控えとバイト単位で一致することを確かめて戻した）:
- FG-1: TC-01 が 100 件すべて落ちた／FG-2: TC-02 が 100 件中 99 件落ちた（1 件は乱数でたまたま重ならなかった）／FG-3: TC-03 が一意制約の `IntegrityError` で落ちた／FG-4: TC-04・TC-05 の 3 件が落ちた／FG-5: TC-06 が `22:59:58` で落ちた／FG-6: TC-07 が `DID NOT RAISE CommandError` で落ちた
- 1 回目にシェルのスクリプトの中から docker を動かしたときは、サンドボックスの中で `.env` を読めず、テストが流れないまま非 0 になった（無効として数えず、docker のコマンドを直接打って流し直した）

## Backend（`backend/dashboard/tests/test_I524_dashboard_verify_volume.py`・新規）
共通: `NOW = 2026-11-16 15:00 JST`（`TODAY` = 11-16）。直近 7 日 = `TODAY-6`〜`TODAY`、今日より前の 6 日 = `TODAY-6`〜`TODAY-1`、範囲の外 = `TODAY-13`〜`TODAY-7`。DB を使うテストは `override_settings(DEBUG=True)`、パスワードは `mock.patch.dict(os.environ, {'VERIFY_PW': 'pw-for-test'})`。(日, 科目) ごとの数は `answered_at` を日本時間の日付にして数える。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | 種 0〜99 で `plan_answers(random.Random(seed), NOW)`（DB を使わない） | 今日より前の 6 日のうち、解答が 0 件の日がちょうど 1 日。それ以外の 6 日（今日を含む）は、2 科目（`verify-i487-math`・`verify-i487-english`）のどちらも 10 以上 20 以下。範囲の外の (日, 科目) は 1 以上 5 以下で、範囲の外の解答が 1 件以上ある。どの解答も `answered_at < NOW` |
| TC-02 | 種 0〜99 で `plan_answers`（DB を使わない） | 科目ごとに、直近 7 日の解答のある 6 日の数を集めると、6 つすべて違う（`len(set(counts)) == 6`）。科目どうしの同じ数は見ない |
| TC-03 | 種 3・11 で `seed_verify_data` を流す（DB）。種 3 の後に種 11 をもう一度流す | 確かめ用の利用者の解答を (日本時間の日付, 科目) でまとめると、どの組も問題の id がすべて違う（件数 == 集合の大きさ）。確かめ用の科目ごとの問題は 20 問ちょうど（`確かめ数学の確かめ問題 1`〜`20`）で、2 回目の作り直しの後も 20 問のまま（増えない） |
| TC-04 | `override_settings(DEBUG=False)` で `call_command('seed_dashboard_verify', '--password-env', 'VERIFY_PW', '--soft-stop', stdout=out)`。確かめ用データが無い DB で | 例外が出ない。標準エラーに `確かめ用のデータは作りませんでした: DEBUG が偽` を含み、標準出力は空。組織 `verify-i487-org`・利用者 `verify_i487@example.com`・`verify-i487` で始まる科目・解答が 0 件 |
| TC-05 | `DEBUG=True` で、環境変数が無い（`clear=True`）と空（`VERIFY_PW=''`）の 2 通りで `--soft-stop` 付きのコマンド。1 回作った後の DB で | 例外が出ない。標準エラーに `確かめ用のデータは作りませんでした: パスワードが空` を含み、`pw-for-test` を含まない。標準出力は空。確かめ用の利用者の解答の id の集合と組織の数が前と同じ |
| TC-06 | `_random_time` に、`random()` が決まった値を返す小さな置き物（`random.Random` を継いで `random` だけを返す値に替えたクラス）を渡す（F6） | 過去の日（`TODAY-2`）: 0.0 → 7:00:00、`1 - 2**-53` → 22:59:59。今日（`NOW` 15:00）: 0.0 → 0:00:00、`1 - 2**-53` → 14:58:59。今日・0:00:30 の `now`: どちらの値でも 0:00:00 |
| TC-07 | 同じメールの利用者がほかの組織（`other-org`）にいる DB で、`--soft-stop` を付けずにコマンドを流す（F10） | `CommandError` で、文に `が確かめ用の組織（verify-i487-org）にいないため` を含む（`VerifyDataError` の文がそのまま伝わる）。その利用者の組織・パスワード・セッション・解答が前と同じ |
| TC-08 | TC-07 と同じ DB で、`--soft-stop` を付けてコマンドを流す（ユーザーの BP の確認で足した。TC-07 と同じテスト関数の parametrize） | TC-07 と同じ（`--soft-stop` でも、起きてはいけない状態は正常終了にしない） |

## Backend（`backend/dashboard/tests/test_I513_seed_dashboard_verify.py`・直す）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-49（F5） | 種 0〜19 で `plan_answers` を同じ日の 0:30 と 23:00 で作る | `(科目, 日, 正誤, 秒)` の `collections.Counter` が同じ（並び順に依らない） |
| TC-40〜TC-48 | そのまま（TC-42 は新しい作りでも成り立つ） | 今どおり通る |

FG（失敗の注入。実装の中で一時的に壊して落ちることを確かめ、結果をここに書く。コミットしない）:
- FG-1（TC-01）: 解答の無い日を `rng.sample(recent_past_days, 2)` の 2 日にする → TC-01 が落ちる
- FG-2（TC-02）: 量の割り当てを `rng.choices(range(10, 21), k=6)`（重なりあり）にする → TC-02 が落ちる種がある
- FG-3（TC-03）: `_write_answers` の問題を `problems[i % 5]` にする → TC-03 が落ちる（一意制約の `IntegrityError` か、id の重なり）
- FG-4（TC-04・TC-05）: `--soft-stop` の分岐を外す（いつも `CommandError`）→ TC-04・TC-05 が落ちる
- FG-7（TC-08）: `except VerifyDataUnavailable` を `except VerifyDataError` に戻す（異常も正常終了）→ TC-08 が落ちる
- FG-5（TC-06）: 過去の日の `span` を `DAYTIME_HOURS * 3600 - 1` に戻す → TC-06 が落ちる（22:59:58）
- FG-6（TC-07）: `_ensure_user` の組織の確かめを外す → TC-07 が落ちる

## 決定論ゲート（自動実走）
compose を読む既存のテスト（新しいサービスがポート・`image:`・名前の無い保存領域の決まりに当たらないこと）。計画の時点（変更前）で実行し、どちらも exit 0（下の記録）。
```bash
bash scripts/claude/tests/test_compose_ports.sh
bash scripts/claude/tests/test_i213_dependabot.sh
```

記録（計画の時点・2026-11-16・変更前の `docker-compose.yml`）:
- `test_compose_ports.sh` → pass=13 fail=0（exit 0）
- `test_i213_dependabot.sh` → pass=17 fail=0（exit 0。FG-I1・FG-V1 で、指紋の無い `image:`・名前の無い保存領域を入れると不合格になることを中で確かめている）

## 実行記録（test-gate・2026-11-16 01:50）
- `bash scripts/claude/gate-check.sh I524` → exit 0（`GATE_CHECK: OK`・レビュー済み 718311f5 以降は記録の場所だけ）
- 決定論ゲート 2 本は review-gate の `code-review.sh` が実走して exit 0（`docs/reviews/I524_code_review_20261116_0138.md`）。test-gate に委譲されたものは無い
- pytest・Jest・E2E は CI（PR #526・HEAD 718311f5）の 8 ジョブすべて合格。手元で流し直したものは無い

## 再発防止記録（fix-loop・2026-11-16・ユーザーの BP の確認）
- なぜ失敗したか: マージ依頼の後、ユーザーの「BP の観点で問題ないか」の確認に、規約（`rules/ultimate_django_coding_standards.md` §14 のエラーの握りつぶしの禁止・ログの適切なレベル）と照らして報告し、ユーザーが「1と2をこのPRで直して」と決めた。(1) `--soft-stop` が `VerifyDataError` をすべて正常終了にし、ほかの組織に同じメールの利用者がいる異常も終了コード 0 になっていた。計画が「想定内で作れない」と「起きてはいけない状態」を 1 つの例外の型で扱い、分けていなかった (2) 「作りませんでした」の案内を、成功の出力と同じ標準出力に普通の文で出していた
- 何を変えたか: `VerifyDataError` の下に `VerifyDataUnavailable`（DEBUG が偽・パスワードが空）を足し、`--soft-stop` はこの型だけを正常終了にする（ほかの組織は `--soft-stop` でも `CommandError`）。案内は `self.stderr.write(self.style.WARNING(...))`。診断メモ `docs/reviews/I524_fix_diagnosis_20261116_1035.md`（案 A）
- セキュリティ上の考慮点: 止まる条件・順番は同じ（DEBUG が偽・パスワードが空は書き込みより前）。異常が失敗として見えるようになる向きの直しで、案内にパスワードの値は入らない（TC-05）
- 次回どう防ぐか: 「止まったら正常に終わる」を足すときは、止まる理由を「想定内（環境が整っていない）」と「起きてはいけない状態」に分け、前者だけを正常終了にする。I513 の BP の直し・今回とも、マージ依頼の後に規約の節と照らして見つかった（I487 の振り返りの「自作の前に規約と依存を実ファイルで照合」の範囲）
- 確かめた結果: Red（直す前に TC-04・TC-05 の 3 件が標準エラーで空・TC-08 が `DID NOT RAISE CommandError` で落ちた）→ 直した後 `test_I524_dashboard_verify_volume.py`・`test_I513_seed_dashboard_verify.py`・`studylogs/tests/test_I455_org_scoped_querysets.py` 313 passed。FG-7（`except VerifyDataUnavailable` を `except VerifyDataError` に戻す）で TC-08 が落ち、元に戻した

## 実行記録（test-gate・BP の直しの後のやり直し・2026-11-16 10:48）
- `bash scripts/claude/gate-check.sh I524` → exit 0（`GATE_CHECK: OK`・レビュー済み 28d5d86d 以降は記録の場所だけ）
- 差分のコードレビュー `docs/reviews/I524_code_review_20261116_1040.md` は OK（F2 は解決済み）。決定論ゲート 2 本は `code-review.sh` が実走した
- pytest・Jest・E2E は CI（PR #526・28d5d86d）の 8 ジョブすべて合格。手元で流し直したものは無い
- 起動し直して作り直しが今までどおり動くこと・画面がログと同じことを、手動テストの「画面確認」の 4 行目に記録した（止まる道の確かめは TC-04・TC-05・TC-08）
