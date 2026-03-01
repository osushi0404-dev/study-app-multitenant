# Vibe Coding 運用フロー（安全寄り）

## ディレクトリ規約
- docs/issues/open, docs/issues/closed
- docs/plans/open, docs/plans/closed
- docs/tests/open, docs/tests/closed
- docs/reviews/open, docs/reviews/closed

## フロー（あなたの運用をそのまま型にする）
1. /issue-bootstrap → ユーザーがイシューファイル確認（OK/NG）
2. /plan I### → ユーザーが計画書確認（OK/NG）
3. /implement I### → 実装＆自動検証 → ユーザー検証（OK/NG）
4. NG の場合 /fix-loop I###（差分計画→承認→修正→再検証）
5. OK の場合 /close I###（open→closed へ移動、PR説明を整備、マージ依頼）

## ゲート
- 計画承認（OK）前にコード変更を開始しない
- Danger Ops は明示承認（danger-approved + DANGER_OK=1）なしに実行しない
- develop/main への直 push を禁止（PR経由）
