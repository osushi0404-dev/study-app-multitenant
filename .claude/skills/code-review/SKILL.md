---
name: code-review
description: "/test の前に実行。CI 完了を待機し、実装が受け入れ条件・セキュリティ・ベストプラクティスを満たしているかレビューする。Blocker があれば差し戻す。"
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Bash
---

# /code-review

```bash
bash scripts/claude/code-review.sh "$ARGUMENTS"
```
