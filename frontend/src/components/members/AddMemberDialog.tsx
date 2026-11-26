/**
 * メンバーを追加するダイアログ（I620）。入力はユーザー ID だけ（メール・パスワード・名前は持たない）
 * 追加の後は、呼ぶ側が続けて登録用リンクを発行する
 */
import { useEffect } from 'react';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from '@mui/material';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

import { apiErrorText } from '../../utils/passkeyErrors';

const ADD_FAILED = 'メンバーを追加できませんでした。もう一度お試しください';
const schema = yup.object({
  userId: yup
    .string()
    .trim()
    .required('ユーザーIDを入力してください')
    .min(3, '3文字以上で入力してください')
    .max(30, '30文字以内で入力してください')
    .matches(/^[a-zA-Z0-9_]+$/, '半角英数字とアンダースコアのみ使用できます'),
});
type FormValues = yup.InferType<typeof schema>;

type Props = {
  open: boolean;
  onAdd: (userId: string) => Promise<void>;
  onCancel: () => void;
};

function AddMemberDialog({ open, onAdd, onCancel }: Props) {
  const { register, handleSubmit, setError, reset, formState } = useForm<FormValues>({
    resolver: yupResolver(schema),
    mode: 'onTouched',
    defaultValues: { userId: '' },
  });

  useEffect(() => {
    if (open) reset({ userId: '' });
  }, [open, reset]);

  const submit = async ({ userId }: FormValues) => {
    try {
      await onAdd(userId);
    } catch (error) {
      setError('userId', { message: apiErrorText(error, ADD_FAILED) });
    }
  };

  return (
    <Dialog open={open} onClose={onCancel} fullWidth maxWidth="xs" aria-labelledby="add-member-title">
      <DialogTitle id="add-member-title">メンバーを追加</DialogTitle>
      <form onSubmit={handleSubmit(submit)} noValidate>
        <DialogContent>
          <TextField
            fullWidth
            autoFocus
            label="ユーザーID"
            error={!!formState.errors.userId}
            helperText={formState.errors.userId?.message ?? '3〜30 文字の半角英数字とアンダースコア'}
            {...register('userId')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onCancel} sx={{ minHeight: 44 }}>
            キャンセル
          </Button>
          <Button type="submit" variant="contained" disabled={formState.isSubmitting} sx={{ minHeight: 44 }}>
            追加してリンクを発行
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

export default AddMemberDialog;
