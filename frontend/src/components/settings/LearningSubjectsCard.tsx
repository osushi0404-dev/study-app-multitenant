/**
 * 設定画面の「学ぶ科目」のカード（I494）
 *
 * - 自組織の科目をチェックで選び、「学ぶ科目を保存」で丸ごと置き換える（最低 1 つ）
 * - 取得・保存は React Query。チェックは保存するまでこの画面の中だけの状態
 * - 保存の失敗はカードの中に残る表示で伝え、チェックは消さない（C7）
 * - /settings#learning-subjects で開いたら、カードまで送り見出しにフォーカスを移す（ダッシュボードの導線）
 */
import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  FormGroup,
  FormHelperText,
  Typography,
} from '@mui/material';
import { Save } from '@mui/icons-material';

import { useAuth } from '../../contexts/AuthContext';
import { useAvailableSubjects } from '../../hooks/useAvailableSubjects';
import { isBadRequest, useSaveUserSubjects, useUserSubjects } from '../../hooks/useUserSubjects';
import { extractApiErrorMessage } from '../../utils/apiError';
import SubjectsRetryRow from '../SubjectsRetryRow';
import { LEARNING_SUBJECTS_ANCHOR } from '../../constants/routes';

// チェックボックスのまとまりに、見える見出し・説明・注意を結び付ける id（画面読み上げで何の選択かが分かるように）
const HEADING_ID = 'learning-subjects-heading';
const DESCRIPTION_ID = 'learning-subjects-description';
const ERROR_ID = 'learning-subjects-error';
const SAVE_FAILED = '学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください';

/** 400 なら裏側の理由、それ以外は決まった文言 */
const saveErrorText = (error: unknown): string =>
  isBadRequest(error) ? extractApiErrorMessage(error.response?.data, SAVE_FAILED) : SAVE_FAILED;

const sameIds = (a: number[], b: number[]) =>
  a.length === b.length && a.every((id) => b.includes(id));

const LearningSubjectsCard = () => {
  const { user } = useAuth();
  const userId = user?.id ?? '';
  const { hash } = useLocation();
  const available = useAvailableSubjects(userId);
  const selected = useUserSubjects(userId);
  const save = useSaveUserSubjects(userId);
  // null はまだ触っていない（保存済みの選択をそのまま出す）
  const [checked, setChecked] = useState<number[] | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const scrolled = useRef(false);

  const subjects = available.status === 'success' ? available.data : [];
  const ready = available.status === 'success' && selected.state.status === 'success';

  // 保存済みの選択（組織の科目にあるものだけ・組織の科目の並び）
  const savedSet = new Set(selected.state.status === 'success' ? selected.state.subjects.map((s) => s.id) : []);
  const savedIds = subjects.filter((s) => savedSet.has(s.id)).map((s) => s.id);
  // 触った後の選択も、いまの組織の科目の一覧と毎回突き合わせる
  // （保存の 400 の後に一覧を取り直して消えた科目を、見えないまま送り続けない・F1）
  const availableSet = new Set(subjects.map((s) => s.id));
  const currentIds = (checked ?? savedIds).filter((id) => availableSet.has(id));
  const isEmpty = currentIds.length === 0;
  // 赤い注意は、一度触ってから 0 件にしたときだけ出す（触る前は説明文だけ。保存できない決まりは同じ）
  const showEmptyError = checked !== null && isEmpty;
  const canSave = ready && !isEmpty && !sameIds(currentIds, savedIds) && !save.isPending;

  useEffect(() => {
    if (!ready || scrolled.current || hash !== `#${LEARNING_SUBJECTS_ANCHOR}`) return;
    scrolled.current = true;
    headingRef.current?.scrollIntoView?.({ block: 'start' });
    // 送り直さない（scrollIntoView の余白を保つ）
    headingRef.current?.focus({ preventScroll: true });
  }, [ready, hash]);

  const toggle = (id: number) => {
    setSaveError(null);
    setChecked(currentIds.includes(id) ? currentIds.filter((x) => x !== id) : [...currentIds, id]);
  };

  const handleSave = () => {
    setSaveError(null);
    save.mutate(currentIds, {
      onSuccess: () => {
        setChecked(null);
        toast.success('学ぶ科目を保存しました');
      },
      onError: (error) => setSaveError(saveErrorText(error)),
    });
  };

  const retry = () => {
    if (available.status === 'error') available.retry();
    if (selected.state.status === 'error') selected.retry();
  };

  const renderBody = () => {
    if (available.status === 'error' || selected.state.status === 'error') {
      return <SubjectsRetryRow onRetry={retry} />;
    }
    if (!ready) {
      return (
        <Box display="flex" justifyContent="center" py={2}>
          <CircularProgress size={24} aria-label="学ぶ科目を読み込み中" />
        </Box>
      );
    }
    if (subjects.length === 0) {
      return (
        <Alert severity="info">
          この組織には選べる科目がありません。組織の管理者に科目の登録を依頼してください
        </Alert>
      );
    }
    return (
      <>
        <FormGroup
          role="group"
          aria-labelledby={HEADING_ID}
          aria-describedby={showEmptyError ? `${DESCRIPTION_ID} ${ERROR_ID}` : DESCRIPTION_ID}
        >
          {subjects.map((subject) => (
            <Box key={subject.id} sx={{ mb: 1 }}>
              <FormControlLabel
                control={
                  <Checkbox checked={currentIds.includes(subject.id)} onChange={() => toggle(subject.id)} />
                }
                label={subject.name}
              />
              {subject.description && (
                <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
                  {subject.description}
                </Typography>
              )}
            </Box>
          ))}
        </FormGroup>
        {showEmptyError && (
          <FormHelperText id={ERROR_ID} error>
            科目を最低1つ選択してください
          </FormHelperText>
        )}
        {saveError && (
          <Alert severity="error" role="alert" sx={{ mt: 2 }}>
            {saveError}
          </Alert>
        )}
        <Button
          variant="contained"
          startIcon={<Save />}
          onClick={handleSave}
          disabled={!canSave}
          sx={{ mt: 2 }}
        >
          {save.isPending ? <CircularProgress size={20} aria-label="保存中" /> : '学ぶ科目を保存'}
        </Button>
      </>
    );
  };

  return (
    <Card id={LEARNING_SUBJECTS_ANCHOR} data-testid="learning-subjects-card">
      <CardContent>
        {/* 送った先で、上に固定されたアプリのバーの下に見出しが隠れないよう余白を取る。
            フォーカスの枠は、利用者が選べる「フォーカス表示強化」（AccessibilityProvider・既定でオン）に任せる */}
        <Typography
          variant="h6"
          component="h2"
          gutterBottom
          id={HEADING_ID}
          ref={headingRef}
          tabIndex={-1}
          sx={{ scrollMarginTop: (theme) => theme.spacing(11) }}
        >
          学ぶ科目
        </Typography>
        <Typography id={DESCRIPTION_ID} variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください
        </Typography>
        {renderBody()}
      </CardContent>
    </Card>
  );
};

export default LearningSubjectsCard;
