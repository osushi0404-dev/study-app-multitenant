/**
 * 画面の固定の要素の置き場所（I636）
 *
 * 上のバー（Layout の AppBar・position: fixed）の高さは、MUI の Toolbar の既定で幅 600px 未満が 56px、それ以上が 64px。
 * 上のバーの下に出す浮いた表示（通知・アクセシビリティ設定のパネル）は、どの幅でも上のバーに重ならないよう、
 * 高いほう（64px）に 8px の余白を足した位置に出す。
 */
export const BELOW_APP_BAR_TOP = 72;
