# 敵対的レビュー [I151] ── 2026-10-15〜16（fix-loop 後の再実施）

- 起動条件: `/code-review I151`（`docs/reviews/I151_code_review_20261015_1826.md`）が `RISK: YES` / `FINAL_VERDICT: OK` → `ADVERSARIAL_STAGE: REQUIRED`
- 既知 findings: 前回ステージ `I151_adversarial_review_20261014_1736.md`（上限到達・HIGH）の全 findings を合算して各エージェントへ渡した
- 周回: 3 周・サブエージェント 12 体（各周 4 体＝固定 3 観点＋動的 1 観点「記録と実体の整合」）
- 結果: **第 3 周で新規 Critical / High 0 件 → ステージ通過**
- High の findings は、メインセッションが自分で再実証してから扱った

## 周回サマリ

| 周 | 観点（エージェント数） | NEW_CRITICAL | NEW_HIGH | 是正コミット |
|---|---|---|---|---|
| 1 | ロジック回避 / false-green / 要件網羅 / 記録整合（4） | 0 | 4 | 5e2f74e ＋ GitHub #267・#272 本文同期 |
| 2 | 同上（4） | 0 | 1 | 94271e4 ＋ GitHub #267 本文同期 |
| 3 | 同上（4） | 0 | 0 | （Medium / Low の記録是正のみ。本記録と同じコミット） |

**依存更新が原因の抜け道は 3 周とも見つからなかった。** ロジック回避の観点は 3 周とも反証に失敗した。実測した範囲は次のとおり。旧依存（Django 4.2.30）と新依存（5.2.17）での HTTP 全経路 6,857 リクエストの比較（差分 0）。ModelSerializer の生成結果。スロットル・ratelimit・CORS・JWT。admin の全経路と書き込み。クッキー・ヘッダ。django-redis で旧版が書いた値を新版で読み出し。celery の全 14 タスク。ORM とタイムゾーン。パスワードハッシュ・署名・メールの新旧互換。アップロード処理。本番ターゲット（collectstatic・gunicorn）。I159 由来の lockfile。High はすべて、テスト判定式と記録の不備だった。

## 第 1 周 findings（High 4）と対応

| # | 重大度 | 指摘 | 再実証 | 対応 |
|---|---|---|---|---|
| 1-1 | High | AC-12 / 13 / 14 の証跡が、R6（openai 3.31.0）と I159 の取り込みより前の run だった（E2E の根拠 run 32651105381 は 2026-08-23・openai 1.3.0）。R6 を push した直後の CI 失敗（run 38564774555・npm audit）も記録されていなかった | `gh run list` で headSha と conclusion を確認 | 最新の run（head 5c31947・全 6 success・E2E 7 passed）で TC-AUTO-12 / 13 / 14 を取り直した。CI 失敗の経緯を記録。TC-AUTO-13 に判定 0（job の後に docs 以外の変更が無い）を追加 |
| 1-2 | High | イシュー本文（I151.md / #267）に R6 の反映が無かった（確定セット・AC・コミット数・リスク） | `grep openai` で 0 件を確認 | I151.md に反映し、#267 に同期 |
| 1-3 | High | 実装レビュー記録 `I151_review.md` が古いままだった（3 ファイル・7 モジュール・1 コミット・openai が無い・未記入） | 該当行を確認 | 全項目を実体に合わせて更新 |
| 1-4 | High | 攻撃シナリオ #5 が、未マージの I142 の `token_blacklist` を根拠に「担保済み」としていた。実体は、ログアウトが常に 400 を返し、refresh を再利用できる（既存の不備） | `git grep token_blacklist HEAD` で 0 件。`accounts/views.py:419-429` を確認。I142 の PR #256 が OPEN であることを確認 | #5 / #6 を訂正し、サマリーから外して「既存・範囲外」とした |
| — | Medium | TC-16 の件数 regex の数え漏れ・TC-15 ゲートが記録の鮮度を見ない・TC-13 ローカル手順で backend を作り直さない・R6 コミットを単独で取り消せない・#272 未同期・レート制限の失敗時の向き（実際はフェイルクローズ） | — | numstat 化・判定 3 の追加・手順 L1b / L1c / L0b の追加・§8 に追記・#272 の同期・申し送りの訂正 |
| — | Low | 件数・行番号のずれ・I153 が openai 1.x 前提のまま・推移的依存の変化の記録不足・PR 本文に R6 / I159 の記載が無い・DRF 3.16 以降で大きな JSON が HTML 400 になる・celery の freeze を判定していない | — | 件数・行番号は是正。それ以外は下の「未是正」に残す |

## 第 2 周 findings（High 1）と対応

| # | 重大度 | 指摘 | 再実証 | 対応 |
|---|---|---|---|---|
| 2-1 | High | TC-AUTO-13 がコミットを `<run_id>` から、ログを `--job <job_id>` から取っていた。`gh run view` は `--job` があると run_id を無視するため、新しい run_id と旧 job_id を組み合わせると、旧 run（openai 1.3.0）のログで判定 0〜2 がすべて合格した | `gh run view 38711268663 --log --job 97222730997` の出力に `openai==1.3.0` と `7 passed (15.4s)` があることをメインセッションで確認 | ログもコミットも同じ job_id から取る形に変更（`gh api .../actions/jobs/<id> -q .head_sha`）。判定 0b（未コミットの変更が無い）と 0c（HEAD が PR の head と一致）を追加 |
| — | Medium | TC-15 判定 3 が宣言の写しと一致するだけ・TC-16 が requirements-dev を触るほかのコミットを見ない・判定 0 の比較先のずれ・フェイルオープンの旧前提が 4 か所に残っていた・C7 / §11 が I142 前提・#5 の申し送りが不完全（ローテーション後の refresh）・nginx の背後で IP キーが全員共通になる | フェイルクローズは `django_ratelimit/core.py:249-252` で確認。I142 の `BLACKLIST_AFTER_ROTATION=False` は `git grep` で確認 | TC-15 判定 4（anyio / kombu）・TC-16 判定 11 を追加。全箇所を訂正。申し送りを (a)(b) に分割。残余リスクに追加 |
| — | Low | run 失敗ジョブの内訳の誤記・R6 行が「系列変更を伴わない」のまま・§8 の件数 7→9・review.md の §7 と結果節・manual No.9 / 10 が未更新・冒頭注記・I151.md の危険操作とロールバック | — | すべて是正 |

## 第 3 周 findings（Critical / High 0）

ロジック回避と要件網羅の 2 観点は新規の Critical / High を出さなかった。false-green と記録整合の 2 観点も同じく 0 件で、Medium / Low だけだった。

| 重大度 | 指摘 | 対応 |
|---|---|---|
| Medium | 新しく足した判定（TC-13 の 0b / 0c・TC-15 の 3 / 4・TC-16 の 11）の実施記録が無い | 実施記録を追加。TC-13 は push 後の job 116375327027（head 94271e4）で、判定 0〜2 がすべて exit 0。TC-16 判定 11 は一時リポジトリで false-green を検証 |
| Medium | #5 の 2 系統への分割が、表の行・訂正注記・サマリーに波及していなかった | 是正 |
| Medium | 手動 No.11 に、nginx の背後での但し書きと R6 後の再実施の記録が無い | 但し書きを追加 |
| Medium | 残余リスク (b) の是正先が誤っていた。FE は存在しない `/api/auth/token/refresh/` を呼んでいる（実ルートは `/api/auth/refresh/`） | grep で確認し、是正範囲の補足を追記 |
| Medium | #4 の根拠が TC-AUTO-15 / ホスト venv の実測だった | 第 3 周の実コンテナでの実測（allowed 60 / denied 2）に差し替え |
| Medium | 手元の backend イメージが別ブランチの Django 4.2.30 に戻っていた | ユーザー指示で作り直した（下記）。manual_test の前提に注意書きを追加 |
| Medium（未是正） | TC-16 判定 11 は、1 段目の `fix(I151)` にプラグインや `--extra-index-url` を同梱すると見逃す（1 段目の中身を照合する判定が無い。既知 Low「TC-16 が 1 段目を照合しない」の延長）。実リポジトリの 4877e18 は `requirements-dev` が 1 行置き換えだけで、実害は無い | /retro へ申し送り |
| Medium（未是正） | TC-13 が job の attempt・conclusion・名前を縛っていない。re-run で通った attempt の job を選ぶと、attempt をまたいだ flaky を見逃す | /retro へ申し送り（現 head の job は attempt 1・success） |
| Low | フェイルオープン前提の残り 2 文・#4 の TC の取り違え・review.md の TC-03 旧判定式・TC-13 の書きぶりの衝突・開発環境の dev proxy で DRF スロットルも全員共通・nginx の段数を確かめられない・Redis 障害時に sessions などのキャッシュは 500 | 是正、または残余リスクへ追記 |
| Low（未是正） | TC-16 判定 11 の件名照合が部分一致・TC-13 判定 1 が件数を固定していない・TC-15 判定 4 の主張が過大（kombu はベースラインと同じ値）・手動 No.4 が R6 後の freeze 差し替えに触れていない | /retro へ申し送り |

## 環境の作り直し（2026-10-16・ユーザー指示）

手元の `backend` イメージは、別ブランチ（develop）で作り直されて Django 4.2.30 に戻っていた。そこで `docker compose build backend celery celery-beat` と `docker compose up -d --wait` を実行した（6 サービス healthy）。作り直し後の確認結果は次のとおり。
- backend・celery の両コンテナで、全 8 固定値と anyio 4.15.1 が一致した
- backend の freeze は記録と完全に一致した
- TC-AUTO-03 `94 passed`・TC-AUTO-01 で脆弱性 0 件・TC-AUTO-17 は合格

## 別イシュー候補（I151 の範囲外・未起票。前回ステージの 1〜6 に加えて）

7. ログアウト不備 (b): FE の refresh の URL 誤り（`/api/auth/token/refresh/`）の修正と、`BLACKLIST_AFTER_ROTATION=True` への復帰
8. `@ratelimit(key='ip')` と DRF の anon スロットルが、プロキシの背後で全員共通になる（`RATELIMIT_IP_META_KEY` と dev proxy の `xfwd`、本番構成の確認）
9. Redis 障害時の設計（@ratelimit の 403・sessions などの 500・DRF スロットルのフェイルオープン）
10. I153 を openai 3.x 前提へ更新
11. TC 判定式の残りの穴（TC-16 で 1 段目の中身を照合・TC-13 で attempt と件数を固定）を、テンプレートと review 観点へ反映（harness）

VERDICT: OK
