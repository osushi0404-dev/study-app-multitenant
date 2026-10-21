# I174 敵対的レビュー記録（fix-loop 後のやり直し・第 2 周）

- 対象: ブランチ `feature/I174-guard-based-permission-review`（head 45cdfa5・第 1 周の修正の後）
- 前周: `docs/reviews/I174_adversarial_review_20261017_1443.md`（やり直し第 1 周）
- 周回: やり直しの第 2 周・エージェント 4（固定 3 観点＋動的 1 観点「余計な確認・誤ブロック」）。総エージェント数は第 1 周の分が不明（原文消失）のため、上限 15 の判定は最大 5 と見なして 9
- 所要時間: ロジック回避の観点が約 4 時間 20 分かかった（時間の上限を付けずに起動したため。途中で打ち切りを指示）。次の周からはプロンプトに時間・攻め筋の上限を書く

## 集計
- NEW_CRITICAL: 1 ／ NEW_HIGH: 9（ロジック回避 3・テスト 1・要件 2・余計な確認 2＋Critical 1）
- 指摘はすべて、オーケストレーターが guard に流して再現を確かめた

## findings（Critical / High）
| # | 重大度 | 内容 | 観点 | 修正 |
|---|---|---|---|---|
| 1 | Critical | 同じコマンドの中で `cat > f.py <<EOF`（危険なコード）を書いてから `shell < f.py` を実行すると、ディスクに残る古い無害な中身で判定して素通り | 余計な確認（測定中に発見） | `_WRITTEN`・`_record_writes`: 書き込むファイルは、ディスクの中身と書き込む中身を合わせて判定。中身の見えない書き込みは確認（F15〜F20） |
| 2 | High | `send_study_reminders_task.apply()`・`t.run()`・`.s().apply()` が素の docker exec で素通り（実メール）。構文木化で、名前だけで止めていた予備の正規表現が効かなくなった後退 | 要件 | タスク名（別名を戻した名前）を起点にした呼び出しを外部送信に（X49〜X51） |
| 3 | High | `git clean -f`（`-d` / `-x` なし）が素通り。未コミットの記録ファイル約 100 件が消える | 要件 | `-f` だけで危険操作（`-n` は除く）。danger-ops.md も更新（A162・A163・P86） |
| 4 | High | 解除不可の停止 `\bdd\b`・`\bshred\b`・`\bmkfs` がコマンド全体の文字列に当たり、`YYYY-MM-DD`・grep の検索語で DANGER_OK=1 でも止まる（このレビュー中に 2 回、オーケストレーターも 2 回止められた） | 余計な確認 | コマンド名で判定（`_cmd_hard`）。計画書 R8 を範囲に入れた（H7〜H12・P83〜P85） |
| 5 | High | compose の構文木の許可リストが狭く、`time.time()`・`inspect.getsource`・`importlib.metadata.version` 等の読み取りで確認が増えた（compose の Python 100 件中、確認 17→38 件） | 余計な確認 | 読み取りだけの標準ライブラリを `_SAFE_CALLS` / `_SAFE_IMPORT_ROOTS` に追加（P87〜P89） |
| 6 | High | テスト S61 は一覧外の `dir()` で ASK になり、`getattr` / `vars(settings)` の判定を外しても合格する（覆い隠し） | テスト | 判定を単独で確かめる S63〜S66 を追加。判定を外した複製で落ちることを確認 |
| 7 | High | `python - 引数`・`python /dev/stdin` をスクリプトの引数と取り違え、パイプで流すコードの確認が外れた（第 1 周の修正による後退） | ロジック回避 | 最初の位置引数が `-` や `/dev/`・`/proc/` なら標準入力のコードとして扱う（F21〜F23） |
| 8 | High | `Path('/app/.env').read_text()`・`dotenv_values('backend/.env')` が素通り（構文木化で文字列の `.env` の判定が抜けた後退） | ロジック回避 | 文字列の定数にも `_secret_path` を当てる（S72・S73） |
| 9 | High | `cat backend/.env*`・`tail backend/.e*`・`cat backend/{.env,x}`・`/proc/*/environ` が素通り（`_SECRET_PATH_RE` は名前の完全一致だけ） | ロジック回避 | `_secret_path`: ブレース展開を開き、glob は秘密のファイル名に当たり得るかで判定（S67〜S71・P91） |

## 同時に直した Medium / Low
- `>|` が `>` とパイプに分かれ、別 worktree への書き込みのブロックが外れた（第 1 周の `;` `&` の区切りでの後退）→ `>|`・`2>&1` を区切りにしない（worktree テスト A11c〜A11e・P92）
- テストの無検証: `&` の区切り（checkout G15）・`reverse_lazy`（X52）・`environ` の別名の `setdefault`（P90）

## 先送り（Medium / Low）
計画書 0-11 の「先送り」に一覧を記録した（多対多の `.clear()`・変数の SQL・素の docker exec の `dumpdata` 等・`git worktree remove --force` / `git stash clear`・`wget` 等での登録 API・キャッシュの別名・`import os as o` 等）。

## 承認待ちの実測（余計な確認の観点・作業記録 3,373 件・45cdfa5 時点）
| 区分 | I174 の前 | d079b26 | 45cdfa5 |
|---|---|---|---|
| docker compose exec/run（264 件） | 264 | 112 | 103（61% 減） |
| 素の docker exec/run（157 件） | 4 | 19 | 16 |
| ホスト（2,952 件） | 21＋settings の ask | 74 | 31 |
| 合計 | 約 289（8.6%） | 205（6.1%） | 150（4.4%） |
誤判定は約 57 件（1.7%）。うち約 30 件（インライン Python の許可リスト・同じコマンドで作るファイル）は今回の修正で素通しになる見込み。

## テスト（修正後）
- container 648・checkout 18・worktree 30・push 87・settings 12・adversarial 40（すべて fail=0）
- 修正前（45cdfa5）の guard で流すと、新しいケースのうち 29 件が狙いどおり失敗（偽合格でない）。判定を 1 つずつ外した複製 6 通りでも、それぞれ狙ったケースが失敗

## 判断（オーケストレーター）
新規 Critical / High があったので通過ではない。修正したうえで、第 3 周（やり直しの上限）で修正の妥当性も含めて反証する。

VERDICT: HIGH
