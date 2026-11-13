# 診断レビュー [I487]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 根本原因は成立している。`invalidateQueries` は古いと印を付けるだけで、取り直しが終わるまで旧値を `isSuccess` として返す。`useDailyStudyGoal` は `isSuccess` だけを見ている（`useDailyStudyGoal.ts:32`）。PATCH 応答が手元にあるのにキャッシュへ入れていない。コードを読んで確認した。 | `Settings.tsx:193`、`useDailyStudyGoal.ts:30-34` |
| Info | 対応方針 | 案 A は妥当。`updateUserSettings` は `Promise<UserSettings>` を返し、キャッシュの型 `UserSettings` と一致する。キーは `userSettingsKey(user.id)` で揃う。<br>実装時の注意が 2 点ある。<br>① 現状は `scheduleReminders` が `invalidateQueries` より前にあり、これが例外を投げるとキャッシュ更新に届かない。`setQueryData` は PATCH 成功の直後（`scheduleReminders` の前）に置くとよい。<br>② 現状の `invalidateQueries` はルートキーで全ユーザー分を対象にしている。`setQueryData` は userId 単位になるが、問題はない。`user` が無いときに `invalidateQueries` へ倒す案どおりでよい。 | `Settings.tsx:184-193` |
| Info | 対応方針 | 案 C を見送る根拠は妥当。ただし、別タブや別端末で目標を変えた場合の古いキャッシュ（staleTime 既定 0 で、マウント時の取り直し中は旧値が success として返る）は、残るリスクとして記録に明記すること。今回の再現手順は案 A で消える。 | 案 C の短所の記述 |
| Info | 影響調査 | TC-10d の書き換え方針は妥当。「保存後、取り直しを待たずにキャッシュが保存値になっている」ことを検証する。現行テストは `isInvalidated` を見ているので、`getQueryData` の確認に変えること。 | `Settings.test.tsx:95-103` |

## 影響調査の網羅性評価
- **同型バグ**: 設定キャッシュの利用箇所は grep で網羅されている。使っているのは `useDailyStudyGoal` だけで、`NotificationContext` と `Settings` の初期読み込みは `getUserSettings` を直接呼ぶ。実コードで再確認し、診断メモと一致した。
- **波及**: overview と科目一覧のキャッシュは、この画面から書き換えないので影響しない。
- **残る穴**: 他タブや他端末起因の古いキャッシュは案 C の領域で、今回は意図的に対象外としている。この扱いはメモ内で説明されており、許容できる。
- 重大な漏れはない。

VERDICT: OK
