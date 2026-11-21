/**
 * I609: 問題管理の作成・編集の出典の欄と、任意になった解説（TC-20〜TC-23）
 */
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import QuizManagement from '../QuizManagement';
import apiClient from '../../services/api';
import quizService from '../../services/quiz.service';

jest.mock('../../services/api');
jest.mock('../../services/quiz.service', () => ({
  __esModule: true,
  default: { updateProblem: jest.fn() },
}));
jest.mock('../../hooks/useMediaImage');
jest.mock('react-hot-toast', () => ({
  toast: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

// 作成のダイアログ（入力欄が多い MUI の画面）を開いて全部入れるので、ほかのテストと並べて流すと
// 既定の 5 秒を超えることがある（I609 の実装のときに全部を流して 1 回超えた）
jest.setTimeout(20000);

const SOURCE_PLACEHOLDER ='令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1';

const existingProblem = {
  id: 'p1',
  question_text: '既存の問題文',
  subject: '1',
  subject_name: '科目1',
  difficulty: 'easy',
  problem_type: 'single_choice',
  choices: [
    { id: 'c1', text: '正解', is_correct: true },
    { id: 'c2', text: '不正解', is_correct: false },
  ],
  explanation: '',
  source: '出典X',
  created_at: '2026-11-21T00:00:00Z',
  updated_at: '2026-11-21T00:00:00Z',
  question_images: [],
  explanation_images: [],
};

// 科目の選択欄にはラベルの結び付けが無い（名前で探せない）ので、ダイアログの中の最初の選択欄として探す
const subjectSelect = (dialog: HTMLElement) => within(dialog).getAllByRole('combobox')[0];

const precedes = (a: Element, b: Element) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

const renderPage = async (problems: unknown[] = []) => {
  (apiClient.get as jest.Mock).mockImplementation((url: string) =>
    Promise.resolve({
      data: url.startsWith('/api/organizations/subjects/') ? [{ id: 1, name: '科目1' }] : problems,
    })
  );
  render(<QuizManagement />);
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/api/problems/'));
};

const openCreateDialog = async () => {
  fireEvent.click(screen.getByRole('button', { name: '問題を作成' }));
  return screen.findByRole('dialog');
};

const fillRequired = (dialog: HTMLElement) => {
  fireEvent.change(within(dialog).getByRole('textbox', { name: '問題文' }), {
    target: { value: '新しい問題文' },
  });
  fireEvent.mouseDown(subjectSelect(dialog));
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: '科目1' }));
  ['A', 'B', 'C', 'D'].forEach((letter) => {
    fireEvent.change(within(dialog).getByRole('textbox', { name: `選択肢 ${letter}` }), {
      target: { value: `選択肢${letter}の文` },
    });
  });
  // 問題タイプの 2 つの後に、選択肢ごとの正解のラジオが並ぶ
  fireEvent.click(within(dialog).getAllByRole('radio')[2]);
};

describe('QuizManagement の出典と解説（I609）', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('TC-20: 出典の欄は問題用画像の後・科目の前にあり、ラベルと入力例が出る', async () => {
    await renderPage();
    const dialog = await openCreateDialog();

    const source = within(dialog).getByRole('textbox', { name: '出典（任意）' });
    expect(source).toHaveAttribute('placeholder', SOURCE_PLACEHOLDER);
    expect(precedes(within(dialog).getByText('問題用画像'), source)).toBe(true);
    expect(subjectSelect(dialog)).toHaveAttribute('id', 'mui-component-select-subject');
    expect(precedes(source, subjectSelect(dialog))).toBe(true);
    expect(within(dialog).getByRole('textbox', { name: '解説（任意）' })).toBeInTheDocument();
  });

  it('TC-21: 解説を空のまま作成でき、出典を送る', async () => {
    (apiClient.post as jest.Mock).mockResolvedValueOnce({ data: {} });
    await renderPage();
    const dialog = await openCreateDialog();
    fillRequired(dialog);
    fireEvent.change(within(dialog).getByRole('textbox', { name: '出典（任意）' }), {
      target: { value: '出典X' },
    });

    fireEvent.click(within(dialog).getByRole('button', { name: '作成' }));

    await waitFor(() => expect(apiClient.post).toHaveBeenCalledTimes(1));
    const [url, formData] = (apiClient.post as jest.Mock).mock.calls[0];
    expect(url).toBe('/api/problems/');
    expect(formData.get('explanation')).toBe('');
    expect(formData.get('source')).toBe('出典X');
    expect(screen.queryByText('解説は必須です')).not.toBeInTheDocument();
  });

  it('TC-22: 上限を超えた出典はエラーを出して送らない', async () => {
    await renderPage();
    const dialog = await openCreateDialog();
    fillRequired(dialog);
    fireEvent.change(within(dialog).getByRole('textbox', { name: '出典（任意）' }), {
      target: { value: 'あ'.repeat(2001) },
    });

    fireEvent.click(within(dialog).getByRole('button', { name: '作成' }));

    expect(await within(dialog).findByText('出典は2000文字以内で入力してください')).toBeInTheDocument();
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('TC-23: 編集を開くと出典が入っていて、更新で送る', async () => {
    (quizService.updateProblem as jest.Mock).mockResolvedValueOnce({});
    await renderPage([existingProblem]);
    fireEvent.click(await screen.findByRole('button', { name: '編集' }));
    const dialog = await screen.findByRole('dialog');

    expect(within(dialog).getByRole('textbox', { name: '出典（任意）' })).toHaveValue('出典X');
    fireEvent.click(within(dialog).getByRole('button', { name: '更新' }));

    await waitFor(() => expect(quizService.updateProblem).toHaveBeenCalledTimes(1));
    const [id, formData] = (quizService.updateProblem as jest.Mock).mock.calls[0];
    expect(id).toBe('p1');
    expect(formData.get('source')).toBe('出典X');
    expect(formData.get('explanation')).toBe('');
  });
});
