# I610 計画書: フックの起動役の無視されるファイル・gate-check のリンクの見逃し・run-all の中のキャッシュ

## 基本情報
- **計画書ID**: plan_I610
- **関連イシュー**: #610
- **Draft PR**: #612
- **作成根拠資料**: docs/issues/open/I610.md（GitHub #610 の本文の写し・正は GitHub）
- **実装後評価**: docs/reviews/open/I610_review.md
- **作成日**: 2026-11-21

## 1. 背景/目的
- I599 で、`scripts/claude/` のスクリプトは既定でサンドボックスの中・外に出すのは起動役を通る 16 本だけにした。そのレビューで止めなかった指摘のうち、再現のある High（F24・SECURITY=yes）と Medium（F30）と、そのテストの穴（F31）が残った。あわせて、外から中へ移った `run-all.sh` が、中で uv のキャッシュに書けずに落ちる
- 目的: 3 つを塞ぎ、外と中の境目を動かすときに、動いた側のスクリプトを確かめる手順を決まりにする

## 調査結果
### 原因の概要
- F24: フックの起動役（`.claude/hooks/reviewed-hook.sh`）は「変更があるか」を差分と未追跡だけで見て、git が無視するファイルを数えない。しかもフックを `-I` なしの `python3` で起こすので、`scripts/claude/hooks/` に置いた無視されるモジュールが、サンドボックスの外で動くフックに読み込まれうる
- F30・F31: `gate-check.sh` の「サンドボックスのふさぎの印は数えない」判定（`-c`）がシンボリックリンクをたどるので、`/dev/null` を指すリンクも見逃す。テスト（G9b）もリンクで印を作り、見逃しを正しい動きとして固定している
- キャッシュ: `run-all.sh` は、中では uv の既定のキャッシュ（`~/.cache/uv`）に書けない

### 詳細な原因分析
- `.claude/hooks/reviewed-hook.sh:38-41`: `git diff --quiet "$base" -- scripts/claude` と `git ls-files --others --exclude-standard -- scripts/claude` が空なら作業ツリーのフックを動かす。無視されるファイル（`--ignored`）を数えない。起動役 `.claude/hooks/unreviewed.py:95-102`（`_unreviewed_files`）は差分・未追跡・無視されるファイルを数えており、2 つの「レビュー前の中身」の定義が食い違っている
- `.claude/hooks/reviewed-hook.sh:29,36,40,55,57`: 5 か所とも `python3 <パス>`（`-I` なし）。Python は既定でスクリプトの置き場所を読み込み先の先頭に入れる
- `scripts/claude/gate-check.sh:118`: `[[ "${entry:0:2}" == "??" && -c "$p" ]] && continue`。bash の `-c` はリンク先を見る
- `scripts/claude/tests/test_i193_official_flow.sh:230-236`（G9b・FG-G9b）: `ln -s /dev/null .bashrc` で印を作り、0（数えない）を期待している
- `scripts/claude/tests/run-all.sh:22`: `uv run --locked --project …` に `UV_CACHE_DIR` を渡していない。CI は `UV_CACHE_DIR` を指定している（`.github/workflows/ci.yml` の Harness Tests の env）

### 確かめたこと（2026-11-21・スパイク）
- **訂正（計画レビュー 20261121_1727 の指摘）**: `scripts/claude/hooks/*.py` の先頭の import は標準ライブラリだけだが、`posttooluse_check.py:39-43` の `_check_yaml` が関数の中で任意に `import yaml` する（無ければ YAML の構文チェックを黙って飛ばす）。`-I` は利用者の site（`~/.local`）を読まないので、yaml が利用者の site にだけある環境ではチェックが外れる。この環境では `python3 -I -c 'import yaml'` が `/usr/lib/python3/dist-packages/yaml/` を読む（2026-11-21 に実測）ので外れない（R3）
- **成立**: 一時フォルダに `json.py`（`print("EVIL")`）と `h.py`（`import json`）を置くと、`python3 h.py` は `EVIL` を出し、`python3 -I h.py` は出さない（`-I` で置き場所のモジュールを読み込まない）
- **成立**: サンドボックスの中の `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i468_lint_frontend.sh` は `Read-only file system … /home/tacic/.cache/uv` で exit 2。`UV_CACHE_DIR="$TMPDIR/uv-cache"` を付けると合格（pass=1 fail=0）
- ベースライン: `UV_CACHE_DIR="$TMPDIR/uv-cache" bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i599_unreviewed_scripts.sh scripts/claude/tests/test_i193_official_flow.sh` → pass=2 fail=0
- 環境: Python 3.12.3（`-I` は `-E -s -P` を含む）・git 2.43.0・uv 0.13.6

## 2. 受け入れ条件
- [ ] AC1: フックの起動役は、`scripts/claude/hooks/` に無視されるファイルがあるとき、作業ツリーのフックを動かさない（TC-01・失敗注入つき）
- [ ] AC2: フックの起動役がフックを起こす `python3` はすべて `-I` 付き（TC-02・置き場所に置いたモジュールを読み込まないことを失敗注入で確かめる）
- [ ] AC3: `gate-check.sh` は、未追跡の `/dev/null` を指すシンボリックリンクを汚れとして数える（TC-03・失敗注入つき）
- [ ] AC4: `run-all.sh` はサンドボックスの中で、キャッシュに書けないことで落ちない（`test_i193_official_flow.sh` の F9 が手元で通る）。`UV_CACHE_DIR` を指定したとき（CI）の動きは変わらない（manual No.1・No.2）
- [ ] AC5: `docs/runbooks/plan-writing-rules.md` に、外と中の境目を動かすときの確かめの手順がある（manual No.4）

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend・Frontend・DB | なし |
| フック | `.claude/hooks/reviewed-hook.sh`（すべてのフックの起動役。このセッションのフックも即座にこれで動く） |
| 関所 | `scripts/claude/gate-check.sh`（汚れの判定） |
| テスト | `scripts/claude/tests/i599_cases.py`（TC-12 の続き）・`scripts/claude/tests/test_i193_official_flow.sh`（G9b）・`scripts/claude/tests/run-all.sh`（入口） |
| 文書 | `docs/runbooks/plan-writing-rules.md` |
| 意図的に変えない | `.claude/hooks/unreviewed.py`（数え方の正として呼ぶ側）・`scripts/claude/hooks/*.py`（中身は変えない）・`docs/runbooks/harness-audit.md`・`.claude/settings.json`・`.github/workflows/ci.yml` |
| 依存 | 追加なし |

## 4. 変更点一覧（具体）
### 修正アプローチ
フックの起動役は「変更があるか」の判定を起動役（`unreviewed.py dirty`）に任せて定義を 1 か所にし、フックを起こす `python3` すべてに `-I` を付ける。`gate-check.sh` は数えない印を「リンクでない文字デバイス」に絞る。`run-all.sh` は、キャッシュの置き場が指定されておらず書けないときだけ一時フォルダに向ける。手順書に、外と中の境目を動かすときの確かめを足す。

### 4-1. `.claude/hooks/reviewed-hook.sh`
修正方針: (1) 38-41 行の「変更が無ければ作業ツリーのフック」の条件を、`CLAUDE_PROJECT_DIR="$root" python3 -I "$root/.claude/hooks/unreviewed.py" dirty >/dev/null 2>&1` の終了コード 0 に置き換える（差分・未追跡・無視されるファイルを数える。起動役と同じ定義）。`unreviewed.py` は `.claude/hooks/` にあり、サンドボックスから書けない（読むだけ）。終了コードが 0 以外（中身あり・基準を求められない・起動の失敗）は、今の「変更あり」と同じく写しの道に進む（安全側）
(2) フックを起こす `python3` 5 か所（29・36・40・55・57 行）をすべて `python3 -I` にする。
```bash
if CLAUDE_PROJECT_DIR="$root" python3 -I "$root/.claude/hooks/unreviewed.py" dirty >/dev/null 2>&1; then
  exec python3 -I "$root/$rel" "$@"
fi
```
- 冒頭のコメントに「変更の判定は unreviewed.py dirty（I610）・フックは -I で起こす（置き場所のモジュールを読まない）」を足す

### 4-2. `scripts/claude/gate-check.sh`
修正方針: 118 行を `[[ "${entry:0:2}" == "??" && -c "$p" && ! -L "$p" ]] && continue` にし、コメントに「リンクは数える（印は bind mount で、リンクではない・I610）」を足す。

### 4-3. `scripts/claude/tests/test_i193_official_flow.sh`（G9b・F31）
修正方針: G9b を逆向きにし、本物の文字デバイスの道は判定の差し替えで確かめる。
- G9b: 最上位に `ln -s /dev/null .bashrc`（未追跡のリンク）→ 1（汚れとして数える）。深い場所（`scripts/x/.bashrc`）のリンクも → 1
- G9c: `gate-check.sh` の写しで `&& ! -L "$p"` を外したもの（リンクを印と見なす＝本物の文字デバイスの道を通す）で、最上位のリンクだけなら → 0（印を数えない道が残っている）
- FG-G9b: `&& ! -L "$p"` を外した写しで G9b が 0 になり不合格
- FG-G9c: 印を数えない行ごと消した写しで G9c が 1 になり不合格
- 古い G9b・FG-G9b の行は置き換える

### 4-4. `scripts/claude/tests/i599_cases.py`（TC-12 の続き）
修正方針: フックの起動役の新しい 2 つの決まりを、一時のリポジトリで確かめる（`make_repo` を使う・本物は書き換えない）。
- TC-12b（AC1）: `scripts/claude/hooks/x.tmp`（`.gitignore` の `*.tmp` で無視される）を置くと、フックは分かれた時点の写しで動く（出力が `V1 <写しのパス>`）
- TC-12c（AC2）: 分かれた時点（BASE）に `scripts/claude/hooks/json.py`（`print("EVIL")`）をコミットし、`h.py` を `import json` にした一時のリポジトリで、フックの出力に `EVIL` が無い
- TC-12d（AC2）: 起動役の中の、フックを起こす `python3`（`exec python3`・`python3 -I "$root/.claude/hooks/unreviewed.py"` を含む全部）がすべて `python3 -I` で始まる（行を読んで確かめる・5 か所の道を全部覆う）
- TC-12e（V5）: 一時のリポジトリの `.claude/hooks/unreviewed.py` を壊す（`raise SystemExit(5)` だけにする）と、変更が無くてもフックは写しの道で動く（判定の失敗で作業ツリーに倒れない）
- FG: 4-1 (1) の行を元の git の 2 つの確かめに戻した写しで TC-12b が作業ツリーで動き不合格／`-I` を 1 つ外した写し（作業ツリーの道の `exec python3 -I "$root/$rel"`）で TC-12c に `EVIL` が出て不合格／写しの道の `exec python3 -I "$snap/$rel"` の `-I` を外した写しで TC-12d が不合格／判定の行の後ろに `|| true` を足した写し（失敗でも作業ツリー）で TC-12e が不合格
- 既存の FG（`never_snap`）の置き換え元の文字列が変わるので、新しい条件の行に合わせて直す

### 4-5. `scripts/claude/tests/run-all.sh`
修正方針: uv で流し直す前（22 行の前）に、`UV_CACHE_DIR` が空で、既定の置き場（`${XDG_CACHE_HOME:-$HOME/.cache}/uv`）に一時ファイルを作れないときだけ、`UV_CACHE_DIR` を `$TMPDIR/uv-cache`（`TMPDIR` が無ければ `mktemp -d` の新しいフォルダ。共有の `/tmp` の決まった名前は、ほかの利用者が先に作れるので使わない）にして `export` する。理由を 1 行、標準エラーに出す。
```bash
if [ -z "${UV_CACHE_DIR:-}" ]; then
  uv_default="${XDG_CACHE_HOME:-$HOME/.cache}/uv"
  if ! { mkdir -p "$uv_default" 2>/dev/null && probe=$(mktemp -p "$uv_default" .w.XXXXXX 2>/dev/null) && rm -f "$probe"; }; then
    if [ -n "${TMPDIR:-}" ]; then export UV_CACHE_DIR="$TMPDIR/uv-cache"; else UV_CACHE_DIR=$(mktemp -d) && export UV_CACHE_DIR; fi
    echo "（uv のキャッシュ ${uv_default} に書けないので ${UV_CACHE_DIR} を使います・サンドボックスの中など）" >&2
  fi
fi
```

### 4-6. `docs/runbooks/plan-writing-rules.md`
修正方針: 「外部/ハーネス挙動依存のスパイク実証」の後に節「外と中の境目を動かす計画（I610）」を足す: サンドボックスの外に出す型（`.claude/settings.json` の `excludedCommands`）・外で動くスクリプトの一覧（`.claude/hooks/unreviewed.py` の `OUTSIDE_SCRIPTS`）を変える計画では、中へ移るスクリプトごとに (a) 中でだけ見える物（ふさぎの印＝`/dev/null` の bind mount）を読まないか (b) 中で書けない場所（`~/.cache` など）に書かないか を、計画の前にサンドボックスの中で 1 回流して確かめ、結果を「調査結果」に書く。外へ移るスクリプトは、外で動く必要（gh・`claude -p`・docker）の根拠を書く。

## 5. 実装手順（ステップ）
1. フックの起動役（4-1）と、そのテスト（4-4）→ TC-01・TC-02 参照。最初に置く（このセッションのフックも即座にこれで動くので、文法を確かめてから保存する → TC-04 参照）
2. `gate-check.sh` と G9b（4-2・4-3）→ TC-03 参照。ステップ 1 と並行してよい
3. `run-all.sh`（4-5）→ manual No.1・No.2 参照
4. 手順書（4-6）→ manual No.4 参照
5. `/simplify` で整理し、push する（implement 段階）。`/simplify` の後に、変えたファイルを読むテストを流し直す

## 6. テスト計画
### 自動（`docs/tests/open/I610_auto_test.md`）
- テストレベル: シェル・Python の決定論テスト（`scripts/claude/tests/`・CI の `run-all.sh` が流す）。pytest・Jest・E2E は対象のコードが無いので対象外
- TC-01（AC1）・TC-02（AC2）: `test_i599_unreviewed_scripts.sh`（`i599_cases.py` の TC-12b・TC-12c と FG）
- TC-03（AC3）: `test_i193_official_flow.sh`（G9b・G9c と FG）
- TC-04: `bash -n .claude/hooks/reviewed-hook.sh`（文法）
- 決定論テストの対象の選び方（plan-writing-rules）: F24・F30 は、壊れても気づきにくく（フックはエラーを出さずに作業ツリーのものを動かす・関所は黙って通す）、被害が大きい（外で動く守りの差し替え・レビューを通らない変更）のでテストにする。`run-all.sh` のキャッシュは、壊れると手元のテストがすぐ落ちて気づけるので決定論テストにしない（manual No.1・No.2）。手順書の文言もテストにしない（manual No.4）
### 手動（`docs/tests/open/I610_manual_test.md`・実施者はすべて Claude）
- No.1（AC4）: サンドボックスの中で `UV_CACHE_DIR` なしに `test_i193_official_flow.sh` を流して F9 を含め合格
- No.2（AC4）: `UV_CACHE_DIR` を指定すると、その置き場が使われ、案内の行が出ない
- No.3: 本物のフックの起動役に、見張りが止める入力を渡すと止める答えが返る（変更後もフックが動く）
- No.4（AC5）: 手順書の節を読む
- No.5（AC3 の補い）: サンドボックスの中の `gate-check.sh I610` が、本物のふさぎの印（`.bashrc` など）を汚れとして数えない

## 7. ロールバック
- この PR を revert する（スクリプト・テスト・文書だけ。データの変更なし）。フックの起動役は revert で元の判定に戻る

## 8. Risk & 回避策
<!-- 処遇: 回避 か 受け入れ。受け入れの行は --route の照合で使う（I512） -->
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: `reviewed-hook.sh` を壊すと、このセッションを含むすべてのフックが動かなくなる（見張りが止まり、Claude が何もできなくなる） | 保存の前に `bash -n` で文法を確かめる（TC-04）。`unreviewed.py dirty` の失敗は「変更あり」と同じ写しの道に倒す（フックは動き続ける）。保存の後に、本物の起動役で見張りが動くことを確かめる（manual No.3） | 回避 |
| R2: `unreviewed.py dirty` は git を 3 回呼ぶので、写しが無いときのフックが少し遅くなる | 写しがあるときは今までどおり git を呼ばない（35-37 行の近道は変えない）。写しの無い最初の 1 回だけ | 受け入れ |
| R3: `-I` で、利用者の site（`~/.local`）にだけ入れた yaml が見えなくなり、`posttooluse_check.py` の YAML の構文チェックが黙って外れる | この環境の yaml は共有の場所（`/usr/lib/python3/dist-packages`）にあり外れない（実測）。外れても、YAML の誤りは pre-commit の check-yaml と CI が止める。`-P`（置き場所だけ外す）より `-I` を選ぶのは、環境変数（`PYTHONPATH` など）も読まない二重の守りのため。manual No.3 で本物のフックが動くことを確かめる | 受け入れ |
| R4: 無視されるフォルダ（`__pycache__`・`.venv`）は `unreviewed.py` が数えない（I599 の R3 で受け入れ）ので、そこに置いたモジュールは数えられない | `-I` でスクリプトの置き場所を読み込み先にしないので、`__pycache__` のモジュールも `import` で読まれない（二重の守り・TC-02） | 回避 |
| R5: `run-all.sh` が一時フォルダのキャッシュを使うと、毎回の取得で遅くなる | 同じ `$TMPDIR` のあいだは使い回される。CI は `UV_CACHE_DIR` を指定しているので変わらない | 受け入れ |
| R6: `gate-check.sh` でリンクを数えるようにすると、ほかの正しい未追跡のリンクで止まる | 未追跡のリンクは本来汚れ（記録の場所の外の未コミットの変更）。記録の場所の中のものは今までどおり数えない | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- F24 は、変更の数え方を起動役と同じにし（無視されるファイルまで）、フックを起こす `python3` すべてに `-I` を付ける（両方）
- `run-all.sh` は `UV_CACHE_DIR` が無く既定の置き場に書けないときだけ `$TMPDIR` の下に向ける。CI と外で流す人の動きは変えない
- 予防の手順は `docs/runbooks/plan-writing-rules.md` に書く（`harness-audit.md` には書かない）
- F30 は `[ -c "$p" ] && [ ! -L "$p" ]`。G9b はリンクを汚れとして数える向き・本物の文字デバイスは判定の差し替えで確かめる

Claude が決めた（技術的な選択と理由）:
- 起動役の「変更があるか」は `unreviewed.py dirty` を呼ぶ（git の確かめをシェルに写さない）— 定義を 1 か所にし、食い違いという根本原因を直す。`unreviewed.py` は `.claude/hooks/` にあり、サンドボックスから書けないので、呼んでも外で動く守りが増えるわけではない。`-I` で起こす
- 写しがあるときの近道（35-37 行）は変えない — 写しは BASE の中身なので、無視されるファイルがあっても写しの道は安全。毎回 git を呼ばない速さを保つ
- フックのテストは `i599_cases.py` の TC-12 の続きに足す — 一時のリポジトリ・起動役の写しの土台（`make_repo`）がそのまま使える。新しいファイルを作るより重複が少ない
- `run-all.sh` のキャッシュは決定論テストにしない — 壊れると手元の全テストがすぐ落ちて気づける（plan-writing-rules「決定論テストの対象の選び方」）
- 書けるかの確かめは、ディレクトリを作って一時ファイルを作る（`[ -w ]` だけでは、無い・読み取り専用のファイルシステムで食い違いうる）
- 一覧 `docs/reviews/backlog/I599.md` F31（G9b がリンクで印を作り見逃しを固定）: 同梱 — 4-3 そのもの
- 一覧 `docs/reviews/backlog/I211.md` F1・F2（`run-all.sh` の相対パス・`VIRTUAL_ENV` の判定）: 残す — キャッシュの置き場とは別の話
- 一覧 `docs/reviews/backlog/I195.md` F10・`docs/reviews/backlog/I204.md` F6（`test_i193_official_flow.sh` の別の箇所）: 残す — G9b とは別の箇所
- 一覧 `docs/reviews/backlog/I209.md` F1（`plan-writing-rules.md` のキャッシュを含む読み取りの API）: 残す — アプリのテストの話
- 一覧 `FILE=-` の行（I224 F9・I223 B1〜B4）: 残す — 関係しない
- 一覧のほかの実装対象（`.claude/hooks/reviewed-hook.sh`・`scripts/claude/gate-check.sh`・`scripts/claude/tests/i599_cases.py`）: 一覧の該当なし

要件適合性・業務ロジック: 受け入れ条件の範囲を超える仕様の追加は無い。マルチテナント・ステータス遷移は該当なし

セキュリティ・ベストプラクティス:
- F24 は外で動くフックにレビュー前の中身を読ませない直し（SECURITY=yes）。判定の正を 1 か所にし、`-I` で二重に守る。判定に失敗したときは写しの道（安全側）に倒す
- F30 は関所の見逃しを塞ぐ（数えない範囲を狭める側）
- 入力: フックの起動役の引数の確かめ（`scripts/claude/hooks/*.py`・`..` を禁じる）は変えない
- バックエンド・フロントエンドのコード変更なし。依存の追加なし。bandit・npm audit の対象なし（重大度の基準は変えない: bandit は MEDIUM 以上・npm audit は high/critical）
- P3/P5/P8 影響なし（DB・外部 API・非同期・新しいインフラなし）。P6 影響なし（UI なし）。P9 影響なし（個人情報・テナントデータを扱わない）

設計品質: 判定の失敗は安全側（写し・汚れとして数える）に倒す。キャッシュの置き場は環境変数で上書きできる（CI の指定を優先）

Danger Ops（有無/手順/ロールバック）:
- 無（スクリプト・テスト・文書の変更。データの削除・GitHub の設定の変更なし）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 無視されるファイルがあるとき、フックが作業ツリーのものを動かさない: TC-01（TC-12b）が `*.tmp` の無視されるファイルで写しの道に進むことを確かめ、判定を元の git の 2 つに戻した写しで不合格になる |
| V2 | 1 | 読んで可 | フックが置き場所のモジュールを読み込まない: TC-02（TC-12c）が BASE に置いた `json.py` を読み込まないことを確かめ、`-I` を外した写しで不合格になる |
| V3 | 1 | 読んで可 | `gate-check.sh` が `/dev/null` を指すリンクを汚れとして数え、本物の文字デバイスの道は残る: TC-03（G9b・G9c と FG）。本物の bind mount の印は manual No.5 |
| V4 | 2 | 読んで可 | 既存の FG（`never_snap` など）が、置き換え元の文字列の変更で「置き換えに失敗して合格」にならない（`assert old in lsrc` が効いている） |
| V5 | 3 | 読んで可 | 判定の失敗（`unreviewed.py` が起動できない・基準が無い）で、作業ツリーのフックに倒れない（写しの道か、基準なしの既存の道だけ）: TC-05（TC-12e）が壊した `unreviewed.py` で写しの道に進むことを確かめ、`|| true` を足した写しで不合格になる |
| V6 | 2 | 読んで可 | フックを起こす `python3` の 5 か所がすべて `-I` 付き: TC-06（TC-12d）が全行を読み、写しの道の `-I` を外した写しで不合格になる |

## 計画変更記録
- 計画レビュー（20261121_1727）の Warning 4 件・Info 1 件を反映: `-I` と任意の yaml の前提を訂正し R3 を受け入れに（実測でこの環境は外れない）／5 か所の `-I` を全部覆う TC-12d（TC-06）と、判定の失敗で写しの道に倒れる TC-12e（TC-05）と FG を足した／manual No.3 の入力と期待を 1 つに決めた／`run-all.sh` の置き場を `$TMPDIR/uv-cache` か `mktemp -d` にした。方式・範囲・受け入れ条件は変えていない（TC の追加と前提の訂正だけ）ので計画レビューはやり直さない

## レビュー結果
- [20261121_1727 判定: ✅ 完了](../../reviews/I610_plan_review_20261121_1727.md)
