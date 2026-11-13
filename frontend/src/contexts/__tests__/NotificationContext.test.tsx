/**
 * リマインダーが設定の裏側の項目名を読む（I487・TC-18）
 */
import React from 'react';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotificationProvider, useNotifications } from '../NotificationContext';
import notificationService from '../../services/notification.service';
import dashboardService from '../../services/dashboard.service';
import { UserSettings } from '../../types/api';

jest.mock('../../services/notification.service', () => ({
  __esModule: true,
  default: {
    getPermissionStatus: jest.fn(),
    isEnabled: jest.fn(),
    getActiveRemindersCount: jest.fn(),
    scheduleStudyReminder: jest.fn(),
    cancelStudyReminder: jest.fn(),
    cancelAllReminders: jest.fn(),
    requestPermission: jest.fn(),
    testNotification: jest.fn(),
    showAchievementNotification: jest.fn(),
    showStreakNotification: jest.fn(),
  },
}));

jest.mock('../../services/dashboard.service', () => ({
  __esModule: true,
  default: { getUserSettings: jest.fn() },
}));

jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

const service = notificationService as jest.Mocked<typeof notificationService>;

const settings = (patch: Partial<UserSettings> = {}): UserSettings => ({
  daily_study_goal_minutes: 40,
  study_reminders_enabled: true,
  reminder_time: '19:00:00',
  theme_preference: 'light',
  notification_settings: {},
  ...patch,
});

const Schedule: React.FC<{ value: UserSettings }> = ({ value }) => {
  const { scheduleReminders } = useNotifications();
  return <button type="button" onClick={() => scheduleReminders(value)}>組む</button>;
};

const renderWith = async (value: UserSettings) => {
  render(
    <NotificationProvider>
      <Schedule value={value} />
    </NotificationProvider>
  );
  // 起動時の設定の読み込み（失敗させて何もしない）を済ませる
  await act(async () => { await Promise.resolve(); });
  service.scheduleStudyReminder.mockClear();
};

describe('NotificationContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    service.getPermissionStatus.mockReturnValue('granted');
    service.isEnabled.mockReturnValue(true);
    service.getActiveRemindersCount.mockReturnValue(0);
    service.scheduleStudyReminder.mockReturnValue('reminder-1');
    (dashboardService.getUserSettings as jest.Mock).mockRejectedValue(new Error('not loaded'));
  });

  it('TC-18a: reminder_time と daily_study_goal_minutes でリマインダーを組む', async () => {
    await renderWith(settings());
    await userEvent.click(screen.getByRole('button', { name: '組む' }));

    expect(service.scheduleStudyReminder).toHaveBeenCalledTimes(1);
    expect(service.scheduleStudyReminder).toHaveBeenCalledWith(
      '19:00:00',
      '今日の学習目標は40分です。一緒に頑張りましょう！'
    );
  });

  it('TC-18b: study_reminders_enabled が false なら組まない', async () => {
    await renderWith(settings({ study_reminders_enabled: false }));
    await userEvent.click(screen.getByRole('button', { name: '組む' }));

    expect(service.scheduleStudyReminder).not.toHaveBeenCalled();
  });
});
