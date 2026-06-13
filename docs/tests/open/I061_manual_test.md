# I061 手動テスト（axios 更新後の API 通信スモーク・CI 緑確認）

対象: axios を `^1.6.7`→`^1.17.0`（1.x 内）に更新した後の、実アプリでの API 通信動作確認。自動テストで担保できない「ブラウザ実操作での通信成功・画面遷移」を確認する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | アプリ起動後、ログイン（`auth.service.ts` 経由）を実行 | 認証 API が成功しトークン取得・ログイン後画面へ遷移できる（401/通信エラーが出ない） | Human | | ブラウザ実操作 |
| 2 | ダッシュボードを開く（`dashboard.service.ts` 経由） | overview/analytics の GET が成功し数値が表示される | Human | | axios GET 経路 |
| 3 | クイズを開始・回答送信（`quiz.service.ts` 経由） | 問題取得 GET と回答 POST が 2xx で成功し、回答後に結果/次問題画面へ遷移する | Human | | axios POST 経路・遷移先を観察 |
| 4 | 設定画面で更新操作（`Settings.tsx` 経由） | 設定の取得・更新 API が 2xx で成功し、保存後に反映される | Human | | axios 経路 |
| 5 | パスワードリセット申請（`PasswordReset.tsx` 経由） | リセット API が 2xx で成功し、完了メッセージが表示される（4xx/5xx・通信エラーが出ない） | Human | | axios 経路・完了表示を観察 |
| 6 | 共通 API クライアント（`api.ts`）のインターセプタ動作 | DevTools の Network でリクエストに認証ヘッダ（Authorization 等）が付与され、エラー時のハンドリングが従来どおり動く（axios 1.x minor 差異の影響なし） | Human | | DevTools Network でヘッダを確認 |
| 7 | PR #127 の CI 全ジョブを確認 | `Frontend Lint & Security` を含む全ジョブが pass（緑） | Claude | | `gh pr checks 127` |
| 8 | develop マージ後、PR #125（I060）の CI を再確認 | `Frontend Lint & Security` が緑に戻る | Claude | | I061 マージ後・#125 へ develop 取り込み後 |

## 補足
- No.1〜6 は axios の 1.x 内更新（semver 非破壊）の確認。挙動差が出た場合は計画書 §9 Risk の手順（呼び出し側調整、必要なら STOP→提案）に従う。
- No.7/8 は Claude が `gh` で確認可能。
