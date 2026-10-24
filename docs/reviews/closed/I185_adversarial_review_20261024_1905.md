# 敵対的レビュー [I185] ── 2 周目（上限到達・未収束）

- **実施日**: 2026-10-24
- **見直した範囲**: `git diff 93d5199...d94bd9b`（1 周目の指摘への修正の差分）
- **体制**: 固定 3 観点 × 1 体（各 15 分上限）。3 体とも時間内に報告（時間切れなし）。タイマーは 3 体の完了後に止めた
- **通算**: 1 周目（`I185_adversarial_review_20261024_1830.md`）と合わせて 2 周。イシュー全体の上限（2 周）に到達

## 観点 1: ロジック回避・実機 repro

| 重大度 | 指摘内容 | 該当箇所 | 再現証跡（要約） |
|---|---|---|---|
| Medium | 新しく書いた「判定前の失敗」の基準（最終行に `VERDICT:` が無い）が実際の出力と合わない。レビュー記録 105 本のうち 99 本は最終行がコードブロックの閉じ記号で、VERDICT は最終行に来ない。「かつ」と読めば、VERDICT の無い出力を exit 0 で返したときに止まらない。スクリプトの予備判定は VERDICT 無しを OK に倒し「`/implement` を実行」と出す | `.claude/skills/plan-issue/SKILL.md`・`scripts/claude/plan-issue-review.sh`（`detect_plan_verdict`） | 偽の claude（Blocker を書き VERDICT 無し）で `plan-issue-review.sh` が rc=0・「✅ プランレビュー完了」 |
| Medium | fix-loop 条件 ⑥ の除外が、製品のテスト（pytest・Jest・e2e）・lint/scan の設定と抑制・判定基準を定めた文書（SKILL.md・danger-ops.md・review-rules.md）を含まない。5.5／6.5 が SKIP でも次へ進むので、3.5 が PASS した後は人も実 diff のレビューも通らずに入りうる | `.claude/skills/fix-loop/SKILL.md` | 静的読解 |
| Low | gh の応答の先頭が dict でないとき「最新イシュー: なし」と出る（「取得できませんでした」にすべき） | `scripts/claude/hooks/sessionstart_context.py` | 静的読解・format_context で実測 |

問題なしと確かめたもの: ASCII 化で「I185の修正」のような日本語隣接も拾える／命令文は漏れない／bool の番号は `#-`／TC-11f・11g は意図どおり／security-review で Bash を使えるようにしても新しい抜け道はない。

## 観点 2: テストの false-green・tautology

| 重大度 | 指摘内容 | 該当箇所 | 再現証跡（要約） |
|---|---|---|---|
| High | 条件 ④（危険操作を含まない）・⑥（触れない）の「含まない／触れない」の部分をテストが確かめていない。「含んでもよい」「触れても進めてよい」に反転させても 31/31 合格。⑤b は 1 周目の修正で「に触れない」が照合から落ち、検出力が下がった | `scripts/claude/tests/test_i185_harness_docs.sh`（TC-14⑤b・⑤i） | 複製で反転させた版が pass=31 fail=0 |
| Medium | TC-14⑤b2 は除外リストの括弧の書き出しまでしか見ず、中身を空にしても合格 | 同上（⑤b2） | 複製で「（なし）」に置換 → 合格 |
| Medium | ③c・③d は、手順 1 に「承認ポイントを提示して OK を待つ」を挿入してレビュー前の承認に戻しても合格 | 同上（③c・③d） | 複製で挿入 → 合格 |
| Medium | TC-11g は matcher を `compact` にしたり、コマンドを `true # …パス…` にしても合格（どの場面で発火するかを見ていない） | `scripts/claude/tests/test_sessionstart_context.sh`（TC-11g） | 複製の設定で合格 |
| Medium | TC-14⑧c は完全一致の禁止だけで、引用符を変えて必須に戻しても合格（lint を実際に流していない） | `test_i185_harness_docs.sh`（⑧c） | 複製で単一引用符に → 合格 |
| Low | `DATE` の ASCII 化を試すテストがない | `test_sessionstart_context.sh`（TC-11e） | `\d` 版でも合格 |
| Low | ⑤k は停止の文の後ろに「ただし…進めてよい」を足しても合格（言い換えの一般的な限界に近い） | 同上（⑤k） | 追記版で合格 |

## 観点 3: 要件・脅威モデルの網羅漏れ

| 重大度 | 指摘内容 | 該当箇所 | 再現証跡（要約） |
|---|---|---|---|
| Medium | 観点 1 の 1 件目と同じ（VERDICT 無しが OK に倒れ、P2 で人がスクリプトの出力を見なくなったため、レビューしていない計画が「判定 OK」で承認ポイントに出うる） | 同上 | 偽の claude（エラー文だけを返す）で rc=0・記録あり・VERDICT 無し・「✅ プランレビュー完了」・計画書に「完了」リンク |
| Medium | 6 つの条件は修正方針の段階で Claude が自分で判定するだけで、実際の差分が条件内に収まるかを確かめる関所がない。条件を満たす理由は 3.5 の後に書くので誰もレビューしない。共通ルール (a) の自動の戻りでは条件を判定し直さない | `.claude/skills/fix-loop/SKILL.md`・`.claude/review-agents/fix-implementation-reviewer.md` | 静的読解・grep |
| Medium | 観点 1 の 2 件目と同じ（条件 ⑥ の除外範囲の取りこぼし） | 同上 | 静的読解 |
| Low | `onboarding.md` の fix-loop の説明が「差分計画→承認→修正」のまま | `docs/runbooks/onboarding.md:39,121` | grep |
| Low | `docs/claude-code-structure.md:186` と open の I044・I040 の計画・イシューに「allowed-tools 最小権限」が残る | 各ファイル | grep |

## 種類ごとの集計（1 周目と合算）

| 種類（どの仕組みのどんな穴か） | 1 周目 | 2 周目 | 2 周続いたか |
|---|---|---|---|
| A. 文書を文字列で照合するテストが、守りの部分の削除・反転・挿入を見逃す | High 1・Medium 4 | High 1・Medium 4・Low 2 | **続いた** |
| B. fix-loop の自己判定での自動進行（P3）の条件が、実際の差分を誰も確かめず、除外範囲が取りこぼす | Medium 2 | Medium 3 | **続いた** |
| C. 計画レビューのスクリプトが VERDICT 無しを OK に倒す（P2 で人が出力を見なくなり影響拡大） | ― | Medium 2（同一指摘） | 2 周目で初出 |
| D. 変えた考え方を使う箇所の取りこぼし（P2・P4 の古い記述） | Medium 3・Low 1 | Low 2 | 続いたが Low |

## 判定

- 新規: Critical 0・High 1・Medium 10（重複 2 を含む）・Low 5
- 通算 2 周で High が残ったため、上限到達・未収束。自動 OK にせず、最終判定を HIGH に固定して停止し、ユーザーに選択肢を示す（種類 A・B が 2 周続いたので、先頭は「止める場所・方式の見直し」）

REVIEWED_COMMIT: d94bd9b631cef5369559146f2a65b9216e92079d
ROUNDS: 1
VERDICT: HIGH
