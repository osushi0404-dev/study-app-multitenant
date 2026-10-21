# I174 敵対的レビュー記録（fix-loop 後のやり直し・第 1 周）

- 対象: ブランチ `feature/I174-guard-based-permission-review`（head ccf5944・fix-loop 完了後の基本レビュー OK の後）
- 前回までの記録: `docs/reviews/I174_adversarial_review_20261016_1745.md`・`_1930.md`・`_2130.md`（第 1〜3 周・上限到達・未収束 → `/fix-loop` 済み）
- 周回: やり直しの第 1 周（上限 3 周・総エージェント 15 を数え直す）

## 記録についての注記（復元）
- この周の指摘の原文は、前のセッションの中だけにあり、記録ファイル・PR コメントのどちらにも残っていなかった（セッションの切り替えで消えた）。
- そのため、下の findings は**未コミットの修正差分と、そこで足したテストケース（A160・A161・X42〜X48・S53〜S62・C59・P75〜P82・G12〜G14）から復元**したものである。重大度・出した観点・エージェント数は原文が無いため確定できない（復元の対象外）。
- 修正後の再確認は、次の周（第 2 周）の敵対的レビューで行う。

## findings（復元）
| # | 内容 | 再現ケース |
|---|---|---|
| 1 | `call_command('migrate', app_label=..., migration_name='zero')` のキーワード指定の巻き戻しが素通り | A160 |
| 2 | `caches['default']` を変数に入れてからの `.clear()` が素通り（Redis の全消去） | A161 |
| 3 | `reverse()` のルート名を名前空間付き（`accounts:register`）・キーワード（`viewname=`）・AI 生成のルート名（`problem-generate-ai/adaptive`）で書くと、メール送信・OpenAI への送信を見逃す | X42〜X47 |
| 4 | 別名で import したタスク関数（`import send_study_reminders_task as t; t()`）の実行を見逃す | X48 |
| 5 | 設定の秘密を属性以外で読む書き方を見逃す: `getattr(settings, 'OPENAI_API_KEY')`・`settings.SIMPLE_JWT`（SIGNING_KEY）・`settings` の別名・`from os import environ`・`from core.settings import EMAIL_HOST_PASSWORD`・`connection.settings_dict`・`vars(settings._wrapped)`・`getattr` で設定をまとめて表示 | S53〜S61 |
| 6 | `ps auxeww`（BSD 形式の `e`）で各プロセスの環境変数＝秘密情報が出る | S62 |
| 7 | 多対多の `.set([])`（関係を全部外す書き込み）が、組み込みの `set()` と同名のため許可リストを通る | C59 |
| 8 | 誤判定（余計な確認）: 秘密でない設定の参照・外部送信でないルート名・`caches[...]` の 1 件削除・別名の安全な関数・普段の読み取りの呼び出し（`get_*_display`・`get_fields`・`localdate` 等）・`ps aux`・パイプで JSON を `python3 <スクリプト>` に渡す・組み込みの `set()` | P75〜P82 |
| 9 | 誤判定（checkout ガード）: 語にくっついた `;`（`git checkout feat; git log -- x`）を区切らず、後ろの `-- x` を checkout の対象と誤読して停止 | G12〜G14 |

## 修正内容（`scripts/claude/hooks/pretooluse_guard.py`）
- `_segments`: `shlex` の `punctuation_chars` で、語にくっついた `; & |` も区切る（#9）
- `_CodeVisitor`:
  - `from x import y as z` の別名を覚え、元の名前で判定する（#4）
  - `django.conf` の `settings` の別名・`from os import environ` の別名を覚える（#5）
  - 秘密の設定名を、属性・文字列・import のどの形でも確認に回す（`_SECRET_NAMES`・`_SECRET_ATTRS`）（#5）
  - `getattr(settings, 変数)`・`vars(settings)` を確認に回す（#5）
  - キャッシュを代入した変数・`caches[...]` を追い、`.clear()` は止め・`.delete('k')` は通す（#2・#8）
  - `call_command('migrate', ..., migration_name=...)` を巻き戻しとして止める（#1）
  - `reverse` / `reverse_lazy` のルート名を名前空間を外して比べ、キーワード `viewname=` にも対応（`_EXTERNAL_ROUTES`）（#3）
  - 受け手のある `.set()` は許可リストから外す（#7）
  - 読み取りの呼び出しと `get_*_display` を許可リストに追加（#8）
- `_CODE_EXTERNAL`（正規表現の判定）にも、名前空間付きのルート名・AI 生成のルート名・秘密の設定名を追加（#3・#5）
- `_cmd_external`: 実行するファイルを引数で指定した `python` では、パイプの中身をコードと見なさない（#8）
- `_container_safe`: `ps` は BSD 形式の `e` を含むときだけ確認に回す（#6・#8）

## テスト
- `test_pretooluse_container_guard.sh`: pass=604 fail=0（前回 574 から +30）
- `test_pretooluse_checkout_guard.sh`: pass=17 fail=0（G12〜G14 を追加）
- `test_pretooluse_push_guard.sh` 87・`test_pretooluse_worktree_guard.sh` 27・`test_settings_permissions.sh` 12・`test_adversarial_trigger.sh` 40: すべて fail=0

## 判断（オーケストレーター）
- この周は新規の指摘があったので通過ではない。修正したうえで、第 2 周で修正の妥当性も含めて反証する。

VERDICT: HIGH
