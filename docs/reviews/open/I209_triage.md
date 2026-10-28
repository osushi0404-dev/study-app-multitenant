# I209 棚卸しの判定一覧（track:harness の開いているイシュー）

- 対象の時点: 2026-10-28 `gh issue list --state open --label track:harness --limit 200 --json number` で 53 件（I209 #349 自身を除く 52 件）
- 判定基準（設計確認メモ）: ① 前提のスキル・仕組みが廃止済み ② 別のイシュー・今のファイルで解決済み ③ 同じ穴を扱う開いたイシューがある（統合） ④ 観点・手順を足すだけで、今の方針（その場で捕まり手戻りなしの見逃しには足さない・決定論チェックを優先）では足さない。どれにも当たらなければ残す
- 判定の作り方: 4 つのサブエージェントが 13 件ずつ本文と今のファイルを照らして案を出し、意見の割れた件と根拠の要の件を Claude が確かめて決めた（下の「Claude が決めた点」）
- 反映の仕方（計画書 4.3）: 閉じる＝`gh issue close <番号> --reason "<理由>" --comment <閉じるコメント>`。統合＝統合先の本文の先頭の読み替えの節に中身を同梱してから `gh issue close <番号> --duplicate-of <統合先> --comment <閉じるコメント>`（統合先に別のコメントは足さない）。残す＝本文の先頭に「## 今の流れでの読み替え（I209）」を足す（元の本文はそのまま後ろに残す）
- 閉じる理由の対応: ② → `completed`、① ④ → `not planned`、③ → `duplicate`

## 集計
| 判定 | 件数 |
|---|---:|
| 閉じる | 37 |
| 統合（閉じる） | 4 |
| 残す | 11 |
| 計 | 52 |

## 判定一覧
| # | I | 判定 | 基準 | 理由（根拠） | 小さな指摘の行き先 |
|---:|---|---|---|---|---|
| 10 | （番号なし） | 閉じる | ① | 本文は「詳細は 00_issue.md」の 1 行だけで、その運用（00_issue.md でのイシュー管理）は無い。CLAUDE.md は参照先の索引として短くなっている | なし |
| 153 | I075 | 閉じる | ② ④ | P2（CI に Redis が無い）は `.github/workflows/ci.yml` の redis サービスで解決済み。P1 はレビュー観点の追加だけ | backlog F1 |
| 154 | I076 | 閉じる | ④ | 観点の追加だけ。テナント境界の観点は `.claude/agents/code-reviewer.md` にある。問題の作成・更新の越境は `backend/problems/views.py:256-259,309-312` で拒否済み（I103）を Claude が確かめた | なし |
| 168 | I085 | 閉じる | ① ② | 動的入力まで網羅させる方針は逆転した（`docs/runbooks/review-rules.md`「普通の書き方の事故まで」・I179） | なし |
| 172 | I088 | 統合→#335 | ③ | 不具合は残っている（`scripts/claude/hooks/pretooluse_guard.py:2553,2557` が貪欲な `re.search` のまま、Claude が確かめた）。見張りの止め方を見直す #335 I200 で扱う | #335 の本文の読み替えに同梱 |
| 173 | I089 | 閉じる | ② | `scripts/claude/gate-check.sh` が REVIEWED_COMMIT から HEAD までを照合する（`docs/runbooks/workflow.md:52`） | なし |
| 175 | I090 | 閉じる | ② | fix-loop は止める指摘だけを直し、ほかは retro が後続へ回す（`.claude/skills/fix-loop/SKILL.md:15`） | なし |
| 176 | I091 | 閉じる | ② ④ | スパイク実証は `docs/runbooks/plan-writing-rules.md`「外部/ハーネス挙動依存のスパイク実証」(1) にある。残りは plan-reviewer の観点の追加だけ | なし |
| 177 | I092 | 閉じる | ② | `docs/runbooks/worktree.md`・`scripts/claude/wt-ports.sh`・`wt-remove.sh` が実在 | なし |
| 179 | I093 | 閉じる | ④ | grill-me・plan-reviewer に 1 項目ずつ足すだけ。元の事例は /plan-issue の段階で捕まった | なし |
| 180 | I094 | 残す | なし | false-green の確かめに「削除・反転・挿入」の種類の決まりがまだ無い（`plan-writing-rules.md` の false-green 節は「壊した状態」だけ）。I185 で手戻りの実例あり | #189・#289・#294・#230 の中身を同梱 |
| 189 | I099 | 統合→#180 | ③ | ゲート・assert の発火可能性は #180 の false-green 節の見直しと同じ穴 | #180 の本文の読み替えに同梱 |
| 191 | I101 | 残す | なし | `docs/issues/open/` に I031〜I034・I036・I040〜I044・I047 が残り、closed にも同じ番号がある（`git ls-files docs/issues/open` で確認） | なし |
| 197 | I105 | 閉じる | ④ | 認可の観点の追加だけ。元の I104 は別イシューで直っている | backlog F2 |
| 206 | I111 | 閉じる | ① ② | /code-review は廃止。CI の失敗は review-gate→fix-loop が扱い、close で `scripts/claude/pr-base-sync.sh` が develop に追いつかせる | なし |
| 207 | I112 | 閉じる | ④ | 分類ルール・観点の追加だけ。手戻りは無かった | backlog F7 |
| 208 | I110 | 閉じる | ④ | 観点の追加が中心。Human に回すのは観測できない項目だけになった（`plan-writing-rules.md`「実施者の区別」・I187・I195） | backlog F4 |
| 214 | I116 | 閉じる | ④ | レビュー観点に 1 行足すだけ。高リスクの変更は敵対的レビューと組み込みの /security-review が見る | backlog F8 |
| 216 | I118 | 閉じる | ① | 「/test で記録し /code-review が空欄を止める」流れは廃止。Claude の手動テストは test-gate がまとめて行い記録する | なし |
| 222 | I120 | 閉じる | ② | 画面確認は Claude が Playwright で行う（`docs/runbooks/frontend-verify.md`）。Human の振り分けは `scripts/claude/check-manual-test-executor.sh` が見る | なし |
| 226 | I123 | 統合→#268 | ③ | 依存監査の是正の手順は、依存監査を作り直す #268 I152 の中で決まる | #268 の本文の読み替えに同梱 |
| 227 | I124 | 閉じる | ② | 計画レビュー役の観点「コマンド衛生」に既にある（`.claude/agents/plan-reviewer.md`） | なし |
| 230 | I125 | 閉じる | ④ | grill-me と計画レビュー役に 1 行ずつ足すだけ。実例は計画の段階で捕まった | #180 の本文の読み替えに同梱（AC の確かめの手段が実在するか） |
| 231 | I126 | 閉じる | ① ② | 3 点とも片付いた（高リスク判定は計画レビュー役・環境の整備は I187・I195・レート制限の観点は plan-reviewer・code-reviewer にある） | なし |
| 233 | I128 | 閉じる | ② ④ | 止めるとき・人の手動テストの手前・振り返りには平易に伝える決まりが既にある（`workflow.md`・test-gate・retro）。残りは grill-me の出し方の 1 か所だけ | backlog F9 |
| 237 | I130 | 残す | なし | P1（引用符の中の `|` で BLOCKER）が未修正（`scripts/claude/code-review.sh` の `classify_gate`）。P3・P4 の手順も無い | なし（P2 は ④ で外す） |
| 244 | I135 | 閉じる | ② | 下流の決定論ゲートは `gate-check.sh`、集計は `adversarial-review.sh`、敵対的レビュー役は読むだけ（`.claude/agents/adversarial-reviewer.md` の tools）（I193・I197） | なし |
| 245 | I136 | 閉じる | ④ | 観点を 1 行足すだけ。P3 の実例は `gate-check.sh` の `core.quotePath=false` で解決済み | なし |
| 247 | I138 | 閉じる | ① ④ | test-gate は手元でビルド・重いテストを流し直さないので、前提がほぼ無い。残りは観点の追加だけ | なし |
| 250 | I139 | 残す | なし | `code-review.sh` の omission_lint が fence の種類・字下げを区別しない、`check-*.sh` を受け付けない、`check-memo-body-paths.sh` が見出しの完全一致で黙って合格する、がどれも未解決 | #279 の中身を同梱 |
| 252 | I141 | 閉じる | ④ | grill-me に手順を足すだけ。修正の流れでは fix-loop の診断メモに同型バグの章がある | backlog F2 |
| 255 | I143 | 閉じる | ① | /test が手元で Jest・E2E を流すことが前提。今の test-gate は流し直さない | なし |
| 258 | I144 | 閉じる | ② | 計画レビューが高リスクなら plan-review が `NEXT: design-security-review` を書き、`scripts/claude/flow-stage.sh` が決定論でその段階へ進める | backlog F3 |
| 259 | I145 | 閉じる | ① ② | 再実行の範囲は前提が廃止（`gate-check.sh` が決定論で見る）。Human の実行資源は、手動テストを原則 Claude にしたことで大半が解決 | backlog F4 |
| 268 | I152 | 残す | なし | `ci.yml` の監査は今もリポジトリ全体を見る形のまま | #226 の中身を同梱 |
| 278 | I160 | 残す（範囲を縮める） | なし | 相互依存の通過経路は未実装（`code-review.sh` の CI 待ちは fail が 1 つでも止まる）。CI 待ちの時間切れの部分は I193 で解決済みなので外す | なし |
| 279 | I161 | 統合→#250 | ③ | 計画の段階で omission-lint を走らせる話は、omission_lint を作り直す #250 と同じ関数 | #250 の本文の読み替えに同梱 |
| 280 | I162 | 閉じる | ② | 実施者は原則 Claude、画面は Playwright MCP で確かめる（I187・I195） | なし |
| 283 | I165 | 閉じる | ① ② | 直す対象の `fix-implementation-review.sh` は I197 で廃止。方式を変えたら plan-review を通り直す決まりは `workflow.md:60` にある | backlog F5 |
| 289 | I171 | 閉じる | ② ④ | 発端の事例は I151 の中で捕まり、敵対的レビューに「必ず確かめる項目」「未検証は合格にしない」が入った（I197・I205）。残りは書き方・観点の追加 | #180 の本文の読み替えに同梱（応答の中身で確かめる） |
| 290 | I172 | 閉じる | ② | 「止めて聞く条件は 3 つだけ」と「自律判断の記録」が入った（`workflow.md:39-47`・I193） | なし |
| 291 | I173 | 閉じる | ② | 3 件とも直った（次の段階は plan-review が決める・[I074] の見出しは無い・判定行が無ければ止まる） | backlog F6 |
| 294 | I175 | 閉じる | ② ④ | 承認画面の判定は I187 で `claude -p`・`check-permission-prompt.sh` に置き換わった。残りは観点の追加 | #180 の本文の読み替えに同梱（信号を対照で確かめる） |
| 295 | I176 | 閉じる | ① ② ④ | 上限到達時の部分は I181 で済み、想定する相手は「普通の書き方の事故」と決まった（`.claude/agents/adversarial-reviewer.md`）。grill-me に聞かせる部分は、grill-me が価値判断だけを聞く形になり前提が合わない | なし |
| 296 | I177 | 閉じる | ① | 前提は「ユーザーが起票コマンドを写して打つ」こと。retro が issue-bootstrap を呼んで起票まで行う形になった（I193） | なし |
| 316 | I186 | 残す | なし | 定期の見直しの仕組みはまだどこにも無い（I193 でも範囲外） | なし |
| 319 | I188 | 閉じる（取り下げ） | ② | ユーザー決定（2026-10-24・`docs/issues/closed/I193.md`）に沿って確かめた。同じ名前の重なりの解消・レビュー役の `.claude/agents/` への移動・公式に無い部分だけ残す判定は I193 で済み、残る作業は無い | なし |
| 321 | I189 | 残す | なし | 登録の直前に同じ番号のタイトルを確かめる処理がまだ無い（`.claude/skills/issue-bootstrap/SKILL.md`・`scripts/claude/next-issue-num.sh`） | なし |
| 324 | I191 | 残す | なし | 効果測定。10-31 10:30Z の予約のコメントを待つ。今の流れで起票済み | なし |
| 325 | I192 | 閉じる（取り下げ） | ② | ユーザー決定（同上）に沿って確かめた。/plan-issue から review-gate・test-gate まで続けて進み、手元の pytest・Jest・E2E の流し直しは廃止、fix-loop の戻り先は review-gate の 1 か所になった（`workflow.md:22-28`）。残る作業は無い | なし |
| 335 | I200 | 残す | なし | 見張りの確認を絞る作業は未着手。今の流れで起票済み | #172 の中身を同梱 |
| 337 | I201 | 残す | なし | 変えたファイルからテストを選ぶ作業は未着手。今の流れで起票済み | なし |

## Claude が決めた点（サブエージェントの案が割れた・迷いがあった件）
- #172: 単独で残す案もあったが、同じファイル（見張り）の見直しを扱う #335 に統合する。誤って止める（exit 2）不具合なので、#335 の「確認を減らす」とは焦点が違うが、同じ関数の近くを触るため一緒に直すのが手戻りが少ない。統合のコメントに「確認を減らす話ではなく誤ブロックの修正」と明記する
- #189: ④ で閉じる案もあったが、残す #180 の false-green 節の見直しと同じ穴なので統合にする
- #233: 残す案だったが、平易に伝える決まりは止める場面すべてに既にあり（`workflow.md`・test-gate・retro）、残るのは grill-me の出し方の 1 か所だけなので閉じて一覧（F9）に回す
- #278: #268 に統合する案もあったが、相互依存の通過経路は依存監査以外の原因でも起きうるので残す（範囲を縮める）
- #279: 残す案もあったが、同じ `omission_lint` 関数を作り直す #250 に統合する
- #291: 診断レビューの SKIP の素通りが残るが、直した後は必ず review-gate を通るので閉じ、一覧（F6）に回す
- #154: サブエージェントが「未確認のアプリの越境」を挙げたが、Claude が確かめて拒否済み（`backend/problems/views.py:256-259,309-312`）。アプリ側の後続は無い
- 小さな指摘の行き先が閉じるイシュー（#252・#294）になっていたものは、#180 か一覧へ付け替えた

## 残すイシューの先頭に足す「今の流れでの読み替え（I209）」
共通の書き出し: `## 今の流れでの読み替え（I209・2026-10-28）` の見出しの後に次の行を書き、最後に `---` で元の本文と区切る。共通の 1 行目: 「I193・I197 で流れを組み直した。ユーザーが打つのは /issue-bootstrap・/grill-me・/plan-issue・/proceed だけで、/code-review・/test・/plan-issue-review などの自作のコマンドは段階のスキル（plan-review・implement・review-gate・test-gate・fix-loop・retro・close）に置き換わった。本文の古い名前は次のように読む」

| # | 読み替え | まだ残っている作業 |
|---:|---|---|
| 180 | plan-issue-review → plan-review 段階（`.claude/agents/plan-reviewer.md`）。`.claude/review-agents/` → `.claude/agents/` | `plan-writing-rules.md` の false-green 節に「守りの部分は削除・反転・挿入の 3 種類の写しで偽合格を確かめる」を入れるか決め、決定論テストの雛形に寄せる。同梱: #189（ゲート・assert に NG を返す入力を 1 つ示す）・#289（ステータスコードだけで合否を決めず応答の中身で確かめる）・#294（判定に使う信号は対照で確かめる）・#230（受け入れ条件ごとに確かめる手段が実在し対象を通ることを確かめる） |
| 191 | close スキル → close 段階（`.claude/skills/close/SKILL.md`。記録の移動は `git mv` 化済み） | `docs/issues/open/` の I031〜I034・I036・I040〜I044・I047 と closed の同じ番号を突き合わせ、重複を整理する。再発防止は簡単なチェック 1 本で足りるかを決める |
| 237 | /code-review の機械判定 → review-gate が呼ぶ `scripts/claude/code-review.sh` | P1（`classify_gate` の引用符の考慮とテスト・ゲートで実行できる書き方の明文化）・P3（起票後の GitHub 本文の同期）・P4（plan-issue でのイシューファイルの復元）。P2（計画変更時の旧値の検索）は I209 の基準 ④ で外す |
| 250 | /code-review の機械判定 → review-gate が呼ぶ `scripts/claude/code-review.sh`。/plan-issue-review → plan-review 段階（`scripts/claude/plan-issue-review.sh`） | 本文の解決方針 1〜5。同梱: #279（計画の段階〔`plan-issue-review.sh`〕でも omission-lint を流す・plan-issue の生成物にテンプレートのパスを書き添える）。#237 が先 |
| 268 | /code-review → review-gate。依存監査の runbook は `docs/runbooks/dependency-audit.md` | 本文どおり（着手前に内容を再検討する）。同梱: #226（是正イシューの標準手順〔lockfile の写しに模擬適用して残り件数・ゲートの合否・宣言ファイル無変更を測る〕を runbook に書く） |
| 278 | /code-review の CI ゲート → review-gate が呼ぶ `scripts/claude/code-review.sh` の CI 待ち | 相互依存の宣言と、合流 PR の全緑・既知の失敗ステップで通す部分だけ。CI 待ちの時間切れを止める側に倒す部分は I193 で解決済みのため外す。#268 の結果で必要性が変わりうる |
| 316 | 周回数・承認の回数 → 段階の記録（`STAGE_DONE` の行）とレビューの台帳から数える | 公式機能を回す順番の手順と、承認の回数・周回数の数え方を作る。#324 I191 の結果を入力にする |
| 321 | 起票 → `/issue-bootstrap` に加えて retro 段階も issue-bootstrap を呼んで起票する（並行トラックで番号がぶつかる危険が増えた） | 本文どおり（登録の直前に同じ番号のタイトルを確かめ、スクリプトとテストで固める） |
| 324 | 今の流れで起票済み（読み替えなし） | 本文どおり |
| 335 | 今の流れで起票済み（読み替えなし） | 本文どおり。同梱: #172（`pretooluse_guard.py` の `--all/--mirror/--repo` の判定が貪欲な正規表現で、安全な push を誤って止める。確認を減らす話とは別の誤ブロックの修正） |
| 337 | 今の流れで起票済み（読み替えなし） | 本文どおり |

## 反映の結果
（2026-10-28 implement。ユーザー確認の後に反映。時刻は UTC。閉じた件は `gh issue list --state closed --label track:harness --search "closed:>=2026-10-28"` の stateReason・closedAt）

### 残す 11 件（本文の先頭に読み替えを追記）
- #180・#191・#237・#250・#268・#278・#316・#321・#324・#335・#337: 追記済み。追記の前の本文は `docs/reviews/open/I209_original_bodies/<番号>.md`、足した節は `<番号>.header.md`。11 件とも、送った本文（`.header.md` ＋ `.md` を `cat` でつなげたもの）と、更新後に `--template "{{.body}}"` で取った本文が `cmp` で一致（exit 0）
- #335 には、計画にないコメントを 1 件足した（#172 の誤ブロックの再現の実例。下の「計画と違ったこと」）

### 統合 4 件（DUPLICATE）
| # | 統合先 | closedAt |
|---:|---|---|
| 172 | #335 | 2026-10-28T10:52:19Z |
| 189 | #180 | 2026-10-28T10:51:58Z |
| 226 | #268 | 2026-10-28T10:52:03Z |
| 279 | #250 | 2026-10-28T10:52:07Z |

### 閉じる 37 件
| # | stateReason | closedAt |
|---:|---|---|
| 10 | NOT_PLANNED | 2026-10-28T10:52:28Z |
| 153 | COMPLETED | 2026-10-28T10:52:31Z |
| 154 | NOT_PLANNED | 2026-10-28T10:52:34Z |
| 168 | COMPLETED | 2026-10-28T10:52:36Z |
| 173 | COMPLETED | 2026-10-28T10:52:39Z |
| 175 | COMPLETED | 2026-10-28T10:52:42Z |
| 176 | COMPLETED | 2026-10-28T10:52:46Z |
| 177 | COMPLETED | 2026-10-28T10:52:49Z |
| 179 | NOT_PLANNED | 2026-10-28T10:52:52Z |
| 197 | NOT_PLANNED | 2026-10-28T10:52:55Z |
| 206 | COMPLETED | 2026-10-28T10:53:01Z |
| 207 | NOT_PLANNED | 2026-10-28T10:53:05Z |
| 208 | NOT_PLANNED | 2026-10-28T10:53:09Z |
| 214 | NOT_PLANNED | 2026-10-28T10:53:12Z |
| 216 | NOT_PLANNED | 2026-10-28T10:53:15Z |
| 222 | COMPLETED | 2026-10-28T10:53:18Z |
| 227 | COMPLETED | 2026-10-28T10:53:21Z |
| 230 | NOT_PLANNED | 2026-10-28T10:53:23Z |
| 231 | COMPLETED | 2026-10-28T10:53:26Z |
| 233 | COMPLETED | 2026-10-28T10:53:29Z |
| 244 | COMPLETED | 2026-10-28T10:53:35Z |
| 245 | NOT_PLANNED | 2026-10-28T10:53:38Z |
| 247 | NOT_PLANNED | 2026-10-28T10:53:40Z |
| 252 | NOT_PLANNED | 2026-10-28T10:53:43Z |
| 255 | NOT_PLANNED | 2026-10-28T10:53:45Z |
| 258 | COMPLETED | 2026-10-28T10:53:48Z |
| 259 | COMPLETED | 2026-10-28T10:53:51Z |
| 280 | COMPLETED | 2026-10-28T10:53:53Z |
| 283 | COMPLETED | 2026-10-28T10:53:56Z |
| 289 | COMPLETED | 2026-10-28T10:53:59Z |
| 290 | COMPLETED | 2026-10-28T10:54:05Z |
| 291 | COMPLETED | 2026-10-28T10:54:08Z |
| 294 | COMPLETED | 2026-10-28T10:54:10Z |
| 295 | COMPLETED | 2026-10-28T10:54:13Z |
| 296 | NOT_PLANNED | 2026-10-28T10:54:16Z |
| 319 | COMPLETED | 2026-10-28T10:54:19Z |
| 325 | COMPLETED | 2026-10-28T10:54:21Z |

### 計画と違ったこと
- #172 の最初の閉じるコマンドは、コメントの文中に push のオプション名（全参照・ミラー）を書いたため、`pretooluse_guard.py` に「requires DANGER_OK=1」で止められた（#172 の誤ブロックそのものの再現）。オプション名を言い換えたコメントで閉じ直し、再現の実例を #335 にコメントで残した（直すときの回帰テストの入力になる）
- 「反映の結果」は 1 件ずつではなく、全件を流した後に GitHub から状態を取ってまとめて書いた（状態は GitHub が正なので、取り直した値のほうが確か）
