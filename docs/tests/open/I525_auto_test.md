# I525 自動テスト: 敵対的レビューの延長を引数で受け取り、Claude の Bash からサンドボックスの外で起動できるようにする

実行コマンド（例）: アプリのテストは無い（アプリのコードを変えない）。ハーネスのテストは下の決定論ゲートと CI の `bash scripts/claude/tests/run-all.sh`

結果:
- backend: 対象外
- frontend: 対象外
- ハーネス（2026-11-16・実装時・手元）: TC-01 pass=170 fail=0（A9e〜A9i・FG-A9e・FG-A9h を含む）・TC-02 pass=7 fail=0（FG 4 件を含む）

## TC-01 `scripts/claude/tests/test_i197_adversarial_process.sh`（既存に追加）
一時のリポジトリ（`mk`）に、過去の記録 `ROUNDS: 1` を 2 本（`prev_rec`・上限を使い切った状態）置いて起動する。`claude` はスタブ。新しく `run_args <名前> <引数…>` を足す（`run` と同じ環境変数で、`bash scripts/claude/adversarial-review.sh <引数…>` を流す）。

| ID | 入力 | 期待値（合否は終了コードの比較・`ck`） | AC |
|---|---|---|---|
| A9e | 2 周使い切り・`run_args a9e --round-limit 3 I900` | exit 0・`ADVERSARIAL_VERDICT: OK`・記録が 3 本 | AC1 |
| A9e2 | 2 周使い切り・`run_args a9e2 I900 --round-limit 3`（イシューが前） | exit 0 | AC1 |
| A9f | 2 周使い切り・環境変数 `ADV_ROUND_LIMIT=2`・`--round-limit 3` | exit 0（引数を採る） | AC1 |
| A9f2 | 2 周使い切り・環境変数 `ADV_ROUND_LIMIT=3`・`--round-limit 2` | exit 4・`ADVERSARIAL_VERDICT: LIMIT`・claude の呼び出し 0（引数を採る） | AC2 |
| A9g | 2 周使い切り・`--round-limit`（値なし）／`--round-limit abc I900`／`--round-limit 0 I900`／`--round-limit -1 I900`／`--round-limit 4 I900`／`--round-limit 99999999999999999999 I900`／`--foo I900`／`I900 I901` | どれも exit 2・`ADVERSARIAL_ERROR: USAGE`・claude の呼び出し 0・記録が 2 本のまま | AC2 |
| A9h | 2 周使い切り・環境変数 `ADV_ROUND_LIMIT=abc`・引数なし | exit 2・`ADVERSARIAL_ERROR: USAGE`・claude の呼び出し 0（今は上限を外して exit 0 になる穴） | AC2 |
| A9i | 2 周使い切り・作業ツリーに未追跡の `scripts/new.txt`・`--round-limit 3 I900` | exit 2・`ADVERSARIAL_ERROR: DIRTY`・出力に `scripts/new.txt`・claude の呼び出し 0 | AC3 |
| 既存 A9a | 2 周使い切り・引数なし | exit 4・LIMIT（変わらない） | AC2 |
| 既存 A11 | 記録の場所の外の未追跡 | exit 2・claude を呼ばない（変わらない） | AC3 |

失敗の注入（`fg_copy` で壊した写しを `with_src` で流し、上の確かめが**落ちる**ことを `ck` で確かめる）:
- FG-A9e: 引数の読み取りの `ADV_ROUND_LIMIT="$2"; shift 2 ;;` を `shift 2 ;;`（値を捨てる）にした写し → A9e が exit 4 になる（合格の確かめが落ちる）
- FG-A9h: 値の確かめ `[[ "$ADV_ROUND_LIMIT" =~ ^[1-3]$ ]] || usage_error` の行を消した写し → A9h が exit 2 にならない（上限を外して動く）

## TC-02 `scripts/claude/tests/test_i525_skill_sandbox_form.sh`（新規）
| ID | 確かめること（合格=exit 0） | AC |
|---|---|---|
| S1 | `.claude/skills/*/SKILL.md` に、`<英大文字と _>=<値> bash scripts/claude/` の形（環境変数を前に付けた起動）が 1 つも無い | AC1 |
| S2 | `.claude/skills/review-gate/SKILL.md` に `bash scripts/claude/adversarial-review.sh --round-limit 3` を含む行がある | AC1 |
| S3 | S2 の起動の文字列（バッククォートの中）が、`.claude/settings.json` の `sandbox.excludedCommands` の形（ファイルから読む・テストに書き写さない）のどれかに bash の glob で当たる | AC1 |

失敗の注入（一時のフォルダに写しを作り、テストの検査の関数をその写しに向けて流す。本物のファイルは書き換えない）:
- FG-S1: 写しの SKILL.md の 1 行を `ADV_ROUND_LIMIT=3 bash scripts/claude/adversarial-review.sh I###` にする → S1 が落ちる
- FG-S2: 写しの review-gate の SKILL.md から `--round-limit 3` の行を消す → S2 が落ちる
- FG-S3: 写しの settings.json の `excludedCommands` から `bash scripts/claude/*` を消す → S3 が落ちる

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_i525_skill_sandbox_form.sh
```
