# 敵対的レビュー [I179] ── 2026-10-21

- 起点: `/code-review I179`（`docs/reviews/I179_code_review_20261021_0107.md`・FINAL_VERDICT: OK・RISK: YES）→ 敵対的レビューステージを自動起動
- 上限: 最大 3 周・サブエージェント総数 15（各エージェントは 25 分・攻め筋 10 本で打ち切り）

## 第 1 周（4 エージェント・固定 3 観点＋動的 1 観点）
観点: ①ロジック回避・実機 repro ②テストの false-green・tautology ③要件・脅威モデルの網羅漏れ ④運用文書と実装の整合（動的）

| 重大度 | 観点 | 指摘 | 対応 |
|-------|------|------|------|
| High | ② | 撤去テストが `down -v` の実行フォルダを見ておらず、`cd` を外して primary で `down -v` が走っても全件 PASS | スタブが `cwd=` を記録し R3b で検証・FG5（`cd` 除去の複製で落ちる） |
| High | ③④ | 外側のワークツリーを撤去すると、gitignore 済みの入れ子が未コミットの作業ごと消える（git は拒否しない。計画の前提が誤り） | 撤去前チェック（3）入れ子の検査（登録済み・深さ 2 以上の `.git`）・R17/R18・FG6・計画 Risk 表の訂正 |
| High | ③④ | 公式の基点は手元の `refs/remotes/origin/HEAD`（実物は `origin/main`＝README だけ）で決まり、空のワークツリーができる | `worktree.md` §2「作る前の確認」（`git symbolic-ref`・`git remote set-head origin --auto`）・イシュー/計画の記述を訂正 |
| High | ④ | 取り残しの片付けの `docker compose -p <名前> down -v`・`docker volume rm` がガードを素通り | ガードに規則を追加・DV1〜DV9・FG-DV1 |
| Medium | ① | `ps` が無いと使用中のロックを「終了済み」と判定 | `ps` 不在で中止・`/proc` でも確認・R16 |
| Medium | ① | `.env` の `export` 付き・`compose.yaml`・override・`COMPOSE_FILE` を見逃す | 判定を拡充・R1h〜R1j |
| Medium | ② | `volume ls` 失敗・`.env` の指定・空のプロジェクト名に TC が無い | R1g・R1h・R1k |
| Medium | ③ | primary が I179 より前のブランチだと `.worktreeinclude` 等が効かない | §2 確認 2 |
| Medium | ④ | docker が使えないと撤去できない | （第 1 周）`DANGER_OK=1` で down せず撤去 →（第 2 周で `KEEP_DATA=1` に分離） |
| Medium | ④ | §11 に wt-harness の未コミットのイシューファイルを移す手順が無い | §11 手順 1〜4 |
| Medium | ① | ガードは作業フォルダで現ワークツリーを決めるため、primary のセッションが入れ子へ `cd` すると入れ子扱い | 既知の限界として §9 に明記（代わりの判定はサブエージェントを壊すため受容） |
| Low | 各 | 入れ子名と primary 名の衝突・同名の入れ子・Cursor の別ウィンドウ手順の削除・§6 の例が別ワークツリーの `.env` を書く・`wt-ports` の既定ポート未計上・DANGER_OK の契約の注記・文書の不在チェックがファイル不在で PASS | 同名の検査・§2 セッションを開く・§6 の例を修正・`existing_ports` の既定値・コメント修正・`lacks()` と FG-D1 の削除注入 |

NEW_HIGH 合計: 4（重複を除く）→ 修正して第 2 周へ（コミット ac25833）

## 第 2 周（4 エージェント・同じ 4 観点・第 1 周の修正の妥当性を反証対象に含める）

| 重大度 | 観点 | 指摘 | 対応 |
|-------|------|------|------|
| High | ① | 名前を確定できない（戻り値 2）のに `DANGER_OK=1` で `down -v` を実行し、実際の名前が primary なら primary のデータが消える | `down -v` を `-p <既定名>` で固定・戻り値 2 は `DANGER_OK=1` でも中止・R22/R22b |
| High | ③ | 第 1 周で足した「docker 不在＋`DANGER_OK=1` で消さずに撤去」のため、`DANGER_OK=1` が「消さない」と「消す」の両方を意味し、デーモン復帰後の再実行で意図せず `down -v` が走る | 消さない撤去は `KEEP_DATA=1` に分離・`DANGER_OK=1` は消す専用・R20a/R20/R20c |
| High | ④ | 停止メッセージ・文書が案内する `scripts/db_backup.sh` は今いるフォルダのプロジェクトが対象で、撤去対象のバックアップにならない（出力も gitignore のまま一緒に消える） | 撤去対象を `-p` で指定した `pg_dump` を primary で実行するコマンドを表示・§4 を更新 |
| Medium | ① | 入れ子に compose ファイルが無いと親（primary）の compose が選ばれる・同名の別クローン | `-p` 固定・コンテナの `working_dir` ラベルが撤去対象と違えば中止（戻り値 4・R21） |
| Medium | ①② | ガードが `docker --context x compose down -v`・クォート・`-vt 5` を素通り、`system prune --volumes` に TC が無い | トークン判定 `_docker_volume_wipe` に置き換え（`sh -c`・改行・`&`・サブシェルも）・DV10〜DV23・FG-DV1 を判定関数の除去に |
| Medium | ① | `.env` の `COMPOSE_PROJECT_NAME: prim`（コロン区切り）を見逃す | `[=:]` に拡張・R22b |
| Medium | ③ | prunable な入れ子の登録で永久に撤去できない | フォルダが無い登録は数えない・`git worktree prune` を案内・R23 |
| Medium | ③ | 記録（計画 4-6・Danger Ops・レビュー文書・テスト件数・敵対的レビューの記録ファイル）が実装に追いついていない | 計画 4-6／Risk／Danger Ops を書き直し・計画変更記録 3・本ファイルを作成・件数を更新 |
| Medium | ④ | §11 手順 1 がクローズ済みイシューの古い open 版まで移す | 「コピーしないもの」を追記 |
| Low | 各 | 登録済み入れ子のループ・compose ファイル 8 種・`name :`・行頭空白・docker あり判定失敗＋`DANGER_OK=1` が未検証、R16 が正しくない理由で PASS、pipefail の SIGPIPE（`printf \| head`・ckhas/cknot）、`settings.local.json` が黙って消える、`set-head` 未設定時の fatal、§2 確認 2 がガードを見ていない、ガードがコミットメッセージ等を誤ブロック、`wt-ports` が `export`/クォート付きの値を読めない | R1j を 8 種＋`name :`・R1i を行頭空白・R1c2・R16 の PATH に bash/env・先頭行の取得を展開に・ckhas/cknot をヒアストリングに・§11 に gitignore 済みファイル・§2 に fatal 時と確認 2 に `_owning_root`・トークン判定（ヒアドキュメント本文も除外）・`port_val`・P15 |

NEW_HIGH 合計: 3 → 修正して第 3 周へ
- 未対応で残す Low: 登録済み入れ子のループ自体は find でも検出されるため単独の TC が無い（二重の検出で、片方を消しても安全側に止まる）

## 第 3 周
（実施後に記入）
