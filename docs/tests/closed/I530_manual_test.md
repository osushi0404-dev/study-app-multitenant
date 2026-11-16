# I530 手動テスト: マージ前の最終確認の CI 待ちをレビュー段階の wait_ci に一本化する

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | この PR の close の手順 5.5 で `bash scripts/claude/pr-base-sync.sh final`（背景の実行）の出力を読む | `wait_ci` の出力（CI が終わっていなければ `待ち（未完了: …）... <経過>s / 1980s` の行、終われば `CI_WAIT: OK`）が出て、`✅ CI 全グリーン（BLOCKED＝Approve 待ち等）。マージ依頼へ進めます` で exit 0。古い `pending... <経過>s / <N>s` の行は出ない | Claude | 未実施（close の手順 5.5 で確かめる・2026-11-16 test-gate） | test-gate の時点では PR が Draft なので final は DRAFT で止まり確かめにならない（計画書 §6）。close の手順 5.5 の実行の出力で確かめ、結果はマージ依頼の報告に書く |

結論:
