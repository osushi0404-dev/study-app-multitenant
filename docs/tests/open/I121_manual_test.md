# I121 手動テスト: frontend 依存監査の緊急是正（npm audit fix 非破壊）

対象: PR #224（feature/I121-npm-audit-fix → develop）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | push 後、`gh pr checks 224 --watch` で PR の CI 全ジョブの完了を確認する | 全ジョブ（Backend Lint & Security / Frontend Lint & Security / Backend Tests / Frontend Tests / E2E 等）が **pass** と表示される | Claude | | AC4 |
| M2 | `gh run view <run-id> --log` で「Frontend Lint & Security」ジョブの `npm audit` ステップのログを確認する | `npm audit --audit-level=critical --omit=dev` ステップが成功（exit 0）しており、critical の記載がない | Claude | | AC4 の直接証跡（ブロック原因ステップの回復） |
| M3 | （マージ後）`gh issue close 220 --comment "I121 で対応済み"` を実行し、`gh issue view 220 --json state` で確認する | #220 が **CLOSED** になる | Claude | | AC5・runbook 2 段階運用 step 3 |
| M4 | （マージ後・非ブロック）ブロックされていた PR #219（I113）の「Frontend Lint & Security」を `gh pr checks 219` で再確認（必要なら CI 再実行） | I121 マージ後の再実行で当該ジョブが pass する（CI ブロック解除の実証） | Claude | | I113 再開手順の前提確認（project メモ準拠）。fail が続く場合のみ調査 |
