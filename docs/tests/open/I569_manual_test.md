# I569 手動テスト: イシューの番号の検査が 3 桁固定で、I1000 から流れ全体が止まる

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | test-gate の段階で、このイシュー（3 桁の I569）の流れの中で `bash scripts/claude/flow-stage.sh I569` と `bash scripts/claude/gate-check.sh I569` を流す | `flow-stage.sh` が exit 0 で `NEXT_STAGE: test-gate`（そのときの次の段階）を出す。`gate-check.sh` が `使い方` を出さず、`GATE_CHECK: OK` で exit 0 | Claude |  | 3 桁の番号の回帰が無いことを、本物の記録で確かめる（I1000 の側は自動テストの TC-01・TC-02） |

## 画面確認
<!-- frontend/src を変えないイシューのため対象外 -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  | 理由: frontend/src を変えないため対象外 |

結論: OK / NG
