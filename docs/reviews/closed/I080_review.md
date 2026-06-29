# I080 実装後レビュー

- **対象イシュー**: docs/issues/open/I080.md（#160）
- **計画書**: docs/plans/open/plan_I080.md
- **Draft PR**: #165

## レビュー対象（実装物）
1. `.claude/settings.json` — allow に `Bash(git push)`・`Bash(git push *)` 追加、ask から `Bash(git push *)` 撤去、deny 維持
2. `scripts/claude/hooks/pretooluse_guard.py` — `_current_branch`/`_norm_push_dest`/`_push_protected_target` 追加、protected/HEAD push 判定の置換、`--all`/`--mirror` 追加
3. `scripts/claude/tests/test_pretooluse_push_guard.sh`（新規） — 決定論テスト（TC-P/false-green）
4. `docs/claude-code-structure.md` — フック/権限説明の同期

## レビュー観点チェックリスト
- [~] **要件適合（静的形のみ）**: イシュー AC を**静的形の範囲で**満たす（settings の allow/ask/deny・フックの**静的**宛先形 block・DANGER_OK escape・FP 解消・`--all`/`--mirror`・doc 同期）。TC-P/TC-S/TC-DOC 全 PASS＋M1〜M3 で実証。**ただし AC「force push requires DANGER_OK」は F1（下記再レビュー）で未達＝`-f`/複合で擦り抜け→I083 へ繰り越し**
- [~] **protected 検出の網羅性（静的形のみ）**: 明示名・引数なし(保護ブランチ上)・refspec・`+develop`・`refs/heads/`・`HEAD:refs/heads/main`・`--all`/`--mirror`・`--repo`・dst側`+` が全て exit 2（TC-P4,11-17,21,22,27-33）。**ただし動的形は未カバー**（下記「敵対的レビュー」参照）: コマンド置換 `$(...)`／変数展開 `$VAR`／エイリアス `-c alias.`／`eval`・`sh -c` ラッパーは全て exit 0 で擦り抜ける
- [x] **danger-op モデル**: protected 宛先 push が `if not danger_ok:` 内（`pretooluse_guard.py:220`）＝`DANGER_OK=1` で exit 0（無条件化していない）。M3-B で release/hotfix escape の実行成立を確認
- [x] **誤検知ゼロ**: feature 上の素 push・`<src>:<feature>`・`develop-fix`/`main-backup` 宛先が exit 0（TC-P5,8-10,18-20）。M1 で feature push 無確認も実証
- [x] **false-green でない**: TC-FALSEGREEN-A〜F（protected／`--all`/`--mirror`／`--repo` の3判定行を各々無効化→素通り(0)、実体→block(2)）を対で確認
- [x] **回帰なし**: `test_pretooluse_checkout_guard.sh` を再実行し **pass=14 fail=0** 維持
- [x] **権限レイヤー実証**: 新 settings ロード済セッションで M1（安全 push 無確認）・M2（未承認 protected push はフック exit 2 遮断）・M3（DANGER_OK で escape 到達・使い捨て repo で成立）を確認
- [❌] **セキュリティ（二重担保は不成立）**: 「`allow: git push *` 緩和がフック＋deny で二重担保」は**反証された**。deny 完全一致 glob は付加引数（`2>&1` 等）で外れ（M2 実証）、TC-S4 は deny の**存在**のみ検証で**効力**未検証＝実質フック単層。そのフックも静的トークナイザのため動的宛先を捕捉できず擦り抜ける（下記参照）。subprocess がリスト引数（shell=False）・fail-open 一貫・`DANGER_OK=1` 行頭リテラル必須の点は妥当
- [x] **設計品質**: ヘルパ分割（`_current_branch`/`_norm_push_dest`/`_push_protected_target`/`_segments`）・`PROTECTED_BRANCHES` 定数化（`:89`）・正規化関数への集約。アンチパターン無し
- [x] **コマンド衛生（I081 gate）**: 実装/検証手順に不要な複合化・パイプ・未コミットファイルへの checkout/restore が無い
- [x] **doc 同期**: `claude-code-structure.md` の `git push *`(ask→allow)・protected danger-op 化が反映、追記にイシュー番号なし（TC-DOC1〜3 PASS）
- [x] **計画一致**: 実装変更は計画記載の4ファイル（`settings.json`・`pretooluse_guard.py`・`test_pretooluse_push_guard.sh`・`claude-code-structure.md`）のみ。残りの差分は全てプロセス記録（issue/plan/review/test）でコード変更なし

## 敵対的レビュー（独立サブエージェント2体・2026-06-28）

自己レビューの追認バイアスを排すため、判定を**反証する**マンデートで独立サブエージェント2体（①フック回避、②テスト/レビュー品質）を実行。**重大な穴を発見**したため、当初の自己レビュー「合格」は**撤回**する。

### Critical — 静的トークナイザ回避（protected push が exit 0 で実行到達）
フックは**シェル展開前の生コマンド文字列**を静的に正規化するため、実行時に develop/main へ解決される動的宛先を捕捉できない。`allow: git push *` により**プロンプトなしで自動実行**される。develop ブランチ temp repo＋実フック投入で実証（リテラルは exit 2 だが下記は全て exit 0）:
- `git push origin $(echo develop)` — コマンド置換
- `git push origin $(git rev-parse --abbrev-ref HEAD)` — **自然な書き方**（現ブランチ push の一般的イディオム）。事故として現実的
- `D=develop; git push origin $D` — 変数展開
- `git -c alias.p="push origin develop" p` — エイリアス間接参照（`push` トークンが消え `"push" not in toks` で skip）
- `eval "git push origin develop"` / `sh -c "git push origin develop"` — ラッパー（`"git" not in toks` で skip）

### Med — 「二重担保」未実証
deny 完全一致 glob は付加引数で外れる（M2 実証）。TC-S4 は存在のみ検証＝効力未検証。実質フック単層。

### 確認できた強み（false-green ではない）
- 決定論ゲート再走 pass=40/0・checkout 14/14。false-green 注入（FG-A〜F）は sed が各被テスト行に**ちょうど1回**マッチし load-bearing と機械裏取り（subagent②が独立確認）。**静的形（リテラル・refspec・`+`・`refs/heads/`・`HEAD`・`--all`/`--mirror`/`--repo`）のカバレッジは強固**。

## 再レビュー（対応後・独立サブエージェント2体・2026-06-29）

「動的形回避の対応（スコープ縮小＋限界明示＋I083 起票）」を**私（メイン）が文書編集しただけで独立検証していない**ため、コミット前にサブエージェント2体（①対応・文書整合性、②静的形スコープ内の新規欠陥）で敵対的に再レビューした。**新たに1件の High バグ（F1）と文書の過大表現/サイレントギャップを発見**したため、対応前はコミット不可だった。

### F1（High・新規・静的形スコープ内）— force push danger-op の取りこぼし
フックの force 判定 `re.match(r"git\s+push\b.*--force", cmd, re.I)`（`pretooluse_guard.py:243`）が**先頭アンカー（`re.match`）かつ `--force` 文字列限定**のため、以下が danger-op を回避（temp repo＋実フックで実測）:
- `git push -f origin x` → **exit 0**（`-f` 短縮形・単体ですり抜け）
- `cd foo && git push --force origin x` / `true; git push --force origin x` → **exit 0**（複合コマンド）
- deny glob `Bash(git push * --force*)` も先頭一致せず空振り → **非保護ブランチへの force push が無防備**。
- 原因: force 判定だけ他の danger-op（`re.search`）と一貫性を欠く。保護ブランチ宛は `_push_protected_target`（`_segments` 分割）が捕捉するため漏れは非保護宛に限定。
- AC「force push requires DANGER_OK」を実装が満たせていない。**根治（`re.search` 化＋`-f`/`--force-with-lease`＋理想は `_segments` ベース）は I083(#166) へ同梱**（F1 も「回避経路」の一種＝I083 の射程）。

### 文書の過大表現・整合性（対応＝本更新で是正済み）
- **Med-1**: `plan_I080.md` のセキュリティレビュー段落が「二重に担保／むしろ厳密化」のまま R5 と矛盾 → 訂正注記を追記（静的形に限る・R5/R6 参照）。**是正済み**。
- **Med-2**: コミット済み `I080_code_review_20260628_1829.md` が「全形捕捉✅/VERDICT OK」のまま → supersession 注記を追記。**是正済み**。
- **Low**: `I080.md`/`plan_I080.md`/`auto_test.md`/本ファイルの「網羅/全形」表現 → 各文書に権威ある限定注記（静的形に限る・I083 で根治）を追加。**是正済み**。

### コミット衛生（要対応）
未追跡の無関係ファイル（`backend/media/.../i073-manual/`・`backend/tmp_test_images/`・`docs/issues/open/I074〜I078.md` 等）が混在。**I080 コミットはパス指定で範囲限定**（実装4ファイル＋プロセス記録＋ `docs/issues/open/I083.md`）。`git add -A` は禁止。

## 判定

**結論: 条件付き合格（スコープ＝静的形のみ／F1 も I083 へ繰り越し）。** ユーザー判断により I080 のスコープを「**静的形の protected push 保護**」に確定。動的形回避（R5・`$(...)`/`$VAR`/エイリアス/`eval`/`sh -c`）に加え、再レビューで発見した **force 取りこぼし（R6/F1）も I083（#166）へ繰り越す**（2026-06-28／29 決定）。

スコープ内（静的形）の品質は強固・false-green でない（決定論 40/0・checkout 14/14・FG 注入 load-bearing）。ただし繰り越す Critical を**サイレントな穴にしないため、マージ前に以下の限界明示を必須条件**とする:

### マージの必須条件（限界の明示・サイレントギャップ防止）
1. ✅ **後続イシューを起票**（動的宛先回避の根治）= **I083 / GitHub #166**（2026-06-28 起票）。
2. ✅ `docs/claude-code-structure.md` のフック説明に「**本ガードはコマンド置換/変数展開/エイリアス/`eval`・`sh -c` ラッパー等、実行時にしか宛先が確定しない形は捕捉しない（静的形のみ）。後続イシュー I083(#166) で対応**」の限界注記を追加。
3. ✅ I080 イシューの「既知の限界」節に同旨を明記（I083(#166) 参照）。
4. （任意・低コスト）TC-P に動的形の負例を「現状 exit 0＝既知の限界・後続で block 化」とコメント付きで参照追加し、回帰の起点を残す（I083 で実施予定のため I080 では見送り可）。
5. ✅ **再レビュー（2回目）の指摘を反映**: F1 を I080「既知の限界 (L2)」・plan R6・I083 へ記録、Med-1/Med-2/Low の過大表現を是正（本更新で完了）。
6. ⏳ **コミットはパス指定で範囲限定**（実装4ファイル＋I080 プロセス記録＋ `docs/issues/open/I083.md`。無関係 untracked を含めない）。コミット実行時に満たす。

### 後続イシュー I083(#166)（根治方針・繰り越し）
- **R5（動的宛先）**: `not danger_ok` の git push で**宛先が静的に確定できない**場合（`$(`／`` ` ``／`${`／`$`変数／`-c alias.`／`eval`/`sh -c`/`bash -c` ラッパー等）は宛先不定として **ask に degrade**（allowlist／fail-safe）。`allow: Bash(git push *)` は維持しフックに判定集約。
- **R6/F1（force 取りこぼし）**: force 判定を `re.search` 化＋`-f`/`--force-with-lease` 対応（理想は `_segments` ベースで push セグメントの force フラグ検出）。複合コマンド・短縮形でも DANGER_OK ゲートが効くようにする。

### A. 対応品質
- **問題特定・修正の適切性**: 「安全 push の無確認化（allow 化）」と「危険 push の確実な阻止（フック danger-op）」を両立。deny の完全一致 glob が付加引数で外れ得る脆さを、フックが宛先正規化＋完全一致で吸収するバックストップ設計（M2 で実証）。
- **検証の充実度**: 決定論（exit code）・回帰・false-green 注入・手動権限レイヤー（M1〜M3）の4層。M3 は実 origin develop へ push せず使い捨て bare repo で escape 到達を安全に実証。

### B. プロセス
- ワークフロー（issue→plan→implement→test→review）遵守。計画外のコード変更なし。plan/code/test/review の記録が揃う。

### C. 技術
- subprocess はリスト引数（shell=False）でインジェクション耐性。fail-open は既存方針と一貫。`DANGER_OK=1` 行頭リテラル必須は意図通りの fail-safe（先行する変数代入では解除されず block 側に倒れる＝M3 で確認）。

### D. 改善提案
- **予防策（軽微・本イシュー同梱可）**: 手動テスト記録に追記済の知見「`DANGER_OK=1` はコマンド行頭リテラルでないと無効」を `docs/runbooks/danger-ops.md` に一文で明記すると、escape hatch 使用時の取り違え（変数前置で block される）を予防できる。新規イシューは過剰。
- **中長期**: deny glob の脆さ（付加引数で外れる）はフックで担保済だが、settings 側 deny を `Bash(git push origin develop*)` 等のパターンに見直す余地（フックが一次防御である現状は妥当）。
