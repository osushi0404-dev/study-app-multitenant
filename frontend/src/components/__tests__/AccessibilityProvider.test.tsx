/**
 * アクセシビリティ設定のボタンの置き場所（I487・TC-19）
 * 上のバーのボタンがある間は浮いた丸いボタンを出さない（画面の中身に重ねない）
 */
import React, { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AccessibilityProvider, { AccessibilityToggleButton } from '../AccessibilityProvider';

const toggleButtons = () => screen.getAllByRole('button', { name: 'アクセシビリティ設定' });

const WithHeaderButton: React.FC = () => {
  const [shown, setShown] = useState(true);
  return (
    <>
      {shown && <AccessibilityToggleButton />}
      <button type="button" onClick={() => setShown(false)}>上のバーを外す</button>
    </>
  );
};

describe('AccessibilityProvider', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('TC-19a: 上のバーのボタンが無ければ、浮いた丸いボタンを出す', () => {
    render(<AccessibilityProvider><div /></AccessibilityProvider>);

    expect(toggleButtons()).toHaveLength(1);
    expect(toggleButtons()[0]).toHaveClass('MuiFab-root');
  });

  it('TC-19b: 上のバーのボタンがあれば、浮いたボタンを出さず、押すと設定のパネルが出る', async () => {
    render(<AccessibilityProvider><WithHeaderButton /></AccessibilityProvider>);

    expect(toggleButtons()).toHaveLength(1);
    expect(toggleButtons()[0]).not.toHaveClass('MuiFab-root');

    await userEvent.click(toggleButtons()[0]);
    expect(screen.getByRole('dialog', { name: 'アクセシビリティ設定パネル' })).toBeInTheDocument();
  });

  it('TC-19c: 上のバーのボタンが外れたら、浮いた丸いボタンに戻る', async () => {
    render(<AccessibilityProvider><WithHeaderButton /></AccessibilityProvider>);

    await userEvent.click(screen.getByRole('button', { name: '上のバーを外す' }));
    const buttons = await screen.findAllByRole('button', { name: 'アクセシビリティ設定' });
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveClass('MuiFab-root');
  });
});
