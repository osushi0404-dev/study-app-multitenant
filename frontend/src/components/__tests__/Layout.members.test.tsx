/**
 * メニューの「メンバー管理」の出し分け（I620・TC-20）
 * 人を迎えられる組織の管理者だけに出す（本人ひとりの組織の管理者・一般の利用者には出さない）
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Layout from '../Layout';

let mockUser: Record<string, unknown> = {};
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockUser, logout: jest.fn() }),
}));

jest.mock('../../contexts/ThemeContext', () => ({
  useTheme: () => ({ darkMode: false, toggleDarkMode: jest.fn() }),
}));

jest.mock('../AccessibilityProvider', () => ({
  AccessibilityToggleButton: () => null,
}));

const mountLayout = (user: Record<string, unknown>) => {
  mockUser = user;
  render(
    <MemoryRouter>
      <Layout />
    </MemoryRouter>
  );
};

describe('Layout のメンバー管理', () => {
  it('TC-20: 招待で人を迎えられる組織の管理者には出す（科目管理の後）', () => {
    mountLayout({ id: 'a', role: 'admin', organization_is_individual: false });
    const labels = screen.getAllByText(/管理$/).map((element) => element.textContent);
    expect(labels).toEqual(expect.arrayContaining(['科目管理', 'メンバー管理']));
    expect(labels.indexOf('メンバー管理')).toBe(labels.indexOf('科目管理') + 1);
  });

  it('TC-20: 本人ひとりの組織の管理者には出さない', () => {
    mountLayout({ id: 'b', role: 'admin', organization_is_individual: true });
    expect(screen.queryByText('メンバー管理')).not.toBeInTheDocument();
    expect(screen.getAllByText('科目管理').length).toBeGreaterThan(0);
  });

  it('TC-20: 一般の利用者には出さない', () => {
    mountLayout({ id: 'c', role: 'user', organization_is_individual: false });
    expect(screen.queryByText('メンバー管理')).not.toBeInTheDocument();
  });
});
