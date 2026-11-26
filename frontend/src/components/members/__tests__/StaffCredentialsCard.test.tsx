/**
 * 運営の利用者の編集画面の「パスキーと登録用リンク」の欄（I620・TC-26）
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import StaffCredentialsCard from '../StaffCredentialsCard';
import { credentialApi } from '../../../services/member.service';
import passkeyService from '../../../services/passkey.service';

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

jest.mock('qrcode.react', () => ({ QRCodeSVG: () => null }));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'staff-1', is_staff: true } }),
}));

jest.mock('../../../services/member.service', () => ({
  MEMBERS_BASE: '/api/members/',
  ADMIN_USERS_BASE: '/api/admin/users/',
  credentialApi: jest.fn(),
}));

jest.mock('../../../services/passkey.service', () => ({
  __esModule: true,
  default: { list: jest.fn(), reauthWithPassword: jest.fn(), reauthOptions: jest.fn(), reauthWithPasskey: jest.fn() },
  createPasskeyCredential: jest.fn(),
  getPasskeyAssertion: jest.fn(),
}));

const BASE_TARGET = {
  id: 'u-1', user_id: 'alice', is_admin: false, is_superuser: false, organization_is_individual: false,
};

const mountCard = (target: typeof BASE_TARGET) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <StaffCredentialsCard target={target} />
    </QueryClientProvider>
  );
};

describe('StaffCredentialsCard', () => {
  beforeEach(() => {
    (credentialApi as jest.Mock).mockReturnValue({
      passkeys: jest.fn(), deletePasskey: jest.fn(), issueLink: jest.fn(), revokeLink: jest.fn(),
    });
    (passkeyService.list as jest.Mock).mockResolvedValue([]);
  });

  it('TC-26: 一般の利用者には［登録用リンク］［パスキー］を出し、運営の API を使う', () => {
    mountCard(BASE_TARGET);
    expect(screen.getByRole('heading', { name: 'パスキーと登録用リンク' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '登録用リンク' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'パスキー' })).toBeInTheDocument();
    expect(credentialApi).toHaveBeenCalledWith('/api/admin/users/');
  });

  it.each([
    ['運営のアカウント', { is_admin: true }],
    ['スーパーユーザー', { is_superuser: true }],
    ['本人ひとりの組織の利用者', { organization_is_individual: true }],
    ['自分', { id: 'staff-1' }],
  ])('TC-26: %s には画面から発行できない', (_, extra) => {
    mountCard({ ...BASE_TARGET, ...extra });
    expect(screen.getByText('この利用者には画面から発行できません')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '登録用リンク' })).not.toBeInTheDocument();
  });
});
