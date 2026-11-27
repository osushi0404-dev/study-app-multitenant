# イシューの扱い（番号・置き場所・起票・ラベル）

段階の流れ（計画 → 実装 → レビュー → テスト → 振り返り → クローズ）の正は `docs/runbooks/workflow.md`「フロー」と各段階のスキル。ここはイシューそのものの扱いだけを決める。

## イシューの番号と置き場所（I221）
- **新しいイシューは GitHub のイシューが唯一の正**。手元の `docs/issues/open/` にファイルを作らない（起票・grill-me は GitHub の本文を読み書きする）。番号は GitHub が振り、「I＋GitHub の番号」（#427 → I427）で呼ぶ。記録のファイル名・ブランチ名・ゲートのスクリプトの I### の形はそのまま使う。GitHub はプルリクエストと番号を共有するので I 番号は飛ぶ。どのワークツリーから起票しても番号はぶつからない
- **見分け方は `scripts/claude/issue-source.sh` の 1 か所**（読む・写す・番号を出すのもこのスクリプト）: 手元にイシューファイルがあればそれを使う。無く、I427 以上で、GitHub の題名が `I###: ` で始まらないものが新しいイシュー。I427 未満でファイルが無いときは GitHub を読まずに止まる（別のワークツリーにしか無い I196 で、GitHub の #196〔別のイシュー〕を黙って読まないため。#426 以下はすべて今までの番号）。PR の番号も止める
- **今までのイシュー（I426 以下・手元にファイルがあるもの）は今の流れのまま**。ファイルは起票したワークツリーで扱い、消さない（別のワークツリーで `/plan-issue` すると `issue-source.sh` が「ファイルが見つからない」で止める）
- **本文の写し**: `/plan-issue` が計画を始めるときに GitHub の本文を `docs/issues/open/I###.md` に 1 回だけ写し、最初のコミットにする（`issue-source.sh snapshot`）。写しは同期しない。計画を始めた後の範囲・受け入れ条件の変更は、計画書の計画変更記録と写しに書き、GitHub の本文には戻さない（`docs/runbooks/workflow.md`「GitHub への書き込みの時点」）。GitHub の本文は「起票と grill-me で決めた依頼」の正、写しと計画書は「この PR で何をしたか」の正。写しがあるので、計画の後の段階（計画レビュー・review-gate・敵対的レビュー・close の移動）は今までのイシューファイルと同じに動く。`issue-source.sh` の `body` と写しには、本文の後ろに GitHub のコメントの節が付く（立場が OWNER・MEMBER・COLLABORATOR・CONTRIBUTOR の人だけ中身を出す・I639）。`/grill-me` が GitHub に書き戻す下書きは、本文だけを出す `issue-source.sh raw-body` で作る
- **本文の変更の履歴**: GitHub が本文の全版を残す（`gh api graphql` で `issue(number:N){userContentEdits{nodes{editedAt diff}}}`）。起票〜grill-me の変更はここで追える
- **既存イシューに同梱するとき**: 本文は直さず `gh issue comment <番号> --body-file <ファイル>` でコメントする（新しいイシューでも今までのイシューでも同じ。計画を始めた後のイシューは写しも直さない）。新しいイシューのコメントは、次の `/grill-me`・`/plan-issue` の入力に入る（`issue-source.sh body`・`snapshot`）
- **閉じ方**: イシューは、PR の本文の `Closes #N`（close 段階が書く）でマージのときに GitHub が閉じる。closing keyword は既定ブランチ（今は develop）宛ての PR でだけ効くので、既定ブランチを変えるとイシューが黙って閉じなくなる

## 起票

起票は `issue-bootstrap` スキル（`.claude/skills/issue-bootstrap/SKILL.md`）の手順で行う（手順の正はスキル）。ユーザーが `/issue-bootstrap` を打ったときと、会話の中で別イシューにすると決まったとき（Claude が呼ぶ・確認の要否は `docs/runbooks/workflow.md`「Claude が会話の中で起票するとき」）。

- **分ける単位**: 改善案・導入候補が 2 つ以上あるときは 1 イシューにまとめず、触る場所・失敗したときの影響・戻し方がそろう単位で分けて起票する。「互いに関係している」はまとめる理由にしない（どちらを先に入れても安全なら分ける）
- **既存イシューへの同梱の前に**: 指摘の前提が本当かをコードで確かめ、同じ穴がほかにもないかを grep で測る。同梱は同じファイル・同じ原因・同じ直し方のときだけにし、原因・直す場所が違うもの、複数の手順に広がって毎回踏むものは別イシューにする
- **一覧に回す前に**: 軽い指摘の一覧（`docs/reviews/backlog/`）に回る重さ・再現の指摘でも、対応中のイシューの目的そのものを崩すものは一覧に回さず、その PR で直す（計画を直して plan-review から）

**ラベル（2 軸・両方必須）**:
- **種別ラベル**: Bug → `bug` / Feature → `enhancement` / Documentation → `documentation` / Refactoring → `refactoring`
- **トラックラベル**（`track:app` / `track:harness` のどちらか 1 つを必ず付ける）:
  - 変更対象が `docs/runbooks/`・`scripts/claude/`・`.claude/`（skills/hooks/settings）・`.github/`・レビュー/ゲート/テンプレートの仕組み → `track:harness`
  - 変更対象が `backend/`・`frontend/`・`e2e/` 等のアプリ機能・アプリのテスト → `track:app`
  - 両方にまたがる場合は主目的の側に**1 つだけ**付ける（両方は付けない）。迷ったら Claude が決め、起票の報告に理由を 1 行書く（ラベルはいつでも付け直せる）
