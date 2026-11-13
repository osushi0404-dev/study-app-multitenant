/**
 * 設定画面の項目名（I487・TC-17）
 * 裏側（UserSettingsSerializer）の名前で読み、同じ名前で保存する
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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

describe('Settings', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGet.mockResolvedValue({ data: SAVED });
    mockPatch.mockImplementation((_url: string, body: object) =>
      Promise.resolve({ data: { ...SAVED, ...body } })
    );
  });

  it('TC-17: 裏側の項目名で読み、同じ名前で保存する', async () => {
    render(<Settings />);

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
});
