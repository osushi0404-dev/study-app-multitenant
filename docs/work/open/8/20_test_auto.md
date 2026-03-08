---
github_issue_number: 8
created_at: 2026-03-08
---

# 自動テスト — Issue #8: docs/work ディレクトリ再構成

## テスト方針

アプリコードの変更なし。ファイル・ディレクトリ構造と CI の正確性を shell スクリプトで確認する。

---

## T01: ディレクトリ構造チェック

```bash
# 必須ディレクトリの存在確認
for dir in \
  docs/work/open \
  docs/work/closed \
  docs/work/templates \
  docs/indices; do
  [ -d "$dir" ] && echo "OK: $dir" || echo "NG: $dir missing"
done
```

**期待結果:** 全行 `OK`

---

## T02: テンプレファイルの存在確認

```bash
for f in \
  docs/work/templates/00_issue.md \
  docs/work/templates/10_plan.md \
  docs/work/templates/20_test_auto.md \
  docs/work/templates/21_test_manual.md \
  docs/work/templates/30_review.md \
  docs/work/templates/40_error_log.md \
  docs/work/templates/90_closeout.md; do
  [ -f "$f" ] && echo "OK: $f" || echo "NG: $f missing"
done
```

**期待結果:** 全行 `OK`

---

## T03: 索引ファイルの存在と review_seq.json の形式確認

```bash
for f in \
  docs/indices/review_seq.json \
  docs/indices/WORK_INDEX.md \
  docs/indices/REVIEW_INDEX.md; do
  [ -f "$f" ] && echo "OK: $f" || echo "NG: $f missing"
done

# review_seq.json の形式確認
python3 -c "
import json
with open('docs/indices/review_seq.json') as f:
    d = json.load(f)
assert 'next' in d and isinstance(d['next'], int), 'invalid format'
print('OK: review_seq.json format valid, next =', d['next'])
"
```

**期待結果:** 全行 `OK`

---

## T04: スクリプトの実行確認

```bash
# build_indices.py が正常実行できるか
python3 scripts/build_indices.py --dry-run 2>&1 | tail -5

# move_work_item.sh のヘルプが出るか（dry-run）
bash scripts/move_work_item.sh --help 2>&1 | head -3
```

**期待結果:** エラーなく完了

---

## T05: スキルファイルに旧パスが残っていないか

```bash
# 旧パスが SKILL.md に残っていないことを確認
OLD_PATHS="docs/plans/ docs/issues/ docs/tests/ docs/reviews/"
for old in $OLD_PATHS; do
  hits=$(grep -rl "$old" .claude/skills/ 2>/dev/null)
  if [ -z "$hits" ]; then
    echo "OK: no old path '$old' in skills"
  else
    echo "NG: old path '$old' found in: $hits"
  fi
done
```

**期待結果:** 全行 `OK`

---

## T06: CI plan-gate の新パス正規表現確認

```bash
# plan-gate.yml に新パスパターンが含まれているか
grep -q 'docs/work' .github/workflows/plan-gate.yml \
  && echo "OK: new path in plan-gate.yml" \
  || echo "NG: new path not found in plan-gate.yml"

# 旧パスが残っていないか
grep -q 'docs/plans' .github/workflows/plan-gate.yml \
  && echo "NG: old path still in plan-gate.yml" \
  || echo "OK: old path removed from plan-gate.yml"
```

**期待結果:** 全行 `OK`

---

## T07: DEPRECATED.md の存在確認

```bash
for dir in docs/issues docs/plans docs/tests docs/reviews; do
  [ -f "$dir/DEPRECATED.md" ] && echo "OK: $dir/DEPRECATED.md" || echo "NG: $dir/DEPRECATED.md missing"
done
```

**期待結果:** 全行 `OK`

---

## T08: Issue #8 自身の Work Item 構造確認

```bash
for f in \
  docs/work/open/8/00_issue.md \
  docs/work/open/8/10_plan.md \
  docs/work/open/8/20_test_auto.md \
  docs/work/open/8/21_test_manual.md; do
  [ -f "$f" ] && echo "OK: $f" || echo "NG: $f missing"
done
```

**期待結果:** 全行 `OK`

---

## テスト実施記録

| テスト | 実施日 | 結果 | 備考 |
|--------|--------|------|------|
| T01 | - | - | |
| T02 | - | - | |
| T03 | - | - | |
| T04 | - | - | |
| T05 | - | - | |
| T06 | - | - | |
| T07 | - | - | |
| T08 | - | - | |
