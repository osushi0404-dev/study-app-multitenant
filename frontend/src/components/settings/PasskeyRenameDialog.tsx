/**
 * パスキーの名前を変えるダイアログ（I619）。1〜64 文字（前後の空白を除く）
 */
import { useEffect } from 'react';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from '@mui/material';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

import { apiErrorText, PASSKEY_RENAME_FAILED } from '../../utils/passkeyErrors';

const NAME_MAX_LENGTH = 64;
const schema = yup.object({
  name: yup
    .string()
    .trim()
    .required('名前を入力してください')
    .max(NAME_MAX_LENGTH, `名前は${NAME_MAX_LENGTH}文字までです`),
});
type FormValues = yup.InferType<typeof schema>;

type Props = {
  open: boolean;
  currentName: string;
  onSave: (name: string) => Promise<void>;
  onCancel: () => void;
};

function PasskeyRenameDialog({ open, currentName, onSave, onCancel }: Props) {
  const { register, handleSubmit, setError, reset, formState } = useForm<FormValues>({
    resolver: yupResolver(schema),
    mode: 'onTouched',
    defaultValues: { name: currentName },
  });

  useEffect(() => {
    if (open) reset({ name: currentName });
  }, [open, currentName, reset]);

  const submit = async ({ name }: FormValues) => {
    try {
      await onSave(name);
    } catch (error) {
      setError('name', { message: apiErrorText(error, PASSKEY_RENAME_FAILED) });
    }
  };

  return (
    <Dialog open={open} onClose={onCancel} fullWidth maxWidth="xs" aria-labelledby="passkey-rename-title">
      <DialogTitle id="passkey-rename-title">名前を変える</DialogTitle>
      <form onSubmit={handleSubmit(submit)} noValidate>
        <DialogContent>
          <TextField
            fullWidth
            autoFocus
            label="名前"
            error={!!formState.errors.name}
            helperText={formState.errors.name?.message ?? `1〜${NAME_MAX_LENGTH}文字`}
            {...register('name')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onCancel} sx={{ minHeight: 44 }}>
            キャンセル
          </Button>
          <Button type="submit" variant="contained" disabled={formState.isSubmitting} sx={{ minHeight: 44 }}>
            保存
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

export default PasskeyRenameDialog;
