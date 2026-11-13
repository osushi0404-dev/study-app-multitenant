# I430 計画書: サンドボックスを土台にした見張りの組み直しと許可の設定の整理

## 基本情報
- **計画書ID**: plan_I430
- **関連イシュー**: #430
- **Draft PR**: #506
- **作成根拠資料**: docs/issues/open/I430.md（GitHub #430 の本文の写し・正は GitHub）
- **実装後評価**: docs/reviews/open/I430_review.md
- **作成日**: 2026-11-13

## 1. 背景/目的
- 見張り（`scripts/claude/hooks/pretooluse_guard.py`・3,880 行）は、公式のサンドボックス・許可の設定・ワークツリーの隔離を使わずに、シェルの読み解きから自作で大きくなった。公式を土台にした見直しを一度も通っていない（イシューの根本原因 7）
- 目的: 公式の守り（サンドボックス・許可の設定）と GitHub の守り（ブランチ保護）だけで組んだ守りを先に描き、それで止まらない漏れだけを見張りに残す。公式・GitHub で足りる判定は見張りから消し、行数を減らす。許可の設定も auto mode を前提に見直す
- 脅威モデルは「事故」のまま（意図的な回避は対象外。`docs/runbooks/danger-ops.md`）

## 調査結果

### 環境の前提（2026-11-13 に確認）
- Claude Code 2.1.323（`claude --version`）・WSL2（Ubuntu 24.04）
- サンドボックスに要る bubblewrap 0.9.0-1ubuntu0.3・socat 1.8.0.0-4ubuntu0.1 は、2026-11-13 にユーザーが入れた（`which bwrap socat` → `/usr/bin/bwrap`・`/usr/bin/socat`）。sudo は deny なので Claude は入れられない（設計確認メモ 2026-11-13）
- 新しい PC で作業を始めるときも同じ 2 つが要る → onboarding.md に足す（4-5）

### 公式の文書で確かめたこと（https://code.claude.com/docs/en/sandboxing.md ・2026-11-13 に確認）
| 事柄 | 文書の記述（要約） |
|---|---|
| 効く範囲 | Bash（と Monitor）のコマンドとその子プロセスだけ。Read・Edit・Write・WebFetch・MCP・フックはサンドボックスの外（許可の設定が効く）。サブエージェントの Bash にも効く |
| 書き込み | 既定は作業ディレクトリの下・`$TMPDIR`・追加したディレクトリだけ。`filesystem.allowWrite`／`denyWrite` で足し引きする。リンクされたワークツリーでは共有の `.git` への書き込みを許す（`hooks/`・`config` は拒否） |
| 読み取り | 既定はほぼ全体（`~/.ssh` を含む）。`filesystem.denyRead` で塞ぐ。Read の deny ルールの場所も塞がれる（下の試し S4 で確認） |
| 通信 | `network.allowedDomains` の宛先だけ（既定は空）。`strictAllowlist: true` で一覧の外は確認を出さずに拒否。TLS の中身は見ないので、許可した宛先経由の持ち出しは止めない |
| 外に出すコマンド | `excludedCommands`（`Bash(...)` と同じ書き方。`docker *` は引数なしも含む）。1 回の呼び出しの中のコマンドが**すべて**当たるときだけ外で動く。文字どおりの一致（スクリプトの中から呼ぶ docker は当たらない）。外に出したコマンドは許可の設定（allow・ask・deny・auto mode の判定役）を通る。「インタプリタや作業ディレクトリのファイルを動かす道具を外に出すと、書いたファイルを外で動かせる」と警告がある |
| 自動で通す | `autoAllowBashIfSandboxed`（既定 true）。サンドボックスの中のコマンドは承認なしで通る。deny は効く。中身つきの ask（`Bash(git push *)` など）は確認を出す |
| 外での再実行 | `allowUnsandboxedCommands: false` で、`dangerouslyDisableSandbox` による外での再実行を無効にする（Strict sandbox mode） |
| 使えないとき | `failIfUnavailable: true` で、サンドボックスを起こせないときに起動を止める（既定は外で動かす） |
| docker | サンドボックスと両立しない。`excludedCommands` に `docker compose *` などを入れる |

### 試し（スパイク）の結果（2026-11-13・`claude -p`・haiku・`--setting-sources user --settings <試しの設定>`。試しの道具はスクラッチパッドに置き、リポジトリには入れていない）
試しの設定は、今の `.claude/settings.json` に `sandbox`（enabled・autoAllow・allowUnsandboxedCommands=false・excludedCommands・allowedDomains=github.com/api.github.com）を足し、見張り（PreToolUse）を外したもの。S11〜S13・S15 は見張りを残した版。

| No | 確かめたこと | 結果 |
|---|---|---|
| S1 | 作業場所の中への書き込み・`rm`・`&&` を承認なしで通すか（manual モード） | 成立。承認なしで通った。中では `SANDBOX_RUNTIME=1`・`TMPDIR=/tmp/claude-1000` |
| S1b | 変数（`$TMPDIR`）を含むコマンド（manual モード） | 「変数を事前に確かめられない」の確認になった（サンドボックスでも自動では通らない）。auto モードでは S16 のとおり通る |
| S2 | ワークツリー（harness-1）のセッションから、別のワークツリー（app-1）・primary・共有の `.git/hooks` への書き込み | 成立。3 つとも `Read-only file system` で止まった。共有の `.git` の直下への書き込みは通った（文書どおり） |
| S3 | 通信: `api.github.com`（許可）と `example.com`（一覧の外） | 成立。前者 200・後者は接続できない |
| S4 | 読み取り: `backend/.env`（Read の deny に当たる）・`~/.config/github-app/app.pem`（リポジトリの外の App の鍵） | `.env` は止まった。**App の鍵は読めた**（Read の deny `**/*.pem` はリポジトリの中だけ）→ S11 |
| S5 | `git add`・`git reset`（ワークツリーの索引への書き込み）と `pre-commit run --files`（既存の環境） | 成立。どちらも通った |
| S6 | `docker compose ps`（外に出す） | 成立。承認なしで動いた |
| S7 | `gh issue view 430 --json state`（外に出す） | 成立。`{"state":"OPEN"}` |
| S8 | `git fetch --dry-run origin develop`（外に出す） | 成立 |
| S9 | `git push --dry-run …`（外に出す） | 成立（GitHub まで届き、読み取りだけの鍵なので 403。外で動き、資格情報の仕組みが働いた） |
| S10 | サンドボックスの中から `bash scripts/claude/test-session.sh`（レビュー役の `claude -p`）を起こす | **不成立**。`api.anthropic.com` への通信が拒否された → `bash scripts/claude/*` を外に出す（S13） |
| S11 | `filesystem.denyRead` に `~/.config/github-app`・`~/.cache/github-app` を足す | 成立。App の鍵と 1 時間の鍵の控えが読めなくなった。`README.md` は読める |
| S12 | 外に出した `bash scripts/claude/issue-source.sh gh-number I430`（中で gh を呼ぶ） | 成立。`430` |
| S13 | 外に出した `bash scripts/claude/test-session.sh …`（レビュー役） | 成立。`PONG` が返った。`… | tail` を付けると `tail` が外に出す一覧に当たらず、中で動いて失敗した（文書どおり） |
| S14 | サンドボックスの設定がプロジェクトの `.claude/settings.json` から効くか・ワークツリーではどちらの設定が効くか（一時のリポジトリ） | 成立。プロジェクトの設定から効き、**ワークツリーのセッションではワークツリー自身の設定が効く**（本体の設定ではない）。許可（allow）は信頼の済んでいないフォルダでは無視されたが、サンドボックスは効いた |
| S15 | auto モード・見張りつき | 見張りは今までどおり先に止める（別のワークツリーへの書き込み） |
| S16 | auto モード・見張りなしで、変数入りのコマンドと別のワークツリーへの書き込み | 変数入りは通り、別のワークツリーへの書き込みはサンドボックスが止めた |
| S17 | 見張りなし・manual モードで、Write ツールで別のワークツリーに書く | 確認になった（承認なしでは書けない） |
| S18 | 見張りなし・**auto モード**で、Write ツールで別のワークツリーに書く | **書けてしまった**（判定役が通した。書いたファイルはすぐ消した）→ Edit／Write の別ワークツリーの判定（G01）は見張りに残す |
| S19 | primary のセッションで、作業ディレクトリの中の `.claude/worktrees/` への書き込みを `filesystem.denyWrite` で止める（相対・`./` つき・絶対の 3 通り） | 成立。3 通りとも止まり、ほかの場所には書けた |

### 見張りの判定の棚卸し（読み取り・2026-11-13）
判定は 39 種（G01〜G39）。主なものと、公式・GitHub で代わりに止まるか（全体の表は 4-1）:
- 入口は `main()`（3707–3838）。出口は `_block`（28）・`_block_cross_worktree`（846）・`_ask`（866）・`_fail_safe`（3853）
- 判定の多く（G10〜G35）はホストとコンテナで同じ関数を使う（`_expand` 1823–1843 で docker の中身を `ctr=True` にして同じ判定に通す）。コンテナの判定は docker を外に出すので残り、土台の大半（F07・F09〜F17・約 1,400 行）は消せない
- 公式・GitHub に置き換えられるのは、Bash の別ワークツリーへの書き込み（G02・G03）・保護ブランチへの push（G05・G09）・fork の PR の扱い（G33〜G35 と gh 専用の読み方 F18）

### 見張りが実際に止めた・確認を出した回数（会話の記録・2026-10-14〜11-13・全ワークツリーとサブエージェントの記録・ツール呼び出しの id で重複を除いた）
- 対象: 記録 1,311 本（メイン 784・サブエージェント 527）・Bash 約 19,600 回
- **止めた 72 件**: 事故を止めたと言えそうなのは約 4 件（未コミットの変更の取り消し 3・Playwright の書き先が秘密ファイル名 1）。残りの約 9 割は止める必要のない操作（一時フォルダの片付け・見張りのテストの中の文字列）
- **確認 184 件**: 確認が要ったのは約 20 件（実際の `.env` の読み出しなど）。約 8 割は要らない確認
- **別のワークツリーへの書き込みを止めた記録は 0 件**。保護ブランチへの push を止めた 5 件は、すべて一時フォルダの空のリモート宛て（見張りのテスト）。fork の PR を扱った記録は 0 件
- 「絶対パス宛先のみ検査します」の警告（G03）は約 940 回出ていた（止めない通知）
- 限界: 約 30 日より古い記録は無い・本物か誤検知かは中身からの手の判断・`claude -p` の確認は記録に残らないことがある

### GitHub の守り（2026-11-13 に `gh api repos/…/branches/develop` と `docs/runbooks/branch-protection-setup.md` で確認）
- develop は保護あり（必須チェック 6 本・`enforcement_level: everyone`）。PR 必須・Code Owners（`oshui0404`）の承認必須・「Do not allow bypassing」ON・「Restrict who can push」で `oshui0404` 以外は push もマージもできない。bot（App）の直接の push・マージ・承認は効かない
- main も同じ設定（CODEOWNERS は develop の内容が届くまで無いが、push の制限で bot はマージできない）

### コーディング規約
- バックエンド・フロントエンドのコードは変えない。`rules/ultimate_django_coding_standards.md`・`rules/react-coding-standards-integrated.md` の対象外

## 2. 受け入れ条件
- [ ] AC1: 公式（サンドボックス・許可の設定・ワークツリーの隔離）だけで組んだ守りと、それで止まらない漏れの一覧が、出典の公式文書つきで計画書にある（4-1）。見張りに残す判定は、すべて「公式でも GitHub でも止まらない漏れ」に対応している
- [ ] AC2: 公式に任せると決めた判定ごとに、実際に動かして止まることを確かめた結果がある（調査結果の S1〜S19 と、最終の設定での手動テスト M-01〜M-12）。docker・`gh`・`git push`・`claude -p` のレビュー役が今までどおり動くことも確かめてある
- [ ] AC3: 公式で足りる判定は見張りから消えており、`pretooluse_guard.py` の行数が 3,880 行（2026-11-13）から **3,050 行以下**になっている（TC-08）。消した判定 → 代わりに止める仕組みの対応が 4-3 にある
- [ ] AC4: 許可の設定の整理（auto mode を前提にした allow・`autoMode.environment`）について、変える・変えないの結果と根拠が 4-4 にある
- [ ] AC5: サンドボックスが有効で、中の Bash が確認の画面なしで通る。外に出したコマンドの一覧と理由が 4-2 にあり、`claude -p` で承認画面の出方を確かめた結果がある（M-01・M-06〜M-08）
- [ ] AC6: danger-ops.md と plan-writing-rules.md に「見張りに判定を足すときの決まり」（公式で表せないかを先に書く・事故の実例を書く・意図的な回避の指摘は一覧へ）がある（TC-11・TC-12）
- [ ] AC7: 既存のハーネステスト（`bash scripts/claude/tests/run-all.sh`）・CI がすべて pass する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `.claude/settings.json`（`sandbox` の追加・deny 2 行の追加・PreToolUse の GitHub MCP の登録の削除。安全装置）
  - `scripts/claude/hooks/pretooluse_guard.py`（判定の削除。安全装置・高リスク）
  - ハーネステスト（`scripts/claude/tests/` の見張りと設定のテスト）
  - 手順書: `docs/runbooks/danger-ops.md`・`docs/runbooks/plan-writing-rules.md`・`docs/runbooks/workflow.md`（fork の PR の節）・`docs/runbooks/worktree.md`（§9）・`docs/runbooks/onboarding.md`（道具の準備）・`CLAUDE.md`（§3 に 1 行）
  - 手元の環境: Claude Code のセッションの Bash が、すべてサンドボックスの中で動くようになる。マージの後は primary（develop）のセッションも同じ。ワークツリーのセッションでは、そのワークツリーの `.claude/settings.json` が効く（S14）ので、このブランチのワークツリー（harness-1）では、設定を変えた時点からこの会話の Bash にも効く見込み

## 4. 変更点一覧（具体）

### 4-1. 公式と GitHub だけで組んだ守りと、それで止まらない漏れ（AC1）
確認の基準 (A) GitHub の破壊・(B) 復旧できない状態・(C) 秘密や個人情報の流出（`docs/runbooks/danger-ops.md`「確認を出す基準（I200）」）ごとに、公式・GitHub の守りを先に描く。

| 守るもの | 公式・GitHub の守り（出典） | 止まらない漏れ | 見張りの扱い |
|---|---|---|---|
| (B) 別のワークツリー・primary への Bash の書き込み | サンドボックスの書き込みの制限（sandboxing.md「Default write behavior」・S2）。primary のセッションからの `.claude/worktrees/` は `denyWrite`（S19） | 外に出したコマンド（docker・gh・git push/fetch/pull・`bash scripts/claude/*`）の中の書き込み | G02・G03 を消す。漏れは「外に出すものは書き込み先を持たない道具か、レビュー済みのリポジトリのスクリプトだけ」で受け入れる（4-2） |
| (B) 別のワークツリーへの Edit／Write | 無い（Edit はサンドボックスの外。auto モードで通った・S18。deny は「primary の下、ただし自分は除く」を書けない） | 全部 | **G01 を残す** |
| (B) 作業ディレクトリの中の戻せない操作（未コミットの変更の取り消し・`reset --hard`・`clean -f`・`rm -r`・`find -delete`） | 無い（中は書ける） | 全部 | G13〜G15・G32 を残す |
| (B)(C) コンテナの中の操作（DB の破壊・秘密の表示・外部への送信・/tmp 以外への書き込み） | 無い（docker は外に出す・sandboxing.md「docker is incompatible」） | 全部 | G16〜G23・G26・G27・G29〜G31 を残す（コンテナの許可リストの整理は #444 の範囲で済んでいる） |
| (A) develop／main への push・保護ブランチへの宛先の決まらない push | GitHub のブランチ保護（PR 必須・bypass 不可・Restrict who can push。bot は push できない）と既存の deny（`git push origin develop` など） | 無い（拒否される。手元の作業は残る） | G05・G09 を消す |
| (A) force push・`--all`／`--mirror`・リモートブランチの削除・push の設定の変更 | 保護ブランチの分は GitHub。作業ブランチは無い | 作業ブランチ（別のワークツリー・別のセッションの push 済みの作業）の上書き・削除 | G06・G07・G10・G11 を残す |
| (C) 秘密の検査を飛ばす `--no-verify`／`-n` | push protection（push の時点）と CI の detect-secrets（push の後）。手元は無い | push してから捕まる（公開リポジトリでは取り消せない） | G08・G12 を残す |
| (A) fork の PR のマージ | GitHub（bot はマージできない・Code Owners の承認必須） | 無い | G33 のマージの判定を消す |
| (A)(B) fork の PR の手元への取り込み（`gh pr checkout`・`gh co`。相手の `.claude/` とフックが手元で動く） | 許可の設定の deny（permissions.md の前方一致） | `git fetch origin pull/<N>/head` などの別の書き方（今も見張りの対象外・workflow.md の手順で扱わない） | G33 の取り込みの判定を消し、deny `Bash(gh pr checkout *)`・`Bash(gh co *)` に置き換える |
| (A) fork の PR への ready・edit・update-branch・承認（今は確認） | GitHub（承認は Code Owners の分しか数えない・マージは bot にできない） | fork の PR の題・本文の書き換え、fork のブランチへのマージコミット（相手のブランチ・取り消せる） | G34・G35 を消す（GitHub の MCP は入れていない・`.mcp.json` は playwright だけ） |
| (C) 手元の秘密ファイルの読み出し（Bash） | Read の deny の場所はサンドボックスでも読めない（S4）。App の鍵は `denyRead`（S11） | `git show`・`git diff` での履歴からの表示・コンテナの中 | G24・G25 は残す（ホストとコンテナで同じ関数を使い、ホストの分だけを分けると判定が増える） |
| (C) 外部への送信（ホストの Bash） | `network.allowedDomains`＋`strictAllowlist`（S3）・既存の deny（`curl`・`wget` など） | 許可した宛先（GitHub）経由の持ち出し（TLS の中を見ない・文書の警告）・外に出したコマンド・コンテナの中 | G20〜G22 は残す（主にコンテナ） |
| (B) Playwright の書き先 | 無い（MCP はサンドボックスの外） | 全部 | G36 を残す |
| (C) ワークフロー・pre-commit の設定の書き換え | 無い（ask にすると毎回確認になる） | 全部 | G37 を残す |
| 見張り自身の読み落とし・失敗 | フックの `timeout`・`onFailure: block`（hooks.md） | — | G38・G39 を残す |

### 4-2. `.claude/settings.json` の変更（AC5・安全装置）
**方針**: サンドボックスを有効にして中の Bash を承認なしで通す（設計確認メモ 2026-11-13）。外での再実行は無効にし、起こせないときは起動を止める（安全側）。外に出すのは「サンドボックスの中では動かないもの」だけにする。

足す `sandbox`:
```json
"sandbox": {
  "enabled": true,
  "autoAllowBashIfSandboxed": true,
  "allowUnsandboxedCommands": false,
  "failIfUnavailable": true,
  "excludedCommands": [
    "docker *",
    "docker-compose *",
    "gh *",
    "git push *",
    "git fetch *",
    "git pull *",
    "bash scripts/claude/*"
  ],
  "filesystem": {
    "denyWrite": [".claude/worktrees"],
    "denyRead": ["~/.config/github-app", "~/.cache/github-app"],
    "allowWrite": ["~/.cache/pre-commit"]
  },
  "network": {
    "allowedDomains": ["github.com", "api.github.com", "pypi.org", "files.pythonhosted.org", "registry.npmjs.org"],
    "strictAllowlist": true
  }
}
```

外に出すコマンドと理由:
| パターン | 理由 |
|---|---|
| `docker *`・`docker-compose *` | docker はサンドボックスと両立しない（文書）。S6 |
| `gh *` | 鍵の取り直しで `~/.cache/github-app` に書く（`~/.local/bin/gh-app-token`）。その場所は `denyRead` で塞ぐので、中では動かない。S7 |
| `git push *`・`git fetch *`・`git pull *` | 資格情報の仕組み（同じ `gh-app-token`）が鍵の控えを読み書きする。S8・S9 |
| `bash scripts/claude/*` | レビュー役の `claude -p`（`api.anthropic.com`・`~/.claude` への書き込み）と、中で gh を呼ぶスクリプト（`issue-source.sh`・`code-review.sh`・`pr-base-sync.sh` ほか 8 本）が中では動かない。S10・S12・S13。ハーネステスト（`run-all.sh` の `uv`）もここに当たる |

- `bash scripts/claude/*` は「作業ディレクトリのファイルを外で動かせる」形（文書の警告）。`scripts/claude/**` は Claude が Edit できる。脅威モデルは事故なので、普通の書き方（手順書どおりのスクリプトの呼び出し）では問題ないと判断し、受け入れる（8. Risk）。`bash *`・`python3 *`・`sh *` のような一般のインタプリタは外に出さない（TC-01 で固定する）
- 最小権限の点検（ユーザーの指示「BP の観点で問題ないやり方で」・2026-11-13）: 外に出すスクリプトを、要るもの（claude・gh・git push・docker を中で呼ぶ約 15 本と run-all.sh）の一覧に絞る案と比べた。どちらも Claude が Edit できるスクリプトが外で動く点は同じで、守りの強さは変わらない。一方、一覧に絞ると、新しいスクリプトが gh などを使い始めたときに、中で黙って失敗する（一覧の漏れに気づきにくい）。そのためディレクトリごとにする。`bash scripts/claude/../<外>` のような `..` を使う書き方は、普通の書き方の事故では起きないので対象外（意図的な回避）
- `denyWrite: [".claude/worktrees"]`: primary のセッションでは他のワークツリーが作業ディレクトリの中にあるため（S19）。ワークツリーのセッションでは、その下にある入れ子（サブエージェントのワークツリー）を守る
- `denyRead`: GitHub App の秘密の鍵と 1 時間の鍵の控え（S4・S11）。gh・git push は外で動くので影響しない
- `allowWrite: ["~/.cache/pre-commit"]`: pre-commit の設定の版を上げた後の最初の `git commit`（中で動く）が、検査の環境を作れるようにする。中の実行ファイルを動かすのは pre-commit だけで、`git commit` もサンドボックスの中で動く
- `allowedDomains`: GitHub（`git clone` で pre-commit の環境を作る・`api.github.com`）と、pre-commit の環境に要る PyPI・npm。`strictAllowlist: true` で一覧の外は確認を出さずに拒否（持ち出しの事故を確認の画面で通さない）

足す deny（4-1 の G33 の置き換え）:
- `"Bash(gh pr checkout *)"`・`"Bash(gh co *)"`（手順で使っていない・2026-11-13 に `.claude/skills`・`scripts/claude`・`docs/runbooks` を grep して 0 件）

消すフックの登録:
- PreToolUse の `"matcher": "mcp__github__merge_pull_request|mcp__github__update_pull_request_branch|mcp__github__create_pull_request_review"`（GitHub の MCP は入れておらず、判定 G35 も消す）

### 4-3. 見張りから消す判定と、代わりに止める仕組み（AC3）
| 消すもの | 主な関数（2026-11-13 の行） | 代わり |
|---|---|---|
| D1: Bash の別ワークツリー・primary への書き込み（G02）と、書き先を読めない旨の警告（G03） | `main` の 3754–3765、`_bash_write_targets`（765–787）・`_split_redir_target`（755–763）・`_bash_uncovered_risk`（828–844）・`_has_write_intent`（789–794） | サンドボックスの書き込みの制限・`denyWrite: [".claude/worktrees"]`（S2・S19） |
| D2: develop／main への push（G05）・宛先の決まらない push の確認（G09） | `_push_protected_target`（590–624）・`_norm_push_dest`／`_push_dest_*`（497–557 のうち G07・G10 が使わない部分）・`_push_is_dynamic`（655–688）と、`_danger_reasons`・`_cmd_danger`・`_analyze`・`main` の呼び出し | GitHub のブランチ保護・既存の deny |
| D3: fork の PR の判定（G33・G34・G35）と gh 専用の読み方（F18） | `_gh_pr_target`（3477–3618）・`_mcp_pr_target`（3621–3642）・`_cross_decision`（3645–3668）・`_guard_cross_repo`（3671–3678）・`_guard_gh_pr_targets`（3681–3704）・`_pr_is_cross_repo*`（2964–3004）・`_safety_net_mismatch`（3168–3174）・`_GH_PR_SPECS`・`_safety_text`・`_gh_coarse_count`・`_shell_code`・`_gh_tokens`（3007–3476）と、`main` の GitHub MCP の分岐（3732–3736）・3789 | GitHub（マージ・承認）と deny `Bash(gh pr checkout *)`・`Bash(gh co *)` |

- 残す判定が使う関数は消さない（実装で `grep` して呼び出し元を確かめる。消せなかったものは計画変更記録に書く）。消した関数の名前が残ったコードから参照されていないことは、`python3 -m py_compile` とテストで確かめる
- **行数の目標: 3,050 行以下**（今の 3,880 行から 830 行以上減らす）。棚卸しの見積もりは D1 約 75・D2 約 120・D3 約 750 行で計 約 945 行。共有の関数が残る分を見込んで目標を 830 行にした
- 残す判定の振る舞いは変えない（判定の条件は触らない）

### 4-4. 許可の設定の整理（AC4・#440 の C23）
- **allow は変えない**。理由: (1) auto モードの判定役に止められたのは 14 日で 1 回ほど（#440 の点検）・承認画面の主な出どころは見張りの確認だった（会話の記録で確認 184 件・うち約 8 割は要らない確認）。見張りの判定を減らすほうが効く (2) サンドボックスの中のコマンドは allow にかかわらず承認なしで通るようになり、allow の Bash の行は外に出したコマンド（docker・gh・git push・スクリプト）と、manual モードで動く `claude -p`（`check-permission-prompt.sh`）の判定にだけ効く。外に出したコマンドの承認なしの範囲を今のまま保つため、行を消さない
- **`autoMode.environment` は足さない**。理由: 判定役の拒否が少なく（14 日で 1 回ほど）、サンドボックスの中のコマンドは判定役を通らなくなる
- **`Read(*)`・`Grep(*)`・`Glob(*)` は変えない**。`claude -p` が「作業ディレクトリでは既定と同じで何も足さない」と警告を出す（S10 の出力）。`Read` に変えると作業ディレクトリの外も確認なしで読めるようになり、範囲が広がる。警告は表示だけで害が無い。片付けは #450（古い記述の片付け）の範囲
- 足す deny は 4-2 の 2 行だけ

### 4-5. 手順書・CLAUDE.md
- `docs/runbooks/danger-ops.md`「見張り（pretooluse_guard.py）の扱い」:
  - 先頭に「第 1 層はサンドボックス（`.claude/settings.json` の `sandbox`）。見張りは公式と GitHub で止まらない漏れだけを見る」と、4-1 の要約（公式に任せたもの → 仕組み）を足す
  - 1.「常に止める」から「別 worktree への書き込み」を Edit 系だけに直す（Bash はサンドボックス）。2. の「保護ブランチへの push」を外し、GitHub のブランチ保護に任せたと書く。(A) の「fork（外部）の PR の取り込み」は deny と書き換える
  - 33 行目の「見張りの Edit 系の判定は、このほかに別 worktree への書き込みの停止」はそのまま
  - 新しい小節「見張りに判定を足すときの決まり（I430）」: ①足す前に、公式の仕組み（`.claude/settings.json` の deny／ask・サンドボックスの設定）で表せないかを計画に書き、表せるなら公式を使う ②足すなら、実際に起きた事故の例を計画に書く（レビューの「この書き方でもすり抜けられる」だけでは足さない）③レビューで見張りへの意図的な回避の指摘が出たら、Low として一覧（`docs/reviews/backlog/`）に回すだけにし、後続のイシューにしない
  - 「新しい秘密ファイルを置くときは」の項に、リポジトリの外の秘密は `sandbox.filesystem.denyRead` に足すと書く
- `docs/runbooks/plan-writing-rules.md`: 新しい小節「見張り（`pretooluse_guard.py`）に判定を足す計画」。計画に書くこと 3 つ（公式で表せないかの検討・事故の実例・意図的な回避の指摘は一覧へ）を書き、正は danger-ops.md の小節と書く
- `docs/runbooks/workflow.md`「外部（fork）からの PR の扱い」249・253–259 行: 見張りの説明を「`gh pr checkout`・`gh co` は settings.json の deny で拒否。マージ・承認は GitHub のブランチ保護で止まる」に直す
- `docs/runbooks/worktree.md` §9 の 247–249 行: 「削除・破棄は技術的には止めない」を、「Bash の書き込みはサンドボックスが止める（外に出したコマンドは除く）。Edit／Write は見張りが止める」に直す
- `docs/runbooks/onboarding.md`「手元の準備」: `sudo apt install -y bubblewrap socat` を足す（無いと `failIfUnavailable` で Claude Code が起動しない。別の端末で打つ。`!` からは sudo のパスワードを入れられない＝2026-11-13 に確認）
- `CLAUDE.md` §3: 「Bash は公式のサンドボックスの中で動く（`.claude/settings.json` の `sandbox`・docs/runbooks/danger-ops.md）」の 1 行を足す（参照だけ。ルールは増やさない）

### 4-6. テスト
- `scripts/claude/tests/test_settings_permissions.sh`:
  - 見張りを呼ぶ PreToolUse フックの数の期待値を 4 → 3 に直す
  - サンドボックスの決まり（壊しても気づきにくく、壊れると別ワークツリーの守りが消える）を足す: `sandbox.enabled` が true・`allowUnsandboxedCommands` が false・`failIfUnavailable` が true・`filesystem.denyWrite` に `.claude/worktrees`・`filesystem.denyRead` に `~/.config/github-app`・`excludedCommands` に一般のインタプリタとシェル（`bash *`・`sh *`・`python3 *`・`python *`・`node *`・`env *`・`*` だけの行）が無い。それぞれ失敗の注入（FG）を付ける
  - deny の `Bash(gh pr checkout *)`・`Bash(gh co *)` を確かめる（消すと fork の PR の取り込みの守りが無くなり、気づきにくい）
- 消した判定の期待値を消す（逆の期待値＝「通す」には書き換えない。通すかどうかは見張りの役目ではなくなった）:
  - `scripts/claude/tests/test_pretooluse_gh_pr_guard.sh`（494 行・G33〜G35 だけを見る）を消す
  - `scripts/claude/tests/test_pretooluse_worktree_guard.sh`: Bash の書き込みの例を消し、Edit／Write の例（G01）を残す
  - `scripts/claude/tests/test_pretooluse_push_guard.sh`: 保護ブランチ・宛先の決まらない push の例を消し、force・`--no-verify`・削除・`--mirror` の例を残す
  - `scripts/claude/tests/guard_must_stop_cases.txt`: 消した判定の形（gh の fork PR・保護ブランチへの push・別のワークツリーへの Bash の書き込み）の行を消す
  - そのほか、実装で `run-all.sh` を流して落ちたテスト（候補: `test_pretooluse_guard_matrix.sh`・`test_i200_guard_narrowing.sh`・`test_i182_guard_failsafe.sh`・`test_i197_adversarial_process.sh`・`test_wt_lifecycle.sh`・`guard_bash_oracle.py`）は、落ちた期待値が消した判定のものかを 1 件ずつ確かめてから消す。残す判定の期待値が落ちたら、見張りの削除の誤りとして直す（テストを直さない）

## 5. 実装手順（ステップ）
1. **設定（未知のリスクの先）**: `.claude/settings.json` に 4-2 の `sandbox`・deny 2 行を足し、GitHub MCP のフックの登録を消す。このワークツリーのセッションの Bash にも効く見込み（S14）なので、足した直後に、この会話の Bash で作業場所の中の書き込み・`git status`・`bash scripts/claude/issue-source.sh gh-number I430` が動くことを確かめる → TC-10・M-01・M-07。動かなければ `sandbox.enabled` を false に戻して（Edit はサンドボックスの外）計画をやり直す
2. **設定のテスト**: `test_settings_permissions.sh` を 4-6 のとおり直す（ステップ 1 の後） → TC-01
3. **見張りの削除**: 4-3 の D1・D2・D3 の順に消す（ステップ 2 と並行してよい）。1 つ消すごとに関係するテストの期待値を 4-6 のとおり直す → TC-02〜TC-07・TC-08
4. **手順書**: 4-5 を直す（ステップ 3 の後。消した判定に合わせる） → TC-11・TC-12
5. **整理と push**: implement 段階の手順（/simplify・コミット・push）。push は外に出した `git push` で行う

- サービスの再起動は要らない。サンドボックスの設定は次のコマンドから効く（文書）。primary のセッションには、マージの後に develop の設定が届いた時点から効く

## 6. テスト計画
### 自動
- 決定論のゲート（`docs/tests/open/I430_auto_test.md`）: TC-01〜TC-07・TC-10〜TC-12。CI の Harness Tests（run-all）が全部を流す（AC7）
- TC-08（行数）は test-gate で Claude が流す
- 手元では、関係するテストだけを流す（全体は CI・自動テスト文書の TC の一覧）
- 失敗の注入: TC-01 の各決まりに FG を付ける（設定を壊した写しで不合格になる）

### 手動（`docs/tests/open/I430_manual_test.md`・実施者はすべて Claude・`claude -p の判定`）
- 最終の `.claude/settings.json` を読ませた新しいセッションで、S1〜S19 のうち公式に任せた判定の分を流し直す（M-01〜M-12）
- Human の行は無い

## 7. ロールバック
- 全体: PR を revert する（設定・見張り・テスト・手順書が 1 つの PR に入る）
- サンドボックスだけ止める: `.claude/settings.json` の `sandbox.enabled` を false にする（Edit ツールはサンドボックスの外なので、Bash が動かなくなっても直せる）。見張りの消した判定はサンドボックスなしでは守りが無くなるので、止めたまま使うなら PR ごと revert する
- 見張りが起動しなくなったとき: ユーザーが端末で `! git restore scripts/claude/hooks/pretooluse_guard.py`（danger-ops.md の既存の手順）
- 道具: `sudo apt remove bubblewrap socat`（その前に `sandbox` を外す。`failIfUnavailable` で起動しなくなるため）

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| R1: サンドボックスの中で今の手順のコマンドが動かなくなる（外に出す一覧の漏れ） | 外に出す理由を S6〜S13 で確かめた。implement 以降の段階はこのワークツリーでサンドボックスの中で動くので、漏れはこのイシューの中で出る。出たら計画変更記録に書いて一覧に足す（一般のインタプリタは足さない） |
| R2: `bash scripts/claude/*` を外に出すので、Claude が書いたスクリプトを外で動かせる | 脅威モデルは事故。`scripts/claude/` は PR でレビューされる。一般のインタプリタは外に出さない（TC-01）。見張りは外に出したコマンドにも今までどおり効く |
| R3: 許可した宛先（github.com）経由の持ち出し（文書の警告） | 事故の範囲では起きにくい（秘密の場所は `denyRead`・Read の deny で読めない）。TLS の中を見るプロキシは費用に見合わないので入れない |
| R4: `failIfUnavailable` で、道具の無い PC で Claude Code が起動しない | onboarding.md に入れ方を書く。起動しないほうが「守りが無いまま動く」より安全 |
| R5: 見張りの削除で、残す判定まで壊す | 残す判定のテスト（push・コンテナ・checkout・matrix・oracle・止めるべき形の一覧）を変えずに流す。期待値を消すのは消した判定の分だけ（4-6） |
| R6: manual モードでは変数入りのコマンドが確認になる（S1b） | ユーザーのセッションは auto モードで、通ることを確かめた（S16）。`claude -p` のレビュー役は Read・Grep・Glob だけを使う |
| R7: 自分のワークツリーで設定が効いたとたん、この会話の Bash が動かなくなる | ステップ 1 の直後に確かめ、動かなければ Edit で `enabled` を false に戻す（7.） |
| R8: 未実証: `failIfUnavailable` がプロジェクトの設定から効くか | 道具を外して試すと環境を壊すので試さない（文書どおり）。効かなくても、道具が無い PC ではサンドボックスなしで動くだけで、今と同じ（見張りは Edit を守る・GitHub が最後の守り） |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 公式を出発点にし、GitHub でも止まらない漏れだけを見張りに残す（2026-11-10）
- 見張りの行数を増やさない・判定を足すときの決まりを書く（2026-10-30）
- bubblewrap・socat はユーザーが入れる（2026-11-13・入れ済み）
- #436 を待たず、会話の記録から数えた回数を根拠にする（2026-11-13）
- サンドボックスの中の Bash は確認なしで通す（2026-11-13）
- 1〜4・6 の取りこぼし・コンテナの許可リストは扱わない（#444 で完了）。run-all の決まりは #445

Claude が決めた（技術的な選択と理由。設定の変更はユーザーに確かめる＝下の Danger Ops）:
- `allowUnsandboxedCommands: false`・`failIfUnavailable: true`（安全側。外での再実行は、auto モードでは判定役が通しうるので、別ワークツリーへの書き込みの事故の経路になる）
- 外に出すコマンドの一覧（4-2。S6〜S13 の結果）
- `denyWrite: [".claude/worktrees"]`・`denyRead`（App の鍵）・`allowWrite`（pre-commit の環境）・`allowedDomains` 5 つ・`strictAllowlist: true`
- fork の PR の判定を deny と GitHub に置き換える（4-1。記録上 0 件・手順で使わない・GitHub がマージを止める）。ready・edit・update-branch・承認の確認は無くす（GitHub が実害を止める）
- G01（Edit の別ワークツリー）・G24/G25（秘密ファイル）・コンテナの判定は残す（S18・4-1）
- allow・`autoMode.environment`・`Read(*)` などは変えない（4-4）
- 行数の目標 3,050 行（4-3）
- テストは消した判定の期待値を消す（「通す」に書き換えない）

一覧（`docs/reviews/backlog/`）の該当行:
- 一覧 I454 F5（`_has_write_intent` が未カバー警告を出さなくなる）: 同梱 — D1 で警告（G03）と `_has_write_intent` を消すので、指摘ごと無くなる。実装で行を消す
- 一覧 I454 F7（`rsync --remove-source-files` の移動元を別ワークツリーの停止が取りこぼす）: 同梱 — Bash の別ワークツリーはサンドボックスが場所で止めるので無くなる。実装で行を消す
- 一覧 I454 F9（`_record_writes` と `_bash_write_targets` の 2 通りの書き先の見分け）: 同梱 — D1 で `_bash_write_targets` を消す。`_record_writes` が残る場合は docstring を合わせる。実装で行を消す
- 一覧 I454 F8（`_PS_VALUE_OPT_RE` の BSD 形式）: 残す — コンテナの環境変数の表示の判定で、今回消す判定と関係しない
- 一覧 I463 F4（flock の読み方）: 残す — 同上
- 一覧 I200 F5（`_RISKY_WORDS` の境界）: 残す — 語の判定は残り、今回の範囲（公式への置き換え）と別
- 一覧 I209 F1・I221 F9・I224 F5・I220 F2/F7/F8（plan-writing-rules.md・workflow.md）: 残す — 今回直す節と別の話題
- 一覧 I223 B1〜B4・I224 F9（`FILE=-`）: 残す — bot の停止中の作業・別のイシューの測定

要件適合性・業務ロジック: 受け入れ条件の範囲を超える仕様の追加は無い（設定・見張り・手順書・テストだけ）。マルチテナント・ステータス遷移は該当なし

セキュリティ・ベストプラクティス:
- 入力の検証・認証・認可・OWASP・依存ライブラリ: アプリのコードを変えないので該当なし。bandit・npm audit の対象の変更も無い
- 機密データ: 手元の秘密（`.env`・App の鍵と鍵の控え）がサンドボックスの中から読めないことを確かめた（S4・S11）。会話の記録の集計で作った、中身を含む一時ファイルは消した
- 最小権限: 外に出すコマンドを、中で動かないものに絞った。一般のインタプリタは外に出さない
- P3/P5/P8 影響なし（DB・非同期処理・新しいインフラの費用なし。手元の道具 2 つの追加だけ）。P6 影響なし（画面なし）。P9 影響なし（個人情報を扱わない）

設計判断の明示（イシューに明記／仮定で決めた）:
- イシューに明記: サンドボックスの有効化・確認なしで通す・#436 を待たない・公式が出発点・判定を足すときの決まり・行数を減らす
- 仮定で決めた（技術）: 上の「Claude が決めた」の各項目。要件・UI の仮定は無い

Danger Ops（有無/手順/ロールバック）:
- 有（安全装置そのものの変更: `.claude/settings.json` と見張りの判定の削除）。`docs/runbooks/workflow.md`「止めて聞く条件」2 に当たるので、計画レビューの前にユーザーに確かめた（2026-11-13）: 4-2 の設定・4-3 の削除・残す判定をまとめて示し、ユーザーの答えは「BP の観点で問題ないやり方で進めて」。Claude が最小権限の点検を足し（4-2）、計画の内容のまま進める。データの削除・強制 push は無い
- ロールバックは 7.

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 最終の `.claude/settings.json`（見張りつき・見張りなしの両方）で、ワークツリーのセッションの Bash から別のワークツリー・primary への書き込みが止まる。外に出したコマンドを混ぜた形（`git push … && echo x > <別のワークツリー>` など）でも、中で動く部分が止まる（M-02・M-03） |
| V2 | 1 | 実験必須 | primary のセッションの Bash から `.claude/worktrees/` の下への書き込みが止まる（M-04） |
| V3 | 1 | 実験必須 | 外での再実行（`dangerouslyDisableSandbox`）が無効で、サンドボックスに止められたコマンドが外で動かない（M-05） |
| V4 | 2 | 読んで可 | TC-01 のサンドボックスの決まりと deny が、設定を壊した写しで不合格になる（FG）。`excludedCommands` の一般のインタプリタの判定が `bash *` だけでなく `sh *`・`python3 *`・`*` を落とす |
| V5 | 3 | 読んで可 | 4-1 の表で、消した判定（D1〜D3）ごとに代わりの仕組みがあり、止まらない漏れが書いてある。残した判定は「公式でも GitHub でも止まらない」に対応している |
| V6 | 2 | 読んで可 | 消したテストの期待値が、消した判定の分だけである（残す判定の期待値を消していない）。TC-02〜TC-07 |
| V7 | 1 | 実験必須 | `gh pr checkout <N>`・`gh co <N>` が、最終の設定の `claude -p` で拒否される（M-09） |
| V8 | 1 | 実験必須 | レビュー役（`bash scripts/claude/test-session.sh …`）・`gh`・`git fetch`・docker が、最終の設定で承認なしに動く（M-06〜M-08） |
