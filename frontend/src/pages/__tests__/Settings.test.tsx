/**
 * 設定画面の項目名（I487・TC-17）と、保存のときの設定のキャッシュ（TC-10d・F7）
 * 裏側（UserSettingsSerializer）の名前で読み、同じ名前で保存する
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import toast from 'react-hot-toast';
import Settings from '../Settings';
import apiClient from '../../services/api';

jest.mock('../../services/api');

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1', email: 'u@example.com', role: 'user' } }),
}));

jest.mock('../../contexts/ThemeContext', () => ({
  useTheme: () => ({ darkMode: false, toggleDarkMode: jest.fn() }),
}));

jest.mock('../../contexts/NotificationContext', () => ({
  useNotifications: () => ({
    permission: 'default',
    isEnabled: false,
    requestPermission: jest.fn(),
    scheduleReminders: jest.fn(),
    testNotification: jest.fn(),
    activeRemindersCount: 0,
  }),
}));

const mockGet = apiClient.get as jest.Mock;
const mockPatch = apiClient.patch as jest.Mock;

const SAVED = {
  daily_study_goal_minutes: 45,
  study_reminders_enabled: false,
  reminder_time: '19:00:00',
  theme_preference: 'dark',
  notification_settings: { email: false, push: true, achievements: true, reminders: false },
};

// 取得のキャッシュ（React Query）の中で描く。QueryClient はテストごとに新しくする
const renderSettings = (queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })) =>
  render(
    <QueryClientProvider client={queryClient}>
      <Settings />
    </QueryClientProvider>
  );

describe('Settings', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGet.mockResolvedValue({ data: SAVED });
    mockPatch.mockImplementation((_url: string, body: object) =>
      Promise.resolve({ data: { ...SAVED, ...body } })
    );
  });

  it('TC-17: 裏側の項目名で読み、同じ名前で保存する', async () => {
    renderSettings();

    const goal = await screen.findByLabelText('1日の学習目標時間（分）');
    expect(goal).toHaveValue(45);

    await userEvent.clear(goal);
    await userEvent.type(goal, '50');
    await userEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledTimes(1));
    const [url, body] = mockPatch.mock.calls[0];
    expect(url).toBe('/api/settings/');
    expect(body).toEqual({
      daily_study_goal_minutes: 50,
      study_reminders_enabled: false,
      reminder_time: '19:00',
      theme_preference: 'dark',
      notification_settings: { email: false, push: true, achievements: true, reminders: false },
    });
    expect(body).not.toHaveProperty('daily_study_goal');
    expect(body).not.toHaveProperty('study_reminder_enabled');
    expect(body).not.toHaveProperty('theme');
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('設定を保存しました'));
  });

  it('TC-10d: 保存すると、ダッシュボードが持つ設定のキャッシュを保存した値にする（古い目標で判定させない・F7）', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // ダッシュボードで読んだ古い設定（目標 30 分）がキャッシュにある
    queryClient.setQueryData(['user-settings', 'user-1'], { ...SAVED, daily_study_goal_minutes: 30 });
    renderSettings(queryClient);

    const goal = await screen.findByLabelText('1日の学習目標時間（分）');
    await userEvent.clear(goal);
    await userEvent.type(goal, '60');
    await userEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('設定を保存しました'));

    // 取り直しを待たずに、キャッシュは保存の応答（60 分）になっている
    const cached = queryClient.getQueryData<{ daily_study_goal_minutes: number }>(['user-settings', 'user-1']);
    expect(cached?.daily_study_goal_minutes).toBe(60);
  });

  it('TC-10d（競合）: 保存の前に始まった設定の取得が後から古い値を返しても、キャッシュは保存した値のまま（F10）', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const key = ['user-settings', 'user-1'];
    queryClient.setQueryData(key, { ...SAVED, daily_study_goal_minutes: 30 });
    // ダッシュボードで始まった、まだ終わっていない設定の取得
    let resolveOld: (value: unknown) => void = () => {};
    const pendingFetch = queryClient
      .fetchQuery({ queryKey: key, queryFn: () => new Promise((resolve) => { resolveOld = resolve; }) })
      .catch(() => undefined);
    renderSettings(queryClient);

    const goal = await screen.findByLabelText('1日の学習目標時間（分）');
    await userEvent.clear(goal);
    await userEvent.type(goal, '60');
    await userEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('設定を保存しました'));

    // 古い取得の応答（30 分）が保存の後に届く
    resolveOld({ ...SAVED, daily_study_goal_minutes: 30 });
    await pendingFetch;

    const cached = queryClient.getQueryData<{ daily_study_goal_minutes: number }>(key);
    expect(cached?.daily_study_goal_minutes).toBe(60);
  });
});
