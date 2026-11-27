/**
 * 画面の固定の要素の置き場所と重なり順（I636）
 *
 * 上のバー（Layout の AppBar・position: fixed）の高さは、MUI の Toolbar の既定で幅 600px 未満が 56px、それ以上が 64px。
 * 上のバーの下に出す浮いた表示（通知・アクセシビリティ設定のパネル）は、どの幅でも上のバーに重ならないよう、
 * 高いほう（64px）に 8px の余白を足した位置に出す。
 */
export const BELOW_APP_BAR_TOP = 72;

/**
 * 通知（react-hot-toast の z-index: 9999）より手前に出す重なり順。
 * アクセシビリティ設定のパネルは通知と同じ高さに出るので、通知に操作を塞がれないよう手前にする。
 * 通知そのものの重なり順は下げない（MUI の Dialog〔1300〕より手前のままにし、ダイアログの中の通知を隠さない）
 */
export const ABOVE_TOASTS_Z_INDEX = 10000;
