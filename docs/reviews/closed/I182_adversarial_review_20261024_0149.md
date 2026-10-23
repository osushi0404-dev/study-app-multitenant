# 敵対的レビュー [I182] ── 2026-10-24

## 前提
- 基本レビュー: `docs/reviews/I182_code_review_20261024_0134.md`（FINAL_VERDICT: OK・高リスク判定 YES）。PR #308 の CI は 6 件すべて成功（I183 マージ後の develop 取り込み d5934f4 の後）
- 範囲: ユーザー決定（2026-10-23）により「GitHub Actions と秘密情報に関わる範囲だけ・1 周・時間上限付き」。rm/mv の allow 化・guard_corpus_diff・ワークツリー境界・見張りの failsafe は対象外
- 時間上限: 各エージェント 20 分以内・攻め筋 12 個まで（実績はどれも約 2 分）
- 既知 findings として渡したもの: /security-review の Medium 1・Low 4 と残余リスク処遇、計画書 4-0 の対象外（意図的な回避）

## 第 1 周（エージェント 3）
| 観点 | NEW_CRITICAL | NEW_HIGH |
|------|------|------|
| ロジック回避・実機 repro（秘密情報の push 経路: `_commit_no_verify()`） | 0 | 0 |
| テストの false-green（Actions と秘密情報のテスト: C1〜C4・N・E・S） | 0 | 1 |
| 要件・脅威モデルの網羅漏れ（Actions と秘密情報） | 0 | 0 |

### findings と処遇
| 重大度 | 指摘 | 再実証（オーケストレーター） | 処遇 |
|--------|------|------|------|
| High | C1 が「pre-commit/action のステップがある」「SKIP に detect-secrets が無い」しか見ず、ステップへの `continue-on-error: true`・`if: false`・`with: extra_args`、ジョブへの `if` で検査を事実上外しても合格する（網羅漏れ観点も同じ点を Medium で指摘） | c.py を取り出し、ci.yml の複製に `continue-on-error: true` を注入 → C1 exit 0 を確認 | **修正**: C1 をジョブ・ステップのキーの許可リストに変更（今の形以外は不合格。数え上げない）。FG-C5（4 件）を追加 |
| Medium | C2 が `id`・`args` しか見ず、`stages: [manual]`・`files`・`exclude: '.*'` で検査対象が無くなっても合格する | 読解で確認（C1 と同じ作り） | **修正**: フックを完全一致・最上位のキーは `repos` だけ。FG-C5（3 件）を追加 |
| Medium | C3 が `branches` しか見ず、`paths` で PR を絞っても合格する（必須チェックが pending のまま残るので黙っては通らない） | 読解で確認 | **修正**: `pull_request` のキーは `branches` だけ。FG-C5（1 件）を追加 |
| Medium | 見張りの `_COMMIT_VALUE_SHORT` が `-S`（値を省略できる）を値が必須として扱い、`git commit -S -n -m x` の `-n` を読み飛ばして素通し（実際の git はフックを飛ばす） | 見張りに入力 → exit 0 を確認 | **修正**: `-S`・`-u` を「値を省略できる」（くっつけた分だけ値）に分けた。N11（2）・N13（0）を追加、FG-N1 に N11 を追加 |
| Low | `-uno`（`--untracked-files=no`）の `n` を `-n` と読み違えて止める（止めすぎ） | 上の修正で解消 | **修正**（同上）: N12（0）を追加 |
| Low | `--no-verif`（長いオプションの前方一致の省略形）が素通し | — | 見送り: 普通の書き方の事故ではない（計画書 4-0 の脅威モデル外）。後ろに push protection と CI の detect-secrets が残る |
| Low | `.gitignore` の `.env` 除外の行が settings.json の ask にも danger-ops.md の表にも無い | — | 見送り: 手元の detect-secrets・push protection・CI の detect-secrets が後ろに残る。「ローカルの安全装置は最小限」の方針。必要なら別イシュー |
| Low | `pre-commit/action@v3.0.1` と pre-commit の `rev` が SHA で固定されていない | — | 見送り: 今回の差分の外（以前からの設定）。`permissions: contents: read` で被害は小さい |
| Low | `dependency-audit.yml` の `issues: write` がワークフロー全体に付いている | — | 見送り: 今回の差分の外。`ref: develop` 固定で PR から悪用する経路は無い |

### 見送った Low の処遇（2026-10-24 ユーザー判断で確定）
判断基準: ループエンジニアリング・ハーネスエンジニアリングのベストプラクティス、かつサクサク進める。
- `--no-verif`: 対応しない。見張りの守る範囲は「普通の書き方の事故」で、省略形まで足すと文字列の判定を作り込み続けることになる（I179 の教訓）。後ろに push protection と CI の detect-secrets が残る
- `.gitignore` の `.env` 除外: 対応しない。消しても `.env` の鍵は手元の detect-secrets・push protection・CI の detect-secrets の 3 段で捕まる。編集のたびの確認は手間に見合わない
- `pre-commit/action` の SHA 固定・`dependency-audit.yml` の `issues: write` の絞り込み: I152（#268）に同梱（同じ 2 つのワークフローを作り直すイシューのため。新しいイシューは立てない）

### 修正の確認（決定論）
- `test_i182_secret_gates.sh`: pass=54 fail=0（N11〜N13・FG-C5 8 件を含む）
- 見張りの回帰: matrix pass=391・oracle 見逃し=0／余計な停止=0・corpus_diff 新しく確認・停止 0 件・push_guard pass=185・failsafe pass=12・docs pass=9
- テスト文書 `docs/tests/open/I182_auto_test.md` に N11〜N13・C1〜C3 の許可リスト化・FG-C5 を反映

### 第 2 周を行わない理由
ユーザー決定の「1 周」に従う。修正は「許可リストで粗く不合格に倒す」形にしたため（同種の書き方を数え上げない）、修正後の取りこぼしは FG-C5 の失敗注入と既存の回帰テストで決定論的に確かめた。

VERDICT: OK
