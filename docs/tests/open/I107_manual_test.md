# I107 手動テスト: GitHubイシューのトラック軸ラベル分類（track:app / track:harness）導入

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `gh label list` を実行しラベル一覧を確認する | `track:app`（色 0e8a16・description に「学習アプリ開発トラック（worktree: study-app-multitenant）」）と `track:harness`（色 5319e7・description に「ハーネス改善トラック（worktree: wt-harness）」）の2行が表示される。既存10ラベルは変更されていない | Claude | | |
| 2 | `gh issue list --state open --limit 200 --label "track:app"` を実行する | #199, #196, #193, #170, #156, #155, #44, #42 の8件が表示される（承認済み分類表の app 側と一致） | Claude | | |
| 3 | `gh issue list --state open --limit 200 --label "track:harness"` を実行する | #197, #191, #190, #189, #180, #179, #177, #176, #175, #173, #172, #169, #168, #154, #153, #10, #200 の17件が表示される（承認済み分類表の harness 側と一致） | Claude | | |
| 4 | Read で `.claude/skills/issue-bootstrap/SKILL.md` の step 4 と `docs/runbooks/issue-flow.md` のラベル設定2箇所を確認する | 3箇所すべてに「種別＋トラックの2ラベル必須」「トラック判定基準（docs/runbooks/・scripts/claude/・.claude/ → track:harness、backend/・frontend/・e2e/ → track:app、両属は主目的側に単一付与・迷えばユーザー確認）」が同一粒度で記載されている | Claude | | |
| 5 | GitHub Web UI（https://github.com/osushi0404-dev/study-app-multitenant/issues）でラベル `track:harness` によるフィルタを操作する | イシュー一覧に紫色の `track:harness` ラベルが視認でき、フィルタ適用で該当17件のみに絞り込まれる | Human | | |

結論: OK / NG
