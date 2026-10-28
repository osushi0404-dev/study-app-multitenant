# I204 レビュー: ハーネスのテストが頼る道具を CI と手元で同期する

- 計画書: docs/plans/open/plan_I204.md
- イシュー: docs/issues/open/I204.md（#340）
- Draft PR: #354

## 変更概要
（実装後に書く）

## 変更点
（実装後に書く）

## 影響範囲
- ハーネスだけ（計画書 3）。アプリ本体・DB の変更なし。`.github/workflows/ci.yml` は Harness Tests の 1 step だけ

## テスト結果
（test-gate の後に書く）

## 計画との差分
（実装後に書く）

## ロールバック
- PR を revert する（計画書 7）

## 自律判断の記録
- [plan] 一覧は `scripts/claude/tests/required-tools.txt`、確かめるのは `check-tools.sh`（`run-all.sh` の冒頭から呼ぶ）にした — 手元で単独で流せ、写しの一覧で単体のテストができ、CI も `--pip-specs` で同じ一覧から入れられる
- [plan] PyYAML・pre-commit も python と同じく版の下限だけを書いた — 手元の PyYAML は apt のもので、版の固定には仮想環境が要る。ぴったり揃えるのは後続のイシューで python と一緒に扱う
- [plan] `guard_bash_oracle.py` の「bash が無ければ SKIP」も消す — AC3 を全件で調べて当たった同じ形
- [plan] TC-C1 は pre-commit の `Passed` の行まで合格の条件にした — スパイクで、対象外のファイルだと `Skipped` で exit 0 になることを確かめた

- [plan-review] 判定 HIGHRISK（`.github/workflows/ci.yml` の変更）。Warning 2 件（一覧の shellcheck の確認が Skipped を見逃す・依存の監査の扱い）と Info 2 件は計画に足し、runner の挙動の Warning はステップ 1 に前倒し済みで対応不要とした — 方式・範囲・受け入れ条件は変わらないので再レビューはしない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
