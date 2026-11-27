/**
 * 設定画面の項目名（I487・TC-17）と、保存のときの設定のキャッシュ（TC-10d・F7）
 * 裏側（UserSettingsSerializer）の名前で読み、同じ名前で保存する
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import toast from 'react-hot-toast';
import Settings from '../Settings';
import apiClient from '../../services/api';
import SubjectService from '../../services/subjectService';

jest.mock('../../services/api');

// 「学ぶ科目」のカード（I494）の取得は、このファイルでは中身を見ない（TC-29 で置かれていることだけを見る）
jest.mock('../../services/subjectService', () => ({
  __esModule: true,
  default: {
    getUserSubjects: jest.fn(),
    getAvailableSubjects: jest.fn(),
    updateUserSubjects: jest.fn(),
  },
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

// 「パスキー」の欄（I619）の中身は PasskeysCard のテストで見る。ここでは置き場所だけを見る（TC-23）
jest.mock('../../components/settings/PasskeysCard', () => ({
  __esModule: true,
  default: () => <section data-testid="passkeys-card">パスキー</section>,
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

// 取得のキャッシュ（React Query）の中で描く。QueryClient はテストごとに新しくする。
// 「学ぶ科目」のカードが URL のハッシュを読むので Router の中で描く（I494）
const renderSettings = (queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })) =>
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Settings />
      </MemoryRouter>
    </QueryClientProvider>
  );

describe('Settings', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // CRA の Jest は各テストの前にモックの実装を消す（resetMocks）ので、ここで入れ直す
    (SubjectService.getUserSubjects as jest.Mock).mockResolvedValue([]);
    (SubjectService.getAvailableSubjects as jest.Mock).mockResolvedValue([]);
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

  it('TC-29: 「学ぶ科目」のカードが置かれている（I494）', async () => {
    renderSettings();

    expect(await screen.findByRole('heading', { name: '学ぶ科目' })).toBeInTheDocument();
    expect(screen.getByTestId('learning-subjects-card')).toBeInTheDocument();
  });

  it('I619 TC-23: 「パスキー」の欄が「学習設定」の後・「学ぶ科目」の前にある', async () => {
    renderSettings();

    const studyForm = await screen.findByRole('form', { name: '学習設定' });
    const passkeys = screen.getByTestId('passkeys-card');
    const subjects = screen.getByTestId('learning-subjects-card');
    // eslint-disable-next-line no-bitwise
    expect(studyForm.compareDocumentPosition(passkeys) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // eslint-disable-next-line no-bitwise
    expect(passkeys.compareDocumentPosition(subjects) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('TC-29b: 「学習設定」の form に名前があり、その中の「保存」だけを指せる。見出しは h1・各カード h2（I494）', async () => {
    renderSettings();

    const form = await screen.findByRole('form', { name: '学習設定' });
    expect(within(form).getByRole('button', { name: '保存' })).toBeInTheDocument();
    expect(within(form).queryByRole('button', { name: '学ぶ科目を保存' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: '設定' })).toBeInTheDocument();
    for (const name of ['アカウント情報', '学習設定', '学ぶ科目', '表示設定', '通知設定']) {
      expect(screen.getByRole('heading', { level: 2, name })).toBeInTheDocument();
    }
  });

  it('I636 TC-15: StrictMode で 2 回走る読み込みの、遅れて届いた古い応答が入力を戻さない', async () => {
    // 1 回目の取得（後片付けされる方）は解決を待たせ、2 回目はすぐ 30 で返す
    let resolveFirst: (value: { data: typeof SAVED }) => void = () => undefined;
    let settingsCalls = 0;
    mockGet.mockImplementation((url: string) => {
      if (url === '/api/settings/') {
        settingsCalls += 1;
        if (settingsCalls === 1) return new Promise((resolve) => { resolveFirst = resolve; });
        return Promise.resolve({ data: { ...SAVED, daily_study_goal_minutes: 30 } });
      }
      return Promise.resolve({ data: SAVED });
    });
    render(
      <React.StrictMode>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <MemoryRouter>
            <Settings />
          </MemoryRouter>
        </QueryClientProvider>
      </React.StrictMode>
    );
    const goal = await screen.findByLabelText('1日の学習目標時間（分）');
    expect(goal).toHaveValue(30);
    expect(settingsCalls).toBe(2);
    userEvent.clear(goal);
    userEvent.type(goal, '45');
    expect(goal).toHaveValue(45);

    resolveFirst({ data: { ...SAVED, daily_study_goal_minutes: 50 } });
    // 古い応答が届いても、入力した 45 のまま（50 に戻らない）
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.getByLabelText('1日の学習目標時間（分）')).toHaveValue(45);
  });
});
