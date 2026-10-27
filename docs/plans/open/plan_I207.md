# I207 計画書: 台帳の残りを捨てるときに目印・重大度が消える穴を直し、軽い指摘は後続イシューにせず一覧へ回す

## 基本情報
- **計画書ID**: plan_I207
- **関連イシュー**: #346
- **Draft PR**: #347
- **作成根拠資料**: docs/issues/open/I207.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I207_review.md
- **作成日**: 2026-10-27

## 1. 背景/目的
- I206 で、台帳の残り（止めない open の指摘）の番号を open で書いた行は「止める中身なら振り直す・それ以外は捨てる」にした。捨てる側で、その行が持つ止める側の値（`RISK=up`・重大度の引き上げ・`SECURITY=yes`・`REPRO=yes`）まで捨てる穴（I206 の台帳の F1・Medium）と、同じ回に resolved と書いた番号が後の open の行で open に戻る穴（F2・Low）が残った
- retro の手順 4-0 は、止めなかった指摘を軽いものも含めてすべて後続イシュー（または既存イシューへのコメント）に回すので、台帳を直すたびに「レビューの残り」のイシューが生まれ、軽い指摘のために全工程が回っている（I197 → I202 → I205 → I206 → I207）
- 目的: ①F1・F2 を決定論で直す ②軽い指摘（Low、または再現なし）は後続イシューにせず一覧ファイルへ回し、一覧は計画の段階で 1 か所だけ見る

### 調査結果
- **原因の概要**: 台帳の残りの書き直しを「振り直す／捨てる」の 2 択にしたとき、捨てる側で、既にある指摘の書き直しと同じ「止める側の値を残すマージ」をしていなかった。また、「捨てる」条件に「この回で初めて読む番号（`fid not in seen`）」が入っていたので、同じ回の 2 行目以降は別の扱い（既にある指摘の書き直し）にすり抜けた
- **詳細な原因分析**（`scripts/claude/code-review.sh`・develop 8b8c923）:
  1. 759〜760 行 `if fid in rest_ids and st == "open" and fid not in remap and fid not in seen and not blocking(fresh): continue`: 行を丸ごと捨てる。774〜776 行のマージ（重大度は下げない・`SECURITY`・`REPRO` は yes が残る・`RISK` は up が残る）を通らない（F1）
  2. 761 行 `keep = fid in seen or fid in shown or (fid in rest_ids and st == "resolved")`: 同じ回に resolved の行が先にあると `seen` に入るので、後の open の行は 759 行の条件をすり抜けて `keep` が真になり、STATUS が open に戻る（F2）
  3. 同じ `seen` の近道で、同じ回に「resolved → 止める中身の open」と書くと、止める中身が振り直されず前の行（前の SCOPE）へ合流する。前の行が `SCOPE=outside` なら止まらない（I197-F1 と同じ形の穴。F2 の同じ箇所）。逆に「止める中身の open → resolved」と書くと、resolved の行が振り直し先（新しい止める指摘）に付き、新しい指摘が resolved になる（762〜763 行の `remap` が先）
  4. retro の手順 4-0（`.claude/skills/retro/SKILL.md` 152〜160 行）は振り分け先が後続イシューか既存イシューへのコメントだけで、指摘の重さで分ける決まりが無い
- **再現（スパイク・2026-10-27・成立）**: scratchpad のスクリプトで `REVIEW_LIB_SOURCE_ONLY=1` の `ledger_update` を呼んだ
  - F1: 前の台帳 `F2 SEV=Low STATUS=open SCOPE=outside KIND=app REPRO=yes RISK=- SECURITY=no` に、`FINDING: F2 SEV=Medium STATUS=open FILE=backend/x.py LINE=200 SECURITY=yes STOP=- RISK=up | … | 再現: r` → 台帳の F2 は元のまま（Low・RISK=-・SECURITY=no）、`ledger_risk` は NO
  - F2: 前の台帳 `F2 SEV=Low … KIND=harness REPRO=no`（台帳の残り）に、同じ回で `F2 … STATUS=resolved` → `F2 … STATUS=open`（止めない中身） → 台帳の F2 は `STATUS=open`（要約も 2 行目のもの）
- **環境前提**: `python3`・`git`・`bash` はある（既存のハーネステストが動く）。新しいツールは使わない
- **既存テストのベースライン**（2026-10-27・develop 8b8c923）: `test_i202_ledger_cleanup.sh` pass=106・`test_i205_stop_criteria.sh` pass=91・`test_i197_review_ledger.sh` pass=64・`test_i180_retro_triage.sh` 13/13（どれも fail=0）
- **テストの文字列の参照（消費箇所）**: 変える行を写しの置き換え前の文字列に使っているテスト（`test_i202_ledger_cleanup.sh`）
  - 132 行 FG-L6 `keep = fid in seen or fid in shown or (fid in rest_ids and st == "resolved")` → 新しい形に合わせて直す
  - 452 行 FG-N2 `        if fid in rest_ids and st == "open" and fid not in remap and fid not in seen and not blocking(fresh):` → 直す
  - 460 行 FG-N3 `fid not in seen and not blocking(fresh):` → 直す
  - 70 行 FG-R4 `"up" if "up" in (risk, o[8]) else "-"`（マージを関数にしても同じ文字列が残るようにする）
- **文言の消費箇所（「止めない指摘は retro が後続のイシューへ回す」）**: grep で全件を拾った
  - `.claude/skills/retro/SKILL.md` 152〜160 行（4-0 本体）
  - `docs/runbooks/review-rules.md` 69 行（関所の穴は後続のイシューで最優先）・70 行（retro が 1 件の後続のイシューにまとめる）
  - `.claude/agents/code-reviewer.md` 184 行（retro が後続のイシューへ回す）・198 行（台帳に残り後続のイシューへ回る・後続のイシューで最優先になる）
  - `.claude/skills/review-gate/SKILL.md` 14 行（retro が後続のイシューへ回す）・72 行（ハーネスの Medium・すべての Low は retro が後続のイシューへ回す）。71 行（アプリ本体の Medium は最優先の後続のイシュー）はアプリ本体なので新しい振り分けでも後続イシュー＝変えない
  - テストでこれらの文言を固定しているものは無い（grep で確認）。`test_i205_stop_criteria.sh` D4 は retro の `grep -h '^LEDGER: .*STATUS=open'` と「最優先」を見る → 新しい 4-0 でも両方を残す
- **一覧の置き場所**: `docs/reviews/` の直下の `I###_*_review_*.md` は close が `closed/` へ移す（`.claude/skills/close/SKILL.md` 77 行の glob）。サブフォルダ `docs/reviews/backlog/` は close・`review_records()`（`-name "${I}_${種類}_*.md"`）のどちらの glob にも当たらない。`is_record_path()`（`code-review.sh` 109 行）は `docs/reviews/*` を記録の場所として扱う（レビューの範囲に入らない）

## 2. 受け入れ条件
1. 台帳の残りの番号を open で書いた行を捨てても、その行の `RISK=up`・重大度の引き上げ・`SECURITY=yes` が前の行に残ることを、失敗注入つきのハーネステストで固定している（I197-F1 の守りと、中身の無い指摘を増やさないことが弱まっていないことも）
2. 同じ回に resolved と書いた台帳の残りの番号が、後の open の行で open に戻らないことを、失敗注入つきのハーネステストで固定している
3. retro の手順 4-0 が、後続イシューにするもの（再現のある Medium 以上・`SECURITY=yes`・`KIND=app`）と一覧に追記するもの（それ以外）を分けて書いてあり、そのことを失敗注入つきのテストで固定している
4. 一覧ファイルがあり、I206 の F3〜F6 が受け入れの理由つきで載っている。ハーネスのイシューの計画で一覧を見る決まりがある
5. 既存のハーネステスト（`bash scripts/claude/tests/run-all.sh`）・CI がすべて pass する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: ハーネスだけ（`scripts/claude/code-review.sh`・`scripts/claude/tests/test_i202_ledger_cleanup.sh`・`.claude/skills/retro/SKILL.md`・`.claude/skills/plan-issue/SKILL.md`・`.claude/skills/review-gate/SKILL.md`・`.claude/agents/code-reviewer.md`・`docs/runbooks/review-rules.md`・`docs/reviews/backlog/I206.md`〔新規〕）
- `gate-check.sh`・`path_risk_trigger()`・`blocking()`・見張り・settings は変えない

## 4. 変更点一覧（具体）

### 4.1 台帳の残りの番号の行の扱い（F1・F2・AC1・AC2）
**修正方針**: 台帳の残りの番号（前の台帳で open・止めない行の番号）を書いた FINDING 行は、同じ回の何行目でも、その行の中身だけで次の 3 つに分ける（同じ回の前の行に左右されない＝`seen` の近道を使わない）。
| 行の中身 | 扱い |
|---|---|
| `STATUS=resolved` | 前の行を resolved にする（既存のマージ）。振り直し先（`remap`）には行かない |
| `STATUS=open` で止める中身（`blocking(fresh)` が真） | 新しい指摘として振り直す（I197-F1 の守り・今までどおり）。同じ回の 2 回目も止める中身なら同じ振り直し先へ（I197-F12）。2 回目が止めない中身なら下の行の扱い（元の行へ合流・振り直し先は open のまま。P6） |
| `STATUS=open` で止めない中身 | 新しい行は作らない（I206 の「中身の無い指摘を増やさない」）。前の行へ、止める側の値だけを合流する: 重大度は高い側・`REPRO`・`SECURITY` は yes が残る・`STOP` は一覧に当たる方・`RISK` は up が残る。**STATUS と要約は前の行のまま**（F1・F2） |

- 合流した結果、前の行が止める指摘になることがある（例: 前の行が `REPRO=yes`、書き直しが `STOP=flow`）。止める側に倒れる向きで、既にある指摘の書き直しのマージと同じ規則なので、そのままにする
- 「止める中身の open → resolved」の順では、resolved は前の行（台帳の残り）に付き、振り直した新しい止める指摘は open のまま（今は新しい指摘が resolved になる＝止まらない向き）
- 「resolved → 止める中身の open」の順では、止める中身を新しい番号に振り直す（今は前の行へ合流し、前の SCOPE が outside なら止まらない）

**コード（`_LEDGER_PY` の `update`）**:
```python
    def merged(o, sev, st, stop, repro, sec, title, risk):
        # 既にある行への書き直し: SCOPE・KIND は前のまま（今回の範囲で決め直すと、触っていない行の未解決の指摘が消える）。
        # 止める側の値は残す（重大度は下げない・SECURITY・REPRO は yes が残る・一覧に当たる STOP は残る・RISK は up が残る）
        return [sev if RANK[sev] > RANK[o[0]] else o[0], st, o[2], o[3],
                o[4] if STOP_RE.fullmatch(o[4]) else stop, "yes" if "yes" in (repro, o[5]) else "no",
                "yes" if "yes" in (sec, o[6]) else "no", title or o[7], "up" if "up" in (risk, o[8]) else "-"]
    for fid, sev, st, path, line, sec, stop, risk, rest in findings:
        ...（fresh を作るまでは今のまま）
        if fid in rest_ids:
            # I207: 台帳の残りの番号の行は、同じ回の何行目でも、その行の中身だけで決める（F2）
            if st == "resolved":
                # 直った: 前の行を resolved にする（振り直し先には付けない）
                led[fid] = merged(led[fid], sev, st, stop, repro, sec, title, risk)
                continue
            if not blocking(fresh):
                # 止めない中身（「直していない」の書き直しなど）: 新しい行を作らず、STATUS・要約は前のまま、
                # 止める側の値だけ前の行へ合流する（F1。I206 F8 の「中身の無い指摘を増やさない」）
                o = led[fid]
                led[fid] = merged(o, sev, o[1], stop, repro, sec, o[7], risk)
                continue
            # 止める中身の open は、下で新しい指摘として振り直す（I197-F1 の守り）
        keep = fid in seen or fid in shown
        if fid in remap:
            ...（今のまま）
        if fid in led:
            led[fid] = merged(led[fid], sev, st, stop, repro, sec, title, risk)
        else:
            led[fid] = fresh
```
- 台帳の残りの番号は `seen` に入らない（上の 2 つの `continue` の前で終わるか、振り直し先の番号が入る）ので、止める中身の open は同じ回の前の行に関係なく `keep` が偽になり、振り直される
- 既にある指摘の書き直し（775〜776 行のマージ）は `merged()` に移すだけで、中身は変えない（FG-R4 の置き換え前の文字列 `"up" if "up" in (risk, o[8]) else "-"` も残る）
- 757〜758 行のコメント（I206 F8）は新しい扱いに合わせて書き直す

### 4.2 retro の手順 4-0 の振り分け（AC3）
`.claude/skills/retro/SKILL.md` 4-0 の「拾った指摘は、1 件ずつ起票せず、まとめて 1 か所に振り分ける…」を、次の 2 つに分ける（拾うコマンド `grep -h '^LEDGER: .*STATUS=open'` と「最優先」の文は残す）。
- **後続イシュー（または合う既存イシューへのコメント）にするもの**: 次のどれかに当たる行。1 件の後続イシュー（タイトルに「$ARGUMENTS のレビューの残り」）にまとめるか、既存イシューへのコメントに入れる（今までどおり）
  - 再現のある Medium 以上（`SEV=Blocker|High|Medium` かつ `REPRO=yes`）
  - `SECURITY=yes`（重さに関係なく）
  - `KIND=app`（アプリ本体。`SCOPE=outside` も）
  ```bash
  grep -h '^LEDGER: .*STATUS=open' <最新のコードレビューの記録> | grep -E 'KIND=app|SECURITY=yes|SEV=(Blocker|High|Medium) .*REPRO=yes'
  ```
- **一覧に追記するもの**: それ以外（Low、または再現なし。ハーネス・guard の行だけになる）。イシューにしない
  ```bash
  grep -h '^LEDGER: .*STATUS=open' <最新のコードレビューの記録> | grep -vE 'KIND=app|SECURITY=yes|SEV=(Blocker|High|Medium) .*REPRO=yes'
  ```
  - 追記先: `docs/reviews/backlog/$ARGUMENTS.md`（起点のイシューごとに 1 ファイル。並行のワークツリーで同じファイルの末尾に書き足して衝突しないように分ける）。無ければ作る。形は 4.3
  - 各行の `FILE=` は、その番号の FINDING 行（同じイシューのコードレビューの記録を新しい順に見て最初のもの）の `FILE=` の値。見つからなければ `FILE=-`
  - 追記したファイルは retro の手順 4 の「このイシューで直す」（記録の場所）と同じく commit/push する
- 判定の仕組み（`scripts/claude/code-review.sh` など）に関わる指摘・`SECURITY=yes` の指摘を「次のハーネスの作業で最優先」と書く文は、後続イシューに回したものに対して残す
- 「## 自律判断の記録」の振り分け先は `#番号` か一覧のファイル（`docs/reviews/backlog/$ARGUMENTS.md`）を番号ごとに書く。0 件なら「台帳の残り 0 件」
- 手順 2.7 の 4 問による見送りは使わない文は、「判定は後続のイシューの計画、または一覧を見る計画で行う」に直す
- 後続イシューの判定の正規表現は、要約（`|` の後ろ）に `KIND=app` などの文字があっても当たる。当たると後続イシューに回る（重い側）だけなので、そのままにする

### 4.3 一覧ファイルの形と最初の行（AC4）
新規 `docs/reviews/backlog/I206.md`:
```markdown
# I206 の台帳の残り（軽い指摘の一覧）

- 記録: `docs/reviews/closed/I206_code_review_20261027_1815.md`
- 一覧に回した決まり: `.claude/skills/retro/SKILL.md` 4-0（Low、または再現なし。後続イシューにしない）
- 見る場所: `.claude/skills/plan-issue/SKILL.md`「台帳の残りの一覧」（実装対象のファイルに当たる行を、同梱するか残すか決める。同梱して直した行は消し、行が無くなったらこのファイルを消す）

- F3 SEV=Low REPRO=yes KIND=harness FILE=scripts/claude/adversarial-review.sh | `flock 9` の戻り値を見ていない（鍵の取得に失敗しても鍵なしで実験役を動かす） | 受け入れ: ロック非対応のファイルシステムという起きにくい場面で、起きても 2 つの観点の実験役が同時に動くだけ（Low）
- F4 SEV=Low REPRO=yes KIND=harness FILE=scripts/claude/code-review.sh | `changed_outside_records`・`delta_hunks` の一時ファイルが `OFFICIAL_DIR` の外に作られ、途中で止まると残る | 受け入れ: 一時ファイルの残りだけで、判定は変わらない（Low）
- F5 SEV=Low REPRO=no KIND=harness FILE=scripts/claude/tests/test_i202_ledger_cleanup.sh | N10・FG-N10 が実時間に依存し、遅い CI で揺れうる | 受け入れ: 再現なし（推測）。揺れたら CI で見える
- F6 SEV=Low REPRO=no KIND=harness FILE=scripts/claude/adversarial-review.sh | `check_worktree` を鍵の中へ移したため、締め切りの周では比べない | 受け入れ: 再現なし。最終の比較は残り、検出が遅れるだけ
```
- 行の形: `- <番号> SEV=<…> REPRO=<…> KIND=<…> FILE=<パス|-> | <要約> | <一覧に回した理由／受け入れの理由>`。retro が追記する行の理由は「Low」か「再現なし」でよい
- I206 の F1・F2 はこのイシューで直すので載せない

### 4.4 計画で一覧を見る決まり（AC4）
`.claude/skills/plan-issue/SKILL.md` の「計画レビューの前に必ず以下を実施する」の前に、次の節を足す。
```markdown
**台帳の残りの一覧（必須・I207）**
軽い指摘の一覧（`docs/reviews/backlog/`。retro の手順 4-0 が追記する）から、計画書の変更点（実装対象）のファイルに当たる行を拾う（ファイルごとに `-e` を足す）:
```bash
grep -rnF -e "FILE=<実装対象のパス1>" -e "FILE=<実装対象のパス2>" docs/reviews/backlog/ || true
```
当たった行ごとに、このイシューで直す（同梱）か残すかを決め、計画書の「## 9. 確定事項と自律判断」に `- 一覧 <ファイル> <番号>: 同梱／残す — 理由` を 1 行ずつ書く。同梱する行は計画書の変更点に入れ、実装で直したらその行を一覧から消す（行が無くなったファイルは消す）。当たる行が無ければ「一覧の該当なし」と書く。
```
- アプリのイシューでも同じコマンドを流してよい（一覧はハーネス・guard の行だけなので当たらない）。条件分けをしない方が手順が増えない
- 見る場所はこの 1 か所だけ（「消化されない墓場」にしないため。一覧の全体の棚卸しは、retro で起票する「ハーネスの古いイシューの棚卸し」でも扱える）

### 4.5 文言の消費箇所（AC3 の整合）
- `docs/runbooks/review-rules.md` 69 行: 「関所の穴は…止めずに台帳に残し、後続のイシューで最優先にする」→「…止めずに台帳に残す（後続のイシューに回ったときは最優先にする）」
- 同 70 行: 「止めない指摘は台帳に残り、retro が 1 件の後続のイシューにまとめるか既存のイシューに同梱する（4-0）」→「止めない指摘は台帳に残り、retro が重さで振り分ける: 再現のある Medium 以上・`SECURITY=yes`・アプリ本体（`KIND=app`）は 1 件の後続のイシューにまとめるか既存のイシューに同梱し、それ以外（Low、または再現なし）は一覧（`docs/reviews/backlog/`）に追記する（4-0）。一覧は計画（`/plan-issue`）で実装対象のファイルに当たる行を見る」
- `.claude/agents/code-reviewer.md` 184 行・`.claude/skills/review-gate/SKILL.md` 14 行・72 行: 「retro が後続のイシューへ回す」→「retro が後続のイシューか軽い指摘の一覧へ回す」
- `.claude/agents/code-reviewer.md` 198 行: 「台帳に残り後続のイシューへ回る」→「台帳に残り retro が後続のイシューか一覧へ回す」・「後続のイシューで最優先になる」→「後続のイシューに回ったときは最優先になる」
- `.claude/skills/review-gate/SKILL.md` 71 行（アプリ本体の Medium）は変えない

### 4.6 テスト（AC1〜AC4）
`scripts/claude/tests/test_i202_ledger_cleanup.sh` に「I207」の節を足す（一時のリポジトリ `$R`・`ledger`・`broken`・`without` をそのまま使う）。項目は auto_test の TC-01 の表（P1〜P6・D1〜D3 と FG）。既存の FG-L6・FG-N2・FG-N3 の置き換え前の文字列を新しいコードに合わせて直す（期待値は変えない）。

## 5. 実装手順（ステップ）
未知リスクは無い（スパイクで F1・F2 を再現した）。最優先の 4.1 を先にする。
1. テストを先に書く（TDD）: `test_i202_ledger_cleanup.sh` に「I207」の節を足す → TC-01（今のコードで新しい振る舞いの項目が不合格になった件数を TC-01 の結果に書く）
2. 4.1（`_LEDGER_PY` の `update`）と、FG-L6・FG-N2・FG-N3 の置き換え前の文字列 → TC-01 の P1〜P6・既存の L6・N2・N3・R4、TC-02
3. 4.2・4.5（retro・review-rules・code-reviewer・review-gate の文言）→ TC-01 の D1・D2
4. 4.3（一覧ファイル）・4.4（plan-issue）→ TC-01 の D3、手動 No.1
- 依存: 2 は 1 の後。3・4 は 1 の後なら順不同（同じテストファイルに足すので順にする）

## 6. テスト計画
### 自動（docs/tests/open/I207_auto_test.md）
- テストのレベル: すべてハーネスの単体（`ledger_update`・`ledger_risk`・`ledger_verdict` を `REVIEW_LIB_SOURCE_ONLY=1` で読み込む）と、指示ファイルの文言の確認。アプリのテスト（pytest・Jest・E2E）は非該当
- 再発防止: F1・F2 をイシューの再現の形で固定する（P1・P2）。I197-F1 の守り（P3・P4・既存の N3）と中身の無い指摘を増やさないこと（既存の N2）を同じファイルで流す
- 振り分けの正規表現は、retro に書いた文字列そのものをテストに持ち、retro に同じ文字列があること（D1）と、その正規表現が I206 の実物の台帳の行と代表の行を正しく分けること（D2）を確かめる
- 否定・不在の項目にはすべて失敗注入（FG: 本体の写しの判定の要を壊す／指示ファイルから行を消すと不合格）を付ける
### 手動（docs/tests/open/I207_manual_test.md）
- No.1: 一覧ファイルの中身（AC4）と、計画で見るコマンドが実際に当たること
- このイシュー自身の retro で新しい振り分けを使ったこと（イシューの制約）は、test-gate の後の retro で行うので手動テストにしない。retro が「## 自律判断の記録」に番号ごとの振り分け先を書き、close の報告に含める

## 7. ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書・一覧ファイルだけ。データ・設定の変更は無い）。revert の後に一覧へ追記された行は、そのファイルを残しても害は無い（読む決まりが無くなるだけ）

## 8. Risk & 回避策
- 止めない中身の書き直しの合流で、前の行が止める指摘に変わる → 止める側に倒れる向き。既にある指摘の書き直しと同じ規則（4.1）。レビュー役には「台帳の残りは直していなければ書かない」（I206）が既に伝わっている
- 台帳の残りの番号の resolved が振り直し先に付かなくなる → 振り直した新しい止める指摘は、別の番号で resolved と書かれるまで open（止める側）。P4 で固定
- 一覧が消化されない（墓場） → 見る場所を計画の 1 か所に決め、ファイル単位で当たる行を必ず「同梱／残す」と記録させる（4.4）。当たらないまま残る行は、棚卸しのイシューで扱える
- `FILE=` の取り違え（振り直した番号の FINDING 行が無い） → `FILE=-` にする。`FILE=-` の行は計画のコマンドに当たらない（棚卸しで扱う）。台帳の形（`LEDGER` 行）を変えて FILE を持たせる案は、台帳の読み書き・既存テストへの波及が大きいので採らない
- 振り分けの正規表現が要約の文字に当たる → 後続イシューに回る（重い側）だけ（4.2）
- 並行のワークツリーで同じ一覧ファイルに書く → 起点のイシューごとのファイルにして衝突しない（4.2）

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・解決方針）:
- 範囲は I206 の台帳の F1・F2 の直しと、retro 4-0 の振り分けの変更・一覧の新設・計画で一覧を見る決まり。F3〜F6 は直さず一覧に「受け入れ（理由つき）」で載せる
- 後続イシューにするのは「再現のある Medium 以上」「`SECURITY=yes`」「`KIND=app`」のどれかだけ。それ以外は一覧に追記する。判定は機械的な欄（`SEV`・`REPRO`・`SECURITY`・`KIND`）で決める
- I197-F1 の守り・I206 の「中身の無い指摘を増やさない」・振り直し先の番号の決め方は保つ。止める基準・変更の種類・行で決める範囲の方式・`gate-check.sh`・`path_risk_trigger()` は変えない
- 粗く確実な形を優先し、見る場所は計画の 1 か所だけ
- このイシュー自身の retro から新しい振り分けを使う。retro で「ハーネスの古いイシューを棚卸しし、今の流れで不要なものを閉じる」を起票し、close の報告に含める

Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は無い）:
- 台帳の残りの番号の行は、同じ回の前の行に関係なく行の中身だけで決める（`seen` の近道を使わない）（仮定で決めた）。理由: F2 の根本は「同じ回の 2 行目」が別の規則にすり抜けることで、近道を外せば F2 と、同じ箇所の「resolved → 止める中身」「止める中身 → resolved」の 2 つの止まらない向きの穴（調査結果 3）も同時に消える。規則が行ごとに 1 つになり、粗く確実
- 止めない中身の書き直しは、STATUS と要約を前の行のまま、止める側の値だけ合流する（仮定で決めた）。理由: 要約を「今回の差分では直していない。」で上書きしない（I206 N2 の「前の行と 1 字も違わない」を保つ）。止める側の値はイシューの解決方針どおり既存のマージと同じ規則
- マージを `merged()` に共通化する（仮定で決めた）。理由: 既存の書き直しと台帳の残りの合流で同じ規則を 2 か所に書かない（F1 の根本は 2 つの扱いを並べて比べなかったこと）
- 一覧は `docs/reviews/backlog/<起点のイシュー>.md`（起点のイシューごとに 1 ファイル）（仮定で決めた）。理由: retro が書いてよい記録の場所の中で、close・`review_records()` の glob に当たらない。並行のワークツリーが 1 つのファイルの末尾に書き足すと衝突するので分ける
- 一覧を見る場所は `.claude/skills/plan-issue/SKILL.md`（仮定で決めた。イシューで「置き場所は計画で決める」）。理由: 計画書を作るスキルそのものなので、実装対象が決まった時点で必ず通る。計画書の書き方の決まり（plan-writing-rules.md）は読むだけの文書で、実行されるコマンドを置くならスキルの方が確実
- 振り分けはスクリプトにせず、retro に `grep` の 2 本を書く（仮定で決めた）。理由: イシューの制約「大きな自作のコードを足さない」。正規表現はテストで実物の行に当てて固定する（D2）
- テストは新しいファイルを作らず、`test_i202_ledger_cleanup.sh` に「I207」の節を足す（仮定で決めた）。理由: 一時のリポジトリ・`ledger`・`broken`・`without` をそのまま使える
- 一覧の確認（plan-issue の新しい節）: このイシューの計画の時点では一覧がまだ無いので「一覧の該当なし」
- 一覧 docs/reviews/backlog/I206.md F4: 残す — このイシューで作った一覧に、実装対象の `scripts/claude/code-review.sh` が当たった（implement で確認）。イシューの設計確認メモで F3〜F6 は直さず受け入れと決まっている
- 一覧 docs/reviews/backlog/I206.md F5: 残す — 同上（`scripts/claude/tests/test_i202_ledger_cleanup.sh`）
- 高リスク判定: `scripts/claude/code-review.sh` は判定の仕組み（台帳）だが、`path_risk_trigger()` の集合（`.github/`・`.pre-commit-config.yaml`・`.secrets.baseline`・見張り・settings）に触れない。アプリの高リスクの条件（認証・認可・テナント境界・個人情報・決済など）にも当たらない。変更は止める側に倒す向きだけ → No の見立て（判定は plan-review）

セキュリティ・ベストプラクティス:
- セキュリティ影響なし（アプリのコード・認証認可・個人情報・依存ライブラリを変えない。bandit・npm audit の対象の変更なし）。判定の仕組みの変更は、止める判定を見逃す向き（fail-open）にしないことを P3・P4・既存の N3 と FG で固定する（4.1 は fail-open の穴を 2 つ閉じる）
- 振り分けで `SECURITY=yes` は重さに関係なく後続イシュー（C8。D2 で固定）
- 入力の扱い: FINDING 行は今までどおり `FIND` の正規表現で全体一致したものだけを読む（形の崩れは exit 2）。新しく読む値は無い
- 公開リポジトリ: 一覧に書くのは要約と `ファイル` の参照だけ（コマンドの出力・ログは貼らない。retro の既存の決まりどおり）

要件適合性: 受け入れ条件の範囲を超えた仕様の追加は無い（4.1 の「止める中身 → resolved」「resolved → 止める中身」の扱いは F2 と同じ箇所・同じ根本原因の直しで、止める側に倒すだけ）。マルチテナント・ステータス遷移は非該当

P3/P5/P8 影響なし（DB・外部 API・非同期処理・インフラの追加なし。依存関係ファイルの変更なし）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・未成年データ・テナントデータを扱わない）

設計品質: Python の部分は今の `_LEDGER_PY` の形（1 つの埋め込みスクリプト・モードで分ける）を保つ。設定値・定数の追加は無い

Danger Ops（有無/手順/ロールバック）:
- 無（データ削除・破壊的変更・強制 push は無い）

## 必ず確かめる項目
（高リスク判定が Yes になったときに敵対的レビューが使う。No なら使わない）
| 項目 | 確かめ方 |
|---|---|
| 1. 台帳の残りの番号を止める中身で書けば、同じ回の前の行（resolved・止めない open）に関係なく新しい指摘として振り直され、止まる | 読んで可（P3・既存の N3 と FG） |
| 2. 止めない中身の書き直しで、新しい行が増えず、前の行の止める側の値が下がらない（重大度・REPRO・SECURITY・RISK・STOP） | 読んで可（P1・P5・既存の N2） |
| 3. 同じ回のどの順序でも、台帳の残りの resolved が振り直した新しい止める指摘を resolved にしない | 読んで可（P4） |
| 4. retro の振り分けで、`SECURITY=yes`・`KIND=app`・再現のある Medium 以上の行が一覧に落ちない | 読んで可（D2） |

## 計画変更記録
（実装中に計画と違うことをするときに書く）
- 1（計画レビュー 20261027_1925 の Warning 対応・2026-10-27）: Warning 1（表とコードの食い違い）は (b) を採り、4.1 の表を「2 回目が止めない中身なら元の行へ合流」に直し、テスト P6（止める中身の open → 止めない open の順で、F3 は open のまま・F2 に合流・F4 なし）を足した。理由: 行ごとに 1 つの規則（計画書 9）のまま揃い、止める側は弱まらない。Warning 2（パイプの grep）は `check-permission-prompt.sh` で 4.2 の `grep -h … | grep -vE …` を確かめ、承認なしで実行された（0）ので形は変えない。Info 2 件は対応不要（guard の再現なしの High は 4.4 の計画の段階で拾える）。方式・範囲・受け入れ条件は変えないので再レビューはしない
- 2（implement・2026-10-27）: 計画書の記載「auto_test P3・P4・P6 の前の台帳は `l6_prev`」。採った方法: 3 つとも同じ回に `F1 … STATUS=resolved`（既存の `N2_F1`）を先に書く。理由: `l6_prev` の F1（High・STOP=flow）が止めるので、合否が F3 に関係なく HIGH になり、FG-P4 が不合格を捕まえられなかった（実装後に判明）。あわせて FG-P4 の写しは「resolved を振り直し先へ付ける」形（`fid = remap[fid]` を足す）にした（auto_test の `fid not in remap` の形では止めない中身の分岐へ流れて F3 が open のまま）。FG-L6・FG-N2・FG-N3 の置き換えは新しいコードの分岐に合わせた（期待値は同じ）。一覧の確認（9 の F4・F5）も足した。計画レビューのやり直し: 不要（テストの入力の細部だけで、方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261027_1925 判定: ✅ 完了](../../reviews/I207_plan_review_20261027_1925.md)
