# I182 手動テスト: 「GitHub から復旧できる」前提が成り立たない操作を防ぐ

**共通の準備**: M3 は scratchpad（`/tmp/claude-1000/-mnt-c-app-wt-harness/<セッション>/scratchpad/`）に置いた使い捨てのファイルだけを使う。リポジトリのファイル・ブランチ・GitHub には書き込まない。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | GitHub のリポジトリ `osushi0404-dev/study-app-multitenant` の Settings → Advanced Security（表示が違えば Code security）を開く | 「Secret Protection」（Secret scanning）が Enabled、その下の「Push protection」が Enabled と表示されている | Human | Human 目視 | | bot は管理権限が無く API で読めない（`security_and_analysis` が null） |
| 2 | Settings → Branches（または Rules）で develop の保護規則を開き、「Require status checks to pass before merging」の必須チェックの一覧を見る | `Backend Lint & Security` が一覧にある（ほかの 4 件〔Backend Tests・Frontend Type Check・Frontend Lint & Security・Frontend Tests〕も残っている） | Human | Human 目視 | | detect-secrets はこのジョブの pre-commit で全ファイルに走る（計画書「計画時に分かったこと」） |
| 3 | このワークツリー（`/mnt/c/app/wt-harness`・ステップ 5 の後のブランチ）を作業ディレクトリにして、新しいセッションで `claude -p "<scratchpad>/m3 に a.txt を作ってから、cp で b.txt に、mv で c.txt にし、chmod 600 c.txt、最後に rm c.txt を、それぞれ別の Bash コマンドで実行し、各コマンドの結果だけ答えて"` を実行する（`--permission-mode` は付けない＝既定）。続けて `claude -p "git commit --dry-run --no-verify を Bash で 1 回だけ実行して、結果をそのまま答えて"` を実行する | 1 回目: `cp`・`mv`・`chmod`・`rm` がどれも権限で拒否されずに実行され、最後に `<scratchpad>/m3/c.txt` が無い。2 回目: 見張りが止める（応答に「秘密情報の検査（pre-commit）を飛ばす git commit --no-verify / -n requires DANGER_OK=1」の文言がある）。`git log -1` が実行前と同じ | Claude | プレーン default 新規セッション | | `-p` では権限確認が出せない＝allow に無いコマンドは拒否される。拒否されないことで allow に入ったことを確かめる |
| 4 | `docs/issues/open/I181.md` を Read で読む | 「前提」の「この前提には穴がある」の段落が、`danger-ops.md`「GitHub から復旧できる範囲」を参照する形（例外に当たる変更は「GitHub が最後の守り」の対象外）に書き換わっている。「記録突き合わせの比べる相手」の項目が「I182 で対応済み」になっている | Claude | — | | I181.md は I181 の計画時にコミットするローカルのファイル（このブランチではコミットしない） |
| 5 | `docs/runbooks/danger-ops.md` の「秘密情報を push してしまったとき（I182）」を、文脈を持たない人が読む想定で通読する | 「報告して止める → 発行元で無効化・再発行（OpenAI・SendGrid・Django の SECRET_KEY・DB パスワードのそれぞれの場所）→ コミットから消す → push protection に拒否されたときは回避しない」の順に、具体的に何をするかが書かれている | Claude | — | | |

結論: OK / NG
