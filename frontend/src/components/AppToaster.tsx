/**
 * 画面全体の通知の置き場所と見た目（react-hot-toast・I636）
 *
 * - 上の中央の、上のバーのすぐ下に出す（上のバーのボタンを隠さない）
 * - 押す操作を持たない通知（success・error・loading の種類）は、クリックを受け取らない表示にする。
 *   通知の下にあるボタン・メニュー・パネルを塞がない（通知の上を押すと下のものが押される）。
 *   マウスを乗せても止まらず、4 秒で消える
 * - 押す操作を持つ通知（セッションの期限の警告の［セッション延長］など）は、種類を付けない `toast((t) => …)` か
 *   `toast.custom` で出す。この指定の外なので、ボタンは押せる
 */
import { CSSProperties } from 'react';
import { Toaster } from 'react-hot-toast';
import { BELOW_APP_BAR_TOP } from '../constants/layout';

const PASS_THROUGH: CSSProperties = { pointerEvents: 'none' };

function AppToaster() {
  return (
    <Toaster
      position="top-center"
      containerStyle={{ top: BELOW_APP_BAR_TOP }}
      toastOptions={{
        duration: 4000,
        style: {
          background: '#363636',
          color: '#fff',
        },
        success: { style: PASS_THROUGH },
        error: { style: PASS_THROUGH },
        loading: { style: PASS_THROUGH },
      }}
    />
  );
}

export default AppToaster;
