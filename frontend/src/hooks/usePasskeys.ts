/**
 * 本人のパスキーの一覧と、登録・名前の変更・削除（I619）
 * 取得は React Query（規約 §5）。書き込みの後は一覧のキーを読み直す
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import passkeyService, { createPasskeyCredential } from '../services/passkey.service';
import { toLoadState } from './queryLoadState';

const passkeysKey =(userId: string) => ['passkeys', userId] as const;

export const usePasskeys = (userId: string) => {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: passkeysKey(userId), queryFn: () => passkeyService.list() });
  const refresh = () => queryClient.invalidateQueries({ queryKey: passkeysKey(userId) });

  const register = useMutation({
    mutationFn: async (reauthToken: string) => {
      const options = await passkeyService.registerOptions(reauthToken);
      const credential = await createPasskeyCredential(options);
      return passkeyService.register(reauthToken, options.challenge_id, credential);
    },
    onSuccess: refresh,
  });

  const rename = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => passkeyService.rename(id, name),
    onSuccess: refresh,
  });

  const remove = useMutation({
    mutationFn: ({ reauthToken, id }: { reauthToken: string; id: string }) => passkeyService.remove(reauthToken, id),
    onSuccess: refresh,
  });

  return { list: toLoadState(query), register, rename, remove };
};
