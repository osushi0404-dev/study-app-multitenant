# 診断レビュー [I636]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 影響調査 | 同型の穴が `showWarningToast` に残る。`showWarningToast` は `toast((t)=>…)` で出す blank 種別で、押す操作がなく、クリックを受け取ったままになる。警告が出ている間は F5 と同じ「下のメニューを塞ぐ」状態が再現しうる。診断メモは「呼び出しが少ない」ことを理由に残している。ただし blank 種別にも `pointerEvents: 'none'` を付ければ、セッション期限の警告は別の経路なので影響しない。付けるほうが構造的に一貫する。少なくとも、受け入れ条件 AC12 の言い直しで「警告通知は対象外」と明記してほしい。 | `ErrorToast.tsx:62-76`、診断メモ 影響調査 1 |
| Info | 対応方針 | `AuthContext.tsx:116` の `toast((t)=>…)` は blank 種別で、`success`・`error`・`loading` の指定の外にある。ボタンが押せるまま残る点は意図どおりで、コードでも確認した。ただし、blank 種別全体に指定を付ける案に切り替える場合、このボタン付き通知を巻き込む。その場合は、押す操作を持つ通知だけ個別に `pointerEvents: 'auto'` を付ける必要がある。 | `AuthContext.tsx:116` |
| Info | 対応方針 | 通知ごとの `style`（`ErrorToast.tsx:38` など）は toastOptions の style とマージされる。`pointerEvents` を上書きしている箇所はない。ただし将来 `style` を丸ごと差し替える呼び出しが入ると指定が消える。E2E（TC-30）の `elementFromPoint` の確認が、その退行の検知になる。 | `ErrorToast.tsx:36-41` |
| Info | 根本原因 | 根本原因の記述は、置き場所と重なり順の組み合わせでは全部を避けられず、通知が不要にクリックを受け取っていた、という構造で成立している。F5・F6 の再現と z-index の値も具体的で、コードの該当箇所とも整合している。 | 根本原因 |

## 影響調査の網羅性評価
- 通知の出し口が `App.tsx` の `Toaster` 1 か所であることは確認した。押す操作を持つ通知は `AuthContext.tsx:116` と `useAutoLogout.tsx:43` の 2 か所で、grep の結果と一致した。
- `toast.custom` は `toastOptions.style` を使わないため、ボタンは影響を受けない。
- `showErrorToast` の 2 経路（`toast.error` に関数を渡す形と文字列を渡す形）は、どちらも error 種別に入る。
- `showSuccessToast` も success 種別に入る。
- パネルの `ABOVE_TOASTS_Z_INDEX` の削除先は `AccessibilityProvider.tsx:12,222` と `layout.ts:15` で、使用箇所を確認した。ほかの参照は見つからなかった。
- MUI `Snackbar` は別機構として除外されている。
- 影響調査と同型確認は十分で、残るのは `showWarningToast` の扱いだけ。方針の核心は妥当で、全案の比較と推奨理由も示されている。案 B・C は却下理由が具体的。

VERDICT: OK
