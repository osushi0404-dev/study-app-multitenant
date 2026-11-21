# I586 レビュー: 勉強用の環境と DB スペシャリスト午前Ⅱ（令和6年度秋期）の過去問の登録

## 変更概要
-

## 変更点
-

## 影響範囲
- Backend/Frontend/DB/Config:

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし / あり（理由）

## ロールバック
-

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] ブランチは既にあった `feature/I586-study-worktree-past-exams` を使い、最新の develop（853a6283）にそろえた — skill の `git checkout -b` の代わり。そろえる途中、`git merge` を後ろにつないで流したためサンドボックスの中で動き `.claude/hooks/` を書けず止まった。ユーザーに `! git reset --hard origin/develop` を流してもらった（#615 に事例のコメント）
- [plan] 手順書は `docs/runbooks/worktree.md` に §11 を足す — 新しいファイルにすると `CLAUDE.md` の参照先も増えるため
- [plan] 作業の置き場所は `.evidence/I586/exam/`（git の対象外）— サンドボックスの中から書け、`$TMPDIR` と違って消えないため
- [plan] 図の切り出しは使い捨てのコンテナの `pdftoppm` — ホストに道具が無く、スパイクで成立を確かめた
- [plan] 決定論ゲートは置かない — 手順書と記録だけの変更で、守る決まりは `.gitignore` が担うため
- [plan-review] 計画レビューの Warning 4 件を直した（解説の変更を計画変更記録に書く・画像を渡せるかをステップ 3 で先に試す〔MT-04b〕・（一部改変）の問の表を作業の記録に足し MT-10 で突き合わせる・MT-02 に選択肢と正解の数）。再レビューはしない — 方式・範囲・受け入れ条件を変えないため。Info 2 件はそのまま（MT-11 の拡大は、できなければ使いにくさの候補に入れる）
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
